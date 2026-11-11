# Code

Trace the real caller and change the smallest coherent part that produces the requested behavior. Reuse the project's existing patterns and mechanisms. Add an abstraction, dependency or compatibility layer when the current task needs it.

Match types, errors, logs and documentation to the changed behavior and the project's conventions. Keep adjacent cleanup separate unless it is needed for the fix.

Use a regression check for the failure being repaired and a real-client check for the user-facing result. Put disposable helpers and builds under the project's ignored `.tmp/`; reusable agent tools belong in `.agents/at/`.

See `src/common/protocols/CODE.md` for project conventions and test coverage markers.
