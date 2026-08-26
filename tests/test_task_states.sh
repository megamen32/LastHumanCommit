#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
template="$root/src/common/templates/.agents/tasks/task_template.md"

require() {
  grep -Fq "$1" "$template" || {
    printf '%s\n' "FAIL: task template lacks $1" >&2
    exit 1
  }
}

require 'Accepted business outcome / Definition of Done:'
require 'Exact business canary:'
require 'Cheapest sufficient proof:'
require 'Actual production consumer path:'
require 'Next shortest action:'
require 'Why this is least-cost:'
require 'Every 20 active minutes is a reporting checkpoint, not a lifetime limit.'
require 'Use the harness wait/join tool while a required child is non-terminal.'
require 'Overseer is the supreme route controller'
require 'Cycle estimates (cycle / minimum / maximum / actual):'
require 'Time-guard state:'
require 'Какие реальные задачи закрыты:'
require 'Recommendation and proposed default:'
require 'Safe independent work continuing in parallel:'

if grep -Fq 'Lifecycle snapshot: todo | work | done' "$template"; then
  echo 'FAIL: task template still requires snapshot lifecycle copies' >&2
  exit 1
fi

if grep -Fq 'Snapshot commit:' "$template"; then
  echo 'FAIL: task template still requires a snapshot commit' >&2
  exit 1
fi

python3 "$root/tests/validate.py" >/dev/null
echo 'PASS: compact task state keeps business routing ahead of lifecycle ceremony'
