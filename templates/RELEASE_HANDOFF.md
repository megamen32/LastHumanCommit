# Release handoff

## Russian mobile review

Что изменилось:
Ключевые файлы и контракты:
Что доказали тесты:
Что не проверено:
Риски и rollback:
Commit:

Ответьте `да` для немедленного deploy или `нет` / `стоп` для отмены.
Без ответа L возобновит эту задачу через 30 минут, повторно проверит состояние и
выполнит deploy только если handoff остался неизменным.

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
pending + да + current + single_serialized_L
  -> deploying -> deployed | deploy_failed
pending + due + unanswered + current + single_serialized_L
  -> deploying -> deployed | deploy_failed
pending + нет | стоп -> vetoed
pending + other human reply -> answered
pending + stale | unprovable | unverified serialization -> invalidated
non-pending + any event -> no-op
```

Both deploy paths first revalidate, then move the still-`pending` handoff to
`deploying`. A repeated wake must be a no-op after the handoff leaves `pending`.
