# Same-model Superpowers comparison

Status: todo
Harness: unknown (legacy; not recorded)
PID: unknown (legacy; not recorded)
Agent session: unknown (legacy; not recorded)
PID status: unknown (legacy)
Last PID signal (UTC+3): unknown (legacy; not recorded)
Last task-file transition (UTC+3): unknown (legacy; filename was todo-)
Started at (UTC+3): unknown (legacy; cannot infer from mtime)
Lifecycle provenance: legacy-missing; audited 2026-08-10
Last task-file mtime observed (UTC+3): 2026-08-09 10:30:27 +0300 (last write observed, not start)
Symptom: No valid published Superpowers result exists for the same five scenarios on GPT-5.6 Luna and GPT-5.4 Mini.
Evidence: Existing public Codex baseline is a different gpt-5.5-era matrix; the first mapped Superpowers canary reached deterministic checks but Gauntlet returned `investigate` with no verdict because the new comparison container lacked a usable grader route.
Smallest next step: provide a working grader credential/route, then run the mapped five-scenario Superpowers campaign on Luna and 5.4 Mini and compare only matched cells with L0.
Excluded: do not count setup/indeterminate canaries as Superpowers quality results; do not rerun or publish until transcript redaction and one combined campaign archive are ready.
