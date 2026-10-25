# Единый LhcPlan MCP — 1.5.58

До изменения стандартный scripts/plan_mcp.py предоставлял четыре инструмента
и сам записывал листы. Отдельная реализация, запускаемая plan_publish_mcp.py,
предоставляла семь. Это две реализации, а не два подтверждённых работающих сервиса.

Теперь оба входа используют src/common/tools/lhc_plan_mcp.py. Стандартный вход
предоставляет create_leaf, update_leaf, update_progress, build_plan, estimate_cost,
publish_html, revise_plan. Изменения листов выполняет канонический CLI:
атомарность, created_at, plan_origin, история и проверка expected_hash сохранены.
Старые аргументы, Python call shim, локальные файлы и офлайн-зеркало поддерживаются.
Portable mcp.json использует AgentPlugins 1.0 schema, stdio и PLUGIN_ROOT;
нативные compatibility descriptors сохраняют свой формат и одно имя LhcPlan.

Проверено исполнителем:

- 70 passed: tests/test_lhc_plan_mcp.py, tests/test_single_plan_mcp.py,
  tests/test_plan_publish.py, tests/test_plan_mirror.py.
- После найденной Lead несовместимости внутреннего тестового API:
  tests/test_plan_origin.py переведён с удалённого command() на публичный
  handle/tools-call с сохранением проверок created_at и plan_origin; 9 passed.
  Генерация, parity, валидатор пакета и diff --check повторно PASS.
- Сохранены проверки ошибок/отказов и регистрации; добавлены CLI equivalence,
  семь инструментов из standalone root/native пакетов, восстановление JSON-RPC,
  отсутствие записи при невалидном обновлении и устаревшем хеше.
- sync_skills.py --check: PASS; scripts/publish_package.py --check: PASS;
  scripts/validate.py внутри пакета: PASS; git diff --check: PASS.

Независимые доказательства, переданные Lead в этой сессии:

- .tmp/lead-single-mcp-consumer.py: пакет вне checkout, изолированный HOME,
  все семь инструментов, bundled CLI paths и совместимый launcher; created_at,
  plan_origin, три события истории, stale-hash отказ без записи, malformed args
  затем ping; r001 неизменна после r002. Недоступное зеркало 127.0.0.1:9:
  publish_html локально поставлен в очередь за 0.247 с.
- Изолированный native manager: установка 1.5.58 из repository marketplace,
  codex mcp list --json показывает ровно один LhcPlan.
  Профиль: /tmp/lhc-one-mcp-native-efvlg2za; глобальный профиль не менялся.

Границы: выполнены только source/docs/package projections и локальные тесты.
Установленные профили, отключённые hooks, credentials и сервисы не изменялись.
Публикация main и обновление активного fleet-lhc принадлежат Lead.
Самостоятельной проверки реального сайта в этой задаче нет.
