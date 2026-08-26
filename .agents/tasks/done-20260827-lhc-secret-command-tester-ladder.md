# work-20260827 — /secret команда + скилл тестера + возврат Reviewer

Started at: 2026-08-27 (UTC+3), источник: ручные часы этой сессии; активное время: не контролировал.

## Запрос пользователя (суть)

Идея AskSecret не ужасна — проблема была в церемонии вокруг неё. Нужна команда
/secret для codex/minimax/zcode: удобно скинуть/вставить секрет с телефона (не
открывая .env вручную). Ревью иногда нужно — вернуть как опцию. Тестеру —
подробный скилл: accessibility tree насколько возможно; при доступности и
suitability — улучшенные MCP (browserclaw/touchpoint/agent-browser); хуже но ок —
CDP/Playwright; XY-клики — последний шанс, не забывать прежде чем говорить
«невозможно». Плюс: прочитать кодекс-сессии вокруг матов пользователя и поискать
в интернете существующие решения.

## Evidence (2026-08-27)

- Кодекс-сессия 2026-08-18: кнопочный AskHuman-ритуал, пользователь:
  «lhc -заебал меня заставлять всё подтверждать. убери эти…». Выжившие слои:
  AskSecret → pswd.bezrabotnyi.com/mcp, AskHuman → notify.bezrabotnyi.com/mcp
  (уже в ~/.codex/config.toml:502-516 и в zcode-сессии как MCP-инструменты).
  Боль = принудительные подтверждения и церемония, не сам инструмент.
- Интернет: 1Password+Telegram approve (reddit r/1Password tool), Infisical
  pull-based (`infisical run`), Agent Secret (kovyrin.net) — паттерн
  «телефон как поверхность подтверждения/вставки» валиден, своего MCP достаточно.
- BrowserClaw подтверждён: idan-rubin/browserclaw — a11y snapshot + ref
  targeting (Playwright резолвит ref).

## План (Short, direct)

1. /secret: zcode-скилл + codex-prompt + каноничная копия в репо; оркестрация
   существующих AskSecret/AskHuman MCP; запрет эхо значения и новой инфраструктуры.
2. Канон: «Secrets are not work» + одна строка про санкционированный /secret и
   запрет подтверждений на рутину.
3. Reviewer вернуть как optional risk-triggered (5 ролей; Adviser/Critic остаются
   удалёнными).
4. Tester.md + skills/real-use-testing/SKILL.md: лестница инструментов.
5. Валидатор/тесты под 5 ролей и новые фразы; прогон; коммит; rollout.

## Прогресс

- 2026-08-27 — исследование завершено (см. Evidence); реализация начата.

## Result (2026-08-27)

- Commit cd470f6; validators green (validate.py 5 roles, 39 pytest, task_states,
  marketplace, hermes plugin 10, plugin parity 10).
- Rollout cd470f6 preview/apply/verify complete on targets 100/44/88/mac.
- /secret installed: ~/.zcode/skills/secret/SKILL.md, ~/.codex/prompts/secret.md,
  canonical src/common/commands/secret.md (deploys via bundle).
- MiniMax: no slash-command mechanism found on disk (~/.minimax empty,
  ~/.config/minimax has only env) — not installed there, noted to user.
