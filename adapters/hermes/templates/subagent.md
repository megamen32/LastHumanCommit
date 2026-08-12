# Hermes subagent instructions template

Before every delegated goal:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Prefix the goal with `[LHC_ROLE=<role>]` and send one compact assignment:
  role/mode, current business outcome, actual production-path evidence,
  allowed/excluded scope, one acceptance check, expected total range, stop
  conditions, and compact return format.
- The expected total range may exceed 20 minutes. Include a 20-minute reporting
  checkpoint for progress, business delta, blocker, route value, and shortest
  next action; it is not a cancellation deadline.
- Resume/message the same Worker for implementation or a shorter route whenever
  Hermes exposes that transport and its context remains useful.
- Persist task/result detail only when handoff, recovery, reuse, or rediscovery
  cost justifies it.
- Use optional independent roles only for a concrete risk whose expected value
  exceeds delay.
- Ask L at decision boundaries through a proven non-blocking parent transport,
  include recommendation/default and parallel-safe work, and continue safe work
  while waiting. Otherwise return the question at the next checkpoint.
- Run `common/tools/lhc_time_guard.py` at observable lifecycle/checkpoint events
  and deliver new hourly/overrun prompts without simulating scheduler wakes.
- Every status/question reports exact known start, original min/max, wall-clock,
  and active time with its measurement source. If continuous active time is
  unavailable, say `не контролировал`; never infer it from wall-clock or mtime.
- After compaction, read the bounded `current-handoff.md`, state its compaction
  count, and checkpoint to L if the count rose without business delta.

Use the harness wait/join tool when the child result is required. Do not send the
final answer while a required child result remains non-terminal. A timeout is
observational: inspect status, request the checkpoint, continue/redirect the same
Worker, and join again. Cancellation or replacement is exceptional.
