# Shared checkout safety

Routine LHC work happens in the current primary project checkout, not in hidden
branches or scattered harness worktrees. The project contains its own work.

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

Do not create, switch, merge, or delete a branch or worktree merely for
isolation, cleanliness, review, or routine task work. Those are explicit human
authorization boundaries.

When the user explicitly requests a new worktree, create it only at:

```text
<primary-project-root>/.worktrees/<task-slug>
```

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
tip; report any divergence and do not silently merge, rebase, or discard it.

Unified history: review every change, fix every unsafe or unreviewable item,
and commit the complete repaired result into one reachable history. Never call
a Full cycle complete with any modified, deleted, untracked, ignored-by-accident,
or dirty nested-repository path. If required authority to repair a path is
missing, the cycle is blocked and must not be described as complete. Every Full
cycle ends with clean repositories, pushed reachable commits, deployment where
deployable, and a final real-surface test after the last change.
