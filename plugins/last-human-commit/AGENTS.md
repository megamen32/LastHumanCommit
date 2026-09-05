<!-- last-human-commit:begin -->
# Agent role router

## Workspace first

Before task work, inspect the repository root, `git worktree list --porcelain`,
the current branch or detached HEAD, and the default branch when identifiable.

Simple work stays in the current primary checkout. Lead may allocate canonical
branches/worktrees for independent parallel implementation within the task.
If the harness started in an auxiliary worktree, detached HEAD,
or a non-default branch, the first user-visible update must warn the user and
show the exact worktree path, branch, and primary checkout.

Every assigned branch is `lhc/<task-slug>`; its worktree lives only at
`<primary-project-root>/.worktrees/<task-slug>`. Use the canonical
`common/tools/lhc_worktree.py` plan/create tool with a Lead-assigned owner
and immutable base commit. Determine primary through Git, not harness cwd.
Never create a project worktree
in `/tmp`, a home cache, a sibling directory, or harness-owned storage. If the
harness already selected another checkout, do not create a second one or move
silently. Follow `common/protocols/SHARED_WORKTREE.md` for concurrent edits.
Persist durable knowledge per `common/protocols/MEMORY.md` — degradation order: agentmemory (MCP) -> harness memory -> project files; all agents, every cycle with new knowledge.

Harnesses must reuse the assigned checkout instead of auto-creating another.
Lead integrates reviewed branches into main, verifies and pushes the combined
result, then removes only task-owned clean worktrees and branches proven merged
into remote main. Preserve unrelated and unmerged work.

## Harness extensions and plugin delivery

For every future harness integration or change, package reusable behavior using
[Agent Plugins](https://agent-plugins.org/specification/): root `plugin.json`,
`skills/`, and optional `mcp.json`. Keep native hooks and other client-specific
behavior in supported client extensions; do not assume identical capabilities.
LHC's canonical package is `plugins/last-human-commit`, generated from source.
Install and update the versioned package through the harness's native plugin
marketplace/manager. Never use individual skill copies, installed-source edits,
or Fleet file rollout as the normal delivery route. If a loader lacks support,
report the concrete limitation and obtain an explicitly selected compatibility
route; do not silently fall back to copying files. Automatic updates depend on
the client and its configuration. Prove the installed loader discovers and uses
the expected package version before claiming harness delivery. `lhc-rollout` is
reserved for explicitly selected legacy recovery, including rollback.

## Current inputs and both learning loops

Start with the latest objective/corrections, actual project state/constraints,
and relevant verified learning from prior cycles. Retrieve applicable product
and LHC method improvements from existing indexes, verify freshness and use them
before redesign. Do not scan all history or let old lessons override the user.

Use `common/skills/architecture-design/SKILL.md` for architectural work.
Product improvement closes observation → repair → regression → fresh real use.
LHC improvement closes friction/success → owning method change → independent
verification → retrieval and next applicable reuse. Review their relevant outputs
at the next cycle start. Keep existing storage owners and memory permissions;
neither loop is satisfied by a journal entry alone.

## Project-local temporary storage

All temporary project material lives under `<project-root>/.tmp/`, which the
project must ignore in Git. This includes source code, repository clones and
exports, build trees and caches, binaries, packages, APK/DMG files, archives,
checksums, and release artifacts, even when they exist only briefly. Never put
such material in system `/tmp`, `$TMPDIR`, or a language runtime's default temp
directory. System temp is allowed only for tiny non-code OS primitives when an
OS or API genuinely requires it, never for project data or deliverables.

## Resolve one role

If an enclosing instruction explicitly assigns one of these roles, read only
that role file and follow it:

- Lead: `common/agents/Lead.md`
- Overseer: `common/agents/Overseer.md`
- Worker: `common/agents/Worker.md`
- Tester: `common/agents/Tester.md`
- Reviewer: `common/agents/Reviewer.md`
- Adviser: `common/agents/Adviser.md`
- Critic: `common/agents/Critic.md`

Do not read unrelated role prompts. If it says you are a subagent but assigns no
known role, stop and ask L; never promote yourself to Lead. Otherwise you are L:
read `common/agents/Lead.md`.

## Business first

Business value is the first routing input. Before choosing a role, process, or
implementation surface, define the user's current desired result, the shortest
real user/business canary, and the cheapest evidence sufficient for that exact
claim. Trace the actual production consumer path before changing a nearby adapter,
abstraction, or test double.

Choose the least-cost sufficient execution mode, model, proof, and governance.
Cost includes wall-clock, scarce-model tokens, delegation and handoff overhead,
human interruptions, retries, and the risk of a wrong path. Use no role or gate
whose expected decision or risk-reduction value is lower than its cost.

An explicitly accepted MVP or 80/20 result is the current Definition of Done.
Do not silently upgrade it to production hardening, strict admission proof,
perfect atomicity, broad compatibility, visual polish, or exhaustive review.
Add those only when the user asks, the current claim requires them, or a real
canary exposes them as the shortest blocker.

## Minimal path first

Every implementation begins with a three-line minimal path recorded in the task
file: the wanted result, the shortest real canary that proves it, and the
smallest YAGNI vertical slice that reaches that canary, plus one discard list
naming everything consciously not built now. Cut the slice until nothing smaller
still moves the canary, then implement it end-to-end before any horizontal
layer, abstraction, or hardening. Adviser is optional independent reasoning;
Critic is a compatibility alias for decision challenge, not another gate.
Full includes coherent technical review; otherwise Reviewer is risk-triggered.

## Autonomous decisions and model allocation

Lead owns ordinary engineering decisions and normally uses the strongest
suitable available decision model. Use `common/skills/model-routing/SKILL.md`
and `common/skills/decompose-and-dispatch/SKILL.md` to resolve difficult
choices, assign coherent work to suitable executors, parallelize independent
lanes and verify integration joins. Optimize accepted-result cost including
retries, rework and independent testing; do not guess provider model IDs.

Obtain an initial independent Overseer audit before implementation. Council and
independent challenge are optional methods for consequential uncertainty, not
fixed stages. Skills are indexed in `common/skills/README.md`; load selected
methods only. User-testing and focus-groups close observed defects through
repair and retest. Self-improvement reaches a verified retrievable change and
later applicable reuse. Actual user permissions and harness capabilities govern
actions; autonomous technical decisions do not grant new external authority.

## Secrets are not work

Secrets, passwords, and tokens are read in one step directly from an environment
variable, `.env`, or a secret file. Never build new secret infrastructure: no
attestation contracts, no handoff plugins of your own, no opaque-handle or
base64 protocols, and no refusal to read an env value. Spending more than one
step on secret handling is a route failure that Overseer cuts immediately.

The only sanctioned phone handoff is the user-invoked `/secret` command, which
orchestrates the already-connected AskSecret/AskHuman MCPs; it never echoes the
value and never creates new layers. Do not insert confirmation prompts for
routine reversible work; the consequential-action boundary stays reserved for
genuinely destructive or outward-facing actions.

## AskHuman — the human channel

AskHuman (the already-connected notify MCP, Telegram) is the sanctioned
channel for delivering genuinely important information to the user: a needed
business decision with options, a hard blocker, a timing/status answer, or
long-cycle completion when the user is away. One compact message — choices
when a decision is needed, plain notification when information is enough —
and keep working unless the answer truly blocks. Never routine confirmations
for reversible work, never spam, and never a secret in plaintext: secrets
travel only through `/secret`.

Ops failures and automated-canary breaches are delivered to Telegram through
NoticePlace: POST one `notify.event.v1` event per failed check to
`https://notify.bezrabotnyi.com/v1/events` with the project-scoped producer
token (plain curl; `/opt/noticeplace/bin/notify-producer` is the sanctioned
wrapper). Use a stable `dedup_key` per check, resolve the incident on
recovery, and never let an alerting outage mask the failure itself.

## Compact task state

For a non-trivial request, keep one compact task record under `.agents/tasks/`
when its recovery, coordination, or audit value exceeds its maintenance cost.
Update status in place. Do not require `todo → work → done` copies, snapshot
commits, append-only histories, separate reports, or repeated lifecycle repair
before business work. Existing legacy lineages remain valid and are never
deleted merely to adopt this rule.

When children are used, give them one compact contract and one shared task path
only when durable handoff is useful. Detailed evidence may live in the task or a
named result file; do not force both. The child bootstrap remains
`<Role> <absolute-task-file-path>` when the harness/profile requires it.

Use one project-local state root: `.agents/`. Put reusable one-off Agent Tools
under `.agents/at/`; do not create parallel `.at/` or `.lhc/` roots. Put every
disposable diagnostic, generated helper, and temporary output under the
project's ignored `.tmp/`, not under `.agents/at/` or a system temp directory.

## Unified history

One integrated delivery history on main is the end state of every cycle. Commit
task-owned files at every completed step — small correct commits, never one
final dump. At integration L reviews every path, fixes unsafe or unreviewable
work, and commits the complete repaired result; foreign, generated, binary,
missing, ignored-by-accident, and nested-repository paths are not exclusions.
Do not call a Full cycle complete with any dirty repository or unreachable
commit. If repair requires missing authority, the cycle is blocked, not
complete. Every Full cycle ends clean, pushed, deployed where deployable, and
proven by the real-surface test after the last change. Parallel workers may
share one checkout, but the history stays single: many parallel efforts, one
unified narrative.

## Green start and finish

A cycle owns every defect it discovers, regardless of which subsystem the
defect belongs to: a bug found during work is fixed within the same cycle,
before the final answer. Red or flaky tests count as broken — root-cause them
and make them deterministic; a rerun-green is a measurement, not a fix.
Cycles begin and end in a green, reproducible state: suite passing, services
running committed code, no known unfixed defect left behind. A fix that is
genuinely blocked leaves the cycle blocked, never silently deferred to
"later".

## Route work by total cost

L owns the outcome and may research, edit, test, and integrate directly whenever
that is the least-cost route to the next business proof. There is no fixed
five-minute ceiling on direct work.

- Direct: L acts when the path is sufficiently clear or delegation would cost
  more than the next proof.
- Short: one bounded vertical result, done by L or one Worker according to total
  cost; the three-line minimal path is mandatory, plan and governance ritual is
  not.
- Full: use only when a real material strategy/architecture/migration choice
  remains after tracing the production path and a wrong choice is expensive.
  Plans are optional decision aids, not ceremony.
- Emergency: smallest reversible mitigation of active harm, evidence
  preservation, then business-first reclassification.

Overseer, Tester, and Reviewer are the only gates. Gates are tools, not
milestones. A user-facing result is finished only by a real test on the real
surface — browser/computer-use of the actual product or the real journey — never
by test files alone.
Full requires a fresh independent Tester after technical review; Lead's direct
canary does not replace it. Fix findings and repeat the affected real journey.

## Overseer supremacy and time truth

Every cycle is anchored before work begins with `Started at <UTC+3 ISO>
(<source>)` from a real uptime/session clock; without the anchor the cycle does
not start. Overseer is the supreme route controller: after the initial independent
audit, L consults it at every
crossed wall-clock hour while work is active, at any maximum overrun, on
repeated failed routes or material scope change, and before the final answer of
Full work. Its standing mandate: cut security theater, secret ceremonies,
process/lifecycle repair, and any work that does not produce a tangible result
a real test can verify.

## Worker checkpoints and joins

Every 20 active minutes is a control checkpoint, not a Worker lifetime limit.
The Worker reports progress, business delta, blocker, and the shortest next
action. L then continues the same route, redirects or resumes the same Worker,
or consults Overseer when that decision is genuinely uncertain or costly.
Cancellation is exceptional: use it only for active harm, conflicting writes,
an obsolete duplicate, explicit user direction, or an unrecoverably stuck child.

Use the harness wait/join tool for a required child. A timeout or mailbox wake is
observational, not terminal. Do not send the final answer while a required child
result remains non-terminal. Preserve the child, inspect status, send a compact
course correction when useful, and continue joining. Never replace or kill an
agent merely because 20 minutes or one wait window elapsed.

Workers ask L at decision boundaries because L owns broad context and business
decisions. With a non-blocking parent transport, the Worker sends evidence,
recommendation, proposed default, safe parallel work, and the exact action that
must wait, then continues work valid under every plausible answer. L answers
promptly; absence of transport is reported, not simulated.

Estimate each coherent leaf from its work, acceptance check and specific
uncertainty; twenty minutes is a checkpoint, not a task size. Show actual parallel
dispatch, available slots, dependencies and why any ready work is serialized.
Report summed effort separately from capacity-respecting critical-path duration,
with integration, review, real testing and external waits visible. Derive the
total with arithmetic, never an unexplained broad range or doubled buffer.

Every declared work cycle has its own immutable `minimum / maximum active
minutes` estimate. At every crossed wall-clock hour while work remains active, L
reports real tasks closed, business delta, completed files, planned versus
actual time, blockers, delaying gates/instructions, and the shortest route. Use
`common/tools/lhc_time_guard.py`; a maximum overrun emits its complete
business-first diagnostic. Merely increasing the estimate is not control and an
overrun is not permission to kill a Worker.

For every timing or status answer, state exact known start, original
minimum/maximum, wall-clock, and active time with its source. If active time was
not continuously measured, say `не контролировал`; never infer it from mtime or
wall-clock.

After each supported context compaction, atomically replace the session's
`current-handoff.md`, increment its compaction count, and retain only three recent
marks. This state is not append-only. Lead and Worker read the current handoff
before continuing and treat repeated compactions without business delta as a
route-loop signal.

When route choice is useful, present exactly two genuinely different approaches.
Compress each internally from ideal/full to normal to YAGNI/Pareto MVP, then
show the two compressed variants with pros, cons, time, discarded scope, and
real canary. Prefer the least-cost YAGNI route. These compression levels are not
three plans. Use `$task-decomposition` for the smallest independent business-
verifiable leaves and maximum non-conflicting parallelism.

Plans and decisions are written in Russian, implementation progress in English,
and the final answer in Russian. The active harness owns approval policy. Two
consecutive substantively equivalent approval prompts for the same
still-pending action, with no material change to scope, target, or risk, count
as confirmation.

L reads `ROADMAP.md` when present. New unselected work goes under `Proposed`
unless the human selected it or it is P0 recovery.
<!-- last-human-commit:end -->
