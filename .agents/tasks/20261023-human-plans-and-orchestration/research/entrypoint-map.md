# Canonical entrypoint map

Canonical editable sources are the repository-root `AGENTS.md` and `PRODUCT-PHILOSOPHY.md`, shared `src/common/`, and harness-specific `adapters/`. `CLAUDE.md` is generated from `AGENTS.md`; `plugins/last-human-commit/` is the delivery package, with its `common/`, `native/codex/`, tools, skills, and installed loaders generated from canonical sources. This follows root `AGENTS.md` and `plugins/last-human-commit/scripts/sync_skills.py`.

## Mode and shortcut rules

- Product definitions: root `PRODUCT-PHILOSOPHY.md` (quickfix/fullcycle semantics).
- Native routing/Lead ownership: root `AGENTS.md` and `src/common/agents/Lead.md`.
- Runtime classifier and outcome state: `src/common/tools/lhc_outcome.py` (`ENGINEERING`, task-class inference and stages), projected to package tools.
- Native startup/entrypoint: `src/common/tools/lhc_entry.py`, projected to package tools.
- Assigned-leaf/delegation shortcut: `src/common/skills/last-human-commit/SKILL.md` and `src/common/skills/decompose-and-dispatch/SKILL.md`; root `AGENTS.md` says an assigned no-delegation leaf uses native self-check and does not inherit parent PASS.

## Mandatory plan and tester rules

- Human plan format: `src/common/protocols/PLAN_REPORT.md`.
- Graph schema and dependency/wave rules: `src/common/protocols/TASK_GRAPH.md`.
- Decomposition procedure: `src/common/skills/task-decomposition/SKILL.md`.
- Artifact generation procedure: `src/common/skills/plan-artifacts/SKILL.md`.
- Real consumer tester requirement: `src/common/skills/real-use-testing/SKILL.md`; independent user journeys: `src/common/skills/focus-groups/SKILL.md`.
- Contradiction risk: generated package/native Codex copies plus root/CLAUDE copies can drift; edit canonical sources first and run `python3 plugins/last-human-commit/scripts/sync_skills.py` before the package validators.

## Generated outputs and command

For a record `<record>` under `.agents/tasks/<objective>/`, canonical outputs are `plan.graph.json`, `plan.html`, and `plan.md`. Use:

```sh
python3 src/common/tools/lhc_grid.py export <record> -o <objective>/plan.graph.json
python3 src/common/tools/lhc_grid.py render <objective>/plan.graph.json --out-dir <objective>
python3 src/common/tools/lhc_grid.py check-plan <record> <objective>/plan.graph.json
```

The native package is generated/published through the current package's `lhc-update-agents` workflow after source checks; installed package/readback is separate evidence from source or tests.
