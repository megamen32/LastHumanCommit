# Worktrees, PRs and merging

## Start

Find the primary checkout with `git worktree list --porcelain`, not the chat cwd.
Check this repository's live sessions in Agent Herder. If another session may
write, use a worktree; reuse an assigned one, otherwise:

```sh
python3 <LHC>/common/tools/lhc_worktree.py create --repo <project> --task <slug> --base <remote>/<target-branch>
```

Branch `lhc/<slug>`, path `<primary-root>/.worktrees/<slug>`. `<target-branch>`
is `target` from `<primary checkout>/.agents/PROJECT.md`; without it, `AGENTS.md`
Delivery decides: `main` in the owner's repository, the owner's own branch
(e.g. `megamen32-dev`) in someone else's. A sole session may stay in the
primary checkout. Unknown ownership of files means isolation, not a full stop.

## During work

Announce ownership once in the project chat. Commit coherent steps. A conflict
blocks only its own operation; do the rest first. Foreign WIP stays with its
owner; file age or a missing session does not transfer ownership.

## Integration

1. Fetch the target branch, merge it into your branch, resolve conflicts by
   meaning, rerun affected checks.
2. Push and open the PR into the target branch. Inside one task the Lead merges
   its Workers' leaf branches into the task branch; between tasks there is no
   integrator: each session merges its own PR.
3. Mergeable and green: merge. Target moved or push rejected: fetch, merge,
   verify, push again. The later session reconciles; nobody waits.
   Never force-push or delete foreign code.
4. Check the combined target branch once after merge; repair failures with a new
   checked change.
5. Deploy dev from the target after your merge, holding the project deploy lock
   only for the deploy and its test.

Never push, merge or open a PR into the `main` of a repository the owner does not
own. Do not change GitHub App privileges, required checks or branch protection.
Use native Git and `gh`.

## Completion

Done when this task's changes, including nested repositories (publish nested
commits before their pointer), are merged into the target branch and the
combined result is green. Other sessions' unfinished work is not part of your
completion; never wait for it. Record `resume_after` only for a real dependency
on a peer's result. Remove only your own clean worktrees after their commits are
on the target branch.
