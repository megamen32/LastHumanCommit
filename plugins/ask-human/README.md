# Ask Human

Ask Human is the standard way for any harness to ask a human: the harness asks
its own question, the question reaches the human through the Notice Place
human-request intake (Telegram), and the answer comes back to the harness.

It is a plugin of the **last-human-commit** marketplace, so every harness of the
fleet installs it from the same marketplace it already uses.

```
plugins/ask-human/
  plugin.json                 Agent Plugin manifest (portable surface)
  .claude-plugin/plugin.json  Claude Code manifest
  .codex-plugin/plugin.json   Codex manifest, declares the MCP server
  .mcp.json                   the AskHuman MCP server, without a credential
  commands/askhuman.md        the command: ask one blocking question
  hooks/hooks.json            the interception of the harness's own question
  hooks/zcode-hooks.json      the same interception in the form of ZCode
  scripts/ask_human_hook.py   the interceptor: payload -> human -> answer
  scripts/setup_mcp.py        registration of the MCP server in the harnesses
  tests/                      the tests of both scripts
```

## What it does

The harness already knows how to ask a human: it asks for a permission. Ask
Human does not invent a second question channel. It intercepts the moment the
harness asks, forwards that exact question to the human, waits for the answer
and hands the answer back to the harness.

```text
harness asks  ->  hook reads the payload  ->  POST /v1/human-requests
                                                (the human answers in Telegram)
                     hook polls GET /v1/human-requests/{id}
                                                |
        harness gets  <-  hook prints the answer on stdout
```

## Which hook event, and why

The plugin registers **`PermissionRequest`**.

* `PermissionRequest` is the one event that means, by definition, *the harness
  is asking a human*. It fires exactly at the permission gate, and its payload
  carries the question in a structured form: `tool_name` and `tool_input`, plus
  `session_id`, `cwd` and `turn_id`. Nothing has to be guessed from prose.
* `Stop` was considered and is **not** registered by default. Its payload
  carries `last_assistant_message`: free text with no marker that says "this is
  a question". Registering it would send a Telegram card at the end of every
  turn. The script can read it (`--event Stop`, the answer comes back as the
  `reason` of a blocked stop), so it is one line of `hooks/hooks.json` away.
* `Interrupt` was considered and rejected. Its payload has no question at all:
  it says that the human interrupted the agent, which is the opposite direction.

Both harnesses agree on the wire. Codex declares the event as
`permission-request.command.input` and Claude Code builds the same payload with
`tool_name`, `tool_input` and `permission_suggestions`; both accept the same
answer, `{"hookSpecificOutput": {"hookEventName": "PermissionRequest",
"decision": {"behavior": "allow" | "deny", "message": "..."}}}`.

Two fields of that answer are reserved and fail the hook closed, so the plugin
never writes them: `interrupt` and `updatedInput` / `updatedPermissions`.

## The two hook forms

The same interception is shipped twice, because the harnesses do not read a
hook document the same way:

| file | timeout key | read by |
| --- | --- | --- |
| `hooks/hooks.json` | `timeout`, in seconds | codex, Claude Code, MiniMax Code |
| `hooks/zcode-hooks.json` | `timeoutMs`, in milliseconds | ZCode |

Both forms name the same event, `PermissionRequest`, and both run the same
script of this plugin. The path of the script is resolved through the chain
`${CLAUDE_PLUGIN_ROOT:-${CODEX_PLUGIN_ROOT:-${PLUGIN_ROOT:-${ZCODE_PLUGIN_ROOT:-<the installed copy of this plugin>}}}}`,
so a hook always runs the script of the package it is installed with, never the
script of another package.

The plugin declares no `.zcode-plugin/plugin.json`. ZCode reads the
`hooks/hooks.json` of a package by default and honours its `timeout` in
seconds, so the question is intercepted once. A package that also declares
`hooks/zcode-hooks.json` in that manifest registers `PermissionRequest` twice,
once per file, and the human is asked the same question twice.

## Which harness intercepts the question

| harness | the question is intercepted | why |
| --- | --- | --- |
| codex | yes | codex reads `hooks/hooks.json` of the package and exports `PLUGIN_ROOT` |
| Claude Code | yes | the same document, and `CLAUDE_PLUGIN_ROOT` |
| ZCode | yes | `PermissionRequest` is one of its supported events, and its own form carries the timeout in `timeoutMs` |
| MiniMax Code | only with a form of its own | it reads `hooks/hooks.json`, but it accepts a handler timeout of 1 to 10 seconds only, so `timeout: 120` is refused and the handler is skipped |
| hermes | no | its manifest installs no lifecycle observer |
| opencode | no | its plugins are TypeScript modules with their own contract; there is no JSON hook document and no permission event |

## How the question reaches the human

The transport is the contract of `ask_human` in the notify MCP, unchanged. No
second transport is invented:

* `POST /v1/human-requests` with the `ask_human.request.v1` envelope, a
  `Bearer` token and the `Idempotency-Key: human-request:<request_id>`;
* `GET /v1/human-requests/{request_id}` until the state leaves `pending`;
* the answer is `response_value`, the one who answered is `response_actor`.

The address and the token come from the host environment:

| key | meaning |
| --- | --- |
| `ASK_HUMAN_URL` | the human-request intake |
| `NOTIFY_CENTER_EVENT_URL` | the events URL; `/events` is rewritten to `/human-requests` |
| `NOTIFY_CENTER_TOKEN` | the bearer token of the producer |
| `NOTIFY_CENTER_PROJECT` | the project scope of the question |
| `NOTIFY_CENTER_RECIPIENT` | the recipient of the question |
| `ASK_HUMAN_ALLOWED_ACTORS` | the actors allowed to answer |

`~/.config/ask-human/env` (the protected env file of the host) and a plain
`.env` are read as well. The process environment wins over the protected file,
and the protected file wins over a plain `.env`. Nothing of this is in the
repository: the file has no token and no absolute path.

## How the answer comes back

* **The human answered.** The hook prints the answer on stdout, and for
  `PermissionRequest` it also prints the decision: `deny` when the answer
  contains one of the refusal words (`ASK_HUMAN_DENY_WORDS`, by default `no`,
  `deny`, `stop`, `cancel`, `нет`, `отказ`, `стоп`, `запрет`, ...), `allow`
  otherwise. The answer text is always in `systemMessage` and in the `message`
  of the decision, so the harness shows the human's own words.
* **No answer yet.** The hook prints that the question was sent to the human,
  with the `request_id`, and no decision: the harness then asks the human in
  its own UI as usual.
* **The human could not be reached.** The hook prints the reason and no
  decision. The hook never blocks the harness, and it never prints nothing:
  every path ends in an explicit message.

The hook waits at most `ASK_HUMAN_HOOK_TIMEOUT` seconds (90 by default); the
manifest allows 120. A shorter wait makes the hook give up earlier and let the
harness ask directly.

## Registration of the MCP server

The marketplace cannot pass parameters, so the endpoint comes from the
environment of the host:

```bash
python3 plugins/ask-human/scripts/setup_mcp.py             # dry-run: prints the snippet
python3 plugins/ask-human/scripts/setup_mcp.py --apply     # patches ~/.codex/config.toml
```

The script is dry-run by default. `--apply` writes the config of the harness on
this machine, keeps a timestamped backup and leaves the sections of the other
servers alone. It reads `LHC_ASKHUMAN_MCP_URL`, `ASK_HUMAN_MCP_URL` and
`ASK_HUMAN_URL`; an explicit `--url` wins over all of them. When the endpoint
comes from `ASK_HUMAN_URL` it is the human-request intake of the service, so
the MCP URL of the same service is derived from it and the derivation is
printed before anything is written. The bearer token comes from
`NOTIFY_CENTER_TOKEN`.

For codex the result is a `[mcp_servers.AskHuman]` section with the URL and a
`[mcp_servers.AskHuman.http_headers]` section with the `Authorization` header.
For hermes, zcode, opencode and minimax the dry-run prints the equivalent JSON
snippet of each of them.

## The credential stays out of the repository

`.mcp.json` declares the AskHuman MCP server with
`"bearer_token_env_var": "NOTIFY_CENTER_TOKEN"`, which codex reads as the name
of the environment variable that holds the token. The value is never written to
a file of the repository.

The Claude Code manifest declares no MCP server: Claude Code resolves the
credential only through `allowedEnvVars`, which belongs to the operator's own
settings and not to a plugin. Register the AskHuman MCP for Claude Code with
`setup_mcp.py --apply`, which prints the snippet with the `Authorization`
header for it.

## The marketplace entry

The plugin is a third entry of the marketplace of the repository, next to
`last-human-commit` and `gsd`:

```json
{
  "name": "ask-human",
  "source": "./plugins/ask-human",
  "description": "Ask Human: forward the harness's own permission question to the human through the Notice Place human-request intake, and hand the answer back to the harness.",
  "version": "1.0.0",
  "category": "workflow"
}
```

## The tests

```bash
python3 -m pytest plugins/ask-human/tests -q
```

The tests need no network and no real recipient: a local HTTP server on
`127.0.0.1` stands in for the Notice Place service.
