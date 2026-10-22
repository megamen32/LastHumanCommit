# Council, quotas и человеческий ответ: проверенные причины и минимальный дизайн

Дата: 19 октября 2026. Режим: **RESEARCH ONLY / READY_TO_IMPLEMENT**. Это исследование и предложение, не реализованный council и не приёмка исправленного runtime.

## Граница и происхождение доказательств

Пользователь/получатель — владелец LHC и ведущий реализации outcome-contract. До изменения агент может спутать наличие модели в каталоге с доступной квотой и закончить работу после создания недоставленного вопроса. Требуемый результат будущей реализации: перед council/focus acceptance агент видит реальные ограничения, использует разрешённые модели и сохраняет недостающую приёмку pending; вопрос получает одну карточку и возвращает ответ в исходную сессию. Места ручной проверки: существующий Herder MCP, реальные native transcripts и существующая карточка Notice Place.

Исходный запрос и последние ограничения сверены с `AGENTS.md`, установленным контрактом `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.4.13/AGENTS.md` и `.agents/tasks/lhc-outcome-contract-20261019.md`. Текущий корень и cwd: `/home/roomhacker/agents-projects/LastHumanCommit`; harness Codex; native session `01a155b4-56bf-70d1-adb3-d4481df5de66`; хост `roomhacker-server-100`. Native transcript указан в контексте: `/home/roomhacker/.codex/sessions/2026/10/19/rollout-2026-10-19T22-47-24-01a155b4-56bf-70d1-adb3-d4481df5de66.jsonl`.

Срезы исходников: LHC `373cbd218c7cd9b911948cac2ae69840206d046c`; agent-herder `0b3533d3a7fcd80acd05cc24b5ce81bdfb912ca3`; noticeplace `21b9850c96803724e1bee6e18e1b838fcd5dacf0`; локальные primary Hermes sources `71d34bad1045610252eda02ee79549436896e784`, remote `https://github.com/NousResearch/hermes-agent.git`. `git diff --stat` по исследуемым Herder/Notify исходникам был пуст. Исследуемые `mcp/notify_mcp.py`, `notification_center/http_api.py`, `notification_center/core.py` побайтно совпали с `/opt/noticeplace/` (`cmp` exit 0 для каждого).

Herder: существующая user service, PID `488984`, владелец `roomhacker`, active; начало процесса `22:10:17 MSK`. Все MCP reads выполнены через `dist/http-mcp-stdio.js` к singleton `http://127.0.0.1:18787/mcp`. `initialize` вернул `agent-herder 0.3.0`. До вызовов прочитан живой `tools/list`; `dist/index.js`, root-дубликат и новый manager не запускались. Создана только требуемая runtime-инструкцией coordination note на этот отчёт: `cfe02e16-f13b-4538-adb6-a73c1214493b`, TTL до `20:21:41 UTC`; это не изменение чужой задачи или разрешение на dispatch.

AgentMemory recall вызван с project/task query; результат содержал нерелевантные AutoSeller записи, они исключены из доказательств. Локальная историческая память использована только как указатель на старую границу Notify receipt/consumer proof; актуальные выводы ниже перепроверены в исходниках. GrepMesh использован до поиска по проектам. Один поиск `current_interval_remaining_percent` завершился `state=failed`, `indexed search unavailable: interrupted`; ограниченный `rg` затем применён к уже установленным конкретным файлам. Частичный mesh output не выдаётся за полный аудит.

Единственный записанный исследователем файл в checkout — этот отчёт. Исходники, main, auth, модели, сессии, права, cron и runtime-конфигурация не менялись; вложенные агенты/тестировщики не запускались. Созданных вопросов/уведомлений/звонков нет; receipt такого действия отсутствует по замыслу. Платные inference для quota не выполнялись. У исследования нет блокера: недостающие проверки реализации перечислены как следующий этап, не как выполненная работа.

## 1. Живые квоты и точные единицы

### Снимок Herder `model_quotas`, 19:48:48 UTC / 22:48:48 МСК

Живая схема: `model_quotas` принимает `{}`. Описание обещает GLM Coding Plan, MiniMax Token Plan и local Codex usage; при отсутствии credentials/usage — `unknown`. Формального outputSchema у инструмента нет; ответ содержит text JSON и `structuredContent`. Типы реализации: `reported | quota_exhausted | unknown`, `checkedAt`, `details`, optional `error`.

| Провайдер | Проверенный ответ | Корректное чтение и ограничение |
| --- | --- | --- |
| GLM | `state=quota_exhausted`; CREDIT_LIMIT unit 3: `usage=28000,currentValue=0,remaining=28000,percentage=0`; unit 6: `usage=140000,currentValue=140087,remaining=0,percentage=100,nextResetTime=1792778782999` | Единицы — кредиты плана, не токены и не количество вызовов. `usage` здесь ёмкость, `currentValue` расход, `remaining` остаток. Недельное окно блокирует использование даже при свободном коротком. Расход на 87 кредитов выше ёмкости — сохранить raw и считать исчерпание, не делать отрицательный доступный остаток. |
| MiniMax | `state=reported`; `model_name=general`, `current_interval_status=2`, `current_interval_remaining_percent=0`, `current_weekly_status=1`, `current_weekly_remaining_percent=69`; total/usage counts обоих окон `0` | 0% включённого общего пула сейчас; 69% — **остаток** недельного пула, не расход. Абсолютные токены/вызовы из нулевых counts не выводятся. Video — отдельная строка, её 100% не делает text/council доступным. Числовые enum status 1/2 сохранены; официальной таблицы enum в проверенных документах не найдено. Вывод о нулевой квоте опирается на remaining_percent, а не догадку об enum. |
| Codex | `state=reported`, plan `pro`, `primary_used=34`, `primary_reset_s=435114`, `limit_reached=false` | 34% **использовано**, не остаток. Из одного Herder-ответа длительность primary неизвестна: адаптер её удаляет. Нет доказательства доступности каждой модели/vision/tool path. |

MiniMax general window: `start_time=1792422000000` → 19 октября 15:00 UTC, `end_time=1792440000000` → 20:00 UTC / **23:00 МСК**. `remains_time=671257` — около 671.257 секунды, то есть **миллисекунды**, не число токенов. Weekly: `weekly_start_time=1792368000000` → 19 октября 00:00 UTC, `weekly_end_time=1792972800000` → **26 октября 00:00 UTC / 03:00 МСК**; `weekly_remains_time=533471257` тоже ms. Это provider reset metadata, не TTL достоверности снимка. У video API вернул также суточные поля; официальная текущая FAQ описывает video как weekly-only, поэтому не переносить его interval semantics на general.

### Уточнение прямым read-only чтением, 19:51:40 UTC

Существующие защищённые credentials использованы внутри процесса, без вывода значений, копирования в отчёт или refresh/auth mutation. GLM GET повторён, чтобы увидеть поля, потерянные sanitizer. Codex GET повторён, чтобы увидеть длительность окна. Inference endpoints не вызывались.

GLM raw whitelist, ответ `code=200, level=max`:

```json
{"limits":[
  {"type":"CREDIT_LIMIT","unit":3,"number":5,"usage":28000,"currentValue":0,"remaining":28000,"percentage":0},
  {"type":"CREDIT_LIMIT","unit":6,"number":1,"usage":140000,"currentValue":140087,"remaining":0,"percentage":100,"nextResetTime":1792778782999}
]}
```

Связка `unit=3,number=5` соответствует пятичасовому окну, `unit=6,number=1` недельному: это проверенный account payload плюс официальные квоты Max 28 000 / 140 000 кредитов. Публичную нормативную таблицу всех numeric unit enums не найдено; неизвестные будущие units не следует нормализовать по позиции строки. GLM weekly reset: **23 октября 18:06:22.999 UTC / 21:06:22.999 МСК**. У короткого окна reset отсутствует; не придумывать now+5h. [Официальные allowances/reset rules](https://docs.z.ai/devpack/overview).

Codex raw whitelist, время `19:51:40.814 UTC`:

```json
{"plan_type":"pro","rate_limit":{"allowed":true,"limit_reached":false,
 "primary_window":{"used_percent":35,"limit_window_seconds":604800,"reset_after_seconds":434942,"reset_at":1792874442},
 "secondary_window":null}}
```

Теперь период установлен: **неделя, 604 800 секунд**; 35% использовано, 65% арифметический остаток этого окна; reset **24 октября 20:40:42 UTC / 23:40:42 МСК**. Рост с 34 до 35 — другой момент наблюдения, не расхождение единиц. `secondary_window=null` — окно не сообщено, не «0% использовано». Исследование не определяет, какая из параллельных native нагрузок потребила процент.

### Первичные механизмы проверки

| Источник | Проверенный механизм | Что не делать |
| --- | --- | --- |
| Z.AI | Herder GET `https://api.z.ai/api/monitor/usage/quota/limit`, Authorization raw protected key. Тот же GET и raw Authorization в [официальном query-usage.mjs](https://github.com/zai-org/zai-coding-plugins/blob/main/plugins/glm-plan-usage/skills/usage-query-skill/scripts/query-usage.mjs), строки 40–53,112–123. Скрипт собирает ещё model/tool usage; для quota достаточно quota GET. | Не переносить legacy `TOKENS_LIMIT` label «5 Hour» на все CREDIT_LIMIT; не переводить кредиты в токены/стоимость по памяти; не менять domain/account scope без доказательств. |
| MiniMax | GET `https://www.minimax.io/v1/token_plan/remains` с Bearer Subscription Key. Это endpoint из [официальной FAQ](https://platform.minimax.io/docs/m-plan/faq); там же documented `mmx quota`. CLI здесь не запускался. | Не POST messages для «бесплатного» preflight; не использовать обычный PAYG API key; не разрешать credit-pack overage только потому, что запрос может пройти. |
| Codex | Herder сейчас читает `https://chatgpt.com/backend-api/wham/usage` через local native ChatGPT auth. Предпочтительный документированный native fallback — [App Server `account/rateLimits/read`](https://learn.chatgpt.com/docs/app-server), без turn/inference. `rateLimitsByLimitId`, `usedPercent`, `windowDurationMins`, `resetsAt` (Unix **seconds**). | Не считать внутренний wham endpoint стабильным публичным API; не запускать новую auth-сессию/refresh ради измерения; не путать `account/usage/read` token activity с quota. Не вызывать consume reset credit / billing methods. |

Документы MiniMax подтверждают независимые 5h и weekly windows для non-video, при исчерпании одного окно другого не освобождает. Та же FAQ сообщает автоматическое расходование имеющихся credit packs после включённой квоты; доступность платного остатка — отдельная величина и здесь **unknown**, использовать его это исследование не разрешает. Это существенная причина не делать inference probe. Numeric `status=2` сам по себе не используется как документированный enum.

Текущая реализация `readModelQuotas` **не кэширует** результат и не выдаёт TTL. `checkedAt` GLM/MiniMax ставится перед GET, не является TTL/сроком reset. HTTP deadline 5 секунд для каждого; Codex — 10 секунд. Общий Promise.all не делает снимки атомарными. Никакой reservation/shared-budget fence из snapshot не возникает: другие клиенты могут потратить квоту немедленно.

## 2. Подтверждённые дефекты и ближайшее исправление

Основной путь: `agent-herder/src/mcp/session-tools.ts:69–77` → `src/model-quota.ts:105–122` → provider GET / `src/web/quota-lens.ts:76–98`.

**Q1 — MiniMax exhaustion пропущен.** В `model-quota.ts:38–47` generic `explicitlyExhausted` понимает `remaining`, `remaining_quota`, `percentage>=100`, но не `current_interval_remaining_percent`/`current_weekly_remaining_percent`. В `:84–85` числовые current/usage fields доказывают «есть измерения», затем неизвестные exhaustion fields превращаются в `reported`. Это подтверждённый дефект нормализации: `reported` буквально означает «данные получены», поэтому само слово не обещает доступность, однако intended ветка `quota_exhausted` для реального нулевого пула не срабатывает. Он позволяет наивному потребителю ошибочно выбрать исчерпанную подписку.

Без файловых изменений выполнен mock reproduction через импорт существующего `dist/model-quota.js` и `fetchImpl: async()=>Response.json(fixture)`, без сети и credentials. Реальные source/dist SHA256: `442b2ce78f7809068be63ea43bc09f9c4ca6d467c1941c3103a4da2ca3f9cca2` / `9314faa7329c80625630690b67155e32f5656706f77d0894558de0e207020cbe`.

```text
case observed-general-zero-week69: expected quota_exhausted; actual reported
case general-weekly-zero (interval50, weekly0): expected quota_exhausted; actual reported
case general-positive-video-zero: actual reported (защита от будущего неверного any-row fix)
case codex-secondary100-primary34-limitfalse: actual reported
```

Первые два — RED evidence нормализатора на установленном JS плюс живое подтверждение первого случая. Третий показывает необходимое разделение scopes: нельзя просто распознать любой `_remaining_percent=0` рекурсивно во всех строках; video не должен блокировать доступный text-пул. Четвёртый — непокрытый конфликтный synthetic input: secondary saturation сейчас игнорируется. Live такой конфликт не наблюдался; минимум — не возвращать безусловную доступность при противоречащих windows/flag.

Минимум Q1: provider-specific mapping relevant general/text pool, exhaustion при нулевом остатке **любого применимого** окна, unknown при неизвестном scope/формате. Сохранить `reported` как telemetry status, отдельно вычислять eligibility для конкретного задания. Counts `0/0` при наличии процентов не использовать как division/полный расход. Не считать отдельную video-квоту квотой text.

**Q2 — sanitizer теряет период.** `model-quota.ts:25–29` whitelist не пропускает ключ `number`: direct GLM `number=5/1` исчезает из MCP. `quota-lens.ts:91–98` теряет Codex `limit_window_seconds`, `reset_at`, `allowed`, secondary reset, multi-bucket информацию. Следствие: клиент не может честно объяснить период/доступность. Минимум: безопасные числовые period/reset fields сохранить; sensitive keys продолжать исключать. Это не запрос ослабить sanitizer целиком.

**Q3 — отдельный «quota preflight» расходует inference.** `src/automation/minimax-quota-preflight.ts:25–33` вызывает POST `https://api.minimax.io/anthropic/v1/messages`, `max_tokens=1`, «Reply OK». Кэш 30 секунд (`:15–23`); это **не** TTL `model_quotas` и **не** read-only quota API. `src/index.ts:883` подключает его к `namedSessionRunner`; `src/automation/project-launch-dispatch.ts:386–394` блокирует только confirmed exhaustion, `unknown` проходит к запуску. Исследователь его не вызывал. Минимальная рекомендация владельцу Herder — перевести эту preflight-потребность на existing read-only allowance logic, а не документировать inference probe как quota fallback. Потенциальное потребление credit packs при таком probe не проверялось.

**Q4 — LHC route hints отстают от прямого поручения.** `src/common/skills/model-routing/SKILL.md:39–56` рекомендует OmniRoute paths для GLM/MiniMax; live `list_models` содержит прямые пользовательские subscription routes. `src/named-session.ts:255–264` имеет default GLM-Flash → **OmniRoute MiniMax** fallback. Это не причина менять уже живые сессии: для будущих council assignments явно выбрать preferred routes и передавать `fallbackModels: []` либо только разрешённые явные альтернативы. Unknown/accepted delivery не даёт права создавать замену. Это рекомендация, dispatch здесь не выполнялся.

## 3. Что уже есть в LHC и чему учат primary Hermes sources

`src/common/skills/council/SKILL.md:10–39` уже задаёт independent proposals → cross-challenge → synthesis → fresh recheck → experiment и прямо отвергает majority truth. Не нужен новый council server. Недостающие конкретные элементы: общий quota skill/call site, preferred exact subscription pool, поведение 2/1/0 моделей, явная tradeoff matrix и model-attestation receipts.

`model-routing/SKILL.md:10–37,65–132` уже разделяет role/model/harness, требует explicit model и native identity, говорит unknown outcome не replay, определяет independence context и принятие по evidence. Это полезная основа; не заменять новой иерархией supervisor/router.

`focus-groups/SKILL.md:28–48` уже различает model/persona diversity, требует fresh contexts, реальные entrypoints и полное положительное/критическое task-relevant feedback. Минимум — связать это с тем же quota skill, сохранить фактическое покрытие модели/устройства/tool path, не принимать login page за выполненный сценарий и запретить recursive tester hiring. Самостоятельная компьютерная проверка и provider quota — разные доказательства.

Primary Hermes:

* [Issue 37569](https://github.com/NousResearch/hermes-agent/issues/37569) — **closed as not planned**, 13 июля, policy `delegation-model-routing`. Это предложение proposer/critic/chairman с per-call provider/model routing, не доказательство установленного `/council` core feature. Упомянутые автором tests/E2E в issue — self-report, здесь не выполнялись.
* [Issue 5876](https://github.com/NousResearch/hermes-agent/issues/5876) — **closed completed**, 5 июля; maintainer написал, что это реализовано MoA update. Это подтверждает расширение delegation, а не все детали позднего отдельного council proposal. Эти два issues не противоречат друг другу.
* В локальном primary `tools/delegate_tool.py:625–645,695–745,790–798` и свежем [upstream source](https://github.com/NousResearch/hermes-agent/blob/main/tools/delegate_tool.py) child contexts изолированы; summary — self-report; модель наследуется либо задаётся trusted `delegation.provider/model` config. В model-facing schema нет per-task model/provider arguments. Legacy role ignored, capability определяется depth (`:225–229`). Поэтому нельзя писать совет «вызови Hermes delegate_task(model=...)» или считать role=leaf достаточным runtime запретом рекурсии. Данный запуск не меняет Hermes config; multi-model путь — существующий Herder, а при его отсутствии подходящий native explicit model механизм с заявленными ограничениями.
* [Ridwannurudeen/hermes-council](https://github.com/Ridwannurudeen/hermes-council) — отдельный MCP package с personas и одним настраиваемым `COUNCIL_MODEL`; полезны разделение retrieved/cited evidence и explicit dissent, но persona count не доказывает multi-model diversity. [jrbobbyhansen-pixel/hermes-council](https://github.com/jrbobbyhansen-pixel/hermes-council) — community skill со blind first → cross-examination, но 22 personas, forced dissent, fixed triads, secret auto-loading и provider routing не подходят этому bounded заданию. Ничего из них не установлено.

## 4. Рабочее → идеальное → bounded 80% MVP

**Рабочее решение целиком.** Один общий skill `model-availability` (предлагаемое имя) обслуживает council, model-routing и focus-groups. Он читает Herder `model_quotas` + `list_models`, нормализует provider scope/window, отделяет quota/auth/catalog/capability/attestation, выбирает из разрешённого пула и сохраняет evidence. Без Herder применяет существующие официальные read-only механизмы из §1; не создаёт MCP/controller/cron. Council использует explicit Herder `new_or_resume`; прямой native dispatch описывается как fallback, без скрытого billing switch и без изменения parent/global model.

Preferred pool из **прямого запроса**, подтверждён live catalog:

| Кандидат | Harness + exact route | Snapshot eligibility |
| --- | --- | --- |
| Sol 6.1 | `codex / gpt-6.1-sol` | Каталог есть; ChatGPT account read succeeded, allowed=true и weekly35%. Это quota-eligible candidate, не обещание свободной concurrency/vision/model execution. |
| GLM 5.3 | `opencode / zai-coding-plan/glm-5.3` | Каталог есть; weekly credits exhausted. Исключить из нового оплачиваемого deliberation до свежего положительного измерения. |
| MiniMax M3.1 Flash | `opencode / minimax-coding-plan/MiniMax-M3.1-Flash` | Каталог есть; general interval0%. Включённая подписка исчерпана до reset/повторного чтения; не использовать paid overage. |

Проверен supplement по model-catalog skill: `https://github.com/megamen32/models-supplement/raw/refs/heads/main/supplement.json`. Он не является account execution/quota proof; цены, benchmark ranking и не найденные capabilities для этих routes здесь не утверждаются. Frontier pool определяется поручением, не собственной оценкой брендов.

**Идеальное решение.** Тот же один skill и существующий MCP, но typed provider window records с account/plan scope, source timestamp/latency, reset, provenance и per-task capability receipts; все потребители Herder используют одну read-only normalizer logic. После каждого dispatch реальная native модель сопоставляется с requested route; после quota change учитывается частично завершённый council без повторного inference. Сохранённые proposals/falsifiers/decision/dissent доступны после compaction; synthetic focus feedback связано с конкретным продуктовым build и browser/native receipts. Это не новая служба и не task scheduler.

**Bounded 80% MVP.** Добавить только один небольшой skill с адаптерной таблицей и freshness policy; сослаться на него из трёх имеющихся skills; минимально исправить Q1/Q2 и отдельно заменить имеющийся Q3 probe у владельца Herder. Сохранить текущий evidence/task механизм, существующий HumanRequest/Notify, реальные canaries. Не добавлять модельный маркетплейс, скоринговый сервис, quorum daemon, automatic billing fallback, новые таймеры и «совет из 22 персон». Из ideal отложить прогноз расхода, автоматические reservations и новые dashboards: они не нужны, чтобы правильно прочитать interval0 и не подделать council.

Предлагаемый контракт skill (спецификация, не новый реализованный API): для каждого кандидата выдать `requested_route`, `catalog_present`, `auth_state`, `quota_state`, relevant window `used_percent/remaining_percent`, unit/period/reset (nullable), `source`, `checked_at`, age/freshness, `capabilities` и `actual_model` (unknown до native receipt), причину eligibility. Raw credential-free numeric evidence сохранить рядом. `reported` не переводить автоматически в `available`; quota unavailable/auth invalid/tool missing — разные причины.

Freshness MVP — **проектная рекомендация, не provider SLA**: перед запуском bounded council/focus batch прочитать live один раз, переиспользовать до 30 секунд внутри batch; на следующем этапе после более долгого ожидания перечитать. При прошедшем known reset старый exhausted snapshot устаревает, но не становится positive. Для known exhaustion до reset не запускать inference; после reset сделать новый GET при следующем нужном действии. Missing reset остаётся null; unknown не кэшировать как available, не опрашивать в LLM-цикле и не ставить cron. При read error максимум одна документированная direct read попытка для нужного провайдера; затем честный unknown и независимая работа. Cache TTL и reset timestamp — отдельные поля. Model catalog presence также не снимает quota/auth/capability gate.

### Протокол принятия решения

1. Зафиксировать бизнес-canary, constraints, проверенные факты, разрешённые routes, общий предел работы и обязательный результат. Каждому proposer — одинаковый исходный brief без preferred Lead plan; fresh independent контекст, explicit запрет нанимать дальше. Не путать общий brief с передачей истории родителя.
2. Независимые proposals: решение, ценность для пользователя, альтернативы, сложность/усилие, риск, latency/quota/cash cost (unknown если нет фактов), assumptions, конкретный falsifier и минимальная проверка.
3. Один cross-challenge pass: каждый видит альтернативы, атакует спорные assumptions, формулирует сильнейшее возражение/контрпример и улучшение. Можно скрыть авторов; число голосов не аргумент.
4. Свести **tradeoff matrix** по реальным вариантам, с источником каждого вывода. Lead выбирает или связно объединяет аргументы, пишет decision + dissent + unresolved assumptions. Не притворяться, что несовместимые решения согласованы.
5. Fresh review уже синтезированного решения и короткая discriminating проверка спорного утверждения. Если она меняет данные — адресная корректировка. Bounded MVP: один proposals pass, один cross-challenge pass, synthesis/recheck; дополнительный круг только ради конкретного нерешённого существенного факта. Это ограничение затрат, не право пропустить обязательную проверку.

Состояния пула: 3 eligible — использовать preferred diverse three при оправданной задаче; 2 — полноценное двухмодельное рассмотрение с явным `2 models`, не ждать третью ради числа; 1 — fresh same-model adversarial review допустим как ограниченная проверка, **не multimodel council**. Обязательный multimodel gate остаётся pending, пока не появится второй eligible route или прямое решение пользователя о допустимой замене/ограничении. 0 — сохранить готовые артефакты и точный локальный blocker; продолжать independent non-inference работу. Не покупать доступ и не переключать billing. На снимке 19:51 — только Sol quota-eligible; ни одного реального council этим исследованием не запущено.

Attestation: в живой схеме `new_or_resume` required `harness,name,cwd,message`; есть `model,inputId,fallbackModels,sourceSessionId,sourceHarness`. Имя роли внутри message не равно выбору model. Returned `model`/fallbackFrom у `named-session.ts:235–243` — selected route, не provider execution receipt. Для Codex использовать native turn/transcript model (`adapters/codex.ts:948–958`; app-server thread.model может быть только session metadata). Для OpenCode `adapters/opencode.ts:67–77` уточняет model по последнему native message; сопоставить именно assistant result нужного assignment/turn, а не чужой latest turn. Receipt содержит native ID, turn/message ref, requested и observed model/provider, evidence path. Если observed unknown/mismatch — не засчитывать участника в заявленное model diversity; не запускать повтор accepted/unknown job ради красивой аттестации.

### Матрица вариантов реализации

Это сравнение исследователя, **не** результаты независимых модельных proposals/голосования.

| Вариант | Польза | Усилие/сложность | Риск/стоимость | Решение и возражение |
| --- | --- | --- | --- | --- |
| Только поправить текст «reported не available» | Сразу избегает одного ложного чтения | Малые | Raw parser продолжает пропускать zero; каждый skill вынужден сам разбирать JSON | Полезный hotfix guidance, недостаточно как законченный контракт |
| Один skill + existing model_quotas/direct reads + provider-specific Q1/Q2 | Правильные windows, 2/1 handling, portable маршрут, сохраняет canary | Ограниченные изменения трёх skills и existing normalizer | Snapshot race остаётся; реальные capabilities требуют штатного сценария | **Рекомендация**. Возражение: нет atomic reservation; принимается как честный предел, не обещается отсутствие 429 |
| Новый council/quota MCP, автоматический scheduler и per-provider wrappers | Больше automation | Существенно больше delivery/support | Дублирует Herder; новые secrets/runtime/billing/ownership риски | Отклонить в этом scope; не нужен для доказанного дефекта |

## 5. Notify/HumanRequest: действующие пути, а не угаданный curl

Получен live `GET https://notify.bezrabotnyi.com/v1/instructions`, schema `noticeplace.instructions.v1`. Источник HTTP и installed `/opt` совпал. Дополнительно выполнен **только** `tools/list` существующего `/opt/noticeplace/mcp/notify_mcp.py` с `-B`/`PYTHONDONTWRITEBYTECODE=1`: `ensure_runtime_ready()` для tools/list не вызывается. Он вернул schema `noticeplace_ask_human` и `noticeplace_question_result`. В предоставленном harness tool catalog видны generic `ask_human`, pending/result; bound `noticeplace_ask_human` не был виден. Это ограничение этой поверхности, не доказательство отсутствия функции на сервере; документированный существующий HTTP остаётся fallback.

Правильный будущий путь обычного вопроса:

1. Herder `human_request_create(kind=user,harness,sessionId,cwd,message,choices?)` создаёт durable binding. Live schema choices: `choiceId,label`, 2–4; `cwd` формально optional, но для реального Notice/native resume нужен абсолютный cwd. Hermes требует immutable locator; не угадывать sessionId. Этот инструмент **не отправляет** Notify-карточку. `notify` input в исследованном handler меняет contextRef, не превращает вызов в доставку (`src/mcp/human-request-tools.ts:102–113`).
2. Existing `noticeplace_ask_human` принимает binding.request_id, native_target.harness/session_id/cwd, тот же русский message, optional choices **`label,value`**, incident_id. `choiceId` → `value` без изменения смысла/ID; лимит labels Notice core **80**, а Herder допускает512, поэтому безопасный общий предел80. Нельзя механически отправлять весь Herder binding в HTTP body.
3. Реальный HTTP fallback из source `mcp/notify_mcp.py:327–380` — POST `/v1/human-requests`, Bearer project token, `Idempotency-Key=human-request:<request_id>`. Payload schema **`ask_human.request.v1`**, required `request_id,project,recipient,mode,message`, actors; mode question или choice, choices `label,value`, `native_target={harness,session_id,cwd}`, `kind=user`, optional incident_id. Данные project/recipient/actors/credentials брать из существующей конфигурации, не выдумывать. Core validation `notification_center/core.py:700–758`; request-id exact replay проверяется в `:788–832`.
4. Проверить **доставку**, а не только created row: card status `sent` с provider message receipt. `queued`, `not_configured`, `uncertain` не считать delivered. При incident_id используется та же incident card, возвращается queued/edited_in_place и нужен её delivery outcome (`http_api.py:1787–1798`). Не посылать параллельно generic event/вторую карточку.
5. Ответ из UI/API проходит existing `complete_human_request` (`http_api.py:1535–1599`), canonical value хранится до native/card work. Completion к Herder: `/internal/human-requests/ask-user-completion` с `{event:"ask.user.completed",event_version:1,status:"completed",request_id,result_ref}` из `agent_job_helper.py:592–645`. Herder `resumeHumanRequestOnce` делает durable admission и stable idempotency; lease expiry разрешает observation, не повторную отправку (`resume-admission.ts:44–115`). На unknown/accepted outcome — читать receipt, не создавать другую сессию/повтор.
6. Resumed turn читает `noticeplace_question_result(request_id=...)`, required только request_id; underlying GET `/v1/human-requests/{id}/result`. Это canonical answer, не opaque delivery receipt и не пересказ агентом. Completion prompt уже задаёт этот путь (`resume-admission.ts:125–145`). Свежий HumanStop должен сохраниться; admittedAt используется как explicit-stop fence. Live ответ/возобновление в этом исследовании **не проверялись**.

Важные ограничения:

* Generic `ask_human` не заменяет bound путь. В `mcp/notify_mcp.py:499–537` он создаёт вопрос без `native_target`, опрашивает до wait_seconds и может вернуть `continuation=resume` при pending. Эта строка сама не доказывает, что исходная native session автоматически возобновится. Минимальная правка LHC — явно требовать bound seam для durable решения, не generic notification/final chat.
* Phone escalation существующего incident реализована в `http_api.py:993–1028` после initial incident delivery и зависит от severity/config/active state. Standalone AskHuman send path `:1776–1865` **не планирует такой incident escalation** и в его schema нет escalation policy. Следовательно нельзя обещать звонок любому standalone quota question «через10мин» по старой памяти. Для вопроса внутри существующего incident сохранить incident_id и его настроенную политику; standalone escalation требует отдельного подтверждённого продукта/решения, не фиктивного health incident. Реальный runtime delay/quiet hours здесь не измерены, звонков нет.
* Core `:685–689` не истекает native-bound pending question по expires_at; TTL не считается разрешением отменить её/потерять исходную задачу. Нужны явная отмена/закрытие связанного incident и сохранение canonical answer, не самодельный таймер.
* Не создавать human question при каждом quota GET. Вопрос нужен только для существенного решения, которое нельзя разрешить существующими полномочиями и которое мешает обязательному результату. Routine exhaustion — сначала альтернативный разрешённый маршрут или независимая работа; readiness не подменять council PASS. Здесь нового решения от человека не требуется.

## 6. Минимальная матрица проверки для исполнителя

Ниже **план приёмки**, кроме отмеченных executed RED checks. Он не означает, что новые тесты написаны/запущены или пользователи уже проверили продукт.

| Проверка | Нужное доказательство / ожидаемое поведение | Статус здесь |
| --- | --- | --- |
| MiniMax general interval0/weekly69, counts0/0 | quota_exhausted включённой text quota; не reported→eligible | **RED воспроизведён** на dist + live payload |
| MiniMax interval50/weekly0 | exhausted по weekly независимо от short | **RED воспроизведён**, mock |
| MiniMax general positive, video0 | Text допускается по своему scope; video не блокирует/не освобождает text | Mock current output снят; future classifier не реализован |
| MiniMax unknown enum/shape, missing relevant row, malformed JSON | unknown с reason; не доступность по чужому полю | Требуется fixture test |
| GLM CREDIT_LIMIT unit3/number5 и unit6/number1 | Кредиты, periods/reset сохраняются; weekly0 блокирует | Live evidence есть; нормализованный новый output не реализован |
| GLM MCP TIME_LIMIT0 при text credits positive | Отдельные scopes; tool quota влияет только на задание, которому нужен этот MCP | Требуется fixture test, live такого случая нет |
| Codex used35%,604800s,secondary=null | Weekly35 used,65 arithmetic remaining, reset_at seconds; null не0 | Live raw evidence есть; Herder fields loss подтверждён |
| Codex primary34/secondary100/limitfalse | Конфликт не становится unconditional available | Current mock `reported`; новый контракт проверить |
| Missing credentials,401/403,429 без quota code,timeout | auth unknown/invalid либо throttled/unknown; не считать любой429 weekly exhaustion | Существующие tests покрывают часть unknown; suite здесь не запускался |
| TTL/reset | Snapshot age>policy или reset passed → refresh; reset absent → null; не now+window;0% не positive после таймера | Требуется fake-clock test; no cron |
| Read-only guarantee | Quota path делает только documented GET/native rateLimits read; ни одного messages/turn POST; credits не расходуются | Исследование соблюло; отдельный existing Q3 требует замены |
| 3 / 2 eligible | Independent brief, actual models distinct; при2 не ждать3; synthesis сохраняет dissent | Не запускалось: inference/delegation запрещены заданием |
| 1 / 0 eligible | Честный single-model limitation/pending multimodel gate; готовые артефакты сохранены, независимая работа продолжается | Дизайн; текущий pool практически1 quota-eligible |
| Requested GLM → observed MiniMax, missing actual ID | Не засчитывать подменённую/неаттестованную модель; не платить ещё раз за accepted unknown job | Проверить transcript fixtures + один штатный canary после реализации |
| Compaction/retry | Proposal refs, source model, business canary, pending gates и dissent сохраняются; inputId тот же | Требуется regression scenario |
| Computer-use diversity | Разные реальные goals/devices/conditions; fresh contexts, independent first attempt, fixed revision; модель и персона — отдельные axes | Нужна будущая реальная browser/native проверка |
| Login/tool failure | Login page ≠ goal success; сохраняются snapshot/tool receipt и exact limitation; no invented PASS | Требуется negative real-surface case |
| Raw focus feedback | Полный task-relevant positive+critical feedback, attempts/recovery, screenshots/CLI receipts; без forced complaints/hidden reasoning | Проверить на реальных tester outputs, здесь их нет |
| Human question | Один binding→одна Notice card→human answer→canonical result→ровно одно stop-aware native continuation | Source route подтверждён; end-to-end **NOT TESTED** |
| Duplicate/unknown question delivery | Stable request/idempotency, query receipt; не повторять uncertain provider action; no child/session replacement | Требуются existing registry/HTTP negative tests и controlled canary |
| Escalation | Реальная existing policy/incident binding, provider delivery и ACK/cancel proof; standalone без policy не обещает call | **NOT TESTED**, не переносить старый10min delay |

## Следующий наименьший шаг

Владельцу реализации LHC — использовать эту спецификацию для одного quota skill и адресных изменений council/model-routing/focus-groups. Владельцу Herder — RED fixtures из §2, provider-specific Q1, сохранение period/reset Q2 и удаление billable quota probe Q3 из проверяемого маршрута; без нового MCP. Затем relevant tests и read-only live quota canary, после появления минимум двух eligible models — bounded council с native attestation. Consumer acceptance для focus/Notify проводится только в разрешённом следующем этапе и не выдаётся за результат этого исследования. Текущий отчёт завершён; исправления и live multimodel/Notify acceptance остаются невыполненными, как и требует RESEARCH ONLY.
