# Last Human Commit 1.5

An automatic engineering workflow for ordinary requests, including rough voice transcripts.
Understand the intended result, do the useful work, test it and integrate the shared result.

## What changed

Ordinary tasks retain their class, explicit business canary and applicable delivery
stages in existing session state. Independent native source-backed review can close
the outcome; testing can complete with a product defect. See
[the outcome contract](src/common/protocols/OUTCOME_CONTRACT.md).

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

Design uses three passes: working solution, ideal version, then the smallest
complete implementation preserving roughly 80% of useful value. These are not
three builds or approval rounds; the method is separate from a three-line form.

No mandatory setup interview or initial Overseer. Hourly original-goal direction
review and 120-minute workflow improvement are mandatory. Fresh Zero Knowledge
groups accept ready major milestones, not every hour.
Architecture, decomposition, independent review/testing and learning tools remain
available; scheduled inspection is required even when the current plan looks correct. The complete default workflow is in
[AGENTS.md](AGENTS.md). Details: [1.4 changes](docs/V1.4.md).

## Package and installation

The native Agent Plugin is `plugins/last-human-commit`, version 1.5.0, with 23 optional
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

## 1.4.3 clarification

Define a tangible user/consumer result before code: who needs what, before/after
and where to try it. Start bug TDD immediately. Hourly direction reviews remain;
Zero Knowledge groups accept major outcome milestones (roughly 3 hours), not
every hour or edit. Varied realistic personas leave detailed positive/negative
feedback. Preserve raw feedback, fix actual obstacles and keep preferences
without automatically expanding scope. See docs/V1.4.3.md in the source repository.

OpenCode 2 uses the native `opencode/lhc-v2.ts` entrypoint; V1 retains
`opencode/lhc-time-guard.ts`. OpenChamber shares the connected server installation.
