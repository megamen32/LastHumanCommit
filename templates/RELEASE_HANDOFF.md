# Release handoff

## Russian mobile review

Финальный ответ - только на русском

Что изменилось:
Ключевые файлы и контракты:
Что доказали тесты:
Совместный worktree review:
Что не проверено:
Риски и rollback:
Commit:

Перед deploy L обязан вызвать `Ask User` при attested capability, либо задать
тот же прямой вопрос в harness: `да` для deploy, `нет` / `стоп` для отмены.
Без явного положительного ответа deploy запрещён; wake может только напомнить
или повторно проверить handoff, но не выполнить deploy.

## L-owned handoff state

handoff_id:
status: pending | answered | vetoed | invalidated | deploying | deployed | deploy_failed
review_sent_at:
eligible_not_before:
wake_transport:
wake_job_id_or_cron_id:
session_locator:
execution_guard: single_serialized_L | unverified
commit_or_artifact:
tests:
target:
acceptance_proof:
rollback_reference:
veto_state:
last_human_reply_at_or_id:
deployment_started_at:
deployment_result:

## State transitions

```text
pending + explicit_yes + current + single_serialized_L
  -> deploying -> deployed | deploy_failed
pending + нет | стоп -> vetoed
pending + other human reply -> answered
pending + stale | unprovable | unverified serialization -> invalidated
non-pending + any event -> no-op
```

Both deploy paths first revalidate, then move the still-`pending` handoff to
`deploying`. A repeated wake must be a no-op after the handoff leaves `pending`.
