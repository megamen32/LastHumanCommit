# READY — исходники корневого каталога, версия 1.5.59

Владелец доставки: Codex Luna `01a1744b-71ee-70e0-a4ef-06d54c6aac70`.
Worktree: `/home/roomhacker/agents-projects/LastHumanCommit/.worktrees/plan-home-sso-20261025`.
Ветка: `lhc/plan-home-sso-20261025`, исходная база `a886c1e` (1.5.58).

## Готово в исходниках

- `/` показывает «Проекты и планы» при `sso_enabled: true`, loopback TCP peer и
  единственном `X-LHC-SSO-Verified: 1`. Без SSO корень закрыт. Старый capability
  в SSO режиме имеет ту же защиту; в прежних установках работает как раньше.
- Все принятые снимки группируются по стабильному `snapshot.project`, сортируются
  по исходному событию. Есть счётчики, статусы, поиск проекта/плана, все/в работе,
  мобильная раскладка, ссылка на текущий план и ревизию. Примечания листов на
  обзор не попадают. Живость агента явно неизвестна.
- Обновление каждые 12 секунд сохраняет поиск, фильтр и позицию. Истёкший вход,
  redirect, 401/403 или HTML входа сохраняют данные и предлагают войти снова.
- `graph_sources` читает явно заданные абсолютные plan.graph.json тем же
  наблюдателем, без записи в граф и без создания листов. Sidecar с историей
  рядом с графом; исходные временные поля/неизвестные actuals сохранены.
  Дубли разрешённого пути объединяются; проект определяется по Git root.
- Повреждение/удаление графа не заменяет последний хороший снимок. Исправлен
  проверенный дефект: успешная пересылка старого снимка больше не стирает ошибку
  нового повреждённого источника во время retry capture.
- Bearer API независим от SSO; observer/offline/revisions используют прежний путь.
- Обновлены manifests/MCP version до 1.5.59, проекции получены генераторами.

## Проверено

`LHC_UI_BROWSER_TESTS=1 python3 -m pytest -q tests/test_plugin_version_parity.py tests/test_plan_home.py tests/test_plan_graph_sources.py tests/test_plan_mirror.py`

20 passed, включая настоящий изолированный Chrome: 36 планов / 12 проектов,
поиск/фильтр, мобильная ширина, настоящее fetch-обновление, истечение SSO.
HTTP-тесты проверяют root/capability/proxy-header/peer и Bearer read/write.
Graph-тест проходит offline → restart → raw edit → malformed → missing → recovery,
проверяя неизменность исходных байтов, стабильный URL и baseline.

`python3 -m pytest -q tests/test_plan_origin.py tests/test_single_plan_mcp.py tests/test_plan_dashboard_ui.py`

23 passed: прежние origin, единый MCP и интерфейс плана сохранены.

`python3 plugins/last-human-commit/scripts/sync_skills.py --check`,
`python3 scripts/publish_package.py --check`,
`python3 plugins/last-human-commit/scripts/validate.py` — PASS.
Полный suite намеренно не запускался; native consumer и SSO live здесь не проверялись.

## Точный следующий шаг Luna / hosting

1. Сохранить существующий runtime client/server config при установке;
   hosting владеет install-native.py (preserve-config/sso flags), sso*, hosting.md.
2. Установить source runtime из этой ветки, включить server `sso_enabled: true`,
   nginx должен перезаписать заголовок после existing personal SSO auth_request.
   Защитить все браузерные пути, включая JSON/архивы и capability. Контракт — interface.md.
3. Добавить собранные Lead canonical roots/plans и legacy graph_sources в существующий
   client config. Каталог показывает только реально принятые зеркалом источники;
   фактический инвентарь всего флота этим source receipt не доказан.
4. Проверить установленный корень через SSO, закрытый внешний доступ и синхронизацию
   без браузерного входа. Интеграция/push/release остаются у Luna.

В worktree появились чужие hosting-файлы (например deploy/plan-mirror/sso-nginx.conf);
они не входят в source commit. Primary checkout не изменялся. Новые исполнители
не создавались, runtime не перезапускался, main не публиковался.

## Проверенный итог Luna — 1.5.61, 25.10.2026

- Актуальный пользовательский контракт: SSO требуется только для точного `/`;
  individual plan HTML/JSON/archive и capability URL не закрываются SSO.
  `/v1/status` остаётся Bearer API. Анонимный `/` уходит на точный existing
  auth `rd`; проверенная страница плана отвечает 200. Положительный owner-login
  не наблюдался, cookies не извлекались.
- После bounded source inventory зеркало содержит 22 плана в 10 группах.
  Server100 mirror/observer и Mac observer установлены как 1.5.61; server
  слушает loopback, `sso_enabled=true`. Текущие plans/roots/8 graph sources,
  Mac Apps root и 2 Mac graph sources сохранены. Mac write-token не копировался.
- UI теперь имеет один длинный цветной status bar; min/max/сейчас и временной
  результат находятся в той же карточке без второй длинной оси/точки. Проверено
  на опубликованной странице в headless Chrome при ширине 320 px и времени
  23:45 между границами 23:29 и 00:24: status «Ранняя оценка пройдена на
  15мин · до верхней границы 40мин», все labels помещаются.
- По SHA-256 сравнены прежние 31 сохранённые generation paths: это 16 уникальных
  plan identities; все 16 текущих `r001.html` совпадают байт-в-байт.
- В эту задачу добавлен собственный canonical live LHC plan, привязанный к
  текущей session/worktree. L03 lifecycle-поведение проверено на изолированной
  копии canonical Cloud Telethon 13-leaf `docs/tasks` плана с установленным
  runtime 1.5.61 и текущим Luna session id: точная регистрация при пустом
  `roots`, running/session/progress event, offline raw save, catch-up по тому же
  URL и неизменный `r001`.
- Реальную Cloud Telethon рабочую копию не изменяли. В ней при последнем чтении
  L03 уже имел status `done`; это состояние не приписывается нашему canary.
  Изолированный canary доказывает безопасный consumer-путь, но не выдаётся за
  вмешательство в ту сессию. Старый capability не открывали и секрет не читали.
- `LHC_UI_BROWSER_TESTS=1 python3 -m pytest -q tests/test_plan_time_rail.py
  tests/test_plan_mirror.py` — 25 passed; `test_plugin_version_parity.py` —
  4 passed; `plugins/last-human-commit/scripts/validate.py`,
  `publish_package.py --check` и `sync_skills.py --check` прошли.

Следующий/оставшийся шаг: scoped commit/push LHC branch и integrated readback.
Managed nginx site-scoped apply уже действует; дальнейшая публикация managed
source должна исключить несвязанный локальный `ServersAdministartion` commit.

## Исправление входа fullcycle — 1.5.62 (в работе)

Причина: существующий Codex `UserPromptSubmit` lifecycle не запускал LHC entry
для создания/привязки локального плана; активация была только ручным CLI
действием. Поэтому обычный старт зависел от того, вспомнит ли модель команду.

Исправление в исходнике: Codex hook теперь вызывает локальный `lhc_entry.py`
перед ответом модели. Для fullcycle он в пределах текущего Git worktree
переиспользует точный подходящий план/готовый leaf либо создаёт локальный
scaffold из трёх листов, связывает первый с реальным session ID, создаёт graph
и HTML. Если конфигурации mirror нет, локальные файлы всё равно создаются и
работа начинается; MCP и сеть не вызываются. Повтор того же события не пишет
дублирующий progress event.

Проверено: `tests/test_native_instruction_hooks.py`,
`tests/test_plan_mirror.py` и `tests/test_plan_mirror_installer.py` — 38 passed.
Тест вызывает штатную ветку CLI
`--event UserPromptSubmit --plan-entry` на изолированном Git worktree без
mirror config, проверяет три листа, running/session binding, graph/HTML и
идемпотентный повтор. Plugin validation, generated package parity и sync skills
прошли.

### Доставка и установленный consumer

- Scoped commit `2de7edf` опубликован в `lhc/plan-home-sso-20261025`; после
  повторного fetch `origin/main` оставался его предком и был продвинут обычным
  fast-forward, без force. Main и назначенная ветка сейчас указывают на один SHA.
- Codex marketplace `megamen32-plugins` обновлён; native plugin
  `last-human-commit` 1.5.62 установлен. В установленной копии подтверждены
  version 1.5.62 и `UserPromptSubmit --plan-entry` hook.
- Установленный CLI вызван с синтетическим fullcycle event внутри disposable
  Git repo: созданы три leaves, L01 стал `running` с переданным synthetic
  session ID, graph/HTML собрались; использованные config path не существовал,
  MCP и сеть не вызывались. Temp repo удалён.
- Server100 и Mac mirror/observer runtime 1.5.62 активны. Config readback:
  server `sso_enabled=true`, loopback:8769, сохранены 2 plans/4 roots/8 graphs;
  Mac observer активен, сохранены 1 plan/3 roots/2 graphs.
- После install публичный корень вернул `302` с точным существующим
  `rd=https://lhc.bezrabotnyi.com/`; индивидуальный план вернул `200`.
- Последний fetch прежней страницы собственного live plan вернул `200` и
  отобразил завершённый delivery leaf и auto-entry leaf; адрес mirror не
  записывается в исходники.
- Настоящая новая Codex-сессия не запускалась по прямому указанию пользователя;
  owner login также не наблюдался. Поэтому подтверждены установка и synthetic
  installed-hook consumer, но не факт будущего user session invocation и не
  authenticated owner UI.
