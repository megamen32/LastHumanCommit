# Set a secret

Usage: `/secret NAME [target]`. NAME is the environment variable; target defaults to the current project's `.env`.

Use the connected AskSecret workflow when available. `ask_secret(NAME)` asks the user through its protected surface; `get_secret` or `ask_secret_run` passes the resulting value to the authorized destination. Keep values out of chat, logs and task records.

When the value already exists in an approved environment or secret store, use that reference directly. If no protected delivery route is available, tell the user which credential and destination are needed and use the project's established method.

Confirm the name and destination after it is written. Later reads use the same normal environment or secret-store mechanism.
