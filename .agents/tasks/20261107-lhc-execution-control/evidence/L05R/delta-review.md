# Delta review LHC 1.17.0

APPROVE для candidate `d0c60f89fb3fea69ebcc2bfaaf07ecdb2be53487`.

Исходный report и RED evidence сохранены без изменений. Повторный полный аудит не проводился.

Дочитана delta `5bf8733..c5bf219c`: B11 применяет split_milestones под прежним admission lock; B12 ограничивает catch ValueError execution CLI; B13 обновляет точные assertions без потери смысловых проверок; B14 сохраняет native tool error reason и deterministic wait identity, не повторяет wait; B15 отделяет Saved queue и plan_state. Дочитана delta `c5bf219c..d0c60f89`: B16 исключает undecomposed milestone из candidate/dispatchable и slots/owner accounting с видимым stage_undecomposed. Новых подтверждённых блокеров нет.

Лично повторён исходный двухсторонний repro через `plugins/last-human-commit/native/codex/tools` исправленного candidate. Команда: `python3 .agents/tasks/20261107-lhc-execution-control/evidence/L05R/milestone-repro-package.py`. Exit 0.

1. P queued, M depends_on P, child C parent M: admission теперь отказывает dispatch_not_admitted:dependencies_unmet и оставляет assigned. Исходный RED допускал dispatching.
2. M saved queued, child C done, N depends_on M: admission теперь сохраняет dispatching. Исходный RED ошибочно отказывал dependencies_unmet.

GREEN stdout: milestone-package-green.log. Структурированный результат и новые fixtures: green-native-package/. Product src/scripts/tests/plugins reviewer WT совпадает с exact candidate. Исходный P1 закрыт проверенным поведением native package.

Full suite Reviewer не запускал. Consumer journeys, финальный validate, merge/release, installed readback и hook trust принадлежат root и отдельным testers. APPROVE относится к coherent source review и проверенной исправленной delta, а не к завершённой установке или бизнесрезультату. Реального Herder dispatch, сообщений, LLM turns, native writes и STOP/quota/config изменений нет. Airlock VPS исключён.
