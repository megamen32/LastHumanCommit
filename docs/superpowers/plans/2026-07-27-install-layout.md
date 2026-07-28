# Installable Canon Layout Implementation Plan

> **For agentic workers:** Use this plan task-by-task. Keep changes small and test each installer behavior.

**Goal:** Make Last Human Commit installable on a host and inside a project without harness-specific hooks or plugins.

**Architecture:** Keep maintainer meta at root. Move distributed material under `src/common`, `src/global`, and `src/project`. POSIX `install.sh` copies payloads and manages one marked block in entry files.

**Tech Stack:** POSIX `sh`, Python standard library tests.

## Global Constraints

- Offline and dependency-free.
- No `sudo`, hooks, plugins, or harness API.
- Preserve user files outside managed markers.
- Never overwrite existing project `ROADMAP.md`.
- Host and project install work independently.

### Task 1: Source layout

**Files:** move distributed docs to `src/common`, `src/global`, `src/project`; keep root README, roadmap, tests, and maintainer AGENTS.

- [ ] Add global and project entry templates.
- [ ] Add common role/profile/protocol/template payload.
- [ ] Update references and validator paths.
- [ ] Run `python3 tests/validate.py`.

### Task 2: Installer RED/GREEN

**Files:** `install.sh`, `tests/test_installer.py`.

- [ ] Add failing tests for empty install, idempotency, marker preservation, existing roadmap preservation, and malformed target refusal.
- [ ] Run tests and confirm failure because installer is absent.
- [ ] Implement `host`, `project`, `status`, and `uninstall`.
- [ ] Run tests and `sh -n install.sh`.

### Task 3: Meta docs

**Files:** root `README.md`, root `AGENTS.md`, `docs/agent-authoring.md`.

- [ ] Explain source-of-truth and generated-file rules.
- [ ] Document host/project paths and safe installer commands.
- [ ] Document how agents may change instructions.
- [ ] Run full validator and installer tests.
