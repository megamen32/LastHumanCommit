# Harness adapters

LHC defines roles and the workflow. An adapter supplies native profile syntax, child creation, model selection, message delivery and continuation for one runtime.

Use the current runtime's available APIs and the assigned working directory. Its manifest records `proven`, `unproven`, `unsupported` or adapter-dependent capabilities. Source implementation and a live execution are different evidence.

The child receives the role and the context needed for its assignment. `templates/subagent.md` adds the runtime details; the shared rules remain in AGENTS.md rather than being copied into every prompt.

Native time and compaction events can use `common/tools/lhc_time_guard.py`. Without an event or resume capability, retain the work and state the limitation. Use the runtime's existing memory and authorization mechanisms.

`scripts/lhc-block` manages the marked instruction block while preserving project-owned text.
