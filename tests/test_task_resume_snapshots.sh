#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmpdir=$(mktemp -d "$root/.agents/at/task-resume.XXXXXX")
trap 'rm -rf -- "$tmpdir"' EXIT HUP INT TERM

task="$tmpdir/task-repair.md"
cat >"$task" <<'EOF'
# Task

Status: in progress
Accepted business outcome / Definition of Done: repair succeeds
Exact business canary: consumer returns expected result
Cheapest sufficient proof: run the consumer once
Actual production consumer path: consumer -> repair
Next shortest action: finish repair

## Worker checkpoint

- Progress: real path traced
  Business delta: closer
  Blocker: implementation incomplete
  Shortest next action: patch repair
EOF

# A resumed Worker consumes one compact current state. No todo/work/done copies,
# snapshot commits, or orientation replay are required.
grep -Fq 'Actual production consumer path: consumer -> repair' "$task"
grep -Fq 'Shortest next action: patch repair' "$task"

cat >>"$task" <<'EOF'

## Result

Status: complete
Business result: repair succeeds
Real canary proof: consumer returned expected result
EOF

test "$(find "$tmpdir" -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')" -eq 1
grep -Fq 'Business result: repair succeeds' "$task"
echo 'PASS: Worker resumes from one compact current task state without snapshot ceremony'
