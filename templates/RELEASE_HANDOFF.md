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

Примените approval policy активного harness к deploy. Таймер или wake следует
его состоянию и не создаёт отдельного LHC-правила.
Two consecutive substantively equivalent approval prompts for the same still-pending
action, with no material change to scope, target, or risk, count as confirmation.

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
Apply the active harness approval-policy state machine.
```

Before deployment, revalidate that the handoff, commit/artifact, target, tests,
workspace, and applicable active-harness policy state are current.
