# Начало плана с первого листа

Назначение: один worker, isolated worktree; production runtime и независимая
потребительская проверка принадлежат Lead. Исходный код: b12935d / 1.5.56.

План: одна последовательная задача — RED для начала плана → минимальное
сохранение источника времени → проверка цепочки публикации → пакет 1.5.57.
До изменения шкала начинается с исполнительского started_at или остаётся пустой.
После изменения создание первого листа входит во время плана автоматически.

Рабочий вариант: неизменяемый локальный источник времени и передача в зеркало.
Идеальный вариант: точные даты у всех исторических листов; восстановить их без
доказательств невозможно. Минимальный вариант сохраняет точные native даты,
восстанавливает доступный birthtime, иначе явно сообщает неизвестность.

Реализованная схема: `.lhc-publication/plan-origin.json` содержит `at`
(ISO с часовым поясом либо пустая строка), `source` (`leaf_created_at`,
`file_birthtime`, `recorded_start`, `unknown`), `leaf_id` (без пути),
`recorded_at` (момент фиксации, не начало плана). Объект передаётся как
`plan_origin` в graph/public snapshot. Лист получает immutable `created_at`.

Проверки: RED — 5 ожидаемых отказов; GREEN основной затронутой цепочки —
101 passed, 1 skipped (не запущен opt-in браузерный тест). Дополнительная
проверка публичного created_at и версии: 64 passed, 1 skipped. Новые проверки
импорта, настоящего birthtime и миграции старой ревизии добавлены отдельно.

Независимое наблюдение Lead, сообщение Herder `736acc5b`: payload
`d300d9bbdb9dfa1c` установлен на server100. Observer мигрировал исходный
привязанный legacy-план без изменения plan.json/листьев. Источник:
`2026-10-25T11:23:00.550084Z`, `file_birthtime`, `L01`; текущая HTTPS-страница
показала 14:23 MSK с пометкой восстановления. Исходный r001 сохранил хеш
`bf3dd25661f3121acbf290a65769354891d7c09d8fc4a7d31c6b4b05e6870da0`.
Lead также проверил собственный fixture с реальным birth до upgrade:
atomic replace → удаление первого листа → native O03 → progress → r002,
без сдвига начала и без изменения старого r001. Это сообщение Lead,
а не самостоятельно выполненный этим worker production canary.

Команды сборки: `python3 plugins/last-human-commit/scripts/sync_skills.py`,
`python3 scripts/publish_package.py`; обе затем с `--check`.
Проверка пакета: `python3 plugins/last-human-commit/scripts/validate.py`.
Полный tests/validate.py сознательно не запускался: он запускает весь tests,
что выходит за прямое указание на узкие проверки.

Семантика: sidecar фиксируется локально один раз под отдельным origin.lock;
check/build_document только читают. Native update сохраняет origin до atomic
replace, но ошибка его записи не превращает сохранённый лист в отказ сети.
Observer включает schema/sidecar в fingerprint и мигрирует неизменённые планы.
Нет fallback на mtime/ctime, receipt, render/watch time. При отсутствии
свидетельств начало unknown. started_at/finished_at остаются фактами исполнения;
неизвестный фактический финиш завершённого плана не придумывается.
plan_origin не входит в planning_facts и не создаёт новую принятую ревизию
от обычного progress. Graph/import сохраняет происхождение; server только
валидирует и отображает присланное, не вызывает восстановление по файлам.

Финальный delta-набор: `python3 -m pytest tests/test_plan_origin.py
tests/test_plugin_version_parity.py -q` — 13 passed. Генераторы с `--check`
и package validator — PASS. Installer payload окончательного кода:
`829f5d3f632234b8` (алгоритм существующего install-native.py).

Независимое наблюдение Lead на Mac: установлен именно
`829f5d3f632234b8`, конфигурация сохранена. Новый raw fixture восстановил
native st_birthtime с отклонением менее 1 мс; atomic update сохранил origin.
Native M02 автоматически получил timezone-aware created_at, progress его
сохранил; локальные операции не требовали сети или регистрации.

Ограничения: файловая система без birthtime не позволяет восстановить старую
дату. Скопированный legacy-план без sidecar/graph-origin требует честной
пометки восстановления по доступным локальным файлам; точность исходного
создания копия сама доказать не может. Архивные snapshots без origin остаются
неизменными. Финальный runtime refresh server100+Mac выполняет Lead.
