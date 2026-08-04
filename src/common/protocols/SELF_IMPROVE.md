# Self-improve retrospective

This protocol is mandatory for L after every completed, stopped, or handed-off
task on all non-Hermes harnesses. It is a short evidence record, not a second
planning cycle and not permission to expand the user's task.

Hermes is excluded: its native post-response memory/skill review and `/learn`
flow already own this concern. Do not run a duplicate LHC loop through the
Hermes adapter.

## When and where

Before the final answer, L appends one compact entry to
`.agents/last-human-commit/self-improve.md`. Create the file if absent and
preserve earlier entries. If the project cannot be written safely, include the
same entry in the task record and state the persistence limitation in the final
answer.

Each entry has a timestamp, task or commit reference, cycle, and exactly these
four questions:

1. **What slowed or confused L?** State the observable friction, or `none`.
2. **Which instruction should change?** Name the owning LHC file and the small
   proposed change, or `none`.
3. **Which skill, MCP, or tool is missing?** State the trigger and the smallest
   useful capability, or `none`.
4. **What operation or error repeated?** State the count, evidence, and likely
   guard or automation, or `none`.

## Quality gate

- Write facts from this task, not generic wishes. Include a command, symptom,
  path, or brief evidence where available.
- Before appending, compare the candidate with recent entries. If the same
  fingerprint already exists, update its count/evidence instead of creating a
  duplicate. A fingerprint is the same friction source plus the same proposed
  remedy.
- Classify each signal as `fixed now`, `Proposed`, `needs human decision`, or
  `not actionable`. Record an observed unselected defect as minimal `todo-*`;
  only a new user product proposal belongs under `ROADMAP.md` → `Proposed`.
- Do not silently rewrite LHC, add a skill, install an MCP, or change
  harness configuration from one retrospective. Make an immediate small fix
  only when it is clearly in the user's current scope; otherwise preserve the
  concrete proposal for later selection.
- Keep the entry under 12 lines. This loop must save future time, not create
  reporting theatre.

## Entry shape

```markdown
## 2026-07-31 — <task or commit> (<cycle>)

- What slowed or confused L? <fact | none>
- Which instruction should change? <owner + proposal | none>
- Which skill, MCP, or tool is missing? <trigger + capability | none>
- What operation or error repeated? <count + evidence + guard | none>
- State: fixed now | Proposed | needs human decision | not actionable
```
