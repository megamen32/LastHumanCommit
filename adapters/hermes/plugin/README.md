# Last Human Commit plugin for Hermes

This external plugin does not modify Hermes source code or project instruction
files. Enable `last-human-commit` in `~/.hermes/config.yaml` under
`plugins.enabled`.

Tag a delegated goal to give its child one complete canonical role prompt:

```text
[LHC_ROLE=worker] /absolute/project/.agents/tasks/todo-auth-research.md
[LHC_ROLE=worker] /absolute/project/.agents/tasks/work-auth-implementation.md
```

L writes the bounded assignment in the task file. The child appends its detailed
result there and returns only TL;DR to L.

Hermes' native `role: leaf|orchestrator` remains unchanged. The plugin reads
only the explicit LHC marker block in `AGENTS.md` or `CLAUDE.md`, and reads role
files from `LAST_HUMAN_COMMIT_ROOT` (default:
`~/.local/share/last-human-commit/current`). It never writes those files.

The adapter also ships a versioned Hermes profile bundle under
`adapters/hermes/profile/` for Fleet to materialize a separate `LHC` profile
with native Clarify replaced by AskHuman and secret requests routed through
AskSecret/SSS.
