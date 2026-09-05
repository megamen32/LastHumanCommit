# Shared checkout safety

Simple LHC work happens in the current primary project checkout. Independent
parallel implementation lanes may use Lead-assigned branches and worktrees.
All harnesses use the same canonical project-local allocation; the project
contains its own work.

## Workspace identity

At task start inspect:

- current repository root;
- `git worktree list --porcelain`;
- current branch or detached HEAD;
- the default branch when identifiable.

If the current root is an auxiliary worktree, the branch is detached, or the
branch differs from the default branch, the first user-visible update must say:

```text
⚠️ Работа идёт не в основном checkout.
Worktree: <absolute path>
Branch: <branch or detached HEAD>
Primary checkout: <absolute path>
```

Do not record this only inside the task file. If a harness selected the checkout
before startup, do not create another worktree or move silently.

Lead may allocate worktrees for independent parallel writes within the accepted
task without another permission round. Keep read-only research and small
non-conflicting work in the existing checkout when isolation adds no value.
Workers use their assignment and never invent a second branch or location.

The canonical allocation is:

```text
Branch: lhc/<task-slug>
<primary-project-root>/.worktrees/<task-slug>
```

Each lane has a unique stable lowercase hyphen-separated task slug, assigned by
Lead, plus an immutable base commit and owner in the existing task record. Git
worktree metadata is the registry; do not create a parallel harness registry.
Resolve the primary project root from the Git common directory and registered
worktrees, including when invoked from an auxiliary checkout. Never derive the
root from the current harness working directory alone.

Use the single portable tool `../tools/lhc_worktree.py`:

```sh
python3 <common-root>/tools/lhc_worktree.py plan --repo <checkout> --task <task-slug>
python3 <common-root>/tools/lhc_worktree.py create --repo <checkout> --task <task-slug> --base <commit>
```

Inspect the plan, record its base commit and use that exact commit for create.
Repeat the same assignment by reusing its registered worktree. A matching worker
branch may have advanced through commits; that alone is not a new assignment.
Conflicting branch/path/base ownership is a real conflict, never permission to
overwrite, delete, reset or silently pick another directory. The tool must not
switch the primary checkout. Harness adapters pass the assigned path unchanged
and disable their own automatic worktree allocation for that lane.

The project root must ignore `.worktrees/`. Never create project worktrees in
`/tmp`, a home cache, a sibling directory, or harness-specific storage.

## Project-local temporary storage

The project root must also ignore `.tmp/`. Create that directory when temporary
project work is needed and keep all source code, repository clones or exports,
build trees and caches, binaries, packages, APK/DMG files, archives, checksums,
and release artifacts there. This applies even to short-lived staging that is
deleted at command exit.

Never place those materials in system `/tmp`, `$TMPDIR`, a home cache, a sibling
directory, or a language runtime's default temporary directory. Do not redirect
`TMPDIR` to another non-project location as a workaround. System temporary
storage is reserved for tiny non-code OS primitives such as a required socket,
lock, FIFO, or anonymous atomic handle when the OS or API cannot use the project
path. It must never contain project source, business data, build output, or a
deliverable. Same-directory atomic replacement files remain valid because they
are created beside their durable target, not in system temporary storage.

## Concurrent-edit safety

Assume the checkout may contain concurrent human or agent work. A dirty checkout
is evidence to preserve, not damage to clean up.

At start, before changing a path, and before staging or committing, inspect
`git status --short`, staged/unstaged diffs, untracked files, and mtime where
available.

- A foreign path changed within five minutes is probably active. Preserve it and
  resolve the collision with its owner before a claimed Full completion; do not
  use activity as an exclusion from the final clean history.
- Owner lookup is mandatory before declaring a path orphaned: query Agent
  Herder (send_message / session list) for a live session matching the path's
  task record, coordination note, or recent authorship. An owner who answers
  keeps the path; hand it back and coordinate.
- Orphan TTL: when no live owner exists via Agent Herder AND the newest
  foreign mtime is older than thirty minutes (1800s — Agent Herder's own
  maximum session/note activity window), the acting Lead MUST adopt the
  path — review it, repair or finish what is unsafe or incomplete, run the
  relevant validation, and include it in the cycle's complete commit set.
  Unknown ownership is never permission to leave a path uncommitted, and never
  permission to delete it.
- Older foreign changes are still foreign: review every path, repair every
  unsafe or incomplete change, and commit the resulting complete set. Never use
  unknown ownership, generated output, binaries, missing paths, or mtime
  uncertainty as a reason to leave a path outside a claimed Full cycle.
- Nested repositories and gitlinks are part of that review: create and publish
  their reachable commits before recording their pointers in the parent.

Never use `git stash`, `git reset`, `git clean`, `git restore`, `git checkout
--`, `git revert`, force-push, or rollback to remove work not created by this
task. An explicit human request may authorize one named target only.

## Final integration

Before every integration or release, review the complete target-branch diff,
including foreign and pre-existing changes, so the resulting project state is
coherent. Revalidate that the target branch is the current remote/default-branch
tip. Lead integrates reviewed task branches into the delivery branch (`main`
unless explicitly configured otherwise), using fast-forward when possible or
a reviewed merge when branches diverge. Resolve conflicts against the accepted
outcome and rerun the affected integration checks. Do not silently rebase
published branches, discard foreign changes or force-push.

Check the combined result on main, push main and confirm the remote commit.
Only then remove task-owned worktrees that are clean and inactive, and delete
task-owned branches whose tips are ancestors of confirmed remote main. Preserve
unrelated worktrees, dirty work and unmerged branches; do not sweep old entries.
Branch cleanup never substitutes for integration proof.

Unified history: review every change, fix every unsafe or unreviewable item,
and commit the complete repaired result into one reachable history. Never call
a Full cycle complete with any modified, deleted, untracked, ignored-by-accident,
or dirty nested-repository path. If required authority to repair a path is
missing, the cycle is blocked and must not be described as complete. Every Full
cycle ends with clean repositories, pushed reachable commits, deployment where
deployable, verified tags moved to the verified commits where the project keeps
them, and a final real-surface test after the last change.
