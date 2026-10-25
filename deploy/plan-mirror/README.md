# Установленный локальный наблюдатель LHC

`install-native.py` устанавливает выделенный stdlib Python runtime по хешу
всех Python-файлов tools. Systemd/LaunchAgent запускают конкретный неизменяемый
каталог release; `current` служит удобной ссылкой для CLI. Сервер разрешён
только на Linux server100. Копировать весь tools, не один entrypoint.

На server100:

```sh
python3 deploy/plan-mirror/install-native.py --tools src/common/tools --server \
  --endpoint http://127.0.0.1:8769 \
  --plan /ABSOLUTE/CURRENT-TASK \
  --plan /ABSOLUTE/ORIGINAL-PUBLISHED-PLAN \
  --root /home/roomhacker/.local/share/lhc-plan-mirror/plans
```

Повторная установка сохраняет токен и ключ панели; список plans/roots заменяется
явно переданным списком. `--prepare-only` создаёт только конфигурацию, не службы.
Перед обновлением проверить, что выбран оригинальный plan_dir с прежним
`.lhc-publication/state.json`, а не его tracked-копия из другого worktree.

На Mac скопировать выбранный tools и installer в выделенный staging, передать
существующий write-token прямым SCP в `~/.config/lhc/plan-mirror/write-token`.
Значения не печатать. Выполнить:

```sh
/opt/homebrew/bin/python3 ~/.local/share/lhc-plan-mirror/staging/install-native.py \
  --tools ~/.local/share/lhc-plan-mirror/staging/tools \
  --plan /Users/user/.local/share/lhc-plan-mirror/consumer-plan \
  --root /Users/user/.local/share/lhc-plan-mirror/plans
```

`mac-consumer.py` меняет только отдельный синтетический fixture. `raw-edit`
проверяет обычное сохранение, `verify` проверяет marker на реальной HTTPS-странице.
`offline-revise` уже выполнен один раз; не повторять принятую ревизию ради отчёта.

`nginx.conf` — точный payload установленного LHC vhost. Управляемый источник:
`/home/roomhacker/nginx-dev/state/files/sites-available/lhc.bezrabotnyi.com`.
После поддерживаемых refresh/check используется только
`sudo nginxctl apply --site lhc.bezrabotnyi.com`. Общий apply запрещён этим scope.
API `/v1/` и приватная `/dashboard/REDACTED/` направлены на 127.0.0.1:8769;
остальные планы nginx обслуживает напрямую даже при выключенном сервере.
Capability не записывается в access log.

Проверять только systemd ActiveState/SubState/MainPID и launchctl state/pid/exit.
Полный `launchctl print` содержит посторонние секреты окружения и недопустим.
Приватная ссылка хранится только в защищённом `dashboard-url` server100;
передаётся владельцу напрямую, не в Git/плане/скриншоте/квитанции.

Откат: выбрать предыдущий release, повторно установить units с его tools,
сохранив config/данные. Для полного отключения — остановить только две Linux
службы и Mac `com.lhc.plan-observer`. Старые HTML не удалять. Откат nginx —
только предыдущий LHC payload через тот же scoped apply; общий rollback не нужен.
