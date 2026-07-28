# Readable Subagent Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restore the published concise README and ensure every subagent instruction gives a compact, unambiguous whole-workflow map.

**Architecture:** `README.md` retains the published image, short meaning, and role map while keeping the current working installer commands. Each source role prompt gets the same small shared-workflow section: `L (Lead)` owns outcome and integration; subagents receive a bounded task, do only their assigned role, and return evidence to Lead.

**Tech Stack:** Markdown and Python standard-library validator.

## Global Constraints

- Treat the public README at `https://github.com/megamen32/LastHumanCommit` as the source for image and concise meaning.
- Preserve working install/uninstall documentation.
- Every subagent's first Lead reference must be `L (Lead)`.
- Do not add a vague role handoff or permit subagents to redefine scope, architecture, P0, or final outcome.

---

### Task 1: Lock the compact workflow contract with a failing validation

**Files:**
- Modify: `tests/validate.py`

**Interfaces:**
- Consumes: `src/common/agents/{Adviser,Critic,Explorer,Overseer,Reviewer,Worker}.md`.
- Produces: a static guarantee that every distributed subagent prompt has `L (Lead)` and `## Shared workflow`.

- [ ] **Step 1: Add the failing assertion**

```python
subagent_names = ("Adviser.md", "Critic.md", "Explorer.md", "Overseer.md", "Reviewer.md", "Worker.md")
for name in subagent_names:
    prompt = (ROOT / "src/common/agents" / name).read_text(encoding="utf-8")
    for phrase in ("L (Lead)", "## Shared workflow", "do only my assigned role"):
        if phrase not in prompt:
            fail(f"src/common/agents/{name} lacks shared workflow phrase: {phrase}")
```

- [ ] **Step 2: Run validation**

Run: `python3 tests/validate.py`

Expected: FAIL because current prompts use unexplained `L` and have no shared workflow section.

### Task 2: Add compact workflow maps to role sources

**Files:**
- Modify: `src/common/agents/Adviser.md`
- Modify: `src/common/agents/Critic.md`
- Modify: `src/common/agents/Explorer.md`
- Modify: `src/common/agents/Overseer.md`
- Modify: `src/common/agents/Reviewer.md`
- Modify: `src/common/agents/Worker.md`

**Interfaces:**
- Consumes: a bounded task card from Lead.
- Produces: evidence/report for Lead; only Worker changes assigned files.

- [ ] **Step 1: Add the common section after each role introduction**

```markdown
## Shared workflow

`L (Lead)` owns the user outcome, priority, scope, integration, and final answer.
Lead gives me one bounded task and acceptance proof; I do only my assigned role,
record evidence in that task, and return my report to Lead. I do not take another
role, redefine P0, expand scope, or claim the final result.
```

- [ ] **Step 2: Replace each role's first bare `L` with `L (Lead)`**

Keep later references compact as `Lead` or `L` only after the definition.

- [ ] **Step 3: Run source validation**

Run: `python3 tests/validate.py`

Expected: the new role-contract checks pass; report any unrelated existing validator failure separately.

### Task 3: Merge the public README intent

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: public README image URL and concise role layout.
- Produces: an immediately understandable project overview and usable installer instructions.

- [ ] **Step 1: Restore public identity at the top**

Add the published image, one concise purpose paragraph, an ASCII role map, and the short explanation of lazy roles/profiles/protocols.

- [ ] **Step 2: Retain local installation contract**

Keep `install.sh host`, `install.sh project .`, and the verified CWD install/uninstall commands.

- [ ] **Step 3: Run milestone checks**

Run: `python3 -m pytest -q tests/test_installer.py && python3 tests/validate.py && sh -n install.sh && git diff --check`

Expected: all changed contract checks and installer tests pass; surface any unrelated existing source error without rewriting user-authored requirements.
