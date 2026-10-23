# LHC native release preflight (read-only)

Дата проверки: 2026-10-23. Репозиторий: `/home/roomhacker/agents-projects/LastHumanCommit`, текущая ветка `main`.

## Канонический маршрут

- Источник изменений — `src/common/` и `adapters/`; доставочный пакет — `plugins/last-human-commit`. Корень `skills/` и копии внутри пакета — generated projection, не редактировать напрямую: `plugins/last-human-commit/skills/lhc-update-agents/SKILL.md:8-15`, `docs/plugin-delivery.md:1-12`.
- Перед выпуском Worker должен выполнить `python3 plugins/last-human-commit/scripts/sync_skills.py`, затем `python3 plugins/last-human-commit/scripts/sync_skills.py --check`, релевантные behavioral tests и оба validator/parity checks. Точный общий validator: `python3 plugins/last-human-commit/scripts/validate.py`; это следует из `plugins/last-human-commit/skills/lhc-update-agents/SKILL.md:14-18` и `plugins/last-human-commit/README.md:66-73`.
- Все package manifests обязаны иметь одну версию; `validate.py` сверяет root JSON, Codex/Claude/ZCode manifests, Hermes YAML и catalog parity (`plugins/last-human-commit/scripts/validate.py:68-114`). Текущая исходная версия до изменений: `1.5.36` в `plugins/last-human-commit/plugin.yaml:2` (JSON/YAML parity проверяется validator'ом).

## Публикация исходника

- Обычная поставка — native Agent Plugin marketplace/manager; legacy Fleet file-copy rollout запрещён как обычный путь: `docs/agent-authoring.md:76-82`, `src/common/skills/lhc-rollout/SKILL.md:8-13`.
- Для source publication отдельный native outcome должен связать exact root, owned paths, remote/ref и immutable candidate; после native push обязателен `git ls-remote <remote> refs/heads/<branch>` readback с ожидаемым SHA и blob/candidate proof. Реализация проверок: `plugins/last-human-commit/tools/lhc_source_publication.py:106-149,404-451`; outcome reviewer требует native push + exact current branch readback + candidate proof: `plugins/last-human-commit/tools/lhc_outcome_review.py:1331-1343`.
- Remote/branch в текущем delivery guide явно не зашиты; перед push Lead/Worker должен взять фактический canonical remote и разрешённый target из актуальной authority, не из этого preflight.

## Native manager и установленный readback

Codex (на поддерживаемых Fleet hosts 100/44/88/Mac):

```sh
codex plugin marketplace upgrade megamen32-plugins
codex plugin add last-human-commit@megamen32-plugins
codex plugin list --marketplace megamen32-plugins --json
```

Первичная регистрация marketplace, если отсутствует: `codex plugin marketplace add https://github.com/megamen32/LastHumanCommit.git --ref main`. Документированные команды и marketplace scope: `docs/plugin-delivery.md:63-74`. Installed readback должен показать exact plugin identity, marketplace, target version, `installed=true`, `enabled=true`; checker canonicalizes the command as `codex plugin list --marketplace <marketplace> --json` and matches version in `plugins/last-human-commit/tools/lhc_outcome_review.py:685-715`.

ZCode:

```sh
zcode plugins marketplace add /home/roomhacker/agents-projects/LastHumanCommit
zcode plugins install last-human-commit@last-human-commit
zcode plugins list
```

`zcode plugins list` must independently show enabled package/version and hook count; then open a new ZCode session because a running session keeps its hook snapshot (`docs/plugin-delivery.md:87-96`).

Hermes:

```sh
hermes plugins install megamen32/LastHumanCommit/plugins/last-human-commit --force --enable
```

The guide states that Hermes `plugins update` does not update a subdirectory install; repeat native install for an update, never hand-copy files (`docs/plugin-delivery.md:97-104`). The exact Hermes list/readback command is not specified in this repository and must be obtained from the live Hermes native manager before claiming installed acceptance.

OpenCode uses the same marketplace checkout through native `skills.paths`/`plugin` and `plugins.dirs`; no package-version cache path is a source of truth (`docs/plugin-delivery.md:74-76`). Readback must prove the effective installed plugin root/skills path through the live OpenCode config/loader, then a fresh session canary; no exact OpenCode CLI install command is documented here.

## Fleet and reload limits

- “Fleet independent readback” means independently query each selected host's native manager/loader after publication; it is not a legacy file copy. A package installed on one host does not prove other hosts or runtimes.
- Installation/list output proves registration only. Run an ordinary engineering-request canary through the installed loader, not only an explicit skill invocation: `plugins/last-human-commit/skills/lhc-update-agents/SKILL.md:19-22`.
- Existing sessions are not implicitly reloaded. Start a new Codex/ZCode/OpenCode session after update; long-lived Hermes gateway needs its native service-manager restart. A new installed package/readback is not evidence that the currently active chat reloaded: `plugins/last-human-commit/README.md:69-94`, `docs/plugin-delivery.md:104-108`.
- Therefore final evidence must report separately: source validation, package/publication receipt, per-host installed manager readback, fresh runtime loading/canary, and any active-session reload status. Do not label an active old chat updated solely from package installation.

## Uncertainties to resolve during authorized release

1. Exact new version must be chosen and applied consistently to every manifest; `1.5.36` is only the pre-change baseline.
2. Canonical remote/branch and the selected Fleet host/runtime matrix must come from current release authority and live configuration; this repository documents commands but not a complete current host receipt.
3. OpenCode and Hermes live readback command/schema is not fully specified here; obtain it from their native manager/profile before acceptance. Do not substitute file existence, stale cache, or source tests.
4. No active-session reload can be claimed without a fresh session or explicit runtime reload evidence.
