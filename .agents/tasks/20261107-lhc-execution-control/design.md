# Контракт выпуска LHC execution control

Поручение владельца: собрать исправления аудита, предложить решение, выпустить новую версию. Merge разрешён. Изменения совместимы с существующими планами. Старые события не переписываются.

## Ответственность
L02: lhc_readiness.py, lhc_parallel.py, согласование readiness в lhc_grid.py и тесты.
L03: lhc_assignment.py, lhc_plan_json.py, lhc_plan_mirror.py и тесты.
L04: lhc_execution.py, отдельный HTTP MCP transport при необходимости, тесты.
L05: интеграция новых CLI/MCP операций, представлений, hooks и инструкций после объединения.

## Assignment v1
Leaf.assignment: schema_version=1, attempt_id, executor_kind(self/session/subagent), lead, executor, parent для subagent, state, dispatch, wake, observed_runtime, events.
Ref: host_id, harness, session_id. Root/lead и parent/executor различны. Legacy leaf.session/harness не считаются подтверждённым назначением.
State: assigned, dispatching, submitted, running, result_ready, accepted, blocked, delivery_unknown, cancelled.
dispatch: request_id, status, turn_id если подтверждён, observed_at, reason, receipt. Неизвестный исход не допускает повтор.
wake: wait_id, state, reason, next_at, observed_at, captured turn id. Владельцем wake является lead.
observed_runtime: state, observed_at, source, turn_id, model, worktree. Плановая модель остаётся отдельным фактом.
assignment_history хранит завершённые прошлые попытки; events append-only. Изменение attempt_id никогда не переносит старую квитанцию.

## Автор события
Новые progress_events.actor получают фактический caller из native MCP metadata или проверенного окружения. Без данных actor=unknown. Leaf.session не является источником actor. Явно переданный автор имеет source=declared, не native_verified. Старые events неизменны.
Локальные CLI/API операции не создают новый слой разрешений: авторство и квитанции являются данными, авторизация принадлежит harness/Herder. Не добавлять запрет обычного принятия результата только потому, что shared MCP не передал caller metadata.

## Совместимость
worker_register регистрирует рабочее дерево, не доказывает старт native исполнения; queued не превращается в running от одной регистрации.
Старый activate сохраняет явную привязку текущей сессии и прежнюю semantics saved task status для self-work. Он не выдаёт это за подтверждение чужого runtime. Для явной новой assignment активация сама по себе оставляет assigned, не running.
Сохранённый статус задачи и observed runtime показываются раздельно. Legacy планы читаются без обязательной миграции и без угадывания host/parent/model.

## Единая готовность
Pure evaluate(tasks,slots): dependencies_satisfied отдельно от dispatchable(true/false/unknown), reason_code, unmet_ids, executor_key.
Только done удовлетворяет dependency, включая развёрнутые milestones. Deferred не является done.
Legacy ready остаётся кандидатом по dependencies/capacity, UI прямо называет это кандидатом. Отдельный dispatchable требует явного target и свежего runtime; owner busy, slot0, external waiting, STOP, delivery_unknown и quota blocker исключают запуск.
Все плановые consumers используют один evaluator, включая fallback. Одна native session занимает один слот, а не число running листьев.

## Canonical persistence API
lhc_plan_json.assign_leaf(plan_dir,leaf_id,assignment,actor=None,expected_hash=None).
lhc_plan_json.transition_leaf(plan_dir,leaf_id,attempt_id,state,receipt=None,actor=None,expected_hash=None).
Допустим общий внутренний update_leaf(...,actor=None,assignment_op=...) для существующего file_lock/CAS. Direct fields assignment/history не должны обходить автоматическую историю или терять root route.
lhc_assignment содержит чистые validate_ref, validate_assignment, new_attempt, transition, resolve_actor; он не импортирует plan_json.

## Herder bridge
Использовать существующий HTTP MCP singleton и существующую protected конфигурацию Herder, без нового сервера/секретного хранилища. Разрешён injected transport для изолированной приёмки.
Высокоуровневые dispatch/reconcile работают только по явному текущему attempt и точному target. Сначала durable dispatch intent со стабильным request_id, затем RPC. Crash/timeout/ambiguous результат сохраняется UNKNOWN и автоматически не повторяется.
Accepted submission не означает running. Running требует наблюдения точного native turn. Перед resume_after проверяется turn identity, квитанция wait сохраняет тот же turn. Нельзя подписаться на чужой/позднейший ход.
Завершение хода переводит результат в result_ready. Только отдельная приёмка переводит задачу в done. Ошибка/квота/STOP не маскируется готовностью. Состояние wake читается и показывается.
Руководитель после wake перечитывает актуальную цель и готовность, принимает результат и запускает следующую доступную работу. Используются существующие Herder delivery и resume_after, отдельного scheduler нет.

## Проверка и поставка
RED/GREEN для всех пяти bug records; реальные CLI/MCP процессы собранного пакета, два независимых потребителя, успешный dispatch/wake на изолированном transport и фактический read-only доступ к установленному Herder. Никаких сообщений людям, изменения quota/STOP или повторов существующих UNKNOWN.
Использовать снимки реальных CI/Rust планов для совместимости и объяснимой readiness, не управлять этими сессиями в тестах.
Версию повысить последней по fresh main: добавляется совместимая возможность, ожидается minor. Пакет, merge main, installed readback и hook trust проверяются штатно. Итоговый продукт и доказательства должны быть опубликованы.
