# Outcome-first canon correction

Status: Reviewer APPROVE; Critic route corrections pending release execution
Session: 019fbe04-b90d-7703-af85-9e5671758e6a
Current stage: Ultimate
Pre-implementation Overseer decision: APPROVE
YAGNI evidence: routers byte-identical; owned diff check clean; validator
advances to the first Normal-only contract in Overseer.md.
Post-YAGNI Overseer decision: APPROVE
Normal evidence: role/profile/template diffs clean; validator advances to the
first Ultimate-only Russian-plan contract in templates/FULL_CYCLE.md.
Post-Normal Overseer decision: APPROVE
Ultimate source evidence: canonical validator PASS; block adapter PASS; Hermes
plugin 4/4; routers byte-identical; git diff check clean.
## Post-Ultimate Overseer decision history (append-only)

- Timestamp: 2026-08-01 (exact time not recorded)
  Stage: Ultimate release gate
  Evidence: Out-of-scope mixed self-improve content was present in the
  worktree.
  Decision: STOP_SCOPE_DRIFT
- Timestamp: 2026-08-01 (exact time not recorded)
  Stage: Ultimate release re-gate
  Evidence: Exact release staging exclusions preserve the concurrent
  self-improve entry and generated Graphify artifact untouched.
  Decision: APPROVE

Release staging is restricted to:

- .agents/tasks/work-20260801-outcome-first-canon.md
- AGENTS.md
- CLAUDE.md
- README.md
- ROADMAP.md
- docs/agent-authoring.md
- src/common/agents/Lead.md
- src/common/agents/Overseer.md
- src/common/agents/Reviewer.md
- src/common/agents/Worker.md
- src/common/profiles/Code.md
- src/common/profiles/Infrastructure.md
- src/common/profiles/Planning.md
- src/common/profiles/Test.md
- src/common/protocols/STOP_RETHINK.md
- src/common/templates/.agents/tasks/task_template.md
- templates/FULL_CYCLE.md
- templates/RELEASE_HANDOFF.md
- tests/validate.py

Explicitly excluded from staging and release:

- .agents/last-human-commit/self-improve.md (mixed current-task and unrelated
  concurrent Graphify/OmniRoute entries; preserve untouched);
- graphify-out/ (generated analysis artifact).

Reviewer decision history:

- First review: CHANGES_REQUIRED - STOP_SCOPE_DRIFT terminal behavior, execution
  language, full policy validation, append-only Overseer history, and stale task
  status required direct fixes.
- First fix evidence: validator red on the missing append-only history contract, then
  PASS after the protocol, template, validator, and task-record fixes.
- Second review: CHANGES_REQUIRED - the initial three-plan presentation remained
  in English and the task review status was stale.
- Translation fix applied: the initial three-plan presentation is now in Russian
  and the task status records the final review gate.
- Final re-review: APPROVE, no findings.

Pre-release Critic decision: CHANGES_REQUIRED

- TelegramAuto resolves its project-local .last-human-commit path, not global
  current; both runtime surfaces require explicit synchronization.
- Publication must follow live proof, not precede it.
- Rollback must preserve the old global current target and a durable
  TelegramAuto backup beyond marker-tool cleanup.

Corrected release order:

1. Revalidate and create the local source commit from the exact release list.
2. Do not push yet.
3. Build a temporary immutable version from the commit object, verify it, then
   atomically rename it into versions/<commit>.
4. Preserve global current target and durable TelegramAuto project-local
   rollback assets.
5. Switch global current and atomically synchronize TelegramAuto's actual
   resolved project-local LHC files; apply only its AGENTS marker while
   preserving project-owned text.
6. Prove source/install/resolved-route digests, mandatory contracts, outside-
   marker preservation, project outcome text, and rollback assets.
7. On failure, restore both runtime surfaces. On success, record evidence and
   complete M6.2 in a second evidence-only commit.
8. Push both commits once.

Estimate history:

- Initial: 45 / 70 / 110 active minutes.
- Revised after repository graph, red-test design, and Overseer decomposition:
  55 / 80 / 120 active minutes.
- Revision reason: the selected scope now includes mandatory estimate history,
  exact-path scope gates, three staged Overseer checks, and applied-runtime
  verification.

## Objective and acceptance

Objective: an LHC-enabled agent attempts and proves the shortest safe real
business outcome before spending work on secondary quality, observability,
security, secret, permission, schema, database, provider, or broad-review
concerns.

Canary: given a failed or missing real business canary plus an unrelated
secondary finding, the normative instructions require blocker-chain diagnosis
only and forbid scope expansion. Given a green canary plus a direct regression
introduced by the selected diff, bounded relevant review remains required.

Acceptance proof:

- a red instruction regression fails on `fd3165d` because whole-repository
  review is unconditional and no validator enforces canary precedence;
- the green validator enforces objective, canary, status, allowed scope,
  deferred secondary audits, and direct-regression-only review;
- canonical source, marker-block application, and a new immutable installed
  version are byte-consistent while project-owned text stays unchanged;
- a bounded applied TelegramAuto check preserves its project-specific outcome
  rule and contains the new global precedence gate;
- source commit, tests, active `current`, and runtime digests are recorded.

## Confirmed research

- `fd3165d` added the correct outcome-first paragraph to `Lead.md` and is active
  under `versions/fd3165d` byte-for-byte.
- `Lead.md` still mandates whole-repository review and fixing all in-scope
  defects; `Reviewer.md` immediately expands into security, permissions, data
  integrity, operability, and recovery.
- `tests/validate.py` protects the literal `Review the whole repository` but has
  no ordering or scope-expansion regression.
- README, authoring docs, and roadmap repeat whole-repository breadth as a goal.
- The graph connects Lead, Reviewer, Full Cycle, docs, roadmap, and adapters;
  changing Lead alone cannot make the rule durable.
- `/home/roomhacker/agents-projects/LastHumanCommit` is authoritative. The old
  `_publish/LastHumanCommit` path is absent. Local `main` is one commit ahead of
  `origin/main`.

## Планы

### 1. Максимально идеальный

Объем: установить хорошо заметный глобальный шлюз приоритета в обоих роутерах и
согласовать Lead, Worker, Reviewer, профили Code/Test/Infrastructure, Full Cycle,
README, руководство по авторингу, roadmap и валидаторы. Добавить текстовые
поведенческие фикстуры для случаев failed-canary/unrelated-hardening,
green-canary/direct-regression и явно заданной hardening-objective. Повторно
применить маркер к TelegramAuto, создать новую неизменяемую установленную версию
из проверенного коммита, атомарно переключить `current`, проверить дайджесты и
разрешение инструкций в рабочей среде, выполнить commit и push.

Исключения: никакой несвязанной работы над приложением, безопасностью, DB,
Grafana или провайдерами; никакой массовой переработки принадлежащего проекту
текста за пределами блоков маркера.

Компромиссы и риски: самая сильная защита от повторения проблемы и самый ясный
межролевой приоритет; больший объем дублирующего защитного текста и более широкий
diff документации требуют тщательной проверки согласованности. Миграция — одно
повторное применение маркера и одна новая неизменяемая локальная версия. Оценка:
`35 / 55 / 90` активных минут, относительная стоимость средняя; два ограниченных
отчета Luna/Explorer уже готовы, достаточно одного Luna Worker и одного Luna
Reviewer, а также одного Critic перед выпуском.

Проверка: красный/зеленый валидатор, набор тестов block-adapter, тесты плагина
Hermes, побайтовая идентичность роутеров, сохранение маркера TelegramAuto,
дайджесты установленного источника и проверка на отложенном сценарии инструкций.

### 2. Нормальный

Объем: сузить проверку всего репозитория в `Lead.md` до прямых регрессий после
canary; согласовать Reviewer, Full Cycle, README, руководство по авторингу,
roadmap и валидатор. Установить новую неизменяемую версию и повторно применить
TelegramAuto.

Исключения: без заголовка в роутере и без изменений Worker или опциональных
профилей; только статические фикстуры порядка. Компромисс: изменение меньше и
проще для проверки, но роль или профиль, загруженные без контекста Lead, все еще
могут отдавать вторичной работе завышенный приоритет. Миграция включает то же
обновление установленной версии и маркера. Оценка: `20 / 30 / 50` минут,
относительная стоимость низкая-средняя; Luna Worker и Reviewer.

Проверка: сфокусированный красный/зеленый валидатор, тесты адаптеров, дайджест
источника/рабочей среды и сохранение маркера TelegramAuto.

### 3. YAGNI MVP

Объем: усилить существующий абзац Lead, заменить безусловную проверку всего
репозитория формулировкой о цепочке зависимостей/прямой регрессии и обновить один
литеральный валидатор. Установить в новую активную версию только новый файл Lead.

Исключения: Reviewer/docs/templates/profiles и маркер TelegramAuto остаются без
изменений. Компромисс: самый быстрый обратимый временный вариант, но он сохраняет
противоречащие друг другу поверхности и, вероятно, снова приведет к регрессии.
Оценка: `8 / 12 / 20` минут, относительная стоимость низкая; дополнительный
дочерний агент не требуется.

Проверка: валидатор, проверка diff, дайджест источника/рабочей среды.

## Рекомендация

Выбрать `Максимально идеальный`. Он соответствует явному запросу исправить
правило везде и устраняет подтвержденное валидатором противоречие, а не добавляет
поверх него еще один абзац.

## Выбор пользователя

Выбран Ultimate perfect totally ideal с обязательными дополнениями:

- task card создается для каждого запроса, включая Direct и Short;
- первоначальная и уточненная оценки обязательны;
- Ultimate по умолчанию доставляется последовательными рабочими слоями
  YAGNI -> Normal -> Ultimate;
- Overseer вызывается обязательно и останавливает любое неподтвержденное
  расширение задачи;
- безопасность, секреты, PII, permissions, ACL, DB/schema, Grafana, логи и
  provider-аудиты запрещены, если пользователь их не просил и они не являются
  минимальной предпосылкой безопасного запуска подтвержденного canary;
- первоначальные планы и финальный ответ - по-русски; промежуточная техническая
  работа после выбора плана - строго по-английски.

## Представление выбранного плана

### Call-stack tree

    Запрос пользователя
    └─ Router: создать task card и первоначальную оценку
       └─ Lead: зафиксировать outcome, canary, confirmed scope и exclusions
          └─ Три первоначальных плана на русском
             └─ Явный выбор пользователя
                └─ Overseer: scope gate
                   ├─ YAGNI: минимальный реально работающий слой
                   │  └─ Overseer: сверка с исходным запросом
                   ├─ Normal: надежный и поддерживаемый слой
                   │  └─ Overseer: повторная сверка scope/outcome
                   └─ Ultimate: только подтвержденная полнота
                      ├─ Overseer: финальный scope gate
                      ├─ Reviewer: correctness выбранного diff
                      ├─ Critic: один pre-release challenge
                      ├─ immutable install + marker apply + live digest proof
                      └─ финальный ответ на русском

### File-tree diff

    AGENTS.md / CLAUDE.md
    ├─ mandatory task + estimate gate
    └─ phase language contract
    src/common/agents/
    ├─ Lead.md       staged Ultimate, confirmed scope, mandatory Overseer
    ├─ Overseer.md   hard scope-drift decision contract
    ├─ Worker.md     task/scope/outcome execution boundary
    └─ Reviewer.md   post-canary direct-regression review only
    src/common/profiles/
    ├─ Planning.md   estimate for every task
    ├─ Code.md       no unsolicited quality/security expansion
    ├─ Test.md       no unrelated failing-test expansion
    └─ Infrastructure.md no unsolicited hardening/audit
    src/common/protocols/
    └─ STOP_RETHINK.md unauthorized-scope stop path
    templates/FULL_CYCLE.md
    └─ Russian plan / English execution / Russian final
    templates/RELEASE_HANDOFF.md
    └─ Russian final contract
    src/common/templates/.agents/tasks/task_template.md
    └─ mandatory task, estimate history, stage, and Overseer fields
    README.md / docs/agent-authoring.md / ROADMAP.md
    └─ aligned public and authoring contract
    tests/validate.py
    └─ red/green precedence, task, estimate, Overseer, staging, language gates

### Key contracts

    TaskRecord = {
      original_user_request, objective, canary, confirmed_scope, exclusions,
      initial_estimate: { optimistic, likely, pessimistic },
      revised_estimates: [{ trigger, evidence, optimistic, likely, pessimistic }],
      status
    }

    SecondaryWorkPolicy = {
      prohibited_by_default: [
        security, secrets, PII, permissions, ACL, database, schema,
        Grafana, dashboards, observability, logs, provider_audits
      ],
      allowed_only_if:
        user_confirmed_objective
        OR minimal_prerequisite_for_safe_confirmed_canary,
      violation: STOP_SCOPE_DRIFT
    }

    OverseerDecision = APPROVE | STOP_SCOPE_DRIFT
    UltimateStage = YAGNI | NORMAL | ULTIMATE
    LanguagePhase = INITIAL_PLAN_RU | EXECUTION_EN | FINAL_RU

Implementation starts with a failing validator against fd3165d, then lands
YAGNI, Normal, and Ultimate as separately verifiable slices.
