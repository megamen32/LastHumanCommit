---
name: worker-bugfix
description: Reproduce and fix an assigned behavior failure, then verify the same scenario and protect it against regression.
---

# Fix a bug

Read the symptom, expected behavior and previous attempts. Trace the real caller to the failing boundary, using existing project knowledge and targeted `rg`.

Keep a reproducible failure before changing code. Reuse an existing failing test or add a focused regression at the layer where the defect occurs. A live failure, test output or minimal reproduction can establish the baseline; choose evidence that distinguishes the bug from a broken test setup.

Repair the cause and rerun the same scenario. Check directly affected behavior. Keep routine tests fast, while running integration or end-to-end tests when the defect requires them. A mock that merely repeats the implementation does not establish the real fix.

Use the project's authorized fixtures for accounts and services. Ask the Lead when product intent or a consequential change remains unclear, with a recommendation and the evidence already collected.

If the path or false route is likely to recur, save a compact verified entry with `../worker-research/scripts/code_map.py`. Return the fix, commands, results and any remaining limitation.
