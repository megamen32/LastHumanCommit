# Entry files do not route agent roles

Description: `AGENTS.md` is maintainer-only, `CLAUDE.md` is absent, and agents
cannot cheaply discover their independently stored role instruction.
Evidence: `python3 tests/validate.py` fails with missing `CLAUDE.md`.
Blocks: `work-20260730-role-router-yagni.md`
