# Codex adapter instructions

These instructions are optional Codex integration details, not part of a core
role. When a configured Codex profile embeds the complete role prompt, do not
ask the child to read the role file again. Use the file fallback only when the
active Codex surface has no native profile delivery.

Before every child call, load `templates/subagent.md`. It requires
`fork_context: false`, explicit Task Card context, and the cheapest sufficient
working model class. A Codex surface that cannot honor the no-history boundary
must not create a history-forked substitute.

Do not claim model selection, fresh-context isolation, or resume support until
a live child event proves the actual role, model, context boundary, and result.

Before L sends its final answer, run the core `SELF_IMPROVE.md` protocol and
persist its compact record. This is required even when native profile delivery
is unavailable.
