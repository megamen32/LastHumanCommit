"""Real shell boundary regression: advisory errors must not veto a message."""
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/last-human-commit'


def run_hook(command, root):
    env = dict(os.environ)
    for key in ('CLAUDE_PLUGIN_ROOT', 'CODEX_PLUGIN_ROOT', 'PLUGIN_ROOT', 'ZCODE_PLUGIN_ROOT'):
        env.pop(key, None)
    env['CODEX_PLUGIN_ROOT'] = str(root)
    return subprocess.run(['sh', '-c', command], input='{}', text=True,
                          capture_output=True, env=env, cwd=ROOT, timeout=10)


def test_missing_package_does_not_block_message():
    config = json.loads((PACKAGE / 'hooks/hooks.json').read_text())
    missing = ROOT / '.tmp/nonexistent-cache-version-for-hook-test'
    assert not missing.exists()
    for groups in config['hooks'].values():
        result = run_hook(groups[0]['hooks'][0]['command'], missing)
        assert result.returncode == 0, result.stderr
        assert 'observer unavailable' in result.stderr


def test_existing_observer_executes_without_fallback():
    config = json.loads((PACKAGE / 'hooks/hooks.json').read_text())
    command = config['hooks']['UserPromptSubmit'][0]['hooks'][0]['command']
    result = run_hook(command, PACKAGE)
    assert result.returncode == 0, result.stderr
    assert 'observer unavailable' not in result.stderr
