# Worktrees, integration and shared releases

## Task worktree

Find the primary checkout with `git worktree list --porcelain`. Reuse the assigned task worktree, or create one from the intended remote target:

```sh
python3 <LHC>/common/tools/lhc_worktree.py create --repo <project> --task <slug> --base <remote>/<target>
```

Keep other sessions' work intact. Commit coherent progress on the task branch and push before handoff. Preserve dirty changes rather than stashing, resetting or discarding shared work.

## Integrate the result

The target comes from `.agents/PROJECT.md` and AGENTS.md: the user's own repository normally targets `main`; external work uses the user's designated contribution branch. Airlock uses `megamen32-dev`.

The package's `config/workflow.json` sets `pr_stage: on|off`; `~/.config/lhc/workflow.json` can override it. With PR mode on, open/update the task PR and complete the permitted merge. With it off, use a repository-permitted direct route.

`lhc_worktree.py delivery --repo <task-worktree> --target <target>` checks clean task work, published HEAD and the matching PR when required. A moved target needs reconciliation and affected checks. Actual repository protection and approval requirements remain in force.

Complete the requested installation and client check as well as the merge. Record the integrated revision, installed artifact and observed result separately. Parallel sessions can integrate independently; only the live shared switch needs the release lease.

## Bugs

The plan's `bugs/*.json` records reproductions, impact and resolution. Use `bug_register`, `bug_get`, `bug_list`, `bug_update`, `bug_resolve` and `bug_check` through LhcPlan. Fix task-blocking defects and regressions from this change; keep unrelated findings as separate work. A fixed status needs real verification. Duplicate and false-positive resolutions keep their reason and history.

## Shared deployment

Use Agent Herder `project_release_lease` for the canonical project and actual owner `{hostId, harness, nativeSessionId}`. Acquire it with a built candidate, just before the live operation. `status` gives the current owner and `SendMessage` target.

Check the token/fence and expected live revision immediately before mutation. Preserve a newer release or peer repair. Hold the lease only for the deployment and client check, and release it in `finally`. Terminal stop/abort/error cleanup and TTL cover failures; an ordinary completed turn is not session termination.

A recovery operation uses the project's approved route and a target known to restore service. The lease prevents conflicting writes; it does not decide which release the user requested.

### Herder unavailable

The current fallback uses a Git ref changed atomically with `--force-with-lease`. Try the existing Herder calls with their 20-second timeout at 0, 30, 60 and 120 seconds; after three minutes without success the fallback is available.

```sh
python3 <LHC>/tools/lhc_worktree.py release-guard acquire --repo <wt> --project <p> --session <id> --candidate <sha> [--plan <plan-dir>]
python3 <LHC>/tools/lhc_worktree.py release-guard check --repo <wt> --project <p> --session <id> --candidate <sha> --live-rev <live> --expected-rev <live>
python3 <LHC>/tools/lhc_worktree.py release-guard release --repo <wt> --project <p> --session <id>
```

The ref is `refs/lhc/release/<project>` and expires after 15 minutes. Its record names the session, host and candidate. Renew with `acquire`; release through compare-and-swap. A live foreign ref requires coordination with its owner.

`check` requires a clean worktree, a candidate in `origin/main`, a live revision ancestral to the candidate, a newer candidate VERSION, and a matching expected revision. Acquisition and release record `herder-bypass` in the selected plan and dispatcher mail. Return to Herder for the next release once it answers.

## Existing work and cleanup

Use `lhc_worktree.py inventory` for Git facts and the native session registry for ownership. `lhc_orphan_work.py` can inspect dirty or untracked work before adoption. Preserve its exact diff and commit identity, contact an active owner, and review dependencies before integrating an abandoned change.

Clean merged, clean worktrees and branches after confirming their sessions are inactive. Unknown ownership is a question to resolve, not permission to remove work. Keep the primary checkout and target branch.
