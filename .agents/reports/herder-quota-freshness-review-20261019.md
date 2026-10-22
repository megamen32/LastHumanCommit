# Freshness review Herder quota — 19.10.2026

**SCOPED GREEN / APPROVE для B2-дельты exact SHA `d3c2be632aa5d67048c9d661e17e8bd0e28dcc89`. Блокирующих замечаний в проверенном scope нет.** Это независимый source review, не installed PASS и не разрешение на релиз от имени reviewer.

Объект: branch `lhc/lhc-quota-freshness-20261019`, draft [PR12](https://github.com/megamen32/agent-herder/pull/12), worktree `/home/roomhacker/agents-projects/agent-herder/.worktrees/lhc-quota-readonly-20261019`. Source owner: Codex `01a155c7-a3a1-7d33-817f-8e7419dd152d`; reviewer: Codex `01a155b4-5105-7cb0-ab1c-9274abc05b7e`.

## Факты по exact diff

Прочитан обновлённый `herder-quota-fix-20261019.md` и полный commit diff: только `src/model-quota.ts`, `src/automation/minimax-quota-preflight.ts` и два соответствующих test-файла. HEAD до/после проверки равен заданному SHA; worktree оставался чистым.

- `model-quota.ts:61–67`: deadline — минимум известных `end_time/weekly_end_time` только general/exact text rows. Video deadline не участвует. Null/missing не превращаются в epoch0; единицы не угадываются.
- `:117–122`: положительный snapshot проверяется после получения ответа; при `now >= validUntilMs` становится `unknown/quota_snapshot_expired`, исходные данные сохраняются.
- `minimax-quota-preflight.ts:25,32,44–47`: положительный cache ограничен меньшим из TTL и provider deadline, исключено повторное использование после отката часов; повторная проверка после await закрывает пересечение reset во время GET.
- Изменений controller/fallback/admission/HumanStop в этой дельте нет. B1 не переоткрывался и не перепроверялся.

## Независимый результат тестов

Повторены собственные контрпримеры B2 и соседние negative cases **над Git blobs этого SHA**: TypeScript transpile в памяти → data-URL imports; default network fetch запрещён исключением, provider responses и clock инжектированы, Codex auth dependency заменена заглушкой. Файлы source/tests не редактировались.

**20 проверок прошли:**

| Сценарий | Наблюдение |
|---|---|
| Положительный cache перед interval/weekly reset | До10999ms available; на точном11000ms новый GET, unknown; по2 GET на каждый независимый вариант |
| Собственные прежние B2 cases | В12000ms после reset — unknown; новый reader в40000ms с expired positive payload — unknown |
| Медленный GET пересёк reset | unknown после завершения ответа |
| TTL раньше deadline; новая будущая window | На TTL выполняется новый GET; valid свежий ответ остаётся available |
| Clock rollback; concurrent callers | Rollback вызывает новый GET; concurrent requests используют один in-flight |
| Milliseconds/seconds/null/missing | Milliseconds сохранены; seconds не масштабируются; exact deadline истёк; null/missing остаются неопределёнными, raw null сохранён |
| Video0/expired video deadline | Не блокируют положительный применимый text pool |
| Interval0/weekly0; zero после reset/TTL | Exhausted не повышается таймером; повторный GET со старым zero остаётся exhausted |
| Missing weekly/unknown pool/auth/error | unknown; отсутствие auth не вызывает GET |
| GLM/Codex соседняя telemetry | unit3/number5/reset-null,604800seconds/Unix reset и secondary=null сохранены |

Все26 зафиксированных mock MiniMax requests — **GET без body**; реальных provider/network/inference запросов — **0**. Дополнительно `node_modules/.bin/tsc --noEmit --incremental false` завершился **exit0**, native exec session82114. Авторские111 suite-tests не объявляю своим повторным прогоном.

## Ограничение и передача

B2 закрыт на уровне exact source и детерминированных regressions. Snapshot остаётся telemetry, не резервом quota; concurrent spending способен изменить доступность после чтения. Missing deadline сохраняет прежний конечный TTL, не создаёт фиктивный reset.

Не выполнялись auth reads, runtime restart/deploy, provider calls, запуск агентов, сообщения, commit/merge/rollback. Рабочую установку PR10 не трогал; её квитанции и прежний аудит не расширялись. Source candidate PR12 этим отчётом не считается активированным. Следующий release/installed consumer check принадлежит назначенному координатору. Записан только этот evidence-файл.

