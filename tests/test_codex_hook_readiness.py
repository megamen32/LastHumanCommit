# LHC:COVERS deploy/plugin-autoupdate/codex-hook-readiness.py deploy/plugin-autoupdate/install-codex-plugin.py deploy/plugin-autoupdate/lhc-harness-autoupdate.sh
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'deploy/plugin-autoupdate/codex-hook-readiness.py'
INSTALLER = ROOT / 'deploy/plugin-autoupdate/install-codex-plugin.py'
UPDATER = ROOT / 'deploy/plugin-autoupdate/lhc-harness-autoupdate.sh'


def fake_codex(tmp_path, status='trusted'):
    exe = tmp_path / 'codex'
    exe.write_text('''#!/usr/bin/env python3
import json, sys, time
if sys.argv[1:] != ['app-server', '--stdio']:
    sys.exit(0)
for line in sys.stdin:
    req = json.loads(line)
    if req.get('method') == 'initialize':
        assert req['params']['capabilities']['experimentalApi'] is True
        print(json.dumps({'id': req['id'], 'result': {}}), flush=True)
    elif req.get('method') == 'hooks/list':
        assert req['params']['cwds']
        if STATUS == 'timeout': time.sleep(3)
        hook = {'key': 'namespace:key', 'pluginId': 'last-human-commit@megamen32-plugins', 'eventName': 'SessionStart', 'enabled': True, 'trustStatus': STATUS, 'currentHash': 'sha256:cmd/sha256:content', 'command': 'hook command', 'sourcePath': '/plugin/hooks.json'}
        print(json.dumps({'id': req['id'], 'result': {'data': [{'cwd': req['params']['cwds'][0], 'hooks': [hook], 'warnings': [], 'errors': []}]}}), flush=True)
'''.replace('STATUS', repr(status)))
    exe.chmod(0o755)
    return exe


def run_helper(exe, timeout='1'):
    return subprocess.run([sys.executable, str(HELPER), '--codex-bin', str(exe), '--timeout', timeout], text=True, capture_output=True)


def test_native_readback_ready_and_modified(tmp_path):
    native = fake_codex(tmp_path)
    ready = run_helper(native)
    assert ready.returncode == 0
    assert json.loads(ready.stdout)['status'] == 'READY'
    native = fake_codex(tmp_path, 'modified')
    modified = run_helper(native)
    assert modified.returncode != 0
    result = json.loads(modified.stdout)
    assert result['status'] == 'NEEDS_REVIEW'
    assert result['hooks'][0]['currentHash'] == 'sha256:cmd/sha256:content'
    assert result['hooks'][0]['key'] == 'namespace:key'


def test_missing_runtime_and_timeout_are_errors(tmp_path):
    for result in (run_helper(tmp_path / 'absent'), run_helper(fake_codex(tmp_path, 'timeout'), '0.1')):
        assert result.returncode != 0
        assert json.loads(result.stdout)['status'] == 'ERROR'


def test_installer_fails_if_native_hook_needs_review(tmp_path):
    spec = importlib.util.spec_from_file_location('installer_readiness_test', INSTALLER)
    installer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(installer)
    cache = tmp_path / 'cache/last-human-commit'
    cache.mkdir(parents=True)
    tools = tmp_path / 'source/tools'
    tools.mkdir(parents=True)
    for name in installer.compat.REQUIRED:
        (tools / name).write_text('# hook')
    (tools.parent / 'plugin.json').write_text('{"name":"last-human-commit"}')
    assert installer.install(str(fake_codex(tmp_path, 'modified')), cache, tools) != 0


def test_updater_does_not_retry_after_wrapper_failure(tmp_path):
    home = tmp_path / 'home'
    market = home / '.codex/.tmp/marketplaces/megamen32-plugins'
    (market / 'plugins/last-human-commit/.claude-plugin').mkdir(parents=True)
    (market / 'plugins/last-human-commit/.claude-plugin/plugin.json').write_text('{}')
    (market / 'deploy/plugin-autoupdate').mkdir(parents=True)
    (market / 'deploy/plugin-autoupdate/install-codex-plugin.py').write_text('import sys\nprint("NEEDS_REVIEW", file=sys.stderr)\nsys.exit(1)\n')
    bin_dir = home / '.local/bin'
    bin_dir.mkdir(parents=True)
    calls = tmp_path / 'calls'
    (bin_dir / 'codex').write_text('#!/bin/sh\necho called >> ' + str(calls) + '\n')
    (bin_dir / 'codex').chmod(0o755)
    result = subprocess.run(['bash', str(UPDATER)], env={**os.environ, 'HOME': str(home)}, text=True, capture_output=True)
    assert result.returncode == 0
    assert not calls.exists()
    assert 'NEEDS_REVIEW' in result.stdout + result.stderr


def test_assessment_rejects_empty_disabled_and_warnings():
    spec = importlib.util.spec_from_file_location('readiness_assess_test', HELPER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hook = {'pluginId': module.PLUGIN, 'key': 'k', 'currentHash': 'h', 'enabled': True, 'trustStatus': 'trusted'}
    def assess(hooks, warnings=(), errors=()):
        return module.assess({'data': [{'cwd': '/home/user', 'hooks': hooks, 'warnings': list(warnings), 'errors': list(errors)}]})['status']
    assert assess([]) == 'NEEDS_REVIEW'
    assert assess([{**hook, 'enabled': False}]) == 'NEEDS_REVIEW'
    assert assess([hook], warnings=['unresolved hook']) == 'NEEDS_REVIEW'
    assert assess([hook], errors=['hook failed']) == 'NEEDS_REVIEW'
    assert assess([hook, {**hook, 'pluginId': 'unrelated', 'trustStatus': 'modified'}]) == 'READY'


def test_updater_falls_back_when_wrapper_absent(tmp_path):
    home = tmp_path / 'home'
    market = home / '.codex/.tmp/marketplaces/megamen32-plugins'
    (market / 'plugins/last-human-commit/.claude-plugin').mkdir(parents=True)
    (market / 'plugins/last-human-commit/.claude-plugin/plugin.json').write_text('{}')
    bin_dir = home / '.local/bin'
    bin_dir.mkdir(parents=True)
    calls = tmp_path / 'calls'
    (bin_dir / 'codex').write_text('#!/bin/sh\necho "$*" >> ' + str(calls) + '\n')
    (bin_dir / 'codex').chmod(0o755)
    result = subprocess.run(['bash', str(UPDATER)], env={**os.environ, 'HOME': str(home)}, text=True, capture_output=True)
    assert result.returncode == 0
    assert calls.read_text().splitlines() == ['plugin marketplace upgrade megamen32-plugins']
