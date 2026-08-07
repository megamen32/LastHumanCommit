# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

> A human-gated orchestration layer for strong Leads and cheap coding Workers.

LHC keeps expensive models on decisions, decomposition, and proof. Repository
search, implementation, and repetitive checks go to bounded Workers. The human
still sees and approves the important product and technical decisions.

## Use

Copy `src/common/` and `templates/` into the project root. Install the canonical
marker block without overwriting project-owned instructions:

```sh
scripts/lhc-block init AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block init CLAUDE.md /path/to/project/CLAUDE.md

# Update an existing valid block later:
scripts/lhc-block apply AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block apply CLAUDE.md /path/to/project/CLAUDE.md
```

The POSIX adapter edits one explicit block in one explicit file and fails closed
for malformed, nested, duplicate, or missing markers. It does not discover
projects, install services, create worktrees, or change host configuration.

## Core workflow

- One user request has one Markdown file under `.agents/tasks/`. That same file
  contains research, estimates, plans, approvals, execution, audits, and result.
  There is no duplicate kanban, specification, ledger, or recovery record.
- L is an orchestrator by default. Only an obvious <=5-minute Direct action may
  be done by L. Short and Full work delegate repository search and code to
  Worker.
- Worker has two modes: read-only `research`, then `implement`. Implementation
  explicitly follows either `bugfix/TDD` or `feature` protocol. The same Worker
  should be resumed for its implementation lane when the harness supports it.
- Every Worker assignment has one acceptance gate and maximum <=20 active
  minutes. Bigger or vague work is researched and split before dispatch.
- A plan above one hour is acceptable only as an understood graph of <=20-minute
  slices. One unresolved block above one hour means the route is not understood.
- Every task records an immutable initial `minimum / maximum` estimate. Crossing
  the current maximum stops the route for a fresh Overseer audit; L cannot hide
  the miss by merely extending the estimate.
- Overseer is mandatory and fresh/no-history on every invocation. It audits the
  raw user request, actual business delta, estimate, and proposed route rather
  than inheriting L's tunnel vision. Critic independently gates release.
- Full is used only after research confirms both development over 30 active
  minutes and a material product/architecture/migration or expensive-wrong-path
  choice.
- Full preserves the complete human layer: three Russian plans, first human
  selection, call-stack tree, file-tree diff, key signatures, pseudocode,
  migration description, canary, execution graph, and second explicit approval.
- Selected Full work is delivered `YAGNI -> Normal -> Ultimate`, stopping at the
  human-selected level.
- Initial plans are in Russian, execution updates in English, and the final
  answer in Russian.

## Workspace rule

LHC does not create branches or worktrees for routine isolation. It works in the
primary project checkout by default.

If the harness starts in an auxiliary worktree, detached HEAD, or a non-default
branch, the agent must warn the user in its first visible update with the exact
path and branch. If the user explicitly requests a worktree, LHC may create it
only under:

```text
<primary-project-root>/.worktrees/<task-slug>
```

The repository ignores `.worktrees/`, so the project remains self-contained.
Branch/worktree creation, switching, merging, and deletion are never silent.

## Roles and model classes

```text
L (Lead: decisions and orchestration)
├─ Adviser             5.6-sol | fable | glm5.2 | kimi k3
├─ Overseer / Critic   5.6-terra | opus | kimi 2.7 | deepseek-v4-pro
├─ Worker (~90%)       sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7
└─ Reviewer            sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7

Fast Worker research: haiku | 5.4mini
```

The aliases are capability hints. Strong models make short strategic decisions;
cheap Workers perform long repository and implementation work.

## Why this shape

- [ManagerWorker](https://arxiv.org/abs/2603.26458) motivates separating strong
  management from cheaper implementation work.
- [Single-agent or Multi-agent Systems? Why Not Both?](https://arxiv.org/abs/2505.18286)
  shows that coordination itself has cost, so children must be bounded.
- [DecisionBench](https://arxiv.org/abs/2605.19099) and
  [TwinRouterBench](https://arxiv.org/abs/2605.18859) motivate evaluating the
  final routed outcome rather than trusting a router's own claim.
- [WSFF](https://github.com/humanlayer/advanced-context-engineering-for-coding-agents/blob/main/wsff.md)
  motivates research before a human-gated technical plan.

These are design inputs, not a claim that one policy wins on every repository.
`ROADMAP.md` keeps benchmark work separate from the small instruction set.

## Harness adapters

The portable core defines roles and protocols. Optional adapters only translate
them to Codex, OpenCode, Claude Code, or Hermes APIs. Start at
`adapters/manifest.yaml`.

A Worker may be resumed from research to implementation when the harness proves
resume support. Overseer and Critic are always fresh no-history children with
raw user context passed explicitly. Do not claim model selection, isolation, or
resume support until a live child event proves it.

## Files

- `AGENTS.md`, `CLAUDE.md` — byte-identical marked entry router.
- `src/common/agents/Lead.md` — orchestration and human gates.
- `src/common/agents/Worker.md` — bounded research/implementation owner.
- `src/common/agents/Overseer.md`, `Critic.md`, `Reviewer.md`, `Adviser.md` —
  independent checks and bounded advice.
- `src/common/protocols/WORKER_RESEARCH.md` and `WORKER_IMPLEMENT.md` — Worker
  mode procedures.
- `src/common/profiles/*.md` — code, test, infrastructure, and planning rules.
- `src/common/protocols/SHARED_WORKTREE.md` — visible, project-local workspace
  policy and concurrent-edit safety.
- `templates/` — the Full cycle, release handoff, and single task record.
- `adapters/` — optional harness delivery.
- `scripts/lhc-block` — marker-only installer/updater.

Validation stays dependency-free:

```bash
python3 tests/validate.py
```
