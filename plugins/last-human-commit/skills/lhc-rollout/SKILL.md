---
name: lhc-rollout
description: Recover an explicitly selected legacy LHC Fleet installation using its existing preview, apply and verify commands.
---

# Legacy LHC recovery

Normal updates use the native plugin manager and `lhc-update-agents`. This route is for a user-selected legacy Fleet recovery or rollback.

Use the committed source and the selected manifest. `references/manifest.md` explains the fields; `assets/last-human-commit-fleet.json` is the existing fleet example.

```sh
python3 scripts/lhc_rollout.py preview --legacy-recovery --manifest MANIFEST.json > PREVIEW.json
```

Inspect the preview's version, targets, actions and rollback paths. Correct a missing target or freshness conflict before applying that target. For an authorized recovery, apply the exact returned confirmation:

```sh
confirmation=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["confirmation"])' PREVIEW.json)
python3 scripts/lhc_rollout.py apply --legacy-recovery --manifest MANIFEST.json --confirm "$confirmation"
python3 scripts/lhc_rollout.py verify --legacy-recovery --manifest MANIFEST.json
```

Try the restored router or role through the actual harness. The legacy machine store is `~/.local/share/last-human-commit/current`; preserve its recorded history and the manifest's recovery constraints. The recovery tool's version/freshness checks describe supported writes, not an invitation to rewrite its state.

Report which selected targets were restored, failed or rolled back, and what the client check established.
