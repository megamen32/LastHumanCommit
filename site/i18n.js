/* UI translations only. Canonical Git files and source excerpts are not translated. */
(() => {
  "use strict";
  const STATIC = [
    [".skip", "Skip to content", "Перейти к содержимому"],
    [".nav-links a[href='#workflow']", "The loops", "Циклы"],
    [".nav-links a[href='#roles']", "The roles", "Роли"],
    [".nav-links a[href='#principles']", "The philosophy", "Принципы"],
    [".nav-repo", "View on GitHub <span aria-hidden='true'>↗</span>", "Код на GitHub <span aria-hidden='true'>↗</span>"],
    [".eyebrow", "<span class='status-dot' aria-hidden='true'></span> THE OUTCOME-FIRST ENGINEERING SYSTEM <span class='eyebrow-id'>/ 1.4</span>", "<span class='status-dot' aria-hidden='true'></span> РАЗРАБОТКА РАДИ РЕЗУЛЬТАТА <span class='eyebrow-id'>/ 1.4</span>"],
    ["#hero-title", "The last<br>human <em>commit.</em>", "Последний<br>коммит <em>человека.</em>"],
    [".hero-subtitle", "You describe the result. The system figures out the work. A verified outcome—not an impressive checklist—is the finish line.", "Вы описываете результат. Система определяет, как его получить. Работа заканчивается проверенным результатом, а не внушительным списком выполненных пунктов."],
    [".hero-actions .button-primary", "Explore the workflow <span aria-hidden='true'>↘</span>", "Посмотреть процесс <span aria-hidden='true'>↘</span>"],
    [".hero-actions .button-text", "Meet the agents <span aria-hidden='true'>→</span>", "Познакомиться с агентами <span aria-hidden='true'>→</span>"],
    [".hero-footnote", "<span class='line-pulse' aria-hidden='true'></span> No setup interview. No mandatory agent parade. Just the shortest path that works.", "<span class='line-pulse' aria-hidden='true'></span> Без стартового допроса и обязательного парада агентов. Только кратчайший работающий путь."],
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
    ["#workflow-title", "One router.<br><em>Two speeds.</em>", "Один процесс.<br><em>Две скорости.</em>"],
    ["#workflow .section-heading > p", "LHC chooses the smallest responsible engineering path. A larger decision needs deeper evidence—not just more steps.", "LHC выбирает кратчайший путь без ущерба результату. Чем серьёзнее решение, тем убедительнее должны быть доказательства — а не длиннее список шагов."],
    ["#quick-tab", "<span class='tab-key'>01</span> Quick loop <span class='tab-arrow' aria-hidden='true'>↗</span>", "<span class='tab-key'>01</span> Быстрый цикл <span class='tab-arrow' aria-hidden='true'>↗</span>"],
    ["#full-tab", "<span class='tab-key'>02</span> Full cycle <span class='tab-arrow' aria-hidden='true'>↗</span>", "<span class='tab-key'>02</span> Полный цикл <span class='tab-arrow' aria-hidden='true'>↗</span>"],
    [".mode-aside", "ROUTE / NOT RITUAL", "ПУТЬ / НЕ РИТУАЛ"],
    [".loop-center-pre", "THE NON-NEGOTIABLE", "ТО, ЧЕМ НЕЛЬЗЯ ПОСТУПИТЬСЯ"],
    [".loop-center strong", "USER<br>OUTCOME<span>.</span>", "РЕЗУЛЬТАТ<br>ПОЛЬЗОВАТЕЛЯ<span>.</span>"],
    [".loop-center small", "Evidence over ceremony", "Доказательства, а не ритуалы"],
    [".loop-legend", "<span class='legend-line' aria-hidden='true'></span> Continuously refine until the real scenario works", "<span class='legend-line' aria-hidden='true'></span> Уточняем и исправляем, пока реальный сценарий не заработает"],
    [".excerpt-label", "FROM GIT · ORIGINAL LANGUAGE <span aria-hidden='true'>↗</span>", "ИЗ GIT · НА ЯЗЫКЕ ОРИГИНАЛА <span aria-hidden='true'>↗</span>"],
    ["#stage-link", "Read canonical definition <span aria-hidden='true'>↗</span>", "Открыть исходное определение <span aria-hidden='true'>↗</span>"],
    ["#roles .section-number", "02 / THE PEOPLE BEHIND THE PROCESS", "02 / УЧАСТНИКИ ПРОЦЕССА"],
    ["#roles-title", "Every role.<br><em>A clear purpose.</em>", "У каждой роли —<br><em>своя задача.</em>"],
    ["#roles .section-heading > p", "Specialists are called for a reason, never to fill a quota. Definitions below are generated from the role files in Git on every site build.", "Специалистов подключают по делу, а не ради количества. Определения ниже берутся из файлов ролей в Git при каждой сборке сайта и показаны на языке оригинала."],
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
    ["meta[name='description']", "content", "Last Human Commit: outcome-first engineering with adaptive loops, independent roles, and verified delivery. Synchronized directly from Git.", "Last Human Commit: разработка ради результата. Гибкие рабочие циклы, независимые роли и проверенный результат. Синхронизация напрямую из Git."]
  ];
  const MESSAGES = {
    "title": ["Last Human Commit — Ship the result, not the ritual.", "Last Human Commit — Результат, а не ритуал."],
    "step": ["STEP / {number}", "ЭТАП / {number}"],
    "showStage": ["Show stage {number}: {title}", "Показать этап {number}: {title}"],
    "quick": ["QUICK", "БЫСТРЫЙ ЦИКЛ"],
    "full": ["FULL", "ПОЛНЫЙ ЦИКЛ"],
    "role": ["ROLE / {number}", "РОЛЬ / {number}"],
    "onDemand": ["ON DEMAND", "ПО НЕОБХОДИМОСТИ"],
    "orchestrator": ["ORCHESTRATOR", "ОРКЕСТРАТОР"],
    "roleCount": ["{count} ROLES / CURRENT REVISION", "РОЛЕЙ: {count} / АКТУАЛЬНАЯ ВЕРСИЯ"],
    "readRole": ["Read current definition", "Прочитать определение"],
    "hideRole": ["Hide definition", "Скрыть определение"],
    "verbatim": ["VERBATIM GIT CONTENT", "ИСХОДНЫЙ ТЕКСТ ИЗ GIT"],
    "original": ["GIT SOURCE · ORIGINAL LANGUAGE", "ИЗ GIT · НА ЯЗЫКЕ ОРИГИНАЛА"],
    "roleNotice": ["Optional method reference; the active router decides when to use it.", "Справочный материал: основной регламент определяет, когда нужна эта роль."],
    "openSource": ["Open source file ↗", "Открыть исходный файл ↗"],
    "builtFrom": ["Built from commit", "Собрано из коммита"],
    "generated": ["generated {date} UTC", "сборка: {date} UTC"],
    "updatedOnPush": ["updated on Git push", "обновляется при push в Git"],
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
    "Define the outcome": ["Define the outcome", "Определить результат"],
    "Route intelligently": ["Route intelligently", "Выбрать подход"],
    "Keep work isolated": ["Keep work isolated", "Изолировать работу"],
    "Prove it works": ["Prove it works", "Проверить результат"],
    "Deliver the result": ["Deliver the result", "Доставить результат"],
    "Business claim": ["Business claim", "Целевой результат"],
    "Least-cost route": ["Least-cost route", "Кратчайший путь"],
    "Material options": ["Material options", "Выбор решения"],
    "Delivery order": ["Delivery order", "Порядок доставки"],
    "Verified result": ["Verified result", "Проверенный итог"],
    "Smallest useful route": ["Smallest useful route", "Кратчайший полезный путь"],
    "When a material decision remains": ["When a material decision remains", "Когда нужно принять важное решение"],
    "Name the real user, before/after difference and a hands-on canary.": ["Name the real user, before/after difference and a hands-on canary.", "Определите пользователя, разницу «до и после» и реальный сценарий для проверки результата."],
    "Work directly when the path is clear; use specialists only when evidence justifies them.": ["Work directly when the path is clear; use specialists only when evidence justifies them.", "Когда путь понятен, действуйте напрямую. Подключайте специалистов только тогда, когда они действительно нужны."],
    "Protect colleagues' in-flight changes and delegate only useful independent work.": ["Protect colleagues' in-flight changes and delegate only useful independent work.", "Сохраните незавершённые изменения коллег. Делегируйте только полезную работу, которую можно выполнять независимо."],
    "Run the real scenario, fix failures, and report only verified progress.": ["Run the real scenario, fix failures, and report only verified progress.", "Проверьте реальный сценарий, устраните ошибки и сообщайте только о подтверждённом результате."],
    "Integrate a tested branch through push and review into one reachable history.": ["Integrate a tested branch through push and review into one reachable history.", "Опубликуйте проверенную ветку, проведите ревью и объедините изменения в общей доступной истории."],
    "Pin down the consumer outcome and the exact acceptance path.": ["Pin down the consumer outcome and the exact acceptance path.", "Зафиксируйте результат для пользователя и конкретный способ его приёмки."],
    "Choose the smallest reversible move toward real-world proof.": ["Choose the smallest reversible move toward real-world proof.", "Выберите минимальное обратимое изменение, которое приближает к проверке результата в реальных условиях."],
    "Compare genuinely different choices, then retain the best 80%-value implementation.": ["Compare genuinely different choices, then retain the best 80%-value implementation.", "Сравните действительно разные подходы. Выберите минимальную полноценную реализацию, которая сохраняет около 80% полезного результата."],
    "Run a real canary, independent review, and fresh user acceptance at the right milestone.": ["Run a real canary, independent review, and fresh user acceptance at the right milestone.", "Проверьте реальный сценарий, проведите независимое ревью и дайте новым пользователям проверить готовый крупный этап."],
    "Record actual evidence, integration, and deployment state—not a promise.": ["Record actual evidence, integration, and deployment state—not a promise.", "Зафиксируйте доказательства, состояние интеграции и публикации — а не обещание результата."],
    "An illustration of the short path through the actual LHC router, not a separately mandated protocol.": ["An illustration of the short path through the actual LHC router, not a separately mandated protocol.", "Это наглядный короткий путь по действующему регламенту LHC, а не отдельный обязательный протокол."],
    "Full is conditional, not a synonym for long or important. The template guides material product, architecture and migration decisions.": ["Full is conditional, not a synonym for long or important. The template guides material product, architecture and migration decisions.", "Полный цикл нужен по условиям задачи, а не просто потому, что работа долгая или важная. Шаблон помогает принимать существенные продуктовые и архитектурные решения, а также решения о миграции."]
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
