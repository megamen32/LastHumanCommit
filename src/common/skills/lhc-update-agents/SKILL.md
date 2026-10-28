---
name: lhc-update-agents
description: Update the shared LHC sources, generate and validate the native plugin, then publish and verify the selected installed loaders.
---

# Update LHC

Own the change in `LastHumanCommit`, not in an installed cache or a copy in
another project. Preserve foreign work; use a worktree when another writer is
present. The source is `src/common/` and `adapters/`; the repo-root `skills/` tree
is a generated projection of `src/common/skills/`, not a second source. The delivery
package is `plugins/last-human-commit`.

Generate with `python3 plugins/last-human-commit/scripts/sync_skills.py`, check
with `--check` and run the relevant behavioral tests plus both validators.
Keep manifests at the same version. Review, push, create a PR and merge when
checks and authority allow; then verify the merged source.

Use each selected harness's native plugin manager. For Codex, invoke it through
`python3 deploy/plugin-autoupdate/install-codex-plugin.py` from this checkout,
after refreshing the configured marketplace. This wrapper retains compatibility
routes for old versioned hook paths in the same operation as the native update;
a bare `codex plugin add` can prune paths still used by open chats. These routes
point to the identified marketplace tools and do not install old versions or
edit tool contents in the cache. Verify old expanded hook commands as well as
the new installed definitions; a fresh hook listing is not a live-chat reload.
Test the installed loader
with an ordinary engineering request, not only an explicit skill invocation.
Report source validation, package publication and actual runtime loading
separately. A source test does not prove every running session has reloaded.
