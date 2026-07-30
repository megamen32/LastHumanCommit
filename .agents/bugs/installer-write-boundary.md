# Installer write boundary is unsafe

Description: Legacy installer follows a pre-existing `.last-human-commit`
symlink outside the selected project and multi-file updates are not
transactional.
Evidence: external-write reproducer reaches `install.sh:123-127`; sequential
entry writes occur at `install.sh:109` and `install.sh:134`.
Blocks: `.agents/tasks/todo-agent-fleet-distribution.md`

