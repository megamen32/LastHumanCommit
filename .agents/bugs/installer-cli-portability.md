# Installer CLI and path rendering are unreliable

Description: Legacy installer accepts unexpected arguments, mishandles
documented dry-run forms, and corrupts an entry when the canon root contains a
literal backslash-n pathname component.
Evidence: `host codex --unexpected` and `project PATH --unexpected` exit 0;
`host --dry-run` and `project --dry-run` misparse; rendering uses
`awk -v root` at `install.sh:27-37`.
Blocks: `.agents/tasks/todo-agent-fleet-distribution.md`

