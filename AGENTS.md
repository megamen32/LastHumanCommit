# Maintainer instructions

This repository ships agent instructions. Distributed files live under `src/`:

- `src/common/` — roles, profiles, protocols, and tracked-work templates.
- `src/global/` — host entry instruction.
- `src/project/` — project entry instruction and roadmap template.

Root files are meta: README, roadmap, tests, installer, and this file. Do not
edit generated install targets as source.

Before changing instructions:

1. Read `ROADMAP.md` and preserve its priority order.
2. Change source files under `src/`, not installed copies.
3. Add or update focused tests.
4. Run `python3 tests/validate.py`, `python3 -m pytest -q tests/test_installer.py`,
   and `sh -n install.sh`.
5. Update README when install behavior changes.

Keep text short. No harness hooks, plugins, network fetches, or dependencies.
