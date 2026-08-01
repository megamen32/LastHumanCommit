# Раскатка актуального Last Human Commit на fleet

## Исходный запрос

> «Я там параллельно обновлял этот Last Human Commit, вот его нужно тоже везде раскатать.»

## Цель

Развернуть последнюю подтверждённую ревизию Last Human Commit из
`main` на 100, 44, 88 и Mac, сохранив предыдущую установленную версию как
rollback и не включая незакоммиченные параллельные артефакты.

## Business canary

На каждом из четырёх хостов `current` указывает на новую версию, полный digest
установленного дерева LHC совпадает с digest исходного дерева этой
ревизии, а реальный role-router разрешает Lead через новый `current` без
отсутствующих файлов.

## Подтверждённый scope

- источник: последний чистый commit `main` после проверки worktree;
- хосты: 100, 44, 88, Mac;
- versioned install с атомарным переключением `current`;
- rollback предыдущего `current`;
- проверка полного дерева и role-router на каждом хосте.

## Явные исключения

- не коммитить и не раскатывать `graphify-out/`;
- не изменять чужой `.agents/last-human-commit/self-improve.md`;
- не менять harness-конфигурации, ключи, права, БД, Grafana или providers;
- не публиковать репозиторий и не делать push без отдельного запроса.

## Цикл и начальная оценка

- Цикл: Short.
- Оптимистично: 8 активных минут.
- Вероятно: 15 активных минут.
- Пессимистично: 30 активных минут.
- Оценка зафиксирована до раскатки и не заменяется последующими уточнениями.

## Состояние

Status: complete

## Фактический результат

- Источник: `214e59229a5b68d78bab88087f9198c88d182e6e`, совпадает с `origin/main`.
- Полный payload: 23 файла, digest
  `d478758030588945fc56be8ddcc004c2639ac6817dfbd863ed1ada22d40d2f36`.
- На 100, 44, 88 и Mac `current -> versions/214e592`; независимый повторный
  verify прошёл после apply.
- Проверено 18 глобальных router-файлов, 10 project-local runtime-копий и 17
  project router-файлов; каждый router разрешает все семь role-файлов.
- Hermes plugin синхронизирован на 100, 88 и Mac; на 44 экземпляра Hermes нет.
- Физический OpenCode на каждом хосте прочитал глобальный `AGENTS.md` через
  собственный file subsystem и увидел новый role-router, обязательного
  Overseer, `current` Lead path и task-file contract.
- Rollback сохранён в `~/.local/share/last-human-commit/rollbacks/214e592-fleet-before`
  и соседних `.prev-214e592` для project/plugin runtime.

## Квалификаторы

- LHC не содержит adapters для OpenClaw, Zcode и VS Code; новые
  неподтверждённые adapters в рамках раскатки не изобретались.
- Отдельный inference-canary `OmniRoute best-free` вернул одинаковый server
  `UnknownError` на всех хостах. Это не изменило и не опровергло проверенную
  установку LHC, но live model inference остаётся отдельным незакрытым
  runtime/provider вопросом.

## Оценка после выполнения

- Фактически: около 35 активных минут.
- Пересмотр: пессимистическая оценка превышена примерно на 5 минут из-за
  исправления и локального regression-теста rollback installer, а также
  попытки live inference-canary после успешной раскатки.
