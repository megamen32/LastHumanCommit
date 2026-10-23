# L22 — неизвестная длительность больше не рисуется как нулевая

- **Исполнитель:** Worker этой задачи (владеет renderer source, его проекциями, тестами, release-манифестами и этой квитанцией).
- **Итог:** F1 и F2 исправлены в canonical renderer; все четыре maintained-проекции синхронизированы; native package 1.5.43 опубликован, установлен и прочитан обратно. L17 остаётся `CHANGES_REQUIRED` до свежей реальной browser-проверки.
- **Источник правды:** `src/common/tools/lhc_grid.py`. Проекции, которые `sync_skills.py` не покрывает, ведутся вручную и синхронизированы побайтно: `plugins/last-human-commit/tools/lhc_grid.py`, `plugins/last-human-commit/common/tools/lhc_grid.py`, `plugins/last-human-commit/native/codex/tools/lhc_grid.py`, `plugins/last-human-commit/native/codex/common/tools/lhc_grid.py`. Правило паритета закреплено существующей проверкой `test_lhc_grid_fix_is_present_in_every_installed_package_projection`.

## F1 — шкала Ганта больше не обещает срок

- **Первопричина:** горизонт считался как `max(makespan, delivery_minutes_max, 1.0)`. При оценках UNKNOWN все длительности становились 0.0, и нижняя граница 1.0 превращалась в настоящую минутную шкалу «0…1 мин» с полосами шириной 5 px у нулевой отметки.
- **Исправление:** шкала времени рисуется только когда хотя бы один лист имеет известную длительность. Если известных длительностей нет, панель пишет «Шкала времени недоступна» и поясняет, что строки показывают состояние и волны, а не длительность; вместо полосы у каждой строки стоит знак «—» без геометрии. Минут в панели Ганта не остаётся вообще.
- **Частично известный план:** шкала остаётся настоящей (реальный горизонт по известным оценкам), но лист без оценки получает знак «—» вместо полосы нулевой ширины, а панель пишет, сколько таких листьев.

## F2 — усилие, критический путь, остаток и пик не превращаются в 0 мин

- **Первопричина:** неизвестная оценка подставлялась как 0.0 в расписание, а плитки и панель «Прогноз» печатали полученный ноль без оговорки, хотя рядом стояло «Срок неизвестен».
- **Исправление:**
  - плитка «Усилие» → значение «неизвестно», подпись «известная часть N мин · критический путь неизвестен · N оценок неизвестны»;
  - «Осталось (без завершённых)» в «Прогнозе» → «неизвестно — N листьев без оценки»;
  - «Критический путь» → «неизвестен — оценки длительности не заданы»; маркер «◆ критический путь» на строках Ганта не рисуется, пока путь не доказан;
  - «Пик параллельности по плану» → «неизвестен — оценки длительности не заданы» (в плитке, в «Прогнозе», в подписи графа и в текстовом выводе);
  - «Заблокировано работы» → «неизвестно · известная часть N мин · N листьев без оценки», **только** если заблокированные листья есть и без оценки; при отсутствии заблокированных листьев остаётся настоящий 0 мин.
- **Что осталось правдой:** известная сумма («Усилие (сумма известных оценок): 0 мин · 16 оценок неизвестны»), счётчик неизвестных, «Прогноз финиша → Срок неизвестен», «Готово 0 / 16», «Осталось 16», «Заблокировано 0» — числа, которые действительно известны, не изменились.

## Проверки

- **RED → GREEN.** До исправления четыре новые проверки падали на pre-fix renderer (`git show HEAD:src/common/tools/lhc_grid.py`): `test_the_gantt_draws_no_numeric_scale_when_no_duration_is_known`, `test_unknown_effort_is_not_reported_as_zero_minutes`, `test_a_partly_known_plan_keeps_the_known_subtotal_and_names_the_unknown`, `test_a_fully_known_plan_still_shows_its_numbers`. После исправления все зелёные.
- `pytest -q tests/test_lhc_grid.py tests/test_lhc_grid_regressions.py` — **95 passed**. Дополнительно: `tests/test_lhc_plan_graph_sync.py`, `tests/test_lhc_plan_surface.py`, `tests/test_plugin_version_parity.py`, `tests/test_native_plugin_readback.py` — зелёные.
- `python3 plugins/last-human-commit/scripts/sync_skills.py --check` — parity PASS (25 skills).
- `python3 plugins/last-human-commit/scripts/validate.py` — PASS (canonical и parity по 25 skills).
- `python3 src/common/tools/lhc_grid.py check-plan .agents/tasks/20261023-human-plans-and-orchestration/task.md .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — 21/21, OK.
- `python3 scripts/lhc_validate_graph.py .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — `valid: true`, ошибок нет.
- `git diff --check` — PASS.

## Реальный all-unknown fixture

Перерисован исходный граф приёмки L17 (`.tmp/home-archive-plan-minimax/plan.graph.json`, 16 листьев без оценки, 13 волн) — тем же renderer, который теперь стоит в установленном пакете:

```text
Gantt ticks: 0 | bars: 0 | dash markers: 16 | "мин" в панели Ганта: False
scale note: True
Параллельность | 0 / 3           | пик по плану неизвестен
Прогноз финиша  | Срок неизвестен | 16 листьев без оценки
Усилие          | неизвестно      | известная часть 0 мин · критический путь неизвестен · 16 оценок неизвестны
Прогноз: Усилие (сумма известных оценок): 0 мин · 16 оценок неизвестны
         Осталось (без завершённых): неизвестно — 16 листьев без оценки
         Пик параллельности по плану: неизвестен — оценки длительности не заданы
         Критический путь: неизвестен — оценки длительности не заданы
         Заблокировано работы: 0 мин
         Срок ожидания: неизвестен — 16 незавершённых листьев без оценки
```

## Публикация и readback

- Версия поднята до **1.5.43** в `.claude-plugin/marketplace.json`, `adapters/hermes/plugin/plugin.yaml`, `plugins/last-human-commit/plugin.json`, `plugin.yaml`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.zcode-plugin/plugin.json`, `com.nousresearch.hermes/plugin.yaml`, `native/codex/.codex-plugin/plugin.json`, `plugins/last-human-commit/README.md` и `plugins/last-human-commit/CHANGELOG.md`.
- Commit `ad60a3afc769ff6513758945dab3831521a3f89b` (`Name unknown durations instead of drawing them as zero`) запушен в `origin/main`; `git ls-remote origin refs/heads/main` вернул тот же SHA.
- Штатные команды менеджера: `codex plugin marketplace upgrade megamen32-plugins` → `codex plugin add last-human-commit@megamen32-plugins` → `codex plugin list --json`.
- Readback: `last-human-commit@megamen32-plugins` версии **1.5.43**, `installed=true`, `enabled=true`, корень `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.5.43`.
- SHA-256 совпадают между canonical source, refreshed marketplace и installed cache:
  - `tools/lhc_grid.py`: `ceef04a9ad0be36820268ec168d411150b204c06ec426818ddd2b0afa2ea82ec`
  - `common/tools/lhc_grid.py`: `f439010d97daa1badcef1e7e62bbae676f7c7bbd3e7ba10ac6d9b1d503818f5f`
- Поведенческий readback: **установленный** `1.5.43/tools/lhc_grid.py` отрисовал all-unknown fixture с 0 делениями шкалы, 0 полосами, 16 знаками «—», без слова «мин» в панели Ганта и с «Усилие → неизвестно».
- **Rollback не тронут:** `last-human-commit@fleet-lhc` остался версии 1.5.36, `installed=true`, `enabled=false`; агрегатный SHA-256 дерева до и после релиза одинаков (`b4f6680dd0edc73e9d969efc21fca601b19b72440311214c12a8db15b715ed34`).

## Не выполнено намеренно

- **Свежая независимая browser-проверка L17 не выполнялась.** Предыдущие материалы приёмки (`consumer-tests/L17-full-project-minimax/`) сохранены без изменений: receipt и скриншоты принадлежат тестеру. Статус L17 сохраняется **CHANGES_REQUIRED**, не PASS.
- **Точный entrypoint текущей сессии** из manager readback не выводится: менеджер подтверждает установленный пакет, но не то, какую версию уже открытая сессия загрузила.
- `plan.md`, `plan.graph.json`, `task.md`, `progress.md` не редактировались — они принадлежат Lead/plan writer; интеграция листа L22 в план выполняется назначенным автором плана.

## Файлы

- `src/common/tools/lhc_grid.py`
- `plugins/last-human-commit/tools/lhc_grid.py`, `plugins/last-human-commit/common/tools/lhc_grid.py`, `plugins/last-human-commit/native/codex/tools/lhc_grid.py`, `plugins/last-human-commit/native/codex/common/tools/lhc_grid.py`
- `tests/test_lhc_grid_regressions.py`
- `.claude-plugin/marketplace.json`, `adapters/hermes/plugin/plugin.yaml`, `plugins/last-human-commit/plugin.json`, `plugin.yaml`, `.claude-plugin/plugin.json`, `.codex-plugin/plugin.json`, `.zcode-plugin/plugin.json`, `com.nousresearch.hermes/plugin.yaml`, `native/codex/.codex-plugin/plugin.json`, `plugins/last-human-commit/README.md`, `plugins/last-human-commit/CHANGELOG.md`
- `.agents/tasks/20261023-human-plans-and-orchestration/receipts/L22-unknown-durations.md`

## Следующий шаг

Lead запускает свежую независимую browser-приёмку на установленной 1.5.43: открыть страницу плана с 16 листьями без оценки, убедиться, что у панели Ганта нет минутной шкалы, полосы заменены знаком «—» и подпись называет шкалу недоступной, а плитка «Усилие» и строка «Осталось» показывают «неизвестно» вместо «0 мин». Результат сохраняется отдельной новой квитанцией; прежние L17-материалы остаются нетронутыми.
