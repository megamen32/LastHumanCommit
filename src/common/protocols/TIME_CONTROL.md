# Business time control

Every declared work cycle has its own immutable `minimum / maximum active
minutes` estimate before execution. A cycle is one coherent route to one
business proof: direct Lead work, one Worker lane, one real canary, one review,
one rollout, or another named operation. Tiny atomic commands may share the
estimate of their enclosing cycle; do not create an estimate per shell command.

Use `../tools/lhc_time_guard.py` at cycle start and every observable checkpoint.
When the harness exposes lifecycle hooks or scheduler wakeups, connect the same
tool there. Its JSON state belongs under
`.agents/shared-session/time/<cycle-id>.json` or the harness's equivalent durable
task state.

## Hourly Lead report

At every crossed wall-clock hour while the task remains active, L reports to the
user, without stopping safe work:

```text
Какие реальные задачи закрыты:
Реальная бизнес-дельта:
Завершённые файлы:
План minimum/maximum активных минут:
Факт active / wall-clock:
Что мешает:
Какие гейты или инструкции задерживают бизнес-результат:
Контроль времени и следующий самый короткий маршрут:
```

If nothing real closed, say `ничего` and explain the blocker. Do not substitute
workers started, tests run, reviews completed, task-card edits, or process
receipts for closed business tasks.

## Estimate overrun

Crossing the original maximum immediately emits the tool's complete Russian
business-first diagnostic. The original estimate remains visible; changing it
does not clear the event. L must answer with evidence and choose a shorter route,
one concrete canary-reaching continuation, or one necessary user decision.

The diagnostic does not authorize weaker essential safety, secret exposure,
missing human authority, destructive action, or unproven business claims. Its
purpose is to remove process and optional hardening that do not protect the
accepted result.

## Capability boundary

A native hook calls the guard at session/cycle start, material update, response
finalizer, and scheduler wake. Without hooks, L calls it manually on each
observable update. Without hourly wake support, the next call reports every
crossed hour once; report the delayed-delivery limitation rather than pretending
the reminder fired on time.
