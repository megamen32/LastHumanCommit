# LHC: работающий хост и сохранение nginx-конфигурации

Актуально на **24.10.2026, 16:46 МСК (13:46 UTC)**. Сайт уже работает.
Первоначальная диагностика неправильного сертификата и отсутствующего webroot
была историческим состоянием до развёртывания Lead; она больше не описывает
текущий хост. Bootstrap и повторный выпуск сертификата не нужны.

## Поручение и выполненная работа

Новое назначение: сохранить только уже развёрнутый LHC vhost/enablement в
управляемом nginx-dev, обеспечить reload после продления его сертификата,
сохранить чужой WIP и проверить существующий публичный путь. Один
последовательный этап; начальная оценка и активные минуты не измерялись.

Результат: канонический локальный managed source содержит LHC; отдельная
ветка инфраструктуры опубликована с узким итоговым diff; LHC renewal hook
установлен. Существующие `deploy/live-plans/nginx.conf` и `README.md` сохранены.
Core, плагины, тесты и файлы других исполнителей не изменялись и не stage.

## Текущее живое состояние: независимый readback

- DNS A через системный resolver: `lhc.bezrabotnyi.com → 95.165.165.65`.
- Публичный GET `https://lhc.bezrabotnyi.com/`: **200**, TLS verify result **0**.
- Публичный GET
  `https://lhc.bezrabotnyi.com/lasthumancommit/plan-20261024-1634-01a6b48557d3f9ab9694c3b0/`:
  **200**, TLS verify result **0**; повторный HEAD — HTTP/2 200.
- Публичный сертификат: CN/SAN `lhc.bezrabotnyi.com`, notBefore
  `2026-10-24 12:33:01 UTC`, notAfter `2027-01-22 12:33:00 UTC`.
  Это метаданные сертификата, не время исполнения команды выпуска.
- HAProxy `public_https` TCP :443 → default `be_local_https` → nginx
  `127.0.0.1:8444`; TLS завершается в nginx. HAProxy не менялся.
- Live vhost `/etc/nginx/sites-available/lhc.bezrabotnyi.com`, enabled link
  `/etc/nginx/sites-enabled/lhc.bezrabotnyi.com` →
  `/etc/nginx/sites-available/lhc.bezrabotnyi.com`.
- SHA256 live vhost, `deploy/live-plans/nginx.conf` и нового managed payload
  одинаков: `18a259e15311c28addaf7eb4ec37d8de2f464275eb8d71c07f31c15c5407c839`.
- `/var/www/lhc`: `roomhacker:www-data`, mode 2755. Права не менялись.
- Ответ плана содержит `no-store`, `noindex, nofollow, noarchive`, `nosniff`,
  `no-referrer` и CSP. Корень содержит нейтральную страницу, а не список планов.
  GET `/lasthumancommit/` и `/.lhc-owner` — **403**, листинг недоступен.
  Новые source-кандидаты не подменяли уже установленный vhost.

Эта проверка доказывает hosting GET/TLS. Поведение publisher, неизменность
ревизий и браузерное обновление относятся к отдельной проверке core Lead.

## Managed source: узкое изменение без apply

Канонический checkout: `/home/roomhacker/ServersAdministartion`, текущая ветка
по-прежнему `main`; checkout не переключался, новые Git worktree не создавались.
Добавлен только payload
`nginx-dev/state/files/sites-available/lhc.bezrabotnyi.com`.
Штатные `sudo ./nginxctl refresh` и `sudo ./nginxctl enable
lhc.bezrabotnyi.com --target /etc/nginx/sites-available/lhc.bezrabotnyi.com`
добавили в `state/manifest.json` ровно две записи: файл и enabled symlink.
`sudo ./nginxctl check` прошёл: **store and round-trip are valid**.

Сохранность чужого состояния проверена семантически: после исключения двух
новых LHC-записей JSON manifest полностью совпадает с исходным состоянием.
SHA256 нормализованного исходного JSON:
`13615cb18440861dd81b6afc40636c57fa84f74c4bdf02e6f67e2d17042f6360`.
Чужие payload `agent.bezrabotnyi.com` и `new.auto-gram.ru` побайтово сохранены.
Исходный manifest остался `root:root`, 0600; права не исправлялись ради доступа.

Для публикации подготовлен отдельный **не checkout** native nginx store под
`.tmp/lhc-persistence.XWrexB`, из Git-архива актуального upstream. Использованы
поддерживаемые CLI `--store ... refresh`, `enable`, `check`; Git alternate index
не затрагивал общий index. Ветка создана через commit-tree без переключения main.

Публичная ветка инфраструктуры:
`lhc-host-persistence-20261024`.
База: `7f7952fa127d4de9bf57984bf4a6b8027d012bc8` (`origin/main` при создании).
Подтверждённый remote tip:
**`2f2e5303dd3a414a7163b6947eabc3b3c6706db5`**.

Итоговый diff к базе: **два файла, 53 добавления** — LHC vhost и две записи
manifest. Никаких изменений других записей manifest, policy, HAProxy или приложений.

Важно для воспроизводимости: upstream manifest содержит уже существующий
устаревший hash `sites-available/agent.bezrabotnyi.com`:
`5ce2284e…` против payload `7d3cc683…`. Нативный refresh временного store
нормализовал и этот чужой hash. Первый опубликованный коммит `4d55f412…`
содержал это побочное изменение; следующий коммит восстановил в индексе
исходную upstream-метадату. Итоговая ветка проверена: после удаления двух
LHC-записей весь manifest равен базе. Чужой live/local manifest не откатывался.
Поэтому успешный round-trip относится к локальному каноническому store и
временному нормализованному store, а не к унаследованно несогласованному
upstream manifest. Его сторонний дефект этой задачей не присваивается.

## Почему ветка пока не включена в общий main

`nginx-dev-sync.timer` активен; общий main не push и не merge этой сессией.
От deployed SHA `57716785aa315772d1c7695e06f76f31570932ba` до upstream
`7f7952fa…` уже накоплены посторонние vhost: `00-airlock-demo88.conf`, `agent`,
`desktop`, `dns`, `kube`, `notice`, `noticeplace`, `notify`.
Изменений rendering inputs в этом диапазоне нет: утверждать, что нужен full
apply, было бы неверно. Но общий sync потенциально попытается применить
эти чужие хосты; это выходит за полномочие на LHC. Дополнительно общий checkout
содержит чужой WIP, а upstream — описанный выше stale hash.

**Точный следующий шаг интеграции:** владельцу общего ingress включить только
итоговый diff ветки `lhc-host-persistence-20261024` в его разрешённый цикл main,
сохранив актуальные записи общего manifest. Никакой full apply или перезапуск
HAProxy для LHC не нужен: live vhost уже идентичен сохранённому source.
Если нужен отдельный receipt apply, он только `nginxctl apply --site
lhc.bezrabotnyi.com`, после интеграции и с проверкой уже существующего состояния,
не общий sync/apply. Эта сессия apply и reload не запускала.

## Продление сертификата

Существующий LHC renewal использует webroot `/var/www/letsencrypt`, без
deploy_hook. Старые hooks проверяют другие lineage. Установлен только
`/etc/letsencrypt/renewal-hooks/deploy/40-lhc-reload-nginx`, root:root 0755,
из `deploy/live-plans/renewal-deploy-hook.sh`:

```sh
[ "${RENEWED_LINEAGE:-}" = /etc/letsencrypt/live/lhc.bezrabotnyi.com ] || exit 0
/usr/sbin/nginx -t
/bin/systemctl reload nginx
```

SHA256 hook: `a70d6d9aa7f5bef5a07f241a823745b7231969075be867b4cdcc5946553763a0`.
Синтаксис `sh -n` и выход без действий для чужого lineage проверены.
Живой `sudo nginx -t` прошёл. Hook с LHC lineage вручную не запускался,
renew/force-renew не выполнялись, новая ACME account не создавалась.
Существующий `snap.certbot.renew.timer` продолжает обслуживать продления;
его расписание и соседние hooks не менялись. Фактическое следующее продление
ещё не наблюдалось — это не выдано за выполненную проверку.

Устаревшие ранние bootstrap/TLS-кандидаты из этой задачи удалены, чтобы не
подменить фактический `deploy/live-plans/nginx.conf`. Пример `publish.example.json`
сохранён: `base_url=https://lhc.bezrabotnyi.com`, `webroot=/var/www/lhc`.
