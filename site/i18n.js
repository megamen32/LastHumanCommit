/* UI translations only. Canonical Git files and source excerpts are not translated. */
(() => {
  "use strict";
  const STATIC = []; // All current landing copy uses explicit data-copy keys.
  const ATTRS = [
    [".brand", "aria-label", "Last Human Commit, back to top", "Last Human Commit — наверх"],
    [".nav-links", "aria-label", "Main navigation", "Основная навигация"],
    [".lang-switch", "aria-label", "Site language", "Язык сайта"],
    ["[data-lang='en']", "aria-label", "Switch to English", "Переключить на английский"],
    ["[data-lang='ru']", "aria-label", "Switch to Russian", "Переключить на русский"],
    [".strip", "aria-label", "Principles in brief", "Основные принципы"],
    [".mode-controls", "aria-label", "Workflow to explore", "Выбор рабочего цикла"],
    ["#cycle-nodes", "aria-label", "Click a stage to inspect its source", "Выберите этап, чтобы прочитать его описание"],
    ["#full-depth-steps", "aria-label", "Adaptive Full depth stages", "Адаптивные этапы углублённого цикла Full"],
    ["#prev-step", "aria-label", "Previous stage", "Предыдущий этап"],
    ["#next-step", "aria-label", "Next stage", "Следующий этап"],
    ["meta[name='description']", "content", "Last Human Commit: a work method from human intent to a verified, merged change, sourced from Git.", "Last Human Commit: путь от замысла человека до проверенного и влитого изменения. Источник — Git."]
  ];
  const MESSAGES = {
    "title": ["Last Human Commit — Ship the result, not the ritual.", "Last Human Commit — Результат, а не ритуал."],
    "step": ["STEP / {number}", "ЭТАП / {number}"],
    "showStage": ["Show stage {number}: {title}", "Показать этап {number}: {title}"],
    "quick": ["QUICK", "БЫСТРЫЙ ЦИКЛ"],
    "full": ["FULL", "ПОЛНЫЙ ЦИКЛ"],
    "role": ["ROLE / {number}", "РОЛЬ / {number}"],
    "role.kind.role": ["ROLE", "РОЛЬ"],
    "role.kind.method-reference": ["METHOD REFERENCE", "МЕТОДИКА"],
    "role.kind.compatibility-alias": ["COMPATIBILITY ALIAS", "СОВМЕСТИМЫЙ ПСЕВДОНИМ"],
    "roleCount": ["{roles} ROLES + {methods} METHOD REFERENCES + {aliases} COMPATIBILITY ALIAS / CURRENT REVISION", "РОЛИ: {roles} · МЕТОДИКИ: {methods} · ПСЕВДОНИМ: {aliases} / АКТУАЛЬНАЯ ВЕРСИЯ"],
    "role.summaryLabel": ["ROLE SUMMARY", "КРАТКО О РОЛИ"],
    "role.Lead.summary": ["Own the user outcome and delivery: choose the route, organize needed work, verify the real scenario and integrate changes.", "Отвечает за результат для пользователя: выбирает путь, организует нужную работу, проверяет реальный сценарий и интеграцию изменений."],
    "role.Worker.summary": ["Complete one bounded contribution to the result and report the verified change, limits and blockers to Lead.", "Выполняет ограниченную часть общей задачи и сообщает Lead о проверенном изменении, его границах и препятствиях."],
    "role.Adviser.summary": ["Resolve an important question for Lead with a concrete recommendation and explain when another choice would be better.", "Разбирает важный вопрос для Lead, предлагает конкретный вариант и объясняет, когда другой выбор будет лучше."],
    "role.Critic.summary": ["Independently challenge a material decision with supported objections, a stronger alternative and the smallest useful check.", "Независимо оспаривает существенное решение: обосновывает возражения, предлагает сильную альтернативу и минимальную полезную проверку."],
    "role.Reviewer.summary": ["Review a coherent change when its regression or misunderstanding risk justifies it; identify specific defects and fixes.", "Проверяет целостное изменение, когда риск ошибки этого требует; указывает на конкретные дефекты и минимальные исправления."],
    "role.Tester.summary": ["Try the real user journey without implementation history and report what helped, what obstructed you and whether you reached the goal.", "Самостоятельно проходит пользовательский сценарий без истории реализации и сообщает, что помогло, где возникли трудности и достигнута ли цель."],
    "role.Overseer.summary": ["Watch the overall route and progress, catch drift from the outcome or unjustified delay, and direct Lead to the next useful proof.", "Следит за общим маршрутом и прогрессом, замечает уход от результата или необоснованные задержки и направляет Lead к следующему полезному доказательству."],
    "role.Maintainer.summary": ["Act as the target project's strict maintainer: read the project and the diff, then return a hard critique of every rule and convention the change breaks.", "Выступает строгим мейнтейнером чужого проекта: сначала читает сам проект, потом диф и выдаёт жёсткий разбор всех нарушенных правил и конвенций."],
    "readRole": ["Read current definition", "Прочитать определение"],
    "hideRole": ["Hide definition", "Скрыть определение"],
    "verbatim": ["VERBATIM GIT CONTENT", "ОПРЕДЕЛЕНИЕ ИЗ GIT · ОРИГИНАЛ БЕЗ ПЕРЕВОДА"],
    "original": ["GIT SOURCE · ORIGINAL LANGUAGE", "ИЗ GIT · НА ЯЗЫКЕ ОРИГИНАЛА"],
    "openSource": ["Open source file ↗", "Открыть исходный файл ↗"],
    "builtFrom": ["Built from commit", "Собрано из коммита"],
    "generated": ["generated {date} UTC", "сборка: {date} UTC"],
    "loadingRoles": ["Reading the current Git definitions…", "Загружаем актуальные определения из Git…"],
    "loadingSource": ["Loading the current Git definition…", "Загружаем исходное определение из Git…"],
    "checking": ["checking…", "проверяем…"],
    "missingExcerpt": ["See the canonical source document.", "См. исходный документ в репозитории."],
    "unavailable": ["SOURCE UNAVAILABLE", "ИСТОЧНИК НЕДОСТУПЕН"],
    "fetchHTTP": ["HTTP {status}", "HTTP {status}"],
    "fetchInvalid": ["The Git snapshot is incomplete.", "Снимок данных из Git неполный."],
    "fetchFailed": ["The Git snapshot could not be loaded.", "Не удалось загрузить данные из Git."],
    "loadError": ["Could not load the generated Git data: {reason} The canonical definitions remain available on GitHub.", "Не удалось загрузить данные из Git: {reason} Исходные определения по-прежнему доступны на GitHub."],
    "sourceError": ["The latest generated source data is unavailable. Open the canonical Git repository.", "Актуальные данные из Git недоступны. Откройте исходный репозиторий."],
    "staleWarning": ["The page does not claim its definitions are current while the Git snapshot is unavailable.", "Пока данные из Git недоступны, сайт не подтверждает актуальность определений."],
    "mode.quick": ["QUICK", "КРАТКО"],
    "mode.full": ["FULL", "ПОЛНО"],
    "mode.quick.tagline": ["Same lifecycle, direct depth", "Тот же цикл, прямой путь"],
    "mode.full.tagline": ["Same lifecycle, deeper decisions", "Тот же цикл, глубже решения"],
    "mode.quick.note": ["Quick follows the lifecycle directly when the outcome and route are clear.", "Quick проходит жизненный цикл напрямую, когда результат и путь понятны."],
    "mode.full.note": ["Full follows the same lifecycle with deeper research, planning, council and dispatch when the work warrants them.", "Full проходит тот же цикл с более глубоким исследованием, планированием, советом и распределением работы, когда этого требует задача."],
    "decision.material-choice.title": ["Material decision depth", "Углублённый разбор существенного решения"],
    "decision.material-choice.note": ["Use this method only when a material product, architecture or migration choice remains.", "Используйте этот метод, только если остаётся существенный продуктовый, архитектурный выбор или выбор миграции."],
    "decision.material-choice.summary": ["", "Применяйте, только если остаётся существенный выбор. Сравните варианты по схеме: рабочее решение → идеальная версия → минимальный вариант, сохраняющий около 80% ценности. Это отдельный условный метод выбора пути, а не обязательный дополнительный этап Full."],
    "gitExcerptLabel": ["GIT SOURCE · ORIGINAL LANGUAGE", "ИЗ GIT · НА ЯЗЫКЕ ОРИГИНАЛА"],
    "fullDepth.research.summary": ["", "Изучите актуальный код и ограничения проекта, особенно если задача большая или неопределённая."],
    "fullDepth.working-solution.summary": ["", "Опишите полный путь к нужному результату, опираясь на доступные сейчас данные."],
    "fullDepth.ideal-version.summary": ["", "Определите, что улучшит наиболее полное решение и какую пользу это даст пользователю."],
    "fullDepth.yagni-minimum.summary": ["", "Сохраните ключевую пользу решения, а необязательные для результата улучшения отложите."],
    "fullDepth.frontier-council.summary": ["", "Если остаются разные разумные пути, сравните их с независимой критикой; при ясном выборе этот этап можно пропустить."],
    "fullDepth.small-pieces.summary": ["", "Разбейте работу на небольшие задачи с одним ответственным и проверяемым результатом, если это ускорит выполнение."],
    "fullDepth.worker-dispatch.summary": ["", "Поручайте независимым исполнителям ограниченные задачи, когда это экономит время или улучшает проверку."],
    "fullDepth.review-manual-test.summary": ["", "Проверьте изменения и вручную пройдите нужный пользовательский сценарий: одних автопроверок недостаточно."],
    "fullDepth.shared-history.summary": ["", "Используйте настроенный путь публикации и влейте изменение в ветку назначения: свой репозиторий — в main, чужой — в вашу ветку."],
    "fullDepth.research.title": ["Research current code", "Исследуйте текущий код"],
    "fullDepth.working-solution.title": ["Build a working solution", "Соберите рабочее решение"],
    "fullDepth.ideal-version.title": ["Consider the ideal version", "Продумайте идеальную версию"],
    "fullDepth.yagni-minimum.title": ["Choose the useful minimum with YAGNI", "Выберите полезный минимум по YAGNI"],
    "fullDepth.frontier-council.title": ["Challenge unresolved choices", "Проверьте нерешённые решения независимой критикой"],
    "fullDepth.small-pieces.title": ["Split useful work into small pieces", "Разбейте работу на полезные небольшие части"],
    "fullDepth.worker-dispatch.title": ["Dispatch bounded Worker tasks", "Поручите Worker-ам ограниченные задачи"],
    "fullDepth.review-manual-test.title": ["Review and manually test", "Проведите ревью и ручную проверку"],
    "fullDepth.shared-history.title": ["Push and merge where it belongs", "Отправьте и влейте по назначению"],
    "fullDepth.sourceLink": ["Open the Git source ↗", "Открыть источник в Git ↗"],
    "workflow.outcome.title": ["Start with human intent", "Начните с замысла человека"],
    "workflow.outcome.description": ["Name who benefits, what changes, what failed before and where the result can be tried.", "Определите, кому это нужно, что изменится, что не работало раньше и где проверить результат."],
    "workflow.route.title": ["Choose the responsible route", "Выберите подходящий путь"],
    "workflow.route.description": ["Use the shortest route that can prove the result; investigate further when an unresolved choice could change the outcome or cost.", "Выберите кратчайший путь, который докажет результат; исследуйте глубже, если нерешённый выбор может изменить результат или стоимость."],
    "workflow.execute.title": ["Do the work", "Выполните работу"],
    "workflow.execute.description": ["Make the needed change while preserving other active work, data and ownership.", "Внесите нужное изменение, сохранив чужую незавершённую работу, данные и границы ответственности."],
    "workflow.verify.title": ["Verify the real result", "Проверьте реальный результат"],
    "workflow.verify.description": ["Check the claim through the actual consumer path, fix in-scope failures and keep different evidence levels distinct.", "Проверьте результат через реальный потребительский путь, исправьте ошибки в своей области и разделяйте виды доказательств."],
    "workflow.deliver.title": ["Merge where it belongs", "Влейте изменение по назначению"],
    "workflow.deliver.description": ["Use the project's configured route and report what is verified, what is unknown and any external blocker.", "Используйте настроенный в проекте путь и сообщите, что проверено, что неизвестно и что блокирует работу извне."],
    "showStage": ["Show stage {number}: {title}", "Показать этап {number}: {title}"],
    "Smallest useful route": ["Smallest useful route", "Кратчайший полезный путь"],
    "updatedOnPush": ["updated on Git push", "обновляется при push в Git"],
  };
  Object.assign(MESSAGES, {
  "nav.skip": [
    "Skip to content",
    "Перейти к содержимому"
  ],
  "nav.loop": [
    "The cycle",
    "Цикл"
  ],
  "nav.design": [
    "Design",
    "Проектирование"
  ],
  "nav.roles": [
    "The team",
    "Команда"
  ],
  "nav.plans": ["Plans", "Планы"],
  "hero.eyebrow": [
    "A METHOD FOR AI-LED DEVELOPMENT",
    "МЕТОД РАЗРАБОТКИ КОМАНДОЙ ИИ"
  ],
  "hero.heading": [
    "Your intent.<br>A team of agents.<br><em>A finished change.</em>",
    "Ваш замысел.<br>Команда агентов.<br><em>Готовый результат.</em>"
  ],
  "hero.copy": [
    "You describe what should work. LHC gives coding agents the method to research, design, split the work, test it in practice and integrate the result.",
    "Вы объясняете, что должно работать. LHC задаёт агентам путь: исследовать код, спроектировать решение, распределить работу, проверить её на практике и собрать общий результат."
  ],
  "hero.cta": [
    "Explore the full cycle",
    "Посмотреть полный цикл"
  ],
  "hero.read": [
    "Read the philosophy",
    "Прочитать философию"
  ],
  "hero.footnote": [
    "Not another code generator. A method for taking responsibility for the whole result.",
    "Не ещё один генератор кода. Метод, который охватывает задачу целиком, а не только её реализацию."
  ],
  "hero.mapLabel": [
    "ILLUSTRATION, NOT LIVE STATUS",
    "СХЕМА, НЕ LIVE-СТАТУС"
  ],
  "hero.input": [
    "01 / HUMAN INTENT",
    "01 / ЗАМЫСЕЛ ЧЕЛОВЕКА"
  ],
  "hero.prompt": [
    "“I want a result I can actually use.”",
    "«Хочу результат, который можно попробовать руками»."
  ],
  "hero.lead": [
    "understand → design → orchestrate",
    "понять → спроектировать → организовать"
  ],
  "hero.worker1": [
    "Interface",
    "Интерфейс"
  ],
  "hero.worker2": [
    "Logic",
    "Логика"
  ],
  "hero.worker3": [
    "Regression",
    "Регрессия"
  ],
  "hero.leaf": [
    "bounded task",
    "конкретная задача"
  ],
  "hero.proof": [
    "Review → deploy → real use",
    "Ревью → деплой → реальная проверка"
  ],
  "hero.proofSub": [
    "Fresh eyes. A real user goal. Fix what fails.",
    "Свежий взгляд, своя задача, исправление ошибок."
  ],
  "hero.output": [
    "Merged where it belongs",
    "Влито туда, где нужно"
  ],
  "strip.1": [
    "INTENT, NOT A PERFECT SPEC",
    "ЗАМЫСЕЛ, А НЕ ИДЕАЛЬНОЕ ТЗ"
  ],
  "strip.2": [
    "IDEAL → USEFUL MINIMUM",
    "ИДЕАЛ → ПОЛЕЗНЫЙ МИНИМУМ"
  ],
  "strip.3": [
    "PARALLEL WORK, ONE OWNER",
    "ПАРАЛЛЕЛЬНО, НО НЕ ВРАЗНОБОЙ"
  ],
  "strip.4": [
    "TESTED & INTEGRATED",
    "ПРОВЕРЕНО И ИНТЕГРИРОВАНО"
  ],
  "loop.eyebrow": [
    "01 / THE COMPLETE JOURNEY",
    "01 / ВЕСЬ ПУТЬ ДО РЕЗУЛЬТАТА"
  ],
  "loop.heading": [
    "The whole cycle.<br><em>Not just the coding.</em>",
    "Полный цикл.<br><em>Не только код.</em>"
  ],
  "loop.copy": [
    "The process starts before the first line of code and ends after the result is tried and merged where it belongs.",
    "Работа начинается до первой строки кода и заканчивается после проверки реального результата и его слияния туда, где нужно."
  ],
  "loop.fullBadge": [
    "DESIGN + COORDINATION",
    "ПРОЕКТИРОВАНИЕ И КООРДИНАЦИЯ"
  ],
  "loop.quickBadge": [
    "THE DIRECT ROUTE",
    "КОРОТКИЙ ПУТЬ"
  ],
  "loop.sameEnd": [
    "DIFFERENT DEPTH. SAME FINISH LINE.",
    "РАЗНАЯ ГЛУБИНА. ОДИН РЕЗУЛЬТАТ."
  ],
  "loop.loading": [
    "Loading the current method from Git…",
    "Загружаем актуальный метод из Git…"
  ],
  "loop.fullNote": [
    "Full Cycle unfolds the path from intent through design and parallel execution to an integrated, usable result. Independent challenge is used where a consequential choice remains.",
    "Full Cycle разворачивает путь от замысла через проектирование и параллельную работу до проверенного общего результата. Независимая критика нужна там, где остаётся существенный выбор."
  ],
  "loop.quickNote": [
    "Quick Loop keeps a short plan and targeted implementation when the path is clear. It does not remove real-use verification or the applicable delivery steps.",
    "Quick Loop оставляет короткий план и точечную реализацию, когда путь понятен. Реальная проверка и необходимые шаги доставки не исчезают."
  ],
  "loop.return": [
    "A failed user scenario returns to repair, not to a report marked “done”.",
    "Неудачный пользовательский сценарий возвращает работу на исправление, а не в отчёт со словом «готово»."
  ],
  "group.plan": [
    "01 / UNDERSTAND & DESIGN",
    "01 / ПОНЯТЬ И СПРОЕКТИРОВАТЬ"
  ],
  "group.build": [
    "02 / SPLIT & EXECUTE",
    "02 / РАЗДЕЛИТЬ И ВЫПОЛНИТЬ"
  ],
  "group.proof": [
    "03 / PROVE & INTEGRATE",
    "03 / ПРОВЕРИТЬ И ИНТЕГРИРОВАТЬ"
  ],
  "story.intent.title": [
    "Understand the intent",
    "Понять замысел"
  ],
  "story.intent.copy": [
    "Name the person, the goal, the before-and-after difference and where to try it. Recover spoken intent without demanding a perfect specification.",
    "Определить, кому нужен результат, что изменится и где это можно попробовать. Восстановить смысл запроса, а не требовать от человека идеальное ТЗ."
  ],
  "story.research.title": [
    "Research current code",
    "Исследовать текущий код"
  ],
  "story.research.copy": [
    "Collect the facts and constraints with bounded research. Understand the real system before deciding how to change it.",
    "Собрать факты и ограничения ограниченными исследовательскими задачами. Понять реальное устройство проекта, прежде чем выбирать изменения."
  ],
  "story.options.title": [
    "Compare & challenge",
    "Сравнить и оспорить"
  ],
  "story.options.copy": [
    "Start with viable ways to solve the whole task. Compare trade-offs and test assumptions through independent criticism when the choice matters.",
    "Найти рабочие способы решить задачу целиком. Сопоставить плюсы, минусы и стоимость; проверить существенные предположения независимой критикой."
  ],
  "story.ideal.title": [
    "Design the ideal",
    "Продумать идеал"
  ],
  "story.ideal.copy": [
    "Use the strongest ideas to form an ideal plan. Explain what each improvement actually gives the person using the result.",
    "Собрать из сильных идей идеальный план. Понять, какую реальную пользу даёт каждое улучшение. Это проектирование, а не строительство трёх версий."
  ],
  "story.yagni.title": [
    "Cut with YAGNI",
    "Убрать лишнее: YAGNI"
  ],
  "story.yagni.copy": [
    "Remove additions and rituals that do not serve the accepted outcome. Keep the highest-value minimum that still solves the whole user task.",
    "Выбросить дополнения и ритуалы, не работающие на принятый результат. Оставить минимум изменений, который целиком решает пользовательскую задачу."
  ],
  "story.decompose.title": [
    "Leaves ≤ 15 min",
    "Задачи до 15 минут"
  ],
  "story.decompose.copy": [
    "Split the plan into small leaves with an owner, explicit scope and a checkable result. Fifteen minutes is planning granularity, not an agent kill timer.",
    "Разложить план на небольшие задачи с владельцем, границами и проверяемым результатом. 15 минут относятся к размеру задачи, а не к таймеру остановки агента."
  ],
  "story.parallel.title": [
    "Map the dependencies",
    "Разметить параллельность"
  ],
  "story.parallel.copy": [
    "Decide which leaves run together and which must wait. Assign exclusive ownership of shared files and resources; parallelism must not create collisions.",
    "Сразу определить, что выполняется одновременно, а что ждёт зависимости. Закрепить владельцев файлов и ресурсов, чтобы параллельная работа не создавала конфликтов."
  ],
  "story.estimate.title": [
    "Estimate the whole path",
    "Оценить весь результат"
  ],
  "story.estimate.copy": [
    "Estimate delivery using dependencies and available slots. Preserve the original estimate so the plan can be compared with actual progress.",
    "Оценить срок всего результата с учётом зависимостей и доступных исполнителей. Сохранить исходную оценку, чтобы сравнивать план с реальным продвижением."
  ],
  "story.workers.title": [
    "Dispatch to Workers",
    "Раздать работу Workers"
  ],
  "story.workers.copy": [
    "Workers own bounded contributions. Lead coordinates decisions and integration instead of becoming the single executor of every task.",
    "Workers выполняют конкретные части работы. Lead координирует решения и сборку общего результата, а не превращается в единственного исполнителя всех задач."
  ],
  "story.review.title": [
    "Technical review",
    "Техническое ревью"
  ],
  "story.review.copy": [
    "Independently examine the coherent change for defects that matter to the accepted claim. The review is not a substitute for using the product.",
    "Независимо проверить целостное изменение на дефекты, влияющие на принятый результат. Чтение кода не заменяет использование продукта."
  ],
  "story.deploy.title": [
    "Deploy to a real stand",
    "Деплой на реальный стенд"
  ],
  "story.deploy.copy": [
    "Use the available, authorized development environment. A built artifact is not yet a deployed result that a tester can use.",
    "Выкатить результат на доступный разрешённый dev-стенд. Собранный артефакт ещё не означает, что тестировщику есть чем воспользоваться."
  ],
  "story.test.title": [
    "Zero Knowledge test",
    "Zero Knowledge проверка"
  ],
  "story.test.copy": [
    "Give fresh testers realistic goals that touch the affected paths. No code, diffs or implementation narrative: they interact with the product and report raw observations.",
    "Дать свежим тестировщикам реалистичные задачи, затрагивающие изменения. Без кода, диффов и истории реализации: они работают с продуктом и описывают наблюдения."
  ],
  "story.repair.title": [
    "Repair observed failures",
    "Исправить реальные сбои"
  ],
  "story.repair.copy": [
    "Fix what prevents the promised result and repeat affected real use. Keep optional preferences separate from defects; do not create an endless review loop.",
    "Исправить то, что мешает обещанному результату, и повторить затронутый сценарий. Отделять предпочтения от дефектов, не запускать бесконечные проверки."
  ],
  "story.integrate.title": [
    "Push → PR → dev",
    "Свести в dev-ветку"
  ],
  "story.integrate.copy": [
    "Publish the owned change and merge it: the owner's repository into main when checks are green, someone else's into the owner's branch. Releasing an external main stays that owner's decision.",
    "Опубликовать изменения и влить: свой репозиторий — в main, как только проверки зелёные; чужой — в вашу ветку. Релиз в чужой main остаётся решением его владельца."
  ],
  "story.quick-plan.title": [
    "Write a short plan",
    "Составить короткий план"
  ],
  "story.quick-plan.copy": [
    "When the route is clear, keep the plan compact: a specific change, ownership and a direct acceptance check. Do not manufacture architectural alternatives.",
    "Когда путь ясен, достаточно короткого плана: конкретное изменение, ответственность и прямая проверка. Не выдумывать архитектурные альтернативы ради процесса."
  ],
  "design.eyebrow": [
    "02 / FIRST, DESIGN THE RIGHT THING",
    "02 / СНАЧАЛА СПРОЕКТИРОВАТЬ НУЖНОЕ"
  ],
  "design.heading": [
    "Think to the ideal.<br><em>Build what matters.</em>",
    "Додумать до идеала.<br><em>Сделать нужное.</em>"
  ],
  "design.copy": [
    "Research the code. Compare viable solutions and challenge the assumptions. Then make three passes over one plan, not three implementations.",
    "Исследовать код, сравнить решения, оспорить предположения. Затем трижды проработать один план, а не трижды реализовать один продукт."
  ],
  "design.working": [
    "The working solution",
    "Рабочее решение"
  ],
  "design.workingCopy": [
    "A complete route from today’s system to the requested result. Understand how the whole thing can work.",
    "Целостный путь от текущей системы до нужного результата. Сначала понять, как задача вообще решается полностью."
  ],
  "design.ideal": [
    "The ideal version",
    "Идеальная версия"
  ],
  "design.idealCopy": [
    "Improve the plan. Compare alternatives. Let independent criticism expose weak assumptions and unnecessary compromises.",
    "Улучшить план, сопоставить альтернативы. Через независимую критику найти слабые предположения и ненужные компромиссы."
  ],
  "design.minimum": [
    "The useful minimum",
    "Полезный минимум"
  ],
  "design.minimumCopy": [
    "Cut what does not serve this result. Keep the highest-value changes and deliver the entire accepted outcome.",
    "Убрать то, что не помогает этому результату. Сохранить самые полезные изменения и полностью закрыть принятую задачу."
  ],
  "design.buildThis": [
    "THIS IS THE VERSION WE BUILD",
    "ИМЕННО ЭТУ ВЕРСИЮ РЕАЛИЗУЕМ"
  ],
  "design.pareto": [
    "of the ideal’s useful value is a design target, not permission to deliver 80% of the promised result.",
    "полезной ценности идеала: ориентир проектирования, а не разрешение выполнить лишь 80% обещанной задачи."
  ],
  "parallel.eyebrow": [
    "03 / SMALL TASKS. A SHARED RESULT.",
    "03 / НЕБОЛЬШИЕ ЗАДАЧИ. ОБЩИЙ РЕЗУЛЬТАТ."
  ],
  "parallel.heading": [
    "Split the work.<br><em>Not the responsibility.</em>",
    "Разделить работу.<br><em>Не ответственность.</em>"
  ],
  "parallel.copy": [
    "Lead holds the whole objective. Workers own small, verifiable contributions. Independent tasks run together; real dependencies set the order.",
    "Lead держит общую цель. Workers отвечают за небольшие проверяемые части. Независимые задачи идут одновременно, реальные зависимости определяют порядок."
  ],
  "parallel.example": [
    "ILLUSTRATIVE PLAN / NOT A LIVE TIMELINE",
    "ПРИМЕР ПЛАНА / НЕ LIVE-РАСПИСАНИЕ"
  ],
  "parallel.wave1": [
    "Wave 1",
    "Волна 1"
  ],
  "parallel.wave2": [
    "Wave 2",
    "Волна 2"
  ],
  "parallel.wave3": [
    "Wave 3",
    "Волна 3"
  ],
  "parallel.ui": [
    "Interface",
    "Интерфейс"
  ],
  "parallel.logic": [
    "Core logic",
    "Логика"
  ],
  "parallel.regression": [
    "Regression test",
    "Регрессия"
  ],
  "parallel.integrate": [
    "Integrate + exercise",
    "Сборка + проверка"
  ],
  "parallel.proof": [
    "Fresh user test",
    "Свежий тестировщик"
  ],
  "parallel.critical": [
    "Delivery time follows the critical path and available capacity, not the sum of every task.",
    "Срок доставки определяется критическим путём и доступной параллельностью, а не простой суммой всех задач."
  ],
  "parallel.minutes": [
    "min",
    "мин"
  ],
  "parallel.leafTitle": [
    "One bounded piece of work",
    "Одна конкретная задача"
  ],
  "parallel.leafCopy": [
    "The planned size of a leaf, including its check. Not a timer that kills an agent after 15 minutes.",
    "Плановый размер одной задачи вместе с проверкой. Не таймер, который останавливает агента через 15 минут."
  ],
  "parallel.ownerTitle": [
    "Owner of the whole outcome",
    "Владелец общего результата"
  ],
  "parallel.ownerCopy": [
    "Lead coordinates decisions, dependencies and convergence. Parallel execution never means “someone else will finish it”.",
    "Lead сводит решения, зависимости и готовую работу. Параллельность не означает «кто-нибудь потом это доделает»."
  ],
  "proof.eyebrow": [
    "04 / THE TEST IS SOMEONE USING IT",
    "04 / ПРОВЕРКА: КТО-ТО ЭТИМ ПОЛЬЗУЕТСЯ"
  ],
  "proof.heading": [
    "A green test suite<br>is not <em>the finish line.</em>",
    "Зелёные тесты<br>ещё <em>не финиш.</em>"
  ],
  "proof.copy": [
    "Deploy to the available development environment. Give fresh testers a realistic goal, not your implementation story or a recipe for success.",
    "Выкатить на доступный dev-стенд. Дать свежим тестировщикам реалистичную цель, а не рассказ о реализации или инструкцию, как получить успешный ответ."
  ],
  "proof.review": [
    "Is the change sound?",
    "Корректны ли изменения?"
  ],
  "proof.reviewCopy": [
    "Technical review checks the change and its real regression risk.",
    "Техническое ревью проверяет изменение и реальные риски регрессии."
  ],
  "proof.zk": [
    "Can someone actually use it?",
    "Можно ли этим воспользоваться?"
  ],
  "proof.zkCopy": [
    "No code. No diffs. A deployed product and a real task. Different personas cover the affected user journeys.",
    "Без кода и диффов. Развёрнутый продукт и своя задача. Разные персоны проходят затронутые пользовательские сценарии."
  ],
  "proof.tag1": [
    "Own goal",
    "Своя цель"
  ],
  "proof.tag2": [
    "Real interaction",
    "Реальные действия"
  ],
  "proof.tag3": [
    "Raw feedback",
    "Наблюдения без пересказа"
  ],
  "proof.repair": [
    "Fix what blocks the goal.",
    "Исправить то, что мешает цели."
  ],
  "proof.repairCopy": [
    "Return observed failures to implementation. Do not turn every preference into a new product requirement.",
    "Вернуть реальные ошибки на исправление. Не превращать каждое предпочтение тестировщика в новое обязательное требование."
  ],
  "plans.eyebrow": [
    "FOLLOW ANY PLAN FROM YOUR PHONE",
    "СЛЕДИТЬ ЗА ПЛАНОМ С ТЕЛЕФОНА"
  ],
  "plans.heading": [
    "One link per plan.<br><em>One page for all of them.</em>",
    "Одна ссылка на план.<br><em>Одна страница на все.</em>"
  ],
  "plans.copy": [
    "When a plan is created, the agent gives you its permanent public link once. Every plan also lands on one list: what is moving, what is stuck, at which step and when it should end.",
    "Когда план создан, агент один раз даёт вам его постоянную публичную ссылку. Все планы собраны на одной странице: что движется, что застряло, на каком шаге и когда должно закончиться."
  ],
  "plans.f1": ["Filter by project and state", "Фильтр по проекту и состоянию"],
  "plans.f2": ["Current step and expected finish", "Текущий шаг и ожидаемое завершение"],
  "plans.f3": ["Stuck plans stand out", "Застрявшие планы видно сразу"],
  "plans.state": ["In progress", "В работе"],
  "plans.title": ["Sessions page: rename without restart", "Страница сессий: переименование без перезапуска"],
  "plans.stage": ["Now: connect the mode switch in four adapters", "Сейчас: подключить смену режима в четырёх адаптерах"],
  "plans.eta": ["Ends ≈ today 14:45 (in 20 min)", "Завершится ≈ сегодня в 14:45 (через 20 мин)"],
  "plans.stuckState": ["Stuck", "Застрял"],
  "plans.stuckTitle": ["Voice secretary answers the call", "Голосовой секретарь отвечает на звонок"],
  "plans.stuckStage": ["No changes for 7 h · stopped at: first audible reply", "Нет изменений 7 ч · остановился на: первый слышимый ответ"],
  "plans.example": ["ILLUSTRATION OF THE PLAN LIST", "ИЛЛЮСТРАЦИЯ СПИСКА ПЛАНОВ"],
  "delivery.eyebrow": [
    "05 / FINISHED MEANS MERGED",
    "05 / ГОТОВО — ЗНАЧИТ ВЛИТО"
  ],
  "delivery.heading": [
    "Every session<br><em>merges its own work.</em>",
    "Каждая сессия<br><em>вливает свою работу сама.</em>"
  ],
  "delivery.copy": [
    "A folder of finished worktrees is not delivery. Parallel sessions do not wait for each other or for a shared integrator: whoever merges second reconciles.",
    "Папка с готовыми worktree ещё не доставка. Параллельные сессии не ждут друг друга и общего интегратора: кто вливает вторым, тот и сводит изменения."
  ],
  "delivery.devLabel": [
    "YOUR REPOSITORY",
    "ВАШ РЕПОЗИТОРИЙ"
  ],
  "delivery.devCopy": [
    "Branch → PR → merge as soon as checks are green",
    "Ветка → PR → merge, как только проверки зелёные"
  ],
  "delivery.release": [
    "Someone else's repository: your branch.",
    "Чужой репозиторий — ваша ветка."
  ],
  "delivery.releaseCopy": [
    "PR into a branch you own there, after a strict maintainer review. Their main is their decision.",
    "PR в вашу ветку в этом репозитории, после строгого ревью мейнтейнера. Их main — их решение."
  ],
  "delivery.example": [
    "Set once per project in .agents/PROJECT.md: owner, target branch, dev environment. For Airlock: megamen32-dev.",
    "Задаётся один раз на проект в .agents/PROJECT.md: владелец, целевая ветка, dev-стенд. Для Airlock: megamen32-dev."
  ],
  "roles.eyebrow": [
    "06 / WHO OWNS WHAT",
    "06 / КТО ЗА ЧТО ОТВЕЧАЕТ"
  ],
  "roles.heading": [
    "A team, not<br><em>an agent parade.</em>",
    "Команда, а не<br><em>парад агентов.</em>"
  ],
  "roles.copy": [
    "Lead orchestrates; Workers execute. Independent roles challenge decisions and test the result. Each has a responsibility, not a ceremonial place in a queue.",
    "Lead организует, Workers выполняют. Независимые роли оспаривают решения и проверяют результат. У каждого своя ответственность, а не обязательное место в очереди."
  ],
  "roles.sync": [
    "DEFINITIONS FROM THE CURRENT GIT SNAPSHOT",
    "ОПРЕДЕЛЕНИЯ ИЗ АКТУАЛЬНОГО СНИМКА GIT"
  ],
  "source.show": [
    "Read the source from Git",
    "Прочитать источник из Git"
  ],
  "source.original": [
    "ORIGINAL LANGUAGE · NOT A TRANSLATION",
    "ЯЗЫК ОРИГИНАЛА · БЕЗ ПЕРЕВОДА"
  ],
  "source.open": [
    "Open the source ↗",
    "Открыть источник ↗"
  ],
  "controls.previous": [
    "Previous stage",
    "Предыдущий этап"
  ],
  "controls.next": [
    "Next stage",
    "Следующий этап"
  ],
  "truth.eyebrow": [
    "THE METHOD IS NOT THE ENTIRE PLATFORM",
    "МЕТОД НЕ ЗАМЕНЯЕТ ВСЮ ПЛАТФОРМУ"
  ],
  "truth.heading": [
    "Keep the boundaries clear.",
    "У каждого своя ответственность."
  ],
  "truth.copy": [
    "The backlog chooses the work. Agent Herder manages sessions and harnesses. LHC defines how engineering work reaches a verified result.",
    "Бэклог определяет задачи. Agent Herder управляет сессиями и харнессами. LHC задаёт метод, по которому инженерная работа доходит до проверенного результата."
  ],
  "truth.label": [
    "DESIGN ≠ IMPLEMENTATION STATUS",
    "ЗАМЫСЕЛ ≠ СТАТУС РЕАЛИЗАЦИИ"
  ],
  "truth.note": [
    "This page explains the intended method. It does not claim that every mechanism is already automated. The repository records the remaining implementation gaps.",
    "Эта страница объясняет замысел метода, а не утверждает, что каждый механизм уже автоматизирован. Оставшиеся расхождения реализации записаны в репозитории."
  ],
  "truth.link": [
    "Read the current limitations ↗",
    "Прочитать текущие ограничения ↗"
  ],
  "closing.eyebrow": [
    "FROM AN IDEA TO SOMETHING YOU CAN TRY",
    "ОТ ЗАМЫСЛА ДО ТОГО, ЧТО МОЖНО ПОПРОБОВАТЬ"
  ],
  "closing.heading": [
    "Your next instruction.<br><em>Not your next full-time job.</em>",
    "Следующее поручение.<br><em>Не ещё одна работа.</em>"
  ],
  "closing.cta": [
    "Explore Last Human Commit",
    "Открыть Last Human Commit"
  ],
  "footer.sync": [
    "Source content rebuilds on every push to main.",
    "Данные из источников обновляются при каждом push в main."
  ],
  "footer.top": [
    "BACK TO TOP ↑",
    "НАВЕРХ ↑"
  ],
  "role.Lead.summary": [
    "Owns the outcome, decomposes the work and coordinates decisions and integration. Workers perform execution.",
    "Держит общую цель, разбивает работу и координирует решения, зависимости и интеграцию. Исполнение поручает Workers."
  ],
  "title": [
    "Last Human Commit | Your intent. A complete development cycle.",
    "Last Human Commit | Ваш замысел. Полный цикл разработки."
  ]
});
  function t(key, language, values = {}) {
    const entry = MESSAGES[key];
    let text = entry ? entry[language === "ru" ? 1 : 0] : key;
    for (const [name, value] of Object.entries(values)) {
      text = text.replaceAll("{" + name + "}", String(value));
    }
    return text;
  }
  function apply(language) {
    const ru = language === "ru";
    document.documentElement.lang = ru ? "ru" : "en";
    document.title = t("title", language);
    // Only trusted, locally maintained UI literals use innerHTML. Git data never does.
    for (const [selector, en, russian] of STATIC) {
      const element = document.querySelector(selector);
      if (element) element.innerHTML = ru ? russian : en;
    }
    for (const [selector, attr, en, russian] of ATTRS) {
      const element = document.querySelector(selector);
      if (element) element.setAttribute(attr, ru ? russian : en);
    }
    for (const element of document.querySelectorAll('[data-copy]')) element.textContent = t(element.dataset.copy, language);
    for (const element of document.querySelectorAll('[data-copy-html]')) element.innerHTML = t(element.dataset.copyHtml, language);
    for (const element of document.querySelectorAll('[data-label]')) element.setAttribute('aria-label', t(element.dataset.label, language));
    document.querySelector('meta[name="description"]')?.setAttribute('content', t('hero.copy', language));
    for (const button of document.querySelectorAll("[data-lang]")) {
      const active = button.dataset.lang === language;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("is-active", active);
    }
  }
  window.LHC_I18N = Object.freeze({ t, apply, messages: MESSAGES, staticEntries: STATIC, attributes: ATTRS });
})();
