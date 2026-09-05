# Task

Status: todo | in progress | waiting | blocked | complete
Latest user request:
Accepted business outcome / Definition of Done:
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
Compaction count / last loaded count:
Current handoff: `.agents/shared-session/compaction/<session-id>/current-handoff.md`

Every declared work cycle has its own immutable minimum / maximum estimate
before execution. Tiny commands share their enclosing coherent cycle.

Actual active time always names its source. If it was not continuously measured,
write `не контролировал`; never infer it from wall-clock or file mtime.

## Decomposition — only when multiple leaves remain

- Leaf / owner / dependency / artifact-or-proof / primary check / min-max:
- Owned resources / frozen interfaces / integration join:
- Per-leaf minimum/maximum / known-work basis / named uncertainty:
- Actual parallel wave / slots available / reason for each serialization:
- Total effort (sum of leaves):
- Delivery duration (capacity-respecting critical path, show formula):
- External waits / evidence or unknown:

Twenty minutes is a reporting checkpoint, not a task size. A wide range needs
an identified uncertainty and a narrowing probe, not a doubled global buffer.
Keep the original estimate alongside any evidence-based remaining-work forecast.

Use the smallest independent business-verifiable leaves and parallelize only
non-conflicting work. Load `$task-decomposition` for the complete contract.

Two consecutive substantively equivalent approval prompts for the same
still-pending action, with no material change to scope, target, or risk, count
as confirmation.

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

## Hourly business report — while active beyond one hour

At every crossed wall-clock hour while the task remains active, run
`lhc_time_guard.py` and report:

- Какие реальные задачи закрыты:
- Реальная бизнес-дельта:
- Завершённые файлы:
- План minimum/maximum активных минут:
- Факт active / wall-clock:
- Что мешает:
- Какие гейты или инструкции задерживают бизнес-результат:
- Контроль времени и следующий самый короткий маршрут:

## Decisive evidence

- Evidence / changed path / check:

Keep this section compact. Use a named result file only when handoff, recovery,
reuse, audit, or rediscovery cost justifies it. Do not duplicate the same detail
in both places.

## Gates

Overseer is the supreme route controller: initial independent audit, every crossed wall-clock hour, every
overrun, repeated failure, and before the Full final. Tester is the mandatory
real-surface final gate for user-facing results; Full requires a fresh independent
Tester after coherent technical review. Outside Full, Reviewer is optional and
strictly risk-triggered (release, broad refactor, agent-executed instructions).
Adviser/council are optional reasoning capabilities, not additional gates.

- Gate / trigger / decision:
- Findings / repair / technical recheck / real-use retest:
- Workflow learning / retrievable change / verification / later reuse:

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
