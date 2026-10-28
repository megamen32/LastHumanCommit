# Prepared fixture for post-runtime-fix delta acceptance

No inference was launched for this fixture. It is a new synthetic repository, separate from the earlier failed LHC run and its preserved fix.

- Fixture: `.agents/tasks/20261028-lhc-execution-audit/consumer-tests/native-luna-delta-fixture-20261028/`
- Git root is the fixture itself, on `main`; it has no local `AGENTS.md` and the README is neutral.
- Seed commit: `0e5baff` (`0e5baff78ec3999c70b288ca966a70902471c7d9`). `origin` is a bare Git repository at `../native-luna-delta-fixture-20261028-remote.git`; `main` was pushed locally and the working tree is clean.
- The fixture contains one intentionally faulty `qualifies_for_free_shipping` helper with an inclusive `$50.00` requirement. The meaningful standard-library regression checks `$49.99`, `$50.00`, and `$50.01`.
- Baseline RED was confirmed before any native repair: below/above tests pass, exact-threshold test fails. This preserves the intended defect for a fresh post-fix acceptance.
- The prior failed run remains recorded as `CHANGES_REQUIRED` in `native-luna-final-acceptance.md`; its fixture and `eligibility.py` fix were not changed.
- Root reported a verified trust mismatch between stored hook trust for old `hooks/hooks.json` and the installed plugin's `com.openai/hooks/hooks.json`. This tester made no global config/trust changes. A new native run waits for Root to confirm the runtime fix.

When authorized, use the normal user config so the installed marketplace registration and reviewed hook trust are present. Redirect stdout/stderr separately under `receipts/native-*`, close stdin with `< /dev/null`, keep the native JSON thread ID, use the exact selected `gpt-6-luna` route, and do not include a plan-creation hint in the repair prompt. Follow with the separately authorized status-only check after the repair result is known.
