# ZCode native LHC activation

- **Запрос:** обычный новый ZCode engineering prompt без `@LHC` включает полный
  LHC lifecycle; работать только в назначенном worktree, не трогать отменённую
  `sess_61397aa9...`, установить ZCode после release gates и проверить реальный prompt.
- **До:** ZCode 0.16.9 не имел LHC в `installed_plugins.json`/`plugins list`;
  текущий plugin manifest проходил `zcode plugins validate`, но runtime `zcode`
  отсутствовал в `lhc_entry`/time guard, поэтому Stop/clock lifecycle не включался.
- **Изменение:** native `.zcode-plugin` manifest, отдельный ZCode hook для
  `PostToolUseFailure`, ZCode runtime detection/lifecycle/Stop и регрессии;
  версия пакета 1.4.11. `AGENTS.md` и `CLAUDE.md` синхронизированы после gate
  failure; предел проверки router обновлён до 160 строк (текущий router — 156).
- **Проверки:** RED воспроизведён (ZCode runtime отвергался, 3 regression failures);
  после обоих исправлений `python3 tests/validate.py` — PASS, 296 tests и shell
  adapter; LHC parity/validator и `zcode plugins validate plugins/last-human-commit`
  — PASS. Один независимый Reviewer сначала потребовал сохранить длинный prompt и
  учесть `turnId`; после точечного исправления повторно дал `APPROVE`.
- **Ограничение:** первый новый headless prompt `sess_1cc76e15-307b-4fdf-9b62-6376661e20c9`
  вызвал старый SessionStart hook и записал только `.tmp/zcode-native-red-20261019/`
  `.agents/shared-session/time/zcode-<session>.json`. Plugin отсутствовал в
  registry; model request завершился HTTP 429, затем только эта новая probe-сессия
  отменена. Ответ модели и file fix не получены; это не consumer acceptance.
- **Следующий шаг:** обновить свежую `origin/main`, опубликовать проверенную ветку
  и открыть PR. Затем штатно добавить marketplace/install через ZCode manager,
  предварительно сделав backup его конфигов, открыть новую сессию без `@LHC` и
  сохранить реальные hook output/state и законченный результат prompt. Не заявлять
  готовность без installed consumer proof.
