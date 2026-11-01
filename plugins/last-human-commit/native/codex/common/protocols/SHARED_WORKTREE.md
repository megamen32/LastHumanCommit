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
2. Open/update a draft PR into the permitted target. Record owning session,
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

A local worktree, unpushed commit or pushed branch without a PR is unfinished
publication. A reviewed PR awaiting an actual approval is a precise blocker,
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
Remove only your own clean worktree after its commits are integrated. Never
report publication or a lease receipt as business acceptance.
