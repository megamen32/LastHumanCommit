---
description: Ask one ordinary blocking human question through the configured AskHuman capability.
---

# Ask Human

Create one correlated request for an ordinary decision or missing non-secret
information. Do not use this command for passwords, API keys, tokens, or other
secrets; use `/asksecret` for those.

## Preflight

1. Read the text after `/askhuman` as the question.
2. If no question was supplied, ask the user to provide the ordinary question
   in one sentence. Never request a secret value in chat.
3. Confirm that the `AskHuman` MCP server exposes `ask_human`. If it is not
   available, report the capability as unavailable; do not silently replace it
   with an untracked chat question or another notification path.

## Plan

Call `ask_human` on the `AskHuman` MCP server with the question, an appropriate
urgency, and `blocking: true`. Use a fresh opaque request correlation if the
server supports one. Keep delivery mechanics, notification routes, and any
response value outside the command output.

## Commands

Call:

```text
ask_human({
  "question": "<ordinary non-secret question>",
  "urgency": "normal",
  "blocking": true
})
```

## Verification

Verify that the result contains only the expected opaque request state such as
`request_id` and `state`. Do not expose transport details, credentials, or
unrelated notification metadata. One authorized response must resolve only its
correlated request.

## Summary

Reply with a short acknowledgement that the question was sent and the current
opaque state. Do not duplicate the question through a second delivery channel.

## Next Steps

Continue only after the correlated response arrives. If the request is
cancelled or expires, report that state and do not create a duplicate request
unless the user explicitly asks to retry.
