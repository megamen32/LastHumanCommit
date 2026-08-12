# Lead/Worker feedback and business time guard

Status: in progress

## Latest user request

Workers should ask Lead for context and decisions often, preferably through a
non-blocking transport while continuing safe independent work. Lead should
report every hour which real tasks are complete. Every meaningful cycle should
have a time estimate. Add an LHC tool or hook that emits the user's business-
first overrun diagnostic: planned versus actual time, whether it was controlled,
completed files, blocking gates/instructions, and why the route was not changed.
Install the previously completed business-first version before these changes.

## Outcome and canary

Focused semantic and executable tests prove non-blocking Worker questions,
prompt Lead decisions, hourly business reporting, per-cycle estimates, and
stateful hourly/overrun time-guard events. Updated source is committed, rolled
out, verified, and physically read back on `100/44/88/mac`.

## Scope / exclusions

Instruction/tool/test/rollout scope only. No subagents, push, unrelated service
restart, foreign dirty edits, or weakening of essential safety/authority.

## Time control

- Started at: 2026-08-12T11:10:00+03:00
- Initial estimate: 60 / 120 active minutes
- Current business delta: previous version installed; new contract research done
- Next shortest action: add failing semantic/tool tests
- Hourly report: required at every crossed wall-clock hour while active

## Installed baseline evidence

- Version: `e49eeeb`
- Digest:
  `sha256:efa3dd9aedc11712c6fe6eccc31ae09e086039101791352fcb2afce49b7b90f4`
- Fleet verify: `verified` on `100`, `44`, `88`, and `mac`
- Physical readback: all four active Lead files contain business-first,
  gate-price, and wait/join markers.
