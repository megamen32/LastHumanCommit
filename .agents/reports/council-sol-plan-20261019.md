# Первая независимая Sol-оценка outcome MVP

Статус: **CHANGES_REQUIRED в формулировках плана; выбран bounded вариант B.** Это первая самостоятельная позиция участника, не итог council, не review реализованного patch и не consumer PASS. MiniMax feedback до этой записи не читался; cross-challenge ещё не состоялся.

Модель подтверждена native источником: **`gpt-6.1-sol`**, harness Codex, native session **`01a155b4-56bf-70d1-adb3-d4481df5de66`**, turn `01a155c2-bf63-7352-8259-3c95ce7aed9d`, timestamp `2026-10-19T20:03:08.839Z`. Источник — `turn_context`, строка260 `/home/roomhacker/.codex/sessions/2026/10/19/rollout-2026-10-19T22-47-24-01a155b4-56bf-70d1-adb3-d4481df5de66.jsonl`; это native metadata, а не имя модели в моём prompt. Provider backend beyond native attestation не устанавливался.

Хост server-100; cwd/mainroot `/home/roomhacker/agents-projects/LastHumanCommit`; main HEAD `373cbd218c7cd9b911948cac2ae69840206d046c`. Оценён план `.agents/reports/outcome-mvp-plan-20261019.md`, SHA256 `3e0c9c1ab5b0316b361bfa4355959887b864eeecb9b502fc21d57fbdcd866c60` (mtime 22:58:15 МСК). Implementation owner из плана — `01a155b9-0b2c-7953-8afb-f530945dd0ff`; его source/worktree не присваиваю. Разрешённый файл этой фазы — только данный отчёт. Source/runtime/auth/модели/права/cron/main не менялись, вопросы/агенты не создавались. В существующей coordination note обновлены только мой scope/path.

## Решение, польза и альтернативы

Пользователь — владелец обычных engineering/test поручений. Нужный исход: агент не объявляет выполненным конкретный API/CLI/UI сценарий, который не проверял, и не превращает законченное тестирование с найденным дефектом в бесконечное исправление без полномочий. Ручная проверка — ordinary prompts без `@LHC` в candidate native profiles, с реальными вызовами и доступной историей продолжения/доставки.

Выбираю **B: компактный outcome в существующем per-session state + структурные source checks + один предметный semantic close существующим reviewer-путём**. Убрать двусмысленности ниже до большого patch; не расширять задачу до универсального контроллера успеха. Направление плана верно, но одного перечисления refs и pending stages недостаточно: должен существовать достижимый положительный путь закрытия тех же стадий.

| Вариант | Польза | Усилие/сложность | Риск/стоимость | Позиция |
| --- | --- | --- | --- | --- |
| A. Только инструкции/classification, оставить нынешний UI-only Stop | Быстро объясняет цель и testing semantics | Минимальные правки | Воспроизведённые non-UI/read-only early finishes сохраняются; агент может проигнорировать инструкцию | Недостаточно для исходного canary |
| B. Existing state + минимальный evaluator + source refs и bounded semantic close | Общий canary, честное testing completion, достижимое закрытие, защита от replay | Среднее, локальное изменение entry/state; review по реальному результату | Semantic ошибка возможна; unknown форматы остаются честно pending. Требуются positive и negative native canaries | **Выбрать** |
| C. Универсальное автоопределение deploy/consumer/permission/success по любому shell/stdout, новым registry/controller | Обещает меньше участия Lead | Высокое, неограниченный словарь и адаптеры | Ложный PASS от echo/не того target; ложный вечный pending; новый infra/approval механизм | Убрать из MVP |

Рабочее решение целиком: явный исход/canary и применимые стадии, источник результата, проверка смысла, реальные разрешённые действия доставки. Идеальное: native veto и typed outcome proof для всех harness/потребителей. Полезный 80%: конечный набор обязательных canaries и существующие native adapters, без universal shell parser, нового scheduler, нового quota/Notify MCP и без обещания OpenCode veto. Сокращается автоматизация, **не** обязательный сценарий пользователя.

## 1. Source-backed ref — происхождение, не доказательство смысла

План `:83–85,115–119` правильно отвергает self-authored PASS. Но остаётся невыбранным конкретный переход `evidence exists → required scenario satisfied`. Риск двух крайностей: автор сам закрывает стадии записью refs либо evaluator никогда не может их закрыть, потому что ему запрещено понимать результат.

Проверенный source: `src/common/tools/lhc_time_guard.py:761–828` хранит operation/target/outcome и `action_evidence_sequence`. `returned` в `:798` не означает consumer success; счётчик `:825–827` растёт после релевантного вызова, а не доказанной полезной дельты. Уже действующий `REVIEW_TO_DELIVERY.md:28–41,69–75` различает raw tool evidence и вывод о потребительском результате, не требует нового сертификата.

**Контрпримеры:**

* `curl https://site/health` вернул200, а canary — создать заказ и увидеть его после перезагрузки. HTTP receipt подлинный, нужный исход не проверен.
* Shell исполнил `printf 'HTTP 200 total=0'`; native stdout настоящий, сервер не вызывался. Авторский `record --canary passed --ref call42` не меняет этого.
* Экспорт действительно вернул CSV с двумя строками, но generic parser не знает кодировку/схему приложения. Постоянный pending здесь тоже дефект.

**Минимальное уточнение B:** хранить для stage только source-derived identity/revision/target и candidate claim с refs. Структурная проверка удостоверяет существование/соответствие native ID, нужного call/job/turn и revision; **не** выдаёт business PASS. Существующий reviewer/Lead review проверяет claim против исходного expected observation и raw результата, возвращает concise conclusion + raw references. Для обязательной независимой приёмки reviewer должен быть отдельным существующим участником; авторский record-command не может заменить её. Не делать новый verifier для каждой записи: один review затронутого результата может закрыть несколько явно покрытых claims. Метаданные извлекаются механически, semantic conclusion сохраняется в native review без нового LLM-generated certificate JSON.

Реализация должна иметь положительный fixture: подлинный API/CLI result + reviewer source закрывает assigned stage; ложный echo/другой target/старая revision не закрывают. Неизвестный parser coverage → exact capability limit и доступный штатный ручной/native путь review, не утверждение «универсально доказано».

## 2. Testing success с найденным дефектом и выбор класса

Поддерживаю тезис плана `:16–17,81–82`, но нужны **две независимые оценки**, не общий `success=true`: `assignment completion` и `tested product verdict`. Coverage определяется поручением, не количеством положительных сценариев.

Проверенный source: `lhc_milestone.py:192–193` полностью выходит для read_only; `:455–461` превращает наблюдение проблем в changes-required, а `:488–504` требует accepted feedback для принятия самого продукта. Эти UI rules нельзя просто перенести на успешность поручения исследователя/тестировщика. Task contract `:7,11,13` прямо позволяет test-only результат и не разрешает принудительный code/deploy.

**Контрпример T1:** «Только проверь пустую и двухтоварную корзину, код не меняй». Тестировщик реально сделал оба сценария, пустая дала500, другая прошла. Его **testing assignment complete**, product verdict **CHANGES_REQUIRED**, repair ownership/permission отдельно. Требование product PASS до завершения тестировщика зациклит запрещённую разработку. То же при раннем crash, который делает второй сценарий объективно недостижимым: coverage row содержит attempt+blocking evidence, а не фиктивное выполнение.

**Контрпример T2:** «Протестируй checkout и исправь найденные ошибки». Нельзя классифицировать это как testing и закончить на дефекте; это composite engineering scope с test этапом. `testing` substring не отменяет repair canary.

**Контрпример T3:** в процессе fullcycle человек спрашивает «какой статус тестирования?». Это короткий ответ и продолжение прежней цели, не новая class=status, обнуляющая release obligations.

Минимум: зафиксировать class/source при новой содержательной задаче; correction/status не заменяет его автоматически. Неоднозначный class — рабочая гипотеза по цели/контексту, без отдельного LLM classifier/server. `status` должен быть способом ответа внутри задачи, а не универсальной лазейкой закрытия. Для testing rows: scenario/attempt refs/observed result или доказанный blocker; завершение исследования не даёт продукту PASS. Возражение к «любое actionable pending при неоднозначности»: если смысл уже восстанавливается из явных полномочий, делать доступную часть, а не навечно блокировать на классификации.

## 3. Fingerprint: не one-shot навсегда и не генератор продолжений

В `lhc_entry.py:202–246` `milestone.continuation_requested` — один флаг на всю задолженность; `lhc_milestone.py:216–219` обновляет surface_key, но этот флаг не сбрасывает. Поэтому причина RED4 source-backed. Читал owner fixture `.worktrees/outcome-contract-20261019/tests/test_outcome_contract.py:40–53` и существующий raw log `.tmp/outcome-contract/source-red.log`: четыре failures/2.82s подтверждаются содержимым лога; **сам tests повторно не запускал**. Флаг действительно не различает исправленную поверхность и старый Stop.

Условия нового fingerprint в плане `:88–92` недостаточно точны:

* New turn ID, повторный status poll, новое время или call ID не progress.
* Hash всего checkout позволяет чужому WIP/изменению README бесконечно rearm мою задолженность.
* Surface hash A→B→A может оживить уже отработанный fingerprint, если хранить только last key.
* Исключительно Git hash не видит успешного deploy/auth recovery или результата живой build; canary может продвинуться без code change.
* Новый generic `action_evidence_sequence` без changed relevant condition позволяет rearm после любого того же GET.

Минимум B: identity задолженности = исходный outcome + конкретный pending stage/target + относящаяся к нему revision/условие; **continuation receipt привязать к обоснованной дельте**, а не к каждому boundary. Источники дельты ограниченные: relevant owned source change; завершение известного live native job; новое каноническое человеческое решение; новая успешная или содержательно изменившая возможность продолжения target-specific проверка. Один и тот же результат с другим call ID не новизна. Хранить достаточную дедупликацию уже использованных continuation identities **в existing outcome**, не отдельный event service. Новая полезная попытка не должна стирать прежнюю stop/replay историю.

До trusted progress conclusion сведения — candidates; не строить большой semantic classifier внутри Stop hook. Stop читает уже сформированное состояние и bounded refs. Сильная гарантия MVP: duplicate/restart/compaction без полезной дельты не создаёт новую отправку; real relevant repair разрешает одну дополнительную continuation на исходный pending consumer check. Unknown accepted operation/live job хранится и наблюдается, не переигрывается. HumanStop/new revocation имеют приоритет над любым fingerprint.

«Terminal pending» означает **окончание автоматического повторения при сохранённой задолженности**, а не запрет future native resume после нового разрешённого условия. На final нельзя написать complete; после полезного независимого шага или реального внешнего события можно продолжить ту же задачу. Новый daemon для пробуждения не нужен.

## 4. Notify: binding, delivery, answer и продолжение — четыре факта

Поддерживаю latest поправку плана `:154–158`. Проверенный source: Herder `src/mcp/human-request-tools.ts:102–113` возвращает binding; `src/human-request/question-binding.ts:49–57` прямо назначает карточку существующему Notice POST. Notify `mcp/notify_mcp.py:327–380` реализует bound seam, `:499–537` generic ask_human не передаёт native_target. `notification_center/http_api.py:2167–2214` различает доставку, idempotent retry и uncertain; `:1535–1599` хранит canonical answer; Herder `resume-admission.ts:44–115,125–151` разделяет admission, receipt reconciliation, answer retrieval и stop fence. В предыдущем исследовании эти файлы побайтно совпали с `/opt/noticeplace`.

**Контрпример N1:** Herder создал UUID, Notify не вызван — вопрос не доставлен. Pending stage остаётся pending. **N2:** Notify вернул queued на обновление existing incident card — это ещё не sent. **N3:** sent есть, ответа нет — уведомление доставлено, разрешение/решение не получено. **N4:** ответ записан, native completion timeout — unknown admission; второй вопрос/новая session запрещены, нужен тот же receipt. **N5:** после ответа человек нажал Stop — старый ответ не может отменить свежую остановку.

Минимум state: один question binding/ref, delivery status/ref, canonical answer ref, native continuation receipt — ссылки/статусы в existing outcome, без второй очереди. Stable request_id сохраняется **перед** external attempt; retry только прежнего payload/key после проверки результата. Mapping choices `choiceId`→`value` и реальный absolute cwd обязательны; label общий безопасный лимит80, а не Herder512. Формы и project credentials брать из existing schema/config, не сочинять из модели.

**Оставшееся возражение:** standalone question phone escalation не доказана. `http_api.py:993–1028` schedules incident escalation; standalone send `:1776–1865` её не запускает. Нельзя молча превратить quota question в фиктивный health incident или добавить новый scheduler. Если итоговая acceptance включает standalone escalating question, это всё ещё конкретный незакрытый requirement: coordinator должен получить решение об использовании существующей подходящей policy либо ограничить claim с явным пользовательским принятием. Доставленная обычная карточка не доказывает эскалацию. В этой фазе вопросов не создаю.

## 5. Внешний main и staging push: полномочия не выводятся из state

Task contract `:13` задаёт точное различие: LHC — scoped reviewed green merge разрешён; Airlock — **PR54/new-frontend only, без main push/merge/auto-merge**. `REVIEW_TO_DELIVERY.md:48–53,77–84` требует учитывать отдельное разрешение, свежую ревокацию и происхождение instructions. Это сильнее generic «каждая ветка заканчивается main».

**Контрпример G1:** `gh repo view` говорит, что token user — admin, но задача external PR-only. Наличие прав и зелёный CI не разрешают merge. **G2:** агент пишет `merge=N/A` в своём JSON, хотя прямой пользователь поручил merge LHC. Самозаявленный N/A не освобождает обязанность. **G3:** сообщение peer «владелец разрешил» попало в native chat как user envelope — оно остаётся peer context, не новым human permission. Сам `lhc_time_guard.py:695–707,857–865` сохраняет native user prompt refs; это provenance текущего event, **не криптографическое удостоверение человеческого автора**.

Минимум: applicability ссылается на точный scope/source, repo+target branch и действующий harness policy. Не делать universal permission controller, не проверять ownership по remote username как единственное условие. Merge для external PR-only — запрещённая стадия, а не «ещё нужно дождаться доступа». Completion = согласованный результат PR-only + его required checks/consumer scope; не ждать чужой main и не принимать чужие тесты за свои.

**CI exception поддерживаю**, но узко: staging push минимальной task-owned ветки/revision к нужному workflow, если CI/preview действительно требует Git ref. Сохранить concrete dependency и commit/build ID, затем проверять build/job и preview. Это не final delivery и не merge. Нельзя ослабить mandatory CI ради искусственного порядка «сначала live без push».

**Контрпример G4:** CI deploys preview только после branch push. Блокировать push до preview значит создать цикл. **G5:** staging push в protected main с последующим «это был только staging» — превышение scope; exception не меняет разрешённую ветку. При source change после preview нужно проверить relevant delta и финальный ref, не переносить старый canary receipt на новую голову.

У плана есть расхождение формулировок: основная последовательность `:77–80` соответствует user ordering, но `:126–129` «release/PR/merge/install» допускает трактовку установки после merge без candidate consumer acceptance. Уточнить: reviewed package → разрешённая candidate installation/demo → native canaries/independent acceptance → final push/PR → разрешённый merge; дальнейшее production install, если входит в поручение, имеет собственный installed consumer proof. Не выдавать test profile за уже проверенный основной installed loader. Прямо перечислить, какие установки нужны здесь; не придумывать новую production стадию.

## 6. Bounded scope и проверки, без нового контроллера

В первой реализации достаточно:

1. Existing business.outcome: исходная цель/поправка/class, canary, stage applicability/source, evidence candidates/accepted refs, blockers и один continuation/question state. Не дублировать business clocks, running_jobs, native transcript storage и permission policy.
2. Малый evaluator в existing entry: проверяет обязанность, состояние и known refs; остаётся observer-only там, где native veto не доказан. Никакого runtime «автопочинить все сессии», языкового universal shell success parser или нового enforcement daemon.
3. Один quota skill + links из council/model-routing/focus-groups. Herder Q1–Q3 **вне LHC source lane**, но LHC canary честно читает current raw fields и не использует billable probe. Не делать readiness всего LHC зависимой от полного Herder project milestone.
4. Existing generation/loader path. Мелкое исправление manifest плана: `src/common/AGENTS.md` не существует; source router — корневой `AGENTS.md`, generation подтверждена `plugins/last-human-commit/scripts/sync_skills.py:211–215`; reusable project template — `src/common/templates/project-router.md`. Исправить путь локально, это не новый архитектурный review.

Не фиксирую выдуманные человеко-часы/денежные цены. B дороже A на state/evidence/positive-path checks, но конечнее C и прямо покрывает четыре существующих RED. 1.5.0 — допустимая candidate semver, не доказательство успешной установки.

| Проверка до заявления результата | Что должно различаться |
| --- | --- |
| API/CLI negative **и positive** | Pytest-only не закрывает реальный canary; реальный соответствующий результат+review закрывает, без вечного pending |
| Testing-only found defect / fix-if-broken / status steering | Testing complete с product changes-required; composite repair pending; status не стирает исходную цель |
| Fingerprint, duplicate, A→B→A, чужой WIP, same poll | Ноль новых повторов без полезного изменения; relevant repair/job completion даёт одно нужное продолжение |
| Running/unknown/manual stop/compaction | Тот же job/input/goal/clocks; не дублируется действие; Stop не снимается старым ответом |
| Ref attacks | Echo, другой target/revision/turn, собственный PASS и record-command не закрывают canary |
| External PR-only + LHC merge + CI-only preview | Каждая стадия применима по своему scope; нет main mutation внешнего repo и push-preview deadlock |
| Notify four-state negative/positive | Binding-only/queued/sent unanswered/unknown native не complete; canonical answer возвращается в exact session один раз |
| Actual two-model council / focus CUA | Native model receipts обоих, fresh contexts и реальные tool interactions; persona≠model diversity; login-only≠success |
| Candidate native loader coverage | Codex/ZCode Stop проверены положительно/отрицательно; OpenCode consumed context/compaction с честным observer-only пределом |

## Фактическая доступность и residual dissent

В `20:03:49 UTC` повторил **read-only** `model_quotas` через существующий `http-mcp-stdio.js` после чтения live schema: GLM weekly remaining0; MiniMax general interval **99% remaining**, weekly69, status1; Codex primary_used35, limit_reached=false. Ранее исчерпанный MiniMax interval действительно сменился. Snapshot не reservation и не model execution receipt. Второй участник MiniMax сообщён назначением; его native turn/model evidence должен проверить coordinator. Сам его transcript/feedback не читал. Поэтому корректный предполагаемый формат — **два preferred frontier participants из трёх**, не «три модели», а итог multimodel acceptance всё ещё требует cross-challenge и attestation второй модели.

Моё residual dissent к текущему плану: (1) нужен достижимый semantic close, не только refs и отрицательные tests; (2) полезная дельта fingerprint не равна новому call/hash; (3) testing completion не может требовать product PASS; (4) standalone escalation остаётся недоказанным requirement; (5) порядок candidate install/consumer acceptance/final PR необходимо сделать однозначным. После этих узких уточнений направление B можно реализовывать без универсального контроллера. Чужой будущий counterargument или data может изменить решение; совпадение голосов само по себе не закроет эти пять пунктов.

Следующий шаг — coordinator передаёт этой позиции конкретные контраргументы второй модели для одного cross-challenge pass; реализация и финальный quorum verdict принадлежат назначенному delivery owner. Моя первая позиция сохранена независимо; её наличие не выдаётся за выполненный следующий раунд.
