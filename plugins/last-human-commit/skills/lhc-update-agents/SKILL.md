---
name: lhc-update-agents
description: Update Last Human Commit sources, regenerate the canonical Agent Plugins package, validate, commit and push, then install or update through each selected harness's native plugin marketplace or manager and prove its installed loader. Use for LHC prompts, roles, protocols, commands, skills, or plugin delivery changes.
---

# Rewrite Last Human Commit

Sources: `/home/roomhacker/agents-projects/LastHumanCommit` (git, main).
The canonical delivery unit is `plugins/last-human-commit`, following the
[Agent Plugins specification](https://agent-plugins.org/specification/).
Change owning source, regenerate the package, and use native marketplace
install/update. Never hand-edit installed packages or synchronize individual
skills into harness directories.

## 1. Baseline push — mandatory before edits

Make this bot's future changes identifiable as one commit range:

```bash
cd ~/agents-projects/LastHumanCommit
git status --porcelain   # review dirty paths and resolve ownership before committing
git log @{u}..HEAD       # push reviewed unpushed commits
git push origin main
```

The pushed HEAD is the baseline. Preserve unrelated work; do not absorb it
silently or overwrite another worker's changes.

## 2. Edit sources and generate the package

- Roles, protocols, templates, commands: `src/common/`; native adapter source:
  `adapters/`; operator skills: `skills/`.
- Generate and check the package with:

  ```bash
  python3 plugins/last-human-commit/scripts/sync_skills.py
  python3 plugins/last-human-commit/scripts/sync_skills.py --check
  python3 plugins/last-human-commit/scripts/validate.py
  ```

  Generated package content is not an independent source of truth.
- Run `python3 tests/validate.py` and fix until green; never delete checks.
- Keep the portable root `plugin.json`, `skills/`, and optional `mcp.json`
  conformant. Native hooks, manifests and extension behavior must match each
  actual client; portability does not promise identical capabilities.

## 3. Commit and push

Review the diff and commit task-owned files at completed steps. Push the verified
package and source through the repository's main delivery history.

## 4. Install or update through native loaders

For each selected installed harness, identify its actual plugin marketplace or
manager and supported package entrypoint. Publish/register the versioned package
through that mechanism and request its native install/update. For a missing
installation, use the same native plugin route. Do not use Fleet copy rollout,
per-harness skill synchronization, or direct edits of installed runtime files.

Check the installed package version and run a fresh harness session that
actually discovers and invokes an LHC skill or supported extension from that
package. Static manifest checks and reading a file alone do not prove loading.
Report source tests, package publication, installed version and real loader
canary separately per target. Automatic refresh/restart and extension support
are client-specific; do not claim universal auto-updates.

If the target has no compatible native loader, report that observed limitation
and ask for an explicitly selected compatibility route. `lhc-rollout` is
available only for explicitly selected legacy recovery/rollback, never as an
automatic fallback or normal release step.
