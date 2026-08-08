# Full cycle

Use Full only after Worker research confirms both development over 30 active
minutes and a material product, architecture, migration, or expensive-wrong-
path choice. Keep every decision and result in the same `.agents/tasks/work-*`
file. Children append their detailed evidence and result to that file and return
only TL;DR to L; no child creates a second task record.

## Language

- Планы и решения человека — только на русском.
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
user request, the same task file, estimate/business delta, blocker, and proposed
next action. A non-`CONTINUE` verdict binds L. No 30-minute cooldown may suppress
this or another required event-triggered audit.

## Планы — всегда ровно три

### 1. Максимально идеальный

Результат, объём, сознательные исключения, кратко- и долгосрочные компромиссы,
риски, минимальная/максимальная оценка, проверка, миграция, execution graph:

### 2. Нормальный

Результат, объём, сознательные исключения, кратко- и долгосрочные компромиссы,
риски, минимальная/максимальная оценка, проверка, миграция, execution graph:

### 3. YAGNI 80/20 — полный результат сейчас

Результат, объём, сознательные исключения, кратко- и долгосрочные компромиссы,
риски, минимальная/максимальная оценка, проверка, миграция, execution graph:

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

The graph shows every <=20-minute Worker lane, owned paths, dependencies,
parallel waves, and integration/review joins.

Second explicit approval (verbatim):

Do not implement before the second approval.

## Delivery

The selected plan targets the complete desired outcome. `YAGNI 80/20` is a
complete result, not an unfinished MVP. Delivery slices may be durable prefixes
of that plan, but never relabel a partial slice as the selected outcome or
not create three branches, worktrees, specifications, or throwaway implementations.

For each wave:

1. dispatch independent <=20-minute Worker implementation slices;
2. resume the researching Worker for its lane when supported;
3. run focused checks and the exact canary;
4. review the coherent task-owned diff;
5. run a fresh no-history Overseer audit;
6. on maximum overrun, two failed slices, or no business delta, stop and RETHINK
   instead of extending the route.

After the selected implementation and Reviewer pass, run fresh Tester in
`only-new` mode on the real user-facing surface. Repair findings through bounded
Worker slices, scoped re-review, and retest.

## Release gate

After fresh Tester and canary evidence, run Critic once with raw user context,
the same task file, selected plan, approvals, review, estimate history, and
proof. L cannot prescribe, narrow, rewrite, or override the verdict.

Critic verdict:
Commit (only if created):
Tag decision (explicit release choice only):

## Финальный ответ

Финальный ответ — только на русском.

Мобильный обзор результата:
