# Last Human Commit plugin for Hermes

This external plugin does not modify Hermes source code or project instruction
files. Enable `last-human-commit` in `~/.hermes/config.yaml` under
`plugins.enabled`.

On every `pre_llm_call`, the plugin also invokes the shared business time
guard. After Hermes compacts a transcript, it detects the native compaction
summary, updates one bounded `current-handoff.md`, increments the durable
compaction count exactly once, and injects that handoff into the next user
turn. State lives under the nearest project `.agents/shared-session/compaction/`;
historical handoffs are replaced, not appended forever.

Tag a delegated goal to give its child one complete canonical role prompt:

```text
[LHC_ROLE=worker] mode=research — inspect the authentication boundary and report evidence.
[LHC_ROLE=worker] mode=implement:bugfix/TDD — implement only the approved slice.
```

Hermes' native `role: leaf|orchestrator` remains unchanged. The plugin reads
only the explicit LHC marker block in `AGENTS.md` or `CLAUDE.md`, and reads role
files from `LAST_HUMAN_COMMIT_ROOT` (default:
`~/.local/share/last-human-commit/current`). It never writes those files.
