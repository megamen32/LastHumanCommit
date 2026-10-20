"""Instruction routing and safety shields for authorized local test preparation.

These are policy/projection tests, not a claim that a model rotated credentials.
"""
import json
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = 'src/common/protocols/REVIEW_TO_DELIVERY.md'


def access_policy():
    return (ROOT / PROTOCOL).read_text().split('## Execution-access contract', 1)[1].split('\n## ', 1)[0]


def test_loaded_router_lead_and_project_route_to_primary_test_access():
    router = (ROOT / 'AGENTS.md').read_text()
    assert len(router.splitlines()) <= 150
    assert '<primary checkout>/.agents/TEST_ACCESS.md' in router
    for path in ('AGENTS.md', 'src/common/agents/Lead.md',
                 'src/common/templates/project-router.md'):
        text = (ROOT / path).read_text()
        assert 'TEST_ACCESS.md' in text
        assert 'REVIEW_TO_DELIVERY.md' in text
    policy = access_policy()
    for item in ('git worktree list --porcelain', '--git-common-dir',
                 'approved protected secret refs/paths and field names',
                 'fixture owner', 'cleanup', 'latest direct authority',
                 'After compaction/resume', 'references and scope only'):
        assert item in policy


@pytest.mark.parametrize('case, obligations', [
    ('authorized fixture/local admin', ['Reuse, verify or repair', 'supported app-native local admin/API/CLI',
                                      'intentional sudo', 'Do not ask for the same valid authorization again']),
    ('stale tester password', ['Missing, expired or stale test credentials',
                              'same canonical protected reference atomically', 'preserve permissions',
                              'reference/status only']),
    ('initial password change', ['initial password change', 'ordinary preparation/recovery']),
    ('disposable OAuth registration', ['disposable OAuth client creation/grant',
                                      'test login/consent is already authorized', 'one owner',
                                      'expired codes or unsupported fixed client IDs']),
    ('native token manager', ['existing native OAuth credential manager',
                              'approved opaque-secret or in-process delivery', 'no ad-hoc plaintext copies']),
    ('external or revoked authority', ['unknown/external environment', 'human-stop/explicit denial',
                                      'customer/third-party account', 'missing external secret',
                                      'sudo availability alone never expands authority']),
    ('recoverable wait', ['Recoverable wait is not done', 'actionable next step', 'resume_after',
                          'no blind retries/autopoll', 'Never mutate automation schedules']),
    ('bounded completed coverage', ['Completed assigned consumer coverage',
                                    'no recursive testing', 'parent product acceptance']),
])
def test_access_decisions_retain_authorization_and_recovery_boundaries(case, obligations):
    policy = access_policy()
    for item in obligations:
        assert item in policy, (case, item)


def test_implementation_acceptance_deploy_and_test_skills_load_same_contract():
    for path in ('skills/worker-code/SKILL.md', 'skills/worker-bugfix/SKILL.md',
                 'skills/real-use-testing/SKILL.md', 'skills/business-delivery/SKILL.md',
                 'skills/release/SKILL.md', 'src/common/skills/user-testing/SKILL.md',
                 'src/common/skills/focus-groups/SKILL.md'):
        text = (ROOT / path).read_text()
        assert 'TEST_ACCESS.md' in text, path
        assert 'REVIEW_TO_DELIVERY.md' in text, path
    tester = (ROOT / 'src/common/skills/user-testing/SKILL.md').read_text()
    assert 'before classifying a missing login as BLOCKED_REAL_SURFACE' in tester


def test_generated_access_contract_is_generic_and_parity_checked():
    for facet in ('plugins/last-human-commit', 'plugins/last-human-commit/native/codex'):
        root = ROOT / facet
        assert (root/'common/protocols/REVIEW_TO_DELIVERY.md').read_text() == (
            ROOT/PROTOCOL).read_text().replace('src/common/', 'common/')
        template = (root/'common/templates/test-access.md').read_text()
        assert template == (ROOT/'src/common/templates/test-access.md').read_text()
        assert 'Secret values MUST NOT appear' in template
        for private in ('airlock-admin', 'credentials.json', 'luna4', 'bezrabotnyi.com'):
            assert private not in template + access_policy()
        assert 'TEST_ACCESS.md' in (root/'AGENTS.md').read_text()


def test_native_handoff_preserves_russian_goal_and_only_secret_reference(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    secret = tmp_path/'protected-fixture.json'
    sentinel = 'synthetic-value-must-not-enter-context'
    secret.write_text(json.dumps({'password': sentinel})); secret.chmod(0o600)
    (tmp_path/'.agents').mkdir()
    (tmp_path/'.agents/TEST_ACCESS.md').write_text(
        'Approved fixture; protected ref: protected-fixture.json; field: password. No values.\n')
    prompt = 'Проверь локальный тестовый вход по .agents/TEST_ACCESS.md. Не выводи пароль. Не делегируй.'
    outputs = []
    for event in ('UserPromptSubmit', 'PreCompact'):
        r = subprocess.run([sys.executable, str(ROOT/'src/common/tools/lhc_entry.py'),
            '--root', str(ROOT), '--runtime', 'codex', '--event', event],
            input=json.dumps({'cwd': str(tmp_path), 'session_id': 'access-reference', 'prompt': prompt},
                             ensure_ascii=False), text=True, capture_output=True, check=True)
        outputs.append(r.stdout)
    state = next((tmp_path/'.agents/shared-session/learning').glob('*.json')).read_text()
    assert json.loads(state)['business']['original_prompt'] == prompt
    assert sentinel not in ''.join(outputs) + state
    assert secret.stat().st_mode & 0o777 == 0o600


def test_installed_test_skills_resolve_access_protocol_in_both_native_facets():
    import re
    for facet in ('plugins/last-human-commit', 'plugins/last-human-commit/native/codex'):
        root = ROOT / facet
        for name in ('user-testing', 'focus-groups'):
            text = (root/'skills'/name/'SKILL.md').read_text()
            refs = re.findall(r'`([^`]*protocols/REVIEW_TO_DELIVERY.md)`', text)
            assert refs
            for ref in refs:
                assert (root / ref).is_file(), (facet, name, ref)
