# L19 — прямое назначение и ограниченная делегация

## Решение и изменение

- Для одной конкретной задачи с одним ожидаемым результатом Lead назначает одного Worker напрямую. Пользователю не нужно дополнительно просить «вызвать агента»; Worker не создаёт Child только ради передачи тому же автору того же результата.
- Child допустим при конкретной пользе, которая оправдывает передачу контекста, координацию и проверку: параллельная независимая работа, отдельная компетенция/доступ, слепая независимая приёмка или отдельно проверяемый результат.
- Child у Worker требует явного разрешения Lead с отдельными границами: задача, владелец и пути, зависимость, критерий приёмки и предел потомков/слотов. Без разрешения Worker не делегирует дальше. Lead может разрешить собственную ограниченную дочернюю сессию по тем же правилам.
- Внутреннее сообщение Lead может быть коротким, на любом языке и в рабочем формате. Автор конечного пользовательского файла отвечает за ясность и язык читателя; для русскоязычного человека — естественный понятный русский. То же правило относится к Lead, если файл пишет он.
- Правило синхронизировано между `AGENTS.md`, Lead/Worker, umbrella skill и `model-routing`, включая package и native Codex проекции. Регрессии проверяют противоречия между ними и прямое совпадение generated native-копий.

## Однократное сравнение расхода

| Маршрут | Токены | Слова в файле |
|---|---:|---:|
| Один автор пишет сам, первоначальный ход | 343 550 | 1 101 |
| Исправление пути к файлу после ошибки ведущего | 119 541 | — |
| Один автор, весь цикл | 463 091 | — |
| Lead и Child, суммарно | 343 285 + 592 346 = 935 631 | 1 133 |

Оба прогона использовали `gpt-6-luna`. Подробные файлы: `consumer-tests/token-comparison/direct.md` и `consumer-tests/token-comparison/delegated.md`. Прямой вариант включал один исправительный ход из-за относительной ссылки ведущего. Делегированный вариант потратил примерно вдвое больше токенов, чем полный прямой цикл, в этой конкретной пробе. Это один замер двух несвязанных ходов, а не универсальная оценка цены делегирования или обещание будущей экономии.

## Проверки источника

- `pytest -q tests/test_business_first_contract.py tests/test_umbrella_skill_router_pointer.py tests/test_model_routing_delegation_policy.py` — **45 passed**.
- `python3 plugins/last-human-commit/scripts/sync_skills.py --check` — **PASS**, parity 25 skills.
- `python3 plugins/last-human-commit/scripts/validate.py` — **PASS**, canonical and parity 25 skills.
- `python3 scripts/lhc_validate_graph.py .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — graph valid; 19 leaves, 15 dependency layers. Unknown estimates for earlier leaves remain; total finish time is not inferred.
- `git diff --check` — **PASS**.

## Публикация и manager readback

- Scoped commit: `4fafcc5bf48e558c4b8c38f224198b89c3b31819`; `main` pushed and `git ls-remote origin refs/heads/main` returned the same SHA.
- После push был выполнен `codex plugin marketplace upgrade megamen32-plugins --json`; он завершился без ошибок и обновил marketplace checkout. Затем native `codex plugin list` подтвердил `last-human-commit@megamen32-plugins` version `1.5.40`, `installed=true`, `enabled=true`.
- После того как parent направил не выполнять upgrade/install 1.5.40 до завершения L16/L17, никаких дальнейших plugin-manager mutations не проводилось. Marketplace refresh и обновлённое manager-состояние сообщены parent немедленно.
- Сохранённая запись `last-human-commit@fleet-lhc` осталась `1.5.36`, installed и disabled; её не меняли. Manager перечисляет ещё несколько старых локальных записей LHC, они disabled и не менялись.
- Manager source root: `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/native/codex`.
- Installed cache root: `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.5.40`.
- У SHA-256 совпадают native source, manager marketplace path и installed cache: `.codex-plugin/plugin.json` `842f5ad7338a1d057f888e6bea4c58a17d1cc80d3af06d02ea1c614fd9261a4d`; `skills/last-human-commit/SKILL.md` `30932164a69722b7ef1f092ef507b869f293c55381a0067eee835b690daf1495`; `skills/model-routing/SKILL.md` `074ed2d046b5deca5c780016852d01f4c88b243a4dcc1242da3f9029071add87`; `AGENTS.md` `1f9113da19c5e109d6c9aafefcb16d8e99f6691df30a7eb55444de6331c7f715`; `common/agents/Lead.md` `92337c9890dc23c6c2c2d36b2b271156930d7bb8eaa9e862041cf2161e7e36f0`; `common/agents/Worker.md` `e9b6867ca2dce51c1234d3e558ab77aae5e71f22f29f712e4286659e6ea1cf19`.
- Это подтверждает package-manager release/readback и файлы package cache, но не доказывает, какой entrypoint уже загружен конкретной сессией. Такого утверждения здесь нет. L16/L17 browser acceptance остаются отдельными незавершёнными листьями.
