<!-- last-human-commit:begin -->
LHC is shared through the globally installed `last-human-commit` Agent Plugin.
Read its bundled `AGENTS.md` through the active native plugin/skill location;
resolve `common/` from that same package. Do not use the legacy
`~/.local/share/last-human-commit/current` store or copy LHC rules into projects.
For LHC changes use its `lhc-update-agents` skill and canonical LHC repository.
Infer the current work's owning project from the conversation and files being
changed. Keep its ToDo/tasks under that project's `.agents/`, even when this
session was opened elsewhere. Do not require a project-selection ritual.
<!-- last-human-commit:end -->
