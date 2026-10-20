"""Explicit native task bounds constrain known writes, not harness permissions."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'src/common/tools'))
from lhc_task_scope import write_denial

SCOPE = ['Fix export.py. Work only in this directory. Do not delegate.']


@pytest.mark.parametrize('command', [
    'python3 export.py > /tmp/opencode/out.txt',
    'python3 export.py >> ../foreign/out.txt',
    'python3 export.py 2> /tmp/opencode/error.txt',
    "bash -lc 'python3 export.py > /tmp/opencode/out.txt'",
])
def test_known_external_shell_outputs_are_denied(tmp_path, command):
    assert write_denial(SCOPE, tmp_path, 'shell', {'command': command})


@pytest.mark.parametrize('command', [
    'python3 export.py > .tmp/out.txt',
    'python3 export.py 2>/dev/null',
    'cat /etc/os-release',
    'cd /tmp && cat note.txt 2>/dev/null',
    "printf '%s' 'example > /tmp/opencode/out.txt'",
])
def test_local_outputs_and_read_or_quoted_data_are_not_vetoed(tmp_path, command):
    assert write_denial(SCOPE, tmp_path, 'shell', {'command': command}) is None


def test_file_write_and_symlink_escape_use_actual_directory_identity(tmp_path):
    root = tmp_path/'case'; root.mkdir()
    (root/'outside').symlink_to(tmp_path, target_is_directory=True)
    assert write_denial(SCOPE, root, 'write', {'path': str(root/'FEEDBACK.md')}) is None
    assert write_denial(SCOPE, root, 'edit', {'path': str(root/'outside/other.txt')})
    assert write_denial(SCOPE, root, 'shell', {'command': 'python3 export.py > outside/other.txt'})


@pytest.mark.parametrize('sources', [
    ['Fix export.py; ordinary working directory is not a write restriction.'],
    ['Fix documentation about "Work only in this directory."'],
    ['Fix documentation.\n```\nWork only in this directory.\n```'],
    [*SCOPE, 'Allowed additional output: /tmp/operator-output.txt.'],
])
def test_no_invented_scope_from_cwd_quotes_or_unresolved_user_exceptions(tmp_path, sources):
    assert write_denial(sources, tmp_path, 'write', {'path': '/tmp/operator-output.txt',
        'content': 'Work only in this directory.'}) is None
