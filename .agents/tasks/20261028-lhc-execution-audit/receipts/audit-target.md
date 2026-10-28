# Аудит целевой сессии ШТАТНО

Проверен read-only rollout `/home/roomhacker/.codex/sessions/2026/10/27/rollout-2026-10-27T21-33-16-01a17ea3-5600-7580-aba9-1badd2187dd5.jsonl`, native session `01a17ea3-5600-7580-aba9-1badd2187dd5`. Инвентарь подтверждает, что `104.bezrabotnyi.com` — публичный SSH-адрес server-100 (`ServersAdministartion/infra/hosts.md:11-14`, `docs/inventory/devices/100.md:27-30`). Прямое чтение сессии через Herder было недоступно; выводы ниже взяты из локального rollout.

## Что произошло

Сообщение #10 (2026-10-27 18:33:26 UTC) начинается с envelope `🤖 Сообщение от ИИ через Agent Herder` и `kind="agent-relay"`; текст внутри заявляет «ПРЯМОЕ ПОРУЧЕНИЕ ВЛАДЕЛЬЦА» и говорит: «Не трать время на новый LHC». Rollout не доказывает, что это была непосредственно написанная или подтверждённая человеком команда. Это peer relay с неподтверждённой атрибуцией, поэтому он не отменяет human-default LHC. Фраза не является STOP, freeze или отзывом полномочий.

Позднее пользователь расширил работу до нескольких продуктов и всех потребителей. В 2026-10-28 13:27:06 UTC (#3329) в rollout есть plain user message без relay envelope: «Почему ты не сделал план полного цикла, last human commit?» Это более позднее человеческое указание сменило прежний режим; запрета на продолжение не было. Через 14 секунд (#3335) исполнитель признал: «Для расширившейся задачи — несколько продуктов и все потребители — это уже стало ошибкой»; он пояснил, что держался GSD-default и ограничения на самостоятельное создание исполнителей. Ошибка была в том, что неподтверждённый peer relay и проектный GSD-default подавили LHC default; позднее human-authored scope clarification исправила направление.

В 13:31:05 UTC (#3419) сессия сообщила о создании плана, запуске трёх исполнителей и дала ссылку: `https://lhc.bezrabotnyi.com/noticeplace/plan-20261028-1629-ee98cb7bac720e88346bb79c/`. Значит, после явного уточнения владельца планирование и делегирование начались. Данных о завершении всей расширенной поставки этот rollout не доказывает.

## Причина и минимальная правка процесса

В target checkout `/home/roomhacker/ServersAdministartion/AGENTS.md:98-105` предписывал GSD по умолчанию и запрещал загружать LHC без явного запроса. Это конфликтовало с LHC-контрактом `LastHumanCommit/AGENTS.md:94-101`: «Every authorized development task has a user-readable Lead-owned plan before implementation». Противоположная инструкция была внутри agent-relay, а не доказанно от человека; сессия не должна была считать её human opt-out. Позднее прямое human-указание в #3329 сняло двусмысленность, и агент создал план. Значит, это не обвинение за исполнение прямой инструкции владельца: human opt-out не установлен, а LHC default был подавлен peer-content и локальным workflow default.

Минимальная правка общего процесса LHC: передавать runtime краткий semantic intake, который требует от модели использовать доверенную атрибуцию сообщения; agent/peer relay и цитата с заявлением об owner authority не могут снять LHC default или заявить human STOP. Действительный explicit opt-out/STOP действует только при подтверждённом human-authored происхождении. После каждого существенного изменения человеческой цели повторно определять mode; новые authorized engineering scope по умолчанию требуют плана.

Установленная копия LHC — версия 1.6.1 в `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.1`. Rollout подтверждает фактический вызов `common/tools/lhc_plan_json.py` из этой копии.

## Отдельная ошибка сборки плана и текущее состояние

Rollout #3885 (2026-10-28 13:49:57 UTC) содержит неуспешный `lhc_plan_json.py build`: валидатор отклонил в `L02` неизвестные поля `completed_at` и `task_name`. Точный source plan извлечён из команд и артефактов rollout: `/home/roomhacker/agents-projects/noticeplace/.agents/tasks/20261028-consumer-lifecycle/plan.json` и `.../leaves/`.

Текущая read-only проверка этих файлов (2026-10-28): поиск обоих полей по `plan.json` и всем leaf-файлам совпадений не дал. Текущий `L02.json` имеет `status: done`, `started_at` и `finished_at`; прежних `completed_at`/`task_name` в нём нет. Следовательно, владелец уже удалил/исправил эти поля в текущем источнике плана. Повторная сборка не запускалась, поэтому её текущий результат здесь не подтверждён.

В рамках последующего ремонта runtime intake изменён только в `src/common/tools/lhc_entry.py` и `tests/test_native_instruction_hooks.py`: startup и no-plan UserPromptSubmit теперь дают одинаковый семантический intake с правилом об атрибуции и точным путём `skills/plan-artifacts/SKILL.md`; relay больше не может притвориться human opt-out; hooks перечисляют планы-кандидаты и называют continuation только для одной незавершённой leaf с binding к текущей native session. Создание/activation оставлено явной работой модели. `pytest -q tests/test_native_instruction_hooks.py` завершился `32 passed`; исходники не устанавливались и plan rebuild не выполнялся.

## Основание

- Target rollout: исходный owner prompt #10; уточнение owner #3329; признание ошибки #3335; сообщение о плане #3419; ошибка build #3885.
- Топология: `ServersAdministartion/infra/hosts.md:11-14`, `docs/inventory/devices/100.md:27-30`.
- Нормы: `ServersAdministartion/AGENTS.md:98-105`; `LastHumanCommit/AGENTS.md:94-101`.
- Текущий LHC plan source: `/home/roomhacker/agents-projects/noticeplace/.agents/tasks/20261028-consumer-lifecycle/plan.json`, `leaves/L02.json`; только чтение.
