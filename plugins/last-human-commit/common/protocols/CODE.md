> Load before writing or reshaping code. `AGENTS.md` wins on any conflict.

# CODE — how LHC code is written

The owner tests by blast radius: a change reruns only the tests of the files it
touched. Everything below serves that: small files, few links, pure logic.

## 1. Look before you build

Before a new mechanism, search for an old one that does the same or nearly
(`rg -n`, by the verb and by the noun). Found one: say in one line each
- why it is broken or not enough;
- is it overgrown, so that a new function on top would be a crutch;
- does it hold several jobs that must not fail together.
Then choose: repair it, split it, or replace it and mark the old one `LHC:LEGACY`.
A second mechanism next to a live first one is a bug.

Split by failure: jobs that can hang or fail separately live in separate units
(file, worker, process) joined by a queue or a table, each restartable alone.
Wrong: one scanner that finds new posts, schedules tasks for them and runs
those tasks; a stuck scan then stops the tasks too. Right: scanner, scheduler,
executor.

## 2. Pure core, thin shell

- **Core**: pure functions. Data in, data out, no clock, no network, no disk,
  no globals, no mutation of arguments. All decisions live here.
- **Shell**: everything that touches the outside world (HTTP, DB, files, time,
  random, env, queues, processes). It lives in its own file or files (`io_*`,
  `adapters/`, `*_store`, whatever the project already uses), does no deciding,
  and is handed to the core's caller as an argument, never imported by the core.
- A function reads the shell, calls the core, writes the shell: in that order.
- State is a value passed in and returned, not an object that remembers.
- Tests of the core need no mocks. If a test needs a mock, the logic is in the
  wrong place: move it into the core.

## 3. Async by default

I/O is asynchronous and concurrent by default (goroutines with context in Go,
`async`/`await` in Python and JS). Every outside call has a timeout and can be
cancelled. Independent calls run together. Blocking code is the exception and
says why in a comment. The pure core stays synchronous: it does no I/O.

## 4. KISS, YAGNI, size

- The simplest code that passes the acceptance scenario. No option, layer,
  config key or abstraction without a caller today.
- A code file stays under 1000 lines. A file that crosses it is split by job
  (section 1) in the same task that pushed it over; an old oversized file is
  split when the task touches it for more than a small fix.
- A file imports few project files. A change that forces edits in many files
  means the boundary is wrong: fix the boundary.

## 5. Tests name what they cover

Every test file starts with one comment line listing the source files it
checks, paths from the repository root, space separated, in the comment syntax
of its language:

    # LHC:COVERS src/billing/price.py src/billing/tax.py
    // LHC:COVERS internal/price/price.go

A changed file's tests: `rg -l "LHC:COVERS.*<path>"`. Run these while you work;
the full suite runs once before delivery. A source file no test names is
untested: add the test or the line. Keep the list true when files move.

## 6. Service marks

One grammar for every mark an agent leaves in code, so one query finds them:
`LHC:<KIND> <key=value ...> <text>`. All marks: `rg -n "LHC:[A-Z]+"`.

| Mark | Meaning | Find |
|---|---|---|
| `LHC:COVERS <paths>` | first line of a test file | `rg -n "LHC:COVERS"` |
| `LHC:LEGACY remove=YYYY-MM-DD <what replaces it>` | old code kept for a transition | `rg -n "LHC:LEGACY"` |
| `LHC:BLOCKING <why>` | deliberate blocking call | `rg -n "LHC:BLOCKING"` |

Legacy: the moment code is replaced but not yet deleted, mark it
`LHC:LEGACY remove=<today + 1 month>` (another date only on the owner's word).
Nothing new may call it. At the start of every full cycle run
`rg -n "LHC:LEGACY"`: every mark whose date has passed becomes one leaf
«delete legacy», done in this cycle. Legacy is deleted, not maintained.
