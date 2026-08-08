# Release handoff

## Russian mobile review

Финальный ответ — только на русском.

Что изменилось:
Ключевые файлы и контракты:
Что доказал реальный canary:
Что доказали тесты:
Overseer / Reviewer / Tester / Critic:
Текущий worktree и ветка:
Что не проверено:
Риски и существующий rollback reference, если он уже есть:
Commit:

Для deploy ответьте `да`. `нет` / `стоп` отменяет действие.
Без явного `да` deploy не выполняется. Таймер или wake может только повторно
проверить состояние и напомнить о pending handoff; молчание не является
разрешением.

## L-owned handoff state

handoff_id:
status: pending | answered | vetoed | invalidated | deploying | deployed | deploy_failed
review_sent_at (UTC+3):
wake_transport:
wake_job_id_or_cron_id:
session_locator:
execution_guard: single_serialized_L | unverified
commit_or_artifact:
tests:
target:
acceptance_proof:
rollback_reference_if_existing:
veto_state:
last_human_reply_at_or_id:
deployment_started_at (UTC+3):
deployment_result:

## State transitions

```text
pending + explicit да + current + single_serialized_L
  -> deploying -> deployed | deploy_failed
pending + due + unanswered
  -> pending (revalidate and remind only; never deploy)
pending + нет | стоп
  -> vetoed
pending + other human reply
  -> answered (ask again only if deployment intent remains unclear)
pending + stale | unprovable | unverified serialization
  -> invalidated
non-pending + any repeated wake
  -> no-op
```

Before deployment, revalidate that the handoff, commit/artifact, target, tests,
workspace, and user authorization are still current. A repeated wake is a no-op
after the handoff leaves `pending`.
