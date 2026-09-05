import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def test_registration_preserves_other_settings(tmp_path):
    home = tmp_path / 'home'
    router = home / '.codex/AGENTS.md'
    router.parent.mkdir(parents=True)
    router.write_text('before\n<!-- last-human-commit:begin -->\nold\n<!-- last-human-commit:end -->\nafter\n')
    config = home / '.config/opencode/opencode.json'
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({'plugin': ['other.ts'], 'skills': {'paths': ['/other']}, 'model': 'keep'}))
    cmd = [sys.executable, str(ROOT / 'scripts/migrate_registration.py'), '--home', str(home), '--plugin-root', str(ROOT), '--backup-root', str(tmp_path / 'backup')]
    subprocess.run(cmd, check=True)
    assert '\nold\n' in router.read_text()
    subprocess.run(cmd + ['--apply'], check=True)
    assert router.read_text().startswith('before\n') and router.read_text().endswith('\nafter\n')
    assert 'Legacy Fleet-copy rollout is disabled' in router.read_text()
    d = json.loads(config.read_text())
    assert d['model'] == 'keep' and d['plugin'][0] == 'other.ts' and d['skills']['paths'][0] == '/other'
    before = config.read_bytes()
    subprocess.run(cmd + ['--apply'], check=True)
    assert config.read_bytes() == before
