# Agent System Prompts Implementation Plan

> **For agentic workers:** Execute the tasks in order and retain the existing installation layout.

**Goal:** Make each shipped agent role a self-contained first-person system prompt that states its workflow position.

**Architecture:** The canonical role documents remain in `src/common/agents/`. `Lead.md` defines L's orchestration role; every other role declares itself a subagent and reports back to L. The validator protects those required identity statements.

**Tech Stack:** Markdown, Python standard library, pytest.

## Global Constraints

- Modify source files only; do not edit installed copies.
- Keep role prompts concise and in English.
- Do not change installer behavior.

### Task 1: Add a role-prompt contract

**Files:**

- Modify: `tests/validate.py`

- [x] Add validation requiring `Lead.md` to state `I am L` and each non-Lead role to state `I am a subagent` and `workflow`.
- [x] Run `python3 tests/validate.py` and confirm it fails because existing role files use third-person descriptions.

### Task 2: Rewrite canonical role prompts

**Files:**

- Modify: `src/common/agents/Lead.md`
- Modify: `src/common/agents/{Adviser,Critic,Explorer,Overseer,Reviewer,Worker}.md`
- Modify: `src/common/templates/.agents/tasks/task_template.md`
- Delete: `src/common/templates/.agents/worklog.jsonl`

- [x] Rewrite each document in first person, define its workflow position, boundaries, inputs, actions, and report to L.
- [x] Restore task-card runtime identity fields from commit `ed94f6a2a87fbc6ac0f974ef50d6c002465be794`; remove `worklog.jsonl` because task files are the execution record.
- [x] Run `python3 tests/validate.py`; the role and task-template contracts pass, while an unrelated pre-existing `src/common/profiles/Test.md:11` violation blocks the validator.

### Task 3: Verify the distribution contract

**Files:**

- Verify: `tests/validate.py`, `tests/test_installer.py`, `install.sh`

- [x] Run `python3 -m pytest -q tests/test_installer.py` and `sh -n install.sh`.
- [x] Run `git diff --check`; report unrelated pre-existing failures without altering their files.
