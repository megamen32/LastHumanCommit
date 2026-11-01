# Worktrees, publication, PRs and project releases

## Start

Resolve the primary checkout with `git worktree list --porcelain`, not chat cwd.
Use one isolated task worktree and branch, even when no other session is visible.
Reuse the assigned worktree; otherwise use the existing helper:

```sh
python3 <LHC>/common/tools/lhc_worktree.py create --repo <project> --task <slug> --base <remote>/<target>
```

Fetch the intended target first. `target` comes from the primary checkout's
`.agents/PROJECT.md`; `AGENTS.md` Delivery handles ownership defaults. Never
adopt another task's uncommitted changes or reset the shared primary checkout.

## Publish and review

1. Commit coherent scoped steps and push the task branch. Branch publication is
   independent: nobody waits for other tasks to finish.
2. Open/update a draft PR into the permitted target, with the LHC plan link. Record owning session,
   worktree, branch, exact HEAD and PR URL in the task.
3. Run `lhc_worktree.py delivery --repo <task-worktree> --target <target>`.
   It reads the remote itself, not a stale tracking ref, and checks that the
   open PR names this exact HEAD and target. It performs no push/merge/deploy.
4. Reconcile a moved target in the task branch and rerun affected checks.
   Merge only through the PR and with the applicable owner/harness approval.
   Green checks do not approve a PR or authorize merge. Never direct-push main,
   force-push, weaken branch protections, or delete foreign work.
5. After an authorized merge, verify the integrated revision once. Keep source
   published, merged, installed and consumer-verified states separate.

A local worktree or unpushed commit is not durable publication. A pushed branch
is valid work in progress; an early draft PR is recommended for visibility of
unfinished work. Include the LHC plan link; confirm its intended audience and
access controls before adding private content. Mark ready only after implementation,
tests and review are complete. Draft publication is not merge readiness. A reviewed PR awaiting an actual approval is a precise blocker,
not a reason to discard the branch or pretend the change is installed.

## Shared runtime

Use Agent Herder `project_release_lease` with the canonical project `cwd` and
the actual owner `{hostId, harness, nativeSessionId}`. `status` reports the owner,
expiry, remaining seconds and the existing `SendMessage` target, never its token.

Acquire just before release, renew only while valid, and `check` the current
token/fence immediately before mutation. Re-read the live revision and use the
release entrypoint's expected-revision compare-and-swap. A changed revision or
expired/stale fence stops that candidate. Do not replace a newer deployment or
a peer's emergency fix with an older artifact, even if that artifact was green.

Release in `finally`. Terminal end/abort/error/stop hooks release ownership;
an ordinary completed turn does not. TTL handles a crash with no hook. Never
release a foreign lease; contact its session via the reported `SendMessage`
target. Separate projects do not share a global lock. A lease does not authorize
production or rollback. An authorized rollback must name and verify its target.

If this capability is unavailable in the installed Herder, park only release;
continue isolated implementation and PR publication. A file/chat claim is not
an equivalent fenced lease.

## Completion

Record branch/remote HEAD/PR, authorized integration revision, lease owner/fence
reference (never secret values), actual deployed revision and consumer proof.
On terminal session end, collect the read-only project inventory:
`lhc_worktree.py inventory --repo <project> --target <verified-target>`.
It reports Git facts, not session liveness or cleanup permission. Correlate paths
with Agent Herder's authoritative session registry; unknown ownership is not inactive.
The last active worker owns whole-project integration, verification and cleanup.
Account for every task branch, contact peers through SendMessage, and integrate
known reviewed changes through PRs under the applicable approval policy. Never
blindly merge unknown branches. A required approval or conflict remains a visible
blocker, not an excuse to discard work or claim completion.
Clean up only merged, clean, confirmed-inactive worktrees/branches after rechecking
their exact HEAD, target ancestry and session ownership under project coordination.
Preserve primary/target checkouts, active or locked worktrees, dirty/conflicted,
unmerged and unknown work. No force removal, reset, stash-all or branch -D.
If the last worker exits before integration completes, record the successor or
explicit pending integration blocker; session completion is not project completion. Never
report publication or a lease receipt as business acceptance.


## Existing work without an active owner

Do a bounded owner lookup using current session/declaration state, recent
coordination records and process evidence; record which sources were checked.
An unresponsive or ambiguous owner is not automatically inactive. If no active
owner is found, the current worker must adopt responsibility for finishing the
work instead of leaving a permanent "foreign work" blocker.

Inventory and preserve exact branch/commit identities and dirty diffs first.
Add the adoption, evidence, intended integration and acceptance checks to the
existing project plan. Inspect the full diff and its dependencies, review and
test it, then finish integration through the permitted PR/release path.
Do not blindly copy dirty files, reset another checkout, bulk-stash, discard
changes or silently claim the diff is trusted. Preserve original evidence and
recheck ownership before mutation; if an active owner appears, coordinate.

Ownership adoption is an obligation to investigate and finish, not automatic
acceptance or merge/deploy authorization. Conflicts, unsafe changes or required
approval remain explicit actionable blockers owned by the adopting worker.
Continue unblocked work, arrange the needed review/approval, and report the
precise remaining action rather than abandoning the branch. Clean up only under
the merged, clean, confirmed-inactive rules above, never from owner absence alone.
