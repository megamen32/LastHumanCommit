# work-20260828 — операторские скиллы в плагине 1.0.0

Started at: 2026-08-28 00:40 (UTC+3), источник: ручные часы сессии; активное время: не контролировал.
Initial estimate: 20 / 60 active minutes.

## Запрос

lhc-rollout/lhc-update-agents оформить как часть LHC agent plugin 1.0 (общая
спека для всех харнессов). Ранее удалили плагин-структуру зря — против были,
когда не было спеки; теперь спека есть. Вопрос: были ли в LHC скиллы
(тестирование/написание кода и т.п.) — да, 10 канонических, не удалялись.

## Канарей

validate.py PASS (12 skills), plugin validate PASS skills=12 parity=PASS,
marketplace PASS, pytest 40 passed, зеркала идентичны, deployed == HEAD,
дерево чистое, всё запушено.

## Изменения

- skills/lhc-rollout (SKILL.md + scripts/lhc_rollout.py + references/manifest.md
  + assets/last-human-commit-fleet.json) и skills/lhc-update-agents/SKILL.md —
  канонично в репо; зеркала в plugins/last-human-commit/skills/ и в
  ~/.zcode/skills/ синхронизированы.
- SKILL.md портированы: канонический путь ~/agents-projects/LastHumanCommit,
  machine-wide секция, источник истины, установка на отсутствующие харнессы.
- Плагин поднят 0.3.0 → 1.0.0 (.codex-plugin + .claude-plugin), README
  маркетплейса обновлён; tests/validate.py SKILLS и plugin EXPECTED_SKILLS +2.
- self-improve: зафиксирован fingerprint вложенного time-guard флейка.

## Результат

- (заполняется при закрытии)
