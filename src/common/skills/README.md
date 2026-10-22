# Skill catalog — load on demand

This directory is the single canonical source for every LHC skill. The repo-root
`skills/` tree and every copy inside `plugins/last-human-commit/` are generated
projections of it; edit the skill here and regenerate, never edit a copy.

| Skill | Use when | Typical owner |
| --- | --- | --- |
| [architecture-design](architecture-design/SKILL.md) | Resolve costly design uncertainty, prove boundaries and simplify into complete outcomes before dispatch | Lead / independent challenger |
| [model-availability](model-availability/SKILL.md) | Verify catalog, read-only quotas and assignment capabilities | Lead / council / focus owner |
| [model-routing](model-routing/SKILL.md) | Select/update models using capability and accepted-result cost | Lead / Overseer |
| [decompose-and-dispatch](decompose-and-dispatch/SKILL.md) | Build coherent tasks, parallel lanes and integration joins | Lead |
| [task-decomposition](task-decomposition/SKILL.md) | Plan the same leaves as a machine-readable task graph with a rendered dashboard | Lead |
| [plan-artifacts](plan-artifacts/SKILL.md) | Create the task record, the machine-readable graph, the report and the dashboard in one pass, with the exact schema and the check that proves they agree | Lead / Worker |
| [user-testing](user-testing/SKILL.md) | Attempt an actual user goal without implementation context | Tester |
| [focus-groups](focus-groups/SKILL.md) | Diversify user goals; fix and retest observed obstacles | Lead + Testers |
| [council](council/SKILL.md) | Resolve a difficult choice with independent strong models | Lead + Advisers |
| [challenge-decision](challenge-decision/SKILL.md) | Independently test the reasoning behind a proposal/synthesis | Adviser / Critic alias |
| [business-delivery](business-delivery/SKILL.md) | Prove the least-cost path to an accepted business result | Lead |
| [improve-workflow](improve-workflow/SKILL.md) | Turn experience into a tested, retrievable, reused capability | Lead + Worker |
| [maintainer-review](maintainer-review/SKILL.md) | Before a PR into a repository you do not own: that project's maintainer reads the project and the diff and returns a hard critique | Lead + Maintainer |
| [mini-improvement-loop](mini-improvement-loop/SKILL.md) | Turn reviewed defect lists into a pushed, surface-proven result | Lead |
| [planning](planning/SKILL.md) | Choose the least-cost route to the next real canary | Lead |
| [release](release/SKILL.md) | Run a controlled consequential release action | Lead |
| [real-use-testing](real-use-testing/SKILL.md) | Prove a user-facing result on the real surface with observed evidence | Tester |
| [worker-research](worker-research/SKILL.md) | Trace real production paths, locate symbols and ownership, hand back a decision-ready route | Worker |
| [worker-bugfix](worker-bugfix/SKILL.md) | Reproduce, localize and fix one bounded behavior failure with a fast red regression | Worker |
| [worker-code](worker-code/SKILL.md) | Write the smallest coherent code change on the real business path | Worker |
| [bugfix-tdd](bugfix-tdd/SKILL.md) | Compatibility alias for older assignments naming bugfix TDD | Worker |
| [feature-implementation](feature-implementation/SKILL.md) | Compatibility alias for older assignments naming feature implementation | Worker |
| [lhc-rollout](lhc-rollout/SKILL.md) | Roll out a committed release to the local and SSH Fleet hosts | Lead |
| [lhc-update-agents](lhc-update-agents/SKILL.md) | Update the shared sources, generate and validate the native plugin | Lead |
| [last-human-commit](last-human-commit/SKILL.md) | Handle a normal engineering request end to end | Lead |

These descriptions are the selection index, not mandatory steps. A role
loads only the chosen methods and useful references. Preserve the native adapter's
skill discovery when available; otherwise give explicit file references. Do not
copy every skill into every agent's system prompt.

## Path convention

Skill text points at neighbours in three ways, and each one resolves in every
shipped layout:

- `../<skill>/...` — a sibling skill in the same skills directory.
- `"<tools>/..."` — the tools directory of the active package root: `common/tools/`
  in the installed package, `src/common/tools/` in a source checkout and in the
  repository-root projection of the skills tree. Write the path this way: a
  `../../tools/...` path breaks in the repository-root projection, and a literal
  `src/common/...` path breaks in the installed package.
- `common/protocols/...` and `AGENTS.md` — relative to the active package root,
  the directory that holds `common/` and `AGENTS.md`.
