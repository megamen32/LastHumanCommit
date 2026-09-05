#!/usr/bin/env python3
"""One-time native registrations to an already installed Agent Plugin."""
import argparse
import json
from pathlib import Path

BEGIN = '<!-- last-human-commit:begin -->'
END = '<!-- last-human-commit:end -->'

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--plugin-root', type=Path, required=True)
    p.add_argument('--home', type=Path, default=Path.home())
    p.add_argument('--backup-root', type=Path, required=True)
    p.add_argument('--apply', action='store_true')
    a = p.parse_args()
    root = a.plugin_root.resolve()
    assert (root / 'plugin.json').is_file() and (root / 'common/agents/Lead.md').is_file()
    changes = {}
    for rel in ['.codex/AGENTS.md', '.zcode/AGENTS.md', '.config/opencode/AGENTS.md', '.claude/CLAUDE.md']:
        f = a.home / rel
        if not f.exists():
            continue
        s = f.read_text()
        if s.count(BEGIN) != 1 or s.count(END) != 1:
            continue
        before, rest = s.split(BEGIN)
        _, after = rest.split(END)
        block = f'{BEGIN}\nRead `{root / "AGENTS.md"}` for the LHC role router. Resolve its common/ paths from `{root}`.\nHarness extensions and updates use Agent Plugins and the native marketplace. Legacy Fleet-copy rollout is disabled for ordinary delivery.\n{END}'
        changes[f] = before + block + after
    config = a.home / '.config/opencode/opencode.json'
    if config.exists():
        d = json.loads(config.read_text())
        skills = d.setdefault('skills', {'paths': []})
        paths = skills.setdefault('paths', []) if isinstance(skills, dict) else skills
        paths[:] = [x for x in paths if 'last-human-commit' not in x.lower()]
        paths.append(str(root / 'skills'))
        plugins = d.setdefault('plugin', [])
        plugins[:] = [x for x in plugins if not isinstance(x, str) or ('last-human-commit' not in x.lower() and 'lhc-time-guard' not in x)]
        plugins.append(str(root / 'opencode/lhc-time-guard.ts'))
        changes[config] = json.dumps(d, indent=2) + '\n'
    for path, content in changes.items():
        if content == path.read_text():
            continue
        print(('apply ' if a.apply else 'preview ') + str(path))
        if a.apply:
            backup = a.backup_root / path.relative_to(a.home)
            backup.parent.mkdir(parents=True, exist_ok=True)
            if not backup.exists():
                backup.write_bytes(path.read_bytes())
                backup.chmod(0o600)
            path.write_text(content)

if __name__ == '__main__':
    main()
