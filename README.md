# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

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

`init` appends the canonical LHC block only when the target has no marker lines;
`apply` requires one valid block and replaces only its contents. Both refuse
malformed, nested, or duplicate blocks without writing. The adapter never
discovers paths, creates project directories, changes host configuration, or
installs a runtime service.

The adapter needs only standard POSIX `sh`, `awk`, `ed`, `cp`, and `tail`
utilities. It edits an existing target in place, preserving its ownership,
permissions, and surrounding text; before an edit it keeps a private adjacent
backup and restores the original content if the editor fails.

## Workflow

- Every request, including Direct and Short work, gets one Markdown task file
  under `.agents/tasks/` with an estimate; their execution still stays fast.
- Overseer is mandatory for every task, while other bounded subagents are used
  only when the selected scope needs them.
- Full work researches first and presents the initial plans in Russian:
  Ultimate, Normal, and YAGNI. It then waits for the human to choose.
- `YAGNI -> Normal -> Ultimate` is the delivery order after selection, not the
  initial plan order.
- Use execution updates in English to keep collaboration inspectable. The
  final answer in Russian gives the human the tested outcome and remaining risks.
- Review follows the selected outcome and affected scope. Unsolicited secondary
  work is forbidden unless it is user-confirmed or a minimal safe-canary
  prerequisite.
- L schedules its own 30-minute wake and revalidates before deploy.
- On Codex, OpenCode, and Claude Code, L records a compact self-improvement
  retrospective; Hermes keeps its native memory/skill learning loop.
- L assumes a shared worktree: recent foreign edits are hands-off; older ones
  get final review and, when safe, are committed with the reviewed result.

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

LHC names model classes and requires fresh, scoped cheap-child work. It
does not claim that every harness can select every child model. Add a
harness-specific profile only after a live child test proves its role, model,
and no-history boundary; the Codex CLI limitation is tracked in `ROADMAP.md`.

## Harness adapters

The portable LHC instructions are capability-first; harness adapters are a separate,
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
