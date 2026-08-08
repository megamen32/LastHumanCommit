# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

> A human-gated orchestration layer for strong Leads and cheap coding Workers.

LHC keeps expensive models on decisions, decomposition, human-readable planning,
and proof. Repository search, implementation, and repetitive checks go to
bounded Workers. The human still sees exactly what a long, product-changing
implementation will do before it starts.

## Use

Copy `src/common/` and `templates/` into the project root. Install or update only
the canonical marker block; never overwrite project-owned instructions:

```sh
scripts/lhc-block init AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block init CLAUDE.md /path/to/project/CLAUDE.md
scripts/lhc-block apply AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block apply CLAUDE.md /path/to/project/CLAUDE.md
```

The POSIX helper fails closed for malformed, nested, duplicate, or missing
markers. It does not discover projects, install services, create worktrees, or
change host configuration.

## Core workflow

- One user request has one Markdown file under `.agents/tasks/`. Only L writes
  it. The same file holds research, estimates, plans, approvals, execution,
  audits, and result; children never create separate Task Cards or reports.
- L is an orchestrator by default. Only an obvious <=5-minute Direct action may
  be done by L. Short and Full repository search and code go to Worker.
- Worker has read-only `research`, then bounded `implement` with subtype
  `bugfix/TDD` or `feature`. Resume the same Worker when the harness supports it.
- Every Worker slice has one acceptance gate and maximum <=20 active minutes.
  Bigger or vague work is researched and split before dispatch.
- A plan above one hour is valid only as an understood graph of <=20-minute
  slices. One unresolved block above one hour means the route is not understood.
- Every task keeps one immutable initial `minimum / maximum` estimate. Crossing
  maximum stops the route for fresh Overseer; changing the number alone is not
  progress.
- Overseer is mandatory and fresh/no-history. It runs on events: before Direct
  completion; after the first Short result; after Full research and every wave;
  before release; and immediately on overrun, two failures, route/scope change,
  Lead doing Worker work, or activity without canary movement. Thirty minutes is
  only an additional trigger, never a cooldown.
- Full is used only after research confirms both development over 30 active
  minutes and a material product/architecture/migration or expensive-wrong-path
  choice.
- Full always presents three Russian plans, waits for selection, then shows the
  complete call-stack tree, file-tree diff, key signatures, pseudocode,
  migration, canary, and execution graph, and waits for a second explicit approval.
- The third Full plan is `YAGNI 80/20 — полный результат`; it is complete, not
  an unfinished MVP. Delivery slices never relabel partial work as the result.
- Reviewer checks the task-owned diff. Fresh Tester proves the real user flow for
  Full. Fresh Critic gates release or another irreversible action.

## Workspace rule

Routine work stays in the current primary checkout. LHC never creates branches
or worktrees for cleanliness or isolation.

If a harness starts in an auxiliary worktree, detached HEAD, or non-default
branch, the first visible update shows the exact path, branch, and primary
checkout. A user-requested worktree may exist only at:

```text
<primary-project-root>/.worktrees/<task-slug>
```

`.worktrees/` is ignored by the repository. Branch/worktree creation, switching,
merging, and deletion are never silent. Foreign edits are preserved but never
silently included in the current task's commit.

## Code profile

The strict `Code.md` profile is intentional: explicit function contracts,
structured and rotated logs, cross-platform checks when the project is cross-
platform, splitting files over 800 lines, and dated `LEGACY`/`DEPRECATED`
removal targets are retained. The scope gate prevents those rules from creating
unrequested side projects.

## Human requests

AskHuman handles ordinary blocking decisions when the harness attests it.
AskSecret/SSS handles secrets only through an attested opaque registered-agent
handoff. Plaintext and base64 fallback are rejected; unavailable capability is
reported rather than simulated.

## Roles and model classes

```text
L (Lead: decisions and orchestration)
├─ Adviser             5.6-sol | fable | glm5.2 | kimi k3
├─ Overseer / Critic   5.6-terra | opus | kimi 2.7 | deepseek-v4-pro
├─ Worker (~90%)       sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7
├─ Reviewer / Tester   sonnet | luna | MinimaxM3 | Deepseek v4 flash | mimo | glm-4.7
└─ Fast research       haiku | 5.4mini
```

The aliases are capability hints. Strong models make short decisions; cheaper
Workers perform long repository and implementation work.

## Harness adapters

Optional adapters translate the same core roles to Codex, OpenCode, Claude Code,
Hermes, or ZCode. Start at `adapters/manifest.yaml`. Hermes also includes the
external plugin and LHC profile bundle. Do not claim model selection, fresh
context, resume, or human-request support until a live event attests it.

## Files

- `AGENTS.md`, `CLAUDE.md` — byte-identical marked router.
- `src/common/agents/` — Lead, Worker, Adviser, Overseer, Reviewer, Tester,
  Critic.
- `src/common/profiles/` — planning, code, test, and infrastructure rules.
- `src/common/protocols/` — Worker modes, stop/rethink, workspace, and triggered
  self-improve.
- `templates/` — Full cycle, release handoff, and the single task record.
- `adapters/` — Codex, OpenCode, Claude Code, Hermes, and ZCode delivery.
- `scripts/lhc-block` — marker-only installer/updater.

Validation stays dependency-free:

```bash
python3 tests/validate.py
sh tests/test_task_states.sh
python3 -m pytest -q adapters/hermes/plugin/tests/test_plugin.py
```
