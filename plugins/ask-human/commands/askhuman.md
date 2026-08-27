Deliver something genuinely important to the human: a needed decision, a hard
blocker, a timing/status answer, or long-cycle completion. One compact
message through the already-connected AskHuman/notify MCP (Telegram). No new
infrastructure.

## When

- a business decision or choice only the human can make;
- a hard blocker the human must hear about immediately;
- a timing/status answer while the human is away from the terminal;
- completion of a long cycle the human asked to be told about.

## How

- decision: `ask_human` with 2-3 concrete `choices`; wait only when the answer
  truly blocks, otherwise keep working;
- notification: `send_message` with a short title and the fact
  (`expect_reply=false`).

## Rules

- one compact message per matter; no spam; do not duplicate into the session
  chat when the user is clearly present;
- NEVER use AskHuman for routine confirmations of reversible work — the
  consequential-action boundary stays with the active harness;
- secrets never travel through AskHuman — use `/secret` (AskSecret) instead;
- if the MCP is not connected, say so and continue in-session.
