# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical, marker-delimited entry routers.
`Lead.md` owns the root workflow. Every other role file is a self-contained
subagent prompt.

Keep instructions short, operational, and proportional:

- Direct, Short, and Emergency work remain fast.
- Full work preserves research, three plans, human selection, WSFF views,
  implementation, whole-repository review, tests, commit, Russian summary, and
  L-owned timed resume.
- The router names roles and paths but does not repeat their instructions.
- L sends a role name to a child and does not load that role prompt itself.
- Profiles supplement an assigned role; protocols load only when triggered.
- Templates store decisions and state, not a second normative workflow.
- `profiles/Planning.md` owns Full-work estimate and re-decomposition rules.

When changing instructions:

1. Update the one file that owns the rule.
2. Align only direct references and record schemas.
3. Keep validation literal, dependency-free, and readable in one sitting.
4. Run `python3 tests/validate.py` and `git diff --check`.

The marker lines are an ownership boundary:

```html
<!-- last-human-commit:begin -->
… LastHumanCommit owns only this content …
<!-- last-human-commit:end -->
```

When applying the canon to a project, preserve every byte outside the block.
Use `scripts/lhc-block` with an explicit source and target; it must fail closed
for missing, duplicate, nested, reversed, or malformed marker pairs. A project
may have different project-owned text in `AGENTS.md` and `CLAUDE.md`; never make
installed targets byte-identical by overwriting that text.

Do not add a harness-specific profile until a live child test proves the role,
actual model, fresh-context boundary, and returned result. A profile cannot
force a harness to change a full-history fork. Put proven delivery details in
`adapters/<harness>/`; keep the role contract in `src/common/agents/`.

Do not expand `scripts/lhc-block` into an installer, daemon, hook, generator,
or harness adapter. It owns only one explicit text block in one explicit file;
harness-specific delivery belongs in the modular `adapters/` layer.
