# Установленный локальный наблюдатель и центральный просмотр

## Результат и точный payload

25.10.2026 сервер и два обычных наблюдателя установлены и работают.
Hosting владеет deploy/plan-mirror/** и этим документом; core/test/package/protocol
принадлежат отдельному исполнителю. Один последовательный этап, оценка 20 минут,
фактическое активное время не измерено. Дочерних исполнителей нет.
Рабочий минимум: два разрешённых хоста, native службы, локальные авторитетные
файлы, восстановимая центральная проекция. Расширение флота отложено.

Полный digest Python tools:
`0fc5ed06dfa31a30ff93a58647a638f2ab2810f56590792598ba882ee982d6d6`.
SHA256 lhc_plan_mirror.py:
`926be5b5c6fd545206d1b0d53fac2161189dddd93554acc55b3d55e4394a16ff`.

- server100 runtime: /home/roomhacker/.local/share/lhc-plan-mirror/releases/0fc5ed06dfa31a30/tools/.
- Mac runtime: /Users/user/.local/share/lhc-plan-mirror/releases/0fc5ed06dfa31a30/tools/.
- На каждом хосте ~/.local/share/lhc-plan-mirror/current указывает на release.
- Linux ~/.config/systemd/user/lhc-plan-mirror.service и lhc-plan-observer.service:
  enabled, active/running. Запускаются от roomhacker, bind 127.0.0.1:8769.
- Mac ~/Library/LaunchAgents/com.lhc.plan-observer.plist:
  gui/501/com.lhc.plan-observer, running, pid2631 при последнем readback.
  Python /opt/homebrew/opt/python@3.14/bin/python3.14.
- Серверные данные: /home/roomhacker/.local/share/lhc-plan-mirror/server/.
- Клиентские очередь/registry: ~/.local/share/lhc-plan-mirror/client/.
- Конфигурация ~/.config/lhc/plan-mirror/{server,client}.json;
  server.json только на server100. Каталог0700, файлы 0600.
- Различные секреты write-token и dashboard-key лежат отдельно 0600.
  Units содержат только пути, без значений.
- **Приватная ссылка хранится в защищённом локальном dashboard-url server100;
  передаётся владельцу напрямую.** Она не записывается в Git/планы/снимки.
  Пример маршрута: /dashboard/REDACTED/.

## Контракт и точный watched scope

Контракт — соседний interface.md; stdlib Python 3.10+, команды
lhc_plan_mirror.py serve/watch/once/register/status --config.
Linux endpoint http://127.0.0.1:8769; Mac https://lhc.bezrabotnyi.com.
API /v1/snapshots и /v1/status требует Bearer. Локальная
.lhc-publication/mirror.json сохраняет binding; CLI/MCP работает без env.

Linux explicit plans:

- /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/local-first-plan-mirror-20261025/.agents/tasks/20261025-local-first-plan-mirror
- **Оригинальный** /home/roomhacker/agents-projects/LastHumanCommit/.worktrees/live-plan-publishing-20261024/.agents/tasks/20261024-live-plan-publishing

Новые планы обнаруживаются только под
/home/roomhacker/.local/share/lhc-plan-mirror/plans и
/Users/user/.local/share/lhc-plan-mirror/plans, максимум три уровня.
Mac explicit fixture: /Users/user/.local/share/lhc-plan-mirror/consumer-plan.
Whole-home и старые частные проекты не сканируются.

Ошибочная регистрация tracked-копии старого плана удалена из client plans/registry.
Её созданные метаданные архивированы в .tmp/plan-mirror-copy-metadata/;
собственное изменение tracked observed.json восстановлено. Оригинальный state.json
и история сохранены. Ранняя центральная проекция копии не считается исходным
опубликованным планом; её отправки не replay.

## Реальные проверки

- Первоначальный Mac observer сам обнаружил fixture, получил серверную квитанцию.
- Новый сервер остановлен ровно один раз. На Mac raw-save и local revise без
  LHC_PLAN_MIRROR_CONFIG: rc0 за 0,131 секунды, две локальные ревизии.
  API во время остановки 502, старая и новая статические страницы 200.
  После запуска отложенный marker появился по HTTPS: local seq3=receipt seq3.
  Эта принятая ревизия не повторялась.
- Offline receipt относится к первоначальному payload 1ffca47db9f102e6.
  После установки финального payload выполнена отдельная обычная правка note
  Mac fixture без publish; marker MAC-FINAL-20261025-1128 найден на HTTPS-странице,
  local seq5=receipt seq5, две ревизии, last_successful_sync2026-10-25T11:27:30Z.
  Повторный outage ради нового SHA не запускался.
- Linux observer подтвердил успешные receipts текущего task, оригинального
  плана и нового fixture в выделенном roots; error=null.
- Приватная панель 200 при локальном защищённом readback; без capability
  индекс не раскрывается. Запрос API без токена не перечисляет планы.
- Syntax compile собственного installer/consumer helper прошёл.
  Выявленная teardown-задержка launchd исправлена ограниченным ожиданием
  и безопасной проверкой return codes; повторная установка прошла.
- Браузерную приёмку и тесты core hosting себе не присваивает.

Сохранённый старый URL:
https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261024-1634-01a6b48557d3f9ab9694c3b0/
SHA256 r001.html остался:
`bf3dd25661f3121acbf290a65769354891d7c09d8fc4a7d31c6b4b05e6870da0`.

Mac fixture:
https://lhc.bezrabotnyi.com/consumer-plan/plan-20261025-1418-4c03657014750e578bf07956/

Текущий task:
https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261025-1418-1a13acb09c4a962db06a23ce/

## nginx и сохранение соседей

Прочитаны канонические ServersAdministartion AGENTS/access-topology/inventory
и текущие nginx-dev AGENTS/README. Чужой WIP сохранён.
Штатные refresh/check и только nginxctl apply --site lhc.bezrabotnyi.com:
сначала no-op baseline уже живого идентичного LHC без reload, затем scoped apply.
Receipt rollback: /var/lib/nginx-dev/rollback/20261025T111705Z.
Managed payload:
/home/roomhacker/nginx-dev/state/files/sites-available/lhc.bezrabotnyi.com.
Точная собственная копия: deploy/plan-mirror/nginx.conf.
Добавлены только proxy /v1/ и /dashboard/ на 8769; dashboard access_log off.
Остальные /var/www/lhc напрямую обслуживаются nginx при остановленном сервере.
HAProxy, DNS, TLS, SSH config, native agent hooks и чужие службы не менялись.
Общий manifest с чужим WIP не включён в hosting commit; публикация managed
ingress в общем Git остаётся владельцу. Собственный payload сохранён в deploy.

Mac ~/.config/lhc исторически принадлежал root. Исправлен владелец только
этого каталога через существующий SSS macbook-user-sudo. Пароль не выводился.

## Отдельная редактированная запись диагностической ошибки

Tool-call **2026-10-25T11:18:53.090Z**, ответ **2026-10-25T11:18:55.215Z**.
Неотфильтрованный diagnostic launchctl output включил унаследованные
AGENT_HERDER_DISARM_TOKEN (управление агентами) и USERIO_MCP_TOKEN (доступ UserIO).
Значения, префиксы и auth URLs здесь отсутствуют.
Экспозиция ограничена transcript и его штатным сохранением; вручную в файлы,
Git, страницы и snapshots эти значения не записывались.
Сравнение собственных артефактов с двумя значениями в памяти не нашло совпадений.
Владелец уведомлён; чужие credentials не ротировались, службы не трогались.
Последующие launchctl readbacks выводят только state/pid/exit.

## Откат

Остановить только собственные две Linux-службы и Mac LaunchAgent.
Предыдущие releases сохранены; installer принимает их tools, сохраняя config/данные.
Не удалять local sources, history, очередь или старые HTML.
nginx откатывать только LHC payload через тот же scoped apply, без общего rollback.

Финальный payload 1.5.53 включает отключение legacy state.autopublish при binding
без смены identity/config/history. Предыдущая raw-save проверка seq5 относится
к предыдущему стабилизированному payload; после этой последней source delta
выполнена отдельная raw-save проверка MAC-153-20261025-1131: marker найден по HTTPS,
local seq6=receipt seq6, last_successful_sync 2026-10-25T11:29:29Z,
revision_count=2. SHA256 core на Mac совпал с указанным выше. Offline revise
повторно не выполнялась. Перед commit проверены семь собственных staged файлов
и 41 файл реплик/HTML: совпадений с двумя раскрытыми значениями и с новыми
runtime token/dashboard key нет. Значения при сравнении не выводились.

## Последний refresh по точному финальному core

Оба runtime повторно установлены тем же installer из текущего
`src/common/tools/` назначенного worktree; SHA core сверена отдельно на Linux
и Mac и совпадает с указанной в начале документа. Финальный delta: durable seq
до render, восстановление interrupted render при same-seq retry, HTTP400 для
malformed task objects и renderer signature в generation hash. Изменение
register с legacy autopublish=false также включено.

После этого refresh: Linux обе службы active/running; Mac observer running,
last exit never exited. Приватная панель HTTP200. Last-good static Mac fixture
HTTP200 и содержит уже принятый marker MAC-153-20261025-1131.
Новых raw-save, outage, revise и браузерных проверок не выполнялось;
предыдущие доказательства сохранены с их фактическими payload и seq.
Browser proof Lead (390/1280, active filter, refresh, JS errors) — отдельное
доказательство Lead; hosting его не переисполнял.

Архивные state.json и mirror.json ошибочной копии проверены против server replica:
identity/project/name и owner совпали. Перемещён **только**
`server/9b7898f7c50384c219b8e5e4.json` в
`server/retired/9b7898f7c50384c219b8e5e4.json` внутри server data_dir.
Исходники, история и HTML сохранены. Панель не перечисляет retired JSON;
дубль отсутствует, оригинальная identity присутствует. Старый r001.html снова
подтверждён HTTP200 с прежним SHA256 bf3dd256…6870da0.
Секреты, capability и остальные replica JSON не менялись. nginx не применялся.
