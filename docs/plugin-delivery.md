# Установка и обновление LHC

## Один источник, общие правила, задачи своего проекта

Редактировать LHC: `/home/roomhacker/agents-projects/LastHumanCommit`, ветка `main`.
Роли/протоколы — `src/common/`, операторские навыки — `skills/`; генерировать
пакет `plugins/last-human-commit/scripts/sync_skills.py`, проверять общий validator
и plugin parity, публиковать main и ставить версию через native manager ниже.
Generated package/cache и legacy store не являются редактируемыми источниками.

В проектах остаются только их собственные правила и необязательный короткий
pointer `src/common/templates/project-router.md`. Не вставляйте полный router
LHC в каждый AGENTS/CLAUDE: такие копии устаревают независимо от plugin update.
Старый `~/.local/share/last-human-commit/current` не является маршрутом обычной
доставки. Сначала проверяйте, какой файл действительно загружает агент.

ToDo и рабочие записи принадлежат проекту, над которым сейчас ведётся работа.
Lead определяет его из разговора и файлов; исходный cwd сессии не назначает
владельца. Для изменения LHC из чата GPTAdmin записи всё равно находятся в LHC.
Никакого обязательного выбора проекта или реестра привязок не требуется.

## Обязательное улучшение1.2.1 —2026-09-09

Источник1efe47b добавил независимый от карточек session checkpoint каждые120
минут незавершённой работы;7f1cb0f исправил native вход Codex.23 CLI-регрессии,
полный validator и parity22 skills прошли. Это тесты управляемого времени,
а не наблюдение двухчасового рабочего сеанса.

В текущем Codex native `plugin/read` возвращал0 hooks для переносимого входа,
но5 для `native/codex`. Этот generated вход находится внутри того же пакета,
строится из тех же common/skills/tools/hooks и не содержит затеняющий native
manifest файл `plugin.json`. Наружный Agent Plugins1.0 manifest сохранён.
Не распространяйте отдельные навыки вручную и не редактируйте cache.

Codex1.2.1 установлен native на100/88/Mac. Через штатные `hooks/list` и
`config/value/write` включены и прочитаны обратно пять конкретных hooks LHC
на каждом из этих hosts. В `hooks.state.<key>` записываются `enabled=true` и
`trusted_hash=currentHash` только после проверки команд выбранного плагина;
общий обход hook trust не применялся. Plugin installation сама по себе этого
не доказывает. Fresh Codex session01a085b5-2e56-75a3-833a-06e129fd30af создала
настоящий learning state в13:27:23+03 с due15:27:23 и обновила его после tools.
Сеанс реально прочитал установленный skill и native manifest1.2.1, но не выдал
финальный текст до100-секундного timeout. Подтверждены чтение и hook execution,
а не полное завершение этого model-сеанса; предыдущий1.2.0 сеанс завершился.

Hermes/Claude100 native обновлены до1.2.1. Fresh Hermes CLI загрузила skill
1.2.0; его SHA в1.2.1 неизменён. Claude fresh CLI заблокирована401 configured
API key до skill invocation. Hermes gateway не перезапускался. Сервер44
недоступен (`No route to host`); обновление там не подтверждено. Обычный
OpenCode100 loader timeout не устранён. Рабочие процессы со старым пакетом
не считаются обновлёнными без нового сеанса/штатного reload.

Hook запускает обязательную проверку на наблюдаемой границе действия: он не
прерывает долгий tool call и не будит простаивающего агента. Просроченный
checkpoint остаётся до явного `lhc_time_guard.py checkpoint` с наблюдением,
изменением метода либо обоснованным no-change, проверкой и оставшимся маршрутом.
Проверяется наличие evidence; истинность и исполнение остаются обязанностью
агента и reviewer. Без работающего hook действует явная ручная проверка.

## Обычная доставка

Источник: Agent Plugin `plugins/last-human-commit` в этом репозитории. Канон,
роли, инструменты и навыки входят в пакет. Отдельный Fleet-copy rollout для
обычного обновления отключён; standalone skill-дубликаты выводятся из загрузки.

Codex на 100/44/88/Mac использует marketplace `megamen32-plugins`:

```sh
codex plugin marketplace upgrade megamen32-plugins
codex plugin add last-human-commit@megamen32-plugins
```

Первичная регистрация: `codex plugin marketplace add https://github.com/megamen32/LastHumanCommit.git --ref main`.
OpenCode и ZCode читают этот же пакет из штатного checkout marketplace через
native `skills.paths`/`plugin` и `plugins.dirs`. Эти ссылки не зависят от номера
версии cache. Новый runtime не устанавливается лишь потому, что его команда
не найдена в SSH PATH: на Mac ZCode находится в `/Applications/ZCode.app`.

Hermes использует штатную установку того же пакета:

```sh
hermes plugins install megamen32/LastHumanCommit/plugins/last-human-commit --force --enable
```

В проверенных версиях Hermes `plugins update` не обновляет subdirectory install:
нет `.git` внутри установленной подпапки. Повторная native install выше — рабочий
путь обновления. Не заменять его ручным копированием. Native Hermes entrypoint
пакета сохраняет hook/middleware и регистрирует пакетные навыки.

После обновления начать новую сессию Codex/ZCode/OpenCode. Долгоживущий Hermes
gateway перезапустить штатным service manager, сохранив выбранный runtime и
service overrides. На Mac gateway был остановлен и не запускался автоматически.

## Приёмка 2026-09-05

- Пакет 1.1.2 установлен Codex на 100, 44, 88 и Mac; все пять shell-hook событий
  выполнены из установленного пакета с exit 0 при отсутствующих plugin-root env.
- OpenCode 100/44/88 обнаружил architecture-design, bootstrap и update skill.
- OpenCode Mac: обычный debug skill завис до завершения загрузки конфигурации;
  процесс только нашей проверки остановлен. Native `--pure debug skill` обнаружил
  навыки; отдельно реальный Bun импорт и вызов LHC chat.message hook PASS.
  Это не доказательство успешного старта Mac OpenCode со всеми чужими plugins.
- ZCode 100 и Mac: native plugin list, enabled, 1.1.2, 21 skills. Эта версия ZCode
  не поддерживает PreCompact/PostCompact hooks; не выдавать это за их выполнение
  самим ZCode. Общие shell-команды проверены отдельно.
- Hermes 100/Mac: 1.1.2, native hook registration. Старые `.prev-*` убраны из
  plugin discovery и сохранены в project-local `.tmp`. Рабочий runtime gateway
  100 отдельно загрузил 1.1.2 без plugin error; gateway перезапущен, active.
- Память пользователя дополнена явным правилом Agent Plugins вместо старого
  механизма копирования. Canonical update/rollout skills изменены вместе с пакетом.

Абсолютный путь hook вычисляется из корня установленного пакета; `${PLUGIN_ROOT}`
не используется. Shell fallback разрешает путь через HOME и configured marketplace
при отсутствии native root env. Жёстко заданные имена пользователей в portable
пакете не нужны. Проверять надо исполнение hook, а не только plugin list.
