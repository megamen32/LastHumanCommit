# work-20260827 — machine-wide установка + скилл lhc-update-agents

Started at: 2026-08-27 ~21:00 (UTC+3), источник: ручные часы сессии; активное время: не контролировал.
Initial estimate: 40 / 120 active minutes.

## Запрос

1) `.last-human-commit` больше не ставится в каждый проект — установка одна
на машину (`~/.local/share/last-human-commit`). 2) Нужен скилл «переписать
LHC»: исходники тут; обязательный push ДО правок если грязно (baseline, чтобы
изменения бота были отличимы) и push ПОСЛЕ; затем применение ко всем
установленным харнессам (минимум zcode/codex/opencode/hermes).

## Канарей

Роутеры проектов ссылаются на machine store (absolute current/common/...);
per-project `.last-human-commit*/` удалены на 100/44/88/mac; скилл
lhc-update-agents переписан; дерево чистое; всё запушено; deployed == HEAD.

## Изменения

- lhc_rollout.py: режим `projectRuntime: null` (machine-wide) + фикс
  `has_changes` (вложенные роутеры проектов теперь учитываются — без фикса
  apply молча пропускал замену роутеров).
- Манифест флота: projectRuntime=null, projectReplace удалён; док обновлён.
- ~/.zcode/skills/lhc-update-agents/SKILL.md переписан под новый процесс
  (baseline push → правки → валидаторы → commit+push → rollout → канарей;
  установка на отсутствующие харнессы).

## Результат

- (заполняется при закрытии)
