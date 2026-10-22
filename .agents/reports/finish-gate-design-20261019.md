# Исследование finish gate LHC 1.4.13

Срез: 2026-10-19, 19:51 UTC; host `roomhacker-server-100`, harness Codex, native session `01a155b4-5e49-75b0-a292-e959f3b266d0`, cwd/mainroot `/home/roomhacker/agents-projects/LastHumanCommit`. HEAD `373cbd218c7cd9b911948cac2ae69840206d046c`.

## Результат и границы

**Причина подтверждена:** текущий исполняемый gate — долг независимой UI-приёмки плюс просроченные 60/120-minute reviews, а не общий контракт завершения исходного результата. Для backend/CLI и quickfix обязательный business canary не создаётся; testing-only исключается из UI gate без собственной проверки покрытия. Даже для UI Stop допускает завершение с pending после одного продолжения. Проверок последовательности deploy → hands-on → final push/PR → допустимый merge в этом gate нет.

Пользователь результата — владелец инженерной задачи; ожидаемая разница: вместо финала по тестам/receipt он получает проверенный исходный сценарий и выполненную применимую доставку либо честное незавершённое состояние с точным блокером. Проверять будущую реализацию нужно обычными native prompts без `@LHC`, а не наличием фразы в инструкциях.

Это **RESEARCH ONLY**. Записан только этот evidence-файл. Исходники, main, конфигурация, auth, runtime, модели, cron и чужие сессии не менялись. Подагенты не запускались; safety-blocked probes не повторялись. Выполнены чтение code/tests/config, сравнение байтов и изолированные вычисления в памяти. Полные pytest/Bun suites и новые native engineering sessions не запускались: они создают fixtures/state вне разрешённого файла. Зелёная runtime-приёмка исправления здесь не заявляется.

Прочитаны корневой `AGENTS.md`, актуальный installed `.../last-human-commit/1.4.13/AGENTS.md`, `.agents/tasks/lhc-outcome-contract-20261019.md`, действующие `.planning/{PROJECT,REQUIREMENTS,ROADMAP,STATE}.md` и указанные STATE SPEC/PLAN. Последние относятся к завершённой continuity-задаче 14 октября; не подменяют новое research-поручение.

## Источники и проверка установки

- AgentMemory `memory_recall` вызван с project path и entry/milestone/timeguard/Stop-запросом. Получены старые compact observation IDs без полезного содержательного решения; выводы ими не обоснованы. Локальная память о UI debt использована только как указатель, затем проверена кодом.
- GrepMesh вызван до поиска по source/installed scopes; точный `src/common/tools/lhc_entry.py:1–220` прочитан через `read_text`. Installed search завершился `partial=false`, но `truncated=true`: это ограниченный поиск, не полный аудит всех конфигураций. Далее использованы точные локальные чтения. Существующий Graphify содержит 107 nodes на старом commit `fd3165d942cd818213f7fb65520977370473ceec`, без этих новых tools; для выводов о них непригоден, не перестраивался. Existing code-map подтвердил историческое сужение READ_ONLY до task-wide scope; актуальный код проверен.
- Herder доступен через **существующий** `node /home/roomhacker/agents-projects/agent-herder/dist/http-mcp-stdio.js` → `http://127.0.0.1:18787/mcp`. Выполнены initialize → initialized → tools/list. Live server `agent-herder 0.3.0`, 58 tools, `nextCursor=null`; прочитаны schemas list_agents/coordination/human_request. Дубликат `index.js`, root-manager или daemon не запускался.
- Read-only list_agents для проекта вернул 16 записей, **complete=false, limited=true**, включая эту сессию и двух соседних исследователей. Это не полный fleet audit. Coordination notes сначала пусты; по обязательному runtime-требованию объявлена одна ownership-note только на этот отчёт, ID `0e54474c-8c92-435b-9d28-87a191a3d27e`, TTL до 20:20:44 UTC. Задачи соседей не менялись и сообщения им не отправлялись.

| Поверхность | Подтверждённое состояние | Предел доказательства |
|---|---|---|
| Codex installed 1.4.13 | `~/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.4.13/.codex-plugin/plugin.json`; hooks перечисляют SessionStart/UserPromptSubmit/PreToolUse/PostToolUse/PreCompact/PostCompact/Stop/Interrupt/SessionEnd/PermissionRequest. `~/.codex/config.toml:51,54` включает hooks/plugin_hooks, секции hook state включены, plugin включён на 484. | Manifest/config сами по себе не доказывают Stop. |
| Собственная Codex-сессия | Existing learning-state `967db74c1dbcc32a9f9667a24ce5157852264c13440a5d4018107d7d08bea4d1.json`: native_entry.version `1.4.13`, root cache выше, наблюдены UserPromptSubmit и PreToolUse. | Реальный entry/context работает в этой сессии; финальный Stop ещё не проверен. |
| Codex source parity | Installed `tools/lhc_entry.py`, `tools/lhc_milestone.py`, `tools/lhc_time_guard.py` побайтно равны source. Entry также совпадает в `common/tools`. | Проверка исходников, не model compliance. |
| OpenCode installed adapter | `~/.config/opencode/plugins/last-human-commit-v1410.ts:1` — re-export marketplace `.../opencode/lhc-v2.ts`. Целевой marketplace package **1.4.13**; v2 и tools равны source package. | Имя v1410 не означает старый исполняемый код. Загрузка конкретным живым OpenCode runtime здесь не проверялась. |
| Hermes installed | `~/.hermes/plugins/last-human-commit/plugin.json:4` имеет **1.2.4**. Wrapper `__init__.py:6–11` загружает собственный `com.nousresearch.hermes/__init__.py` и назначает `_root` на этот установленный каталог. | Нельзя считать установку Hermes обновлённой до 1.4.13. Config включает plugin, но live вызов не выполнялся. |
| ZCode | Source `tests/test_zcode_native_lifecycle.py:131–150`, `.zcode-plugin/plugin.json`, supplementary `hooks/zcode-hooks.json` описывают lifecycle 1.4.13. Existing `~/.zcode/hooks/lhc_time_start.sh` — только старый start-anchor; `~/.zcode/plugin-workspace` пуст. | Эти места не доказывают отсутствие другого native loader. Активная installed ZCode 1.4.13 и её Stop **не установлены** этим исследованием. |

Контрольные SHA256:

```text
src/common/tools/lhc_entry.py       1def6e7f4a6980a308546187d0519bcd06dd9a490dd1448caf56845f176c992b
src/common/tools/lhc_milestone.py   0758294770d9cf932af54b18c719ecd3874ca4e2739835d5a33a1b1313736114
src/common/tools/lhc_time_guard.py  c5e655980b32ed6f6753f6c0dd7bf4ecf37f6648c96472b0965d6424acd6cc00
plugins/last-human-commit/opencode/lhc-v2.ts
                                 bd709978fc5b9985901718a83cb34b76da3bc127166849c7855d803352de770c
tests/test_native_milestone_gate.py ec719cca51cb93156edf3d343cce1f4bcac9d44bd5158053b1c2e5f65e73ddfc
```

## Проверенные причины

1. **Нет исполняемой классификации quickfix/fullcycle/testing.** `lhc_milestone.py:19–50,145–170` имеет UI/BUILD/SMALL/READ_ONLY regex и поля expected/explicit/read_only. SMALL лишь снимает крупную UI-приёмку; это не класс quickfix с собственным canary. В `lhc_entry.py`, `lhc_milestone.py`, `lhc_time_guard.py` нет сохраняемого task_class или business-canary obligation. Общая инструкция о результате находится в `lhc_entry.py:26–44`; машинного guard для неё нет.

2. **Gate требует изменённую UI-поверхность или explicit UI acceptance.** `lhc_milestone.py:65–84` выбирает UI extensions либо HTML-подобный код, исключает tests/.agents/.tmp. `:200–219` создаёт pending лишь при required и `(surface or explicit or previous surface_key)`. Backend/CLI, работа с уже готовой сборкой и UI-задача без внесённой дельты могут остаться not-required. `tests/test_native_milestone_gate.py:204–210` прямо допускает Stop после нового UI-запроса без изменения поверхности. Business canary нужен по исходному actionable outcome, а не только после diff.

3. **Testing-only не имеет своего finish-критерия.** `lhc_milestone.py:192–193` возвращает read_only milestone до вычисления приёмки. `lhc_entry.py:202–204` дополнительно считает read_only причиной held для Stop. `tests/test_native_milestone_gate.py:198–202` объединяет minor, reviewer/tester и status в один тест «не нанимать». Не нанимать вложенных тестировщиков правильно; отсутствие проверки назначенного покрытия/raw observations — отдельная щель. Нельзя исправлять её принудительной разработкой или deploy в testing-only.

4. **Первый Stop — ограниченное напоминание, последующие не veto.** `lhc_entry.py:202–246` блокирует Codex/ZCode Stop только при overdue business/learning либо acceptance_due и отсутствии hold. Флаг continuation_requested ставится на весь milestone, а не на конкретный незакрытый этап. stop_hook_active пропускает повтор; новый turn без новых timer debts тоже пропускается. Pending сохраняется, но последняя реплика не анализируется как допустимое утверждение о завершении. `tests/test_native_milestone_gate.py:172–196` и `tests/test_codex_lifecycle_delivery.py:62–71` намеренно закрепляют это поведение. Поэтому не следует просто заменить его бесконечным block.

5. **При новой дельте одноразовый флаг не обновляется.** `lhc_milestone.py:216–219` меняет surface_key/changed_at/status/feedback, но сохраняет continuation_requested. Новый неподтверждённый UI может уже не получить даже первого продолжения. Это воспроизведено реальной observe-функцией с RAM Git-данными.

6. **UI accepted не равен доставленной исходной цели.** `lhc_milestone.py:400–465,467–504` проверяет свежесть, native source, чужой session, соответствие цели, browser action/result, personas и raw feedback; это полезная защита от fabricated PASS. Но accepted ставится по двум успешным попыткам, без technical-tests/deploy/publication/merge obligations. `lhc_entry.py:203–204` после accepted не имеет иного outcome gate. `lhc_time_guard.py:761–828` сохраняет jobs/наблюдения, причём action-result-observed намеренно не delivery. Проверки push/PR/merge в этих tools отсутствуют; `tests/test_business_first_contract.py:356–363` проверяет **текст** требований истории, не порядок операций. `tests/test_review_delivery_contract.py` также прямо ограничен доставленными инструкциями.

7. **Не все adapters способны остановить финал.** В entry ветка veto только `runtime in {codex,zcode}`. Для Claude, несмотря на общий Stop manifest, здесь нет такого veto. OpenCode v2 `opencode/lhc-v2.ts:16–18,46–49,81–102` сохраняет текст в pending и наблюдает Stop уже после `session.execution.succeeded`; не регистрирует pre-final veto и не запускает продолжение. `text()` не извлекает decision/reason, а при runtime=opencode entry их всё равно не выдаёт. Hermes adapter `adapters/hermes/plugin/__init__.py:155–177,333–343` регистрирует pre_llm и вызывает legacy guard, а не общий milestone Stop. Нельзя обещать одинаковую гарантию всех harness по одному Python-тесту.

8. **Hold иногда шире конкретного блокера.** `lhc_entry.py:144–161,202` и `lhc_milestone.py:180–191,243–265`: только structured HTTP error с target+operation распознаётся scoped. Generic nonzero/transport ToolFailure/session.error ставит общий hold и снимает Stop veto. `tests/test_native_milestone_gate.py` содержит structured-private-403, unstructured-private-error и PostToolUseFailure cases. Нужен разбор области; это не основание снять human-stop/auth hold или повторить запрещённый probe. В OpenCode execute.after при status=error идёт сразу ToolFailure, что также минует structured PostToolUse extractor.

9. **Notify вопрос вообще не часть finish-state.** В трёх tools нет human_request/notify transition. Live Herder schema уже имеет human_request_create/get/bind_notify_incident; create принимает native harness/sessionId, marker/locator/contextRef и message/notify, но явного Idempotency-Key в schema нет. Поэтому нельзя объявить exactly-once свойство сервиса по одному имени метода. Для нового finish-contract требуются ссылка на существующий request, проверенный delivery receipt и отдельный канонический ответ. Не создавался пробный вопрос пользователю.

10. **60/120 clocks уже живут отдельно от задач, но не заменяют finish.** `lhc_time_guard.py:575–603` ключует state runtime+session и находит primary checkout; `:605–676` сохраняет 120-minute wall due до evidenced ack. `:830–990` хранит original/latest prompt, активный monotonic интервал, 60-minute business debt; `:955` direction_reviewed имеет milestone_acceptance=not_evaluated. Entry `:68–106,169–201` восстанавливает цель/ссылки и pending при compaction. `:112–114` создаёт отдельный subagent identity; автоматической передачи parent canary/owner child-у нет. Родительские часы не надо сбрасывать или закрывать ответом ребёнка. Это уже рабочий фундамент, не повод создавать ещё таймер/daemon.

Hooks fail-open при недоступном entry: installed/source `hooks/hooks.json` shell fallback сохраняет обработку сообщений; `lhc_entry.py:277–282` отдаёт warning, не finish veto. `tests/test_hook_command_failure.py:20–34` это закрепляет. Правильно сохранять доступность, но отсутствие контроля явно остаётся UNKNOWN, а не PASS.

## Что воспроизведено без записи состояния

Запуск `python3 -B -` компилировал текущие source-файлы через `compile/exec` в Modules в памяти. Для observe заменены только Git/candidates/file_hash; для actual `lhc_entry.handle` — guard persistence, Path/lock и возвращаемый milestone. Native CLI hooks, subprocess builds, browser/provider calls не вызывались. Это branch-level evidence; не consumer/native integration acceptance.

Три assertions желаемого поведения исполнены и дали RED:

```text
R1_backend_canary: RED: actionable non-UI goal has no required business canary
R2_quickfix_class: RED: quickfix class is not persisted
R3_testing_coverage: RED: testing-only has neither coverage nor raw observation obligation
```

Остальные результаты фактического control flow:

| Вход | Наблюдение |
|---|---|
| `Implement retry handling in the CLI and verify the real command` | expected=false, read_only=false, status=not-required; canary/class отсутствуют |
| `Fix a small CSS padding issue in the dashboard` | expected=false, status=not-required; class отсутствует |
| `You are a fresh Zero Knowledge tester. Try the UI goal, do not modify code.` | read_only=true, status=not-required; coverage отсутствует |
| `Status of the dashboard?` | status=not-required; отсутствие canary здесь корректно |
| Pending UI, первый Stop | decision=block; continuation_requested=true |
| Pending UI, stop_hook_active=true | decision отсутствует; pending остаётся |
| То же pending, новый turn | decision отсутствует; pending остаётся |
| accepted UI, нет delivery/deploy/push records | decision отсутствует |
| pending UI + generic ToolFailure hold | decision отсутствует; pending остаётся |
| not-required + running_jobs[42] | decision отсутствует; job сохраняется |
| Новая UI hash при continuation_requested=true | surface_key изменён, status=pending, continuation_requested остался true |

Это не утверждение, что hook написал ложный PASS: он допускает финал и предупреждает о долге, но не контролирует весь критерий завершения.

## Рабочее → идеальное → полезный 80% MVP

**Рабочее целиком.** Расширить существующее состояние бизнес-задачи в learning JSON, а не строить сервис. На обычном actionable prompt сохранять класс, исходный outcome/canary, delivery owner и применимые обязательства. На tool/native evidence обновлять только доказанный этап. На finish вычислять completed либо pending/running/blocked/human-stopped; показывать следующий доступный шаг. Ответ ребёнка закрывает только назначенную ему проверку, не родительскую цель.

**Идеальное.** Каждый действующий harness имеет проверенный native pre-final gate; доказательства относятся к конкретной версии кода, среде и поверхности, typed blockers адресуют ровно операцию; реальные CI/deploy/PR/native tool receipts механически сверяются с потребительским результатом. Handoff восстанавливает lineage, вопросы и clocks, разные реальные personas закрывают milestone, а не метаданные. Это требует отдельных consumer canaries adapters и проверки доступных native возможностей; текущий OpenCode observer не обладает pre-final veto.

**80% MVP.** Один компактный outcome-блок в уже существующем business state; общий evaluator, вызываемый entry/доступными adapter boundaries; адаптация существующих tests. Сохранить действующий bounded Stop, разрешить честный terminal pending, но не обозначать его complete. Не делать universal shell-language parser, новый controller, scheduler, второй evidence registry или автоматическое hiring. Сначала Codex/ZCode поддерживаемая ветка плюс OpenCode context/compaction с честным `observer-only` пределом; остальные adapters не объявлять защищёнными до отдельного доказательства. Canary и testing-only coverage входят в минимум полностью, не вырезаются ради 80%.

### Минимальное состояние (предложение, не существующая схема)

В существующем `business`:

```text
outcome:
  id, owner(harness,native_session), parent_outcome_ref?
  original_source, accepted_goal, latest_constraints, project, owned_scope
  task_class: quickfix | fullcycle | testing | research | status
  canary?: scenario + target + expected_observation + evidence_refs + status
  obligations[]: kind + target + applicable + status + source_revision + evidence_refs
  blockers[]: operation + target/resource + evidence + required_change + request_ref?
  finish_verdict: pending | running | blocked | human-stopped | complete
  last_continuation_fingerprint
```

Не хранить auth-разрешения в state: прямые user sources — контекст, окончательны harness policy/human-stop/новейшая ревокация. Применимость этапа имеет причину/source; `not-applicable` не равно «агент решил не делать».

| Класс | Критерий результата |
|---|---|
| quickfix | Наблюдаемое исправление, focused RED/GREEN для бага, реальный узкий canary; только применимая доставка. Не обязательная большая focus group для каждой опечатки. |
| fullcycle | Technical gates → разрешённый deploy → hands-on и применимая независимая milestone-приёмка → final push/PR → разрешённый ownrepo merge. |
| testing | Назначенное coverage, raw observations/tool refs, результат каждого сценария и ограничения. Defect report может быть полным **результатом тестирования** при неуспешном продукте; не принуждать к разработке/деплою или вложенному найму. |
| research | Проверенные причины/источники и требуемый evidence artifact. Не наследовать implement/deploy/merge obligations. |
| status | Ответ по состоянию; canary/deploy не требуются. Нельзя status-вопросом стирать уже активную исходную инженерную цель. |

### Переходы и завершение

1. `entry → anchored`: классификация по цели/контексту без выбора режима пользователем; для actionable goal сохраняется наблюдаемый canary. Уточнение/карточка/peer message не создаёт новую цель; явная замена пользователя сохраняет lineage и меняет применимость.
2. `anchored → technical-ready`: реальные relevant checks, для бага RED → fix → GREEN. Commit/лог/решение direction-review отдельно от результата.
3. `technical-ready → deployed`: только разрешённая среда, прошедшие gates, установленная ревизия и native job/result. Running/UNKNOWN не считается deployed и не повторяется.
4. `deployed → hands-on/acceptance`: результат целевого действия на нужном runtime. UI login-only/demo вместо требуемого private не закрывает весь canary. Применимая независимая приёмка сохраняет raw feedback, включая позитивное и критическое/честные ограничения.
5. `accepted → published → integrated`: final scoped push/PR, затем ownrepo merge только если разрешён. LHC разрешён в исходном outcome-contract; Airlock external — PR54/new-frontend, **без main push/merge/auto-merge**. Владение repo и полномочия проверять по реальным данным, не по слову «мой» в peer message.
6. Если CI/deploy требует раннего branch push: отдельный **staging-push exception** с причиной/dependency/ref. Это не final acceptance и не разрешение обходить gates; после deploy/hands-on закончить final publication. Разрешённые локальные checkpoint commits не меняют порядок доставки.
7. `any → blocked(scope)`: точное доказательство и требуемое изменение; независимые действия доступны. Provider quota/auth/transport не смешиваются; unknown availability не PASS и не разрешение заменить модель. Когда остался реальный вопрос человеку — существующий bound Notify/AskHuman request; нет вопроса — не слать вымышленный approval request.
8. `question-needed → request-created → delivery-confirmed → answered`: отдельные состояния. Сохранять request_id и native binding/receipt; фактический ответ читать по canonical request result. Created/delivered/expired — не answer и не permission. Exactly-once логически обеспечивать стабильной идентичностью вопроса и сверкой уже принятого/UNKNOWN результата; не обещать сетевое exactly-once и не повторять side effect после timeout. Учитывать штатную escalation существующего сервиса, не добавлять cron.
9. Stop: сначала вычислить все обязательства. `complete` только при необходимых evidence. Human-stop/permission hold всегда прекращает автопродолжение; неполный результат остаётся pending/blocked. Одна bounded continuation на новую доказанную actionable state-delta; повтор того же Stop без прогресса — честный terminal pending, **не** endless continue. Новый turn ID сам по себе не прогресс. Новый surface/canary version меняет fingerprint, а не сохраняет вечный continuation_requested.
10. Compaction/resume/children сохраняют outcome owner/id, canary, scope, blockers/questions, running job IDs и текущие clocks. Дочерняя задача имеет bounded scope/ref к родительскому outcome; её complete не закрывает родительские обязательства или 60/120 debt. Не суммировать пересекающиеся интервалы. Паузы/неизвестные интервалы учитывать по существующим правилам, без нового таймера.

Ограничение: hook, который разрешил terminal pending, не может сам гарантировать текст следующей финальной реплики модели. Для строгого запрета видимого ложного успеха нужен реально поддерживаемый native final gate; observer-only harness честно ограничивается persisted verdict/context. Не выдавать мягкое напоминание за механическую гарантию.

## Точные места минимальной реализации и behavioral regressions

Все изменения ниже — рекомендации владельцу реализации; в этом исследовании не выполнены.

| Файл/место | Минимальная работа | Проверка поведения |
|---|---|---|
| `src/common/tools/lhc_time_guard.py:695–709,830–990` | Расширить existing business outcome, сохранить прямые источники, owner/class/canary/обязательства; evidence transitions отдельно от review. | Original canary не теряется после status, correction, child result, карточки, compact; direction-review не закрывает deploy/canary. |
| `src/common/tools/lhc_entry.py:68–106,108–131,202–246` | Rehydrate outcome; общий finish verdict; bounded continuation fingerprint; различать безопасную остановку и complete. | Technical-green до deploy не даёт complete; pending переживает Stop без бесконечного продолжения; новое доказанное изменение снова проверяется. |
| `src/common/tools/lhc_milestone.py:40–50,145–224,400–504` | Оставить специализацию независимой UI-приёмки, убрать роль единственного canary; связать freshness с outcome/environment; обновлять debt при дельте. | backend/CLI canary обязателен; accepted UI без доставки не полный результат; stale feedback/демо вместо private не закрывают target. |
| `plugins/last-human-commit/opencode/lhc-v2.ts:16–49,52–79,81–102` | Сохранять общий verdict в consumed context/compaction; typed scoped tool failures. Проверить native pre-final возможность до обещания veto. | Context перед моделью содержит исходный canary/блокер; execution.succeeded не превращается в completed outcome; interrupted не продолжается. |
| `adapters/hermes/plugin/__init__.py:155–177,333–343` и фактический installed пакет | По отдельной разрешённой реализации привести adapter к shared outcome и проверить установку; не патчить cache вручную. | Ordinary native prompt/compact сохраняют scope/clocks; установленная версия засвидетельствована; нет фиктивного Stop veto. |
| `src/common/protocols/REVIEW_TO_DELIVERY.md:43–89`, `AGENTS.md` | Явно описать новые классы, порядок, staging exception и разрешённый partial/testing финал. | Текстовые tests вспомогательные, не достаточные. |
| `plugins/last-human-commit/scripts/sync_skills.py:195–246` | Генерировать tools/common/native Codex facets штатным путём. | После реализации `python3 plugins/last-human-commit/scripts/sync_skills.py --check`; затем штатная установка и отдельный native consumer. |

Регрессии добавлять в существующие suites; описания ниже — ожидаемые assertions, не уже пройденные tests:

1. `tests/test_native_milestone_gate.py`: **non_ui_ordinary_goal_requires_canary**, **quickfix_requires_focused_consumer_result**, **preexisting_build_requires_deploy_without_ui_diff**. Вызвать обычный prompt → technical evidence → Stop до canary; assert verdict != complete, обязательство живо. Сейчас первые случаи теряют debt до Stop.
2. Там же: **accepted_ui_is_not_fullcycle_delivery**. Дать два настоящих fixture-transcripts → UI accepted; deploy/publish/merge ещё отсутствуют → outcome pending. Затем ровно нужные transitions дают complete. Backend HTTP 200 без исходного действия не считается hands-on.
3. `tests/test_native_milestone_gate.py`, `tests/test_codex_lifecycle_delivery.py`, `tests/test_zcode_native_lifecycle.py`: **bounded_stop_keeps_incomplete_verdict**, **surface_delta_reopens_finish_check**. Первый Stop продолжает; повтор без прогресса не повторяет side effects и не даёт complete. Новая surface/revision инвалидирует старую приёмку и старый fingerprint. Сохранить существующие human Interrupt/permission tests.
4. `tests/test_native_milestone_gate.py`: **testing_only_requires_coverage_raw_observations**. Тестировщик без tools/наблюдений не completed; выполненное назначенное покрытие с подтверждённым дефектом и честным report — completed testing result, product=changes-required; ноль code/deploy/recruitment calls. Отдельно status prompt — никакого canary. Сейчас эти различия отсутствуют.
5. `tests/test_business_checkpoint.py`, `tests/test_learning_checkpoint.py`, `tests/test_codex_lifecycle_delivery.py`: **parent_outcome_survives_child_and_compaction**. Parent started 0; child/новая карточка/compact не меняют parent canary, active-3600 debt или wall-7200 due. Только evidenced ack с matching id сдвигает соответствующий timer; child ack не закрывает parent. Существующие pause/reconnect/worktree/no-card tests сохранить.
6. `tests/test_native_milestone_gate.py`, `tests/opencode-review-delivery.test.ts`: **scoped_quota_or_private_blocker_leaves_demo_actionable**. Подтверждённый отказ ровно target не становится общим stop для независимого разрешённого действия; ни probe replay, ни auth/model fallback. Running native job ID сохраняется до того же job/result, ноль duplicate/cancel.
7. `tests/test_review_delivery_contract.py` расширить из string assertions до event behavior; `tests/opencode-review-delivery.test.ts`: **fullcycle_order**, **ci_staging_push_is_not_final**, **external_repo_never_merges**, **own_repo_merge_requires_current_gates**. Ledger вызовов: tests → permitted deploy → target hands-on → final push/PR → разрешённый ownrepo merge. Единственное раннее push допускается с реальной CI dependency; запрет подавить checks/force merge сохраняется.
8. `tests/test_native_milestone_gate.py` / adapter mock существующего human-request API: **notify_receipt_is_not_answer**, **unknown_send_is_not_replayed**, **answer_bound_to_exact_native_target**. Повтор Stop/compact не создаёт второй вопрос; существующий request остаётся pending после delivery; чужой/неподтверждённый ответ ничего не разрешает. Не отправлять реальный тестовый вопрос человеку ради unit test.
9. `tests/opencode-milestone.test.ts`, `tests/opencode-v2.test.ts`: **observer_cannot_claim_finish_veto**, **pending_verdict_reaches_next_context_and_compaction**. Проверить реальную capability, а не только отсутствие ошибки TS. `adapters/hermes/plugin/tests/test_plugin.py`: аналогичный state/context test, без обещания unsupported veto.

После реализации достаточно targeted suites, parity, затем отдельно разрешённая установка/test deployment и fresh ordinary native prompts на реальных поверхностях. Сохранять native session/job IDs и полные task-relevant raw observations. Минимальный набор native acceptance: quickfix CLI; testing-only с найденным дефектом; fullcycle с CI staging-push исключением; scoped quota/private blocker с доступным demo; external PR-only; compaction/child continuity. Не повторять известные safetyblocked probes. Зелёные fixtures не заменяют эту приёмку, а независимый researcher report не является multimodel council или focus group.

## Самый короткий следующий шаг

Единственному назначенному владельцу реализации: добавить RED на outcome/class/canary и bounded pending verdict в существующие suites, затем расширить existing business state/entry. Сначала доказать Codex/ZCode контракт и честный OpenCode observer-предел; доставку пакета и остальные runtime проверить отдельно по полномочию. Этот отчёт готов для такого назначения; кодовый дефект здесь не исправлен и live finish guarantee остаётся неподтверждённой.
