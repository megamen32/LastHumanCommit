# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical marker-delimited routers.
`Lead.md` owns orchestration. Every other role file is a self-contained child
prompt.

## Non-negotiable shape

- One request uses one Markdown `.agents/tasks/work-*` file from start to finish. Rename
  that same file to `done-*`; never add a duplicate kanban, spec, ledger,
  recovery file, or review package.
- L is an orchestrator by default. It may execute only an obvious <=5-minute Direct
  action. Short and Full repository search and code belong to Worker.
- There is no Explorer role. Worker uses `mode: research` and
  `mode: implement`; implementation names `bugfix/TDD` or `feature`.
- Every Worker assignment has one acceptance gate and maximum <=20 active
  minutes. Split larger work before dispatch. A whole task above one hour must
  be an explicit graph of understood <=20-minute slices.
- Estimates are `minimum / maximum`. Keep the initial range immutable. A maximum
  overrun requires a fresh Overseer audit before continuation.
- Overseer is mandatory for every task and fresh/no-history every time. Full
  invokes it after research, after each implementation wave, and before release.
  Critic independently gates release or irreversible action.
- Full is reserved for researched work over 30 minutes with material product,
  architecture, migration, or expensive-wrong-path impact.
- Full must preserve three Russian plans, first selection, full technical
  preview, and second explicit approval. Never remove call-stack tree, file-tree
  diff, key signatures, pseudocode, migration description, canary, or execution
  graph from that human layer.
- `YAGNI -> Normal -> Ultimate` is delivery order after selection, not the plan
  presentation order.
- Plans are Russian, execution updates English, final answer Russian.
- Silence never authorizes deploy, rollback, destructive action, branch, or
  worktree operations.

## Workspace ownership

Routine work stays in the primary checkout. At startup, inspect worktree and
branch identity. An auxiliary worktree, detached HEAD, or non-default branch is
reported in the first visible update.

Do not create a branch/worktree for cleanliness or isolation. With explicit
human authorization, a new worktree may exist only under
`<primary-project-root>/.worktrees/<task-slug>`. The repository must ignore
`.worktrees/`. `protocols/SHARED_WORKTREE.md` owns concurrent-edit safety.

## Prompt ownership

- The router names roles and paths but does not duplicate their workflows.
- L sends one role and mode to a child; it does not load that role into its own
  context.
- Profiles supplement an assigned role. Protocols load only on their trigger.
- Templates store the same task's decisions and evidence; they are not a second
  normative workflow.
- `profiles/Planning.md` owns estimate, decomposition, and model-routing rules.
- `profiles/Code.md` owns code-as-docs, structured/rotated logs,
  cross-platform rules, file-size limits, and explicit legacy removal dates.
- Adapter manifests name `subagent_instructions_template`. Harness syntax stays
  in adapters; portable behavior stays in common roles/protocols.
- Worker research may resume into implementation when supported. Independent
  gates must never resume or fork L's history.

## Changing instructions

1. Change the file that owns the rule.
2. Align only direct references, templates, adapters, and validation.
3. Keep the runtime prompt concise; tests may enforce the invariant instead of
   repeating prose everywhere.
4. For instruction-only changes, review the diff, run `git diff --check`, and
   run `python3 tests/validate.py`.

The marker lines are the ownership boundary:

```html
<!-- last-human-commit:begin -->
… Last Human Commit owns only this content …
<!-- last-human-commit:end -->
```

Preserve every byte outside the block. `scripts/lhc-block` remains a narrow
explicit marker utility, not an installer, daemon, generator, scheduler, or
harness adapter.
