---
name: real-use-testing
description: Mandatory final-gate procedure for proving a user-facing result on the real surface, with the interaction tool ladder (a11y tree -> browser MCPs -> CDP/Playwright -> XY clicks) and evidence rules.
---

# Real Use Testing

Use when a user-facing claim needs real-surface proof. This is the final gate
before "done"; test files never substitute for it. The journey executed is the
minimal path's shortest real canary, not an invented broader tour.

## Interaction tool ladder

Climb from the best available rung. Never claim an action is impossible before
trying the last one.

1. **Accessibility tree first, as far as possible.** Take an a11y snapshot
   (`take_snapshot`, accessibility tree, screen-reader structure). Target
   elements by role + accessible name + stable ref. This is the cheapest and
   most reliable targeting and usually suffices for the whole journey.
2. **Improved agent/browser MCPs when available and suitable:**
   - `browserclaw` — a11y snapshot + numbered ref targeting, agent-first;
   - `touchpoint` — accessibility tree across desktop apps, not just browsers;
   - `agent-browser` — high-level agent browser automation;
   - `playwright-mcp` / `chrome-devtools-mcp` — pages, network, console,
     screenshots, performance.
3. **CDP / Playwright scripting** when no MCP fits the surface or precise
   network/console evidence is required.
4. **Raw XY coordinate clicks + keyboard as the last resort.** Some surfaces
   respond only to real coordinates. ALWAYS try this rung before reporting a
   UI action as impossible, and verify every coordinate hit with a fresh
   snapshot or screenshot.

Ladder discipline: after any navigation or state change, re-snapshot before the
next action; a stale ref means re-snapshot, never guess; confirm each decisive
action by observed state, not by command success.

## Procedure

1. Read the accepted claim, proof strength, target surface, allowed
   actions/test data, and stop conditions.
2. Run the shortest actual user journey end-to-end using the ladder, without
   source-based shortcuts.
3. Capture evidence appropriate to the claim and surface: a decisive
   screenshot for browser/UI outcomes, the exact command and output for CLI
   outcomes.
4. Report `PASS`, `CHANGES_REQUIRED`, or `STOP_MISSING_REAL_SURFACE` with the
   exact journey, observed result, evidence path/reference, accepted claim, and
   smallest repair.

## Do not

- Do not declare a UI action impossible before trying ladder rung 4 (XY).
- Do not replace real-user evidence with unit tests or logs for a stronger
  claim.
- Do not make blindness, double testers, or video ceremonial defaults.
- Do not raise the accepted Definition of Done while testing it.
