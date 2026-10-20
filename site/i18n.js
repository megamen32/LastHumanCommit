/* UI translations only. Canonical Git files and source excerpts are not translated. */
(() => {
  "use strict";
  const STATIC = [
    [".skip", "Skip to content", "Перейти к содержимому"],
    [".nav-links a[href='#workflow']", "The workflow", "Рабочий процесс"],
    [".nav-links a[href='#roles']", "The roles", "Роли"],
    [".nav-links a[href='#principles']", "The philosophy", "Принципы"],
    [".nav-repo", "View on GitHub <span aria-hidden='true'>↗</span>", "Код на GitHub <span aria-hidden='true'>↗</span>"],
    ["#eyebrow-label", "OUTCOME-TO-VERIFIED-DELIVERY METHOD", "ОТ ЗАМЫСЛА К ПРОВЕРЕННОМУ РЕЗУЛЬТАТУ"],
    ["#hero-title", "The last<br>human <em>commit.</em>", "Последний<br>коммит <em>человека.</em>"],
    [".hero-subtitle", "LHC gives coding agents a path from your intent to a verified change in the project's configured shared development history.", "LHC помогает ИИ-агентам пройти путь от вашего замысла до проверенного изменения в настроенной общей истории разработки проекта."],
    [".hero-actions .button-primary", "Explore the workflow <span aria-hidden='true'>↘</span>", "Посмотреть процесс <span aria-hidden='true'>↘</span>"],
    [".hero-actions .button-text", "Meet the agents <span aria-hidden='true'>→</span>", "Познакомиться с агентами <span aria-hidden='true'>→</span>"],
    [".hero-footnote", "<span class='line-pulse' aria-hidden='true'></span> Your project sets the backlog; the harness launches agents. LHC defines how work reaches shared history.", "<span class='line-pulse' aria-hidden='true'></span> Проект определяет задачи, а система запускает агентов. LHC описывает, как довести работу до общей истории."],
    [".tiny-label", "PRIMARY OBJECTIVE", "ГЛАВНАЯ ЦЕЛЬ"],
    [".hero-art-word", "RESULT<span class='hero-art-spark'>✳</span>", "РЕЗУЛЬТАТ<span class='hero-art-spark'>✳</span>"],
    [".art-tag-1", "<span class='tag-number'>01 /</span> UNDERSTAND", "<span class='tag-number'>01 /</span> ПОНЯТЬ"],
    [".art-tag-2", "<span class='tag-number'>02 /</span> EXECUTE", "<span class='tag-number'>02 /</span> ВЫПОЛНИТЬ"],
    [".art-tag-3", "<span class='tag-number'>03 /</span> VERIFY", "<span class='tag-number'>03 /</span> ПРОВЕРИТЬ"],
    [".art-corner-l", "[ HUMAN INTENT ]", "[ ЗАМЫСЕЛ ЧЕЛОВЕКА ]"],
    [".art-corner-r", "[ MACHINE WORK ]", "[ РАБОТА МАШИНЫ ]"],
    [".strip span:nth-child(1)", "<i>01</i> ADAPTIVE ROUTING", "<i>01</i> ГИБКИЙ ВЫБОР ПУТИ"],
    [".strip span:nth-child(2)", "<i>02</i> PROPORTIONAL REVIEW", "<i>02</i> ПРОВЕРКА ПО МАСШТАБУ РИСКА"],
    [".strip span:nth-child(3)", "<i>03</i> REAL-WORLD PROOF", "<i>03</i> ПРОВЕРКА В РЕАЛЬНЫХ УСЛОВИЯХ"],
    [".strip span:nth-child(4)", "<i>04</i> INTEGRATED DELIVERY", "<i>04</i> ОБЩИЙ ГОТОВЫЙ РЕЗУЛЬТАТ"],
    ["#workflow .section-number", "01 / HOW IT WORKS", "01 / КАК ЭТО РАБОТАЕТ"],
    ["#workflow-title", "One path.<br><em>Quick or Full.</em>", "Один путь.<br><em>Quick или Full.</em>"],
    ["#workflow .section-heading > p", "Both depths follow the same lifecycle. Full adds deeper research, planning and coordination when the work is large or uncertain; material-decision analysis is a separate conditional depth.", "Обе глубины следуют одному жизненному циклу. Full добавляет исследование, планирование и координацию для масштабной или неопределённой работы; разбор существенного решения — отдельная условная глубина."],
    ["#quick-tab", "<span class='tab-key'>01</span> Quick <span class='tab-arrow' aria-hidden='true'>↗</span>", "<span class='tab-key'>01</span> Краткий путь <span class='tab-arrow' aria-hidden='true'>↗</span>"],
    ["#full-tab", "<span class='tab-key'>02</span> Full <span class='tab-arrow' aria-hidden='true'>↗</span>", "<span class='tab-key'>02</span> Полный путь <span class='tab-arrow' aria-hidden='true'>↗</span>"],
    [".mode-aside", "ROUTE / NOT RITUAL", "ПУТЬ / НЕ РИТУАЛ"],
    ["#decision-label", "CONDITIONAL DEPTH / FULL", "УСЛОВНАЯ ГЛУБИНА / FULL"],
    ["#decision-link", "Read the decision method ↗", "Открыть метод принятия решения ↗"],
    ["#full-depth-label", "ADAPTIVE DEPTH / FULL", "АДАПТИВНАЯ ГЛУБИНА / FULL"],
    ["#full-depth-title", "When the task warrants a deeper route", "Когда задача требует более глубокого пути"],
    ["#full-depth-note", "Use the steps that resolve the work's uncertainty and risk; they are not required for every Full task.", "Используйте этапы, которые помогают разобраться с неопределённостью и риском; они не обязательны для каждой задачи Full."],
    [".loop-center-pre", "THE NON-NEGOTIABLE", "ТО, ЧЕМ НЕЛЬЗЯ ПОСТУПИТЬСЯ"],
    [".loop-center strong", "USER<br>OUTCOME<span>.</span>", "РЕЗУЛЬТАТ<br>ПОЛЬЗОВАТЕЛЯ<span>.</span>"],
    [".loop-center small", "Evidence over ceremony", "Доказательства, а не ритуалы"],
    [".loop-legend", "<span class='legend-line' aria-hidden='true'></span> Continuously refine until the real scenario works", "<span class='legend-line' aria-hidden='true'></span> Уточняем и исправляем, пока реальный сценарий не заработает"],
    [".excerpt-label", "FROM GIT · ORIGINAL LANGUAGE <span aria-hidden='true'>↗</span>", "ИЗ GIT · НА ЯЗЫКЕ ОРИГИНАЛА <span aria-hidden='true'>↗</span>"],
    ["#stage-link", "Read canonical definition <span aria-hidden='true'>↗</span>", "Открыть исходное определение <span aria-hidden='true'>↗</span>"],
    ["#roles .section-number", "02 / THE PEOPLE BEHIND THE PROCESS", "02 / УЧАСТНИКИ ПРОЦЕССА"],
    ["#roles-title", "Every role.<br><em>A clear purpose.</em>", "У каждой роли —<br><em>своя задача.</em>"],
    ["#roles .section-heading > p", "Each role has a defined responsibility. The project context and task determine which capabilities are used. Definitions below are generated from Git.", "У каждой роли есть своя ответственность. Контекст проекта и задача определяют, какие возможности использовать. Определения берутся из Git."],
    [".roles-meta > span:first-child", "<span class='status-dot' aria-hidden='true'></span> SYNCED FROM THE REPOSITORY", "<span class='status-dot' aria-hidden='true'></span> СИНХРОНИЗИРОВАНО С РЕПОЗИТОРИЕМ"],
    ["#principles .section-number", "03 / THE OPERATING IDEA", "03 / ГЛАВНЫЙ ПРИНЦИП"],
    ["#principles-title", "Less theatre.<br><em>More truth.</em>", "Меньше показухи.<br><em>Больше дела.</em>"],
    [".principles-title > p", "Working code matters. But evidence that a person can actually use it matters more.", "Работающий код важен. Но ещё важнее убедиться, что человек действительно может им воспользоваться."],
    [".principle-stack article:nth-child(1) h3", "Start with a real claim", "Начните с конкретного результата"],
    [".principle-stack article:nth-child(1) p", "Define who benefits, what changes, and where the result can be tried. No success-by-commit-count.", "Определите, кому станет лучше, что изменится и где это можно проверить. Число коммитов — не мера успеха."],
    [".principle-stack article:nth-child(2) h3", "Scale the process to the risk", "Соотносите процесс с риском"],
    [".principle-stack article:nth-child(2) p", "Quick repairs stay quick. Material choices get independent challenge, technical review, and fresh acceptance.", "Мелкие исправления остаются быстрыми. Важные решения требуют независимой критики, технического ревью и проверки свежим взглядом."],
    [".principle-stack article:nth-child(3) h3", "Protect shared reality", "Берегите совместную работу"],
    [".principle-stack article:nth-child(3) p", "Isolated worktrees, independent evidence, and a reviewed, integrated history. Never overwrite someone else's active work.", "Отдельные рабочие деревья Git, независимые проверки и общая история с проверенными изменениями. Не перезаписывайте чужую незавершённую работу."],
    [".closing .section-number", "THE CODE IS THE MEANS. THE RESULT IS THE POINT.", "КОД — ЭТО СРЕДСТВО. РЕЗУЛЬТАТ — ЭТО ЦЕЛЬ."],
    [".closing > p", "Make the <em>last commit</em> count.", "Пусть <em>последний коммит</em><br>имеет значение."],
    [".closing .button-primary", "Explore the repository <span aria-hidden='true'>↗</span>", "Открыть репозиторий <span aria-hidden='true'>↗</span>"],
    [".footer > a", "BACK TO TOP ↑", "НАВЕРХ ↑"]
  ];
  const ATTRS = [
    [".brand", "aria-label", "Last Human Commit, back to top", "Last Human Commit — наверх"],
    [".nav-links", "aria-label", "Main navigation", "Основная навигация"],
    [".lang-switch", "aria-label", "Site language", "Язык сайта"],
    ["[data-lang='en']", "aria-label", "Switch to English", "Переключить на английский"],
    ["[data-lang='ru']", "aria-label", "Switch to Russian", "Переключить на русский"],
    [".strip", "aria-label", "Principles in brief", "Основные принципы"],
    [".mode-controls", "aria-label", "Workflow to explore", "Выбор рабочего цикла"],
    ["#cycle-nodes", "aria-label", "Click a stage to inspect its source", "Выберите этап, чтобы прочитать его описание"],
    ["#prev-step", "aria-label", "Previous stage", "Предыдущий этап"],
    ["#next-step", "aria-label", "Next stage", "Следующий этап"],
    ["meta[name='description']", "content", "Last Human Commit: a work method from human intent to a verified change in shared project history, sourced from Git.", "Last Human Commit: путь от замысла человека до проверенного изменения в общей истории проекта. Источник — Git."]
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
    "roleCount": ["{count} ROLES / CURRENT REVISION", "РОЛЕЙ: {count} / АКТУАЛЬНАЯ ВЕРСИЯ"],
    "readRole": ["Read current definition", "Прочитать определение"],
    "hideRole": ["Hide definition", "Скрыть определение"],
    "verbatim": ["VERBATIM GIT CONTENT", "ИСХОДНЫЙ ТЕКСТ ИЗ GIT"],
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
    "fullDepth.research.title": ["Research current code", "Исследуйте текущий код"],
    "fullDepth.working-solution.title": ["Build a working solution", "Соберите рабочее решение"],
    "fullDepth.ideal-version.title": ["Consider the ideal version", "Продумайте идеальную версию"],
    "fullDepth.yagni-minimum.title": ["Choose the useful minimum with YAGNI", "Выберите полезный минимум по YAGNI"],
    "fullDepth.small-pieces.title": ["Split useful work into small pieces", "Разбейте работу на полезные небольшие части"],
    "fullDepth.worker-dispatch.title": ["Dispatch bounded Worker tasks", "Поручите Worker-ам ограниченные задачи"],
    "fullDepth.review-manual-test.title": ["Review and manually test", "Проведите ревью и ручную проверку"],
    "fullDepth.shared-history.title": ["Push and integrate into shared history", "Отправьте и объедините в общую историю"],
    "fullDepth.sourceLink": ["Open the Git source ↗", "Открыть источник в Git ↗"],
    "workflow.outcome.title": ["Start with human intent", "Начните с замысла человека"],
    "workflow.outcome.description": ["Name who benefits, what changes, what failed before and where the result can be tried.", "Определите, кому это нужно, что изменится, что не работало раньше и где проверить результат."],
    "workflow.route.title": ["Choose the responsible route", "Выберите подходящий путь"],
    "workflow.route.description": ["Use the shortest route that can prove the result; investigate further when an unresolved choice could change the outcome or cost.", "Выберите кратчайший путь, который докажет результат; исследуйте глубже, если нерешённый выбор может изменить результат или стоимость."],
    "workflow.execute.title": ["Do the work", "Выполните работу"],
    "workflow.execute.description": ["Make the needed change while preserving other active work, data and ownership.", "Внесите нужное изменение, сохранив чужую незавершённую работу, данные и границы ответственности."],
    "workflow.verify.title": ["Verify the real result", "Проверьте реальный результат"],
    "workflow.verify.description": ["Check the claim through the actual consumer path, fix in-scope failures and keep different evidence levels distinct.", "Проверьте результат через реальный потребительский путь, исправьте ошибки в своей области и разделяйте виды доказательств."],
    "workflow.deliver.title": ["Deliver into shared history", "Доставьте изменение в общую историю"],
    "workflow.deliver.description": ["Use the project's configured route and report what is verified, what is unknown and any external blocker.", "Используйте настроенный в проекте путь и сообщите, что проверено, что неизвестно и что блокирует работу извне."],
    "showStage": ["Show stage {number}: {title}", "Показать этап {number}: {title}"],
    "Smallest useful route": ["Smallest useful route", "Кратчайший полезный путь"],
    "updatedOnPush": ["updated on Git push", "обновляется при push в Git"],
  };
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
    for (const button of document.querySelectorAll("[data-lang]")) {
      const active = button.dataset.lang === language;
      button.setAttribute("aria-pressed", String(active));
      button.classList.toggle("is-active", active);
    }
  }
  window.LHC_I18N = Object.freeze({ t, apply, messages: MESSAGES, staticEntries: STATIC, attributes: ATTRS });
})();
