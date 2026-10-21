---
name: maintainer-review
description: Before a PR into a repository you do not own, let that project's strict maintainer read the project and the diff and return a hard critique.
---

# Maintainer review — use when policy or risk warrants it

Use this when the target repository's actual contribution policy requires maintainer
review or when a concrete external integration risk makes it useful. Ownership alone
does not create an LHC gate. A review can surface defects, policy requirements and
preferences; only concrete defects or required checks block the affected action.

## Who reviews

Request one fresh Reviewer from an allowed gpt6luna, glm53flash or minimax3.1flash
family, resolving it to an exact live model-catalog ID and verifying actual identity,
that plays the target project's maintainer: a senior engineer who has been in that codebase for years, loves
it, and has no patience for changes that ignore how it works. Give it the
target repository path, the branch or diff under review, and the accepted
business result. Do not ask it for a verdict — ask for the maintainer's own
reaction to a foreign PR.

## What the maintainer reads first

The project, before the diff, exactly as the owner would:

- `AGENTS.md`, `CLAUDE.md`, `CONTRIBUTING.md`, `README.md`, `docs/`, and any
  architecture, convention or design note;
- lint, format, type and build configuration; the test layout and what the
  suite is expected to cover;
- CI workflow files, branch protection, required checks;
- `CODEOWNERS`, the recent history of the touched areas, and the naming,
  layering, error-handling and testing conventions the code visibly follows.

A critique that ignores these rules is worthless. When the project has no
written rules, the maintainer's judgement of its conventions *is* the rule, and
the critique must say that instead of pretending a document exists.

## What the maintainer returns

Specific, actionable findings that separate concrete issues from preferences:

- every place the diff breaks a written rule of that project, with the rule quoted;
- every place it breaks a convention the codebase visibly follows;
- what the owner would have to fix in review, and what they would reject outright;
- the smallest correct form of each finding.

Distinguish a real defect from a preference. Do not invent findings to look thorough:
a false objection costs the author exactly as much as a missed one, and it teaches
the owner to ignore the reviewer. Do not soften a real one
either — "I would have written this differently" goes in a separate, clearly
labelled list, never mixed into the blocking findings.

Return concrete findings with the relevant rule, location and fix. Label
non-blocking preferences separately. Do not invent `CLEAN` or `PASS` claims.

## After the review

Fix concrete findings that affect the accepted claim or satisfy required repository
policy, then recheck the affected delta. A reviewer response, LHC receipt or
non-blocking preference is not a release veto. Preserve unresolved material defects
as blockers and state the smallest next action.
