# Lead/Worker feedback and business time guard

Status: todo

## Latest user request

Workers should ask Lead for context and decisions often, preferably through a
non-blocking transport while continuing safe independent work. Lead should
report every hour which real tasks are complete. Every meaningful cycle should
have a time estimate. Add an LHC tool or hook that emits the user's business-
first overrun diagnostic: planned versus actual time, whether it was controlled,
completed files, blocking gates/instructions, and why the route was not changed.
Install the previously completed business-first version before these changes.

## Outcome

- Previous source commit `e49eeeb` is installed and physically verified first.
- Worker asks Lead at decision boundaries with recommendation/default and keeps
  doing safe independent work when non-blocking messaging exists.
- Lead answers child questions promptly and owns business decisions.
- Every meaningful work cycle has a minimum/maximum estimate.
- Each active hour triggers a compact business-result report.
- Estimate overrun triggers the exact business-first diagnostic through an
  executable, persistent time-guard tool suitable for lifecycle hooks.
- The updated committed version is validated and installed to the same Fleet.

## Canary

Focused tests prove non-blocking Worker questions, hourly Lead reporting,
per-cycle estimates, and time-guard hourly/overrun event behavior. Fleet verify
and physical readback prove the updated runtime on `100/44/88/mac`.

## Scope

LHC roles/protocols/templates/adapters, a dependency-free common time-guard
tool, semantic tests, docs, generated skills only when directly affected, and
controlled Fleet rollout.

## Exclusions

No subagents. No unrelated runtime/service restart. No push. No foreign dirty
file changes. The reminder never authorizes bypassing essential safety,
secrets, user authority, or destructive-action boundaries.

## Time

- Started at: 2026-08-12T11:10:00+03:00
- Initial estimate: 60 / 120 active minutes
- 20-minute checkpoint: business delta and shortest next action
- Hourly report: required at every crossed wall-clock hour while active
- Overrun: tool event plus route diagnostic; estimate rewrite alone forbidden

## Current evidence

- `e49eeeb` previewed, applied, verified, and physically read from active
  `current/common/agents/Lead.md` on `100/44/88/mac`.
- Installed digest:
  `sha256:efa3dd9aedc11712c6fe6eccc31ae09e086039101791352fcb2afce49b7b90f4`.
