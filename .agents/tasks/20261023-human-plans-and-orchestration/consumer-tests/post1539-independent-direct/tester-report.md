# Отчёт независимого тестировщика

## Цель и границы

Проверить установленный LHC workflow на обычной просьбе подготовить две памятки: основную заметку силами обычного Worker и отдельный чеклист силами максимум одного Child, которого Worker обязан создать. Lead не должен писать ни одну памятку; Child не должен делегировать. Разрешённая папка: `consumer-tests/post1539-independent-direct/`.

## Наблюдаемое дерево

- Tester: `/root/lhc_independent_workflow_tester_direct` (текущая сессия).
- Lead: `/root/lhc_independent_workflow_tester_direct/lhc_direct_consumer_lead`, создан прямым `collaboration.spawn_agent`, `fork_turns:none`, модель `gpt-6-luna`.
- Worker: `/root/lhc_independent_workflow_tester_direct/lhc_direct_consumer_lead/worker_note`, создан Lead напрямую.
- Child: `/root/lhc_independent_workflow_tester_direct/lhc_direct_consumer_lead/worker_note/child_checklist`, создан Worker после одного разрешённого retry.
- Отдельные внутренние числовые/UUID agent IDs native tree не показал; перечислены наблюдаемые прямые agent paths.

## Handoff и факты

Lead передал Worker: «Твоя исключительная область — создать/редактировать только файл `.../worker-note.md`. Не редактируй другие файлы. Я прямо делегирую тебе право создать максимум одного Child исключительно для `child-checklist.md`… Ты обязан использовать это право… Ты также не делегируй больше никому».

Lead также включил границы, факты и критерии приёмки. Worker получил именно проверенные факты из задания: подтверждённая проблема отличается от неизвестного статуса; неизвестный результат нельзя считать успешным, `PASS` или завершённым. В первой попытке Worker сообщил Lead точную причину spawn-отказа. Во второй попытке Worker передал Child только эти факты и критерии для отдельного чеклиста.

После того как слоты освободились, Tester через `collaboration.followup_task` дал существующему Worker указание выполнить ровно один retry в рамках прежнего гранта. Worker сообщил, что создал единственного Child с исключительной областью `child-checklist.md`, зависимостью от `worker-note.md`, ограничением фактов, acceptance и запретом дальнейшей делегации. Child завершился, не создавая потомков.

## Результаты

- `worker-note.md` создан Worker в его исключительной области и прочитан Tester. Текст простой и понятный по-русски; различает подтверждённую проблему и неизвестный статус, запрещает считать неизвестное успехом/PASS/завершением. Файл читаемый.
- Первая попытка Worker → Child завершилась `agent thread limit reached`; Lead подтвердил, что повторная проверка тогда не обнаружила свободного слота. Это не был отказ Worker по собственной инициативе.
- Единственный разрешённый retry после освобождения слотов успешен: Worker создал Child; Child создал `child-checklist.md` в своей исключительной области. Tester прочитал файл: простой русский, четыре коротких шага, различает «подтверждённая проблема» и «неизвестно», запрещает отмечать неизвестное как успех/PASS/завершение и требует подтверждения свидетельствами. Чеклист читаемый и соответствует acceptance.
- Lead не писал памятки. Никакие файлы вне этой папки не проверялись или изменялись этим тестом.
- Первая попытка Lead → Worker успешна. Для Worker → Child сохранены и исходный отказ, и единственный успешный retry.

## Доказательство установленного entrypoint

Тест запущен из нормального Codex native session context в проекте `LastHumanCommit`; supplied source/plugin path не использовался. Последующий read-only live readback выполнен native Codex plugin manager командами `codex plugin list --json` и `codex plugin marketplace list --json`.

- Активная запись: `pluginId=last-human-commit@megamen32-plugins`, `version=1.5.39`, `installed=true`, `enabled=true`.
- Установленный source path, показанный manager: `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/native/codex`.
- Marketplace source root: `https://github.com/megamen32/LastHumanCommit.git`.
- Marketplace cache root из `marketplace list`: `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins`; package root: `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit`.
- Второй экземпляр `last-human-commit@fleet-lhc` установлен как `1.5.36`, `enabled=false`; его manager-reported marketplace root: `/home/roomhacker/.local/share/agent-harness-fleet/plugin-rollout/marketplaces/codex-fleet-lhc`.
- SHA-256 manifest `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/plugin.json`: `c8ca15284e645cf9a7dd08066c516693223b180f6ddd66226b219b12dc93e136`.
- SHA-256 skill package copy `.../plugins/last-human-commit/skills/model-routing/SKILL.md`: `5b637e195f090d616ed31377d66dfb000d7b2968c479b6f0523c37224d42473e`.
- SHA-256 native Codex copy `.../plugins/last-human-commit/native/codex/skills/model-routing/SKILL.md`: тот же `5b637e195f090d616ed31377d66dfb000d7b2968c479b6f0523c37224d42473e`.
- Marketplace source URL, installed marketplace cache root, package root и installed source path приведены отдельно; это разные уровни. Plugin manager readback подтверждает установленную/enabled запись, но не сообщает exact per-session loaded entrypoint path. Поэтому session-loaded path остаётся **UNKNOWN**; установленную запись нельзя использовать как доказательство того, какой файл уже загрузила эта сессия.

## Итог

Результат по содержанию и делегированию принят: обычный Worker подготовил основную заметку, затем после временного ограничения слотов использовал ранее выданное разрешение для одного Child; Child создал отдельный приемлемый чеклист и не делегировал дальше. Происхождение установленного entrypoint осталось UNKNOWN.
