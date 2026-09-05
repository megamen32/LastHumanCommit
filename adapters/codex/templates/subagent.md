# Codex subagent instructions template

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

Before every `spawn_agent` or resumed Worker call:

- Select the lowest sufficient working model class; do not inherit L's model by
  default.
- Start a new child with `fork_context: false` and pass only the compact context
  it needs: role/mode, current business outcome, actual production-path evidence,
  allowed/excluded scope, one acceptance check, expected total range, stop
  conditions, and return format.
- The expected total range may exceed 20 minutes. Include a 20-minute reporting
  checkpoint for progress, business delta, blocker, route value, and shortest
  next action. This is not a cancellation deadline.
- Prefer `send_input`/resume for course correction and continuity. Do not replace
  the same Worker merely because a checkpoint or wait window elapsed.
- Persist detailed evidence in the assigned task/result path only when handoff,
  recovery, reuse, or rediscovery cost justifies it.
- Beyond the initial Overseer and Full review/Tester gates, use additional
  independent roles only for a concrete risk that makes them worth their cost.
- At a decision boundary, ask L through a proven non-blocking parent transport
  with evidence, recommendation/default, parallel-safe work, and blocked action.
  Continue safe independent work while waiting; otherwise return the question at
  the next checkpoint.
- Run `common/tools/lhc_time_guard.py` at observable lifecycle/checkpoint events;
  deliver new hourly/overrun prompts to L and never claim an unavailable wake.
- Every status/question reports exact known start, original min/max, wall-clock,
  and active time with its measurement source. If continuous active time is
  unavailable, say `не контролировал`; never infer it from wall-clock or mtime.
- After compaction, read the bounded `current-handoff.md`, state its compaction
  count, and checkpoint to L if the count rose without business delta.

Use the harness wait/join tool after dispatch whenever the result is required.
Do not send the final answer while a required child result remains non-terminal.

One Codex V1/V2 wait window uses the absolute monotonic deadline
`deadline = monotonicNow() + 1800000 ms`. On each target-specific wait, mailbox
wake, or `timed_out`, re-check authoritative child status and compute
`remainingMs = deadline - monotonicNow()`; wait only with `remainingMs` and never
reset that window. At `remainingMs <= 0`, preserve the child and return
`join-window-expired` for a control decision. Request/inspect the checkpoint,
redirect through `send_input` when useful, and start another join window when
continuation remains least-cost. Never call `close_agent` or create a replacement
solely because 20 minutes, a timeout, or one 30-minute window elapsed.

If the active Codex surface cannot create, wait for, or resume the needed child,
report that exact capability boundary instead of claiming a delegated result.
