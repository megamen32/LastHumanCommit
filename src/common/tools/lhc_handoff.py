"""Private immutable handoffs in the existing orchestration records."""
import hashlib
import json
import os
import stat
from pathlib import Path

MAX_BRIEF_BYTES = 128 * 1024
MAX_PAYLOAD_BYTES = 256 * 1024


def _digest(value):
    return hashlib.sha256(value).hexdigest()


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('brief_duplicate_field:' + key)
        result[key] = value
    return result


def _fields(text):
    """Read explicit contract field records, without guessing prose semantics."""
    try:
        parsed = json.loads(text, object_pairs_hook=_unique_object)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    result, key, lines = {}, None, []
    for line in text.splitlines():
        if line and not line[0].isspace() and ':' in line and not line.startswith(('#', chr(96) * 3)):
            if key is not None:
                if key in result:
                    raise ValueError('brief_duplicate_field:' + key)
                result[key] = '\n'.join(lines).strip()
            key, value = line.split(':', 1)
            key, lines = key.strip(), [value.strip()]
        elif key is not None and not line.startswith(chr(96) * 3):
            lines.append(line)
    if key is not None:
        if key in result:
            raise ValueError('brief_duplicate_field:' + key)
        result[key] = '\n'.join(lines).strip()
    return result


def _present(value):
    return bool(value) and (not isinstance(value, str) or value.strip() not in {'', 'null', '~'})


def _object(value):
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value, object_pairs_hook=_unique_object)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
        return _fields('\n'.join(line.strip() for line in value.splitlines()))
    return {}


def _empty_scope(value):
    return value == [] or isinstance(value, str) and value.strip() == '[]'


def _identity(value, expected):
    if isinstance(value, dict):
        return value == expected
    parsed = _object(value)
    return parsed == expected if parsed else value == expected['session_id']


def validate_brief(text, leaf_id, assignment, metadata, *, task_id):
    fields = _fields(text)
    required = ('task_id', 'leaf_id', 'owner/session', 'parent_lead_identity',
                'parent_task_id/session/route', 'role', 'mode', 'description',
                'acceptance', 'read_paths', 'write_paths', 'excluded_scope', 'next_action')
    missing = [name for name in required if name not in fields or not _present(fields[name])]
    for name in ('read_paths', 'write_paths', 'excluded_scope'):
        if name in fields and _empty_scope(fields[name]) and name in missing:
            missing.remove(name)
    if missing:
        raise ValueError('brief_incomplete:' + ','.join(missing))
    if fields['leaf_id'] != leaf_id:
        raise ValueError('brief_leaf_mismatch')
    if fields['task_id'] != task_id:
        raise ValueError('brief_task_mismatch')
    if not _identity(fields['owner/session'], assignment['executor']):
        raise ValueError('brief_executor_mismatch')
    if not _identity(fields['parent_lead_identity'], assignment['lead']):
        raise ValueError('brief_return_identity_mismatch')
    return_route = _object(fields['parent_task_id/session/route'])
    if not return_route and isinstance(fields['parent_task_id/session/route'], str):
        parts = fields['parent_task_id/session/route'].split('/', 2)
        if len(parts) == 3:
            return_route = dict(zip(('task_id', 'session_id', 'route'), parts))
    if (return_route.get('task_id') != fields['task_id']
            or return_route.get('session_id') != assignment['lead']['session_id']
            or not _present(return_route.get('route'))):
        raise ValueError('brief_return_route_required')
    if fields['role'] not in {'artifact_writer', 'execution_worker', 'tester', 'research_worker'}:
        raise ValueError('brief_role_invalid')
    if fields['mode'] not in {'quickfix', 'fullcycle', 'testing', 'research'}:
        raise ValueError('brief_mode_invalid')
    if _empty_scope(fields['read_paths']) and not _present(fields.get('input')):
        raise ValueError('brief_source_or_input_required')
    if fields['role'] in {'artifact_writer', 'execution_worker'} and _empty_scope(fields['write_paths']):
        raise ValueError('brief_write_scope_required')
    acceptance = _object(fields['acceptance'])
    output = acceptance.get('output', fields.get('output'))
    destination = acceptance.get('destination', fields.get('destination'))
    checks = acceptance.get('checks', fields['acceptance'] if not acceptance else None)
    if not all(_present(value) for value in (output, destination, checks)):
        raise ValueError('brief_acceptance_requires_output_destination_checks')
    if fields['role'] == 'artifact_writer':
        writer = _object(fields.get('artifact_writer_acceptance'))
        if _empty_scope(fields.get('exclusive_plan_write_paths')) or not _present(fields.get('exclusive_plan_write_paths')):
            raise ValueError('brief_artifact_writer_scope_required')
        if not all(_present(writer.get(key)) for key in ('user_language', 'semantic_completeness', 'readable_artifacts')):
            raise ValueError('brief_artifact_writer_acceptance_required')
    return fields


def read_brief(plan_dir, leaf_id, assignment, metadata):
    """Preflight gives actionable errors before opening a native transport."""
    root = Path(plan_dir).resolve()
    if not leaf_id or Path(leaf_id).name != leaf_id or leaf_id in {'.', '..'}:
        raise ValueError('brief_leaf_invalid')
    root_fd = briefs_fd = brief_fd = None
    try:
        root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        briefs_fd = os.open('briefs', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=root_fd)
        brief_fd = os.open(leaf_id + '.md', os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                           dir_fd=briefs_fd)
        if not stat.S_ISREG(os.fstat(brief_fd).st_mode):
            raise ValueError('brief_regular_file_required')
        with os.fdopen(brief_fd, 'rb') as stream:
            brief_fd = None
            brief_bytes = stream.read(MAX_BRIEF_BYTES + 1)
        if len(brief_bytes) > MAX_BRIEF_BYTES:
            raise ValueError('brief_too_large:limit_bytes=' + str(MAX_BRIEF_BYTES))
        brief = brief_bytes.decode('utf-8')
    except (OSError, UnicodeError):
        raise ValueError('brief_unavailable') from None
    finally:
        for fd in (brief_fd, briefs_fd, root_fd):
            if fd is not None:
                os.close(fd)
    validate_brief(brief, leaf_id, assignment, metadata, task_id=root.name)
    return brief_bytes, brief


def prepare(plan_dir, leaf_id, assignment, leaf_bytes, message, metadata):
    """Under the admission lock, read, validate and save the exact delivered bytes."""
    root = Path(plan_dir).resolve()
    brief_bytes, brief = read_brief(root, leaf_id, assignment, metadata)
    identity = {'schema_version': 1, 'plan_dir': str(root), 'leaf_id': leaf_id,
                'attempt_id': assignment['attempt_id'], 'lead': assignment['lead'],
                'executor': assignment['executor'], 'parent': assignment.get('parent'),
                'brief_path': 'briefs/' + leaf_id + '.md', 'brief_sha256': _digest(brief_bytes),
                'leaf_sha256': _digest(leaf_bytes)}
    route = json.dumps({key: identity[key] for key in ('lead', 'executor', 'parent')}, sort_keys=True)
    payload = (f"LHC canonical plan: {root}\nleaf: {leaf_id}\nattempt: {assignment['attempt_id']}\n"
               f"return and executor identities: {route}\nbrief_sha256: {identity['brief_sha256']}\n\n"
               + brief + '\n\nScoped caller input:\n' + message)
    if len(payload.encode()) > MAX_PAYLOAD_BYTES:
        raise ValueError('brief_payload_too_large:limit_bytes=' + str(MAX_PAYLOAD_BYTES))
    identity['payload_sha256'] = _digest(payload.encode())
    attempt_key = _digest(assignment['attempt_id'].encode())
    identity['record_path'] = f'records/{leaf_id}/attempts/{attempt_key}/handoff.json'
    record = {'identity': identity, 'brief': brief, 'message': payload}
    target = root / identity['record_path']
    for parent in (root / 'records', root / 'records' / leaf_id,
                   root / 'records' / leaf_id / 'attempts', target.parent):
        if parent.is_symlink():
            raise ValueError('brief_record_symlink_forbidden')
        parent.mkdir(mode=0o700, exist_ok=True)
    # Self-exclusion follows the private attempt even when the plan is outside
    # the usual ignored .agents tree. Never rewrite the repository's ignores.
    ignore = target.parent / '.gitignore'
    try:
        ignore_fd = os.open(ignore, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if ignore.is_symlink() or ignore.read_bytes() != b'*\n':
            raise ValueError('brief_private_ignore_mismatch') from None
    else:
        with os.fdopen(ignore_fd, 'wb') as stream:
            stream.write(b'*\n')
            stream.flush()
            os.fsync(stream.fileno())
    encoded = (json.dumps(record, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    try:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        if target.is_symlink() or target.read_bytes() != encoded:
            raise ValueError('brief_record_mismatch') from None
    else:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        parent_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    return identity, payload


def sync_intent(path):
    """Flush the saved admission and its directory before an external send."""
    for target in (Path(path), Path(path).parent):
        fd = os.open(target, os.O_RDONLY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
