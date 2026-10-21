---
name: maintainer-review
description: Before a PR into a repository you do not own, let that project's strict maintainer read the project and the diff and return a hard critique.
---

# Maintainer review — the owner's own gate, before the PR exists

Use this for repositories we do not own: a PR targets a repository whose owner
is not the requester. That owner will read the diff against the rules of *their*
project, and they will read it once. This skill makes that read happen before the PR is opened, with a
fresh agent playing the owner, so the PR arrives clean instead of dirty.

Not for repositories we own: there the Lead's own review and the normal checks
are the gate, and an outside persona only adds theatre.

## Who reviews

Request one fresh session on a strong model that plays the target project's
maintainer: a senior engineer who has been in that codebase for years, loves
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

A mountain of specific, actionable findings — not a verdict, not a summary, not
a compliment:

- every place the diff breaks a written rule of that project, with the rule quoted;
- every place it breaks a convention the codebase visibly follows;
- what the owner would have to fix in review, and what they would reject outright;
- the smallest correct form of each finding.

Distinguish a real defect from a preference. Do not invent findings to look thorough:
a false objection costs the author exactly as much as a missed one, and it teaches
the owner to ignore the reviewer. Do not soften a real one
either — "I would have written this differently" goes in a separate, clearly
labelled list, never mixed into the blocking findings.

Return `CLEAN` only when the diff already satisfies that project's own rules.
Otherwise return the findings, each with the rule, the location and the fix.

## After the review

The author fixes every supported finding, or rejects it in writing with the
reason and the evidence. Then the review runs again on the changed diff: the
same session may be reused, but the review is redone, not assumed from the
previous one. A finding fixed in one place often opens another.

Only a clean or explicitly answered review lets the PR be opened. A PR that
reaches the owner dirty costs more than a later PR: their attention and the
relationship are the scarce resource, not the branch.
