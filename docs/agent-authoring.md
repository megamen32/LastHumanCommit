# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical entry routers. `Lead.md` owns the
root workflow. Every other role file is a self-contained subagent prompt.

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

Do not add a harness-specific profile until a live child test proves the role,
actual model, fresh-context boundary, and returned result. A profile cannot
force a harness to change a full-history fork.

Do not add an installer, daemon, hook, or generator to solve an instruction
change. Harness-specific compilation belongs in a future roadmap item.
