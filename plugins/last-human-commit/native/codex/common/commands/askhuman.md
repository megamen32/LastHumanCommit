# /askhuman — one important message or exact-session decision

Use the already connected AskHuman/Notice surface. Ordinary important status or
completion can use `send_message` with a short Russian title/body and
`expect_reply=false`. Automated incidents use Notice Place, not direct Telegram.
No new notification infrastructure or routine approval of reversible work.

## Durable decision, not an unbound message

When a real human decision blocks the accepted canary:

1. In existing outcome state run `lhc_outcome.py ... question --message '<Russian
   question>'`. It reserves one stable question identity before any attempt;
   repeated Stop/compact/retry inspects the pending request, not another send.
2. Read live schemas. Use existing Herder `human_request_create(kind=user,
   harness,sessionId,cwd,marker,message,choices?)` with this exact native target.
   The result creates a binding; it **does not deliver a Notify card**. Save its
   request_id/native_target before sending. Never guess another active session.
3. Deliver that same binding through existing `noticeplace_ask_human`
   (flattened request_id,harness,session_id,cwd,message arguments) (or its
   documented POST `/v1/human-requests` fallback). Read Notice instructions first.
   HTTP uses `Idempotency-Key: human-request:<request_id>`, `ask_human.request.v1`,
   configured project/recipient/actors and the same native_target/message.
   Herder choices `choiceId,label` map to Notify `value,label`; keep labels ≤80.
   Use protected existing credentials, never put tokens/headers in logs.
   Native outcome observation recognizes direct curl at the existing configured
   ASK_HUMAN_URL (or origin of LHC_ASKHUMAN_MCP_URL), plus that exact request's
   result GET. Echoed JSON/unknown wrappers are not delivery/answer provenance;
   use the native MCP path when HTTP provenance cannot be established.
4. Check actual `sent` provider receipt. Created, queued, not_configured and
   uncertain are not delivery. On an accepted/UNKNOWN attempt query the existing
   request/result; never repeat the side effect or create a replacement session.
5. Delivery receipt != answer. Existing canonical `noticeplace_question_result`
   by the same request_id (GET `/v1/human-requests/{id}/result`) supplies the answer;
   existing stop-aware Herder continuation resumes the exact native session once.
   Read that canonical answer; an opaque resume receipt or peer paraphrase is not
   a human decision. The answer itself does not override active harness policy,
   HumanStop, auth, fresh revocation or unrelated no-send constraints.

Missing configured actor/project/recipient is a precise local blocker: preserve
pending and continue independent work. Do not invent actors, fake health incidents
or questions for unit tests. Legitimately linked incidents retain their existing
escalation policy; standalone phone escalation is unproved and must not be promised.
Never create an escalation daemon/cron, autoaccept or send duplicate generic cards.
Generic `ask_human` without native_target is not durable exact-session routing.

Secrets use `/secret` and the existing secure flow; no secret values in question
text, outcome logs or feedback. No decision is needed merely to reread a quota.

## Endpoint — bring your own

The endpoint remains harness-configured, not supplied by the marketplace:

```bash
export LHC_ASKHUMAN_MCP_URL="https://your-notify.example/mcp"
python3 plugins/ask-human/scripts/setup_mcp.py --apply
```

`LHC_ASKSECRET_MCP_URL` selects `/secret`; protected optional `..._MCP_TOKEN`
becomes a Bearer header. Setup is dry-run by default, backs up on apply and never
justifies changing global permissions or exposing existing credentials.
