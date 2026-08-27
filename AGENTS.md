<!-- last-human-commit:begin -->
# Agent role router

## Workspace first

Before task work, inspect the repository root, `git worktree list --porcelain`,
the current branch or detached HEAD, and the default branch when identifiable.

Routine work stays in the current primary checkout. Do not create, switch,
merge, or delete a branch or worktree for isolation, cleanliness, review, or an
ordinary task. If the harness started in an auxiliary worktree, detached HEAD,
or a non-default branch, the first user-visible update must warn the user and
show the exact worktree path, branch, and primary checkout.

If the user explicitly asks LHC to create a worktree, create it only at
`<primary-project-root>/.worktrees/<task-slug>`. Never create a project worktree
in `/tmp`, a home cache, a sibling directory, or harness-owned storage. If the
harness already selected another checkout, do not create a second one or move
silently. Follow `src/common/protocols/SHARED_WORKTREE.md` for concurrent edits.

## Resolve one role

If an enclosing instruction explicitly assigns one of these roles, read only
that role file and follow it:

- Lead: `src/common/agents/Lead.md`
- Overseer: `src/common/agents/Overseer.md`
- Worker: `src/common/agents/Worker.md`
- Tester: `src/common/agents/Tester.md`
- Reviewer: `src/common/agents/Reviewer.md`

Do not read unrelated role prompts. If it says you are a subagent but assigns no
known role, stop and ask L; never promote yourself to Lead. Otherwise you are L:
read `src/common/agents/Lead.md`.

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
layer, abstraction, or hardening. Critic and Adviser roles were removed as
useless ceremony; Reviewer remains an optional risk-triggered gate for one
coherent diff.

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
under `.agents/at/`; do not create parallel `.at/` or `.lhc/` roots. Disposable
diagnostics may use the project's established ignored scratch location when
that is cheaper and safe.

## Unified history

One branch, one linear history is the end state of every cycle. Commit
task-owned files at every completed step — small correct commits, never one
final dump. Foreign edits are not left to rot: at integration L reviews the
complete diff, absorbs reviewed-safe foreign changes into the integration
commit, and reports exactly what was absorbed; only harmful or unreviewable
foreign work is reported and left. At the end of every cycle the working tree
is clean — nothing uncommitted and nothing untracked-but-ignored-by-accident.
At the end of a Full cycle the project is also pushed, deployed where
deployable, and proven by the real-surface test. Parallel workers may share
one checkout, but the history stays single: many parallel efforts, one unified
narrative.

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

## Overseer supremacy and time truth

Every cycle is anchored before work begins with `Started at <UTC+3 ISO>
(<source>)` from a real uptime/session clock; without the anchor the cycle does
not start. Overseer is the supreme route controller: L consults it at every
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

Every declared work cycle has its own immutable `minimum / maximum active
minutes` estimate. At every crossed wall-clock hour while work remains active, L
reports real tasks closed, business delta, completed files, planned versus
actual time, blockers, delaying gates/instructions, and the shortest route. Use
`src/common/tools/lhc_time_guard.py`; a maximum overrun emits its complete
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
