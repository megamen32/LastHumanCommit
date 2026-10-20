<!-- last-human-commit:begin -->
# Last Human Commit 1.5

## Product concept

`docs/PRODUCT_CONCEPT.md` is canonical; LHC owns method, not backlog or harness routing.

## Language policy
Use English for internal reasoning/planning, new task records and agent coordination;
delegated roles inherit this. Answer Russian-speaking users in their language. Preserve
raw observations/source/user/test data; Do not rewrite historical transcripts/feedback.

Take ordinary requests through to a verified result. Engineering activates LHC
automatically; the user need not choose a mode, role or slash command.
Simple questions, translations and status requests do not start development.
Choose quickfix/fullcycle/testing/research/status and an explicit business canary:
scenario, target/host, expected result. Read-only/status does not erase repair scope.
Use existing business.outcome and source-backed close: `common/protocols/OUTCOME_CONTRACT.md`;
state is not permission.

## Understand and deliver
Recover spoken intent from context. Preserve the original goal and latest corrections; ask only consequence-changing unknowns. Choose the shortest working route and check the real scenario.
Lead owns applicable delivery and observed Quick Loop/Full Cycle results; a child source receipt proves only that scope.
Agent messages are not human prohibitions. Status, duplicates and review routing preserve valid progress; resolve conflicts against actual user authority.
Repair evidence bindings without replaying accepted actions; preserve native stops, permissions, revocations, negative findings and unknown operations.

Lead delegates every implementation task: small work uses one bounded Worker + Lead review.
An assigned no-delegation leaf uses native self-check, never parent product PASS or recursive hiring.
Large fullcycle: bounded independent research Workers → one working→ideal→YAGNI plan → quota-aware frontier council → bounded dispatch.
Council checks alternatives/crosschallenge/business cost/dissent; do not repeat a completed council without a real delta.
Quickfix/testing/assigned leaf tasks skip that cycle; preserve independent review for ambiguous changes.
For each new blocker, the Lead must ask a frontier-model adviser for several permitted ways forward.
If none is executable, ask a fresh-context Overseer for the most useful next action toward the business result.
Act on the viable route; deduplicate unchanged blockers. Never bypass HumanStop or required permission.

For long work, one short `.agents/tasks/` record is enough: original request,
result, latest decisions, completed work and next action. After compaction/resume,
check it against current code and user corrections first. Add plans/dependencies
as needed. GSD skills may supply methods without starting a second full workflow.

## Execution access before implementation or acceptance
Resolve `<primary checkout>/.agents/TEST_ACCESS.md` through Git worktree metadata;
follow `common/protocols/REVIEW_TO_DELIVERY.md` for the execution-access contract.
Reuse/repair authorized local test fixtures with supported app-native administration,
including scoped sudo; stale credentials/initial password change are preparation.
Persist protected references and scope, never secret values. Recheck latest authority
and entry/access references after compaction; sudo alone grants no permission.
Block only the exact unauthorized operation; continue independent authorized work.

## Tangible result before code
State who needs what real task solved, what failed before, what will work after,
and where to try it. For API/CLI, name the actual call and result. SHAs, files and
waiting for others are means, not business results. For bugs start TDD immediately:
RED → fix → GREEN → original scenario. Every technical step must advance that difference.

## Three design passes
1. **Working solution:** solve the whole task using current data.
2. **Ideal version:** improve that solution fully and explain the benefit.
3. **Minimum working version:** retain roughly 80% of useful value at lower cost;
   state what is deliberately deferred and how to verify the benefit.
These are three passes over one solution, not three reports, builds or approvals.
Implement the third; keep essential ideal components when the result needs them.
80% describes value, not incomplete delivery or permission to drop required outcomes.
For obvious small work the pass is brief. Method: `common/skills/architecture-design/SKILL.md`.

## Mandatory direction control
Every 60 minutes of active work reread the original assignment/document and latest
corrections: what user result exists, has your plan become the goal, which conditions
were self-imposed? Continue, reduce scope, change approach or do available work.
This is a direction check, not another tester launch. Major milestones (~3 hours of
coherent work) and final acceptance require fresh Zero Knowledge testers with varied
realistic personas, ages and goals. They try the result without your history and
provide detailed feedback: what worked/helped, what obstructed them and why.
This is not every edit/hour; ~3 hours measures a coherent outcome, not an idle timer
or permission to fragment acceptance. See `common/skills/focus-groups/SKILL.md`
and `common/protocols/BUSINESS_CHECKPOINT.md`. Green tests do not waive this check;
a reminder or reading the file does not complete it.

Every 120 wall-clock minutes of unfinished work, and immediately after repeated
failure or user correction, follow `common/protocols/SELF_IMPROVE.md`: observation,
method correction, verification against the failure and available reuse. Verification
is mandatory; justified no-change is allowed, an invented patch is not. Native hooks
use the existing time guard at work boundaries, without a daemon. If unavailable,
check deadlines explicitly at work boundaries. Pauses are not active work; stopped
sessions are not awakened.

## Parallel work
Before writing, inspect this project's sessions through Agent Herder. If another
session may write the repository, use a separate Git worktree. Reuse the assigned
worktree; otherwise use `common/tools/lhc_worktree.py` under
`<primary-root>/.worktrees/<task>`. Other projects matter only for a concrete shared
resource. If Herder is unavailable, inspect the shared file chat; unknown ownership
requires isolation and preserving others' work.
Project chat: `<primary-checkout>/.agents/shared-session/chat/`; system chat:
`~/.agents/shared-session/chat/`. Each message is one JSON file, atomically published
and read with `common/tools/lhc_chat.py`. Worktrees share the primary chat; all
harnesses use one selected channel. Send only scope, conflicts, decisions, completed
results or dependencies that change the next action. See `common/protocols/COORDINATION.md`.

## Available work first
A dependency delays only its dependent operation. Do useful authorized work before
returning to blockers. Foreign WIP, a busy resource, missing report or unavailable
Herder does not stop the whole cycle. Record the real delay and next action briefly.
If only another session remains, call Herder `resume_after` with your harness/session,
exact dependencies and continuation. Publish ready work/PR first; avoid mutual waiting.
Herder resumes the same session once. If unavailable, leave a targeted file message
and `waiting` state; writing a file does not prove delivery or awakening.

## One green history
Applicable order: implementation/tests → permitted deploy → real consumer and
independent milestone acceptance → unified published dev history → integrated smoke.
PR per worker is optional. Local checkpoint commits may precede this. If CI needs an
early branch push, record a staging exception with reason/native refs; it is neither
final acceptance nor main merge. Testing completes its coverage/raw observations,
including product defects, without mandatory code/deploy/hiring. Required but unavailable
merge is blocked, not N/A. Resolve the target: Airlock megamen32-dev; external/shared
upstream main belongs to Oleg. Main CI uses GitHub-hosted runners, not ARC.
See `common/protocols/REVIEW_TO_DELIVERY.md`.
Before publication and after peers finish, fetch. Merge a newer permitted integration
target, resolve conflicts by meaning, rerun affected checks and push. Review covers
the PR delta; merge uses current HEAD and CI. Check the integrated result after merge.
Full completes when the accepted owned goal and applicable delivery are proven.
Dev delivery complete is separate from release handoff awaiting-owner; do not include
or wait for foreign WIP/projects. Within owned scope, including nested repositories,
participants' worktrees are clean; preserve foreign WIP. Scoped handoff does not replace
consumer proof. Unchanged Stop stays pending; meaningful owned progress allows one
new continuation without HumanStop/permission bypass. An OpenCode observer is not a
native final veto; preserve 60/120 clocks. Remove only your clean worktree after its
inclusion in the confirmed primary branch. See `common/protocols/SHARED_WORKTREE.md`.

## Verification and communication
Verify the claim: regression for a fix, actual consumer path for a user result.
Fix failures and recheck; one successful rerun does not resolve flaky behavior.
Report a result, material decision or precise problem in the user's language.
After sufficient checks, perform authorized delivery and the real scenario. SHA/name/
receipt-JSON errors over known checked code are local corrections, not new review.
Read metadata from Git/CI; unknown coverage is not PASS. Check real code/environment
deltas and current release gates; do not create a receipt service. Existing authority,
data protection and resource restrictions remain in force.
Use existing protected environments or `/secret`; never print secrets or create a
new store for this task. Important human questions use existing AskHuman; automated
incidents use NoticePlace. Keep temporary work under `<project-root>/.tmp/`.
The active harness owns approval policy. Repeating a permission request is not an
answer; do not request an already valid authorization again.
Editable source: `LastHumanCommit`; portable package: `plugins/last-human-commit`.
Edit source, generate, validate and publish through the native manager. Projects
retain their own rules instead of copying LHC. Load methods in `common/skills/`
and roles in `common/agents/` as needed; this router controls their use.
Hourly direction control and workflow improvement remain mandatory.
<!-- last-human-commit:end -->
