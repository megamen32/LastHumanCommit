# Worktrees, PRs and one history

## Start

Identify the primary checkout from Git (`git worktree list --porcelain`), not chat
cwd. Through Herder inspect sessions of this repository, including its worktrees.
With another potential writer use a separate worktree. Reuse the assigned one;
otherwise:

```sh
python3 <LHC>/common/tools/lhc_worktree.py create --repo <project> --task <slug> --base <resolved-remote>/<permitted-integration-branch>
```

Branch `lhc/<slug>`, path `<primary-root>/.worktrees/<slug>`. If Herder is unavailable,
check file chat/current tree. Unknown ownership calls for isolation, not stopping
all work or taking others' changes. A sole session may stay in the primary checkout.
If a writer arrives later, move only your separable work into a worktree and resolve
any actual collision with the owner.

## During work

Declare ownership once in English. Commit coherent ready steps. Inspect peer changes
when they affect your code, not before every action. Chat/runtime data do not replace
source and need no separate commits. All worktrees use the primary checkout chat.
A conflict blocks its own operation. Do available research/code/checks immediately
and return afterward. Foreign WIP stays with its owner; file age or a missing session
list entry does not transfer ownership.

## Unified published dev history

Before push resolve ownership and explicit integration target, fetch and compare that
branch. Merge it into your working branch, resolve conflicts, run affected checks and
scoped push. PR per worker is optional; one integrator converges ready commits into
published dev history. Airlock: branch from/integrate into megamen32-dev; upstream
main belongs to Oleg. External/shared main is never auto-merged; unknown target is
not main. Main CI is GitHub-hosted, not ARC/K3s. Do not change GitHub App privileges,
checks or protection. Final main PR is only an agreed handoff.
Review covers its checked delta; CI covers the actual published version. A SHA change
alone needs no repeated LLM review. Compare actual changes/dependencies once; verify
material differences, correct receipt errors locally. Existing publication/integration
checks remain (REVIEW_TO_DELIVERY.md). With permission and green checks merge the PR;
otherwise preserve the exact reason and continue available work. Use native Git and
`gh`/provider PR tools, not another Git manager.
If push rejects new commits, continue the task: fetch, merge, verify, push again.
No force-push or deleting foreign code. After integration check the combined permitted
dev branch; repair integration failures with a new checked change preserving history.
A sole primary-checkout session also compares remote, integrates new work, verifies
and pushes. Publish through a PR when applicable; lacking a worktree does not waive
outcome requirements.

## Full completion

Converge into one reachable published history and green integrated result. Account
for changes in this cycle, including ready peer work, generated files and nested
repositories. Publish nested commits before their pointer. Your clean branch alone
does not prove integration.
Active owners finish their parts. The integrator or last active session performs
final fetch, incorporation, combined checks, push and real user scenario. Publish
ready parts before waiting to avoid mutual dependency loops. Record `resume_after`
for remaining dependencies; exhaust useful independent work first.
Full completes after relevant PRs/commits converge, participant trees are clean and
the result is green. A future unrelated project does not expand this cycle. For a
real external blocker preserve the PR and required action; do not call partial
publication Full completion. Remove only your own clean inactive worktrees/branches
after confirmed inclusion in remote main. Preserve foreign WIP, unmerged branches
and original work.
