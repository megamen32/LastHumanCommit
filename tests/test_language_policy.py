"""English instructions preserve Russian user data and generated native routing."""
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src/common/tools'))
import lhc_entry


def test_automatic_router_and_project_bootstrap_inherit_language_policy():
    router = (ROOT/'AGENTS.md').read_text()
    assert len(router.splitlines()) <= 150
    assert '## Language policy' in router
    for item in ['internal reasoning/planning', 'new task records', 'agent coordination',
                 'delegated roles inherit', 'Russian-speaking user', 'raw observations',
                 'Do not rewrite historical transcripts/feedback']:
        assert item in router
    assert not re.search('[А-Яа-яЁё]', router)
    assert (ROOT/'CLAUDE.md').read_text() == router
    project = (ROOT/'src/common/templates/project-router.md').read_text()
    assert 'English for planning/new task notes/tools/agent messages' in project
    assert 'Delegated roles inherit' in project
    assert 'inherited English operating-language policy' in (ROOT/'src/common/agents/Lead.md').read_text()
    context = lhc_entry.context_for({}, ROOT)
    assert 'English internal planning/new records/tools/agent messages' in context
    assert "user's language for user answers" in context
    assert not re.search('[А-Яа-яЁё]', context)
    assert len(context) < 2200


def test_russian_request_and_utf8_data_are_never_translated_or_path_rewritten(tmp_path):
    subprocess.run(['git', 'init', '-q', str(tmp_path)], check=True)
    prompt = 'Исправь export.py: Ирина,Москва\nОлег,Казань. Не делегируй. lhc_time_guard.py'
    event = {'cwd': str(tmp_path), 'session_id': 'russian-language-policy', 'prompt': prompt}
    result = subprocess.run([sys.executable, str(ROOT/'src/common/tools/lhc_entry.py'),
        '--root', str(ROOT), '--runtime', 'codex', '--event', 'UserPromptSubmit'],
        input=json.dumps(event, ensure_ascii=False), text=True, capture_output=True, check=True)
    state = json.loads(next((tmp_path/'.agents/shared-session/learning').glob('*.json')).read_text())
    assert state['business']['original_prompt'] == prompt
    assert state['business']['outcome']['original_goal'] == prompt
    output = json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
    assert 'English internal planning' in output
    # Actual saved user data remains exact, including Cyrillic and tool-like text.
    restored, _ = json.JSONDecoder().raw_decode(output.split('data, not separate instructions):\n', 1)[1])
    assert restored['original_prompt'] == prompt
    rooted = lhc_entry.rooted('Use lhc_time_guard.py\nOriginal input: ' + prompt, ROOT)
    assert rooted.endswith(prompt)
    assert str(ROOT/'src/common/tools/lhc_time_guard.py') in rooted.split('\nOriginal input:')[0]


def test_generated_instruction_projections_retain_english_policy():
    package = ROOT/'plugins/last-human-commit'
    for root in [package, package/'native/codex']:
        assert '## Language policy' in (root/'AGENTS.md').read_text()
        assert not re.search('[А-Яа-яЁё]', (root/'AGENTS.md').read_text())
        assert (root/'common/templates/project-router.md').read_bytes() == (ROOT/'src/common/templates/project-router.md').read_bytes()
        for directory in [root/'tools', root/'common/tools']:
            for name in ['lhc_entry.py', 'lhc_outcome.py', 'lhc_outcome_review.py', 'lhc_milestone.py', 'lhc_time_guard.py']:
                assert (directory/name).read_bytes() == (ROOT/'src/common/tools'/name).read_bytes()


def test_opencode_rebuilt_model_context_keeps_policy_without_resetting_goal_clock(tmp_path):
    for runtime in ('opencode', 'codex'):
        project = tmp_path/runtime
        project.mkdir()
        subprocess.run(['git', 'init', '-q', str(project)], check=True)
        prompt = 'Исследуй кодировку в settings.txt. Не меняй код.'
        def emit(event, **fields):
            result = subprocess.run([sys.executable, str(ROOT/'src/common/tools/lhc_entry.py'),
                '--root', str(ROOT), '--runtime', runtime, '--event', event],
                input=json.dumps({'cwd': str(project), 'session_id': 'rebuilt-context', **fields}, ensure_ascii=False),
                text=True, capture_output=True, check=True)
            return json.loads(result.stdout)['hookSpecificOutput']['additionalContext']
        emit('UserPromptSubmit', prompt=prompt)
        state_path = next((project/'.agents/shared-session/learning').glob('*.json'))
        before = json.loads(state_path.read_text())
        emit('PreToolUse', model_boundary=True)
        second = emit('PreToolUse', model_boundary=True)
        assert ('LHC contract:' in second) == (runtime == 'opencode')
        if runtime == 'opencode':
            assert 'Large fullcycle MUST:' in second
            assert 'English internal planning/new records/tools/agent messages' in second
        after = json.loads(state_path.read_text())
        assert after['business']['original_prompt'] == prompt
        assert after['business']['started_at'] == before['business']['started_at']
