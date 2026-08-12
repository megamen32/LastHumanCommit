# ZCode subagent instructions template

Before every delegated task:

- Select the lowest sufficient model in profile frontmatter. Do not pass an
  explicit model key when the active guard forbids it, and do not inherit L's
  model merely because it is the parent default.
- Send one compact fresh-context assignment: role/mode, current business
  outcome, actual production-path evidence, allowed/excluded scope, one
  acceptance check, expected total range, stop conditions, and return format.
- The expected total range may exceed 20 minutes. Include a 20-minute reporting
  checkpoint for progress, business delta, blocker, route value, and shortest
  next action; it is not a cancellation deadline.
- Use `send_message` to continue or redirect the same Worker when available and
  its context remains useful.
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
