# Живая публикация плана

Исходное поручение: из назначенного дерева 1.5.48 реализовать CLI и необязательный
MCP для публикации HTML-плана по постоянной неперечисляемой ссылке. Листья остаются
источником истины; исходный план, факты и явные перепланирования различимы.
Границы: tools, tests, plan docs, package projections, plugins/lhc-plan.
Не менять deploy/live-plans, основной checkout, cost-first-plan-kernel и аккаунты.

## Исходный план реализации

1. Листья: атомарное create/update/progress с lock и expected hash; ISO timestamps,
   append-only events, явная либо надёжная native identity. Оценка 15 минут.
2. Сквозная публикация: freeze r001, явный revise, безопасный HTML поверх Gantt,
   локальная/SSH атомарная доставка и opt-in autopublish. Оценка 25 минут.
3. Тонкий совместимый MCP, package projection, focused regression tests.
   Оценка 15 минут.
4. Реальный безопасный план, CLI/stdIO/browser consumer, независимый read-only
   review и собственный commit/push. Оценка 15 минут.

Листья выполняются последовательно одним исполнителем. Активное время пока не измерено.
Рабочее решение: общий core без MCP. Идеал: богатая совместная панель событий.
Минимальный полезный вариант: статические снимки + лёгкий poller, без daemon/DB.

## CLI/config contract

`python3 src/common/tools/lhc_plan_json.py create-leaf PLAN ID --fields JSON`

`python3 src/common/tools/lhc_plan_json.py update-leaf PLAN ID --fields JSON [--expected-hash SHA256]`

`python3 src/common/tools/lhc_plan_json.py progress PLAN ID --note TEXT [--fields JSON]`

`python3 src/common/tools/lhc_plan_publish.py publish-html PLAN [--config FILE] [--autopublish]`

`python3 src/common/tools/lhc_plan_publish.py revise PLAN --reason TEXT`

Config: host-local `~/.config/lhc/publish.json`, object
`{"webroot":"/var/www/lhc","base_url":"https://lhc.bezrabotnyi.com"}`;
optional `ssh_host` is an existing SSH alias. No credentials stored here.
First publication binds `.lhc-publication/state.json` to project primary Git root
basename and `plan-YYYYMMDD-HHMM-<96 random bits>`. Private immutable revision
snapshots live under `.lhc-publication/revisions/`; public bundle contains only
safe metadata and HTML, no source paths or transcripts. Binding opts into future
build/leaf-hook publication only with `--autopublish`. Failures preserve last good
page and do not block leaf updates. Revision snapshots never update on status writes.

Acceptance: immutable r001 after progress/r002, dependency branches, midnight ISO,
unknown durations, concurrent updates, XSS/traversal, last-good failure, CLI/MCP
parity and live/offline browser behavior. Main merge/version/release belongs to Lead.

## Plan

Цель: Открывать постоянную ссылку на телефоне и видеть исходный план, фактическую работу и перепланирования.
Бизнес-результат: Реальная HTTPS-страница работает; CLI, переносимый stdio MCP, SSH и main 1.5.49 проверены. Native autoload в пользовательских harness не заявляется.
Декомпозиция: 4 листа · 1 параллельно · 4 волны · слотов: 1

✅ (Атомарные листья и история прогресса) начало не зафиксировано, завершена 16:47, оценка 15 минут, факт не измерено
✅ (Снимки ревизий, сравнение и атомарная публикация) начало не зафиксировано, завершена 16:54, оценка 25 минут, факт не измерено
✅ (MCP-фасад, переносимый пакет и регрессии) начало не зафиксировано, завершена 16:55, оценка 15 минут, факт не измерено
✅ (Живая проверка, независимый review и передача исходников) начало не зафиксировано, завершение подтверждено публикацией main, оценка 15 минут, факт не измерено

## Уточнение мандата и checkpoint

На 16:56 получен расширенный мандат координатора: выпустить 1.5.49, добавить
lhc-plan в marketplaces, включить переданные nginx.conf/README без изменения,
push своей ветки и fast-forward remote main без force. Основной checkout не
редактировать. f216a2a — отдельный commit владельца host persistence, уже в ветке.
Это продолжение исходного результата, не отдельный roadmap.

Точное активное время не измерялось; wall clock от первого осмотра примерно
35 минут к 16:56. Первоначальные оценки 15/25/15/15 сохранены. Дополнительные
исследования прекращены; маршрут остаётся CLI → статический сайт → canary.
Независимый read-only reviewer закончил: фильтр history и hash race исправлены.
Реальные проверки и ограничения — в result.md. Нативные user config/cache не менялись.
