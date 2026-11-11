# Ask the user

Use the connected AskHuman/Notice surface for a decision the user needs to make or a material notification. An ordinary completion can use `send_message` with `expect_reply=false`. Routine decisions already covered by the task do not need another question.

## Notice Place and UserIO

When configured, Notice Place owns question/notification policy and UserIO owns account-scoped communications: messages, files, calls and meetings. Use their declared capabilities. UserIO Voice/AgentCall is an internal implementation; Asterisk/GSM2SIP concerns cellular transport.

For a durable question tied to the current session:

1. `lhc_outcome.py ... question --message '<question>'` reserves the question identity. Repeated calls inspect that pending request.
2. The existing Herder `human_request_create(kind=user, harness, sessionId, cwd, marker, message, choices?)` binds it to the exact native target. This creates the binding, not the delivered message.
3. Send the binding through `noticeplace_ask_human` with `request_id`, `harness`, `session_id`, `cwd`, `message`. The documented HTTP route is POST `/v1/human-requests`, using `Idempotency-Key: human-request:<request_id>`, `ask_human.request.v1` and the configured recipient/project. HTTP uses `native_target`. Herder choices map `choiceId,label` to `value,label`; labels are limited to 80 characters by that API.
4. Read the actual delivery receipt. For an uncertain attempt, inspect the same request before retrying.
5. Read `noticeplace_question_result` or GET `/v1/human-requests/{id}/result`. The confirmed result resumes the exact bound session through its existing stop-aware continuation.

Keep the request identity, recipient policy and current user stop. A queued request is not a delivery and a delivery is not an answer. A missing configured recipient or capability is an explicit blocker for that question; continue independent work. Credentials remain in the configured protected store.

The optional outcome importer recognizes direct native curl at `ASK_HUMAN_URL` or the configured `LHC_ASKHUMAN_MCP_URL` origin and the exact result GET. Other clients can use the native MCP path. This is an importer limitation, not a requirement to send the same question again.

Project details: https://github.com/megamen32/universal-userio/blob/main/docs/COMMUNICATIONS-ARCHITECTURE.md

## Configure an endpoint

```bash
export LHC_ASKHUMAN_MCP_URL="https://your-notify.example/mcp"
python3 plugins/ask-human/scripts/setup_mcp.py --apply
```

`LHC_ASKSECRET_MCP_URL` selects the secret surface. Optional protected `..._MCP_TOKEN` supplies the Bearer header. Setup previews by default and backs up changes on apply.
