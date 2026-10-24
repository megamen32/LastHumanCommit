# LHC Plan

План остаётся каталогом `leaves/*.json`. MCP — необязательный фасад над тем же
CLI; установленный пакет не обращается к исходному checkout.

```sh
python3 common/tools/lhc_plan_json.py build-plan /path/to/plan
python3 common/tools/lhc_plan_publish.py publish-html /path/to/plan --autopublish
python3 common/tools/lhc_plan_json.py progress /path/to/plan L01 --note 'Проверка идёт'
python3 common/tools/lhc_plan_publish.py revise /path/to/plan --reason 'Изменились зависимости'
python3 scripts/setup_mcp.py  # только показать регистрацию
python3 scripts/plan_mcp.py   # stdio initialize, tools/list, tools/call
```

Настройка `~/.config/lhc/publish.json`:

```json
{"webroot":"/var/www/lhc","base_url":"https://lhc.bezrabotnyi.com"}
```

Для SSH добавьте `ssh_host` с существующим alias. Доставка требует Python 3 на
обоих концах и права записи в webroot. Исходный r001 неизменяем, статусы и заметки
меняют только текущий факт. Публичная ссылка содержит 96 случайных бит; её
получатель может передать доступ. noindex не заменяет авторизацию. Публикуйте
только безопасные заметки и метаданные; не загружайте чужие/private планы.

Новые планы привязываются отдельным первым `publish-html --autopublish`. Затем
сборка/leaf-write hook обновляет страницу без MCP. Если native hooks глобально
выключены, используйте CLI. Ошибка доставки сохраняет последнюю исправную страницу.
Стоимость недоступна, если `lhc_models.py` не входит в установленный пакет.
