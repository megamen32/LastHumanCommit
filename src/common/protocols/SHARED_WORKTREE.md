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

## Concurrent-edit safety

Assume the checkout may contain concurrent human or agent work. A dirty checkout
is evidence to preserve, not damage to clean up.

At start, before changing a path, and before staging or committing, inspect
`git status --short`, staged/unstaged diffs, untracked files, and mtime where
available.

- A foreign path changed within five minutes is probably active. Do not edit,
  stage, rename, delete, format, or include it. Report the collision and continue
  only on independent paths.
- Older foreign changes are still foreign. Do not assume they are abandoned or
  fold them into the current task.
- Missing paths, renames, binaries, generated output, unknown ownership, or mtime
  uncertainty are hands-off until L can ask the user.

Never use `git stash`, `git reset`, `git clean`, `git restore`, `git checkout
--`, `git revert`, force-push, or rollback to remove work not created by this
task. An explicit human request may authorize one named target only.

## Final integration

Stage and commit only reviewed task-owned paths. Never stage or commit foreign
edits merely because they are old, safe-looking, or already present in the
checkout. Report them separately. Including one foreign change requires an
explicit user instruction naming that change.
