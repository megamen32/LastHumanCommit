Harness: codex
PID: unknown (not captured in this work card)
Agent session: unknown (not captured in this work card)
PID status: alive
Last PID signal (UTC+3): 2026-08-11
Last task-file transition (UTC+3): work
Current stage: implementation
Current owner: Lead
Started at (UTC+3): 2026-08-11
Lifecycle provenance: recorded at work transition; PID/session were not captured
Last task-file mtime observed (UTC+3): 2026-08-11

# LHC worker findings — apply

Status: in progress
Lifecycle snapshot: work
Supersedes: `.agents/tasks/done-20260811-lhc-user-edits-verification.md`
Snapshot commit: pending
Start time: 2026-08-11 Europe/Moscow
Initial active-minute estimate: 45–75
Estimate revisions: none
Result file: `.agents/shared-session/results/lhc-apply-worker-findings/result-lhc-worker-findings.md`

## Original request

Сделай исправления по проверке Worker: внеси мои решения в спецификацию LHC,
добавь тест восстановления следующего Worker после смерти предыдущего и устрани
выявленные несоответствия между Adviser, Critic, Overseer и Tester.

## Objective

Make the core LHC specification, templates, task records, and regression checks
agree with the user's latest decisions, without changing plugin implementations.

## Business canary

An agent can start from a committed `work-*` snapshot after a Worker dies,
resume from its recorded evidence, and the documented Full workflow produces a
business-result proof package rather than stopping at process checks.

## Confirmed scope

- Core Markdown/YAML specifications, templates, task-state validation, and tests.
- Single `.agents` state root; task-local handoff; named search/result artifacts.
- Adviser/Critic ordering, Overseer veto/timer fallback, NoticePlace human request,
  and two final blind Testers.

## Explicit exclusions

- No plugin installation or plugin-source audit.
- No unrelated runtime changes, deployment, release, or destructive cleanup.
- No unsolicited security, strict-validation, or hardening work.

## Plan

1. Reconcile shared-session/task artifact wording.
2. Reconcile Adviser, Critic, Lead, Tester, Overseer, and Full-cycle ordering.
3. Add NoticePlace and hook fallback rules.
4. Add and run the Worker-resume lifecycle regression.
5. Run focused validation and record evidence/result.

## Evidence / result

Checkpoint evidence is complete; the final state is preserved in the copied
`done-*` snapshot. The exact result is maintained at
`.agents/shared-session/results/lhc-apply-worker-findings/result-lhc-worker-findings.md`.
