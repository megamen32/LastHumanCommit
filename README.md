# Last Human Commit

<img width="1672" height="941" alt="Last Human Commit role map" src="https://github.com/user-attachments/assets/7b259f64-50c1-45a4-af27-07a5101d8120" />

A small human/agent workflow canon. It is text, not a framework.

## Use

Copy the complete contents of [`CANON.md`](CANON.md) into the instruction file
your harness already reads. That is the base product and is enough to work.

Copy optional role or record templates only when they help. A project may adapt
formatting and paths, but must preserve the decisions in `CANON.md`.

LastHumanCommit does not install, synchronize, schedule, deploy, or run a
service. Agent Fleet or another external adapter owns those environment-specific
jobs.

## Model map

```text
L (Lead)
├─ Adviser / strategy        fable | sol
├─ Critic / review           opus | terra
├─ Worker (about 90%)        sonnet | luna
└─ Explorer (read-only)      haiku | 5.4mini
```

The strongest models are short strategic advisers, not long-running workers.
Names are capability hints; unavailable aliases must not block the workflow.

## Text map

- `CANON.md` — self-contained copy-paste contract.
- `src/common/agents/` — optional role expansions.
- `src/common/profiles/` — optional code, test, and infrastructure guidance.
- `src/common/protocols/` — optional recovery guidance.
- `src/common/templates/.agents/` — optional task and bug records.
- `templates/FULL_CYCLE.md` — planning and human-selection record.
- `templates/RELEASE_HANDOFF.md` — stable boundary for Agent Fleet or another
  deploy adapter.

Optional tracked task state is `todo -> work -> done`. The workflow remains
usable without task files for direct and short work.

## Validate

The only routine check is intentionally simple and dependency-free:

```sh
python3 tests/validate.py
```
