---
name: mini-improvement-loop
description: Fixed iteration loop for turning a reviewed defect list into a pushed, real-surface-proven result — parallel worker fixes, adversarial critique round, delta re-critique, converge at SHIP. Use when a review, audit, or incident produced concrete findings.
---

# Mini improvement loop

One named cycle for closing a concrete defect list (CRITICAL/HIGH/MEDIUM/LOW
findings from a review, audit, incident, or test round). Not for open-ended
design work — that is Full. Not for a single obvious bug — fix it directly.

## The loop

1. **Fix via workers in parallel.** Give each worker one bounded slice with a
   self-contained contract: absolute paths, the exact findings, invariants that
   must survive, and required test evidence (scenarios with expected exit codes
   and filesystem effects). Forbid git operations in the worker contract —
   parallel workers fight over one index; the Lead integrates.
2. **Lead integrates.** Review every diff personally, add only cross-cutting
   glue, commit small and correct (each logical fix its own commit), push.
3. **Critique round.** Two independent subagents in parallel: an adversarial
   Reviewer that must verify every claimed fix is real AND hunt for new bugs
   the fixes introduced, plus a Tester that re-derives scenarios in a sandbox
   without trusting prior test results or prior test drivers.
4. **Triage the findings.** CRITICAL/HIGH → fix now. MEDIUM → fix if each is
   under ~10 minutes. LOW → fix the one-liners in the same pass, consciously
   drop the rest. Small fixes are the Lead's direct work; only a slice needing
   its own investigation goes back to a worker.
5. **Re-critique only the delta.** One focused reviewer confirming
   finding→fix mapping and scanning the delta for regressions is enough.
   Repeat until a round returns no CRITICAL/HIGH. Default cap: three critique
   rounds; the third is a delta confirmation, not a full re-audit.
6. **Close on the real surface.** One real run or deployment of the changed
   thing with its output in the final report (exit code, state files created,
   canary log lines). The loop ends on that proof, not on "fixes committed".

## Convergence rules

- Every round's fixes are their own commits, so any round is revertible and the
  history reads as the loop it was.
- A finding that survives two fix attempts is a design decision, not a bug:
  stop fixing, present two compressed variants to the user (AskHuman when away).
- Sandbox discipline: workers and testers never touch real user-data paths —
  sed-copied scripts, env-overridden homes, temp trees. The Lead's single real
  run at the end is the only live fire.
- A reviewer or tester that could not execute (no shell, no write) must say so
  in the report; their verdict is then code-read only and cannot replace the
  real-surface step.
- Worker bugs happen too: when a fix's own test exposes a bug in the fix
  (tautological check, lost default branch), it is fixed in the same loop, not
  hidden — the loop converges on truth, not on green.

## Worker contract shape (paste-adaptable)

"Fix findings <N..> in <absolute paths>. Constraints: <invariants>, no git
commands. Required evidence: <scenario → expected exit/effects>, actually run.
Report: files changed, per-finding one-liner, real command outputs."
