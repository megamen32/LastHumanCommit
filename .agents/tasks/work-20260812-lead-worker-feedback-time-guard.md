# Lead/Worker feedback and business time guard

Status: complete

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

- Started at: 2026-08-12T10:21:52+03:00 (first committed task snapshot)
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

## Source implementation evidence

- Worker asks L at context-dependent decision boundaries with evidence,
  recommendation/default, parallel-safe work, and exact blocked action.
- Lead owns and promptly returns the decision; safe independent work continues
  through a proven non-blocking transport.
- Every declared coherent work cycle has an immutable minimum/maximum estimate.
- `src/common/tools/lhc_time_guard.py` persists the original estimate, catches
  each crossed wall-clock hour, emits original-maximum overrun and estimate-
  mutation events once, and writes state atomically.
- `src/common/protocols/TIME_CONTROL.md` defines hook/manual invocation and the
  hourly business report.
- Native scheduler/hook capabilities remain explicitly unproven or
  adapter-dependent; no automatic wake claim is made.

## Verification so far

- Red phase: 5 expected failures before tool/contracts existed.
- Focused green: 11 passed.
- Full semantic/time behavior: business contract 8 passed; time guard 3 passed.
- Full pytest: 20 passed.
- CLI canary: events `hourly, overrun`; crossed hours `1, 2`; original plan
  `30–90`; actual `100 active / 125 wall-clock`; overrun `10`.
- Plugin skill parity and package validation: PASS.
- `AGENTS.md` and `CLAUDE.md`: byte-identical.

## Current control

- Business delta: baseline installed; new tool and instruction contract pass
  source and CLI canaries.
- Estimate state: within initial 60 / 120 active-minute range.
- Next shortest action: final validation, source commit, exact Fleet preview,
  apply, verify, and physical runtime readback.

## Fleet completion evidence

- Committed version: `53e883d`
- Digest:
  `sha256:e1f532648c69e1c0854fcd497ae97beec35c9c0857cbfbc81fb5c7ec13c3c288`
- Fleet verify: `verified`, 54 files on `100`, `44`, `88`, and `mac`
- Active runtime readback: all four targets resolve `current` to
  `versions/53e883d` and contain Lead hourly and Worker decision-boundary text.
- Installed executable canary on every target: events `hourly, overrun`, crossed
  hours `[1, 2]`, overrun `10`, prompt starts `Меньше безопасности, больше
  бизнес-результата.`
- Rollback roots:
  `.local/share/last-human-commit/rollbacks/53e883d-lhc-rollout`
- Native parent-message and scheduler/lifecycle hook events were not attested;
  their manifest state remains `unproven` or `adapter-dependent`.
