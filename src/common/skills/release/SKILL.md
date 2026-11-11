---
name: release
description: Integrate, publish or deploy an authorized change using the project's existing release route.
---

# Release

Resolve the target branch, environment and candidate revision. Use the existing project instructions and test access. Complete the relevant checks and try the candidate in the agreed environment.

Publish the task branch as work progresses. When ready, use `lhc_worktree.py delivery` to check its published state; open a PR when `pr_stage=on`, then complete the permitted merge. With PR mode off, use the repository's permitted integration route.

Build from the integrated revision and install where the task requires it. For a shared live service, acquire the project release lease just before the switch, check the expected live revision, and release it after the scenario check. `common/protocols/SHARED_WORKTREE.md` documents the lease and supported fallback.

Use the existing recovery procedure if needed. Confirm that a proposed rollback version can restore service. Keep actual source, publication, installation and consumer results distinct in the report.

## Version

The root `VERSION` is `X.Y.Z`: X changes a contract incompatibly, Y adds a compatible capability, Z fixes code or wording. Reconcile the target, use `lhc_version.py bump` for the next version, synchronize manifests and publish. A tag belongs to the merged commit.
