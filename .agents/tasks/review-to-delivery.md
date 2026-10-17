# Review must lead to delivery

User problem: useful PostgreSQL concurrency testing was followed by repeated corrections of review receipts, hashes and filenames while the fix remained undeployed. Preserve testing, resource/approval gates, original scope, worktree integration, mandatory periodic reviews and milestone Zero Knowledge feedback.

Observable result: with passed relevant tests and review of the unchanged implementation, an agent repairs a metadata-only receipt error locally when necessary and proceeds to the already-authorized delivery/consumer check. Actual code/configuration/dependency changes and unexecuted tests stay visible and require relevant verification. No new generic receipt service, no production data changes and no receipt-review subagents.

Three passes: (1) distinguish metadata from reviewed implementation and move to delivery; (2) ideal native SCM/CI captures metadata so the model never types hashes; (3) useful 80%: reuse existing Git/CI outputs and native reviewer response, fix LHC routing at entry, role handoff and hourly review, add scenario regressions. Do not build a new evidence infrastructure.

Source: two user screenshots 2026-10-17. Scope of this change: LastHumanCommit only. No AFC/TGC work is resumed or redeployed by this task.

Independent review found one scope-expansion risk: unconditional deployment for source-only work. Added a failing regression, then limited delivery to the original accepted scope. Other gates remain unchanged.
