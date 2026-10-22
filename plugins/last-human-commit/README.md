# Last Human Commit 1.5

An automatic engineering workflow for ordinary requests, including rough voice transcripts.
Understand the intended result, do the useful work, test it and integrate the shared result.

## What changed

Operating instructions, internal planning, new task records and agent/tool messages
use English. User answers use the user’s language; original messages, localized
fixtures and raw feedback retain their language.

Native hooks load instructions at session start or context restoration and issue
time-only 30-minute planning and hourly goal-check reminders.
They do not classify conversation text, mutate task contracts, or block completion.
Every 30 minutes the Lead updates the task note with roughly 15-minute steps,
initial estimate versus actual effort, dependencies and parallel delegation.
The Lead owns the goal, applicable checks and delivery; existing explicit contract
and review commands remain available without automatic conversation parsing. See
[the outcome contract](common/protocols/OUTCOME_CONTRACT.md).

Independent native review remains bound to the reviewer's current task assignment.
When work is genuinely reassigned, use a new native worker session under the existing
mandate and assign the existing reviewer again with the fresh outcome ID and full
current goal. Old reports remain historical and cannot be reused for the new scope.

Agent Herder relays are marked as `agent-relay` transport origin; unmarked origin
remains `unknown`. This marker preserves provenance and does not grant authority.

Parallel writers use Git worktrees. Ready work converges into the explicitly permitted published dev history; PR per
worker is optional. Merge only with authorization, review and green checks. Before finishing, fetch, merge newer work,
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
[AGENTS.md](AGENTS.md). Details: docs/V1.4.md in the source repository.

## Package and installation

The native Agent Plugin is `plugins/last-human-commit`, version 1.5.30, with the full
optional skill set (validated by `scripts/validate.py`), instruction-only startup hooks
and time-only reminders. Use the harness's native plugin manager.
For clients whose plugin hooks are unavailable or still await trust, the package
provides a supported user-instruction bootstrap:

```sh
python3 <installed-package>/scripts/install_runtime.py \
  --runtime codex --plugin-root <installed-package> --replace-gsd-entry
```

`--runtime` also accepts `claude` and `opencode`. Only managed LHC/GSD entry blocks
are replaced; unrelated instructions are preserved and backed up. Existing GSD
skills are not deleted. Reload/start a new session to load changed instructions.

Source updates: edit the source, run `scripts/sync_skills.py`, then `python3 tests/validate.py`
in the source repository.
The validator runs package/source parity and all executable regressions. Runtime
installation and actual use must be verified separately from source tests.

## 1.4.3 clarification

Define a tangible user/consumer result before code: who needs what, before/after
and where to try it. Start bug TDD immediately. Hourly direction reviews remain;
Zero Knowledge groups accept major outcome milestones (roughly 3 hours), not
every hour or edit. Varied realistic personas leave detailed positive/negative
feedback. Preserve raw feedback, fix actual obstacles and keep preferences
without automatically expanding scope. See docs/V1.4.3.md in the source repository.

OpenCode loads its normal AGENTS.md and skill discovery, and the native LHC plugin
(`opencode/lhc-v2.ts`, registered by `scripts/install_runtime.py` into the OpenCode
plugin directory) injects the current installed AGENTS.md into the system context,
reports the time-only 30/60-minute reminders at tool and idle boundaries, and
re-injects the AGENTS.md and bounded current-handoff.md pointers after compaction.
It does not review, gate, approve or evaluate a diff. Hermes retains only
explicit role-selection middleware, without a recurring lifecycle observer.
Codex/Claude/ZCode load concise instructions and time-only 30/60-minute reminders.
The reminders run at the next tool boundary, not through a background scheduler.
Native manager installation does not prove that every existing chat has reloaded
its registered hooks; verify the loaded version when diagnosing an old chat.
