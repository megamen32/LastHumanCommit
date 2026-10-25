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
