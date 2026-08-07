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
