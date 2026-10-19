# Candidate 1.5.0: обратимая установка, пока НЕ выполнена

Owner: Codex `01a155b9-0b2c-7953-8afb-f530945dd0ff`; исходное поручение
`.agents/tasks/lhc-outcome-contract-20261019.md` в основном checkout.
Источник — назначенный branch `lhc/outcome-contract-20261019`. Сначала независимый
source review, все необходимые проверки, immutable SHA; затем только candidate.
Финальная публикация/merge/install требует свежей native acceptance. Нынешний
source GREEN не означает native PASS. Новых installer/daemon/provider/auth нет.

## Pins и подготовленные поверхности

`.tmp/outcome-acceptance-20261019/pins.json` фиксирует source SHA после commit,
версию и hash существующего ship.py. Девять независимых каталогов — три harness ×
quickfix/testing/fullcycle; PROMPT.txt не содержит @LHC. Fixtures уже созданы,
модельные сессии не запускались, deploy не выполнялся. Это CLI лаборатория,
не Airlock/production. Fullcycle здесь явно исключает публикацию/merge;
порядок публикации/CI исключение отдельно проверяется source/native reviewer.

Quickfix: реальные UTF-8 строки из CLI и тест, раньше ASCII corruption.
Testing: реально выполнить empty/two, честно сообщить найденный дефект без правки
кода, новых тестов или deploy; assignment complete допустим при product defect.
Fullcycle: проверить готовую сборку42, штатно deploy demo:v2, реально получить
Hello, Oleg!; private недоступен, production запрещён, повторной сборки нет.
Сохранять native ID, raw transcript/FEEDBACK, точный loaded path/version и outcome
state отдельно. Hook replay и инструкция из файла не считаются активацией.

## Неизменяемый artifact после review

Ниже команды-план; сейчас они не исполнялись. SHA должен быть проверенным commit,
а не HEAD меняющегося checkout. Каталог новый; при существовании не перезаписывать.

```sh
source_sha=$(git rev-parse HEAD)
candidate_dir="$PWD/.tmp/outcome-acceptance-20261019/artifacts/$source_sha"
test ! -e "$candidate_dir"
mkdir -p "$candidate_dir"
git archive "$source_sha" | tar -x -C "$candidate_dir"
python3 "$candidate_dir/plugins/last-human-commit/scripts/sync_skills.py" --check
python3 "$candidate_dir/plugins/last-human-commit/scripts/validate.py"
```

До install снять инвентарь native manager и только защищённую копию изменяемых
loader/plugin-selection/trust документов с исходными правами. Не печатать их
полностью, не копировать auth и не менять models/MCP/permissions. Записать hashes
и выбранные пути. Старый Codex immutable cache:
`~/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.4.13`.
Не менять старый marketplace checkout: существующий OpenCode loader импортирует
оттуда lhc-v2.ts и hooks ещё читают Python tools по этому пути.

## Codex: native manager + отдельный профиль

Локально подтверждены CLI help и generated app-server schemas; профиль
`--profile outcome-candidate-20261019` загружает отдельный
`$CODEX_HOME/outcome-candidate-20261019.config.toml` поверх прежней конфигурации.
Auth остаётся в прежнем CODEX_HOME. Поддерживаемые команды установки:

```sh
codex plugin marketplace add "$candidate_dir" --json
codex plugin add last-human-commit@last-human-commit --json
codex plugin list --json
codex exec --profile outcome-candidate-20261019 --json \
  -C "$PWD/.tmp/outcome-acceptance-20261019/codex-quickfix" - \
  < .tmp/outcome-acceptance-20261019/codex-quickfix/PROMPT.txt
```

Native install может сразу включить новый namespace в base config: это НЕ атомарная
изолированная установка. В том же контролируемом шаге вернуть base selection через
штатный app-server `config/value/write` (keyPath/value/mergeStrategy/filePath,
expectedVersion), затем только в candidate profile включить новый namespace
`last-human-commit@last-human-commit` и выключить старый
`last-human-commit@megamen32-plugins`. У manager нет enable/disable subcommands.
Доверие только точным reviewed candidate hooks, без расширения approvals/sandbox.
`hooks/list` с нужным cwd и фактический native context должны показать новый
immutable cache path/version, а старый профиль — прежний. Если manager меняет старый
cache или нарушает coexistence, остановить candidate install и восстановить selection.

## OpenCode: штатный native plugin в отдельном config directory

`OPENCODE_CONFIG_DIR` read-only `opencode debug paths` уже подтвердил отдельный
config при прежних data/cache/state. Подготовить профиль в
`.tmp/outcome-acceptance-20261019/profiles/opencode`: ссылки на существующие
защищённые config/model/MCP документы и нужные non-LHC plugin/tool каталоги,
плюс один native wrapper, импортирующий `$candidate_dir/plugins/last-human-commit/
opencode/lhc-v2.ts`. Это существующий адаптер, не копия/эмуляция hooks.
Не вызывать global `opencode plugin add` через symlink на исходную конфигурацию.
Проверить effective config whitelist (model, provider IDs, MCP names, plugin paths),
не выводя значения секретов; старый LHC wrapper не должен загрузиться второй раз.

```sh
opencode_profile="$PWD/.tmp/outcome-acceptance-20261019/profiles/opencode"
(cd .tmp/outcome-acceptance-20261019/opencode-quickfix &&
  OPENCODE_CONFIG_DIR="$opencode_profile" opencode run --standalone \
    --model minimax-coding-plan/MiniMax-M3.1-Flash --format json \
    "$(cat PROMPT.txt)")
```

Перед вызовом свежая existing model_quotas/list_models проверка; quota0 не обходить
другим billing/model. Никакого --auto. Observer/compaction контекст доказуем,
pre-final veto OpenCode не заявлять. Выход из env профиля возвращает старый loader,
активные процессы не трогать. Текущий CLI run не имеет --dir; cwd задаётся оболочкой.

## ZCode: native versioned manager, fresh session

Существующий tested route — `zcode plugins marketplace add PATH`,
`zcode plugins install last-human-commit@last-human-commit`,
`zcode plugins list --json`, затем `zcode --cwd DIR --prompt TEXT --json --mode build`.
В user-scoped native registry сохранить прежний selection/cache, установить только
из reviewed immutable local marketplace. Не подменять ZCODE_PLUGIN_ROOT и не
изобретать отдельный home/auth. Native isolation профиля пока НЕ доказана: если
manager не допускает безопасное coexistence, сначала оставить этот candidate
NOT TESTED и передать точную границу координатору, не менять общий активный runtime.
GLM weekly0 отдельно блокирует inference; не ждать reset всей задачей и не менять
глобальную модель. Неподдержанные Interrupt/SessionEnd/compaction остаются явно
неподдержанными. Новая session не доказывает обновление уже открытых sessions.

## Rollback и handoff

При regression прекратить новые candidate runs, сохранить их transcript/состояние.
Вернуть только изменённый selection/loader/trust из защищённого снимка; проверить
old native path/version новым обычным запросом, не переписывать старые cache.
Не abort/restart существующие сессии. Accepted/UNKNOWN действия не повторять;
state.json лаборатории не обнулять ради повторного PASS. Source SHA, package hash,
installed path/version, native IDs, real outcome и границы записывать раздельно.
Notify actors/live question gap не закрывать фиктивным вопросом/incident.
