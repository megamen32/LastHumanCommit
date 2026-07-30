# Roadmap

Priority order: top first.

## M1 — Clear reusable canon

Status: done

- [x] M1.1 Keep core instructions short.
- [x] M1.2 Add lazy roles, profiles, and protocols.
- [x] M1.3 Add file-based task tracking.
- [x] M1.4 Add roadmap and out-of-roadmap priority gate.
- [x] M1.5 Add one-line installer. Retired: copy-paste is the base interface.

## M2 — Installable distribution

Status: blocked — distribution ownership moves to Agent Fleet.

Historical installer work is retained here only as roadmap history. Live
installer artifacts are removed from LastHumanCommit.

- [x] M2.1 Split common, global, project, and meta sources.
- [x] M2.2 Add offline project and host installer.
- [x] M2.3 Add installer regression tests.
- [ ] M2.4 Validate install on Codex, Claude, and OpenCode.
- [ ] M2.5 Document rollback and upgrade.

## M3 — Text-first human/agent workflow

Status: done

- [x] M3.1 Classify direct, short, full, and emergency work.
- [x] M3.2 Require research and human selection among three plans for full work.
- [x] M3.3 Add WSFF planning views and model-class guidance.
- [x] M3.4 Add Russian mobile commit review and timed external deploy handoff.
- [x] M3.5 Make the core canon copy-paste portable and internally consistent.

## M4 — Portable role router correction

Status: active

- [ ] M4.1 Replace `CANON.md` with byte-identical `AGENTS.md` and `CLAUDE.md`.
- [ ] M4.2 Route every known role to one independently loadable prompt.
- [ ] M4.3 Restore the full provider/model role map.
- [ ] M4.4 Make L own timed self-resume, revalidation, and deployment.
- [ ] M4.5 Complete a whole-repository review and close stale contracts.

## Proposed

- [ ] Treat instruction files as installable templates with optional
  `Agents Capable Start` / `Agents Capable End` sections that a future
  harness adapter may remove when native role injection is configured.
