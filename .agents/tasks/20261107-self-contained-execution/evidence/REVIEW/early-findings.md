# Независимый review: ранние findings (не финальный verdict)

Роль: независимый Reviewer; не автор и не consumer Q1. Frozen integrated SHA ещё не передан. Продукт, runtime, конфигурация и чужой WIP не изменялись. Только exact Git source slices F/H/V и собственные fixtures; авторские result/proof/review reports не использовались.

Base: 2988f0f8483a2a33a6fb762c86e597513b445d1a.
F: 5f8e53b7555751c08937c43b977c79a8e130339b.
H: c31f702b1fca54f5e10d132ea698612ec35813a9.
V: dcba0b3fd2f90b769ea71a634d37eb74816e1d17.

## R1 — P1: bind принимает новую цель по COMPLETE старой цели

`src/common/tools/lhc_plan_control.py:159-189`, `bind_session_plan`; особенно строки 183-186. H добавляет автоматический вызов этого пути при `activate` в `src/common/tools/lhc_plan_json.py:2639`.

Сценарий: в той же Lead session уже есть COMPLETE non-status outcome исследования A. Lead активирует другой implementation-план B, либо явно вызывает bind-plan. Session/plan index и роль Lead совпадают. Код проверяет verdict старого outcome, затем без проверки соответствия целей создаёт свежие plan_scope/outcome_scope и acceptance_fingerprint для B. `evaluate()` возвращает `accepted` для B, хотя canary, original_goal и все evidence относятся к A.

Собственный discriminating test вызывает настоящий `lhc_outcome.verdict` (без mock), сохраняет existing native outcome в изолированном Git fixture и вызывает настоящий `bind_session_plan`. Получено `{"binding":"bound", ..., "goal_status":"accepted"}` для отличающейся B. В seed исследования technical=complete, остальные stages=not-applicable, integration policy отсутствует; это моделирует ранее принятый bounded research, а не готовность B.

Минимальное исправление: обычная активация/привязка не должна придавать прошлой acceptance новую plan identity/scope. Сохранить первоначальный binding и его evidence lineage; неизвестное соответствие → unknown/unaccepted, нужен новый явно связанный contract/assessment. Не решать это только исключением status: исследование/тестирование и другая implementation-цель тоже не доказывают B.

## R2 — P1: canonical acceptance fields не участвуют в scope fingerprint

`src/common/tools/lhc_plan_control.py:20-23`, `plan_scope`.

Fingerprint включает singular `acceptance_scenario`, но игнорирует canonical `acceptance_scenarios`, `business_result` и `business_results` (см. публичный OUTCOME_CONTRACT/PLAN_REPORT и `build_document`). При неизменном кратком goal можно изменить пользовательский результат и сценарии приёмки; старый binding и acceptance_fingerprint останутся валидными, старое принятие переносится на новый scope.

Собственный тест сравнил планы с одинаковым goal, но результатами «one request» и «all tenants without losing data», разными acceptance_scenarios. Получен одинаковый SHA-256 plan_scope. Минимальное исправление: fingerprint всех канонических семантических полей, включая legacy aliases; изменение substantive fields инвалидирует acceptance, progress/timestamps — нет.

## Дополнительная проверка V — пока не полноценный blocker

`lhc_plan_catalog.py:82-92` принимает opaque goal_control fingerprints по наличию полей без проверки соответствия текущему document. Собственный unit probe с изменённой goal и сохранённой старой projection даёт completed/accepted. Нужна оценка producer path / snapshot semantics: исторический snapshot сам по себе допустим при явной маркировке, fabricated projection не доказывает normal-path regression. Поэтому это пока риск/подготовленная проверка, не утверждённый P1.

## Evidence и ограничения

Собственный test source: `.tmp/independent-review/test_independent_control.py`.
Вывод: `.tmp/independent-review/control-red.log` (3 failing safety assertions; первые две — R1/R2, третья — ограниченный V probe).
Первый pytest запуск подхватил repository conftest, который переназначил basetemp в собственный project-local .tmp и затем сам его удалил; последующие запуски будут с `--confcutdir` для строгого own directory scope.
Shared AgentMemory: единственный recall завершился успешно с matched_count=0; recall не является evidence корректности. Прочитаны primary AGENTS/TEST_ACCESS, Reviewer, OUTCOME_CONTRACT, REVIEW_TO_DELIVERY и публичные изменённые протоколы.

До frozen integrated SHA и полного diff/generated parity review — APPROVE отсутствует. Наблюдаемая Q1 native access gap этим review не диагностирована и не считается доказательством причины.

## Дополнение: реальные CLI и public projection пути

Снимок `assembled-slices` создан только внутри `.tmp/independent-review`: base + exact changed objects F/H/V, manifest `slice-provenance.json`. Это подготовительная композиция известных slices, НЕ frozen candidate и НЕ итоговый review integrated SHA.

R1 дополнительно воспроизведён через настоящий subprocess CLI `lhc_plan_json.py activate PLAN L1 --session fixture-lead --harness codex`. При старом COMPLETE research A новая карточка B становится running, а `goal_binding.goal_status` уже `accepted` ДО её первого implementation результата. Transport не открывался; mirror отсутствует по isolated env.

R2 дополнительно проверен через `evaluate`: принятая binding сохраняет `accepted` после изменения business_result/acceptance_scenarios без изменения goal.

### R3 — P2: acceptance projection теряется на обычной публикации

`src/common/tools/lhc_plan_catalog.py:82-92`, `goal_projection` / `summarize` рассчитывают completed/superseded по новому полю `goal_control`. H добавляет его в `lhc_plan_json.py:1207` (`build_document`). Но `lhc_plan_publish.py:128-141`, `public_document`, оставляет только старый plan_keys allowlist, без `goal_control`. Обычный mirror путь `lhc_plan_mirror.py:363` вызывает этот sanitizer; replica `valid_document():937` вызывает его повторно. Поэтому новое состояние цели не доходит до каталога обычным поддерживаемым путём.

Собственный public roundtrip тест: один document с принятым source snapshot до sanitizer даёт `completed/accepted`, после того же `public_document` — `awaiting/unknown`. Доказано отсутствие поля, а не реальная acceptance исходного seed. Минимальное исправление: явная безопасная публичная проекция goal_control, без private outcome/decision payload, с проверяемой связью snapshot scope; сохранить её и при capture, и при replica validation. Проверить completed и superseded через public sanitizer/replica, не только прямым вызовом catalog.summarize.

Независимые fixtures и output: `public-path-tests.py`, `public-paths-red.log` в этой REVIEW директории. Три safety assertions падают на exact F/H/V: CLI activation R1, semantic acceptance R2, publication roundtrip R3. `REVIEW_TOOLS=/absolute/frozen/src/common/tools` позволяет применить те же probes к frozen source без правок продукта.

## Что проверено до frozen

- Прочитаны целиком changed source diffs F/H/V, новый handoff и plan_control, затронутые public protocols, вызовы canonical dispatch/admit/update и public mirror sanitizer.
- В exact assembled source локально выполнены `test_execution_handoff.py`, `test_plan_frontier_control.py`, `test_truthful_plan_views.py`: 58 passed (4.82 s), без авторских PASS reports. Собственные R1/R2/R3 assertions остаются RED.
- Просмотрены CAS/lock пути: admission и immutable receipt создаются под plan lock, leaf intent fsync предшествует deliver; public result оставляет identity, internal payload извлекается request-local persistence closure. Прерванный dispatching становится delivery_unknown, а повторная dispatch не отправляет его заново. Existing tests покрывают failed intent write, changed brief, private hash stability, symlink/FIFO, duplicate JSON fields, byte caps и reader write_paths=[]; это source/fixture evidence, не real native delivery proof.
- Явные assignments используют assignment.lead, не executor, в goal ownership. Legacy registration сохраняется legacy hint. Stop frontier advice ограничено fingerprint/window и stop_hook_active; новых scheduler/auto-send не обнаружено.
- Dependency/capacity candidate и actual admission разведены evaluator/формулировками; partial numeric estimates сохраняются, whole-goal ETA не выдумывается в проверенных сценариях.
- `.planning` файлы относятся к ранее завершённому task continuity (2026-10-14); они не заменяют текущее review поручение. Текущий canonical plan.json self-contained-execution прочитан как scope, без использования author proof reports.

Ожидается только отдельное сообщение Root с exact frozen1.18.0 integrated SHA. После него: полный base..SHA diff (включая installer correction), generated parity/readiness и целевые rechecks. До этого нет APPROVE и нет утверждения о full integrated correctness. Runtime/config/credentials, Airlock VPS и foreign Herder hosting не затрагивались.
