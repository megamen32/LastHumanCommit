# Shared project checkout

The project should contain its own work. Routine LHC work happens in the current
primary checkout, not in hidden branches or scattered harness worktrees.

## Workspace identity

At task start inspect:

- current repository root;
- `git worktree list --porcelain`;
- current branch or detached HEAD;
- the default branch when it can be identified.

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

Assume I am not working alone. A dirty checkout is evidence of concurrent human
or agent work, not damage to clean up.

At start, before changing a path, and before staging or committing, inspect
`git status --short`, staged/unstaged diffs, untracked files, and mtime where
available.

- A foreign path changed within five minutes is probably being edited. Do not
  edit, stage, rename, delete, format, or include it. Report the collision and
  continue only on independent paths.
- An older foreign change is an integration candidate, not abandoned work. Leave
  it intact until L's final review.
- Missing paths, renames, binaries, generated output, unknown ownership, or mtime
  uncertainty are hands-off until L can review or ask the user.

Never use `git stash`, `git reset`, `git clean`, `git restore`, `git checkout
--`, `git revert`, force-push, or rollback to remove work I did not create. An
explicit human request may authorize one named target only.

## Final integration

For every older integration candidate L inspects its diff and ownership clues,
rechecks mtime, runs relevant validation, and checks for secrets, generated
noise, conflicts, or unresolved failure. If reviewed-safe, L may include it in
the same commit and names it in the Russian summary. Fresh, unknown, conflicting,
or unreviewable work remains untouched and is reported as a blocker.
