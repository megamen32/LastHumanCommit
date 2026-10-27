<!-- last-human-commit:begin -->
This project is worked with Last Human Commit (LHC), installed as the global
`last-human-commit` Agent Plugin. Read the plugin's bundled `AGENTS.md`: it is the
operating contract (finish line, blocker lists, escalation chain, cycle,
delivery). Do not copy its rules here.

Project facts agents read first:
- `.agents/PROJECT.md`: who owns this repository, which branch PRs go to, how to
  deploy for testing (template: the plugin's `common/templates/project.md`).
- `.agents/TEST_ACCESS.md`: allowed test environments, protected secret
  references and how to create or recover test users (template:
  `common/templates/test-access.md`).
- `.agents/tasks/`: one note per task longer than 15 minutes.

Language: English for planning/new task notes/tools/agent messages; answer the
owner in their language. Delegated roles inherit this policy. Test access rules:
the plugin's `common/protocols/REVIEW_TO_DELIVERY.md`.
<!-- last-human-commit:end -->
