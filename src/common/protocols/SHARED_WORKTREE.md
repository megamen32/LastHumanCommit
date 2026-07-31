# Shared worktree

I assume I am not working alone. A dirty worktree is evidence of concurrent
human or agent work, not damage to clean up.

## Default safety

At the start, before changing a file, and immediately before staging or
committing, inspect `git status --short`, staged and unstaged diffs, and
untracked files. For a modified or untracked path that exists, inspect its
mtime.

- A file changed within five minutes is probably currently being edited. Do not
  edit, stage, rename, delete, format, or include it in a commit. Report the
  collision and continue on independent paths.
- A foreign change older than five minutes is an integration candidate, not
  abandoned work. Leave it intact until final review.
- Missing paths, renames, binary files, generated outputs, unknown ownership,
  and any mtime uncertainty are hands-off until L can review or ask the human.

Never use `git stash`, `git reset`, `git clean`, `git restore`, `git checkout
--`, `git revert`, force-push, or a rollback to remove work that I did not
create. An explicit human request may authorize one named target only; inspect
and state that exact target before acting.

## L's final integration gate

For every older integration candidate, L performs final review: inspect its
diff and ownership clues, recheck mtime, run the relevant validation, and check
for secrets, generated noise, conflicts, or an unresolved failure. If review
passes, include it in L's commit with the task's changes, and mention it in the
Russian summary. Do not split it away merely to make the worktree look clean.

If it became fresh, cannot be reviewed, contains a secret, or conflicts with
the requested outcome, do not touch it or use cleanup commands. Report the
exact blocker and ask the human when a decision is needed.
