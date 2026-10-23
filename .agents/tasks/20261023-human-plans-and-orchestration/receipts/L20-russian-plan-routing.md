# L20 — русские просьбы о плане направляются в plan-artifacts

## Изменение

В canonical umbrella skill и `plan-artifacts` явно добавлены естественные запросы:
«составь план», «сделай план проекта», «помоги спланировать работу», «план
проекта» и «план работ». Запрос плана проекта/работы загружает `plan-artifacts`
и создаёт пользовательскую запись `task.md`, `plan.graph.json` и `plan.html`
(рендер также выдаёт `plan.md`).

Оставлены две явные границы:

- Если человек прямо просит только черновой текстовый набросок в чате, файлы не создаются.
- Короткая просьба записать или обновить один файл не превращается в проектный план, если проектный план не просили. Обычные правила планирования инженерной работы сохраняются.

Канонические источники: `src/common/skills/last-human-commit/SKILL.md` и
`src/common/skills/plan-artifacts/SKILL.md`. Синхронизированы package и native
Codex копии. Regression tests проверяют русские фразы, обязательные выходы,
обе границы и parity generated copies.

## Проверки до выпуска

- `pytest -q tests/test_umbrella_skill_router_pointer.py tests/test_model_routing_delegation_policy.py` — **15 passed**.
- `python3 plugins/last-human-commit/scripts/sync_skills.py --check` — **PASS**, 25 skills.
- `python3 plugins/last-human-commit/scripts/validate.py` — **PASS**, canonical and parity PASS.
- `python3 src/common/tools/lhc_grid.py export .agents/tasks/20261023-human-plans-and-orchestration/task.md --merge .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json -o .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — 20 задач.
- `python3 src/common/tools/lhc_grid.py render .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json --out-dir .agents/tasks/20261023-human-plans-and-orchestration` — создал согласованные HTML/Markdown.
- `python3 src/common/tools/lhc_grid.py check-plan .agents/tasks/20261023-human-plans-and-orchestration/task.md .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — **OK, 20/20**.
- `python3 scripts/lhc_validate_graph.py .agents/tasks/20261023-human-plans-and-orchestration/plan.graph.json` — **valid**, 17 dependency layers; неизвестные оценки L14–L18 сохранены, итоговый ETA не выводится.
- `git diff --check` — **PASS**.

## Commit и публикация

- Release commit: `45aec97c151ad8e4f0abc84433b94e3b44cf5b5b` на `main`.
- `git push origin main` завершился успешно; `git ls-remote origin refs/heads/main` вернул тот же SHA.
- Native Codex command `codex plugin marketplace upgrade megamen32-plugins --json` завершился без ошибок.
- Свежий `codex plugin list --json` readback: `last-human-commit@megamen32-plugins` **1.5.41**, `installed=true`, `enabled=true`, source `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/native/codex`.
- Rollback plugin `last-human-commit@fleet-lhc` **1.5.36**, installed и disabled; не изменялся.
- Installed cache: `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.5.41`.

SHA-256 совпадают между repository native package, manager marketplace source и
installed cache:

| Файл | SHA-256 |
|---|---|
| `.codex-plugin/plugin.json` | `655711035dab9bf34608427a0354389dbb5ac27908f7050c9b10b0a658336cb3` |
| `skills/last-human-commit/SKILL.md` | `a163550e077ef02e5b029b67cc91cbf707550ff9ca78e699571dd0d881e142ab` |
| `skills/plan-artifacts/SKILL.md` | `0931104175fca48773a6f2ba59d0a335d814f1b402171549122f93cbb9787a68` |

Manager readback and cache hashes confirm the selected package release; they do
not establish the exact entrypoint loaded in any particular new session. L16 and
L17 receipts from 1.5.40 are preserved. This Worker did not rerun either user
path; the Lead will run the short negative-trigger case and the project-plan
browser case in separate fresh sessions after this readback.
