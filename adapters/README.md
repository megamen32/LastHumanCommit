# Harness adapters

The adapter layer translates portable Last Human Commit roles to one host's
agent API. Enabling one adapter does not install, configure, or rewrite another.

## Boundary

The core owns roles, profiles, protocols, the one-root-task rule, and human
approval semantics. An adapter owns only delivery syntax, profile frontmatter,
child context boundaries, model selection hooks, and resume transport.

```text
role contract × harness adapter
Lead          × Codex / OpenCode / Claude Code / Hermes / ZCode
Worker        × Codex / OpenCode / Claude Code / Hermes / ZCode
Tester        × Codex / OpenCode / Claude Code / Hermes / ZCode
```

Before every child call, L loads that adapter's
`subagent_instructions_template`. Children receive one compact prompt and their
assigned task path, append detailed evidence and the result to that same task
record, and return only TL;DR. They never create a second `todo-*` file or
parallel task record.

Every manifest records evidence as `proven`, `unproven`, `unsupported`, or
adapter-dependent. Do not claim role/model/fresh-context/resume behavior without
a live child event.

## Human requests

`human.ask_user.v1` and `human.ask_secret.v1` are semantic contracts. Fleet or
the active harness owns installation, routing, and attestation. AskSecret is
fail-closed: only opaque registered-agent SSS is acceptable; plaintext and
base64 fallback never enter an LLM-facing flow.

## Self-improve

Codex, OpenCode, Claude Code, and ZCode load `SELF_IMPROVE.md` only when its
concrete trigger occurred. Hermes uses its native memory/skill loop. Ordinary
success adds no retrospective record.

`scripts/lhc-block` remains a narrow marker utility. It is not an installer,
renderer, daemon, or adapter manager.
