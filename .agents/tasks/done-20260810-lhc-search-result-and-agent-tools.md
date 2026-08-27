# LHC separate search journal, final result, and `.at/` tools

Status: complete
Original user request: Разделить исследование на два файла: отдельный журнал «как я искал», который по умолчанию игнорируется и пригоден для массового анализа/сокращения повторяющихся путей, и отдельный переписываемый финальный результат. Всё, что исследовалось больше 10 минут, нельзя игнорировать и обязательно нужно коммитить. Одноразовые скрипты строго запретить в `/tmp` и `.tmpbin/`; завести `.at/` для Agent Tools и писать после инструкций в AGENTS.md краткое «почему».
Objective: Зафиксировать file-first контракт поиска, финального результата, обязательной фиксации долгого исследования и каталога `.at/`.
Business canary: После смерти harness Lead отдельно открывает search journal и актуальный result; исследование >10 минут попадает в обязательный commit; временный скрипт находится в `.at/` и может быть переиспользован.
Confirmed scope: shared-session abstraction, Worker research protocol, common code/agent rules, routers, `.at/README.md`, validators.
Explicit exclusions: no external MCP/hook installation, no deployment/restart, no unrelated runtime cleanup.
Acceptance proof: text validator passes and all rules are explicit in source instructions.
Cycle: short
Harness: codex
PID: current Lead orchestration process
Agent session: current task
PID status: alive
Last PID signal (UTC+3): 2026-08-10
Last task-file transition (UTC+3): work
Started at (UTC+3): 2026-08-10
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-10
Current stage: implementation
Current owner: L
Initial estimate (minimum / maximum active minutes): 10 / 25
Estimate revisions: none
Stop when: separate files, >10-minute commit gate, `.at/` rule, reasons-after-instructions, and checks are present.
Abandon/rethink when: enforcing the rule requires an unavailable git/harness hook; document the capability gap.
Forbidden without explicit user authorization: external hook/MCP install, deployment, restart, unrelated security/validation work.

## Result

Summary: Split research into an append-only `search.md` journal and a
rewritable `result.md`; made results over 10 active minutes non-ignorable and
commit-required; prohibited one-off scripts outside `.at/` and documented the
reason after the instruction.
Business canary evidence: dead harness recovery can read the final result
without loading the whole chat, while the search journal remains available for
bulk deduplication.
Tests/checks: `python3 tests/validate.py`; `tests/test_task_states.sh`; `git diff --check`.
Unresolved: runtime enforcement of the >10-minute commit gate still needs a
future harness/MCP implementation.
