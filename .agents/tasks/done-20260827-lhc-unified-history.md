# work-20260827 — правило единой истории

Started at: 2026-08-27 (UTC+3), источник: ручные часы сессии; активное время: не контролировал.
Initial estimate: 25 / 60 active minutes.

## Запрос

Обязательное правило: единая история. В конце полного цикла проект запушен,
включая чужие правки (отревьюенные и вобранные). В конце любого цикла и на
каждом законченном шаге — коммит своих файлов. Конечное состояние всегда:
чистое дерево, запушено, задеплоено, оттестировано. Ворктри пользователь
ненавидит: параллельная работа — одна история, как мозг.

## Канарей

`git status` пуст (кроме игнора), `git log @{u}..HEAD` пуст (всё запушено),
rollout verified, валидаторы зелёные, канон содержит раздел Unified history.

## Изменения

- AGENTS.md/Lead.md/SHARED_WORKTREE.md/task_template/FULL_CYCLE/RELEASE_HANDOFF/
  README: раздел/абзацы Unified history (коммит на каждом шаге; абсорб
  отревьюенных чужих правок с отчётом; конец цикла — чистое дерево; Full —
  pushed + deployed + real-surface tested).
- validate.py/test_business_first: требуют unified-history фразы и запрещают
  регрессию «Stage and commit only task-owned paths» / «Commit, only if requested».
- .gitignore: `.agents/at/`, `.agents/shared-session/time/`,
  `.agents/shared-session/compaction/`, `.serena/` (runtime-состояние).
- Вобраны легаси-untracked: 21 старый task-запись + результаты
  knowledge-consistency ревью.
- Для этого репо немедленно: 4+ непушеных коммита запушены, дерево вычищено.

## Результат

- Коммит 08b198a (после rebase поверх чужого c096e71 — новый hash в логе);
  валидаторы зелёные; дерево чистое (0); всё запушено в origin/main;
  rollout verified 100/44/88/mac; deployed current = pushed tip.
- Push чинился: SSH remote упал из-за смены host-key GitHub — remote
  переведён на HTTPS + gh credential helper; host-key НЕ принимался молча.
