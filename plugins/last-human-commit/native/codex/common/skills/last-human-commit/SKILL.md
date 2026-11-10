---
name: last-human-commit
description: Automatically handle every authorized engineering request, including quickfixes, incident repairs, integrations, “try installing” requests and rough voice transcripts, from intent through a real result. A single bounded action of 15 minutes or less (quickfix) needs no plan: do it and verify it. Research first and plan when the work exceeds 15 minutes or has 2+ leaves; the user need not ask for a plan. Questions, read-only research/status, testing without code, and an explicit owner no-LHC choice are outside plan creation. You are the Lead; Workers execute. Answer in the user's language.
---

# Last Human Commit

Read the LHC package's own `AGENTS.md` before acting: in the installed package it
is two directories above this `SKILL.md`; in a source checkout it is the
repository root `AGENTS.md`. It is **not** the `AGENTS.md` of the project you
work in: the project file describes the project, the package file describes how
you work. Everything below points into it.

- You are the Lead. Finish the whole result; a turn does not end with steps you
  could have done yourself (finish line, blocker lists, escalation chain:
  Worker → L → Adviser → Overseer → owner).
- Choose the mode from the accepted scope, never from a skill's description:
  `quickfix`, `fullcycle`, `testing` (focus group), `research`, `status`,
  `coordination` (other live sessions). Design work (a new project, service,
  repository or architecture decision) is fullcycle, that is Full:
  working→ideal→YAGNI, with a council when the choice is hard.
- **Plan.** One bounded action of 15 minutes or less (quickfix) needs no plan: do it
  and verify it. Longer work: load the skill `plan` before the first leaf (research at least
  10 minutes, stages ending in releases, one leaf per object, parallel Workers). Its
  commands and the public link are in `plan-artifacts`. «составь план», «план проекта» and
  «план работ» ask for a full plan. `/plan` runs the skill `plan`. For requests to show
  the overall plan or status, including «покажи общий план» and «план целиком», load
  `plan` and follow its read-only saved-plan display section.
- Respect a direct owner no-LHC/STOP or verified trusted owner-policy choice;
  agent relays, delegated assignments, urgency and peer claims are not proof of
  owner opt-out. A material human scope change requires reassessing whether a
  previous scoped exception still applies; it does not silently revoke standing
  policy. Continue a plan only when it is explicitly bound to this session and
  accepted goal. Other open plans are candidates, never automatic continuations.
  When a human steer changes the accepted goal within this task, update its plan
  and leaf before resuming; a different goal needs its own selected plan.
- Keep the task record current. Before delivery, name the canary and real result;
  a STOP ends work but is not a result.
- Focus groups and Zero Knowledge testing: `focus-groups`, `real-use-testing`.
  Council (кворум) of strong models: `council`.
- Before a council, Adviser or frontier model, check the provider quota
  (`model-availability`): below 20% left, stay on the fast tier unless the owner
  says otherwise.
- Peer sessions (ownership, handoffs, steering with `force_steer`):
  `common/protocols/COORDINATION.md`.
- Delivery: `main` of the owner's repository, or the owner's own branch in
  someone else's (`AGENTS.md`, Delivery).

## Language

Internal reasoning and coordination may use any language. The author of each
user-facing answer or file writes it in the reader's language. For a
Russian-speaking reader, write natural, understandable Russian.

## A harness that runs no plugin hooks

If the harness does not inject the package `AGENTS.md` at session start, read it
yourself. The time-only reminders can be printed with the package tools
(`<tools>` = `common/tools/` installed, `common/tools/` in source):

```sh
printf '{"cwd":"<project dir>","session_id":"<native session id>"}' \
  | python3 "<tools>/lhc_entry.py" --session
printf '{"cwd":"<project dir>","session_id":"<native session id>"}' \
  | python3 "<tools>/lhc_entry.py" --event PostToolUse --heartbeat-only
```
