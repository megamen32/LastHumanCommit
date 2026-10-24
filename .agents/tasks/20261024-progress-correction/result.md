# Результат: автоматическая коррекция прогресса Codex

Реализовано: Codex async PostToolUse → свежий read-only native Overseer →
additionalContext активному родителю → полезное следующее действие.
Таймер вызывает проверку; смысл прогресса оценивает модель. Совет не gate.

## Native canary

Поддержанный проверенный клиент: standalone Codex CLI 0.162.1, Linux
(roomhacker-server-100), модель gpt-6.1-sol, настоящая квота: 40% использовано.
Пакет установлен штатным `codex plugin add` в отдельном CODEX_HOME под
`.tmp/progress-correction/home`; доверие восьми hooks задано штатным `/hooks`
только там. Глобальная конфигурация и пользовательские отключения не изменены.

Искусственно состарен **только таймер disposable fixture на 31 минуту**,
после появления настоящей native telemetry. SHA-проверки воспроизводят старый
маршрут. Native event, модель, callback и выполнение рекомендации настоящие.

Родитель `01a16dbe-6c59-7872-b6e7-a249c9fe07f9`, ход
`01a16dbe-6cca-7420-a3ac-d28b09b04d66`. В native журнале
`rollout-2026-10-24T14-49-18-01a16dbe-6c59-7872-b6e7-a249c9fe07f9.jsonl:65`,
2026-10-24T11:50:55.047Z, записан developer additionalContext: `redirect`,
наблюдение — SHA без установки/consumer; рекомендация — выполнить
`cp ready.txt installed.txt && python3 ../canary.py consumer`.

Родитель выполнил именно эту команду. Локальный журнал
`.tmp/progress-correction/parent-1792842558.jsonl:17-18`: код 0,
`CONSUMER_OK: installed artifact matches the ready product.` Ход завершён;
progress state содержит last_advice=redirect, last_bucket=1, active_turn=null.
После Stop/SessionEnd новый ход не запускался. Lead независимо прочитал и принял
callback и consumer proof.

Сырые native журналы, auth-ссылка и disposable профиль оставлены локально в
`.tmp/`, в Git не включены. Ранние неудачные fixture-попытки сохранены как
неуспешные: запись защищённого таймера из sandbox, завершение до callback,
отсутствие первой telemetry, коллизия собственного имени тестового журнала.

## Проверка и ограничения

Целевые тесты: дедупликация, одна модель в работе, отмена при native новом ходе/
Stop/Interrupt/SessionEnd, peer relay без ложной отмены, недоступная модель,
неизвестная/низкая квота и один metadata retry, JSON-секреты, отсутствие private
reasoning, общий бюджет snapshot, прежний совет и последующие действия.
Независимый read-only Reviewer нашёл пропуск JSON-секретов; исправлен с регрессией.
Отдельный настоящий native Overseer вернул continue для запрошенного аудита с
новым дефектом; redirect — для готового неустановленного кода и повторных SHA.

У остальных harness ручная методика. Transcript-формат version-specific;
неполнота данных остаётся неизвестностью. Inactive parent не пробуждается.
Произвольное окно прогресса и ранний перерасход исходной оценки пока не
реализованы: используется существующий 30-минутный heartbeat, без выдуманного
активного времени. Старые method hold не являются полномочиями или запретом.

## Доставка

Lead разрешил публикацию 1.5.48 после принятия canary. Перед публикацией
origin/main подтверждён как cb08aa0. Чужой cost-first WIP, dirty primary и другие
worktree не затрагиваются. Итоговый remote SHA и installed readback — ниже.

- Финальный релизный smoke и manifest parity: 32 passed; до последнего узкого
  metadata retry расширенный целевой набор: 70 passed.
- `publish_package.py --check`: проекции совпадают; `validate.py`: PASS,
  25 skills, canonical/parity PASS; `git diff --check`: без ошибок.
- Native manager после bump вернул installed/enabled **1.5.48**, источник —
  выделенный worktree, `plugins/last-human-commit/native/codex`; installed cache
  находится только в disposable CODEX_HOME. Глобальные hooks не включались.
