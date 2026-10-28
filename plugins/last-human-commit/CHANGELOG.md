# 1.6.4 — сессия Agent Herder внутри плана

- В опубликованных планах появилась кнопка Agent Herder: боковая панель на компьютере и нижняя панель на телефоне открывают связанную сессию в iframe.
- При нескольких исполнителях доступен выбор сессии; неизвестные привязки не подменяются. Ссылка для отдельной вкладки сохраняет штатный вход SSO.
- Обновления плана применяются после закрытия панели, чтобы не прерывать работу с чатом.

# 1.6.3 — плановые модели и предварительная стоимость

- План хранит явную общую модель `default_model`; назначения модели или класса в отдельных листьях имеют приоритет. Создание и активация сохраняют назначение.
- Калькулятор использует дополнительный каталог моделей, сохраняя источник тарифов и резервный каталог. Предварительная смета не выдаётся за фактические списания подписки.
- Инструкции создания плана требуют модель и оценку работы до первой публикации; отсутствие фактического расхода не стирает предварительную оценку.

# 1.6.2 — план до инженерной работы, точный выбор без prompt regex

- Любая разрешённая инженерная задача, включая quickfix и инцидент, получает краткий план до реализации. Read-only, status и research остаются вне этого требования.
- Native intake сообщает правило и найденные кандидаты; продолжение требует явной связи с текущей сессией и актуальной целью. Хук не создаёт и не привязывает план, а документы описывают этот предел прямо.
- Проверена обработка отсутствующего плана, несвязанного открытого плана, неоднозначной привязки, обычного status/read-only запроса и malformed hook input.

# 1.6.1 — тестовый контур обязателен, проверки — стоимость, хуки без регэкспов

- Всё тестирование автоматическое, без людей. Нет тестового контура — агент строит его первым листом, не трогая прод.
- Лишние проверки запрещены: только проверка изменённого поведения; план нужен, чтобы быстрее дойти до ближайшего бизнес-результата (YAGNI).
- Напоминания на 30/60/120 минут: «время вышло, задача не закончена, какие были блокеры, хватит проверок ради проверок».
- Хук плана больше не классифицирует текст запроса регэкспами: смотрит только на открытые листья плана; Stop-блокировка по тексту удалена.

# 1.6.0 — короткий контракт, доведение до конца, страница всех планов

- `AGENTS.md` переписан коротко и без противоречий: финишная линия, список
  не-блокеров (тестовые данные, доступы к тестовым стендам, смена инструмента —
  делать самому), список настоящих блокеров, одна цепочка эскалации
  Worker → Lead → Adviser → Overseer → владелец.
- Доставка: свой репозиторий — PR в `main`, merge при зелёных проверках; чужой —
  PR в ветку владельца (например `megamen32-dev`). «Единой истории» и общего
  интегратора больше нет: параллельные сессии не ждут друг друга, сводит тот,
  кто вливает вторым. Файл проекта `.agents/PROJECT.md` (owner / target / dev).
- Все роли переписаны коротко от первого лица; Worker после одной попытки
  возвращает блокер Lead. Фокус-группы и кворум — по реальным просьбам владельца.
- Напоминания на 30/60/120 минут больше не завершают ход.
- Страница всех планов: состояние (в работе / застрял / заблокирован / завершён),
  текущий шаг, ожидаемое завершение, фильтры по проекту и состоянию.
- План в `.agents/tasks/` любого репозитория сам попадает в зеркало; при создании
  агент один раз даёт владельцу публичную ссылку (`lhc_plan_mirror.py link`).
- Тесты сокращены с ~1565 до ~530: убраны проверки формулировок промптов и
  фоновых механизмов, добавлен smoke-тест импорта всех инструментов.

# 1.5.66

- Keep recent direct user corrections in a separate bounded input window for existing progress advice; generated goal reminders and explicit agent relays no longer replace the latest correction. Omitted history remains unknown.
- Prioritize the actual installed caller result, the latest requested delivery order and concrete blocker repair; preserve supplied answers instead of asking again.
- Remove mandatory adviser-per-blocker and separate retrospective-session requirements; do useful independent work while existing builds run. No new gate, session type or state store.
- Preserve the single final review, optional MCP, fail-open advice, native Stop and permission boundaries.

# 1.5.65 — OpenCode следует за обновляемым LHC marketplace

Для OpenCode global instructions, skills и LHC plugin теперь можно привязать к
стабильному checkout `megamen32-plugins`. Ежедневный Codex marketplace refresh
обновляет тот же источник; новые OpenCode-сессии загружают текущую версию без
второго Fleet-снимка или отдельного таймера.

# 1.5.64 — owner-only интеграция не блокирует владельца LHC

Правило о владельце upstream main для Airlock-проектов больше не трактуется как
запрет владельцу репозитория LastHumanCommit. Прямое распоряжение владельца на
scoped fast-forward `main` разрешает интеграцию после соответствующих проверок.

# 1.5.63 — инженерный Lead не теряет роль продукта-исполнителя

На старте LHC Lead назначает ближайший исполнимый инженерный лист native Worker.
Бизнес-исполнитель внутри разрабатываемого продукта не подменяет Worker LHC;
отсутствие уже созданного child не меняет роль Lead. Протоколы, навыки, корневой
роутер и package projections согласованы.

# 1.5.62 — автоматический старт локального fullcycle-плана

- Codex автоматически связывает fullcycle запрос с локальным планом/листом при UserPromptSubmit.
- При отсутствии плана создаёт локальный scaffold и обновляет graph/HTML без MCP и сети.
# 1.5.61 — один прогресс-бар и привязка активного leaf-плана

Цветная полоса статусов, число задач и временные границы собраны в одной
карточке: цветная полоса считает задачи, подписи минимума/максимума/сейчас
описывают время отдельно, без второй длинной оси и плавающей синей точки.

Для продолжения выбранного плана добавлена локальная `lhc_plan_json.py activate`:
она привязывает точный plan-dir в текущем Git worktree и реальную сессию,
фиксирует исходный снимок до старта листа, оставляет работу offline и включает
observer для дальнейших локальных сохранений.

# 1.5.60 — главная под SSO и одна временная шкала плана

Существующий личный SSO защищает только корень каталога. Страницы планов,
JSON, архивы и старые capability-ссылки доступны агентским сессиям; запись и
статус наблюдателя по-прежнему требуют Bearer.

В карточке плана остался один временной график с минимумом, максимумом,
текущей отметкой и явной оценкой превышения ранней или поздней границы.
Прогресс задач остаётся числом с процентом и счётчиками статусов.

# 1.5.59 — проекты и планы под существующим SSO

Корневая страница показывает все принятые зеркалом планы, сгруппированные по
проекту, с поиском, фильтром, статусами и свежестью данных. Обновление сохраняет
поиск и список при истечении входа. Корень принимает только подтверждённый
loopback proxy SSO; старый capability URL при включённом SSO защищён так же.
Запись и синхронизация через Bearer API не зависят от браузерного входа.
Явные `graph_sources` добавляют существующие графы в тот же observer без
перезаписи исходных графов; ошибка чтения сохраняет последний хороший снимок.

# 1.5.58 — один LhcPlan MCP

Один стандартный вход с семью инструментами вместо двух реализаций с разными
возможностями. Изменения листов проходят через канонический CLI, сохраняя время
создания, начало плана и историю. Пакет переносим; MCP остаётся необязательным,
локальные файлы и офлайн-зеркало сохраняют прежнюю роль.

# 1.5.57 — начало плана с первого листа

Время Full Cycle включает создание плана. Native-листы автоматически получают
неизменяемый created_at; локальный источник сохраняет начало один раз, включая
восстановление birthtime старых файлов с явной пометкой. Зеркало передаёт это
происхождение без пересчёта по копиям. Редактирование, удаление первого листа и
новые ревизии не сдвигают начало; старые архивные страницы сохраняются.

# 1.5.55 — единая страница плана

Боковое оглавление прокручивает непрерывную страницу к разделам; активный
пункт следует за чтением. Статусы задач и отсутствие блокировок видны сразу.
Обновление страницы сохраняет фильтры и положение чтения; ревизии и архивы
сохраняют прежнюю семантику.

# 1.5.53 — локальные планы с автоматическим зеркалом

Локальные `plan.json`, `leaves/*.json` и история ревизий остаются источником
истины. Отдельный наблюдатель отслеживает обычные сохранения в выбранных
каталогах, хранит последний снимок и догоняет сервер после восстановления
связи. CLI и MCP используют сохранённую локальную привязку без публикации
по сети; для зарегистрированных планов отключается также старый autopublish
клиентов 1.5.52. Прежние ссылки и исходные снимки сохраняются.

Сервер принимает очищенный JSON, проверяет владельца, последовательность и
неизменяемую историю, использует существующий renderer и хранит только
восстанавливаемую реплику. Приватная панель показывает недавние и заявленные
работающие планы; свежесть файла, receipt и неизвестная живость агента
различаются. Обычные локальные renderer и legacy publisher сохранены.

# 1.5.52 - the suite says what it spends, the gate proves itself, and the tool stops asking git twice

**The suite says what it spends.** The full run started about a thousand processes
and most of its wall clock went into waiting for them. The repositories the cases
need are now prepared once and copied, so a case receives a real Git checkout -
the same branch, the same identity, the same committed files, the same answers to
every Git question - without every case paying for the build again. The gate that
counts the processes is green again, and a new case proves the gate still bites: a
session over the budget fails and says so.

**The gate proves itself.** A budget that nothing ever exceeded is not a gate, it
is a comment. The suite now runs a session on purpose, over the budget, and
requires that the session fails and names the budget - and that the same session
within the budget passes.

**The tool stops asking Git twice.** The publication tool learned the name of a
project from a Git process; it now reads it from the disk with the same reader
every other tool of the package uses, and falls back to the Git binary for a
layout the reader does not model.

**The copies are lighter.** The sample hooks `git init` writes are inert, no case
ever runs them, and they were four times heavier than the rest of the repository
they travelled in.

# 1.5.51 - the page prints, the core keeps its promises, and a row without an id says so

**A report row says how its leaf was matched.** A row without an id is never
silently fitted by position: `check-plan` prints "matched by position, not by
id", and a wrong order is a divergence with both sides named.

**The core keeps its promises.** The fifteen-minute limit on a leaf lived only
in prose; the kernel now names every leaf above it - in `validate`, in
`status`, in the plan and on the page - unless the leaf records why it is
deliberately longer. A waiting leaf shows why it waits and when it is planned
to start and finish, and a leaf without a reason says so instead of staying
silent. The planned times of a queued leaf are no longer read as a work
window. A running leaf shows how long it has been running and whether it is
behind.

**The page prints.** `render --print` writes a printable page without the
interactive parts - one wave per sheet - and the PDF command either produces a
file or names the renderer that is missing, with exit code 2. No PDF writer of
its own: a file from a hand-written encoder would be a different document than
the browser's.
# 1.5.50 - the plan prices itself, the report is generated, and the harness can ask the human

**The plan says what it costs.** A leaf declares its model class and its complexity; the
plan kernel adds the model, the token estimate and the price from the live catalogue -
without a model in the loop. Every figure carries its source, measured or provisional,
and a leaf without a chosen model says so instead of showing zero.

**The report is generated from the leaves.** The `## Plan` block of the task record is a
projection of the leaf files: change a status in the leaf and the block changes with the
rebuild, and a doctored header is caught with the named mismatch. The numbers in the
header come from the same code the page uses, so the record and the graph cannot drift
apart silently. `check-plan` on the live plan now says that the tasks of the report and
the leaves of the graph agree and exits zero.

**The plan CLI answers over MCP - from inside this package.** Four operations: create a
leaf, edit a leaf, rebuild the plan, price a leaf. Each one is a call of the existing CLI
and returns its output verbatim. The facade is part of the Last Human Commit package, not
a second plugin: the separate plan plugin is gone and the facade travels with the package
to every host.

**Ask Human is a plugin of this marketplace.** Asking a human is a standard thing for
every harness, so it ships as its own plugin inside the same marketplace: a hook catches
the question the harness itself asks - the permission request - and forwards it to the
human through the human-request intake; the answer comes back to the harness. A harness
with no answer within the timeout is not blocked.

**One meaning per field.** `business_result` is one thing in the three documents that
define it, and the source of the plan is named once: the leaf files are the source, the
graph and the page are projections of them. The plan-artifacts skill names every field a
leaf may carry, and the path it documents really builds the graph and the page.

**The suite stays green, and the package ships what it claims.** The model resolver and
the facade travel with the package instead of being left behind in the source tree.
# 1.5.48 - correct the route from actual progress

- Codex: an optional trusted async hook invokes a fresh read-only Overseer at a
  due work boundary and returns one concrete progress correction to the active turn.
- Bound and redact native evidence, prevent recursive/duplicate reviews, honor
  native stop/new-turn cancellation and hook disablement, and fail open.
- Shorten report-only reminders. Other harnesses retain manual consultation.
- Native fixture proof: actual callback redirected repeated SHA checks to local
  installation and a successful consumer check. Only fixture timing was synthetic.

# 1.5.47 - one answer about a repository, and no leftovers in the package

**The last duplicate is gone.** The milestone module had grown its own search for
a repository next to the one the canon now holds. It asks the canon now, and the
package ships one answer. The check that holds this parses the modules and
requires that an answer exists only in the canon - outside it, an answer may only
be a plain delegation, and the class that describes a repository is defined once.
The check was proved by putting a duplicate back: it fails, and it names the file.

**A leftover stopped shipping.** A module that was merged into another one had
left its copy in the package, where it shipped as dead weight and broke the
bundle check. The publisher now refuses to pass when a projected file has no
source, and says which file it is.

**The suite still runs in about half a minute.** 1323 cases, 31 s on the
development machine; no gate was deleted.
# 1.5.44 - the task opens where the owner taps it, the plan says what it is, and the suite is two lanes

Three things the owner asked for, in the order he asked them.

**The plan says what the work is for, and how much of it is known.** The
remainder of a plan is not "unknown" because one leaf has no duration: the
known part is stated, and the imprecision is named next to it. A wait that no
open leaf carries any more is a note on a known horizon, not a reason to hide
the number. A leaf that really waits - blocked or waiting - still withholds the
clock, because the time of the answer is unknown whatever the durations are.

**Several business results in one task.** A task may deliver more than one
capability the user can touch by hand and check on its own. The report may
repeat the line "Бизнес-результат:", and every repeat is a result of its own:
the graph carries the list, the dashboard shows a card per result, and the text
view prints them one per line. The means - the commits, the internal stages -
are not results.

**The plan is an instrument, not an archive.** A plan does not grow
directories: no receipts per leaf, no consumer-test matrices, no research or
reviews folders, no second copy of the plan in another shape. What a leaf needs
in order to be understood lives in the leaf. A test earns its place by a
measured defect; a test that only restates the implementation is ballast.

**The suite is two lanes.** The work loop must finish in seconds. The cases
that drive an external process - a CLI subprocess, a git operation, a live
reviewer chain - are the long lane and run on the schedule: 1190 cases in 553
seconds before, 616 cases in 38 seconds now, and no gate was deleted. The
marker `nightly` already existed in pytest.ini; it was never applied to the
cases that needed it.

**The projection is a command.** `scripts/publish_package.py` republishes the
generated package copies from the canonical sources, so a change in the canon no
longer leaves the package stale and the projection gate red.

# 1.5.43 - unknown durations are named, not drawn as zero

A plan whose leaves carry no estimate no longer shows a minute axis on the Gantt, and the effort, critical path, remainder and planned peak say "unknown" instead of "0 min". The known subtotal and the count of the missing estimates are kept, and the counts that are really known stay exact.

# 1.5.42 - truthful unknowns and reachable task details

The progress summary now names unknown effort and external wait duration instead of claiming they are absent. Opening a task detail scrolls it below the sticky progress strip so the return control stays reachable.

# 1.5.41 - Russian project-plan requests route to the full plan artifacts

Natural requests such as «составь план» and «помоги спланировать работу» now
select the project-plan workflow and create the task record, graph and HTML.
Explicit chat-only sketches and short single-file writing requests stay outside
that project-plan trigger.

# 1.5.40 - Direct work by default, bounded delegation when it helps

For one concrete task with one result, the Lead assigns one Worker directly.
A child is used only for a concrete benefit that justifies the added context,
coordination and review, and a Worker's child requires explicit bounded Lead
authorization. Internal messages may be brief and use any language; the author
of a user-facing file writes clearly in its reader's language.

# 1.5.39 - Explicitly bounded delegation and role-specific context

Lead-authorized children may be used for an explicitly bounded assignment, and
fresh blind context is reserved for independent acceptance roles that need it.
The regression check covers native Codex projections.

# 1.5.38 - Renderer progress and forecasts match the task state

Completed plans no longer show overdue forecasts, and progress details open when current progress exists.

# 1.5.37 - the Lead owns the decisions, and plans keep their full human detail

**Every authorized development task starts from a plan.** The Lead researches the
user's intent, chooses quickfix or fullcycle from scope and risk, then presents a
proportionate plan before implementation. A worker's assigned leaf does not
change the overall mode or waive the plan.

**Task plans can explain the complete result.** Descriptions have no artificial
short length cap, affected files remain a separate field, and report, graph,
HTML, Markdown, merge and `check-plan` preserve those details independently from
acceptance and technical progress.

**The plan has one accountable decision owner and one file writer at a time.**
The Lead may assign an Artifact Writer to record verified decisions in the task
record, progress, graph and generated views. Execution workers keep their own
progress and result receipts in the canonical task directory; handoffs carry the
parent route and exact evidence.

# 1.5.36 - the dark theme is back, and the page remembers that it belongs to the system

The owner opened the plan on a machine where everything is dark by default and
asked where the dark theme had gone. Two things were true at once: the dark
theme was never removed, and the header of the page - with the title and the
theme switch - had disappeared from the plan pages, because the merge had
replaced the header of the dashboard with the headline of the delivery side and
the plan pages have no delivery side.

**The header of the plan page is the header of the dashboard again.** The title
of the plan, the date of the plan, the revision and the switch are back above
the state of the work.

**The theme has three states, not two.** "As the system", "light" and "dark".
The page follows the scheme of the operating system until the reader says
otherwise, and the button says which of the three it is now, so a page that
got stuck in the wrong theme can be returned to the system with one click. The
choice of the reader is still remembered between openings; the way back to the
system is not forgotten any more.

**The title of the plan is the name of the plan.** The first line of the report
is the name of the plan, and it is the title of the page. A title that was set
in the graph by hand still survives a refresh of the report.

Measured in Microsoft Edge with the dark scheme of the system: the background of
the page is #0d1117, the cards are #151b26, and the delivery side of the merged
page follows the same scheme as the plan.

# 1.5.35 - the progress first, every number opens, and the page builds itself

The owner read the merged page on a phone and did not find the work: the first
number about the state of the plan stood 35 032 pixels down - forty-one phone
screens - and 87,7 % of the page was material nobody had asked for. The Gantt
of the delivery side was a picture: the bars were not clickable, and nothing
showed what depended on what.

**The progress is the first thing and it stays in sight.** A slim strip at the
very top of the page carries the degree of the progress - done, share, what is
left - and it sticks to the top of the window while the page scrolls. The state
of the work, what to do now and what blocks the work follow immediately.

**Every number opens the tasks behind it.** Each tile of the state, and the
strip itself, is a control: a tap shows the tasks of that number, and a tap on
a task in that list opens the full card of the task - the owner, the session,
the model, the next step. The tiles and the strip carry the same numbers as
the plan, so they cannot disagree.

**What blocks, and what needs the owner.** One block states what holds the
work - a leaf that waits and a leaf that is blocked are told apart - and a
second one lists the leaves that wait for a decision of the owner, with the
decision itself.

**The Gantt of the plan of work is alive.** A tap on a bar or on a row opens
the card of the task, right under the grid. The dependencies are drawn as
arrows, the switch turns them off, and the rows say what a task waits for and
what it blocks. The card states that the data carries no executed state: every
task of the plan is a plan, not a done thing.

**The page is generated from the plan, by the hook.** The agent writes the
plan; the PostToolUse hook rebuilds the page of the plan that was just written.
Nobody has to remember a command, and the page can never be older than the
plan.

**The wording of a plan has a budget.** The goal and the business result say
what the work is for, the leaves say what has to happen, and the detail lives
in the card of the leaf and in the journal. The gate `check-plan` refuses a
plan whose wording has grown into a protocol.

Measured on a phone at 390 pixels in Microsoft Edge: the merged page is 10 408
pixels tall, the first number about the state stands at 809 pixels, the page
does not scroll sideways, and no touch target is below 44 pixels.

# 1.5.34 - one page for the state of the plan and the plan of the work

Two pages were read side by side: the dashboard of a task graph and the audit
of a specification with its plan of work. Each was better than the other in
its own way - the dashboard knows the state of the work, the audit knows what
the work rests on - and the owner had to hold both in his head. They are one
page now.

**The delivery side is part of the plan page.** A new module renders the
delivery side of a plan: the conclusions, the remarks, the metrics of the
requirements, the matrix of the readiness, the state of the services, the grid
of the work by phases, the works with their scope and their criterion of
acceptance, the agreed rules, the ready task for an agent, the sources of the
evidence and the text of the specification. Every field of the data reaches the
page; a field that is empty is not shown, a field that is not empty is never
dropped.

**One headline, one navigation, one theme switch.** The merged page has the
headline of the delivery side, one navigation that leads to every section of
both sides in the order of the page, and one switch between the light and the
dark theme. The palette is the one of the dashboard: the delivery side does
not invent colours.

**The leaves of the plan are still there.** The table of the leaves, the state
of every task, the card of a task with its executor, its session and its model
- all of it is on the same page as the evidence the work rests on.

**A new command.** `lhc_grid.py render-product <delivery.json> --out-dir DIR`
builds the merged page out of the delivery side alone: the plan of the work
becomes the graph of the page, and the page shows both.

The mobile page was measured at 390 pixels in Microsoft Edge: the page does
not scroll sideways, the touch targets are at least 44 pixels, and the two
strips that are wider than the screen - the navigation and the grid of the
work - scroll inside themselves.

# 1.5.33 - the task opens where the owner taps it, and says what it is

The owner opened the plan on the phone and could not read a task. Three
defects, all measured on the real dashboard of a real plan with 49 leaves.

**The task opened in the wrong place.** The card with the details of a task was
inserted into a host below the whole table. On a phone the leaves are stacked
blocks and the host is thousands of pixels below the finger that asked for the
task, so the tap produced nothing the owner could see. The card is now opened
under the row that was tapped, and the page scrolls to it.

**The only control was a button at the far end of the row.** The owner taps the
task, not a button that sits after the last column. The whole row is now the
control: it carries the identifier of its task, the pointer changes, and a tap
anywhere on the row opens the task. The button stays as the visible hint of
that there is more.

**The card showed half of the task.** It carried the code, the owner, the
dependencies, the effort and the session, and it showed the description of the
task only when the task had no blocker - one field ate the other. The model was
nowhere at all, and the next step and what the task waits from the person were
missing too. The card now carries the description, the expected result, the
blocker, the next step, what is needed from the person, the session, the model
and the runtime, each on its own line, and no field replaces another.

**The row says who works on it.** Under the name of the task the row carries the
executor, the session and the model, so the owner sees who is on the task
before opening anything.

**The leaves take the whole width of the page.** The table of the leaves was
one column of a two-column grid while it asks for 920 pixels, so on a desktop
it was scrolled sideways inside its own panel. The panel of the leaves spans
the grid now, and the table is read without a sideways scroll.

**The business goal is on the first screen.** The goal and the expected
business result used to sit in a folded brief below the counters, so a plan
read on a phone showed the state of the work and never the reason for it. They
are now in an open block at the top of the page, and the technical wording of
the plan - the confirmed progress and the external waits - stays folded.

# 1.5.32 - the plan says two honest things: it waits, and it is deferred

The dashboard answered one question twice, and the two answers contradicted each
other: the KPI tile said "blocked: 0" while the panel below said "blocked: 2".
A leaf that waits for an answer and a leaf the owner deferred were one and the
same thing, so "deferred" meant both "we wait" and "nobody waits".

**One rule of the count of blockers.** A leaf is blocked when its status is
`blocked`, and nothing else counts. A queued leaf that carries a blocker text is
queued: it is not a blocked leaf, it does not appear in the count of blockers and
the text "блокер:" is printed only for a leaf that really is blocked.

**Two honest states of a leaf.** A leaf that waits for an answer is `waiting`,
and the report marks it with ⌛. A leaf the owner deferred is `deferred`, the
report marks it with ⏸ and the dashboard calls it "Отложено владельцем": no
answer is expected, it waits for nothing and it takes no slot. The plan report
and the task graph reconcile with both of them.

**The deferred leaf is outside the remainder of the delivery.** It does not count
into "Осталось", into the remaining time, into the forecast of the finish and
into the critical path. A deferred leaf without an estimate does not make the
horizon unknown either - the forecast of an unknown estimate is about the work
that is still owed.

**Two meanings of "deferred" cannot be confused with each other.** The group of
the lines that do not fit into a free slot is called "Ждут свободного слота" now;
the deferred state of a leaf is called "Отложено владельцем" everywhere.

The KPI strip carries ten tiles now, five to a row on a desktop, and the hint of
the "Осталось" tile says how many leaves are deferred and that they are not part
of it.

The count of blockers, the two new states and the remainder of the delivery are
covered by tests, so they cannot drift apart again.

# 1.5.31 - the plan snapshot tells the truth about time, about its own horizon and about what it is

The dashboard of a plan is read on a phone, in a hurry, by the person who owns the
work. It has to say what it knows and what it does not.

**Two numbers about time are two different questions.** `actual_minutes` is the
summed effort of the executors; the window on the clock is `started_at` to
`finished_at`. 22 minutes of effort inside an 11 minute window means two executors
worked in parallel, and one number quietly meaning the other was a defect. The
dashboard now shows "усилие" and "по часам" side by side, in the table, in the task
details and in the text summary.

**The horizon counts from the last confirmed event.** The forecast used to start at
the moment the page was opened, so an idle plan pushed its own finish further away
with every minute of silence. It is now anchored at the last confirmed event, and
the anchor and the idle time are shown. A horizon that has already passed is
reported as passed instead of being moved forward.

**One graph, one revision, generated artifacts.** `render --out-dir` writes the
dashboard and the Markdown summary of one graph revision, and both carry that
revision. Two artifacts of one plan are generated, never kept in sync by hand. The
report stays the authored source of the narrative - the plan is written first - and
the graph is the single source of everything derived from it.

**The search promises what it searches.** The searchable text of a row now holds the
owner, the session id, the harness, the model, the note and the blocker, so every
field the box offers can actually be found.

**One palette, two themes.** The light and the dark theme are defined once, the
status colors carry meaning only and are referenced through CSS variables, and a
test measures the contrast of every text and status color on every surface of both
themes. On a phone the cards become compact rows, the leaf table becomes one row
per leaf instead of a wide table, and every touch target is at least 44 CSS px.

**The dashboard says what it is.** It is a snapshot of the plan, not a control
panel: the real state of the work comes from the API of the owners, and a button in
the snapshot does not change the fleet.

Four defects of 1.5.30 are now covered by tests, so they cannot return: the
ordered forecast bounds, the counter and the done count from one layer, the owner
in the searchable text, and the change log rendered as a change log.

# 1.5.30 - the dashboard disagreed with the plan, and the owner search had no data

The generator counted two different universes at once and printed both of them.

**The counters came from a different layer than the table.** The KPI row took its
numbers from the live journal while the table below it showed the graph, so the
headline read "ready 4 / 18" above 24 rows and "remaining 7" hid fourteen
unfinished leaves. "Remaining" now means every unfinished leaf, total minus
done, and the queue keeps its own separate name instead of being printed twice
under two labels.

**The finish time was computed from the wrong end of the range.** `eta_clock_min`
was built from the maximum duration and `eta_clock_max` from the minimum, so
the dashboard could promise a finish earlier than its own stated minimum. Both
clocks are now built from their own bound and the forecast is shown as a range
with the assumption spelled out.

**The search box promised more than it searched.** Its placeholder said "leaf,
id or owner" while the searchable text of a row held only the id and the label,
so an owner id never matched anything. Owner and session id are part of the
searchable text of every row now.

**The wave journal repeated the task names.** A graph may carry its own change
log: time, action, result, confirmation. The section renders that log and is
titled "Change log"; a graph without one falls back to the old list.

# 1.5.29 - the recheck of the council found three real defects, and they are fixed

The independent recheck of the 1.5.28 synthesis attacked the combined result, not
its parts, and it was right three times.

**The export carries more than the first draft said.** 1.5.28 named owner, session,
harness, model, note and the estimate reason as fields the agent has to add after
the export. Measured on a real report, the export copies them. What it really does
not carry is four leaf fields and two document fields, because a report has no
place for them: `role`, `read_paths`, `write_paths`, `paths` per leaf, and
`current_progress`, `external_waits` on the document. The procedure now says
exactly that.

**A refresh must not force a manual edit.** The recheck found the real leak: the
export drops the attribution, so every plan boundary asked the agent to patch the
graph JSON by hand - the very thing the procedure forbids. `lhc_grid.py export`
now takes `--merge <earlier graph>`: the attribution of every leaf survives a
refresh, matched by id and then by label, while the report still drives the
status, the estimates and the times. The procedure refreshes with that flag
instead of re-adding fields by hand.

**One tool path that resolves in every layout.** The convention `../../tools/...`
breaks in the repository-root projection of the skills tree, and a literal
`src/common/tools/...` breaks in the installed package. Every skill now uses
`<tools>` with the resolution written out: `common/tools/` in the installed
package, `src/common/tools/` in a source checkout and in the repository-root
projection.

**The umbrella pointed at a router that is not there in a source checkout.** It
said the package `AGENTS.md` is two directories above the skill; in the canonical
source checkout that is `src/common/`, where no `AGENTS.md` exists. The text now
names both layouts. The 20% allowance gate also moved into the umbrella, because
in a harness that runs no hooks the umbrella is the only always-loaded entry, and
a gate that names no source is a gate the agent has to go and look up.

The recheck also disagreed with the council about the MCP. That dissent is
retained in the record: the recheck argued for a thin wrapper because the export
had no merge mode. The merge mode now exists, as one verb of the existing tool,
so the wrapper would not remove any pain the CLI does not already remove.

Tests: 1062 passed.

The 1.5.28 procedure named owner, session, harness, model, note and the estimate
reason as fields the agent has to add after the export. That was wrong: the export
copies them, and the report parser has them. Measured on a real report, the export
carries per leaf the id, label, status, dependencies, parallelism, the estimate
bounds, the measured actual time, the start and finish, the owner, the session,
the harness, the model, the acceptance, the note and the blocker; on the document
the goal, the business result and the slot count.

What the export really does not carry is three leaf fields and two document
fields, because a report has no place for them: `role`, `read_paths`,
`write_paths` per leaf, and `current_progress`, `external_waits` on the document.
The procedure now says exactly that, and it also says that the mutable paths of
two leaves that may run at the same time must stay disjoint - the offline
checker fails on exactly that conflict, and the canary that produced this release
hit it.

Tests: 1060 passed.


# 1.5.28 - the plan artifacts are one procedure, and the council decided about the MCP

An AI session that had to produce the task record, the machine-readable graph and
the dashboard did not follow a written procedure: it read `lhc_grid.py` to find the
`check-plan` parser regexes, hunted the report regexes and the status legend, and
inferred the shape from an old task record. The protocol existed; the trigger and
the procedure did not.

**One skill, report-first.** The new `plan-artifacts` skill is the procedure. The
report is the only format a person reads, and the graph is derived from it: the
tool assigns the ids, the statuses, the dependencies and the estimate bounds, so
the agent writes one format instead of two and never hand-writes the graph JSON.
What the report cannot carry - owner, session, harness, model, role, acceptance,
read_paths, write_paths, note, the estimate reason, the blocker details - is added
to the exported graph afterwards. `check-plan` stays the gate: it exits non-zero
when the report and the graph are not one set of leaves. Verified on two live
records: 23 and 32 leaves, export and check-plan green.

**The description is the trigger.** No skill description carried "plan", "graph",
"dashboard" or "check-plan", so nothing was selected when a task was decomposed.
The new description carries them, and the umbrella skill and the router point at
the skill by name.

**A broken path, fixed.** The tool path convention was `../../tools/...`, which
resolves in the package projections and breaks in the repository-root projection
of the skills tree. Every skill now uses `<package root>/tools/...`, the same form
the umbrella skill already used.

**The council said no to the MCP, and said why.** Two independent strong models
were asked to argue the owner's proposal of an LHC-owned MCP server against the
skill. Both landed on the same verdict: the incident was a format-discovery
failure, not a transport failure, and an MCP schema would carry the same field
list in another syntax. The package therefore ships no MCP server; the CLI stays
the source of truth, and an MCP surface, if it ever appears, is a thin wrapper
over the same CLI. The reasoning is recorded in the product philosophy.

**The 20% allowance gate.** A provider with less than 20% of its applicable
allowance left is not used for a council, a frontier model or an adviser, unless
the owner says so directly. The gate reads the units before it applies: GLM
reports usage, MiniMax reports what is left, Codex reports usage.

Tests: 1060 passed.

# 1.5.27 - a queued message is not a result, and a supervisor decides

The coordinator session that became the cluster's supervisor found the cause of a
four-hour stall in its own instructions: it had told six sessions to write with
`sync: false`. That is a queue. The runtime holds the message until the peer's
current turn ends, so a worker that held the whole build window sat idle from 09:50
while its instructions waited, and the cluster's own reports read "done or queued".

**A plain send to a busy peer is a queue.** The contract now says it: use
`force_steer: true` for a peer that is running, keep a plain send for a peer that
should start a fresh turn, and never count "queued" as a result - a peer is done when
its own answer appears in `session messages`. A peer that holds the critical path and
stands idle is a defect to repair, not a thing to wait for. The rule is in the
umbrella skill and in the router, because that is where a hook-less session reads it.

**Supervision is a mode too.** A session that watches other sessions decides inside
the protocol instead of asking the owner, wakes a peer that holds a contour and
stands idle, and reports only what the owner cannot decide from the record: a change
of the owner's rules, a risk of losing or reverting another session's work, and a
deadlock that did not close in two cycles. It does not merge, rebuild, restart,
publish, or touch the live runtime and the public production.

Tests: 1051 passed.

# 1.5.26 — a Lead can address a peer session without discovering the channel

A coordinator session was asked to steer six peer sessions, divide ownership between
them and explain how they write back. It did the work correctly — it loaded the
umbrella skill, read the package router, played the Lead and answered the owner in
his own language — but it spent its discovery turns rediscovering how a peer is
reached at all, and it had no mode that matched its own scope.

**The channel is in the package now.** Agent Herder keys sessions by its own native
ids and does not know a native `mvs_...` id, so a coordinator that trusts only Herder
probes for a channel that cannot work. `common/protocols/COORDINATION.md` states that
a peer is addressed through the runtime that owns it: the runtime's session interface
carries the message (`session send` with `force_steer` to merge into a running turn,
`session messages` to read the peer's answer). The receipt is an admission receipt —
`status: accepted` with `mode: activated` or `mode: steered` — not delivery
evidence. A steered message gets no separate answer, and a resend is a second message
that runs the work twice.

**Delivery is proved once, through the runtime.** The coordinator verified six
deliveries by grepping the filesystem and then a stale runtime sqlite copy of session
messages. The contract now says to verify with `session messages`, that the on-disk
session directory name is an encoded id whose mapping sits in `manifest.json`, and
that a partial sqlite store is not evidence.

**The chat directory may not exist yet.** The coordinator told six peers to write to
`.agents/shared-session/chat/` and learned afterwards that the directory had never
been created. `lhc_chat.py send` creates it on its first publish, so an instruction
naming it must not claim that it exists.

**Coordination is a mode.** Ownership, handoffs and steering messages are not a code
change, not research and not a read-only status answer. The mode table names that
scope: read the peers, publish the ownership registry, hand the work over, prove the
delivery — no research cycle and no council. One task, one file and one runtime have
exactly one owner, the registry is published before the handoff, and a handoff is
complete only when the receiver acknowledged it and the sender recorded it in the
canonical task note.

Tests: 1049 passed.

# 1.5.25 — the skill decides the mode, the language and the Lead, not the description

A session in a hook-less harness loads the umbrella skill and nothing else, so that
skill has to carry the first three decisions. It did not.

**Who the Lead is.** The skill mentioned the Lead in passing. The role now opens the
skill: you are the Lead, you orchestrate only, every inspection, edit, check,
deployment, commit, push and install belongs to a Worker, and Workers do not hire
other agents. The full role description is one path away.

**Which mode the scope calls for.** There was no table, so an audit's defect list
matched the mini improvement loop's catalog line and a session ran a fix loop over
work that also creates a new service, a repository and an architecture decision. The
skill now carries the mode table — quickfix, fullcycle, testing, research, status —
with the rule that the mode comes from the accepted scope and never from a skill's
description. The mini improvement loop says in its own catalog line and in a scope
check that design work is Full: research Workers, one working→ideal→YAGNI plan, an
optional quota-aware frontier council, then bounded dispatch.

**Which language the user reads.** The policy reserved English for internal
reasoning, planning, new task records and agent coordination, so leaf labels ended
up in English inside a dashboard the owner reads. English is now for internal
reasoning and agent coordination only. The answers, the task record, the plan
report, the task graph and the dashboard — leaf labels and field wording included —
are written in the user's language.

# 1.5.24 — a fresh session in a hook-less harness finally knows what a Lead is

The umbrella skill said "read the active package's `AGENTS.md` once". In a harness
that runs plugin hooks, the SessionStart hook hands the agent the exact path to the
package router, so the phrase never mattered. A harness without hooks has no such
pointer: the agent read the phrase, opened the `AGENTS.md` of the project it happened
to be working in, considered the router read, and continued without the Lead
contract, the routing, the time boxes or the language policy. It answered a Russian
user in English.

The skill now names the file it means — the LHC package's own `AGENTS.md`, two
directories above the skill, never the project's — and says what to do when the
harness injects nothing: call the package's own `lhc_entry.py --session` once for the
session pointer and state, and `--heartbeat-only` after each significant step to
keep the 30-minute time-only checkpoint alive. Both commands only report elapsed
time and name the next command.

Four regression tests pin the pointer, the file it resolves to inside the delivered
package, the Lead contract that file must still carry, and the no-hook fallback.

The same release also fixes a plan-graph leak: `find_plan_graph` walked up past the
project and could hand a nested project the task graph of the project that contained
it. A checkout, a service inside a monorepo or a test workspace then rendered the
outer project's plan — the compaction handoff carried another project's leaves and
the 30-minute reminder named another project's lanes. The lookup now stops at the
repository boundary: a task graph never comes from outside the repository you are in.

# 1.5.23 — the task template ships what the method says

The task template still asked for 30-minute leaves and described the Overseer as
a reader that only returns a correction. The method it belongs to says a leaf is
about 15 minutes, that the 20-minute mark is the worker's reporting checkpoint, and
that the Overseer is the Lead's guide while the Lead owns the decision. The template
now says the same thing, so a new task card is written against the real contract
instead of the old one.

# 1.5.22 — the dashboard you can actually read

The HTML dashboard is rebuilt around the order a person reads a plan: the goal and the
expected business result, the progress and the status legend, the KPI strip, what to do
right now, the Gantt by waves, the leaves, and the task details. The KPI strip carries
nine metrics and no longer collapses into a tall empty column: the column count is
bounded at every width. The only element that could cover a block of the page is gone,
so the background lives on the canvas and nothing can paint over the content.

A new "Что делать сейчас" panel answers with the same logic as `lhc_parallel.py`: what
runs now, what is ready to launch, what is blocked, how many slots are free, and which
lines are still waiting for a dependency. Every row carries a text status next to its
colour, the status colours pass WCAG AA, and the phone view keeps its table inside a
local scroll instead of dragging the page sideways.

# 1.5.21 — one plan, one graph, one honest dashboard

The plan report and the task graph are now one unit with one validator. `lhc_grid.py`
gained `check-plan <report> <graph>` (exit 0/1/2) so a report whose tasks differ from
the graph leaves is caught instead of quietly rendering an empty dashboard; an
unreadable report is reported as a diagnostic, not as silence. Model classes are the
fleet's own (`glm-5.3-flash`, `minimax-3.1-flash`, `gpt-6-luna`, `glm-5.3`,
`gpt-6.1-sol`) and `⛔ blocked` is a first-class plan group.

A new tool, `lhc_parallel.py`, answers "which lines can run in parallel right now", and
the 30-minute checkpoint reminds the agent to refresh the map through the CLI, rebuild
the view and compare it against the plan. After compaction the agent receives the plan
as text; the JSON stays in the file.

`src/common/skills/` is the single canon of the 24 skills; `skills/` is a generated
projection. `CLAUDE.md` is generated from `AGENTS.md`, so the two routers can never
drift. Hooks are time-only by contract: `hooks.json` registers exactly `SessionStart`,
`PostCompact` and `PostToolUse`, and `BUSINESS_CHECKPOINT.md` now states that fact
instead of promising events that were never wired. The OpenCode V2 adapter is a real
plugin, not a stub.

# 1.5.20 — native manifest parity

All root, native harness and marketplace manifests now report version 1.5.20,
including the Hermes extension. The approved 1.5.19 instruction content is unchanged.

# 1.5.19 — business-first review and delivery

Overseer and review guidance now keeps the Lead in charge of the original business
result. Reviewers are arranged autonomously when risk warrants them; real defects and
claim-critical proof still block the affected release. LHC ledger/manifest and
identity-registration failures are bookkeeping, not delivery vetoes. Ordinary native
reviewer responses remain useful evidence without transcript-export ceremony.

Historical active-time gaps remain explicit but no longer prevent useful authorized
work. Frontier advisers and Overseer provide recommendations; the Lead owns route
choices. User stops, revocations, authorization boundaries, negative findings and
UNKNOWN external operations remain protected.

# 1.5.18 — the task graph and the plan dashboard

Every decomposed objective now keeps a machine-readable task graph next to its task
record as `plan.graph.json` and renders it with one command:

    python3 <LHC>/common/tools/lhc_grid.py render <objective>/plan.graph.json -o <objective>/plan.html

The dashboard is one self-contained HTML file: what is done, what runs now, what is
blocked, the rough finish time and how much of the work runs in parallel, plus the
owner and the session behind every leaf. It reads a task graph (schema version 2),
the canonical plan report or a free-form business-first replan with a decomposition
table, so an existing plan becomes a dashboard without being rewritten first.

The graph is now part of the method instead of an extra artifact: the plan report and
the graph are one unit, written when the objective decomposes and updated together at
every plan boundary. The plan report protocol, the task-decomposition contract, the
decompose-and-dispatch skill and the task record template all require it. The offline
graph checker accepts schema version 2 and validates the live state of a leaf.
# 1.5.17 — the owner's own review before a PR into a repository you do not own

A repository whose owner is not the requester will read the diff against the
rules of their own project, and they will read it once. That read now happens
before the PR exists: a fresh strong session plays that project's maintainer —
a senior engineer who has been in that codebase for years and loves it — reads
the project first (its instructions, conventions, tests, CI, CODEOWNERS and the
history of the touched areas) and then the diff, and returns a mountain of
specific findings instead of a verdict. The author fixes or answers every
supported finding and reviews the changed diff again; only a clean or
explicitly answered review lets the PR open. A dirty PR that reaches the owner
costs more than a later one.

New skill `maintainer-review` and new role `Maintainer`. The rule is wired into
REVIEW_TO_DELIVERY.md, Lead.md, the router and PRODUCT-PHILOSOPHY.md, and
registered in the adapter manifest, the skill catalog and the package
validator. Our own repositories do not need it.
