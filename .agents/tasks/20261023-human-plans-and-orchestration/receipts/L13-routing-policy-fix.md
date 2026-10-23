# L13 — исправление routing policy

## Результат

Обычный Worker не делегирует по умолчанию. Lead может явно разрешить себе или
назначенному Worker ограниченного child, если в поручении заданы scope,
ownership, dependency, acceptance и пределы; child не расширяет их и не
делегирует дальше без отдельного явного разрешения.

Свежий blind/Zero Knowledge контекст применяется к независимой роли, когда
независимость входит в приёмку (например, Tester, которому надо самому пройти
пользовательский сценарий). Обычный исполнитель получает проверенные решения,
релевантные факты и достаточный контекст задачи.

## Канонические пути

- `AGENTS.md` — единственный source router. `src/AGENTS.md` отсутствует.
- `src/common/skills/model-routing/SKILL.md`
- `src/common/agents/Lead.md`
- `src/common/agents/Worker.md`
- `tests/test_model_routing_delegation_policy.py`
- Этот receipt: `.agents/tasks/20261023-human-plans-and-orchestration/receipts/L13-routing-policy-fix.md`

До изменения policy запрещала Worker рекурсивно нанимать исполнителей без
исключения, даже при прямом ограниченном разрешении Lead. Она также предпочитала
свежий Zero Knowledge контекст каждому независимому subtask. Теперь обычная
делегация запрещена по умолчанию с явным Lead-authorized исключением, а blind
контекст оставлен независимым ролям/приёмке, где он нужен.

В `src/common/agents/Lead.md` изменены формулировки про назначенный leaf и
quickfix: child assignment требует явного ограниченного разрешения Lead. В
`src/common/agents/Worker.md` описано то же исключение с точки зрения исполнителя.
В router обновлено аналогичное правило и контекстная свежесть. Иные ограничения
policy не менялись.

## RED / GREEN

- RED: новый тест на старом тексте провалил обе семантические проверки: отсутствовало
  Lead-authorized исключение и требование свежего blind контекста было общим для
  независимых исполнителей.
- В тесте parity первоначально сравнивались сырые байты. Это не соответствовало
  предусмотренным генератором заменам ссылок. Проверку исправил на ожидаемые
  преобразования: `src/common/` → `common/`, а
  `../../config/model-routing.example.json` → `references/model-routing.example.json`.
- GREEN: `pytest -q tests/test_business_first_contract.py tests/test_model_routing_delegation_policy.py`
  — 34 passed.
- `python3 plugins/last-human-commit/scripts/sync_skills.py --check` —
  `parity: PASS (25 skills)`.
- Поиск абсолютных старых формулировок в canonical router/agent/skill sources
  совпадений не дал.

## Native package parity

Пакет сгенерирован штатно командой
`python3 plugins/last-human-commit/scripts/sync_skills.py`. Вручную generated
файлы не редактировались. Генератор проектирует router/roles с заменой
`src/common/` на `common/`, а routing skill дополнительно перенаправляет пример
конфига на `references/model-routing.example.json`.

Сгенерированные файлы:

- Router: `CLAUDE.md`, `plugins/last-human-commit/AGENTS.md`,
  `plugins/last-human-commit/CLAUDE.md`,
  `plugins/last-human-commit/native/codex/AGENTS.md`,
  `plugins/last-human-commit/native/codex/CLAUDE.md`.
- Lead: `plugins/last-human-commit/common/agents/Lead.md`,
  `plugins/last-human-commit/native/codex/common/agents/Lead.md`.
- Worker: `plugins/last-human-commit/common/agents/Worker.md`,
  `plugins/last-human-commit/native/codex/common/agents/Worker.md`.
- Routing skill: `skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/common/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/native/codex/common/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/native/codex/skills/model-routing/SKILL.md`.

## SHA-256

Хэши относятся к итоговым байтам после генерации. В каждой строке перечислены
пути с одинаковым SHA-256.

- `13c5dcb63f7287a5d3c0636cc35c309ff421b1c7c831b10fc13f8c3ff381ae4c` —
  `AGENTS.md`, `CLAUDE.md`.
- `1082d94d15e155df4b8f90a621d9df93c9bd4d326c9b91cc3a4e8683dac92159` —
  `plugins/last-human-commit/AGENTS.md`,
  `plugins/last-human-commit/CLAUDE.md`,
  `plugins/last-human-commit/native/codex/AGENTS.md`,
  `plugins/last-human-commit/native/codex/CLAUDE.md`.
- `54f614f55a015091d8053df477a3a1d6dddd521b91bb392af06bae8142952091` —
  `src/common/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/common/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/native/codex/common/skills/model-routing/SKILL.md`.
- `5b637e195f090d616ed31377d66dfb000d7b2968c479b6f0523c37224d42473e` —
  `skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/skills/model-routing/SKILL.md`,
  `plugins/last-human-commit/native/codex/skills/model-routing/SKILL.md`.
- `1aab2e8d90e6d395b2c283c014df039bd19f3e762c6009bd9ba9b0fbea39c866` —
  `src/common/agents/Lead.md`.
- `9ab053ea22b8f27579c2d90760602ff2f6392f88b600b00d450fa7e40b09c316` —
  `plugins/last-human-commit/common/agents/Lead.md`,
  `plugins/last-human-commit/native/codex/common/agents/Lead.md`.
- `e83e9d41a9d157948aa15df62d80728db17ba2585b888c4fb20c4a137f43ccc6` —
  `src/common/agents/Worker.md`,
  `plugins/last-human-commit/common/agents/Worker.md`,
  `plugins/last-human-commit/native/codex/common/agents/Worker.md`.
- `54607de2db76731058fbecf93ff81ea77e55c1c8c5d406bbce680b71d678e860` —
  `tests/test_model_routing_delegation_policy.py`.

## Границы и ограничения

Не менялись version/manifests, task plans и consumer-test файлы; чужие изменения
в checkout сохранены. Коммит и публикация не выполнялись. Проверена source и
generated package parity, но не установка/перезагрузка runtime consumer.
