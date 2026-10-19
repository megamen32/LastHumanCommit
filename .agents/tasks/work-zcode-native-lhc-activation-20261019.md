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
  failure; исходный предел router 150 строк сохранён.
- **Проверки:** RED воспроизведён (ZCode runtime отвергался, 3 regression failures);
  после обоих исправлений `python3 tests/validate.py` — PASS, 296 tests и shell
  adapter; LHC parity/validator и `zcode plugins validate plugins/last-human-commit`
  — PASS. Независимый Reviewer сначала потребовал сохранить длинный prompt и
  учесть `turnId`; после точечного исправления повторно дал `APPROVE`. Его замечание
  про ослабленный router line budget исправлено в этой PR: исходный лимит 150
  восстановлен, AGENTS/CLAUDE сокращены с 156 до 150 строк только удалением шести
  пустых строк; сравнение непустых строк подтвердило сохранение всех правил.
  Повторный полный запуск с лимитом 150: 296 passed; package sync/parity/validator,
  ZCode manifest validation и `git diff --check` — PASS.
- **Ограничение:** первый новый headless prompt `sess_1cc76e15-307b-4fdf-9b62-6376661e20c9`
  вызвал старый SessionStart hook и записал только `.tmp/zcode-native-red-20261019/`
  `.agents/shared-session/time/zcode-<session>.json`. Plugin отсутствовал в
  registry; model request завершился HTTP 429, затем только эта новая probe-сессия
  отменена. Ответ модели и file fix не получены; это не consumer acceptance.
- **Установка candidate:** штатный ZCode manager установил enabled 1.4.11 в
  `/home/roomhacker/.zcode/cli/plugins/cache/last-human-commit/last-human-commit/1.4.11`;
  backup конфигов лежит в `.tmp/zcode-native-install-backup-20261019/`. Новый prompt
  `sess_ccecf4f4-a01a-476c-8c79-f3ca7b503483` вызвал native `UserPromptSubmit`,
  `PreToolUse` и `PostToolUse`, state указывает runtime zcode и loaded 1.4.11.
  Его fixture пока не изменён, а процесс prompt ещё активен: это подтверждает
  установку/hook execution, не законченный пользовательский результат.
- **Codex/OpenCode baseline:** Codex native manager показывает enabled 1.4.10.
  OpenCode native loader ссылается на `last-human-commit-v1410.ts` и установленный
  runtime в `~/.local/share/last-human-commit/releases/1.4.10`; его manager list
  распознаёт plugin. Ни один из них ещё не обновлён или consumer-tested.
- **Следующий шаг:** закончить текущий изолированный ZCode prompt без остановки его
  процесса; затем довести свежую основную ветку/PR и штатные native updates для
  Codex/OpenCode/ZCode с backup затрагиваемых настроек. По каждому сохранить
  реально загруженную версию и отдельный обычный prompt без `@LHC`; не засчитывать
  hook execution как законченный моделью сценарий и не рестартовать активные сессии.
