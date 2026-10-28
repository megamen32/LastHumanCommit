"""Run the actual native hook shell commands across a pruned plugin root."""
import json
import os
from pathlib import Path
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'adapters/codex/hooks/hooks.json'


def commands():
    hooks = json.loads(MANIFEST.read_text())['hooks']
    return [(event, hook['command']) for event, groups in hooks.items()
            for group in groups for hook in group['hooks']
            if 'lhc_progress_review.py' in hook['command']]


def invoke(command, tmp_path, package):
    env = dict(os.environ)
    for key in ('PLUGIN_ROOT', 'CODEX_PLUGIN_ROOT', 'CLAUDE_PLUGIN_ROOT', 'ZCODE_PLUGIN_ROOT'):
        env.pop(key, None)
    env.update(CODEX_PLUGIN_ROOT=str(package), HOME=str(tmp_path), CODEX_HOME=str(tmp_path / '.codex'))
    return subprocess.run(['/bin/sh', '-c', command], input='{"hook_event_name":"Stop"}\n',
                          capture_output=True, text=True, env=env, timeout=3)


@pytest.mark.parametrize('event,command', commands())
def test_pruned_optional_hook_root_never_blocks(event, command, tmp_path):
    result = invoke(command, tmp_path, tmp_path / 'pruned-version')
    assert result.returncode == 0, (event, result.stderr)
    assert "can't open file" not in result.stderr


@pytest.mark.parametrize('fallback', [False, True])
@pytest.mark.parametrize('event,command', commands())
def test_optional_hook_keeps_stdin_and_invalidation(event, command, tmp_path, fallback):
    package = (tmp_path / '.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit'
               if fallback else tmp_path / 'valid-version')
    script = package / 'tools/lhc_progress_review.py'
    script.parent.mkdir(parents=True)
    script.write_text('import json, sys\nprint(json.dumps({"args":sys.argv[1:],"stdin":sys.stdin.read()}))\n')
    result = invoke(command, tmp_path, tmp_path / 'pruned-version' if fallback else package)
    assert result.returncode == 0, result.stderr
    captured = json.loads(result.stdout)
    assert captured['stdin'] == '{"hook_event_name":"Stop"}\n'
    assert captured['args'] == ([] if event == 'PostToolUse' else ['--invalidate'])


def test_optional_adviser_failure_cannot_veto_a_prompt(tmp_path):
    package = tmp_path / 'failing-version'
    script = package / 'tools/lhc_progress_review.py'
    script.parent.mkdir(parents=True)
    script.write_text('raise SystemExit(7)\n')
    for event, command in commands():
        assert invoke(command, tmp_path, package).returncode == 0, event
