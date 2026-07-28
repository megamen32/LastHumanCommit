# One-Line CWD Installer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide copy-paste install and uninstall commands that apply Last Human Commit to the caller's current project for Codex, Claude, and OpenCode.

**Architecture:** Keep the dependency-free `install.sh project .` contract as the single implementation path. Document one-line remote bootstrap commands that shallow-clone into a newly created temporary directory, invoke that contract against `PWD`, and delete only that temporary directory. Make uninstall preflight every managed entry so malformed files fail without any writes.

**Tech Stack:** POSIX shell, Python `pytest`, Markdown.

## Global Constraints

- Installation targets the caller's current directory, never a global home directory.
- Codex and OpenCode use `AGENTS.md`; Claude uses `CLAUDE.md`.
- Preserve user-owned text and remove only `last-human-commit` marked blocks.
- Do not introduce runtime dependencies, network fetches inside `install.sh`, or `sudo`.

---

### Task 1: Protect project uninstall preflight

**Files:**
- Modify: `install.sh:152-166`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: `uninstall project [PATH]` command-line contract.
- Produces: zero-write failure when either `AGENTS.md` or `CLAUDE.md` has malformed managed markers.

- [ ] **Step 1: Write the failing test**

```python
def test_project_uninstall_rejects_malformed_markers_without_writes(tmp_path: Path) -> None:
    project = tmp_path / "project"
    project.mkdir()
    agents = project / "AGENTS.md"
    agents.write_text("before\\n<!-- last-human-commit:begin -->\\n", encoding="utf-8")
    before = agents.read_bytes()
    env = {**os.environ, "HOME": str(tmp_path / "home")}

    result = run("uninstall", "project", str(project), cwd=project, env=env)

    assert result.returncode != 0
    assert agents.read_bytes() == before
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest -q tests/test_installer.py::test_project_uninstall_rejects_malformed_markers_without_writes`

Expected: FAIL because the current uninstall silently rewrites the malformed file.

- [ ] **Step 3: Write minimal implementation**

```sh
    preflight_entry "$path/AGENTS.md"
    preflight_entry "$path/CLAUDE.md"
```

Place both calls after the `scope` validation and before the uninstall loop.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest -q tests/test_installer.py::test_project_uninstall_rejects_malformed_markers_without_writes`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add install.sh tests/test_installer.py
git commit -m "fix: preflight project uninstall targets"
```

### Task 2: Document CWD one-liners

**Files:**
- Modify: `README.md:8-31`
- Test: `tests/test_installer.py`

**Interfaces:**
- Consumes: a POSIX shell, `git`, `mktemp`, and the caller's `PWD`.
- Produces: one install command and one uninstall command that execute `install.sh project "$PWD"` and `install.sh uninstall project "$PWD"` from an isolated shallow clone.

- [ ] **Step 1: Add exact commands to README**

```sh
tmp=$(mktemp -d) && git clone --depth=1 https://github.com/megamen32/LastHumanCommit.git "$tmp" && sh "$tmp/install.sh" project "$PWD"; rc=$?; rm -rf "$tmp"; exit "$rc"
```

Use the same temporary-clone structure for uninstall, replacing `project "$PWD"` with `uninstall project "$PWD"`.

- [ ] **Step 2: Run the focused installer suite**

Run: `python3 -m pytest -q tests/test_installer.py`

Expected: PASS.

- [ ] **Step 3: Run maintainer validation**

Run: `python3 tests/validate.py && sh -n install.sh`

Expected: all source checks pass and shell syntax is valid.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/superpowers/plans/2026-07-27-one-line-cwd-install.md
git commit -m "docs: add CWD installer one-liners"
```

## Self-Review

- Spec coverage: Task 1 makes removal fail closed; Task 2 gives CWD install/uninstall one-liners for all three harnesses.
- Placeholder scan: no TODO/TBD or undefined implementation steps remain.
- Type consistency: the plan uses existing shell functions and the existing Python `run()` test helper only.
