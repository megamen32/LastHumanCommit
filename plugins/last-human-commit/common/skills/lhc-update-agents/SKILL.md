---
name: lhc-update-agents
description: Edit canonical LHC sources, rebuild the plugin package and update the selected native harness installations.
---

# Update LHC

Edit `common/` and `adapters/` in a task worktree. Root `skills/` and `plugins/last-human-commit` are generated copies.

Run `scripts/publish_package.py` and `plugins/last-human-commit/scripts/sync_skills.py`, synchronize the version, and check the affected behavior and package parity. The full validator is `tests/validate.py`. Publish and integrate into the authorized target.

Update each selected installation through its native plugin manager. For Codex use `python3 deploy/plugin-autoupdate/install-codex-plugin.py` after refreshing the marketplace. The wrapper preserves old expanded hook paths still used by open chats while the new package loads.

Try an ordinary request through the installed loader. For a hook change, include an already-open session when that compatibility matters. Report package publication, installed files and observed runtime behavior separately.
