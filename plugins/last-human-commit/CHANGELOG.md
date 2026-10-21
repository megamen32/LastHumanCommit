# 1.5.17 — the owner's own review before a PR into a repository you do not own

A repository whose owner is not the requester will read the diff against the
rules of their own project, and they will read it once. That read now happens
before the PR exists: a fresh strong session plays that project's maintainer —
a senior engineer who has been in that codebase for years and loves it — reads
the project first (its instructions, conventions, tests, CI, CODEOWNERS and the
history of the touched areas) and then the diff, and returns a mountain of
specific findings instead of a verdict. The author fixes or answers every
supported finding and reviews the changed diff again; only a clean or
explicitly answered review lets the PR open. A dirty PR that reaches the owner
costs more than a later one.

New skill `maintainer-review` and new role `Maintainer`. The rule is wired into
REVIEW_TO_DELIVERY.md, Lead.md, the router and PRODUCT-PHILOSOPHY.md, and
registered in the adapter manifest, the skill catalog and the package
validator. Our own repositories do not need it.

# 1.5.16 — the live plan report and a plan-reading Overseer

Add the canonical live plan report. It answers the user's "декомпозиция задач" / "какой
план" request in the user's language and is written at every 30-minute boundary, so the
plan stays in the model's head and survives compaction. Format: the goal, the business
result, the decomposition shape (leaves, parallel count, waves, slots), then every leaf as
finished (✅), running (🔄) or queued (⏳) with its start/finish, original estimate, actual
minutes, the reason it is behind and why a queued leaf cannot start in parallel.

Overseer becomes the reader of that report: every 30 minutes it compares the plan against
the original request and the accepted business canary and returns the smallest
correction. It is a reader, not a gate — it never blocks delivery, rewrites the plan or
waives anything.

The 120-minute learning checkpoint was dead on 1.5.15: removing the conversation-driven
hooks took the whole stateful path of lhc_entry.py with them, so the checkpoint, the
hourly business review, the Stop gate, the milestone gate and the outcome state all
stopped running. The checkpoint now lives in the time-only heartbeat and asks for a
frontier-model agent that may change the owning instruction, skill or tool; its verdict
binds the session.

Finish the cleanup 1.5.15 left half-done: the validator required the removed
UserPromptSubmit/Stop hooks, and the test suite required the phrase "Overseer is the
supreme route controller" that the roles had already forbidden. Both now assert the
current contract.

Ship PRODUCT-PHILOSOPHY.md: the whole pipeline from the user's request to the merged
change — cheap research subagents, the three work modes, plan-before-work, the 2-3
options with pros and cons, the critique, the ideal super-ultra plan, dropping everything
that does not pay for itself, the 20/80 cut, decomposition into leaves of at most 20
minutes, parallelization, the Gantt-style estimate, execution, a real deploy, hands-on
zero-knowledge testers inside the blast radius, and push, PR and merge into
megamen32-dev. It lists what the philosophy excludes, maps every stage to its
implementation, and records the seven known gaps.

# 1.5.15 — remove conversation-driven control hooks

Remove automatic conversation-driven prompt/tool/Stop lifecycle hooks. Startup
and context restoration load instructions; a time-only heartbeat retains 30-minute
planning and hourly original-goal reminders without semantic state inference. Ordinary text cannot
reclassify tasks, reset evidence, resume holds, or trigger a completion veto.
Explicit CLI evidence checks and native harness permissions/stops remain available;
existing pending outcomes are preserved, not silently accepted.

# 1.5.13 — preserve task and evidence identity

Keep agent relays, status and duplicates separate from the active task and stop
controls. Bind native subagent identities to actual parent dispatch receipts;
future captured assignments remain distinct from human authority. Match independent
reviews to a stable current subject and preserve unaffected accepted stage proofs.
Keep real candidate changes, later negative findings and permission gates effective.
Address command failures to their actual native session and state root; keep
unchanged hook context quiet and preserve accepted checks on repeated contracts.
Bind project identity and existing main permission separately, and recognize the
native plugin manager's exact installation readback.
Installed ordinary-task acceptance is reported separately from source validation.

# 1.5.12 — verify source-only publication

Add explicit source-publication verification for native assignments that deliver reviewed source artifacts. Independent source readiness uses the exact owned candidate files; Git publication requires the configured repository, branch, commit and owned content readbacks. Runtime checks remain unchanged for application work. Source readiness does not claim publication, runtime acceptance or permission.

# 1.5.11 — bind reviews across native project directories

Allow an independent engineering reviewer in a different native directory to bind the currently assigned product when the publisher works directly in that product. Require the exact current outcome, full goal, assigned product root and actual product-bound observations. Preserve native directories, evidence times, revisions and independent-review gates.

# 1.5.10 — preserve exact reviewer assignment lineage

Keep native reviewers bound to the exact outcome ID and full goal in their current task assignment. A genuine reassignment uses a new native worker session under the existing mandate and a fresh review assignment; old reports stay historical and cannot be remapped. This source-only route does not replay product/provider/deploy work or accept historical H32/C2.

Recognize Agent Herder `new_or_resume` and `deliver` relays through an explicit `agent-relay` prolog and unwrap it only for LHC task scope. Unmarked origin remains `unknown`; the marker records transport provenance, not human identity or authorization. Delegated initial tasks continue through the existing mandate and permission gates.

# 1.5.9 — bind independent review to its assignment

The native independent-review export route extends only when exact assignment gates remain. Resolve owned source, revision and Git remote against the explicitly assigned product root while keeping native session identity/state at its original root; report missing session state with an actionable error. Preserve actual external-tool working-directory, ownership, and provenance gates. This release does not synthesize historical evidence or imply C2 PASS.

# 1.5.8 — preserve the independent assessment

Independent engineering review selects the original assessment over later bookkeeping. Preserve its original timestamp, source-call cutoff, and negative findings. Recognize the documented
`env -u AGENT_BROWSER_AUTO_CONNECT agent-browser` launch prefix without accepting
arbitrary environment wrappers.

# 1.5.7 — quiet, accurate completion hooks

Limit overdue Stop reminders to one per unchanged obligation and progress; name the
actual due checkpoint, and avoid treating Russian "установить факт" resolution
questions as software installation. Run the independent Overseer only on a concrete
anomaly with bounded, read-only session evidence.

# 1.5.6 — hook feedback and task-scope continuity

Prevent repeated unchanged reminders and keep coordination metadata out of task
scope. Preserve long task prompts in hourly reminders and recognize bounded
expectation corrections without treating status feedback as a task change.

# 1.5.5 — installed test-skill protocol pointers

Correct the two testing skills to resolve the execution-access protocol from the
active package root. Regression checks all four installed root/native skill paths.
Policy semantics and the accepted 1.5.2 executable runtime are unchanged.

# 1.5.4 — authorized local test access

Before implementation or acceptance, resolve the primary checkout's TEST_ACCESS.md
registry. Reuse and recover explicitly authorized local test identities with existing
protected references and supported app-native administration, including scoped sudo,
initial password change and bounded disposable OAuth registration. Preserve secret
values outside prompts/logs; update the same protected reference atomically and keep
entry/access scope current after resume. External/revoked operations remain blocked.
This instruction release uses the accepted 1.5.2 executable runtime unchanged.
Private 1.5.3 runtime experiments remain deferred, preserved in source history;
this version does not claim their OpenCode or ZCode native acceptance.

# 1.5.2 — bounded research and planning scope

An explicit sentence-level RESEARCH ONLY assignment header takes precedence over
engineering terms in its subject. Later research does not erase an existing repair.
One whole-prompt native quote envelope is interpreted without rewriting raw input.
Automatic context clarifies describe-only behavior when execution/tools are forbidden.
OpenCode reapplies canonical operating instructions to each rebuilt model context.
Research reminders prioritize the assigned finding/report over close-helper investigation.
Research project canaries bind a direct cat read to one explicitly named in-project source file.
Planning-only replies explicitly retain the research/council sequence.
Outer compound commands are rejected before unwrapping a known simple shell command.
Permission, lifecycle and human-stop gates remain; native source evidence is required. Native planning route
selection and global activation remain separate acceptance claims.

# 1.5.1 — grouped delivery prohibitions

A direct operation list such as "No deploy, push, or merge" excludes each named
stage. Clause boundaries preserve separately requested publication/integration.
No permission, evidence, independent acceptance or human-stop gate changes.
Native candidate acceptance and activation remain separate release gates.

# 1.5.0 — outcome contract candidate

Explicit task class/canary, ordered applicable stages, source-backed positive close
and progress-bound continuation in existing state. Testing coverage is a result;
bound question delivery and canonical answers remain distinct. One quota skill
serves council/model routing/focus groups; candid no-defect feedback is accepted.
Native candidate acceptance and installation are separate release gates.

# 1.4.13 — mixed-scope read-only classification

- Scoped, quoted or negated "only review/check" text no longer marks an entire
  task read-only; direct task-wide review-only instructions remain read-only.
- This affects milestone obligation classification only and grants no operation
  permissions or overrides to native harness policy.

# 1.4.12 — scoped delivery and native action evidence

- Keep private access failures scoped to the observed target and operation;
  preserve native PermissionRequest, transport failure and human-stop holds.
- Preserve direct user scope through rehydrate without turning prompt text into
  plugin-created permissions.
- Separate direction decisions, relevant native action results, deployment and
  consumer acceptance; unrelated tool output does not complete a chosen action.
- Retain running process IDs and terminal results without blocking independent
  work or duplicating a live build. Partial demo success leaves excluded work
  pending.

## 1.5.14

- Reject missing assigned testing coverage before confirming the contract or running the consumer check; preserve prior state on rejection.
- Report a missing current assessment directly instead of mistaking the session start timestamp for a stale review.

## 1.4.8 — existing Herder model selection in OpenCode

The standard native LHC entry now routes multi-model delegation to the already
connected Agent Herder MCP with an explicit model and independent role/context.
Updated model-routing skill documents the five existing user routes, retry/Stop
semantics and fresh blind milestone testing. No tool, wrapper, supervisor or
role-by-model profile matrix added. OpenChamber Auto remains a per-message
classifier and is not assumed to route child jobs or enforce LHC acceptance.

## 1.4.7 — native OpenCode business contract and review-to-delivery

- OpenCode V2 calls the canonical Python native LHC entry for the real prompt, model context and tool/idle lifecycle, matching Codex 1.4.6. No extra reviewer, daemon, or copied stale TS policy.
- Native compaction and the first subsequent context restore original goal, latest direct correction and current control from persisted session state; unrelated task cards cannot replace them.
- OpenCode global installation has no stale pinned cache version; all hourly/120-minute/major-milestone rules and honest no-PASS acceptance remain.
- Runtime validation includes a fresh OpenCode 2 session and real review-to-delivery behavior; the OpenChamber integration uses the same backend.

## 1.4.6 — 2026-10-17

Route completed review to authorized delivery, not receipt-review loops. Native
entry, Lead, Reviewer and hourly review distinguish material changes, metadata-only
corrections and unknown coverage. Reuse native review/CI results; machine-fill
existing metadata instead of writing duplicate JSON with LLMs. Preserve real tests,
release/resource/approval gates, timed checks and milestone Zero Knowledge feedback.
No new service, model timer, receipt format or production changes.

## 1.4.5 — 2026-10-17

Repair Codex automatic lifecycle delivery: direct business/three-pass/TDD context,
lazy entry for existing threads, compaction rehydration and continuous clock,
bounded overdue Stop continuation, exact identity with large native inputs, and
no separate pinned cache version in Codex bootstrap. Human Stop and permission
boundaries remain intact; old timers and milestone scope are unchanged.

## 1.4.4 — OpenCode 2 compatibility

Native V2 hook registration and session-bound clock; V1 entrypoint retained.
Business rules unchanged from 1.4.3.

## 1.4.3 — 2026-10-17

Tangible user outcome before code; immediate bug TDD. Hourly direction review
remains mandatory but no longer requires blind testing. Fresh varied Zero Knowledge
personas with detailed positive/negative feedback accept major outcome milestones
(roughly 3 hours), not each hour or edit. Legacy optional reviewer evidence is kept
without treating it as milestone acceptance. Three-pass planning and 120-minute
workflow improvement remain unchanged.

## 1.4.2 — 2026-10-17

Restore compulsory hourly original-goal/Zero Knowledge review and 120-minute
workflow improvement. Reconnect native hooks by default, retain source intent
across compaction, pause observed idle intervals, and require actual review
records rather than treating reminders as completion. Keep the restored 1.4.1
solution → ideal → 80%-value planning and 1.4.0 worktree/chat/PR features.

## 1.4.1 — 2026-10-17

Restore the useful design sequence: working solution -> ideal version -> 80%-value
MVP. Apply it in the default router, Lead, architecture/planning skills and Full
cycle template. This was mistakenly conflated with a mandatory three-line form.
Keep the default lightweight: one design, not three reports, builds or approvals.
The retained value is an orientation, not a claim of measured 80% or permission to
omit mandatory outcomes. Existing worktree/chat/PR behavior is unchanged.

## 1.4.0 — 2026-10-17

Automatic ordinary-language entry; isolated parallel work; PR/merge and final shared
green history; independent work before waits. Atomic file-per-message project/system
chat. Agent Herder `resume_after` protocol. Timer/learning observers opt-in rather
than default. Native-instruction bootstrap preserves unrelated rules. Intentional
policy checks migrated; existing behavioral/tool regressions retained.

# Changelog

## 1.3.0 - 2026-09-10

- Added the standing "Dead remnants finish in-cycle" router rule: units,
  timers, credentials, hooks, scripts, and stale doc warnings made dead by a
  change are removed or re-pointed in the same cycle once the replacement's
  canary is green; blockers must be named, not left silently.

## 0.3.0 - 2026-08-12

- Added dedicated Worker research, code, and bugfix skills.
- Added a bounded project-local code map so verified production paths,
  ownership, configuration, and recurring failure shields can be reused.
- Made `rg` the default fresh source locator, with Graphify limited to
  multi-hop orientation and context-mode to large-output processing.

## 0.2.1 - 2026-08-12

- Preserve a full prompt-based compaction handoff when a least-cost direct task
  intentionally has no task-card.

## 0.2.0 - 2026-08-12

- Added bounded compaction handoff/count hooks for Codex and OpenCode.
- Added task decomposition and two-route YAGNI planning contracts.
- Made timing/status answers name their measurement source instead of inferring
  unknown active time.

## 0.1.0 - 2026-08-10

- Added portable planning, implementation, bugfix, delivery, testing, and
  release skills.
- Added native Codex and Claude Code manifests plus an OpenCode config helper.
- Added dependency-free synchronization, parity, manifest, and loader checks.
- Confirmed that no MCP server is bundled.
# 1.4.11 — ZCode native lifecycle

- Add native ZCode plugin discovery and its failure-tool event adapter.
- Keep the ordinary engineering prompt, 60-minute direction review,
  120-minute learning checkpoint, independent milestone acceptance, and bounded
  Stop continuation on the native event path.
