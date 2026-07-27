# Last Human Commit

<img width="1672" height="941" alt="image" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

Инструкции для оркестровки агентов. Личное, без SEO, без претензий на чужие
процессы. Бери и работай:Grab-n-Go.

> **English version is a placeholder for now.**
> This repository is intentionally Russian-only while it stays personal. An
> English translation will land later if the project ever needs to be read by
> anyone else.
>
> <!-- English placeholder:
> Agent orchestration instruction. Go Away From Here to grub All-In-One stuff
> that you will never understand. This one is Simple Enough, so even you can
> understand it. Grab-n-Go install: curl <add oneliner for ubuntu-mac> | bash
> — all (codex claude opencode zcode). Uninstall: lasthuman uninstall.
> -->

Установка и удаление — позже, инлайнер ещё не написан. Здесь пока — структура
и контракт.

```sh
# install: <one-liner coming>
# uninstall: lasthuman uninstall
```

## Layout

        218-tokens

- `AGENTS.md` — компактное ядро диспетчеризации.
- `agents/` — структура ролей:

  - Overseer → ┬─ Ad(viser)            — 5.6-sol, fable, glm5.2, kimi k3                       /  Интеллект
              ├─ Crit(ic)             — 5.6-terra, kimi 2.7, deepseek-v4-pro                  →  Время
              └─ L(eader)             — основной владелец результата
                  ├─ Ex(plorer, read-only)
                  ├─ Wo(rker)
                  └─ R(eviewer)

  Рабочие модели: MinimaxM3, Deepseek v4 flash, mimo, glm-4.7.

- `protocols/` — процедуры по событиям, например STOP/RETHINK.
- `profiles/` — правила для кода и инфраструктуры, грузятся только под
  соответствующую работу.
- `templates/.agents/` — runtime-состояние, используется только когда работа
  обещает занять больше часа или уже заняла больше двадцати минут. Нет работы
  длиннее маленькой новой фичи, а дороги длиннее «я знаю короткий путь» не
  бывает. Для отслеживаемой работы задачи лежат в `.agents/tasks/` как
  `todo-{id}.md` → `wip-{id}.md` → `done-{id}.md`; переходы делаются
  `git mv` и только так.
- `tests/validate.py` — структура и бюджет размера без внешних зависимостей.

Дальше этот документ можно не читать.

Жёсткие правила защищают «сразу», лимиты ретраев, ритм надзора, необратимые
границы и доказательства завершения. Реализационные советы остаются
контекстными: Overseer и Critic ставят обязательные decision gates, не
превращая бедное контекстом предложенное решение в слепо обязательное.

## File-based task lifecycle

Состояние задачи живёт в репозитории, не во внешней системе. Для отслеживаемой
работы каждая задача — это один Markdown-файл под `.agents/tasks/`. Префикс
имени кодирует стадию:

- `todo-{id}.md` — принято, не начато. Содержит критерии приёмки.
- `wip-{id}.md`  — в работе. Один владелец, текущее доказательство, следующее
  действие.
- `done-{id}.md` — завершено, с секцией `## Evidence` внизу.

Переходы состояний — только `git mv`. Никаких edit-and-rename, никаких
in-place-флагов. Рабочее дерево — это лок, коммит — это журнал аудита. Это
даёт четыре свойства: версионируемость, дифф-читаемость, greppability и
нулевую координационную стоимость. Никакого SaaS-трекера, никакой задержки
API, никакой гонки между людьми и агентами.

Файл `kanban.md` хранит только указатели (`path`, владелец, статус одной
строкой). Тела задач в доску не дублируются.

## Token footprint (tiktoken, cl100k_base)

Краткое описание: компактный канон оркестровки агентов с ленивой загрузкой.
`AGENTS.md` — единственный файл, который грузится в каждый промпт; роли,
профили и протоколы подгружаются по запросу. Полная библиотека: 15 349
символов / 3 427 токенов на 11 файлов.

| File | chars | tokens |
| --- | ---: | ---: |
| AGENTS.md | 790 | 218 |
| agents/Adviser.md | 982 | 213 |
| agents/Critic.md | 1332 | 287 |
| agents/Explorer.md | 1193 | 256 |
| agents/Lead.md | 4480 | 1029 |
| agents/Overseer.md | 1492 | 356 |
| agents/Reviewer.md | 1049 | 228 |
| agents/Worker.md | 1101 | 230 |
| protocols/STOP_RETHINK.md | 1277 | 270 |
| profiles/Code.md | 385 | 80 |
| profiles/Infrastructure.md | 1268 | 260 |
| TOTAL | 15349 | 3427 |

## Canonical installation

Репозиторий публикуется как `megamen32/LastHumanCommit`. Установка Grab-n-Go
делается инлайнером (готовится), а сейчас — клон + симлинки под harness.

```sh
git clone git@github.com:megamen32/LastHumanCommit.git ~/.agent-canon
ln -sfn ~/.agent-canon/AGENTS.md        ~/.codex/AGENTS.md
ln -sfn ~/.agent-canon/agents          ~/.codex/agents
ln -sfn ~/.agent-canon/protocols       ~/.codex/protocols
ln -sfn ~/.agent-canon/profiles        ~/.codex/profiles
```

Для отслеживаемой работы:

```sh
cp -R ~/.agent-canon/templates/.agents ./.agents
```

## Validation

```sh
python3 tests/validate.py
```