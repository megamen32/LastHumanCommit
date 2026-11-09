# H — read-only диагностика native state Q1

Статус: DIAGNOSIS_DONE, source/runtime не менялись. Снимок: 2026-11-07T21:10:57.947059+00:00.
Поручение этого этапа — диагностика bootstrap; принятую H source-часть не переоткрывать. Worker: `01a1b7ac-35d9-7992-9580-8c9d6b5fb9e6`, Codex, server-100.

## Вывод

Для Q1 ошибка public `outcome status` воспроизводится и в installed 1.17.1, и в текущем root source. Неправильный cwd не подтверждается: native header, фактический root WT и вычисленный state path согласованы. Выявлен отдельный проверяемый разрыв интерфейса bootstrap: startup hooks сознательно не создают business outcome, `status`/`contract` требуют его заранее, а доступный explicit `time_guard hook` создаёт learning/business state без вызова `lhc_outcome.observe`. Полноценного public bootstrap для пустого native outcome в просмотренном source/installed route не найдено.

При этом причина отсутствия даже timer-state у конкретной Q1 **не установлена**. Installed/enabled plugin и наличие hook registrations не доказывают, что frozen Codex Desktop session загрузила эти hooks, передала ожидаемый payload и успешно выполнила PostToolUse. Hook execution log/effect для Q1 не наблюдался; runtime/config не трогались. Здесь два разных вопроса: наблюдённое отсутствие файла Q1 и source-разрыв инициализации outcome. Второй объясняет, почему предложенный «повтори startup/contract» не является полным supported решением, но не доказывает причину первого.

## Наблюдённые факты

1. Сохранённое evidence Q1 прочитано: `evidence/Q1/independent-goal-consumer-native-context.json`, `.md`, `-commands.jsonl`. Там реальный ID `01a1b7a4-2eb2-7471-83fd-2edb027f38c5`, cwd `/home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107`, status exit 1. Q1 не seed-ил state.
2. Поддерживаемые read-only `lhc_native_identity.find_native_journal` + `read_native_header` прочитали **только первую session_meta запись** Q1. Подтверждены тот же native ID и cwd, `originator=Codex Desktop`, `parent_thread_id=null`, `agent_path=null`. Полный journal, пользовательские сообщения и parent transcript не читались. Оснований заменять ID на выдуманный composite subagent key нет.
3. Public safe projection `codex plugin list --json --marketplace megamen32-plugins` дала только LHC-поля: `pluginId=last-human-commit@megamen32-plugins`, `version=1.17.1`, `installed=true`, `enabled=true`. Это current local configuration/list evidence, **не факт загрузки plugin данным Q1 turn**.
4. Installed manifest `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.17.1/.codex-plugin/plugin.json` указывает `hooks=./com.openai/hooks/hooks.json`. Таким образом для Codex существенен именно этот файл, а не только generic `hooks/hooks.json`. SHA256 installed Codex hook file: `2759ac85b60dec801cd057768ca193028766766c0df108ca71c0a5104cd67cc3`.
5. `learning_path` вызван read-only из H source, root source и installed tools. Из native root WT, его canonical plan directory и primary checkout все три реализации выбирают один файл:

```text
/home/roomhacker/agents-projects/LastHumanCommit/.agents/shared-session/learning/c80c02b16e39ffedd071fec1f22d0b648843bd1cc0aa9107adc19bdcdab8de9c.json
```

Файл и соответствующий `.lock` отсутствуют. Проверены также только вычисленные filenames для того же Q1 ID с `claude`, `opencode`, `zcode`: файлов нет. Чужие session states не читались. Это не доказывает, какой runtime реально получил hook, но не даёт evidence существующего Q1 state под этими альтернативными runtime keys.
6. Два read-only вызова воспроизвели одинаковый отказ, без state creation:

```sh
python3 -B /home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.17.1/tools/lhc_outcome.py --cwd /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107 --runtime codex --session-id 01a1b7a4-2eb2-7471-83fd-2edb027f38c5 status
python3 -B /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107/src/common/tools/lhc_outcome.py --cwd /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107 --runtime codex --session-id 01a1b7a4-2eb2-7471-83fd-2edb027f38c5 status
```

У обоих exit 1, stdout пуст, stderr:

```text
LHC outcome: no LHC session state for codex/01a1b7a4-2eb2-7471-83fd-2edb027f38c5 from session root /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/audit-followup-20261107; no state was created
```

## Трасса source / installed route

Относительные source пути ниже — `src/common/tools/` принятого H WT; root-source проверен отдельно там, где указано. Installed аналог — `<installed>/tools/`. `lhc_entry.py`, `lhc_time_guard.py`, `lhc_outcome.py`, `lhc_milestone.py`, `lhc_native_identity.py` в H и installed 1.17.1 имеют попарно одинаковые SHA256. Root `lhc_entry` и `lhc_outcome` уже отличаются интеграционными изменениями; root `time_guard`/`milestone`/`native_identity` совпадают с installed. Root HEAD при последнем чтении: `1ae641272980f9aacc8acd4c7244762fe2af0692`; конкурентная интеграция может двигать его дальше.

| Путь / функция | Что действительно делает | Может создать нужный outcome? |
| --- | --- | --- |
| `lhc_entry.py:896 main`, `:1053–1057`; installed `SessionStart --instructions-only`, `PostCompact --instructions-only` | Внедряет instructions/current bound plan. Legacy invocation без flags инертен. SessionStart также может восстанавливать исчезнувшие tool links через `restore_codex_routes`; этот hook диагностикой не запускался. | Нет. |
| `lhc_entry.py:26 _plan_entry`, `:1029` `--plan-entry` | Codex UserPromptSubmit: read-only кандидаты session-bound планов и intake. Комментарий явно запрещает создавать/привязывать план и классифицировать prompt. | Нет. |
| `lhc_entry.py:929–980 --heartbeat-only` | PostToolUse требует string `cwd` и `session_id`/`sessionID`; при `agent_id` добавляет `:subagent:<agent_id>`. Сначала `learning_checkpoint`, затем `native_heartbeat`. Исключения ряда типов поглощаются fail-open; отсутствие ожидаемых полей даёт ранний return. | Создаёт time-state, **не business outcome**. |
| `lhc_time_guard.py:1289 learning_checkpoint` | Если state отсутствует, пишет schema/started_at/due_at/last_observed_at; это 120-minute wall deadline. | Нет. |
| `lhc_time_guard.py:1156 native_heartbeat` | Проверяет runtime, абсолютный существующий cwd, session key; пишет только `native_heartbeat` и clock fields, не интерпретирует prompt/outcome. | Нет. |
| `lhc_time_guard.py:1788 hook`, public `hook --runtime codex --event UserPromptSubmit --session-only` | Берёт cwd/session из **stdin payload**, а не `--session-id`; вызывает learning checkpoint, затем `business_checkpoint`. Тот сохраняет runtime и native prompt/business observation под тем же lock. `--session-only` исключает legacy cycle discovery. | Файл и business observation — да; `business.outcome` — нет в просмотренном коде. Не запускался в этом read-only этапе. |
| `lhc_outcome.py:1098 observe`, `:1142` | При goal создаёт pending `business['outcome']` с owner `{harness:business.runtime, session_id}`, cwd, source/contract fields. | Внутренняя функция способна создать outcome, но рабочего public bootstrap call-site не найдено. |
| `lhc_outcome.py:1784 main`, `:1822–1832`; root `:1836` | Сначала `learning_path`; без файла немедленный отказ для всех subcommands. Даже при timer-файле нужен dict `business.outcome`. Затем требует **точного** совпадения `outcome.cwd` с CLI `--cwd`. | `contract` не init. `status` не init. Root `bind-plan`/`frontier` также идут после existing-file prerequisite. |
| `lhc_milestone.py:1889 _observe`, `:1936 main` | Явный `observe --event` сначала `_load_state`, затем меняет milestone. | Не init пустого state и не создание business outcome. |
| `lhc_native_identity.py:69/100` | Bounded native header/ID/path resolution, provenance helpers. | Read-only; не пишет state. |
| `lhc_plan_json.py:2639–2642 activate` | Вызывает F `bind_session_plan` с **returned actual** `session/harness`, а lookup cwd передаёт canonical `args.plan_dir`. | Не init. |
| root `lhc_plan_control.py:136 read_context`, `:159 bind_session_plan` | Lookup через `learning_path`; принимает только outcome owner session/harness. Binding дополнительно проверяет session-plan index и Lead ownership, затем пишет plan_binding в **существующий** native outcome. Если outcome отсутствует — unknown/native_outcome_missing. | Намеренно не создаёт clock/goal. |

Текст «lhc_native» следует различать: отдельного `lhc_native.py` в известных H/root/installed tools не обнаружено. В `lhc_outcome.py:22` имя `native` — alias `import lhc_milestone as native`; native identity helper — отдельный `lhc_native_identity.py`. Alias не является скрытым bootstrap API.

Поиск `rg -n '\.observe\(|def observe\(' src/common/tools --glob '*.py'` дал definitions outcome/milestone и отдельный plan-mirror observer; вызова `lhc_outcome.observe` в рабочем tools path нет. Поиск присваиваний `business['outcome']` нашёл создание только в самом outcome.observe и восстановление snapshot в той же функции. Это ограниченный source-факт, не доказательство отсутствия внешней неизвестной harness-интеграции. В установленном hook manifest такой интеграции не заявлено. Async `lhc_progress_review.py` явно не меняет outcome и не выполняет tool operations.

## Ключи и почему не следует менять cwd наугад

`learning_path(cwd, runtime, session_id)` (`lhc_time_guard.py:1124`) использует SHA256 от UTF-8 `runtime + NUL + session_id`. Сначала переиспользует существующий ancestor clock до Git boundary; для Git worktree без такого clock выбирает **primary checkout** `.agents/shared-session/learning/<hash>.json`. Для non-Git cwd применяется ближайший `.agents` или `<cwd>/.agents`. `XDG_STATE_HOME` управляет отдельным session→plan index (`lhc_plan_json.py:1736`), не этим native learning-state file.

Поэтому physical storage в primary не означает, что `outcome --cwd` должен стать primary: logical `outcome.cwd` должен оставаться исходным native session root. `--product-root` меняет продуктовый scope, не native root. В данном Q1 root WT и canonical plan lookup уже дают одинаковый файл, так что аргумент `args.plan_dir` в H binding не объясняет текущую ошибку отсутствия state. Обычный standalone Q1 header не даёт основания добавлять subagent suffix. Для настоящего child hook composite key применяется только при наблюдённом `agent_id`/проверенной native relation.

## Минимальный следующий шаг / fix

1. **Существующий полный supported bootstrap не подтверждён.** Не советовать Q1 повторять `contract` в пустом каталоге, переключать cwd или вручную записывать JSON. Нельзя представлять synthetic stdin event как реально наблюдённый native lifecycle. Повтор SessionStart сам по себе исходный разрыв outcome не устраняет; одна time-only запись дала бы другой отказ — «no LHC outcome».
2. Отдельно зафиксировать для disposable Q1 **фактическое** выполнение одного обычного native PostToolUse через безопасную LHC projection: event name, resolved tool path/revision, runtime, native ID, cwd, state path, status/error и state-exists. Никаких prompt text, credentials или whole config. Это установит, загружен ли нужный hook и почему отсутствует timer. В этом этапе такой tracing не добавлялся и событие не инициировалось. Public plugin list недостаточен. Перезапуск чужого Codex/Herder для проверки не нужен.
3. Рекомендуемый минимальный целостный **source fix для отдельного разрешённого этапа**: явный bootstrap в существующем outcome CLI, например opt-in `contract --init-native` (это **предложение, такого flag сейчас нет**). Проверить actual native ID/cwd через bounded identity API, принять явно объявленный task-class/canary/owned scope и native source reference; под существующим state lock создать только pending outcome. Повтор не должен заменять действующий outcome, сбрасывать STOP/evidence, выдумывать human provenance или отмечать stages accepted. Не добавлять store/scheduler и не возвращать automatic prompt classifier в startup hook. После этого штатные contract → activate/bind → status/frontier смогут работать через тот же публичный путь.
4. Если отдельный verified bootstrap уже существует вне просмотренного LHC package, сначала показать его точный supported entrypoint и реальный эффект Q1. Это могло бы заменить п.3; сейчас такого evidence нет. Прямой Python вызов `_observe`/`write_state` или manual JSON seed не является выполнением public consumer-проверки.

Приёмка будущего fix: без ручного seed реальная disposable native session вызывает public explicit bootstrap; public status видит pending goal с тем же native owner/cwd; closed card не принимает goal; activate связывает именно её outcome; повторный bootstrap не стирает STOP/goal/evidence. Это отдельный consumer run, а не результат данного read-only этапа.

## Границы

Никаких новых агентов, отправок, stateful CLI, seed, tests с записью fixtures, исходных H edits, commit/push, installed config/runtime changes или рестартов. Native transcript прочитан только через bounded first-header helper Q1. Ключи/credentials/settings dumps не читались. Единственный намеренно записанный артефакт этого этапа — данный diagnosis в canonical `records/H1/`. Parent plan/leaves/acceptance и bug registry не менялись; source bugfix scope не расширялся. Исходная foreign deletion `downloaded_files/dashboard.lock` сохранена.
