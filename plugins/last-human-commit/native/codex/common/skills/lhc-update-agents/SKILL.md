---
name: lhc-update-agents
description: Update the shared LHC sources, generate and validate the native plugin, then publish and verify the selected installed loaders.
---

# Update LHC

Own the change in `LastHumanCommit`, not in an installed cache or a copy in
another project. Preserve foreign work; use a worktree when another writer is
present. The source is `common/` and `adapters/`; the repo-root `skills/` tree
is a generated projection of `common/skills/`, not a second source. The delivery
package is `plugins/last-human-commit`.

Generate with `python3 plugins/last-human-commit/scripts/sync_skills.py`, check
with `--check` and run the relevant behavioral tests plus both validators.
Keep manifests at the same version. Review, push, create a PR and merge when
checks and authority allow; then verify the merged source.

Use each selected harness's native plugin manager. Test the installed loader
with an ordinary engineering request, not only an explicit skill invocation.
Report source validation, package publication and actual runtime loading
separately. A source test does not prove every running session has reloaded.
