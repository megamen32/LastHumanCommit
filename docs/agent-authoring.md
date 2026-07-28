# Instruction authoring

Change source files only:

- `src/global/entry.md.in` — host entry.
- `src/project/entry.md.in` — project entry.
- `src/common/` — shared roles, profiles, protocols, templates.

Do not edit installed `AGENTS.md`, `CLAUDE.md`, or `.last-human-commit/` as
source. Keep entry text short. Use `@CANON_ROOT@` for shared-file paths.

Every instruction change must:

1. preserve roadmap priority;
2. add or update focused test;
3. run validator, installer tests, and `sh -n install.sh`;
4. update README when install behavior changes.

No harness hooks, plugins, network fetches, or new dependencies.
