# Agent Canon

Public canonical source for agent orchestration. The always-loaded core is kept
under 800 Unicode characters; role, event, and domain instructions are loaded
only when relevant. The full directory must never be concatenated into one
prompt.

## Layout

- `AGENTS.md` — 790-character dispatch and interaction core.
- `agents/` — L, Explorer, Worker, Reviewer, Хлыст, Adviser, Critic.
- `protocols/` — event-triggered procedures such as STOP/RETHINK.
- `profiles/` — code and infrastructure rules loaded only for matching work.
- `templates/.agents/` — runtime state used only when work is expected to exceed
  one hour or has already exceeded twenty minutes. Tracked work uses
  `.agents/tasks/todo-{id}.md` → `wip-{id}.md` → `done-{id}.md`; state
  transitions are `git mv` only.
- `tests/validate.py` — dependency-free structure and size guard.

Runtime logging is intentionally quiet: every agent records only start and end;
there are no heartbeat messages. Detailed work stays in subagent results,
commits, evidence, and L's cumulative Overseer brief.

## Canonical installation

Target repository: `megamen32/agent-canon`.

Clone once, then expose the canonical files to each harness through symlinks or
its native agent configuration. Harness adapters should reference these files,
not fork their text. Keep project-specific topology and secrets in the project's
own instruction files.

For Codex user-level files, one possible layout is:

```sh
git clone git@github.com:megamen32/agent-canon.git ~/.agent-canon
ln -sfn ~/.agent-canon/AGENTS.md ~/.codex/AGENTS.md
ln -sfn ~/.agent-canon/agents ~/.codex/agents
ln -sfn ~/.agent-canon/protocols ~/.codex/protocols
ln -sfn ~/.agent-canon/profiles ~/.codex/profiles
```

For tracked work only:

```sh
cp -R ~/.agent-canon/templates/.agents ./.agents
```

## Validation

```sh
python3 tests/validate.py
```

Rigid rules protect P0, retry limits, oversight cadence, irreversible
boundaries, and completion evidence. Implementation advice remains contextual:
Overseer and Critic create mandatory decision gates without making a
context-poor proposed solution blindly binding.

## Token footprint (tiktoken, cl100k_base)

Short description: a compact, lazy-loaded canon for agent orchestration. The always-loaded core (`AGENTS.md`) is the only file carried in every prompt; roles, profiles, and protocols load on demand. Total library: 15,349 chars / 3,427 tokens across 11 files.

| File | chars | tokens |
| --- | ---: | ---: |
| AGENTS.md | 790 | 218 |
| agents/Adviser.md | 982 | 213 |
| agents/Critic.md | 1332 | 287 |
| agents/Explorer.md | 1193 | 256 |
| agents/Lead.md | 4480 | 1029 |
| agents/Overseer.md | 1492 | 356 |
| agents/Reviewer.md | 1049 | 228 |
| agents/Worker.md | 1101 | 230 |
| protocols/STOP_RETHINK.md | 1277 | 270 |
| profiles/Code.md | 385 | 80 |
| profiles/Infrastructure.md | 1268 | 260 |
| TOTAL | 15349 | 3427 |
