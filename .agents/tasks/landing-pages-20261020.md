# LHC landing / GitHub Pages — 2026-10-20

- User goal: visually show actual Full Cycle and conceptual Quick path plus all current roles with descriptions automatically refreshed from Git on push; publish on GitHub Pages.
- User can try: public Pages site; switch cycles, select steps and read role descriptions linking to exact repo source.
- Decision: site separate from LHC runtime in `site/`; Python standard-library static generator reads `AGENTS.md`, `templates/FULL_CYCLE.md`, `src/common/agents/*.md` from current checkout; Pages Actions run generator for every main push. Quick is an illustrated short route, not an invented mandatory protocol. Template Full is material-decision-only.
- Scope: this isolated worktree; do not edit other active worktrees/foreign files; PR without automatic merge, per LHC.
- Status: worktree created, source verified. Next: implement, test, push and PR; if possible publish approved demo and validate URL.
