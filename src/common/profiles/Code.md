# Code profile

Load only for code changes. This profile serves the accepted business claim; it
does not silently enlarge it.

## Business-first scope

- Trace the real production consumer and call chain before editing a nearby
  abstraction or unused adapter.
- Implement the thinnest coherent vertical change that can prove the accepted
  outcome.
- Reuse an existing mechanism when it is cheaper and adequate. Add an
  abstraction or dependency only when it reduces present total cost.
- Stop when the accepted canary and direct regression checks pass.

## Proportional engineering

Use explicit types, errors, logs, documentation, compatibility work, migration,
cleanup, and refactoring only to the degree required by changed risk, project
conventions, or the current claim. None is an automatic deliverable.

Do not initiate security, secrets, PII, permissions, ACL, database/schema,
Grafana/dashboard, observability, provider, cross-OS, deprecation, file-splitting,
or broad logging work unless the user requested it or the real canary exposes it
as the shortest necessary blocker. Report unrelated concerns without repairing
them.

Prefer the simplest readable local pattern. Build a concrete working vertical
before introducing a general abstraction. Preserve explicit existing project
conventions unless following them would block the accepted result.

Use one-off tooling only when it is cheaper than direct commands. Reusable Agent
Tools belong under `.agents/at/`; disposable diagnostics may use the project's
established ignored scratch path. Never expose secrets in tools, logs, task
records, or output.
