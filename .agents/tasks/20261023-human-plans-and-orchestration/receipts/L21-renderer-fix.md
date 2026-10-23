# L21 — исправление двух дефектов страницы плана

- **Исполнитель:** Worker этой задачи
- **Итог:** два дефекта исправлены; источник, сгенерированные package/native копии и установленный native package 1.5.42 совпадают.
- **Первопричина 1:** summary строил фразу «без неизвестных оценок и ожиданий» именно при наличии неизвестных estimate или срока внешнего ожидания. Теперь summary называет число листьев без оценки и явно сообщает, что срок ожидания не подтверждён.
- **Первопричина 2:** открытие карточки показывало её после sticky progress strip, но не прокручивало к кнопке возврата. Теперь после показа карточка получает scroll margin по фактической высоте полоски и прокручивается в начало видимой области.
- **Regression:** до исправления новые проверки воспроизводили обе ошибки; после исправления `pytest -q tests/test_lhc_grid.py tests/test_lhc_grid_regressions.py` — 91 passed. Дополнительные проверки: `python3 plugins/last-human-commit/scripts/sync_skills.py --check` — parity PASS (25 skills); `python3 plugins/last-human-commit/scripts/validate.py` — PASS; `python3 src/common/tools/lhc_grid.py check-plan .agents/tasks/20261023-human-plans-and-orchestration/task.md .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — 21/21; `python3 scripts/lhc_validate_graph.py .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — valid; `git diff --check` — PASS.
- **Публикация:** commit `0a95a9c` (`Fix plan dashboard uncertainty and task navigation`) запушен в `origin/main`; remote main совпал с этим коммитом.
- **Установленный readback:** Codex plugin manager показывает `last-human-commit@megamen32-plugins` версии 1.5.42, installed/enabled. SHA-256 совпадает между native package, refreshed marketplace и installed cache:
  - `.codex-plugin/plugin.json`: `075a2bcca701f3c3e5286ed2b761b43735097911f5dfaf0177548f66deb9d2e7`
  - `tools/lhc_grid.py`: `a1bdef5d6078cf4dae121ff67a9bd4f9b6e89a03ed1f74e0b4ae0a1f395344fd`
  - `common/tools/lhc_grid.py`: `4ee15d3384e8747c80ff1dd03325225e3af75d17662445d4dfcf0d40fcd3f16e`
- **Rollback:** `last-human-commit@fleet-lhc` остался версии 1.5.36, installed/disabled; не менялся.
- **Не выполнено намеренно:** независимая свежая browser-проверка L17. Его статус сохраняется `CHANGES_REQUIRED`, не PASS; Lead запускает отдельную свежую user session и сохраняет новый результат.
- **Файлы:** `src/common/tools/lhc_grid.py`, четыре generated `plugins/last-human-commit/**/lhc_grid.py` projections, `tests/test_lhc_grid.py`, `tests/test_lhc_grid_regressions.py`, versioned plugin manifests/README/CHANGELOG и task-plan artifacts.
- **Следующий шаг:** Lead выполняет L17 в свежей установленной сессии 1.5.42 и фиксирует browser evidence; точный entrypoint текущей сессии не выводится из manager readback.
