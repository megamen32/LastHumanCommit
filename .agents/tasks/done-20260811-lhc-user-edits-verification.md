# Worker verification: user decisions present in LHC core

Status: complete
Original user request: Запусти Worker, который проверит, внесены ли все мои правки в LHC.
Objective: Независимо сопоставить текущую core-спецификацию LHC с пользовательскими решениями и отметить `PRESENT`, `MISSING`, `CONTRADICTED` или `AMBIGUOUS`.
Business canary: Lead получает точный read-only отчёт с путями/строками и понимает, какие пользовательские правила реально действуют.
Confirmed scope: `/home/roomhacker/agents-projects/LastHumanCommit/AGENTS.md`, `CLAUDE.md`, `README.md`, `ROADMAP.md`, `docs/`, `src/common/`, `templates/`, `adapters/` excluding plugin source, historical task cards, generated/cache files.
Explicit exclusions: no specification edits, no plugin audit, no deployment/restart, no runtime changes, no task migration.
Acceptance proof: every checklist item below has a verdict and exact evidence; contradictions are not silently resolved.
Cycle: short
Harness: codex
PID: parent orchestration process; Worker PID/session to append
Agent session: Worker will append if harness exposes it
PID status: alive
Last PID signal (UTC+3): 2026-08-11
Last task-file transition (UTC+3): work
Started at (UTC+3): 2026-08-11
Lifecycle provenance: recorded at creation
Last task-file mtime observed (UTC+3): 2026-08-11
Current stage: research
Current owner: L
Initial estimate (minimum / maximum active minutes): 10 / 20
Estimate revisions: none
Stop when: checklist is fully classified with evidence.
Abandon/rethink when: a claim depends on excluded plugin/runtime behavior; mark that boundary instead.
Forbidden without explicit user authorization: any source/spec change, plugin/runtime work, deployment, restart.

## Verification checklist

1. One `.agents/` root; no instructed top-level `.lhc`/`.at`; Agent Tools in `.agents/at/`.
2. No separate handoff file; handoff is inside task file; task file contains exact tracked `result-*` path.
3. `search-*` and `result-*` are separate named files in separate directories; search tree is Git-ignored; result is tracked.
4. Research: first 3 minutes orientation; after that persistent search/result files; after 10 minutes result cannot be ignored and requires commit; Worker may write metadata/files but not project code.
5. Lifecycle: `todo-*` business request, `work-*` implementation, `done-*` outcome; transitions are `cp + commit`, old snapshots remain, latest committed snapshot is current.
6. Dead Worker can be resumed by the next Worker from committed `work-*`; corresponding regression exists in Roadmap.
7. Adviser is pre-implementation and optional only for a real method branch; history fork is allowed.
8. After three plans, Critic first gives common/long-term criticism; Adviser receives it, recommends to L, and rewrites plans with business goal, long-term consequences, and YAGNI ladder.
9. Tester runs at final only, with two independent blind real-user passes and durable business-result evidence such as screenshots/video.
10. Overseer continues persistent context, reads durable files, has binding veto against unsolicited security/validation/hardening, and 30-minute hook/cap-off behavior is represented.
11. Human-request notification uses the attested NoticePlace capability rather than a plain transcript question.

## Worker report — append-only

Worker verdicts (read-only core audit, 2026-08-11):

1. PRESENT — One `.agents/` state root and Agent Tools location are normative:
   `AGENTS.md:65-69` and `CLAUDE.md:65-69` require `.agents/at/` and forbid
   separate `.at/`/`.lhc/`. The checkout probe found `.agents/at/` and no
   top-level `.at`/`.lhc` (`find . -maxdepth 2 ...`); this is a current-tree
   observation, not a claim about generated runtime state.

2. AMBIGUOUS / internally contradicted — The no-separate-handoff rule is
   PRESENT at `AGENTS.md:45-48`, `README.md:30-33`, and
   `src/common/templates/.agents/tasks/task_template.md:113-118`. However the
   same core specification requires a separate tracked result file at
   `src/common/agents/Worker.md:34-41`, `src/common/protocols/WORKER_RESEARCH.md:5-15`,
   and `docs/shared-session-abstraction.md:31-37,91-113`. The assigned task
   itself contains no exact tracked `result-*` path, so the checklist's full
   requirement is not proven.

3. PRESENT — Separate named search/result files and ignored search tree are
   specified at `src/common/protocols/WORKER_RESEARCH.md:5-15` and
   `docs/shared-session-abstraction.md:91-113`; `.gitignore:7` ignores the
   search tree. Adapter templates repeat the tracked result path, e.g.
   `adapters/codex/templates/subagent.md:17-20`. The current checkout has no
   `.agents/shared-session/` tree, so this is specification evidence only.

4. PRESENT — Orientation threshold, persistent files, mandatory non-ignored
   result after 10 minutes, and commit requirement are explicit at
   `src/common/protocols/WORKER_RESEARCH.md:5-15` and
   `docs/shared-session-abstraction.md:93-113`.

5. PRESENT — Lifecycle names and copy/commit/preserve semantics are explicit at
   `AGENTS.md:40-44`, `README.md:30-33`, and
   `src/common/templates/.agents/tasks/task_template.md:1-6`. The task record
   also models lifecycle snapshots at `task_template.md:3-6`.

6. MISSING — `ROADMAP.md:85-89` leaves the dead-Worker resume regression
   unchecked. The general lifecycle contract exists, but the requested proof
   that the next Worker resumes from committed `work-*` without redoing research
   is not implemented/evidenced.

7. AMBIGUOUS — Adviser is explicitly optional and pre-implementation only for a
   real architecture/scale/long-term choice at `src/common/agents/Adviser.md:3-20`.
   The three-plan comparison contract is explicit there, but no core rule was
   found that history forks are allowed; that sub-claim is therefore unproven.

8. CONTRADICTED — The current plan order says Adviser may compare plans and L
   waits for selection (`src/common/agents/Lead.md:144-153`), while Critic is
   invoked only after fresh Tester evidence (`src/common/agents/Lead.md:168-173`;
   `templates/FULL_CYCLE.md:111-119`). No rule was found requiring Critic to
   first give common/long-term criticism after the three plans, then Adviser to
   rewrite plans with business goal/consequences/YAGNI ladder.

9. MISSING — Tester is final, fresh, real-user, and `only-new` for Full at
   `src/common/agents/Tester.md:3-18,22-45`, but the core spec does not require
   two independent blind passes or durable screenshot/video business-result
   evidence. It asks for a useful screenshot/snapshot or command reference
   (`Tester.md:36-38`) and defines one Tester gate.

10. AMBIGUOUS — Persistent Overseer context, durable files, binding verdict, and
    fallback when MCP/hook/transport is unavailable are specified at
    `docs/shared-session-abstraction.md:128-156`; lifecycle `response_stop`
    human-question hook and explicit capability failure are at `:64-89`.
    The 30-minute trigger is explicitly non-cooldown at `AGENTS.md:96-101`,
    `src/common/agents/Overseer.md:29-37`, and
    `src/common/agents/Lead.md:126-132`. However, no explicit binding-veto
    wording for unsolicited security/validation/hardening was found; only the
    broader scope/audit constraints are present.

11. MISSING — The core names a generic registered human-request capability and
    fail-closed behavior at `docs/shared-session-abstraction.md:76-89` and
    `docs/human-request-capabilities.md:18-27`, but does not attest or name the
    NoticePlace capability. Therefore the requested NoticePlace-specific rule is
    not present in the included core specification.

Scope/limitations: no source/spec/plugin/runtime/deployment changes were made;
no live runtime or user-facing canary was run. The required Worker research
artifact paths under `.agents/shared-session/` are themselves absent, but
creating them would exceed this task's confirmed read-only core-audit scope.

## Result

Summary: Independent Worker verification completed with PRESENT, AMBIGUOUS,
MISSING, and CONTRADICTED verdicts across all eleven checklist items.
Tests/checks: read-only core audit; no specification changes.
