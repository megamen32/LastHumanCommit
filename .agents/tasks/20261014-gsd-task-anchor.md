# OGSD: сохранение исходного поручения

Started at 2026-10-14T03:12:37+03:00 (clock MCP). Активное время до03:13:13 не контролировал; далее lhc_active_time ledger gsd-task-anchor-active.json.
Оригинальная оценка: trace+regression15–25мин, adapter+install15–25мин, Codex real consumer+review20–30мин: сумма50–80мин, последовательный critical path50–80мин. Независимый read-only Overseer не конкурирует с source.

Результат: тонкий originalGSD/OGSD сохраняет исходную цель, уточнения, мандат, проект, границы и приёмку; сверяется с current SPEC/PLAN/STATE и остальными GSD documents на entry/reentry/resume/compaction/смене направления.
Canary: настоящий Codex с установленным native GSD, свой проект/план → неподтверждённый detour → продолжение своего плана → разрешённый handoff → resume/compaction с сохранённой целью; collision блокирует только конкретный ресурс.
Минимальный slice: один session-scoped task anchor в существующем .agents/, короткий reference в существующем adapter/autoentry и focused regressions; upstream workflow/SDK сохраняются.
Discard: новый workflow/scheduler/supervisor, global config.toml, Exmanager/Go/Node/runtime, UserIO/Airlock, телефоны/ключи/чужие сессии, новые worktrees, чужие milestones.

## Полномочия и source
Прямой пользовательский brief: /home/roomhacker/agents-projects/exmanager/.agents/tasks/briefs/20261014-gsd-task-anchor-adapter.md (прочитан полностью).
Canonical cwd/main: LastHumanCommit. Исходный checkout чист. Existing worktrees чужие, не трогаем.
GSD package mirror: plugins/gsd. Live originalGSD personal overlay владеет /home/roomhacker/agents-projects/gsd-agent-plugin (clean main); существующий OGSD integration владеет /home/roomhacker/ServersAdministartion/templates/fleet-codex-instructions/{ogsd_project_state.py,ogsd_autoentry.md,install.py,test_ogsd_autoentry.py}.
Infra foreign WIP: .agents/tasks/20261013-userio-matrix-browser-budget.md — сохраняем, не commit.
Global ~/.codex/config.toml запрещён для edits. Installed caches не source.

## State
COMPLETE: originalGSD/OGSD source published/main, normal native GSD install and scoped OGSD install verified. Real Codex same thread opened before update, resumed after it: own current plan followed, unverified Root/Bob detour rejected, human-appointed Alice handoff accepted and linked, actual compaction preserved original task, exact foreign file collision preserved while independent own work completed. After final installed detector change, same-thread paged reentry passed with native CODEX_HOME and fresh current plan.
Current SPEC: .planning/phases/01-task-continuity/01-SPEC.md
Current PLAN: .planning/phases/01-task-continuity/01-01-PLAN.md
Current STATE: .planning/STATE.md
Native consumer: .tmp/gsd-native/{result.json,final-reentry-result.json,*-native.jsonl}. Recorded outputs created by actual installed Codex/GSD, not test doubles.
Relevant checks: LHC package11 passed, actual live integration24 passed, OGSD13 passed. Independent initial Overseer CONTINUE; Reviewer original/delta APPROVE.
Installation: native codex plugin add gsd@megamen32-public; existing OGSD install.py --ogsd --apply/--check; installed source/readback and original SDK owning-root recognition verified. config.toml content unchanged by manager, models/keys unchanged.
Limitation: current Codex portable AgentPlugin loader intentionally skips plugin hooks. Supported existing OGSD instruction surface + original skill reference proves continuity; no automatic native hook delivery claimed. No unsupported hook copies, scheduler or runtime patch.
Foreign WIP: Infra .agents/tasks/20261013-userio-matrix-browser-budget.md preserved; no other checkout clean claim.

## Budget
Source regressions expected3s/emergency30s: one process/worker, RAM soft=hard512MiB, swap0, CPU1, tasks64, .tmp64MiB, IOWeight20. Native Codex canary expected300s/emergency3000s: one own consumer, RAM soft=hard2GiB, swap0, CPU2, tasks256, .tmp256MiB, IOWeight20. Host fresh MemAvailable36GiB, preserve20GiB host reserve; no foreign runtime changes. Native parent limits inspected before canary admission. No broad suite/build.

## Regression evidence
RED: PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python3 -m pytest -q /home/roomhacker/agents-projects/gsd-agent-plugin/tests/test_task_continuity.py --basetemp=.tmp/pytest/red --override-ini cache_dir=.tmp/pytest/cache -> 3 failed/1 passed (0.35s): session task absent, initial record absent, continuity reference absent.
RED: python3 /home/roomhacker/ServersAdministartion/templates/fleet-codex-instructions/test_ogsd_autoentry.py -> 1 failed/11 passed (1.12s): foreign portfolio native root accepted.
GREEN: same focused tests -> 4 passed (0.37s) and 12 passed (0.98s).
Method change: existing SessionStart now restores bounded saved assignment from its native session identity; existing adapter loads one continuity reference. Authority remains actual human mandate, not sender assertion. Initial independent Overseer CONTINUE.

Technical independent Reviewer: APPROVE, no blocking findings; actual consumer remains pending. Packaging checks: LHC11 passed; live integration17 passed; OGSD12 passed. Mixed-repository pytest invocation hit a module-name collision, reran with correct owning cwd; one explicit basetemp parent was absent, created it before run. No source workaround or removed coverage.

Native discovery: Codex0.162.1 plugin/read + hooks/list return hooks=[] for original portable AgentPlugin; official core-plugins loader intentionally skips hooks when manifest format=AgentPlugin (loader.rs913–923). No hook execution is claimed or forced, no runtime patch or config fallback. Existing authorized OGSD instruction materializer + installed originalGSD skills is the supported consumer; validate actual task/policy/current docs reads on same native thread across resume/real compaction. Hook source retained for harnesses supporting existing legacy declaration.

Consumer exposed another adapter defect: detector ignored native CODEX_HOME and selected global plugin while own consumer used isolated native home. RED: OGSD13 tests1failed (expected custom plugin path, actual global path). Minimal fix: honor native CODEX_HOME, optional exact --codex-home and existing --home override precedence. GREEN13 tests. No model/key/config.toml changes.

Current direct user correction: «Забудь про тот бриф. Ты можешь его править на здоровье.» This removes the earlier config.toml restriction discussed immediately before it. Original adapter task and ownership remain; normal GSD native installation is authorized, no model/key changes. Single-plugin-only native add avoids whole-marketplace/foreign-plugin update.

Final reentry harness failure shield: asyncio default stdout.readline limit64KiB cannot consume the grown native full-history resume JSON line; a focused transport repro returned “Separator is found, but chunk is longer than limit”. Own native scope run-u8350 stopped after read-only resume, before payload; previous accepted fixture actions preserved. Disposable client now uses supported thread/resume excludeTurns=true and finite2MiB stream limit; no product/runtime changes. Rerun only same-thread final reentry, no previous action replay.

## Closure learning
Product loop closed: reported task loss → focused Red/Green → published owning adapter reference → normal installed native consumer. Native CODEX_HOME mismatch repaired by another focused Red/Green and fresh final reentry. Method loop closed: retrieve actual source ownership, reject unsupported hook assumptions, use one continuity reference with original mandate/current docs; independent review and later same-thread reuse after native compaction/reentry verified. No useful additional method change beyond these owning fixes. Native time-guard hook absent; manual checkpoint inspection done; hook checkpoint CLI correctly refused because no observed session checkpoint existed, no fake receipt created. Original whole forecast remains50–80min; no overrun.

Measured checkpoint before final publication: 1577.002s active since03:13:13.934+03 (explicit monotonic ledger). Cycle wall anchor03:12:37+03; first36.934s не контролировал. Final publication remains measured by resumed same ledger; original estimate50–80min retained.
