# Restore Canon Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore historically required agent-workflow guarantees that were lost during the source relocation and English rewrite, without restoring duplicate worklog bookkeeping.

**Architecture:** Keep the existing `src/common` distribution layout and add concise requirements to its canonical role and template sources. The installer continues copying that source tree unchanged. A compact `bugs.md` tracks confirmed cross-task defects; task cards and `subagents.jsonl` remain the sole activity record.

**Tech Stack:** Markdown source templates, POSIX shell installer, Python standard-library test runner and pytest.

## Global Constraints

- Restore only requirements independently confirmed by two history audits.
- Do not restore `worklog.jsonl`; it duplicates existing task/session records.
- Do not change the valid two-file project entry arrangement: `AGENTS.md` serves Codex/OpenCode and `CLAUDE.md` serves Claude.
- Do not translate, re-style, or revive unrelated historical content.

---

### Task 1: Add failing contract regressions

**Files:**
- Modify: `tests/test_installer.py`
- Modify: `tests/validate.py`

**Interfaces:**
- Consumes: `sh install.sh project PATH`.
- Produces: an installed `common/templates/.agents/bugs.md` and static source validation for the restored requirements.

- [ ] **Step 1: Write failing installer regression**

```python
def test_project_install_copies_confirmed_bug_register(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("project", str(project), cwd=project, env=env)

    assert result.returncode == 0, result.stderr
    register = project / ".last-human-commit/common/templates/.agents/bugs.md"
    assert register.is_file()
    assert "| ID | Severity | Evidence | Owner | Status | Next proof |" in register.read_text(encoding="utf-8")
```

- [ ] **Step 2: Run it and observe failure**

Run: `python3 -m pytest -q tests/test_installer.py::test_project_install_copies_confirmed_bug_register`

Expected: FAIL because the distributed bug register does not exist.

- [ ] **Step 3: Add failing source-contract assertions**

Require `bugs.md`, Lead's early Explorer/Worker, P0 escalation, STOP/RETHINK, complex-close Critic, lifecycle/blocker and release clauses, and Explorer source/date provenance.

- [ ] **Step 4: Run validation and observe the missing-contract failure**

Run: `python3 tests/validate.py`

Expected: FAIL on a newly required source phrase before implementation; preserve and report unrelated validation failures separately.

### Task 2: Restore the minimal role and template guarantees

**Files:**
- Create: `src/common/templates/.agents/bugs.md`
- Modify: `src/common/agents/Lead.md`
- Modify: `src/common/agents/Explorer.md`
- Modify: `src/common/templates/.agents/tasks/task_template.md`

**Interfaces:**
- Consumes: task files under `.agents/tasks/` and confirmed defects/blockers.
- Produces: auditable lifecycle, recovery, review, research provenance, release, and defect-register requirements.

- [ ] **Step 1: Create compact confirmed-bug register**

```markdown
# Confirmed bugs and blockers

| ID | Severity | Evidence | Owner | Status | Next proof |
|---|---|---|---|---|---|
```

- [ ] **Step 2: Restore Lead requirements**

Add concise requirements for early bounded Explorer and safe Worker work, P0 escalation, STOP/RETHINK plus Critic after two independent hypotheses, Critic before complex closure, task-ID/blocker invariants, and forward-fix/release discipline.

- [ ] **Step 3: Restore Explorer provenance**

Require current primary sources and source/date evidence for web research; retain exclusions, contradictions, risks, and next probe.

- [ ] **Step 4: Make task lifecycle fields inspectable**

Add immutable task identity, derived filename state, an exact blocker section, and transition information without turning the template into an activity log.

- [ ] **Step 5: Run focused regressions**

Run: `python3 -m pytest -q tests/test_installer.py::test_project_install_copies_confirmed_bug_register && python3 tests/validate.py`

Expected: both pass except any separately documented pre-existing validation defect.

### Task 3: Verify distribution and document the decision

**Files:**
- Modify: `README.md`
- Modify: `ROADMAP.md`
- Modify: `docs/superpowers/plans/2026-07-27-restore-canon-contract.md`

**Interfaces:**
- Consumes: public description of tracked project state.
- Produces: accurate statement that a confirmed-bugs register is copied and audit decision that worklog remains intentionally absent.

- [ ] **Step 1: Update concise documentation**

Mention the confirmed-bugs register as installed tracked state; do not claim worklog support.

- [ ] **Step 2: Run milestone checks**

Run: `python3 -m pytest -q tests/test_installer.py && python3 tests/validate.py && sh -n install.sh && git diff --check`

Expected: installer suite, canonical validation, shell syntax, and whitespace check pass.

- [ ] **Step 3: Commit**

```bash
git add README.md ROADMAP.md src/common tests tests/test_installer.py docs/superpowers/plans/2026-07-27-restore-canon-contract.md
git commit -m "fix: restore canonical workflow guarantees"
```

## Self-Review

- Spec coverage: all independently confirmed current-rewrite losses are assigned to Task 2; `bugs.md` is restored and worklog intentionally remains absent.
- Placeholder scan: no deferred implementation is needed.
- Type consistency: all test paths match the installer copy layout and existing standard-library test tooling.
