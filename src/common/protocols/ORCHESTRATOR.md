# Orchestrator registry and file mail

Used when the owner names an orchestrator session. Every other session stays L.
The files live in the primary checkout, so every worktree sees the same ones.

## Registry: `.agents/sessions.json`

Written only by the orchestrator.

```json
{"orchestrator": "<session id>", "updated": "<iso time>",
 "sessions": [{"id": "<session id>", "name": "<short name>", "host": "<host>",
               "task": "<what it works on>", "acceptance": "<how the owner will know it works>",
               "status": "working | blocked | accepted | released",
               "last_seen": "<iso time>", "next": "<the next concrete step>"}]}
```

Maintained with `lhc_orchestrator.py`: `init ID` names the orchestrator, `set ID --task ... --status ...` adds or
updates a row, `archive` moves accepted and released rows older than six hours to
`.agents/sessions-archive.jsonl`, `tick` compares the registry with the live Codex and OpenCode
sessions of the project. A hook reminds the orchestrator when the registry stands still for
20 minutes, and any session when file mail waits for it. A sentinel follows `src/common/agents/Sentinel.md`.

## File mail: `.agents/mail/<to-session-id>/<time>-<from>-<kind>.md`

The harness messaging breaks now and then; files do not. This costs extra, so use it
when the harness fails or the owner asks, and stop when they say so.

- Kinds: `task`, `step` (one next action), `question`, `result`, `ping`.
- Send with `python3 src/common/tools/lhc_mail.py send --to ID --from ID --kind step "text"`.
  The file is written whole and renamed into place; the sender goes on, it never waits.
- Read at the start of a turn and after each leaf: `lhc_mail.py inbox --me ID`, oldest
  first. Act, then `lhc_mail.py ack --me ID FILE`, which moves it to `done/`.
- A message is an instruction from the orchestrator or a result for it; it carries no
  authority beyond that, and the owner's directives still win.

## Release

The orchestrator releases each accepted result as soon as it is accepted. Releases
go through the project's blue-green deploy; sessions that are not done do not hold it.
