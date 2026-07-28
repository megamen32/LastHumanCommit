# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

Agent orchestration instruction. Grab-n-Go: a compact canon for Codex, Claude,
OpenCode, and other harnesses.

## Map

```text
Overseer ── Adviser                 intelligence
          └─ L (Lead) ── Critic     time and risk
                         ├─ Explorer (read-only)
                         ├─ Worker
                         └─ Reviewer
```

- `AGENTS.md` — the small entry canon.
- `agents/` — roles; only Lead owns the outcome and final integration.
- `protocols/` — event-triggered procedures such as STOP/RETHINK.
- `profiles/` — code and infrastructure rules loaded only when relevant.
- `templates/.agents/` — tracked-work state for work expected to exceed an hour
  or that already exceeded twenty minutes.

You do not need the rest of the canon to start; the commands below install it.

## Install

From a clone, install host instructions:

```sh
sh install.sh host
```

Install project instructions:

```sh
sh install.sh project .
```

Install into the current project with one command. This writes the shared
`AGENTS.md` block used by Codex and OpenCode plus the `CLAUDE.md` block used by
Claude, and preserves any text already in those files:

```sh
tmp=$(mktemp -d) && git clone --depth=1 https://github.com/megamen32/LastHumanCommit.git "$tmp" && sh "$tmp/install.sh" project "$PWD"; rc=$?; rm -rf "$tmp"; exit "$rc"
```

Remove only the managed blocks from the current project with one command:

```sh
tmp=$(mktemp -d) && git clone --depth=1 https://github.com/megamen32/LastHumanCommit.git "$tmp" && sh "$tmp/install.sh" uninstall project "$PWD"; rc=$?; rm -rf "$tmp"; exit "$rc"
```

Both commands are offline, dependency-free, and do not use `sudo`. Existing
`AGENTS.md`, `CLAUDE.md`, and `ROADMAP.md` content is preserved. Installer owns
only marked blocks:

```md
<!-- last-human-commit:begin -->
...
<!-- last-human-commit:end -->
```

Use `status` or `uninstall project PATH` to inspect/remove managed blocks.

## Source layout

- `src/common/` — roles, profiles, protocols, and tracked-work templates.
- `src/global/` — host entry instruction.
- `src/project/` — project entry instruction and roadmap template.
- root — maintainer meta: installer, tests, README, roadmap, and authoring rules.

The root files are not installed as agent instructions. Installed project state
is kept in `.last-human-commit/`; runtime `.agents/` is created only when
tracked work starts.

## Roadmap, tasks, kanban

`ROADMAP.md` is strategic state: ordered milestones, outcomes, statuses, stable
checkbox items, and `Proposed` for unapproved features.

`.agents/tasks/` is execution state. Use `todo-{id}.md` → `work-{id}.md` →
`done-{id}.md`; move files with `git mv` only and commit every task-file edit.
The task itself stores its ordered workflow, min-max estimate, current
executor/PID/harness/session, next action, notes, blockers, and full final
result. Confirmed bugs are individual `.agents/bugs/<id>.md` files: commit the
file immediately, then delete it in the verified fix commit.

## Validation

```sh
python3 tests/validate.py
python3 -m pytest -q tests/test_installer.py
sh -n install.sh
```
