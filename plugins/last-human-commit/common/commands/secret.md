# /secret — hand a secret to the agent from the phone

Usage: `/secret NAME [target]`

- `NAME` — the environment variable name to set (for example `API_KEY`).
- `target` — optional destination file; default `.env` in the current project.

The whole operation is a few steps, produces no lectures, and never builds new
secret infrastructure.

## Flow

1. If an AskSecret MCP is connected (tools like `ask_secret`, `get_secret`,
   `ask_secret_run`), call `ask_secret(NAME)`. The user receives a phone prompt
   and pastes the secret there. When the secret is ready, `get_secret` returns
   an opaque file/URL: pipe the file content straight into the target (append
   `NAME=<value>` to `.env`, or export it for the process) in one command,
   without reading, printing, or echoing the value into chat or logs.
2. Otherwise, if AskHuman/notify (Telegram) is available, send one short
   message asking the user to deliver `NAME` (AskSecret link or direct paste),
   wait for the reply, and write it to the target the same way.
3. Otherwise ask in chat for the value, write it to the target immediately, and
   do not quote it back.

## Rules

- Confirm completion only as `NAME set in <target>`; never echo the value.
- Later reads of the secret are a normal one-step env/`.env` read.
- Do not demand attestation, do not create handoff layers, and do not insert
  confirmation prompts for this routine operation.
