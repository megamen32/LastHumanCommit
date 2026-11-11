# Dispatcher registry and file mail

Use when the user appoints a dispatcher. Project files live in the primary checkout so task worktrees share the same registry.

## Registry

`.agents/sessions.json` is maintained by the dispatcher:

```json
{"dispatcher":"<session id>","updated":"<iso time>","sessions":[{"id":"<session id>","name":"<short name>","host":"<host>","task":"<current work>","acceptance":"<recognizable result>","status":"working | blocked | accepted | released","last_seen":"<iso time>","next":"<next step>"}]}
```

`lhc_dispatcher.py init ID` names the dispatcher; `set ID --task ... --status ...` updates a session. `tick` compares the registry with live sessions. `archive` moves accepted/released entries older than six hours into `sessions-archive.jsonl`. A reminder is not evidence that a session stalled; inspect its actual work.

Legacy `lhc_orchestrator.py`, registry key `orchestrator` and mail destination `ORCHESTRATOR` remain aliases.

## File mail

Use native messages first. When unavailable, the existing file channel is `.agents/mail/<to-session-id>/<time>-<from>-<kind>.md`. Kinds are `task`, `step`, `question`, `result`, `ping`.

```sh
python3 common/tools/lhc_mail.py send --to ID --from ID --kind step "message"
python3 common/tools/lhc_mail.py inbox --me ID
python3 common/tools/lhc_mail.py ack --me ID FILE
```

Writes are atomic; `ack` moves a processed message to `done/`. Messages carry the sender's task context, not new user authority.

Move accepted work through its execution owner and existing deployment route. A peer's unfinished independent task need not hold a ready result.
