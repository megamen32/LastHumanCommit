# Независимое ревью LHC 1.17.0

Решение для проверенного candidate: CHANGES_REQUIRED.

Проверенный commit: `5bf8733ba00f7e681823d883688402d113cf478a`.
База: `fd039303dbd548dd25c7030d6aa15622bb47d8b7`.
Роль: независимый Reviewer, leaf L05R. Product source не менялся.

## Проверенная область

Прочитаны applicable AGENTS.md, primary TEST_ACCESS.md, MODELS.md, Reviewer.md и accepted design. Scoped AgentMemory recall вернул 0 результатов. Graphify graph в reviewer WT отсутствует.

Проверены новые assignment/readiness/execution/transport модули, изменения canonical persistence и atomic admission, CLI/MCP request actor, plan recovery, grid/publish projection и package copy list. Просмотрены новые regression cases для actor, attempt/CAS/history, native turn, UNKNOWN, wake registration/status, lifecycle/acceptance, slot/owner accounting и UI. Авторские GREEN логи не использовались как доказательство бизнесрезультата.

## P1: atomic admission оценивает неразвёрнутые milestones

Место: `src/common/tools/lhc_plan_json.py:2016-2017`.

`admit_leaf` внутри существующего plan lock передаёт в `evaluate` результат `collect_leaves`, пропуская `split_milestones`. Остальные plan consumers разворачивают milestone dependencies и наследуемые prerequisites перед readiness. Поэтому публичный dispatch получает решение, противоположное показанному пользователю и договорённому контракту.

Воспроизведение выполнено без native dispatch, на двух disposable fixtures через настоящие `assign_leaf`, `transition_leaf` и `admit_leaf`:

1. P queued; milestone M depends_on P; queued child C parent M. У C нет собственных depends_on. Canonical expanded readiness возвращает `dependencies_satisfied=false`, `unmet_ids=[P]`; atomic admission реально сохраняет `dispatching`. Следующий этап публичного dispatch смог бы отправить работу до завершения prerequisite.
2. Milestone M хранит queued; его единственный child C done; N depends_on M. Expanded readiness допускает N, но atomic admission отказывает `dispatch_not_admitted:dependencies_unmet`. Такая нормальная milestone модель останавливает продолжение завершённого этапа.

Evidence: `milestone-repro.py`, `milestone-repro.json` и два fixture каталога рядом. Минимальный ремонт: под тем же lock применить `split_milestones` к collected tasks перед `evaluate`; закрепить обе стороны расхождения regression tests. Root уведомлён сразу после воспроизведения и принял finding в исправление.

## Остальные выводы

Других подтверждённых P0/P1 в проверенной области не найдено. Native send intent сохраняется перед RPC; ambiguous outcomes и interrupted dispatch не повторяются автоматически; wake status сверяется по owner/dependency/turn; completion и acceptance разделены. Это вывод из source review, а не установленного бизнесрезультата.

## Что выполнено лично и ограничения

Лично выполнено только bounded two-case reproduction выше. Full suite, consumer journeys и native runtime не запускались и не дублировались. Реальных сообщений, LLM turns, native writes, STOP/quota/config изменений нет; Airlock VPS исключён. Package stage/install readback, external authorization и реальные consumer outcomes принадлежат root и двум отдельным acceptance sessions. Generated package projection просмотрена на уровне списка новых модулей и diff, отдельная сборка Reviewer не выполнялась.

Это ревью exact candidate. После ремонта требуется дочитать только его малую delta; повторное полное ревью не требуется.
