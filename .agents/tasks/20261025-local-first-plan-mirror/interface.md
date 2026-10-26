# Контракт размещения наблюдателя и зеркала

Исполняемый файл: `src/common/tools/lhc_plan_mirror.py` рядом с остальными `lhc_*.py` (stdlib Python 3.10+). Копировать весь каталог tools; загруженный код не исполняется.

Команды:

```
python3 lhc_plan_mirror.py serve --config ~/.config/lhc/plan-mirror/server.json
python3 lhc_plan_mirror.py watch --config ~/.config/lhc/plan-mirror/client.json
python3 lhc_plan_mirror.py once --config CLIENT
python3 lhc_plan_mirror.py register PLAN_DIR --config CLIENT
python3 lhc_plan_mirror.py status --config CLIENT
```

server.json: `{"listen":"127.0.0.1","port":8769,"data_dir":"/home/roomhacker/.local/share/lhc-plan-mirror/server","webroot":"/var/www/lhc","base_url":"https://lhc.bezrabotnyi.com","token_file":"PROTECTED_ABSOLUTE_PATH","dashboard_key_file":"PROTECTED_ABSOLUTE_PATH"}`. Два файла содержат разные случайные значения; режим 0600, не публиковать. Токен записи не используется в браузере. Ключ панели — capability, URL `/dashboard/KEY/`.

client.json: `{"mode":"mirror","endpoint":"http://127.0.0.1:8769","base_url":"https://lhc.bezrabotnyi.com","token_file":"PROTECTED_ABSOLUTE_PATH","data_dir":"/home/roomhacker/.local/share/lhc-plan-mirror/client","roots":[],"plans":["ABSOLUTE_PLAN_DIR"],"poll_seconds":1,"debounce_seconds":1,"timeout_seconds":3}`. На Mac endpoint — доступный HTTPS origin; nginx проксирует `/v1/` и `/dashboard/` на 8769. Не перехватывать текущие статические ссылки. ROOT нейтрален. `roots` — только явно выбранные каталоги планов: поиск `plan.json` максимум на 3 уровня вниз. `plans` — существующие явно привязанные планы. Никаких домашних каталогов/транскриптов.

API: `GET /health` без секретов; `POST /v1/snapshots` с Bearer из token_file, JSON ≤8 MiB; `GET /v1/status` с тем же Bearer. Тело снимка v1: schema_version, owner, project, name, identity, seq, last_file_event, document, revisions, observed. Идентификаторы URL наследуются из `.lhc-publication/state.json`. Снимки содержат только очищенные данные renderer, не HTML/пути/команды. seq монотонен для owner; другой owner на той же identity/URL — 409. Старый seq не откатывает состояние. Receipt содержит seq, received_at, url. Dashboard показывает факт последнего события файла и receipt отдельно; живость агента неизвестна.

Наблюдатель пишет только локальные `.lhc-publication/` и client data_dir. Сервер пишет только replica data_dir и webroot. CLI/MCP редактируют прежние локальные файлы. `register` и первое обнаружение сохраняют `.lhc-publication/mirror.json`: все последующие CLI/MCP build/publish/revise автоматически используют эту локальную привязку без env/--config и без сети. Новый план в roots/plans стандартного `~/.config/lhc/plan-mirror/client.json` тоже распознаётся до первого прохода observer. `LHC_PLAN_MIRROR_CONFIG=CLIENT` — необязательная замена пути config при первом обнаружении. `revise --reason ...` сохраняет ревизию локально даже без сервера.

Инфраструктурный исполнитель владеет units/nginx/LaunchAgent и hosting.md. Исходный исполнитель владеет этим контрактом и Python core. Установка runtime, остановка production и Mac consumer — у инфраструктурного исполнителя; исходный исполнитель предоставляет тестируемый core и disposable consumer.
