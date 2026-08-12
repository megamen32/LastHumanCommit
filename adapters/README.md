# Harness adapters

The adapter layer translates portable Last Human Commit roles to one host's
agent API. Enabling one adapter does not install, configure, or rewrite another.

The core owns business-first routing, optional roles, cost-triggered persistence,
claim-calibrated proof, and secret/workspace safety. An adapter owns only
delivery syntax, profile frontmatter, child context boundaries, model hooks,
wait/join, and resume transport.

Before a child call, L loads that adapter's
`subagent_instructions_template`. The child receives the smallest sufficient
context. A task/result path is included only when durable handoff, recovery,
reuse, or rediscovery economics justify it; no adapter makes a task card or
duplicate detailed report mandatory.

Every manifest records capabilities as `proven`, `unproven`, `unsupported`, or
adapter-dependent. Do not claim role/model/fresh-context/wait/resume behavior
without a live child event.

When available, adapters map a non-blocking child-to-parent message to Worker
decision questions and map lifecycle/checkpoint/finalizer/scheduler events to
`common/tools/lhc_time_guard.py`. Without either capability, preserve the
question/time state and report delayed delivery; never simulate a live event.

## Human requests

`human.ask_user.v1` and `human.ask_secret.v1` are semantic contracts. Fleet or
the active harness owns installation, routing, and attestation. AskSecret is
fail-closed: only opaque registered-agent SSS is acceptable; plaintext and
base64 fallback never enter an LLM-facing flow.

## Self-improve

Codex, OpenCode, Claude Code, and ZCode load `SELF_IMPROVE.md` only on its
concrete trigger. Hermes uses its native memory/skill loop. Ordinary success
adds no retrospective record.

`scripts/lhc-block` remains a narrow marker utility, not an installer, daemon,
scheduler, or adapter manager.
