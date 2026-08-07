# Full cycle

Use Full only after Worker research confirms both development over 30 active
minutes and a material product, architecture, migration, or expensive-wrong-path
choice. Keep every decision and result in the same `.agents/tasks/work-*` file.

## Language

- Планы — только на русском.
- Execution updates — English only.
- Финальный ответ — только на русском.

## Outcome and boundary

Outcome:
Exact business canary:
Durable proof:
Confirmed scope:
Explicit exclusions:
Constraints:
Started at (UTC+3):
Initial estimate (minimum / maximum active minutes):
Estimate revisions (append-only, never replace the initial range):
Stop when:
Rethink when:
Consequential actions requiring explicit authorization:

## Research

L delegates repository research to `Worker(mode=research)` and does not search
or write code itself.

Findings and existing mechanism:
Canary blocker:
Unknowns:
Proposed execution graph:

Every implementation node must have one owner, owned paths, one acceptance gate,
known dependencies/join point, and maximum <=20 active minutes. A whole plan may
exceed one hour only as such a graph. One unresolved block above one hour means
more research, not a vague long Worker assignment.

## Mandatory Overseer route audit

Run a fresh no-history Overseer after research and before plans. Pass the raw
user request, the same task file, estimate delta, business delta, blocker, and
proposed next action. Record the compact verdict. A non-`CONTINUE` verdict binds
L.

## Планы

Все планы остаются в подтверждённых границах задачи.

### 1. Максимально идеальный

Результат, объём, исключения, кратко- и долгосрочные компромиссы, риски,
минимальная/максимальная оценка, проверка, миграция, параллельный граф:

### 2. Нормальный

Результат, объём, исключения, кратко- и долгосрочные компромиссы, риски,
минимальная/максимальная оценка, проверка, миграция, параллельный граф:

### 3. YAGNI MVP

Результат, объём, исключения, кратко- и долгосрочные компромиссы, риски,
минимальная/максимальная оценка, проверка, миграция, параллельный граф:

Рекомендация L:
Первый выбор человека (дословно):

Do not implement before explicit selection.

## Full technical preview of the selected plan

Call-stack tree:
File-tree diff:
Key types and method signatures:
Pseudocode:
Migration description:
Exact business canary:
Consequential authorization boundaries:
Execution graph:

The execution graph shows every <=20-minute Worker lane, owned paths,
dependencies, parallel waves, and integration/review joins.

Second explicit approval (verbatim):

Do not implement before the second approval.

## Delivery

Default stage order is `YAGNI -> Normal -> Ultimate`, stopping at the selected
target. Skip or collapse a layer only when it is impossible, unsafe, or pure
throwaway rework; record the reason in the same task file.

For each wave:

1. dispatch independent <=20-minute Worker implementation slices;
2. resume the researching Worker for its lane when supported;
3. run focused checks and the exact canary;
4. review the coherent diff;
5. run a fresh no-history Overseer audit;
6. on maximum overrun, two failed slices, or no business delta, stop and
   RETHINK instead of extending the route.

YAGNI slice and evidence:
Normal slice and evidence:
Ultimate slice and evidence:
Stage exceptions:
Test/canary evidence:
Reviewer evidence:
Overseer receipts:

## Release gate

Run Critic once with raw user context, the same task file, selected plan,
approvals, review, estimate history, and fresh canary proof. L cannot prescribe,
narrow, rewrite, or override the verdict.

Critic verdict:
Commit:
Tag decision (explicit release choice only):

## Финальный ответ

Финальный ответ — только на русском.

Мобильный обзор результата:
