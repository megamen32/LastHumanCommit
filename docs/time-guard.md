# LHC business time guard

`src/common/tools/lhc_time_guard.py` is a dependency-free lifecycle/checkpoint
tool. It does not run a daemon, mutate product state, cancel agents, or make a
release decision. A harness hook, scheduler wake, Lead checkpoint, or response
finalizer calls it for each active work cycle.

## Contract

- Every declared work cycle records one immutable minimum/maximum active-minute
  estimate before work starts.
- The tool persists the original estimate and reports attempts to replace it.
- Every crossed wall-clock hour emits one idempotent hourly business report.
- Crossing the original active-minute maximum emits one idempotent overrun
  diagnostic.
- The diagnostic asks for completed real tasks/files, business delta, planned
  versus actual time, control evidence, blocking gates/instructions, why the
  route was not changed, and the new shortest route.
- The reminder never authorizes weaker secret handling, missing user authority,
  destructive action, or removal of safety needed by the current claim.

## Example hook call

```bash
python3 .last-human-commit/common/tools/lhc_time_guard.py check \
  --state .agents/shared-session/time/my-cycle.json \
  --cycle-id my-cycle \
  --started-at 2026-08-12T10:00:00+03:00 \
  --minimum-minutes 30 \
  --maximum-minutes 90 \
  --active-minutes 65 \
  --business-delta 'public canary passes' \
  --completed-task 'deployed working vertical' \
  --completed-file src/service.py
```

The command prints JSON. When `events` is non-empty, the adapter/hook delivers
`prompt` to Lead and records it with the current task. Repeating the same check
does not repeat already delivered hour or overrun events.

## Hook timing

Call at session/cycle start, each material update, every response finalizer, and
every available scheduler wake. A harness that can schedule hourly wakeups uses
them; a harness without scheduling calls on the next observable update and
reports that exact capability limitation. The tool detects crossed hours, so a
late call still emits the missed report once.
