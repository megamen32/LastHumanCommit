# ZCode adapter instructions

ZCode exposes two native role-delivery surfaces. Prefer the project-or-agent
profile mechanism when one is configured: a complete canonical role is
materialized as a Markdown file under the ZCode agents directory
(`~/.zcode/agents/<role>.md`) with YAML frontmatter (`name`, `description`,
`model`, `tools`) and the full role prompt as the body. ZCode has no include
directive, so the complete role contract must live in that file; it must not
spend a turn reading `src/common/agents/<Role>.md`. Otherwise the
marker-preserving `AGENTS.md` block is the portable fallback. The adapter must
keep the complete role context in the child prompt and must not overwrite
project-owned text outside the marker pair.

ZCode dispatches children through its `Agent` tool with a `subagent_type`
identifier; an active `PreToolUse` guard forbids passing an explicit `model`
key, so the role's model is selected by the agent profile's frontmatter, not by
the dispatch call. Never fork the parent conversation history; rely on the
fresh-context boundary.

Before every child call, load `templates/subagent.md` for the native context,
Task Card, and cheapest-sufficient model rules.

Do not promise scheduled resume until the active ZCode surface exposes and
verifies its cron or scheduled-task transport.

Before L sends its final answer, run the core `SELF_IMPROVE.md` protocol and
persist its compact record.
