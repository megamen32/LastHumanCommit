---
name: real-use-testing
description: Verify the requested behavior through the actual installed app, browser, device, API or CLI.
---

# Real-use testing

Run the scenario that demonstrates the user's requested result through the actual consumer. Read `.agents/TEST_ACCESS.md` when the scenario needs accounts or fixtures. Access preparation is described in `common/protocols/REVIEW_TO_DELIVERY.md`.

Choose an interaction tool that fits the surface: accessibility references or a browser MCP for ordinary UI work, CDP/Playwright for precise scripting, coordinates when the UI requires them. Refresh the relevant view after it changes. A failing tool may justify another route; it does not require trying every tool in order.

Observe the decisive action and its result. Save a screenshot for a UI issue or the actual command and output for a CLI result. On ambiguous state, capture the evidence needed to distinguish the likely causes before retrying.

Report the goal, actions, result and any remaining failure. A fresh Tester is useful when independent usability or coverage is part of the claim; a bounded direct client check may be enough for a simple repair. Use `PASS`, `CHANGES_REQUIRED` or `STOP_MISSING_REAL_SURFACE` when the calling workflow needs a status.
