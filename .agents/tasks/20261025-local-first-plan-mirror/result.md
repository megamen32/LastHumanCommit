# Результат: локальные планы с автоматическим зеркалом, LHC 1.5.53

Обычное сохранение `plan.json` или `leaves/*.json` автоматически появляется на
сайте. Источник истины и история остаются локальными. Агенту не нужны publish,
переменные окружения, MCP, SSH или доступный сервер для записи листа.

## Реализовано и проверено в исходниках

- Один stdlib core `src/common/tools/lhc_plan_mirror.py`: роли serve/watch,
  локальные register/status и одноразовый проход once. Узкий configured scope,
  автоматическое обнаружение новых планов, hash/debounce, retry с backoff,
  один durable latest snapshot на план с полной локальной историей.
- Локальная привязка переключает прежние CLI/MCP publish/revise на offline
  путь. Ошибка bookkeeping не превращает успешную запись листа в отказ API.
  Регистрация выключает legacy `state.autopublish`; настоящий publisher
  1.5.52 из 223ea5c проверен с отсутствующим legacy config и запрещёнными
  transport: automatic вернул None, конфигурацию и сеть не трогал.
- Сервер принимает ограниченный очищенный JSON с Bearer auth; входные HTML,
  пути и команды не исполняются. Проверяются owner/URL, seq, immutable revisions
  и сохранение observed completed facts. Seq фиксируется до отрисовки;
  interruption восстанавливается повтором того же запроса без отката replica.
  Одинаковый seq не запускает renderer при существующем готовом output.
- Прежние URL и r001 HTML сохраняются. Пустой сервер восстанавливается из
  локального снимка вместе с ревизиями и удалёнными/завершёнными фактами.
- Приватная панель: мобильная вёрстка, недавние планы, фильтр работающих,
  обновление списка, отдельные file event/receipt и неизвестная живость агента.
  Контакт без изменения файла не обновляет file event. Последняя успешная
  синхронизация хранится локально; сервер прямо показывает её как неизвестную.
- Пакет и все native проекции с manifests 1.5.53 сгенерированы штатными
  publish_package/sync_skills. Конвенции AgentPlugins 1.0 и отключённые hooks
  не менялись; standalone renderer/legacy publisher для unbound планов сохранены.

## Доказательства

1. Source Worker: 123 целевых регрессии планов, CLI/MCP, publisher и пакета
   прошли. После последнего delta — 9 mirror тестов прошли за 5.33 секунды.
   В их числе настоящий observer subprocess + HTTP: raw save без publish,
   промежуточный битый JSON/зависимые saves, offline local revise, рестарт,
   catchup, пустая replica, owner/replay/history conflicts, malformed HTTP,
   native MCP file parity, bookkeeping failure и interrupted renderer.
2. Source Worker: обычным сохранением L04 добавлена фраза «Обычное сохранение
   проверяется через установленный наблюдатель». Затем отдельный HTTPS GET200
   нашёл её в HTML; local seq2 = server receipt2, received_at
   2026-10-25T11:25:09Z, error=null. Ни build, ни publish между save/read не было.
   URL: https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261025-1418-1a13acb09c4a962db06a23ce/
3. Независимый Lead: новый план создан только обычными Python JSON saves
   внутри configured roots; без register/publish/build. Он обнаружен, вторая
   raw note отрисована по URL:
   https://lhc.bezrabotnyi.com/lead-raw-check-20261025/plan-20261025-1424-058b7348936339dfcf295c64/
   r001 SHA256: 79e705840c63e3ae4cde8e0160fde03426aa331ed462f2bc4db8972fc657d762.
4. Независимый Lead: реальная приватная HTTPS-панель открыта в отдельном
   Chrome без inherited secrets. На ширинах390/1280 scrollWidth совпал с
   viewport; пять cards, active-only toggle работает; через12 секунд badge
   подтвердил обновление, ошибок JavaScript0. Script: `.tmp/lead-dashboard-check.mjs`
   в workspace Lead. Capability не записана в этот документ/Git.
5. Hosting Worker: настоящий сервер остановлен один раз; Mac raw edit и revise
   без env завершились rc0 за0.131s, локально2 ревизии. Статика200, API502.
   После восстановления marker появился, local seq3 = receipt3. Принятая
   ревизия не повторялась. Затем на обновлённом runtime выполнен отдельный
   Mac raw save MAC-153-20261025-1131: HTTPS marker найден, seq6=receipt6,
   revision_count2. Это отдельные доказательства hosting, не тесты source Worker.
   Полные безопасные ссылки, runtime readback и ограничения — в hosting.md.

## Проверки и границы

Plugin validator PASS (25 skills), sync_skills --check PASS,
publish_package --check PASS; git diff --check без ошибок.
`tests/validate.py` неожиданно запускает всю suite: этот лишний запуск остановлен
после764 passed; полный suite PASS не заявляется. Целевые проверки выше завершены.

Единственный разрешённый read-only reviewer подтвердил временный capture retry
дефект; исправлен, добавлена регрессия без нового file save/restart.
Других reviewers, council, новых planner/framework/DB или двустороннего sync нет.

Конфигурация и private dashboard URL передаются через защищённые references
из hosting.md; публичного enumerable index нет. Runtime binding/outbox и
локальные authoritative revision files сохранены на исходных хостах и не
включены в публичный Git. Документированная hosting диагностическая экспозиция
двух чужих токенов описана отдельно без значений; ротация не входила в эту
область, поэтому она не заявляется выполненной.

Финальный runtime обоих хостов: `0fc5ed06dfa31a30`, полный tools digest
`0fc5ed06dfa31a30ff93a58647a638f2ab2810f56590792598ba882ee982d6d6`.
SHA256 lhc_plan_mirror.py:
`926be5b5c6fd545206d1b0d53fac2161189dddd93554acc55b3d55e4394a16ff`.
Hosting подтвердил совпадение всех четырёх установленных tools, живые две Linux
службы/Mac observer и сохранённые Mac HTML200/r001 hash после final refresh.
Outage/revise/browser для нового hash не повторялись.

Основной checkout и чужой WIP не редактировались. Infra commits301d3bc/1618f10 принадлежат
hosting и уже находятся в истории назначенного worktree; source commit включает
только свои пути. Установленные caches и глобальные disabled hooks не менялись.
