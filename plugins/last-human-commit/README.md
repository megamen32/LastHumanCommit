# Last Human Commit 1.4

An automatic engineering workflow for ordinary requests, including rough voice transcripts.
Understand the intended result, do the useful work, test it and integrate the shared result.

## What changed

Parallel writers use Git worktrees. Each working branch is pushed and gets a PR;
merge it when review and checks permit. Before finishing, fetch, merge newer work,
retest and push. A Full cycle converges the participants' changes, including nested
repositories, into one reachable green history. Foreign active work is preserved.

A blocker delays only the operation that needs it. Finish independent work first.
Agent Herder's `resume_after` can wake the original session after selected sessions
finish their native execution. A finished session is not automatically a correct result.

Shared coordination uses one atomic JSON file per message. Project worktrees share
`<primary-checkout>/.agents/shared-session/chat/`; host-wide communication uses
`~/.agents/shared-session/chat/`. Cross-host communication uses an explicit shared
address, not coincidentally identical local paths.

No mandatory setup interview, initial Overseer, three-line form or hourly ritual.
Architecture, decomposition, independent review/testing and learning tools remain
available when they improve the outcome. The complete default workflow is in
[AGENTS.md](AGENTS.md). Details: the repository's docs/V1.4.md.

## Package and installation

The native Agent Plugin is `plugins/last-human-commit`, version 1.4.0, with 22 optional
skills and small automatic-entry hooks. Use the harness's native plugin manager.
For clients whose plugin hooks are unavailable or still await trust, the package
provides a supported user-instruction bootstrap:

```sh
python3 <installed-package>/scripts/install_runtime.py \
  --runtime codex --plugin-root <installed-package> --replace-gsd-entry
```

`--runtime` also accepts `claude` and `opencode`. Only managed LHC/GSD entry blocks
are replaced; unrelated instructions are preserved and backed up. Existing GSD
skills are not deleted. Reload/start a new session to load changed instructions.

Source updates: edit the source, run `sync_skills.py`, then `python3 tests/validate.py`.
The validator runs package/source parity and all executable regressions. Runtime
installation and actual use must be verified separately from source tests.
