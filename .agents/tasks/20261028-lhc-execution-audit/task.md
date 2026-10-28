# Запуск и ведение инженерных планов LHC

Обычная инженерная задача должна доходить до работающего результата через план и исполняемые листья. Результат проверяется на свежем Luna canary и отдельно подтверждается в исходном и установленном package/runtime состоянии.

## Подтверждённые находки и исправление

Три независимых Luna-аудита завершены: receipts/audit-contract.md, receipts/audit-target.md, receipts/audit-active.md. В целевой сессии исходное «не новый LHC» пришло как Agent Herder agent-relay, а не как подтверждённый прямой человеческий opt-out. После расширения цели сессия продолжала прежний режим до замечания владельца. К моменту аудита план создан, а некорректные поля листа уже исправлены самим владельцем задачи; его исходники не менялись.

В выборке пяти активных сессий на server-100 четыре связанных плана найдены, у XERJ план не найден в проверенных стандартных путях. Покрытие остальных хостов неполное, отсутствие планов за пределами проверки не утверждается.

Source intake исправлен: нет молчания при отсутствии плана, нет автоматического продолжения чужой задачи, нет мутаций из prompt hook и ложного обещания auto-scaffold. Только проверенное решение человека меняет обязательный инженерный план; agent relay не доказывает такого исключения. Контракт допускает однолистовой quickfix и read-only диагностику до плана.

Отдельно опубликован узкий hunk Server Administration AGENTS.md, заменяющий устаревший GSD/no-LHC default: ServersAdministartion main 48b0845f. Ранее существовавший WIP того же файла сохранён через staging только собственного hunk; чужая часть не вошла в commit. Runtime hook: 33 passed; полный tests/validate.py после интеграции пакета: 530 passed, 5 skipped. LHC 1.6.2 опубликован (48a00d3), установлен native manager; hashes установленных файлов совпали. Native API выявил девять недоверенных текущих хуков из-за смены регистрации: после проверки команд все девять trusted/enabled, 72 прежних состояния сохранены. Инструкция проверки готовности и квитанция опубликованы в ef6e190.

Реальная приёмка: первый изолированный запуск с отключённой пользовательской конфигурацией не загрузил LHC и сохранён как RED. Штатный запуск сам создал план до исправления и привязал L01 к реальной сессии; искусственный четырёхминутный таймер прервал ход. Одно продолжение в разрешённом владельцем режиме доступа закрыло тот же лист и завершилось turn.completed/exit 0, без дублирования плана. Независимые 3/3 проверки прошли; local main и bare origin совпали на 8e2621b. Root независимо прочитал L01 done, graph/session и local origin, а также turn.completed. Отдельный status-only запрос сохранил один план/один лист. Сырой native stdout/stderr остаётся локальным; публикуются только сводные квитанции. Полная история и ограничения: receipts/native-luna-delta-acceptance.md. Peer-relay/STOP не проходили отдельный нативный поведенческий сценарий; resolved model/provider и hook-event не экспортировались CLI, поэтому они не заявляются как аттестованные этим canary.

## Plan

Цель: обычный инженерный запрос приводит Lead к началу подходящего плана до реализации; quickfix не исключает план; новый запрос не присоединяется молча к несвязанному открытому плану.
Что будет работать: краткий точный стартовый шаг, явный смысловой выбор при неоднозначном продолжении, исполняемый связанный лист и точная документация фактического runtime.
Декомпозиция: 3 листа · 1 параллельно · 3 волны · слотов: 1

✅ L01 Проверить целевую и активные сессии, оценка 15 минут
  Описание задачи: Сверить canonical checkout и целевой main, посмотреть активные сессии и ownership; зафиксировать условия, при которых можно менять общий механизм, сохраняя WIP.
  Приёмка: Записаны источник целевого checkout, branch/status, актуальные receipts и покрытие инвентаря активных сессий; неизвестное покрытие явно оставлено unknown.
  Затрагиваемые файлы: `AGENTS.md`, `plugins/last-human-commit/AGENTS.md`, `src/common/tools/lhc_entry.py`, `src/common/skills/last-human-commit/SKILL.md`, `src/common/skills/plan-artifacts/SKILL.md`, `plugins/last-human-commit/com.openai/hooks/hooks.json`, `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.6.1/common/tools/lhc_entry.py`

✅ L02 Исправить подтверждённый разрыв активации и ведения плана, после L01, оценка 15 минут
  Описание задачи: Реализовать согласованный механизм начала или продолжения плана до изменений, устранить немое отсутствие плана и неверное присоединение чужой задачи; синхронизировать описание с реальным поведением.
  Приёмка: Воспроизводимые сценарии new-task/no-plan, unrelated-open-plan и exact continuation получают однозначный start/choice/continuation; контракт и skill соответствуют коду; без prompt regex, Stop veto и нового scheduler.
  Затрагиваемые файлы: `src/common/tools/lhc_entry.py`, `src/common/tools/lhc_plan_json.py`, `src/common/tools/lhc_plan_mirror.py`, `src/common/skills/last-human-commit/SKILL.md`, `src/common/skills/plan-artifacts/SKILL.md`, `tests/test_native_instruction_hooks.py`, `plugins/last-human-commit/common/tools/lhc_entry.py`, `plugins/last-human-commit/native/codex/tools/lhc_entry.py`, `plugins/last-human-commit/common/skills/last-human-commit/SKILL.md`, `plugins/last-human-commit/common/skills/plan-artifacts/SKILL.md`

✅ L03 Проверить реальное выполнение и установить пакет, после L02, оценка 15 минут
  Описание задачи: Проверить source отдельно от выпущенного пакета, провести изолированный Luna canary обычного инженерного запроса и проверить наблюдаемое runtime-поведение, затем выполнить установку выбранным штатным путём и прочитать установленный пакет.
  Приёмка: Есть отдельные receipts на source/check, artifact/package, installed readback и реальный canary; обычный запрос не теряется и не привязывается к постороннему плану; LHC принимает результат.
  Затрагиваемые файлы: `plugins/last-human-commit/`, `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/`
