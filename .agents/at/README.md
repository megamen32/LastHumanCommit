# `.agents/at/` — Agent Tools scratch space

This is the only project-local scratch directory for one-off agent scripts.
Do not create a separate top-level `.at/`, `.lhc/`, or another agent-state
root. Keep each script reproducible and give it a short README or usage
comment.

Why: one-off scripts often become reusable Agent Tools or MCPs, so keeping them
under the single `.agents/` root makes them discoverable and promotable.
