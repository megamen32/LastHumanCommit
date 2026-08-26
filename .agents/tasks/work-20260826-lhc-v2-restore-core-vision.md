# work-20260826 — LHC v2: вернуть ядро видения (аудит истории + план)

Started at: 2026-08-26 18:50 (UTC+3), источник: часы сессии ZCode; active minutes: не контролировал на момент записи.

## Запрос пользователя (исходник)

Прошлый GPT «всё сломал». Ранние коммиты — ручные. Идея проекта: самонаблюдение,
самоэволюция, слежение за ошибками и файлами чтобы не ломалось, против ритуалов,
против зацикленности на секретах (env-чтение должно быть нормой; AskSecret-показуха
— убрать и жёстко пресекать). Расширить: обязательное планирование минимального
короткого бизнес-пути (ladder → YAGNI, вертикальные срезы, референс fast-agent),
самоэволюция как в Ouroboros, бенчмарк/самоулучшение промптов как future-agi,
реальное автотестирование через browser/computer use (НЕ тест-файлы). Reviewer и
Critic — бесполезны. Overseer — полезен, должен быть главнее всех, с жёсткой
фиксацией времени через uptime в начале, и пресекать дрейф в безопасность/ерунду:
критерий — осязаемый результат, проверяемый реальным тестированием.

## Аудит истории (2026-08-26)

- Ручной базис: `3e41520`, `e5e2f0d`, `ad89b82` ("manual"), `ed94f6a` ("my own") —
  всё 2026-07-27. Дерево `ed94f6a` = 22 файла: AGENTS.md, README, 7 ролей,
  3 профиля, STOP_RETHINK, шаблоны .agents, tests/validate.py. Простой канон.
- Далее 108 коммитов, +14004/−668 строк, 190 файлов. Основной рост: tests/ (10
  файлов, 1235 строк), protocols (6), plugins/, adapters/hermes, capabilities,
  install_http_capabilities.py, marketplace.
- Прямое нарушение собственного контракта: `AGENTS.md` (maintainer) требует
  «No harness hooks, plugins, network fetches, or dependencies», но `77629a5`
  (08-07, Ask Secret contract), `059bc8d` (08-12, require HTTP AskSecret/AskHuman),
  `898c901`/`64290f2` (08-14, marketplace-плагины ask-secret/ask-human) построили
  ровно это: HTTP-инфраструктуру и плагины для передачи пароля.
- Деплой-фрагментация: `~/.zcode/AGENTS.md` — устаревшая ритуальная версия от
  08-08 (todo/work/done, append-only); `current` → `versions/059bc8d` (роли
  business-first); repo AGENTS.md — третья (компактная) версия. Три канона в бою.
- Overseer в текущем каноне «optional, risk-triggered» (итог 08-10/08-12) →
  фактически не вызывается; стартовая фиксация времени в ZCode не выполняется
  никаким хуком (нативные хуки time guard есть только для Codex/Hermes/OpenCode).
- SELF_IMPROVE.md — пассивный журнал (записи «Proposed» никогда не применяются).
  Самоэволюции как цикла (патч → проверка → коммит) нет.
- Tester.md уже требует реальную поверхность — совместимо с запросом; культура
  tests/*.py-валидаторов формулировок (validate.py 363 строки) — ритуал.

## Внешние референсы (2026-08-26)

- future-agi: платформа самоулучшающихся агентов — evals + tracing + simulations,
  «turn every trace into signal for the next version»; один feedback-loop.
- fast-agent (evalstate/fast-agent): паттерн `evaluator_optimizer` — generator +
  evaluator + min_rating (EXCELLENT/GOOD/FAIR/POOR) + max_refinements; bounded
  цикл «сгенерировал → оценил → докрутил». Это «ladder»-механика для канона.
- Ouroboros (arXiv 2608.08311): self-developing агент — tools/context/prompts/core
  улучшаются через reviewed commits; эволюция собственного харнесса.

## План (Full, два маршрута)

### Маршрут 1 — хирургия + ядро v2 (рекомендован)

1. Удалить: `plugins/ask-secret`, `plugins/ask-human` (+ marketplace.json/README),
   `scripts/install_http_capabilities.py`,
   `src/common/tools/install_http_capabilities.py`,
   `src/common/capabilities/human.ask_secret.v1.yaml`,
   `src/common/capabilities/human.ask_user.v1.yaml`,
   `tests/test_install_http_capabilities.py`,
   роли `Adviser.md`/`Critic.md`/`Reviewer.md`.
2. Lead.md: секреты — напрямую env/.env/файл, ≤1 шаг, ЗАПРЕТ строить
   секрет-инфраструктуру/аттестацию; обязательный мини-план «минимальный путь»
   (цель → канарей → YAGNI-ступень → что НЕ делаем); финал юзер-видимой работы —
   реальная проверка на живой поверхности; gates: Overseer на каждом часе/овerrun.
3. Overseer.md: верховный контроллер маршрута; время фиксируется в начале (uptime),
   без стартовой записи цикл не начинается; пресекает дрейф в безопасность и любую
   работу без осязаемого результата; критерий — результат, проверяемый реальным
   тестом; вызов обязателен на пересечении часа, overrun и перед финалом Full.
4. Tester.md: единственный финальный гейт — browser/computer use на реальной
   поверхности; тест-файлы пользовательским результатом не считаются.
5. TIME_CONTROL.md: первая строка цикла — `Started at <ISO> (uptime: <источник>)`;
   честное «не контролировал» вместо выдумки.
6. SELF_IMPROVE.md: цикл вместо журнала — триггер → запись с мини-патчем (diff) →
   пакетное применение через задачу self-evolve с канарей-проверкой (Arena или
   ручной канарей) перед коммитом (Ouroboros-style reviewed commits); повтор
   ошибки → fingerprint → guard-строка.
7. AGENTS.md (repo) + ~/.zcode/AGENTS.md: роутер v2 (Lead/Worker/Explorer/
   Overseer/Tester), анти-секретная строка, минимальный путь обязателен.
8. tests/validate.py: убрать проверки формулировок удалённых сущностей, оставить
   структурную согласованность.
9. ZCode SessionStart-хук (~/.zcode/hooks): пишет
   `.agents/shared-session/time/<session-id>.json` со стартовым UTC от реальных
   часов — жёсткая фиксация времени в этом харнессе.
10. Редеплой `current` через сущ. rollout-механику.

Канарей Маршрута 1: новый ZCode-сесс видит роутер v2 + старт-фиксацию времени;
`rg AskSecret src/` пуст; Overseer-мандат на месте; Marketplace без ask-*.

Оценка: min 60 / max 150 активных минут.

### Маршрут 2 — перезагрузка к ручному ядру

Канон с нуля ~200 строк (Lead/Worker/Overseer/Tester + TIME/SELF_IMPROVE),
удалить хуки/плагины/адаптеры/compaction-инфраструктуру, tests/ → 1 файл,
self-improve сразу в evaluator_optimizer-цикл с Arena-гейтом. Минусы: теряем
работающие compaction continuity/time guard для Codex/Hermes/OpenCode, дольше
(240–480 мин), выше риск регресса флота.

## Прогресс

- 2026-08-26 18:50 — audit complete (git history, deployed state, protocols,
  validator, plugins, external refs indexed). Route 1 selected by user.
- 2026-08-26 21:00 — Route 1 implemented: canon v2 written (AGENTS/CLAUDE,
  Lead, Overseer, Tester, TIME_CONTROL, SELF_IMPROVE, task template);
  Adviser/Critic/Reviewer + secret-theater infra deleted (capabilities/,
  install_http x2, plugins/ask-*, marketplace entries); adapters x5,
  agent-authoring, FULL_CYCLE, RELEASE_HANDOFF, README, hermes profiles
  cleaned; validate.py + test_business_first_contract.py rewritten to v2
  contract; lhc_time_guard AskHuman string fixed (+ plugin copy).
- 2026-08-26 22:05 — zcode SessionStart time-anchor hook installed
  (~/.zcode/hooks/lhc_time_start.sh + repo adapters/zcode/hooks/ +
  config.json registration, backup config.json.bak-lhc-time-20260826),
  self-test OK. Validators: validate.py PASS, 37 pytest PASS,
  task_states PASS, marketplace PASS (entries=1), hermes plugin 10 PASS.
  Fixed pre-existing drift: test_native_time_guard_hooks stale event set.
- Leftover AskSecret/AskHuman/NoticePlace mentions are intentional
  prohibition lines (AGENTS/CLAUDE/Lead), test forbid-lists, and ROADMAP
  history.
