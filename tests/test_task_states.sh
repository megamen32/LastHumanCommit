#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
probe=$(mktemp "$root/.agents/tasks/todo-validator-probe.XXXXXX.md")
trap 'rm -f -- "$probe"' EXIT HUP INT TERM

printf '%s\n' '# Invalid task probe' '' 'Status: nonsense' >"$probe"

if output=$(python3 "$root/tests/validate.py" 2>&1); then
  echo "FAIL: validator accepted an unknown task prefix" >&2
  exit 1
fi

case "$output" in
  *"todo task has invalid status"*) ;;
  *)
    printf '%s\n' "$output" >&2
    echo "FAIL: validator rejected the probe for the wrong reason" >&2
    exit 1
    ;;
esac

rm -f -- "$probe"
trap - EXIT HUP INT TERM
python3 "$root/tests/validate.py" >/dev/null
echo "PASS: task filenames and statuses use the exact canonical matrix"

probe=$(mktemp "$root/.agents/tasks/todo-lifecycle-probe.XXXXXX.md")
trap 'rm -f -- "$probe"' EXIT HUP INT TERM

printf '%s\n' '# Missing lifecycle probe' '' 'Status: todo' >"$probe"

if output=$(python3 "$root/tests/validate.py" 2>&1); then
  echo "FAIL: validator accepted a todo task without lifecycle identity" >&2
  exit 1
fi

case "$output" in
  *"todo task lacks lifecycle field"*) ;;
  *)
    printf '%s\n' "$output" >&2
    echo "FAIL: validator rejected the lifecycle probe for the wrong reason" >&2
    exit 1
    ;;
esac

rm -f -- "$probe"
trap - EXIT HUP INT TERM
echo "PASS: todo tasks require lifecycle identity"

probe=$(mktemp "$root/.agents/tasks/work-lifecycle-empty-probe.XXXXXX.md")
trap 'rm -f -- "$probe"' EXIT HUP INT TERM

printf '%s\n' '# Empty lifecycle probe' '' 'Status: in progress' 'Harness: codex' 'PID:' 'Agent session: known' 'PID status: alive' 'Last PID signal: now' 'Last task-file transition: work' 'Started at (UTC+3): now' 'Lifecycle provenance: recorded' 'Last task-file mtime observed (UTC+3): now' >"$probe"

if output=$(python3 "$root/tests/validate.py" 2>&1); then
  echo "FAIL: validator accepted a work task with an empty PID" >&2
  exit 1
fi

case "$output" in
  *"work task has empty lifecycle field"*) ;;
  *)
    printf '%s\n' "$output" >&2
    echo "FAIL: validator rejected the empty lifecycle probe for the wrong reason" >&2
    exit 1
    ;;
esac

rm -f -- "$probe"
trap - EXIT HUP INT TERM
echo "PASS: lifecycle identity values cannot be empty"
