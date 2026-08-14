---
description: Create a one-time browser link for entering a secret without exposing its value in chat.
---

# Ask Secret

Create an opaque, one-time browser handoff for a secret value. The secret must
never be typed into this conversation, returned by an MCP tool, written to a
file, placed in an argument or environment variable, or included in a summary.

## Preflight

1. Read the optional argument after `/asksecret` as the logical secret name.
2. If no name was supplied, ask only: `Как назвать секрет?` Never ask what the
   secret is and never ask the user to paste it here.
3. Confirm that the `AskSecret` MCP server exposes `get_secret`. If it is not
   available, stop and explain that the Ask Secret MCP capability must be
   enabled; do not fall back to a normal chat question.

## Plan

Call `get_secret` on the `AskSecret` MCP server with the named secret. Include a
fresh opaque `request_id` when the tool accepts it, so completion can be
correlated without carrying the secret. Use the server's registered-agent
encryption path when the tool exposes an `agent_id`; never use a base64 or
plaintext fallback.

## Commands

Call:

```text
get_secret({
  "name": "<logical secret name>",
  "request_id": "<fresh UUID, if supported>",
  "agent_id": "<registered agent identity, if required by the server>"
})
```

When the result says the secret is missing or pending, extract only the
one-time `/i/<token>` browser URL. Present that URL as a clickable Markdown
link and tell the user to open it and enter the value there.

Never display or forward a `/d/<token>` URL, an encrypted blob path, a bearer
token, an API key, or any returned plaintext. If no `/i/` URL is present, do
not invent one.

## Verification

Verify that the response contains an input URL beginning with `/i/` (normally
under the configured SSS HTTPS origin), and that no secret-like value was
included in the response. Do not submit the form yourself and do not fetch the
secret after the user enters it unless the user separately requests a
specific, approved opaque consumer action.

## Summary

Reply briefly:

> Откройте одноразовую ссылку и введите секрет там: [ввести секрет](<input-url>)

Do not quote the secret name if it could reveal sensitive context. If the
secret is already provisioned, say that it is already available and that a new
input link was not created; do not show its retrieval URL.

## Next Steps

After the user submits the form, a later approved secret-consuming operation
may call `get_secret` again and pass the result only through the registered
opaque runtime/consumer path. The value must remain outside chat output.
