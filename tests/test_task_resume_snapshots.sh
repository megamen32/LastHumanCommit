#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
tmpdir=$(mktemp -d "$root/.agents/at/task-resume.XXXXXX")
trap 'rm -rf -- "$tmpdir"' EXIT HUP INT TERM

git -C "$tmpdir" init --quiet
git -C "$tmpdir" config user.email lhc-test@example.invalid
git -C "$tmpdir" config user.name lhc-test

cat >"$tmpdir/todo-repair.md" <<'EOF'
Status: todo
Lifecycle snapshot: todo
Result file: results/result-repair.md
Business canary: repair succeeds
EOF
git -C "$tmpdir" add todo-repair.md
git -C "$tmpdir" commit --quiet -m 'task: record todo request'

cp "$tmpdir/todo-repair.md" "$tmpdir/work-repair.md"
cat >>"$tmpdir/work-repair.md" <<'EOF'
Status: in progress
Lifecycle snapshot: work
Worker evidence: orientation complete; active file src/repair.py
Resume rule: continue from this snapshot; do not redo orientation
EOF
git -C "$tmpdir" add work-repair.md
git -C "$tmpdir" commit --quiet -m 'task: checkpoint worker progress'

# Simulate Worker death: the committed work snapshot is the only input to the
# next Worker, and its evidence must survive without a new research pass.
test -f "$tmpdir/work-repair.md"
grep -q 'Resume rule: continue from this snapshot' "$tmpdir/work-repair.md"
cp "$tmpdir/work-repair.md" "$tmpdir/done-repair.md"
cat >>"$tmpdir/done-repair.md" <<'EOF'
Status: complete
Lifecycle snapshot: done
Result: business canary passed
EOF
git -C "$tmpdir" add done-repair.md
git -C "$tmpdir" commit --quiet -m 'task: record completed result'

test -f "$tmpdir/todo-repair.md"
test -f "$tmpdir/work-repair.md"
test -f "$tmpdir/done-repair.md"
grep -q 'business canary passed' "$tmpdir/done-repair.md"
test "$(git -C "$tmpdir" log --oneline --all | wc -l | tr -d ' ')" -eq 3
test "$(git -C "$tmpdir" status --porcelain)" = ''
echo "PASS: dead Worker resumes from committed work snapshot and preserves todo/work/done copies"
