# LHC: существующий личный SSO — инфраструктура

Назначение: закрыть браузерные маршруты lhc.bezrabotnyi.com существующим
auth.bezrabotnyi.com; после входа корень показывает каталог проектов/планов.
Машинные snapshots/status сохраняют Bearer, наблюдатели и история сохраняются.
Исполнитель: infrastructure Worker, без делегирования. Файлы: deploy/plan-mirror/sso*,
эта заметка и единственный назначенный managed vhost ServersAdministartion.
Core Python/UI/tests/package принадлежат другому исполнителю.

План (одна инфраструктурная задача, последовательно, оценка 15 минут):
1. Проверить контракт interface.md, managed nginx и текущие configs без секретов.
2. Добавить существующие auth snippets ко всем браузерным маршрутам;
   проксировать точный корень и dashboard с перезаписанным verified header.
3. Refresh/check, scoped commit/push и apply только lhc.bezrabotnyi.com.
4. После core READY обновить только mirror/observer штатным installer,
   сохраняя конфигурацию, plans/roots и защищённые ссылки.
5. Проверить анонимный/невалидный доступ, exact return URL, Bearer API,
   loopback bind и доступность каталога; отдельно отметить доступность owner fixture.

Выбранный маршрут: переиспользовать рабочий cookie-auth_request nginx.
Идеальный вариант с отдельной реализацией входа не нужен: существующий SSO
уже решает задачу. Минимальная реализация сохраняет весь требуемый результат.

Доступ: прямое назначение разрешает site-scoped sudo/apply и перезапуск только
LHC mirror/observer. Существующий TEST_ACCESS.md относится к прежней source-задаче;
личные сессии/куки не извлекаются, новые аккаунты и SSO credentials не создаются.
Полный launchctl/env/config auth dump запрещён. Секреты не входят в Git/отчёт.

Исходное состояние: HTTP→HTTPS; HTTPS корень/статические планы без SSO;
/v1/ и /dashboard/ проксируются на loopback 8769. В monorepo есть чужой WIP
в AGENTS, inventory, disk-cleanup, airlockplan и других путях; он сохраняется.
AgentMemory не дал релевантных результатов; используются проверенные live/source.

## Готовый инфраструктурный handoff — 25.10.2026

Владелец дальнейшей доставки по прямому уточнению пользователя:
Codex Luna `01a1744b-71ee-70e0-a4ef-06d54c6aac70`. Она координирует runtime
integration, consumer checks и final release. Этот Worker новых сессий не создаёт.

Готово:
- `deploy/plan-mirror/sso-nginx.conf` — новый SSO payload, точная копия managed
  vhost `nginx-dev/state/files/sites-available/lhc.bezrabotnyi.com`.
- ServersAdministartion main: `2110a575fd7eb87ac46339c1fdb718792aecdbdb`
  (SSO) и `da27b926` (точное исключение дополнительного status URL).
  Оба опубликованы на origin/main. Коммиты содержат только LHC vhost и
  соответствующую запись manifest, сгенерированную `nginxctl refresh`.
- Применён только `sudo -n ./nginxctl apply --site lhc.bezrabotnyi.com`.
  Оба вызова завершились 0; последний rollback snapshot:
  `/var/lib/nginx-dev/rollback/20261025T182402Z`.
- `nginxctl refresh`, `check`, `git diff --check` успешны; после rollout
  `sudo nginxctl diff --source /etc/nginx`: `no managed drift`.
- Слушатели mirror 8769 и cookie-auth 18991 доступны только на 127.0.0.1.
  Mirror и observer systemd active/running; другие службы не менялись.
- ACME HTTP location сохранён; public ingress, TLS, DNS и общие SSO snippets
  не менялись. Корень и dashboard проксируют verified=1 только после auth_request;
  machine locations очищают внешний verified-header.

Наблюдения HTTPS:
- Анонимные `/`, `/project/plan/`, `/project/plan/version.json`,
  `/project/plan/r001.html`, `/dashboard/invalid/` → 302 existing SSO.
- Реальный старый dashboard capability также → 302; значение читалось только
  внутри процесса из существующего защищённого файла, нигде не записывалось.
- Cookie с невалидным значением и внешний `X-LHC-SSO-Verified: 1` не обходят SSO.
- Корень возвращает точный Location:
  `https://auth.bezrabotnyi.com/login?rd=https://lhc.bezrabotnyi.com/`.
- `POST /v1/snapshots` без Bearer → 401, без Location.
- `GET /v1/status` с существующим Bearer → 200, без Location; каталог = 8 планов.
  Bearer доставлен в запрос внутри процесса, значение не выводилось.
- Дополнительный `GET /v1/snapshots/status` первоначально → 302 (найдено Luna).
  После исправления точного location: анонимный, invalid-cookie и spoof-header
  варианты → app 404, без Location. Это НЕ существующий endpoint core:
  установленный и новый Python обслуживают `/v1/status`; новый API не добавлялся.
- `/health` извне → 302, нового незащищённого discovery нет.

Точные остатки для Luna:
1. Live server config ещё `sso_enabled: false`; новый core runtime НЕ установлен.
   Корень уже приватен, но после успешного входа до обновления app вернёт 404.
2. Core Worker уведомлён: текущий install-native.py пересоздаёт client/server
   config. Нужны сохранение всех существующих полей и plans/roots + sso_enabled.
   Не запускать старый installer без сохранения этих параметров.
3. Наблюдатель сейчас имеет 2 явных plan и 1 root; mirror содержит 8 планов.
   Никакие скопированные истории не регистрировались. Полнота инвентаря не доказана.
4. Реальный valid-owner SSO login не проверен. Одобренный owner fixture этой
   сессии неизвестен; сессии не создавались, личные cookies не извлекались.
   Loopback spoof-header не использовался как доказательство SSO входа.
5. Старая `deploy/plan-mirror/nginx.conf` сохранена, поскольку она вне assigned
   sso* scope; она описывает старый public payload и НЕ должна применяться теперь.
   Актуальный payload — `sso-nginx.conf` и опубликованный managed vhost.

Откат: nginxctl автоматически восстанавливает snapshot при провале проверки.
При проблеме нового app оставить SSO включённым и восстановить предыдущий
native release с сохранением configs/данных; временный 404 после SSO безопаснее
публичного каталога. Ручное восстановление старого pre-SSO vhost снова откроет
планы и требует явного решения владельца; общий apply/rollback не выполнялся.

Чужой WIP monorepo и shared LHC worktree сохранён. Пока шла работа,
чужой ранее локальный коммит был независимо опубликован его владельцем;
наша публикация стала обычным fast-forward без переноса/перезаписи его истории.
