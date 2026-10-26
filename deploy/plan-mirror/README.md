# Установленный локальный наблюдатель LHC

`install-native.py` устанавливает выделенный stdlib Python runtime по хешу
всех Python-файлов tools. Systemd/LaunchAgent запускают конкретный неизменяемый
каталог release; `current` служит удобной ссылкой для CLI. Сервер разрешён
только на Linux server100. Копировать весь tools, не один entrypoint.

Повторная установка дополняет точные `plans`, `roots` и `graph_sources`,
сохраняет прежние пути, секретные ссылки и остальные поля конфигурации.
Добавленные пути сравниваются как точные значения. `--sso-enabled` действует
только вместе с `--server` и закрывает существующим SSO только точный `/`.
Плановые HTML, JSON, архивы и capability URL остаются доступны без SSO;
`/v1/snapshots` и `/v1/status` по-прежнему требуют Bearer.

На server100:

```sh
python3 deploy/plan-mirror/install-native.py --tools src/common/tools --server \
  --endpoint http://127.0.0.1:8769 --sso-enabled \
  --root /ABSOLUTE/SELECTED-PLAN-DIRECTORY \
  --graph-source /ABSOLUTE/LEGACY-TASK/plan.graph.json
```

`--prepare-only` создаёт только конфигурацию, не службы. Выбирай исходные
plan_dir/graphs, а не копии из worktree текущей поставки. Существующий
`.lhc-publication/state.json` должен оставаться в своём каталоге.

На Mac скопировать выбранный tools и installer в выделенный staging. Существующий
`write-token` остаётся на месте и сохраняется; не переносить и не печатать его.

```sh
/opt/homebrew/bin/python3 ~/.local/share/lhc-plan-mirror/staging/install-native.py \
  --tools ~/.local/share/lhc-plan-mirror/staging/tools \
  --root /Users/user/Documents/Apps \
  --root /Users/user/Documents/Apps/.agents/tasks
```

`mac-consumer.py` меняет только отдельный синтетический fixture. `raw-edit`
проверяет обычное сохранение, `verify` проверяет marker на реальной HTTPS-странице.
`offline-revise` уже выполнен один раз; не повторять принятую ревизию ради отчёта.

`sso-nginx.conf` — текущий root-only SSO payload LHC vhost. Управляемый источник:
`/home/roomhacker/nginx-dev/state/files/sites-available/lhc.bezrabotnyi.com`.
После поддерживаемых refresh/check используется только
`sudo nginxctl apply --site lhc.bezrabotnyi.com`. Общий apply запрещён этим scope.
Старый `nginx.conf` сохранён как исторический payload и применять его нельзя.
Capability не записывается в access log.

Проверять только systemd ActiveState/SubState/MainPID и launchctl state/pid/exit.
Полный `launchctl print` содержит посторонние секреты окружения и недопустим.
Приватная ссылка хранится только в защищённом `dashboard-url` server100;
передаётся владельцу напрямую, не в Git/плане/скриншоте/квитанции.

Откат: выбрать предыдущий release, повторно установить units с его tools,
сохранив config/данные. Для полного отключения — остановить только две Linux
службы и Mac `com.lhc.plan-observer`. Старые HTML не удалять. Откат nginx —
только предыдущий LHC payload через тот же scoped apply; общий rollback не нужен.
