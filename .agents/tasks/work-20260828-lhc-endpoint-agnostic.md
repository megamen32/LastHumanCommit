# work-20260828 — endpoint-agnostic AskHuman + opt-in упаковка

Started at: 2026-08-28 03:20 (UTC+3), источник: ручные часы сессии; активное время: не контролировал.
Initial estimate: 20 / 50 active minutes.

## Запрос

Вариант A, но: опора на личный notify.bezrabotnyi.com — не идеал; эндпоинт
должен настраиваться, а маркетплейс не умеет параметризованную установку
(env при install). Нужен механизм «эндпоинт из env/.env → регистрация MCP в
харнессе» + возможность оставить только один плагин.

## Канарей

В репо нигде не зашит URL эндпоинта; ask-human в маркетплейсе AVAILABLE
(opt-in); setup_mcp.py регистрирует MCP из env (dry-run по умолчанию,
--apply с бэкапом); все валидаторы зелёные; запушено/задеплоено.

## Изменения

- marketplace: ask-human INSTALLED_BY_DEFAULT → AVAILABLE.
- plugins/ask-human 0.3.0: + scripts/setup_mcp.py (env → codex config.toml,
  сниппеты для остальных), команды/скиллы получили секцию Endpoint (BYO).
- README: явная связь «компаньоны, не зависимости», оба деградируют мягко.

## Результат

- rg по репо: ни одного зашитого URL эндпоинта. ask-human 0.3.0:
  setup_mcp.py (dry-run самотест OK, --apply с бэкапом), секция Endpoint в
  команде/каноне-команде/zcode-скилле, маркетплейс AVAILABLE.
- validate.py PASS, 41 pytest, marketplace entries=2, plugin parity 12;
  вложенные фейлы теперь печатают полный вывод (4-й флейк задокументирован).
- Запушено, rollout verified, дерево чистое (см. финальную канарейку).
