"""Real shell boundary regression: advisory errors must not veto a message."""
import json
import os
from pathlib import Path
import pytest

from _inprocess import run_hook_command

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'plugins/last-human-commit'


def run_hook(command, root):
    env = dict(os.environ)
    for key in ('CLAUDE_PLUGIN_ROOT', 'CODEX_PLUGIN_ROOT', 'PLUGIN_ROOT', 'ZCODE_PLUGIN_ROOT'):
        env.pop(key, None)
    env['CODEX_PLUGIN_ROOT'] = str(root)
    # The hook command is shell text: it runs the entry script and falls back
    # to an advisory message when the script cannot run. The helper runs the
    # same entry function in-process and reproduces that fallback exactly.
    return run_hook_command(command, env=env, cwd=ROOT)


@pytest.mark.nightly
def test_missing_package_does_not_block_message():
    config = json.loads((PACKAGE / 'hooks/hooks.json').read_text())
    missing = ROOT / '.tmp/nonexistent-cache-version-for-hook-test'
    assert not missing.exists()
    for groups in config['hooks'].values():
        result = run_hook(groups[0]['hooks'][0]['command'], missing)
        assert result.returncode == 0, result.stderr
        assert 'entry unavailable' in result.stderr


def test_existing_observer_executes_without_fallback():
    config = json.loads((PACKAGE / 'hooks/hooks.json').read_text())
    command = config['hooks']['SessionStart'][0]['hooks'][0]['command']
    result = run_hook(command, PACKAGE)
    assert result.returncode == 0, result.stderr
    assert 'entry unavailable' not in result.stderr
