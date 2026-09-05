# OpenCode subagent instructions template

Use the Lead-assigned canonical checkout when one is supplied. Allocation comes
only from `common/tools/lhc_worktree.py`: branch `lhc/<task-slug>`, path
`<primary-project-root>/.worktrees/<task-slug>`, immutable base and one owner.
Pass that existing working directory to the harness; disable implicit worktree
creation and never substitute a harness-private directory. If the API cannot
use an existing directory, report that capability limit to Lead before dispatch.
Lead owns main integration, final verification and task-owned cleanup.

Carry the latest objective, constraints and applicable verified project/LHC
learning in the compact assignment. Retrieve relevant lessons before repeating
research; preserve both product repair/retest and method improvement/reuse loops.

Use the portable `model-routing` and `decompose-and-dispatch` skills. Include
dependencies, owned resources, frozen interfaces, selected model and suitability
reason, acceptance and integration join. Resolve API identifiers from actual
harness capabilities; never send example aliases blindly. Record actual model
selection when available and disclose unsupported selection or concurrency.
Use fresh independent sessions for the initial Overseer audit and Full Tester
after coherent technical review. Adviser/council are optional reasoning methods;
Critic is a compatibility alias, not an extra required gate. Resume useful
Workers but do not reuse the implementation session as its independent Tester.

Before every delegated task:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Send one compact assignment: role/mode, current business outcome, actual
  production-path evidence, allowed/excluded scope, one acceptance check,
  expected total range, stop conditions, and compact return format.
- The expected total range may exceed 20 minutes. Include a 20-minute reporting
  checkpoint for progress, business delta, blocker, route value, and shortest
  next action; it is not a cancellation deadline.
- Resume/message the same Worker for implementation or a shorter route whenever
  supported and its context remains useful.
- Persist task/result detail only when handoff, recovery, reuse, or rediscovery
  cost justifies it.
- Beyond the initial Overseer and Full review/Tester gates, use additional
  independent roles only for a concrete risk whose expected value exceeds delay.
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
