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

Заполняется после scoped commit/push и native Codex plugin manager readback.

Consumer/browser acceptance выполняет отдельный Tester; этот release leaf её
не запускает и не засчитывает.
