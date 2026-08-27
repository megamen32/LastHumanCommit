---
name: lhc-rollout
description: Roll out a committed Last Human Commit release or compatible versioned instruction set across local and SSH Fleet hosts with exact preview, confirmation-bound apply, atomic current switching, marker-preserving router updates, machine-wide store, project/plugin copies, rollback receipts, and digest verification. Use when the user asks to deploy, synchronize, update, verify, or preview an LHC release on one or more agent-harness machines.
---

# LHC Rollout

Use the bundled deterministic script. Do not rediscover or rewrite the rollout
procedure in the prompt.

## Workflow

1. Require a committed source revision and an explicit Fleet manifest. When
   creating or changing the manifest, read [references/manifest.md](references/manifest.md).
   For the current 100/44/88/Mac topology, use
   `assets/last-human-commit-fleet.json`; do not rediscover that matrix.
2. Run preview:

   ```bash
   python3 scripts/lhc_rollout.py preview --manifest MANIFEST.json > PREVIEW.json
   ```

3. Check the version, digest, exact targets, actions, and rollback paths. Stop
   on a missing target, freshness conflict, immutable-version collision, or
   unresolved router role reference.
4. If the user's request already authorizes rollout, apply the exact preview:

   ```bash
   confirmation=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["confirmation"])' PREVIEW.json)
   python3 scripts/lhc_rollout.py apply --manifest MANIFEST.json --confirm "$confirmation"
   ```

   Otherwise return the preview and wait. Never manufacture or reuse a stale
   confirmation.
5. Verify independently:

   ```bash
   python3 scripts/lhc_rollout.py verify --manifest MANIFEST.json
   ```

6. Run one physical harness canary that reads the installed router or role
   file. Do not substitute provider, logs, DB, Grafana, permissions, or secret
   checks for LHC delivery.

## Machine-wide store

One LHC store per host: `~/.local/share/last-human-commit/current`. Project
routers reference the machine store absolutely; per-project
`.last-human-commit/` runtimes are legacy — remove them after routers are
re-pointed. One apply per version: a rollback receipt for version X blocks
re-applying X; push a new commit to create a new version. Freshness windows
(~5 minutes) protect files a rollout just touched — wait them out, don't
force.

## Source of truth

- Canonical: `~/agents-projects/LastHumanCommit/skills/lhc-rollout` (repo,
  main branch).
- Mirrors: the LHC plugin package `skills/lhc-rollout/` and harness-local
  copies such as `~/.zcode/skills/lhc-rollout`.
- Never hand-edit a mirror; change the repo, then redeploy. The rollout
  manifest contains no credentials.

## Result

Report one compact host matrix: version, digest, global routers, projects,
copies, rollback receipt, and `verified|failed|rolled_back`. Qualify unsupported
harness adapters explicitly.
