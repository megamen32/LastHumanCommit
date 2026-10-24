# Результат живой публикации LHC

Реальный план задачи:
https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261024-1634-01a6b48557d3f9ab9694c3b0/

Исходные оценки 15/25/15/15 зафиксированы в r001. Историческое активное время
не измерялось и не восстановлено из mtime. Первая фиксация выполнена уже после
начала исходников; это явно указано в исходном плане, а не выдано за начальную
фиксацию до разработки.

## Доказательства

- Local CLI публикует в выданный webroot; HTTPS current/r001 отвечают 200,
  Cache-Control no-store. Исходный план и текущие статусы различимы.
- Chrome через AgentBrowser открыл реальную HTTPS-страницу. После CLI progress
  появился текст «Публичная страница открыта через HTTPS в Chrome» без open/reload.
  Затем проверена следующая заметка о CLI/SSH: note=true, scroll=700 после
  автоматической смены страницы, updated_at=2026-10-24T13:54:27+00:00.
- Mobile через собственную native CLI browser-session: реальный URL открыт,
  innerWidth=390, document.scrollWidth=390, compare-scroll.clientWidth=320,
  table.scrollWidth=768 (локальная горизонтальная прокрутка таблицы).
  Настройка viewport сама по себе не использовалась как PASS.
- Нажата реальная ссылка r001, URL оканчивается /r001.html, live poller=false.
  Тот же HTML открыт file://: rows=4, badge=«Снимок / офлайн», poller=false.
- Синтетический публичный r002, отделённый от реального плана:
  https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261024-1651-287d57e9d0f44d67918f4492/
  r001 до/после progress и r002:
  `45e61541def5b515902163e8253defa1b67d3d9beef6dd9f76fca922af4eb862`.
- Собственный переносимый пакет на MacBook-Pro-User.local запущен вне checkout,
  из /tmp/lhc-plan-20261024-core. Через существующий publish.json/SSH он создал
  https://lhc.bezrabotnyi.com/lhc-portable-canary/plan-20261024-1652-fc5e933778d2fa57ae928f57/ .
  r001 SHA `ad76acbb8743a4bec153b64e51e5bfa0f50ec2c71d54bcf1bf84cfeb628fd0a7`
  неизменен после progress/r002. Реальный stdio initialize/list/call прошёл,
  publish_html CLI/MCP output равны; зависимости от source checkout нет.
- Независимый Lead повторил текущий пакет в своём уникальном Mac fixture:
  https://lhc.bezrabotnyi.com/lhc-portable-canary/plan-20261024-1658-52847f923f11a52f2c8cc676/ .
  По переданному им receipt (не собственный запуск Worker): 7 секунд,
  r001 SHA `9c0b161767d1c22e668670cd814bb82e0f1ff086401a79519729c73b3bff81c7`
  неизменен; stdio initialize/list/call и CLI/MCP parity прошли.
  Receipt: /Users/user/.tmp/lhc-publish-mac.GSlEq6/result.json.

## Исходники и пакет

Core: src/common/tools/lhc_plan_json.py, lhc_plan_publish.py,
lhc_plan_transport.py. Optional stdio: lhc_plan_mcp.py, plugins/lhc-plan.
Пакеты генерируются scripts/publish_package.py и sync_skills.py; 1.5.49,
marketplaces показывают lhc-plan отдельно, без обязательного включения MCP.

Целевые тесты покрывают immutable r001, статус без ревизии, r002, удаление
листа после наблюдённого actual20, reset с сохранением завершённого факта,
ветвление с несколькими родителями, concurrent updates, optimistic conflict,
ISO через полночь/дни, неизвестное время, umask077, bounded generations,
last-good при malformed leaf, XSS/секретные поля/path traversal/collision,
CLI/MCP и отдельный portable stdio. Итог проверки записывается ниже после
финального запуска validators/tests.

Финальный focused run: **88 passed in 3.13s**. Marketplace validator: PASS,
4 entries. check-plan: OK, 4 листа и статусы совпадают с progress.md.
sync_skills --check: 25 skills, parity PASS; publish_package --check: проекции
совпадают. Первый вызов package validator ошибочно получил --source-root .;
Вызов с src/common/skills сравнивал ещё не преобразованные model-routing пути;
штатный validator без --source-root прошёл: skills=25, canonical=PASS,
parity=PASS (25 skills). Это штатное преобразование исходников, не дефект.

## Практическое использование

```sh
python3 src/common/tools/lhc_plan_publish.py publish-html PLAN --autopublish
python3 src/common/tools/lhc_plan_json.py progress PLAN L01 --note 'Проверка идёт'
python3 src/common/tools/lhc_plan_publish.py revise PLAN --reason 'Изменились зависимости'
```

Ограничения: ссылка передаёт доступ, noindex не является аутентификацией.
Новые планы требуют первого publish-html --autopublish по обновлённому workflow;
старые unbound планы не загружаются. На выключенных native hooks используйте CLI.
Установленный пользовательский native plugin/cache этой сессией не обновлялся;
проверены переносимый пакет и native CLI, а не автозагрузка новой версии во всех
живых harness-сессиях. estimate_cost явно unavailable без models CLI.

## Опубликованный результат

LHC 1.5.49: feature commit **ad1390727947c892084c8ba3b04d1eb10838a72f**.
Push своей ветки и fast-forward remote main завершились успешно; независимый
Lead readback подтвердил обе ссылки на этот SHA. Основной checkout не менялся.
Включён ранее переданный hosting commit f216a2a и nginx/README владельца без
изменения. Код, план и разрешённый hosting source опубликованы; host работает.
Native plugin manager installation/autoload не выполнялись: bare native
manifest может не активировать mcp.json автоматически, это не заявляется как PASS.
Подтверждён только фактический переносимый raw stdio transport и тот же CLI.

Исходный реальный r001 HTML остаётся byte-identical:
`bf3dd25661f3121acbf290a65769354891d7c09d8fc4a7d31c6b4b05e6870da0`.
Текущий бизнес-результат и L04 обновлены после remote publication; исходная
ревизия и исходные оценки не переписаны. Дополнительного replan не было.
