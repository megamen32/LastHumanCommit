# Coordinate sessions

Use the native runtime that owns the peer. Native IDs from another runtime may not resolve in Herder. For supported Codex, ZCode and OpenCode sessions, Herder provides the existing message and `resume_after` route.

MiniMax Code uses `session list`, `session send` and `session messages`. A running peer may need `force_steer: true` to receive the message in its current turn; a plain send waits until a new turn can begin. An accepted or steered receipt establishes admission, while the peer's own result establishes completion. Read that result instead of resending the task.

## File channel

Project chat lives in `<primary-checkout>/.agents/shared-session/`; host chat in `~/.agents/shared-session/` or the existing `LHC_SYSTEM_CHAT_ROOT`. Each message is a JSON file, with separate `sessions/` state and reader cursors.

```sh
python3 <LHC>/common/tools/lhc_chat.py --repo <project> send --sender <harness:session> --text 'Updating API; UI is outside my scope.'
python3 <LHC>/common/tools/lhc_chat.py --repo <worktree> read --reader <harness:session>
python3 <LHC>/common/tools/lhc_chat.py --system send --sender <harness:session> --text 'Shared service migration completed.'
```

Use `--to` for the recipient and the same `--id` when retrying that message. Files are published atomically; each reader has its own cursor. A file does not wake a stopped runtime. Use the supported native continuation when a wake is needed.

Read coordination when starting shared work, changing a peer dependency or resuming after a handoff. Send material scope changes, conflicts, decisions and results. Identical paths on different hosts are not shared storage; use the project's configured connection. Keep task decisions in the task record, not only in chat.

## Ownership

Name the session responsible for each shared write or runtime operation. Send its scope before concurrent work and record a handoff when the receiver accepts it. The Lead integrates assigned results; a supervisor should coordinate with that execution owner before modifying the same live service.

Preserve another session's unfinished work. An idle critical-path session can be resumed through its supported route when the task remains authorized. A direct human stop stays in force.

## User communications

Use the existing configured Notice Place/UserIO integration for operator notifications, questions and escalation. `commands/askhuman.md` documents the stable request identity, exact-session binding and answer route. UserIO supports the account's declared message, file, call and meeting channels.

Reconcile an uncertain delivery rather than sending duplicate messages through another route. Keep credentials in their protected store and respect the configured recipient and quiet-hours policy. Missing optional communication support does not require building a new service for the task.
