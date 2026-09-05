# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

Last Human Commit is a business-first, least-cost agent workflow. It keeps the
next real user result ahead of process. A strong Lead decides and decomposes,
suitable executors implement, and independent oversight and testing close the
loop. Model routing optimizes the cost of an accepted result, including rework.

## Core workflow

1. Review current inputs and applicable verified product/LHC learning. Define
   what the user needs now, including the accepted Definition of Done.
2. Trace the actual production consumer path before choosing an implementation
   surface.
3. Name the shortest real business canary and cheapest sufficient proof.
4. Let Lead work directly when delegation costs more; otherwise use the lowest
   sufficient Worker and preserve its useful context.
5. Treat every 20 active minutes as a reporting/control checkpoint, not an agent
   lifetime limit. Continue, redirect/resume, or consult Overseer; cancel only
   exceptionally.
6. Use the harness wait/join mechanism for required children. A timeout is an
   observation, never proof of terminal state.
7. Obtain the initial independent Overseer audit, then re-audit at every crossed
   hour, overrun and repeated failure. Full requires coherent technical review
   and a fresh independent real-use Tester; fix findings and retest.
8. Match evidence to the claim and stop when that claim is proven.
9. Keep one unified history: review every path, repair unsafe or unreviewable
   work, commit the complete result, and end every Full cycle with every
   repository clean, pushed, deployed, and real-surface tested.

Workers ask Lead at decision boundaries because Lead retains the broader user
context and owns business decisions. With a proven non-blocking parent
transport, the Worker sends evidence, recommendation/default, parallel-safe
work, and the exact blocked action, then continues safe work while Lead decides.

Every declared work cycle records an immutable minimum/maximum estimate. The
dependency-free `src/common/tools/lhc_time_guard.py` emits idempotent hourly
business reports and original-maximum overrun diagnostics. Native hooks call it
when attested; otherwise Lead calls it at observable checkpoints and reports any
delayed hourly delivery honestly.

Overseer, Tester, and Reviewer are the only gates. Gates are tools, not
milestones. When
a route choice matters, LHC compares two genuinely
different approaches after compressing each from ideal to normal to YAGNI/Pareto
MVP. It does not manufacture a third option, double testing, per-wave reviews,
or hardening loops merely because a task is important.

The [factory skill catalog](src/common/skills/README.md) adds architecture design, model routing,
decomposition and dispatch, standalone user testing, focus groups, council,
independent decision challenge, and workflow improvement through verified reuse.
Adviser is optional; Critic is a compatibility alias. The
[routing configuration](src/common/config/model-routing.example.json) preserves
user-defined classes and examples as aliases, not verified provider identifiers.
These instructions do not install a scheduler or prove a multi-model run.

[Architecture design](src/common/skills/architecture-design/SKILL.md) starts from
the current inputs and a working solution, probes pivotal risks, verifies an
early end-to-end skeleton, independently challenges the improved design, then
derives complete-outcome YAGNI steps and measurable parallel work. Product
improvement and improvement of LHC's own methods both close with verification
and feed applicable learning into the next cycle.

## State and workspace

Use one compact `.agents/tasks/` record when recovery, coordination, or audit
value justifies it. Update it in place. Legacy `todo/work/done` lineages remain
valid, but new work does not require snapshot copies or snapshot commits.

Simple work stays in the primary checkout. For independent parallel writes,
Lead assigns `lhc/<task-slug>` at
`<primary-project-root>/.worktrees/<task-slug>` through
`src/common/tools/lhc_worktree.py plan|create`. The primary root comes from Git
even when called inside an auxiliary checkout. Every harness reuses that path.
Lead integrates reviewed lanes into main, checks the combined result and pushes;
only clean task-owned worktrees and branches merged into remote main are removed.
Preserve foreign, dirty and unmerged work.

## Human and secret boundaries

The active harness owns approval policy. Ordinary missing decisions use one
compact direct question. Secrets are not work: read them from an environment
variable, `.env`, or a secret file in one step; secret-handoff infrastructure
is forbidden.

## Install the portable router

Copy `src/common/` and `templates/` into a project, then use the explicit
marker-only helper. It preserves project text outside one canonical block:

```sh
scripts/lhc-block init AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block init CLAUDE.md /path/to/project/CLAUDE.md
scripts/lhc-block apply AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block apply CLAUDE.md /path/to/project/CLAUDE.md
```

Optional harness adapters live under `adapters/`. Factory skill sources live in
`src/common/skills/`; `plugins/last-human-commit/scripts/sync_skills.py` generates
self-contained native copies into `skills/` and mirrors all native skills into
`plugins/last-human-commit/skills/`. Existing native skill sources remain in
`skills/`. Edit the owning source, then regenerate and check parity.

Validation:

```bash
python3 -m pytest -q tests/test_business_first_contract.py
python3 -m pytest -q tests/test_time_guard.py
python3 tests/validate.py
sh tests/test_task_states.sh
python3 -m pytest -q adapters/hermes/plugin/tests/test_plugin.py
```
