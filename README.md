# LastHumanCommit

> A small, human-gated instruction set for cheaper multi-agent coding.

The root agent keeps decisions and integration. Specialist prompts are loaded
only by the agent doing that job, so the Lead does not carry every role in
context.

## Use

Copy `AGENTS.md`, `CLAUDE.md`, `src/common/`, and `templates/` into the project
root. The two entry files are intentionally identical and route each agent to
exactly one role file. No installer or runtime service is required.

## Workflow

- Direct and Short work stay fast.
- Full work researches first, presents Ultimate/Normal/YAGNI, and waits for the
  human to choose.
- Full work uses bounded subagents and reviews the whole repository.
- A tested commit receives a Russian mobile summary.
- L schedules its own 30-minute wake and revalidates before deploy.

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

## Files

- `AGENTS.md`, `CLAUDE.md` — portable role router and work classification.
- `src/common/agents/Lead.md` — root workflow, human gate, and release action.
- `src/common/agents/*.md` — independently loadable specialist roles.
- `src/common/profiles/*.md` — optional domain rules for an assigned role.
- `src/common/protocols/*.md` — event-triggered procedures.
- `templates/` — planning and handoff records.
- `docs/agent-authoring.md` — maintainer rules.

Validation stays deliberately small:

```bash
python3 tests/validate.py
```
