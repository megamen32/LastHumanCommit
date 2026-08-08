# Codex adapter instructions

These are optional Codex integration details, not a core role. When a configured
profile embeds the complete role prompt, do not ask the child to read the role
file again. Use file fallback only when native profile delivery is absent.

Before every child call, load `templates/subagent.md`. It requires
`fork_context: false`, explicit compact assignment context, the root-task read-
only boundary, and the cheapest sufficient working model. A Codex surface that
cannot honor no-history must not create a history-forked substitute.

For ordinary missing information use AskHuman. For a secret or password route
through AskSecret/SSS only when attested. The only acceptable handoff is an opaque registered-agent SSS path; reject plaintext and base64 fallback.

Do not claim model selection, fresh-context isolation, or resume support until a
live child event proves it. Before L's final answer, run `SELF_IMPROVE.md` only
when its trigger occurred.
