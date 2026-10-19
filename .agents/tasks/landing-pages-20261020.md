# LHC landing / GitHub Pages — 2026-10-20

- User goal: visually show actual Full Cycle and conceptual Quick path plus all current roles with descriptions automatically refreshed from Git on push; publish on GitHub Pages.
- User can try: public Pages site; switch cycles, select steps and read role descriptions linking to exact repo source.
- Decision: site separate from LHC runtime in `site/`; Python standard-library static generator reads `AGENTS.md`, `templates/FULL_CYCLE.md`, `src/common/agents/*.md` from current checkout; Pages Actions run generator for every main push. Quick is an illustrated short route, not an invented mandatory protocol. Template Full is material-decision-only.
- Scope: this isolated worktree; do not edit other active worktrees/foreign files; PR without automatic merge, per LHC.
- Initial delivery: public Pages preview at https://megamen32.github.io/LastHumanCommit/ from 87be2e4; PR #15 is open, not merged.
- Latest user correction: add a Russian translation of site copy without duplicating/translating canonical Git role documents. Preserve the approved design.
- Implemented: EN/RU header switch, browser-language default, local preference, shareable language URL, translated copy and accessibility labels, preserved cycle/stage/expanded cards, explicit original-language Git excerpts. CSS handles longer Russian labels. Build fingerprints UI assets.
- Verified: 8 passing build/dictionary/source-preservation tests; real Chromium at 320–1440 px for both languages, both five-stage cycles, seven byte-exact role definitions, keyboard tabs, persistence, blocked storage, translated network errors; no uncaught JS exceptions. Runtime, AGENTS.md and canonical role/template files unchanged.
- Next: push this scoped update to the same PR, publish the already authorized Pages preview, verify live behavior. Keep main unchanged and restore any task-owned temporary preview deployment rule after publication.
