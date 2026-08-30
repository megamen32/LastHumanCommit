#!/bin/sh
# Behavioral checks for the narrow, explicit Last Human Commit block adapter.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ADAPTER="$ROOT/scripts/lhc-block"
BEGIN='<!-- last-human-commit:begin -->'
END='<!-- last-human-commit:end -->'
mkdir -p "$ROOT/.tmp"
TMPDIR_TEST=$(mktemp -d "$ROOT/.tmp/lhc-block-test.XXXXXX")
trap 'rm -rf "$TMPDIR_TEST"' EXIT HUP INT TERM

fail() { printf '%s\n' "FAIL: $*" >&2; exit 1; }
expect_fail() { "$@" >/dev/null 2>&1 && fail "expected failure: $*" || :; }
expect_same() { cmp -s "$1" "$2" || fail "files differ: $1 $2"; }

[ -x "$ADAPTER" ] || fail "missing executable adapter: scripts/lhc-block"

cat >"$TMPDIR_TEST/source" <<EOF
$BEGIN
# Canonical LHC router
router-v2
$END
EOF

cat >"$TMPDIR_TEST/project-agents" <<EOF
# Project-owned instruction

$BEGIN
old router
$END

# Project-owned suffix
EOF
cat >"$TMPDIR_TEST/expected-applied" <<EOF
# Project-owned instruction

$BEGIN
# Canonical LHC router
router-v2
$END

# Project-owned suffix
EOF

"$ADAPTER" check "$TMPDIR_TEST/project-agents"
"$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/project-agents"
expect_same "$TMPDIR_TEST/expected-applied" "$TMPDIR_TEST/project-agents"
cp "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/once"
chmod 640 "$TMPDIR_TEST/project-agents"
"$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/project-agents"
expect_same "$TMPDIR_TEST/once" "$TMPDIR_TEST/project-agents"
[ "$(stat -c %a "$TMPDIR_TEST/project-agents")" = 640 ] || fail "apply changed target mode"

cp "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/editor-failure-before"
expect_fail env LHC_BLOCK_ED=false "$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/project-agents"
expect_same "$TMPDIR_TEST/editor-failure-before" "$TMPDIR_TEST/project-agents"

cat >"$TMPDIR_TEST/project-claude" <<'EOF'
# Claude-specific instruction
EOF
cat >"$TMPDIR_TEST/expected-initialized" <<EOF
# Claude-specific instruction

$BEGIN
# Canonical LHC router
router-v2
$END
EOF
chmod 600 "$TMPDIR_TEST/project-claude"
"$ADAPTER" init "$TMPDIR_TEST/source" "$TMPDIR_TEST/project-claude"
expect_same "$TMPDIR_TEST/expected-initialized" "$TMPDIR_TEST/project-claude"
[ "$(stat -c %a "$TMPDIR_TEST/project-claude")" = 600 ] || fail "init changed target mode"

mkdir "$TMPDIR_TEST/paths with spaces"
cp "$TMPDIR_TEST/source" "$TMPDIR_TEST/paths with spaces/source router"
cp "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/paths with spaces/project agents"
"$ADAPTER" apply "$TMPDIR_TEST/paths with spaces/source router" "$TMPDIR_TEST/paths with spaces/project agents"
expect_same "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/paths with spaces/project agents"

ln -s "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/project-agents-link"
cp "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/project-agents-before-link"
expect_fail "$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/project-agents-link"
expect_same "$TMPDIR_TEST/project-agents-before-link" "$TMPDIR_TEST/project-agents"

newline_source=$(printf '%s\n1,$d\nw\nq' "$TMPDIR_TEST/source")
cp "$TMPDIR_TEST/source" "$newline_source"
cp "$TMPDIR_TEST/project-agents" "$TMPDIR_TEST/project-agents-before-newline"
expect_fail "$ADAPTER" apply "$newline_source" "$TMPDIR_TEST/project-agents"
expect_same "$TMPDIR_TEST/project-agents-before-newline" "$TMPDIR_TEST/project-agents"

cat >"$TMPDIR_TEST/broken" <<EOF
# Keep this exact text
$BEGIN
unfinished
EOF
cp "$TMPDIR_TEST/broken" "$TMPDIR_TEST/broken-before"
expect_fail "$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/broken"
expect_same "$TMPDIR_TEST/broken-before" "$TMPDIR_TEST/broken"

cat >"$TMPDIR_TEST/duplicate" <<EOF
$BEGIN
one
$END
$BEGIN
two
$END
EOF
cp "$TMPDIR_TEST/duplicate" "$TMPDIR_TEST/duplicate-before"
expect_fail "$ADAPTER" apply "$TMPDIR_TEST/source" "$TMPDIR_TEST/duplicate"
expect_same "$TMPDIR_TEST/duplicate-before" "$TMPDIR_TEST/duplicate"

cat >"$TMPDIR_TEST/removable" <<EOF
# Project prefix
$BEGIN
managed
$END
# Project suffix
EOF
cat >"$TMPDIR_TEST/expected-removed" <<'EOF'
# Project prefix
# Project suffix
EOF
chmod 600 "$TMPDIR_TEST/removable"
"$ADAPTER" remove-block "$TMPDIR_TEST/removable"
expect_same "$TMPDIR_TEST/expected-removed" "$TMPDIR_TEST/removable"
[ "$(stat -c %a "$TMPDIR_TEST/removable")" = 600 ] || fail "remove changed target mode"

printf '# no final newline' >"$TMPDIR_TEST/no-final-newline"
cp "$TMPDIR_TEST/no-final-newline" "$TMPDIR_TEST/no-final-newline-before"
expect_fail "$ADAPTER" init "$TMPDIR_TEST/source" "$TMPDIR_TEST/no-final-newline"
expect_same "$TMPDIR_TEST/no-final-newline-before" "$TMPDIR_TEST/no-final-newline"

printf '%s\n' 'PASS: block adapter preserves project-owned instructions'
