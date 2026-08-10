# Full cycle

Use Full only after Worker research confirms both development over 30 active
minutes and a material product, architecture, migration, or expensive-wrong-
path choice. Keep every decision and result in one `.agents/tasks/` lineage:
copy `todo-*` to `work-*`, then `work-*` to `done-*`, commit each snapshot, and
preserve all copies. The latest committed snapshot is current. Children append
detailed evidence, handoff, and result to the task file and return only TL;DR to
L; no child creates a separate handoff file or second task record.

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

If the active harness has no lifecycle hooks, retain this explicit capability
marker and do not pretend the timer fired: `<cap-off:hooks>каждые 30 минут </cap-off:hooks>`.
When hooks are attested, count from `session_start` and inject the continuing
Overseer at each 30-minute boundary.

Continue the persistent Overseer after research and before plans. It reads the
append-only user-message file, the same task file, shared-session state,
estimate/business delta, blocker, and proposed next action. Do not resend the
full conversation. A non-`CONTINUE` verdict binds L. No 30-minute cooldown may
suppress this or another required event-triggered audit.

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

## Plan criticism and revision

Before human selection, run the fresh Critic in `plan-review` mode over all
three plans. It attacks long-term consequences, reuse assumptions, false YAGNI,
and rewrite risk, and may propose alternatives. Pass its criticism to Adviser;
Adviser revises/recommends the three plans, then L presents them for selection.

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
5. continue the persistent Overseer audit;
6. on maximum overrun, two failed slices, or no business delta, stop and RETHINK
   instead of extending the route.

Only at the end, after the selected implementation and Reviewer pass, run
exactly two fresh Testers on the real user-facing surface: one
`blast-radius` Tester who knows the whole session scope, and one
`zero-knowledge` typical user who reads no code, Git changes, plans, or session
history. Both must attach durable business-result evidence such as screenshots
or video. Repair findings through bounded Worker slices, scoped re-review, and
repeat both passes.

## Release gate

After both Tester evidence packages and canary evidence, run Critic once with raw user context,
the same task file, selected plan, approvals, review, estimate history, and
proof. L cannot prescribe, narrow, rewrite, or override the verdict.

Critic verdict:
Commit (only if created):
Tag decision (explicit release choice only):

## Финальный ответ

Финальный ответ — только на русском.

Мобильный обзор результата:
