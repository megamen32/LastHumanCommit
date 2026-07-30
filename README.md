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
