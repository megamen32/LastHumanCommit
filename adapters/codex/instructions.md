# Codex

A native profile embeds its complete role. Use the role file when native profile delivery is unavailable. `templates/subagent.md` describes the child assignment and continuation.

One V1/V2 wait window uses `deadline = monotonicNow() + 1800000 ms`. On a mailbox wake or `timed_out`, inspect the child and compute `remainingMs = deadline - monotonicNow()`; keep that deadline for the current window.

At expiry, use the child's checkpoint to decide whether to continue or redirect with `send_input`. Start another join window when the work is still useful. A wait expiry alone is not a reason to call `close_agent` or replace the Worker.

Report an actual missing model-selection, wait or resume capability rather than assuming a delegated result.
