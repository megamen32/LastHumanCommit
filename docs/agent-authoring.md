# Authoring agent instructions

`AGENTS.md` and `CLAUDE.md` are byte-identical, marker-delimited entry routers.
`Lead.md` owns the root workflow. Every other role file is a self-contained
subagent prompt.

Keep instructions short, operational, and proportional:

- Every request, including Direct and Short work, creates one Markdown task file
  under `.agents/tasks/` and records an estimate; rename the same file from
  `work-*` to `done-*` on completion. Never maintain a duplicate kanban.
- Overseer is mandatory for every task and Critic gates release. Both receive
  the raw user context, independently reconstruct the current user priority,
  obey only the user, and bind L with stops or unanswered questions. Add other
  roles only for bounded work required by the selected outcome.
- Full work preserves research, three initial plans in Russian, human selection,
  WSFF views, outcome-and-scope review, tests, commit, and L-owned timed resume.
- `YAGNI -> Normal -> Ultimate` defines delivery layering after selection, not
  the initial plan order.
- Use execution updates in English and give the final answer in Russian.
- Every role runs `uptime` and sends a progress checkpoint after at most 30
  tool calls or shell commands, or 30 elapsed minutes when measurable,
  whichever comes first.
- Unsolicited secondary work is forbidden unless the user confirms it or it is
  a minimal safe-canary prerequisite for the selected outcome.
- The router names roles and paths but does not repeat their instructions.
- L sends a role name to a child and does not load that role prompt itself.
- Profiles supplement an assigned role; protocols load only when triggered.
- Templates store decisions and state, not a second normative workflow.
- `profiles/Planning.md` owns Full-work estimate and re-decomposition rules.
- `protocols/SELF_IMPROVE.md` owns the non-Hermes end-of-task retrospective;
  it records concrete friction and proposals without silently changing LHC.
- `protocols/SHARED_WORKTREE.md` owns collaboration safety: no cleanup of
  foreign edits, five-minute active-edit protection, and final integration
  review by L.

When changing instructions:

1. Update the one file that owns the rule.
2. Align only direct references and record schemas.
3. Keep validation literal, dependency-free, and readable in one sitting.
4. Run `python3 tests/validate.py` and `git diff --check`.

The marker lines are an ownership boundary:

```html
<!-- last-human-commit:begin -->
… Last Human Commit owns only this content …
<!-- last-human-commit:end -->
```

When applying LHC to a project, preserve every byte outside the block.
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
