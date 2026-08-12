# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

Last Human Commit is a business-first, least-cost agent workflow. It keeps the
next real user result ahead of process, chooses the cheapest sufficient agent
and proof, and adds governance only when a concrete risk justifies its cost.

## Core workflow

1. Define what the user needs now, including an accepted MVP/80/20 Definition of
   Done.
2. Trace the actual production consumer path before choosing an implementation
   surface.
3. Name the shortest real business canary and cheapest sufficient proof.
4. Let Lead work directly when delegation costs more; otherwise use the lowest
   sufficient Worker and preserve its useful context.
5. Treat every 20 active minutes as a reporting/control checkpoint, not an agent
   lifetime limit. Continue, redirect/resume, or consult Overseer; cancel only
   exceptionally.
6. Use the harness wait/join mechanism for required children. A timeout is an
   observation, never proof of terminal state.
7. Invoke Overseer, Adviser, Critic, Reviewer, or Tester only when expected
   decision/risk-reduction value exceeds delay and token cost.
8. Match evidence to the claim and stop when that claim is proven.

Overseer, Adviser, Critic, Reviewer, and Tester are risk-triggered. Gates are
tools, not milestones. Full work may have one, two, or three genuine plans; LHC
does not manufacture options, double testing, per-wave reviews, or hardening
loops merely because a task is important.

## State and workspace

Use one compact `.agents/tasks/` record when recovery, coordination, or audit
value justifies it. Update it in place. Legacy `todo/work/done` lineages remain
valid, but new work does not require snapshot copies or snapshot commits.

Routine work stays in the primary checkout. Preserve foreign edits and stage
only task-owned paths. Never silently create/switch/merge/delete a branch or
worktree. A user-requested worktree lives only at
`<primary-project-root>/.worktrees/<task-slug>`.

## Human and secret boundaries

The active harness owns approval policy. Ordinary missing decisions use an
attested human-request capability. Secrets use only attested opaque
AskSecret/SSS registered-agent handoff; plaintext and base64 fallbacks are
rejected.

## Install the portable router

Copy `src/common/` and `templates/` into a project, then use the explicit
marker-only helper. It preserves project text outside one canonical block:

```sh
scripts/lhc-block init AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block init CLAUDE.md /path/to/project/CLAUDE.md
scripts/lhc-block apply AGENTS.md /path/to/project/AGENTS.md
scripts/lhc-block apply CLAUDE.md /path/to/project/CLAUDE.md
```

Optional harness adapters live under `adapters/`; canonical skills live under
`skills/` and are mirrored into `plugins/last-human-commit/skills/`.

Validation:

```bash
python3 -m pytest -q tests/test_business_first_contract.py
python3 tests/validate.py
sh tests/test_task_states.sh
python3 -m pytest -q adapters/hermes/plugin/tests/test_plugin.py
```
