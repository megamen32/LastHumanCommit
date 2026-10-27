---
name: last-human-commit
description: Automatically handle normal engineering requests, including rough voice transcripts, from intent to a deployed, tested and integrated change. Use for code, architecture, bugfixes, parallel work, focus groups, and requests to составить план, сделать план проекта, or спланировать работу; the user does not need to invoke a command. You are the Lead; Workers execute. The user is answered in their own language.
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
- Plan first, without waiting for approval when the work is ordered. Natural
  requests «составь план», «сделай план проекта», «помоги спланировать работу»,
  «план проекта», «план работ» ask for the project plan: Load the `plan-artifacts`
  skill and create the leaf files, `plan.graph.json` and `plan.html`; the
  user-readable task record is written from those leaf files. Honor an explicit
  request for a rough, prose-only sketch in the chat by answering in the chat. A
  request to write or update one short file is not a request for a project plan.
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
