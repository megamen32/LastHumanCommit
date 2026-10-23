# L13 — релиз LHC 1.5.39

## Изменение и проверка пакета

- Каноническая routing policy и generated Codex/package projections прошли
  независимую проверку; добавлен regression test с проверкой native Codex parity.
- Версии всех package, native, Hermes и marketplace manifests синхронизированы
  на `1.5.39`; changelog и README обновлены.
- `python3 plugins/last-human-commit/scripts/sync_skills.py --check` — PASS,
  `parity: PASS (25 skills)`.
- `pytest -q tests/test_business_first_contract.py
  tests/test_model_routing_delegation_policy.py` — PASS, 35 passed.
- `python3 plugins/last-human-commit/scripts/validate.py` — PASS,
  25 skills, canonical and parity PASS.
- `python3 tests/validate.py` — 1176 passed, 5 failed. Все пять падений —
  `tests/test_lhc_merged_page.py`; тесты требуют отсутствующий файл
  `/Users/user/Documents/ServerAdministartion/.tmp/airlock-audit/audit-data.json`.
  Это внешний Mac-путь, вне текущего release scope. Ошибки не относятся к L13.
- `git diff --check` — PASS.

## Публикация и установленная запись

Scoped commit: `3eb3142c3c648e869e6c9273c313dc0db07184a0` на `main`.
`git push origin main` завершился успешно; `git ls-remote origin
refs/heads/main` подтвердил тот же SHA.

Native Codex plugin manager обновил marketplace командой
`codex plugin marketplace upgrade megamen32-plugins --json` (ошибок нет).
Свежий readback `codex plugin list --available --marketplace
megamen32-plugins --json` подтвердил:

| pluginId | version | installed | enabled | source root |
|---|---:|---:|---:|---|
| `last-human-commit@megamen32-plugins` | `1.5.39` | true | true | `/home/roomhacker/.codex/.tmp/marketplaces/megamen32-plugins/plugins/last-human-commit/native/codex` |
| `last-human-commit@fleet-lhc` | `1.5.36` | true | false | `/home/roomhacker/.local/share/agent-harness-fleet/plugin-rollout/marketplaces/codex-fleet-lhc/versions/06ae0e1405d333fb9408b1838c31327bfa2cc4058122f4b15867b0d40e65958a/last-human-commit/native/codex` |

Установленный cache root: `/home/roomhacker/.codex/plugins/cache/megamen32-plugins/last-human-commit/1.5.39`.
SHA-256 installed files:

- `.codex-plugin/plugin.json` — `ade18bab438f8400100ceca1914d8be5c845a49b98cdda26c331ec94dff6f45a`.
- `skills/model-routing/SKILL.md` — `5b637e195f090d616ed31377d66dfb000d7b2968c479b6f0523c37224d42473e`.
- `common/agents/Worker.md` — `e83e9d41a9d157948aa15df62d80728db17ba2585b888c4fb20c4a137f43ccc6`.

Откат: в Codex открыть `/plugins` → Installed, отключить точную запись
`last-human-commit@megamen32-plugins` версии `1.5.39` и включить сохранённую
запись `last-human-commit@fleet-lhc` версии `1.5.36`; подтвердить обе записи
свежим `codex plugin list --json`. Удаление записей или ручная правка cache не
требуются.

Consumer/browser acceptance выполняет отдельный Tester; этот release leaf её
не запускает и не засчитывает.
