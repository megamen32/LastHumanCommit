# LastHumanCommit

> A small, human-gated instruction set for cheaper multi-agent coding.

The root agent keeps decisions and integration. Specialist prompts are loaded
only by the agent doing that job, so the Lead does not carry every role in
context.

## Use

Copy `src/common/` and `templates/` into the project root. The two entry files
are intentionally identical and route each agent to exactly one role file.

Never copy `AGENTS.md` or `CLAUDE.md` over an existing project file. They are
canonical marker blocks. Add or update only that block with the explicit,
POSIX-standard adapter:

```sh
scripts/lhc-block init AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block init CLAUDE.md /path/to/project/CLAUDE.md

# After updating this repository, update an already initialized project:
scripts/lhc-block apply AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block apply CLAUDE.md /path/to/project/CLAUDE.md
```

`init` appends the canonical block only when the target has no marker lines;
`apply` requires one valid block and replaces only its contents. Both refuse
malformed, nested, or duplicate blocks without writing. The adapter never
discovers paths, creates project directories, changes host configuration, or
installs a runtime service.

The adapter needs only standard POSIX `sh`, `awk`, `ed`, `cp`, and `tail`
utilities. It edits an existing target in place, preserving its ownership,
permissions, and surrounding text; before an edit it keeps a private adjacent
backup and restores the original content if the editor fails.

## Workflow

- Direct and Short work stay fast.
- Full work researches first, presents Ultimate/Normal/YAGNI, and waits for the
  human to choose.
- Full work uses bounded subagents and reviews the whole repository.
- A tested commit receives a Russian mobile summary.
- L schedules its own 30-minute wake and revalidates before deploy.
- On Codex, OpenCode, and Claude Code, L records a compact self-improvement
  retrospective; Hermes keeps its native memory/skill learning loop.

## Roles and models

```text
L (Lead)
├─ Adviser             5.6-sol | fable | glm5.2 | kimi k3
├─ Critic / Overseer   5.6-terra | opus | kimi 2.7 | deepseek-v4-pro
├─ Explorer            sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7
├─ Worker (~90%)       sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7
└─ Reviewer            sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7

Fast read-only lookup: haiku | 5.4mini
```

The strongest models are short strategic advisers, not long-running workers.
Aliases are capability hints and may be replaced by the nearest available
equivalent.

## Why this shape

- [ManagerWorker](https://arxiv.org/abs/2603.26458) found that a strong manager
  plus a cheap coding worker matched a strong solo agent on its experiment; the
  manager's early research and direction mattered more than a final review.
- [Single-agent or Multi-agent Systems? Why Not Both?](https://arxiv.org/abs/2505.18286)
  finds coordination has a cost: add agents only for bounded, useful work.
- [DecisionBench](https://arxiv.org/abs/2605.19099) and
  [TwinRouterBench](https://arxiv.org/abs/2605.18859) motivate measuring routing
  on held-out end-to-end tasks, not trusting a model's routing claim.
- [WSFF](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md)
  motivates research before a human-gated plan and compact planning views.

These are preprints and design input, not a promise that one routing policy
wins everywhere. `ROADMAP.md` keeps local benchmark work separate from the
small instruction set.

## Routing boundary

The canon names model classes and requires fresh, scoped cheap-child work. It
does not claim that every harness can select every child model. Add a
harness-specific profile only after a live child test proves its role, model,
and no-history boundary; the Codex CLI limitation is tracked in `ROADMAP.md`.

## Harness adapters

The portable canon is capability-first; harness adapters are a separate,
optional delivery layer. Start at `adapters/manifest.yaml` when installing a
Codex, OpenCode, Claude Code, or Hermes integration. An adapter may provide
small harness-specific instructions, but it must not duplicate or redefine a
core role. The Hermes adapter is an external plugin; the other manifests
record their current proof status and remain opt-in.

## Files

- `AGENTS.md`, `CLAUDE.md` — canonical marked role router for explicit targets.
- `src/common/agents/Lead.md` — root workflow, human gate, and release action.
- `src/common/agents/*.md` — independently loadable specialist roles.
- `src/common/profiles/*.md` — optional domain rules for an assigned role.
- `src/common/protocols/*.md` — event-triggered procedures.
- `templates/` — planning, handoff, and optional `.agents/` records.
- `adapters/` — modular harness manifests, optional instructions, and plugins.
- `scripts/lhc-block` — explicit, marker-only add/update/check/remove adapter.
- `docs/agent-authoring.md` — maintainer rules.

Validation stays deliberately small:

```bash
python3 tests/validate.py
```
