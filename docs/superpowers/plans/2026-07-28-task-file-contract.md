# Task File Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make one committed task file the complete workflow, runtime-identity, communication, and completion record while removing duplicate shared registries.

**Architecture:** Task state is encoded by `todo-`, `work-`, and `done-` filenames plus one staged Markdown document. The document itself explains when each layer is filled. Confirmed bugs are individual files under `.agents/bugs/`; `subagents.jsonl` and the shared `bugs.md` table are removed.

**Tech Stack:** Markdown templates, POSIX shell installer, Python validation and pytest.

## Global Constraints

- Every edit to a task file must be committed.
- Before start requires Description, Severity, Workflow, min-max estimate, and Acceptance.
- On start requires UTC+3 start, PID, harness, session identifier, and Next action.
- Completion requires the full durable result; Lead returns only a short TL;DR.
- Task transitions are `todo-<id>.md` to `work-<id>.md` to `done-<id>.md` via `git mv`.
- Blockers point to `.agents/bugs/<id>.md` or an exact user decision.
- A confirmed bug file is committed immediately and deleted in the verified fix commit.

---

### Task 1: Lock the exact installed contract

**Files:**
- Modify: `tests/validate.py`
- Modify: `tests/test_installer.py`

**Interfaces:**
- Consumes: canonical templates under `src/common/templates/.agents/`.
- Produces: validation of required task fields, filename transitions, and per-file bug tracking.

- [ ] **Step 1: Write failing source validation**

Require the task template phrases `on any edit`, `estimated min-max complete time`, `PID:`, `Harness:`, `session identifier:`, `Next action:`, full result, and Lead TL;DR. Reject `subagents.jsonl`, shared `bugs.md`, `wip-`, `Transition:`, and shared-table references.

- [ ] **Step 2: Write failing installer regression**

Assert installed payload contains `templates/.agents/bugs/bug_template.md`, contains neither `templates/.agents/bugs.md` nor `templates/.agents/subagents.jsonl`, and preserves the task template.

- [ ] **Step 3: Run focused tests**

Run: `python3 -m pytest -q tests/test_installer.py && python3 tests/validate.py`

Expected: FAIL because the old shared registries remain required.

### Task 2: Implement the single-file lifecycle

**Files:**
- Modify: `src/common/templates/.agents/tasks/task_template.md`
- Modify: `src/common/templates/.agents/bugs/bug_template.md`
- Delete: `src/common/templates/.agents/bugs.md`
- Delete: `src/common/templates/.agents/subagents.jsonl`
- Modify: `src/common/agents/Lead.md`

**Interfaces:**
- Consumes: one accepted task and its selected workflow.
- Produces: a committed document that acquires identity and evidence only when those facts become known.

- [ ] **Step 1: Replace the task template**

Use the exact three layers: Before Start, On Start, Message, and When Complete. Include explicit fill timing and `git mv` commands.

- [ ] **Step 2: Simplify the bug template**

Keep Description, optional Severity, immutable Evidence, optional Blocks, and the create-commit/fix-delete-commit rule.

- [ ] **Step 3: Remove duplicate registries**

Delete the shared bug table and subagent event index.

- [ ] **Step 4: Update Lead**

Define workflow as an ordered task-specific chain, require every task-file edit to be committed, record current executor identity in the task, advance Next action from the workflow, and enforce bug-file commits.

- [ ] **Step 5: Run focused validation**

Run: `python3 -m pytest -q tests/test_installer.py && python3 tests/validate.py`

Expected: new contract checks pass; any unrelated pre-existing source failure is reported separately.

### Task 3: Align public documentation

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: installed lifecycle contract.
- Produces: accurate concise documentation.

- [ ] **Step 1: Update lifecycle copy**

Describe `todo → work → done`, task-local workflow/identity/result, and one-file-per-bug behavior.

- [ ] **Step 2: Run milestone checks**

Run: `python3 -m pytest -q tests/test_installer.py && python3 tests/validate.py && sh -n install.sh && git diff --check`

Expected: installer tests, shell syntax, and changed-file checks pass.

## Self-Review

- Spec coverage: all user-supplied fields and transition rules are explicit.
- Placeholder scan: template placeholders are intentional user-fill fields, not implementation gaps.
- Type consistency: filenames, installer paths, and validation paths match.
