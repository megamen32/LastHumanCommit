---
name: focus-groups
description: Run diverse independent goal-driven Testers on the real product, synthesize observed obstacles, repair them and retest through a closed product-improvement loop.
---

# Autonomous focus groups

Use when multiple user goals or conditions could expose product weaknesses, or
when requested. This skill can be invoked independently of a Full task. Full's
single mandatory Tester remains a compact acceptance gate.

## Form a useful group

Lead selects a diverse set of plausible user goals, experience levels, devices,
constraints and expectations. Names and fictional biographies alone do not create
diversity. Example goals: get a first successful result with no product experience;
import existing work; resume a long operation after leaving; correct a mistaken
input on a phone. Do not give the exact intended solution path.

Choose a manageable group based on coverage, available models/tools and the
value of additional evidence; no universal fixed count. Use strong-enough tool
operators even for novice personas. Model diversity and persona diversity are
separate dimensions; do not claim one provides the other.

Give each Tester a fresh session, isolated browser/device profile when needed,
suitable test identity/data and a fixed product revision. Run compatible lanes
in parallel. Testers do not see implementation or one another's findings before
their independent first attempt. Apply `../user-testing/SKILL.md`.

## Turn observations into repairs

Collect attempted actions and failure evidence, not essays imagining a UI.
Consolidate duplicate underlying obstacles while retaining affected scenarios.
Separate tool outages from product defects, and observed inability to meet a goal
from aesthetic preference. Evaluate impact, reproducibility and fit to the goal,
not the count or aggressiveness of complaints.

Lead selects in-scope repairs autonomously; Worker diagnoses and implements;
Reviewer checks the change. During a batch, hold the tested revision stable or
label every observation with its actual revision. Do not combine mixed-version
reports as if all participants saw the same product.

After a repair, preserve a useful regression check and run a fresh user attempt.
For discoverability, a new Tester should not be told which control was changed.
Continue until the selected user goals succeed, actionable serious obstacles are
resolved, or Overseer identifies a real external blocker or diminishing returns.
A bounded exploratory study is not a promise to eliminate all possible criticism.

## Result

Report covered goals/conditions and versions, evidence-backed findings, selected
repairs, regression results, fresh retest outcomes and unresolved issues. Synthetic
participants expose scenarios; they do not estimate the percentage of real users
with a problem. Do not present their preferences as market demand evidence.
