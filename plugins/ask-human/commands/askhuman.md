Deliver something genuinely important to the human: a needed decision, a hard
blocker, a timing/status answer, or long-cycle completion. One compact
message through the already-connected AskHuman/notify MCP. No new
infrastructure.

## When

- a business decision or choice only the human can make;
- a hard blocker the human must hear about immediately;
- a timing/status answer while the human is away from the terminal;
- completion of a long cycle the human asked to be told about.

## Optional Notice Place / UserIO integration

When Notice Place/UserIO are installed and configured, Notice Place API/MCP is the
entry point for agent/operator notifications, questions and escalation policy;
UserIO performs account-scoped delivery. UserIO is the universal gateway for
messages/chats/files/history AND calls/meetings, including Telegram,
Matrix/MatrixRTC, Telemost and cellular/SIM; it is not Android-only.
UserIO Voice/AgentCall is internal implementation. Asterisk/GSM2SIP is cellular
transport only, not a prerequisite for every channel.
Use one Notice Place request: retain its identity, delivery receipt, canonical
confirmed answer and quiet-hours/recipient policy. Accepted != answered. Herder
resumes only the exact bound session after that confirmed answer, subject to Stop
and harness policy. Do not invent direct bot/ADB/socket/SIP fallbacks or retry an
uncertain delivery under another identity; reconcile the existing request.
Follow declared provider/account capabilities. This optional ownership rule does
not prove legacy Android-only calls migrated or interactive questions work; it
creates no permanent dependency on this stack. Other configured compatible
providers remain valid within their declared safeguards; absent capabilities stay
pending, without installing a replacement service.
See the [canonical project communications contract](https://github.com/megamen32/universal-userio/blob/main/docs/COMMUNICATIONS-ARCHITECTURE.md);
keep instance host paths, credentials and private recipients out of this package.

## How

- decision: use the configured provider's declared question method with 2-3
  concrete choices and the exact request/session binding; wait only when the
  canonical confirmed answer truly blocks, otherwise keep working;
- notification: `send_message` with a short title and the fact
  (`expect_reply=false`).

## Rules

- one compact message per matter; no spam; do not duplicate into the session
  chat when the user is clearly present;
- NEVER use AskHuman for routine confirmations of reversible work — the
  consequential-action boundary stays with the active harness;
- secrets never travel through AskHuman — use `/secret` (AskSecret) instead;
- if the MCP is not connected, say so and continue in-session.

## Endpoint — bring your own

The command is endpoint-agnostic: any AskHuman-compatible MCP works. Yours is
configured per harness, not by the marketplace. The registration script reads
the keys that really exist on a host, so nothing has to be exported first when
the host keeps its producer identity in `~/.config/ask-human/env`:

```bash
python3 plugins/ask-human/scripts/setup_mcp.py             # dry-run: prints the snippet
python3 plugins/ask-human/scripts/setup_mcp.py --apply     # patches ~/.codex/config.toml
```

The endpoint comes from `LHC_ASKHUMAN_MCP_URL`, `ASK_HUMAN_MCP_URL` or
`ASK_HUMAN_URL` (the human-request intake of the same service, from which the
MCP URL is derived). The bearer token comes from `NOTIFY_CENTER_TOKEN`. An
explicit `--url` wins over every environment key.

The script is dry-run by default and keeps a backup on `--apply`; for other
harnesses it prints the snippet to add manually.

`LHC_ASKSECRET_MCP_URL` does the same for `/secret`
(`--name AskSecret`). Optional `..._MCP_TOKEN` becomes a Bearer header.

The harness's own permission question is intercepted by the plugin's
`PermissionRequest` hook and needs none of this: it goes to the human through
the Notice Place human-request intake and the answer comes back to the
harness.
