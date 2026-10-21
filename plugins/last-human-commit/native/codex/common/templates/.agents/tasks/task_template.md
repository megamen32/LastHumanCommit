# Task

Status: todo | in progress | waiting | blocked | complete
Latest user request:
Owning project (inferred from the current work, not the initially opened folder):
Current project inputs / constraints / verified state:
Applicable product learning / source / freshness:
Applicable LHC method learning / source / freshness:
Accepted business outcome / Definition of Done:
Who / realistic user goal / before-versus-after / where to try the result:
Bug: failing RED reproduction before repair / GREEN / original scenario:
Major outcome milestones (roughly 3 hours) / fresh personas / raw feedback:
Stopping condition (no next feature once satisfied):
Original whole-objective start / whole-delivery forecast / basis:
Remaining required blockers / revised remaining forecast against original:
Exact business canary:
Cheapest sufficient proof:
Actual production consumer path:
Scope:
Explicit exclusions:
Current blocker:
Next shortest action:

Harness:
Agent session:
Workspace / branch:
Primary project root / assigned canonical worktree / immutable base / owner:
Started at (UTC+3) + anchor source (hook file / manual clock):
Initial estimate (minimum / maximum active minutes):
Actual active minutes:
Actual wall-clock minutes:
Last business delta:

## Route

Execution mode: direct Lead | Worker research | Worker implement | mixed
Why this is least-cost:
Agent/model, only when material:
Decision model / suitability:
Executor model / capability needs / fallback reason:
Gate value test:
Consequential-action / active-harness boundary:
Cycle estimates (cycle / minimum / maximum / actual):
Time-guard state: `.agents/shared-session/time/<cycle-id>.json`
Persistent session learning checkpoint / last verified outcome / next due:
Compaction count / last loaded count:
Current handoff: `.agents/shared-session/compaction/<session-id>/current-handoff.md`

Every declared work cycle has its own immutable minimum / maximum estimate
before execution. Tiny commands share their enclosing coherent cycle.

Actual active time always names its source. If it was not continuously measured,
write `not measured` for that historical gap; never infer it from wall-clock
or file mtime. L owns starting/repairing `lhc_active_time.py` interval accounting
before new work; each executor owns its intervals. Name pause/resume evidence.

## Decomposition — only when multiple leaves remain

- Leaf / owner / dependency / artifact-or-proof / primary check / min-max:
- Owned resources / frozen interfaces / integration join:
- Per-leaf minimum/maximum / known-work basis / named uncertainty:
- Actual parallel wave / slots available / reason for each serialization:
- Total effort (sum of leaves):
- Delivery duration (capacity-respecting critical path, show formula):
- External waits / evidence or unknown:

Decompose into meaningful subtasks estimated at about 15 minutes, not runtime caps.
Fifteen minutes sizes the leaf; twenty minutes remains a reporting checkpoint that is
later than the leaf, so a Worker holding a 15-minute leaf reports by the 20-minute mark.
A wide range needs an identified uncertainty and a narrowing probe, not a doubled
global buffer. Keep the original estimate alongside any evidence-based remaining-work
forecast.

Use the smallest independent business-verifiable leaves and parallelize only
non-conflicting work. Load `$task-decomposition` for the complete contract.

The active harness owns approval policy. Repeated prompts do not manufacture user consent.

## Worker checkpoint — only when delegated

Every 20 active minutes is a reporting checkpoint, not a lifetime limit.

- UTC+3:
  Progress:
  Business delta:
  Blocker:
  Route still shortest:
  Shortest next action:
  L action: continue | redirect/resume | consult Overseer | exceptional cancel

Use the harness wait/join tool while a required child is non-terminal. A wait
timeout is observational. Prefer the same Worker; cancellation is exceptional.

## Worker questions for L — only when delegated

- UTC+3:
  Decision boundary:
  Evidence:
  Recommendation and proposed default:
  Safe independent work continuing in parallel:
  Exact action waiting for L:
  Parent transport / delivery state:
  L decision:

## Plan — live plan report

Canonical format: `common/protocols/PLAN_REPORT.md`. Rewrite this block at
every 30-minute plan boundary and whenever the user asks for the plan. The
Overseer reads it against the original request and the business canary; it never
blocks delivery.

## Task graph — machine-readable plan

Canonical format: `common/protocols/TASK_GRAPH.md`. The graph holds the same
leaves as the report above and is updated with it at every plan boundary.

Graph file: plan.graph.json
Render: python3 <LHC>/common/tools/lhc_grid.py render plan.graph.json -o plan.html

Цель:
Бизнес-результат:
Декомпозиция: N листьев · P параллельно · W волн(а) · слотов: S

✅ (описание листа) начата ЧЧ:ММ закончена ЧЧ:ММ, оценка N минут, факт N минут
✅ (описание листа) начата ЧЧ:ММ закончена ЧЧ:ММ, оценка N минут, факт N минут, ∥ параллельно с листом 1
🔄 работаем (описание листа) начата ЧЧ:ММ, оценка N минут, прошло N минут, отстаём потому что: <причина>
🔄 работаем (описание листа) начата ЧЧ:ММ, оценка N минут, прошло N минут, ∥ параллельно с листом 3
⏳ (описание листа) начнём после листа N, потому что <почему нельзя параллельно>, примерно в ЧЧ:ММ, оценка N минут, закончим в ЧЧ:ММ

## Decisive evidence

- Evidence / changed path / check:

Keep this section compact. Use a named result file only when handoff, recovery,
reuse, audit, or rediscovery cost justifies it. Do not duplicate the same detail
in both places.

## Gates

Overseer is the plan reader and the Lead's guide: it reads the 30-minute plan report
against the original request and the accepted business canary and returns the smallest
correction; it never blocks delivery and never waives a gate, and it does not own the
result — the Lead owns the decision. Tester is the mandatory
real-surface final gate for user-facing results; Full requires a fresh independent
Tester after coherent technical review. Outside Full, Reviewer is optional and
strictly risk-triggered (release, broad refactor, agent-executed instructions).
Adviser/council are optional reasoning capabilities, not additional gates.

- Gate / trigger / decision:
- Findings / repair / technical recheck / real-use retest:
- Workflow learning / retrievable change / verification / later reuse:
- Product improvement / observed issue / repair / fresh-use evidence:
- Next cycle inputs / verified applicable results to retrieve:

## Result

Business result:
Claim strength proven:
Source/test proof:
Deployment state:
Real canary proof:
Tree clean (nothing uncommitted):
Pushed (Full cycle):
Deferred non-blocking findings:
Commit (each completed step):
