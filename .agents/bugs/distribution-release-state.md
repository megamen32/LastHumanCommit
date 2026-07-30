# Distribution release state is incomplete

Description: Only Codex host installation is tested; upgrade may retain removed
payload files; rollback/status semantics are incomplete; `VERSION` is 0.2.0 but
no 0.2.0 tag exists.
Evidence: `ROADMAP.md:22-23`, `tests/test_installer.py:106`,
`install.sh:79`, `install.sh:140`, `VERSION:1`, and `git tag`.
Blocks: `.agents/tasks/todo-agent-fleet-distribution.md`

