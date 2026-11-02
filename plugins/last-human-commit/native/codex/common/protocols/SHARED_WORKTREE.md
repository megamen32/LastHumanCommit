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

The package `config/workflow.json` sets `pr_stage` to `on` or
`off`; build with `python3 scripts/publish_package.py --pr-stage on|off`.
A user's existing LHC config directory `~/.config/lhc/workflow.json`
overrides the built value; otherwise missing configuration defaults to `on`.

1. Commit scoped changes in an isolated worktree and push the task branch.
   Other sessions do not need a PR before continuing their own branches.
2. When PR-on, open/update a draft PR into the permitted target with the LHC
   plan link. Record session, worktree, branch, HEAD and PR URL.
   When PR-off, do not demand or fabricate a PR. Record the same facts
   except URL, plus `pr_stage=off` and the exact intended merge target.
3. Run `lhc_worktree.py delivery --repo <task-worktree> --target <target>`.
   Both modes check clean isolated work and remote published HEAD. PR-on checks
   matching open PR; PR-off skips `gh pr` and PR URL. Neither mode merges
   or deploys. A green publication receipt is not proof of finished work.
4. Reconcile a moved target on the task branch and rerun affected tests.
   After independent review and checks, finish an authorized merge through
   the PR (on) or only through a host-permitted direct merge path (off).
   A host that requires a PR is an exact external gate: no rule bypass,
   force-push, access change or invented approval.
5. Verify integrated target SHA, build artifact, deployed revision and actual
   consumer result separately. PR-off never makes these optional.

A pushed task branch is valid work in progress; when PR-on, an early draft PR is recommended
for visibility. Include the plan link only when a PR is opened, after checking
its audience. Green checks do not authorize merge. A required approval or
branch-protection gate is a precise blocker, not a reason to delete work.

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

Record branch/remote HEAD, effective `pr_stage`, PR URL if on,
authorized integrated revision, lease owner/fence reference (never secret
values), deployed artifact/revision and consumer proof. Off requires all
fields except PR URL; it does **not** permit stopping after branch push.
On terminal session end, collect the read-only project inventory:
`lhc_worktree.py inventory --repo <project> --target <verified-target>`.
It reports Git facts, not session liveness or cleanup permission. Correlate
paths with Agent Herder's authoritative session registry.

The last active worker owns whole-project integration, verification and
cleanup. Account for every task branch, contact peers through SendMessage,
review/test known changes, then integrate them by the route permitted by
the active PR mode and host protections. Never blindly merge unknown branches.
A required approval or conflict remains an explicit blocker, never an excuse
to discard work or claim completion.

Clean only merged, clean, confirmed-inactive worktrees/branches after checking
the exact HEAD, target ancestry and session ownership. Preserve target,
primary and dirty or unknown work; no force removal, reset or bulk stash.

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
