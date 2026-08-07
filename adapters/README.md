# Harness adapters

The adapter layer translates portable Last Human Commit roles into a host's
agent API. Enabling one adapter must not install, configure, or rewrite another
harness.

## Core × harness

The core owns behavior:

```text
Lead / Worker / Overseer / Critic / Reviewer / Adviser
                    ×
Codex / OpenCode / Claude Code / Hermes
```

Worker is one role with `research` and `implement` modes. Adapters must not
recreate an Explorer role or duplicate common prompts.

Every adapter manifest names:

- complete role source;
- optional harness instructions;
- `subagent_instructions_template`;
- evidence for native profile, fresh child, model override, and resume support.

Before a child call, L loads the adapter template. The common core still selects
the lowest sufficient model, caps each Worker assignment at 20 active minutes,
and defines the compact assignment.

## Context boundaries

Two child lifecycles are intentionally different:

- A Worker begins in a fresh context, researches one lane, and should be resumed
  for that lane's implementation when the harness proves resume support.
- Overseer and Critic are always fresh no-history children. Raw user context and
  the current task file are passed explicitly; L's reasoning history and desired
  verdict are not.

An adapter must not claim fresh context, actual model selection, or resume until
a live child event proves it. Evidence states are `proven`, `unproven`, or
`unsupported`.

## Project boundary

Adapters do not create project branches or worktrees. If a harness starts an
agent in an auxiliary workspace, core instructions require immediate disclosure
to the user. An explicitly requested LHC worktree belongs only under the primary
project's `.worktrees/` directory.

`scripts/lhc-block` remains a narrow marker utility. It is not an installer,
renderer, daemon, scheduler, or adapter manager.

## Self-improve ownership

Codex, OpenCode, and Claude Code run the core `SELF_IMPROVE.md` record. Hermes
uses its native memory/skill review and `/learn` flow, so the adapter does not
duplicate it.
