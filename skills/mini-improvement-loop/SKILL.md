---
name: mini-improvement-loop
description: Fixed iteration loop for turning a reviewed defect list into a pushed, real-surface-proven result — parallel worker fixes, adversarial critique round, delta re-critique, converge at SHIP. Use when a review, audit, or incident produced concrete findings AND every finding is a bounded fix inside existing code. If the scope also creates a project, a service, a repository or an architecture decision, that is Full, not this loop.
---

# Mini improvement loop

One named cycle for closing a concrete defect list (CRITICAL/HIGH/MEDIUM/LOW
findings from a review, audit, incident, or test round). Not for open-ended
design work — that is Full. Not for a single obvious bug — fix it directly.

## Scope check before the loop

This loop is only for a **bounded fix list inside existing code**. Before the first
assignment, check the accepted scope: if it also creates a project, a service, a
repository, an architecture or a design decision, stop here. That is Full — read the
package `AGENTS.md` for the Large fullcycle shape: bounded independent research
Workers → one working→ideal→YAGNI plan → an optional quota-aware frontier council →
bounded dispatch. Do not run a design decision through a fix loop: the fix loop has
no phase for choosing the design, and the decision gets made blind.

## The loop

1. **Assign fixes.** Give each Worker one bounded slice with a self-contained
   contract: absolute paths, findings, invariants, and evidence needed for the
   affected claim. Assign every fix to an allowed model family and verify the
   exact live catalog ID. A Worker owns its leaf through result and does not hire.
2. **Coordinate integration.** The Lead resolves path/resource ownership and
   dependencies, collects results, and assigns any cross-cutting glue or delivery
   operation to an allowed Worker. The Lead does not inspect/edit code, run checks,
   commit, push or deploy.
3. **Independent review/testing.** Assign a Reviewer or Tester from an allowed
   model family when a concrete risk or the accepted claim warrants it. It checks
   the actual changed behavior and real consumer path; LHC review metadata is not
   a release gate.
4. **Triage the findings.** CRITICAL/HIGH → fix now. MEDIUM → fix if each is
   under ~10 minutes. LOW → fix the one-liners in the same pass, consciously
   drop the rest. Assign every fix to an allowed Worker; use parallel Workers only for independent
   slices. An assigned Worker does not recursively hire.
5. **Recheck affected delta.** Re-run only the checks needed to confirm fixes
   and resolve concrete findings. Do not repeat a full audit to close bookkeeping.
6. **Close on the real surface.** Assign an allowed Worker to perform any required
   real run/deployment and report observable evidence. The loop ends on the
   accepted claim, not on a receipt or commit.

## Convergence rules

- Every round's fixes are their own commits, so any round is revertible and the
  history reads as the loop it was.
- A finding that survives two fix attempts is a design decision, not a bug:
  stop fixing, ask the Adviser for one choice, take it and record the other
  variant for the owner; do not wait for an answer.
- Sandbox discipline: workers and testers never touch real user-data paths —
  sed-copied scripts, env-overridden homes, temp trees. Only an explicitly scoped Worker performs an authorized live run.
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
