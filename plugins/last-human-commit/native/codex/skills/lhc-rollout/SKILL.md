---
name: lhc-rollout
description: Legacy recovery only. Use solely when the user explicitly selects old Fleet file rollout or rollback for Last Human Commit; never for ordinary plugin install, update, or delivery. Preserves deterministic preview, exact apply, verification and rollback receipts.
---

# LHC legacy recovery

Normal LHC delivery uses the generated `plugins/last-human-commit` Agent Plugins
package and the target harness native plugin marketplace/manager; see
`../lhc-update-agents/SKILL.md`. This old file-copy route is disabled for normal
install/update and must not run as a fallback when a plugin loader is missing.

Proceed below only when the user explicitly selected legacy Fleet recovery or
rollback for named targets. Keep existing rollback receipts and capabilities.
Use the bundled deterministic script; do not rewrite the recovery procedure.

## Explicitly selected legacy workflow

1. Require a committed source revision and an explicit Fleet manifest. When
   creating or changing the manifest, read [references/manifest.md](references/manifest.md).
   For the current 100/44/88/Mac topology, use
   `assets/last-human-commit-fleet.json`; do not rediscover that matrix.
2. Run preview:

   ```bash
   python3 scripts/lhc_rollout.py preview --legacy-recovery --manifest MANIFEST.json > PREVIEW.json
   ```

3. Check the version, digest, exact targets, actions, and rollback paths. Stop
   on a missing target, freshness conflict, immutable-version collision, or
   unresolved router role reference.
4. If the user's request explicitly authorizes this legacy recovery, apply the exact preview:

   ```bash
   confirmation=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["confirmation"])' PREVIEW.json)
   python3 scripts/lhc_rollout.py apply --legacy-recovery --manifest MANIFEST.json --confirm "$confirmation"
   ```

   Otherwise return the preview and wait. Never manufacture or reuse a stale
   confirmation.
5. Verify independently:

   ```bash
   python3 scripts/lhc_rollout.py verify --legacy-recovery --manifest MANIFEST.json
   ```

6. Run one physical harness canary that reads the installed router or role
   file. Do not substitute provider, logs, DB, Grafana, permissions, or secret
   checks for LHC delivery.

## Machine-wide store

One LHC store per host: `~/.local/share/last-human-commit/current`. Project
routers reference the machine store absolutely; per-project
`.last-human-commit/` runtimes are legacy. Remove them only when the selected
recovery includes that migration and the restored consumer path is verified. One apply per version: a rollback receipt for version X blocks
re-applying X; push a new commit to create a new version. Freshness windows
(~5 minutes) protect files a rollout just touched — wait them out, don't
force.

## Source of truth

- Canonical: `~/agents-projects/LastHumanCommit/skills/lhc-rollout` (repo,
  main branch).
- Distribution: generated inside the canonical LHC plugin package. Do not
  synchronize this skill separately into harness-local directories.
- Never hand-edit an installed package; change source and use native package
  install/update. The legacy recovery manifest contains no credentials.

## Result

Report one compact host matrix: version, digest, global routers, projects,
copies, rollback receipt, and `verified|failed|rolled_back`. Qualify unsupported
harness adapters explicitly.
