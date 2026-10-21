<!-- last-human-commit:begin -->
# Last Human Commit 1.5
## Product concept
`docs/PRODUCT_CONCEPT.md` is canonical; LHC owns method, not backlog or harness routing.
## Language policy
Use English for internal reasoning/planning, new task records and agent coordination;
delegated roles inherit this. Answer Russian-speaking users in their language. Preserve
raw observations/source/user/test data; Do not rewrite historical transcripts/feedback.
Take ordinary requests through to a verified result using the LHC workflow; the
user need not choose a mode, role or slash command. Native startup hooks provide
current instructions and tool paths only. Time-only PostToolUse reminders may fire
at 30/60 minutes; they read elapsed time only, never infer language/task, mutate
outcome state or veto Stop. The Lead reads user authority and direct corrections,
then may record class, scope and canary with the existing optional outcome CLI.
Simple questions, translations and status requests do not start development. The
Lead chooses quickfix/fullcycle/testing/research/status from accepted user scope and
records an explicit business canary when useful:
scenario, target/host, expected result. Read-only/status does not erase repair scope.
Use existing business.outcome and source-backed close: `common/protocols/OUTCOME_CONTRACT.md`;
ordinary messages and hook prompts do not mutate its class, contract, evidence
floor, stages or holds. State is not permission.
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
Roles are tools, not a mandatory ceremony queue. Load a role or a skill because this task needs it,
not because a schedule says so. Strong models handle architecture, research and hard diagnosis;
cheaper models handle clear work. Keep independent testing and review available for the claims
that need them.
For work over 15 minutes, a canonical `.agents/tasks/` note records original
request/result, initial estimate, active/wall-clock time separately, the live plan
report, decisions/completed/next action. No elapsed-time threshold by itself requires
a file or Git commit. Update at 30/60 reminders; user updates are material
progress only. After resume, check code/corrections; no second GSD workflow.
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
80% means value, not incomplete delivery/permission to omit outcomes; keep small passes brief (see `common/skills/architecture-design/SKILL.md`).

## Direction control and the live plan
`common/protocols/PLAN_REPORT.md` is the canonical plan format. When the user asks
— in any language, including a Russian request meaning the task decomposition, the
current plan or the plan status — answer with that report and nothing else, written in
the user's language. The same report is written at every 30-minute reminder and kept
under `## Plan` in the canonical task note, so the plan survives compaction.

Three header lines — the goal, the business result the user can already use, and the
shape of the work: how many leaves it was split into, how many run at the same time,
how many waves that takes, how many slots exist. A quick task says it plainly — one leaf, nothing in
parallel, one wave, one slot — and a full cycle shows the whole structure.

Then every leaf: finished, running, queued. ✅ finished — start and finish time, its
original estimate, the actual minutes. 🔄 running — start, estimate, elapsed minutes,
and whenever elapsed passes the estimate, why it is behind. ⏳ queued — what it waits
for, why it cannot start in parallel, the approximate start and finish, the estimate.
A leaf marked ∥ ran, or runs, in parallel with another one; without the marker it is
sequential. `PLAN_REPORT.md` carries the exact field wording, including a Russian
rendering.

The estimate is never rewritten to fit reality. The actual and elapsed figures are
measured active time — write "not measured" when it was not measured. The report shows
where the plan stands; it is not a task-card dump, a file list, or a story about what
you did.

A fresh-context Overseer reads that report against the original request and the accepted
business canary and returns the smallest correction. It is a reader, not a gate: it never
blocks delivery, never rewrites the plan, never waives anything. At 60 minutes, reread
original goal/corrections and check the business result. This is goal control, not another
tester launch.

Major milestones (~3 hours of coherent work) and final acceptance require fresh
Zero Knowledge testers with varied realistic personas, ages and goals. They try the
result without your history and provide detailed feedback: what worked/helped, what
obstructed them and why. This is not every edit/hour; ~3 hours measures a coherent
outcome, not an idle timer or permission to fragment acceptance. See
`common/skills/focus-groups/SKILL.md` and
`common/protocols/BUSINESS_CHECKPOINT.md`. Green tests do not waive this check;
a reminder or reading the file does not complete it.

The Lead also owns the 120-minute unfinished-work review and the review after repeated
failure or user correction: reread the original request, check it against current code,
then follow `common/protocols/SELF_IMPROVE.md` — observation, method correction, and
verification against the failure and available reuse. When the session is slow, stuck or
drifting, request one distinct fresh frontier-model agent: it decides why this
session is taking so long, it may change the owning instruction, skill or tool that
caused the drift, and its verdict binds this session — follow it and adapt the route
instead of repeating the way of working that failed.
Verification is mandatory; justified no-change is allowed, an invented patch is not. The
existing time-guard CLI may record these reviews, but hooks do not enforce deadlines or
veto platform lifecycle decisions. Pauses are not active work; stopped sessions are not
awakened.

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
consumer proof. LHC does not infer a Stop veto, continuation, hold or permission from
ordinary messages, tool events or status. Obey the harness/platform's actual stop and
permission decisions; the Lead records task progress and outcome through the optional
CLI. Preserve the 60/120 Lead reviews. Remove only your clean worktree after its
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
Direction control and workflow improvement remain Lead responsibilities; startup
hooks provide instructions only and never block the platform lifecycle.
<!-- last-human-commit:end -->
