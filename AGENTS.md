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
- Adviser: `src/common/agents/Adviser.md`
- Critic: `src/common/agents/Critic.md`
- Worker: `src/common/agents/Worker.md`
- Reviewer: `src/common/agents/Reviewer.md`
- Tester: `src/common/agents/Tester.md`

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

## Route work by total cost

L owns the outcome and may research, edit, test, and integrate directly whenever
that is the least-cost route to the next business proof. There is no fixed
five-minute ceiling on direct work.

- Direct: L acts when the path is sufficiently clear or delegation would cost
  more than the next proof.
- Short: one bounded vertical result, done by L or one Worker according to total
  cost; no plan or governance ritual.
- Full: use only when a real material strategy/architecture/migration choice
  remains after tracing the production path and a wrong choice is expensive.
  Plans, Adviser, or Critic are optional decision aids, not ceremony.
- Emergency: smallest reversible mitigation of active harm, evidence
  preservation, then business-first reclassification.

Overseer, Adviser, Critic, Reviewer, and Tester are risk-triggered. Invoke them
only for a concrete uncertainty, repeated failure, material scope/route change,
high-impact regression risk, disputed proof, release, or irreversible action
where their expected value exceeds their delay. Gates are tools, not milestones.

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

For every timing/status or AskHuman answer, state exact known start, original
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

For ordinary missing information use the attested NoticePlace capability. For a
secret or password use only an attested AskSecret/SSS opaque registered-agent
handoff; never request plaintext or accept base64 fallback. If the capability is
not attested, report it unavailable.

L reads `ROADMAP.md` when present. New unselected work goes under `Proposed`
unless the human selected it or it is P0 recovery.
<!-- last-human-commit:end -->
