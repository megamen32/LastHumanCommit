# Установка и обновление LHC

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
