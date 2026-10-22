---
name: last-human-commit
description: Automatically handle normal engineering requests, including rough voice transcripts, from intent to tested delivery. Use for code, architecture, bugfixes and parallel project work; the user does not need to invoke a command.
---

# Last Human Commit

This skill is the router. Read the LHC package's own `AGENTS.md` once, before any
action: it carries the Lead, Worker and Overseer contract, the routing, the time
boxes and the language policy. That file ships at the LHC package root, two
directories above this `SKILL.md`; in the source repository it is `AGENTS.md` at
the repository root. It is **not** the `AGENTS.md` of the project you happen to be
working in — a project file describes the project, the package file describes how
you work, and a session that read only the project file does not know what a Lead
is.

Your harness may inject the package `AGENTS.md` at session start. If it does not
— some harnesses have no plugin hooks — read it yourself, and keep the time-only
checkpoints alive with the package's own tools:

```sh
# the package root is the directory two levels above this SKILL.md
printf '{"cwd":"<project dir>","session_id":"<native session id>"}' \
  | python3 "<package root>/tools/lhc_entry.py" --session
```

The same tool with `--event PostToolUse --heartbeat-only` prints the 30-minute
time-only reminder in a harness that runs no hooks. Both are safe to call: they
only report elapsed time and point at the next command.

Every decomposed objective keeps its machine-readable task graph and renders the
plan dashboard (`common/protocols/TASK_GRAPH.md`): the user sees what is done, what runs now,
what is blocked, the rough finish and the parallelism without asking. The package's
router is the workflow; load other skills only when the task needs that method.
Lead only coordinates. Assign every execution step to a Worker, even when small; use an independent allowed-model Reviewer only when the claim and risk justify it. Workers do not recursively hire.
Already delegated no-delegation leaf work uses native tools without recursive hiring.
Preserve the task through compaction, isolate concurrent writers and integrate
one published dev history into the explicit permitted target; no PR per worker.
There is no mandatory setup interview or second GSD workflow.
