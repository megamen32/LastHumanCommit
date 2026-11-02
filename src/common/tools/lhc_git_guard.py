#!/usr/bin/env python3
"""Deterministic guard for the git commands that lose or hide work.

Two rules, both decided from the command text and the repository layout only
(no judgement of what the agent "meant"):

1. git stash is banned for everyone, in every form, including --autostash and
   rebase.autoStash / merge.autoStash set with -c. A stash hides work where neither the
   next session nor the owner looks for it; commit it on the task branch instead.
2. A branch is switched or created only in a linked worktree. The primary checkout
   stays on the branch it has, because other sessions and the live service read it.

The guard fails open: a command it cannot parse, or a directory that is not a
repository, is allowed.
"""
from __future__ import annotations

import os
import shlex
import subprocess

SEPARATORS = {"&&", "||", ";", ";;", "|", "&", "(", ")", "|&"}
WRAPPERS = {"sudo", "command", "env", "time", "nohup", "exec", "nice", "builtin"}
SHELLS = {"bash", "sh", "zsh", "dash"}
GLOBAL_WITH_VALUE = {"-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix", "--config-env",
                     "--exec-path", "--attr-source"}
AUTOSTASH_CONFIG = ("rebase.autostash", "merge.autostash")

STASH_REASON = (
    "LHC: `git stash` is banned (also --autostash and rebase.autoStash). A stash hides work where the next "
    "session and the owner do not look, and it has already buried another session's changes. Commit it on "
    "your task branch instead: `git add -A && git commit -m \"wip: <why>\"` and push. To change context, "
    "open a second worktree."
)
SWITCH_REASON = (
    "LHC: do not switch or create branches in the primary checkout; it stays on its branch (other sessions "
    "and the running service read it). Do it in a linked worktree: `python3 <lhc>/tools/lhc_worktree.py "
    "assignment --repo . --task <slug> --base origin/main --create`, or `git worktree add`. Keep one "
    "worktree per session and switch task branches there: `git switch -c <task> origin/main`."
)


def _git(directory: str, *args: str) -> str:
    try:
        done = subprocess.run(["git", "-C", directory, *args], capture_output=True, text=True, timeout=3)
    except (OSError, subprocess.SubprocessError):
        return ""
    return done.stdout.strip() if done.returncode == 0 else ""


def is_primary_checkout(directory: str) -> bool:
    """True when directory is the main working tree of a repository (not a linked worktree)."""
    lines = _git(directory, "rev-parse", "--path-format=absolute", "--git-dir", "--git-common-dir").splitlines()
    if len(lines) != 2:
        return False
    return os.path.realpath(lines[0]) == os.path.realpath(lines[1])


def _is_ref(directory: str, name: str) -> bool:
    return bool(name == "-" or _git(directory, "rev-parse", "--verify", "--quiet", "--end-of-options", name + "^{commit}"))


def _segments(command: str) -> list[list[str]]:
    """Split a shell command into simple commands; unparsable lines are skipped (fail open)."""
    out: list[list[str]] = []
    for line in command.splitlines():
        if not line.strip():
            continue
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars=True)
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            continue
        current: list[str] = []
        for token in tokens:
            if token in SEPARATORS:
                if current:
                    out.append(current)
                current = []
            else:
                current.append(token)
        if current:
            out.append(current)
    return out


def _git_call(tokens: list[str]) -> int | None:
    """Index of the git word in a simple command, skipping env assignments and wrappers."""
    for index, token in enumerate(tokens):
        if token in WRAPPERS or ("=" in token and not token.startswith("-") and "/" not in token.split("=", 1)[0]):
            continue
        if os.path.basename(token) == "git":
            return index
        return None
    return None


def _check_git(tokens: list[str], directory: str) -> str | None:
    index = 1
    here = directory
    autostash_config = False
    while index < len(tokens):
        token = tokens[index]
        if token == "-C" and index + 1 < len(tokens):
            here = os.path.normpath(os.path.join(here, os.path.expanduser(tokens[index + 1])))
            index += 2
        elif token == "-c" and index + 1 < len(tokens):
            name, _, value = tokens[index + 1].partition("=")
            if name.lower() in AUTOSTASH_CONFIG and value.strip().lower() not in ("false", "0", "no", "off"):
                autostash_config = True
            index += 2
        elif token.split("=", 1)[0] in GLOBAL_WITH_VALUE:
            index += 1 if "=" in token else 2
        elif token.startswith("-"):
            index += 1
        else:
            break
    if index >= len(tokens):
        return None
    sub, args = tokens[index], tokens[index + 1:]
    if sub == "stash" or "--autostash" in args or (autostash_config and sub in ("pull", "rebase", "merge")):
        return STASH_REASON
    if sub == "switch" and is_primary_checkout(here):
        return SWITCH_REASON
    if sub == "checkout" and "--" not in args:
        positional = [a for a in args if not a.startswith("-")]
        creates = any(a in ("-b", "-B", "--orphan") or a.startswith("--orphan=") for a in args)
        if (creates or (len(positional) == 1 and _is_ref(here, positional[0]))) and is_primary_checkout(here):
            return SWITCH_REASON
    return None


def check(command: str, cwd: str, _depth: int = 0) -> str | None:
    """Return the reason a command must not run, or None."""
    if not isinstance(command, str) or not command.strip() or _depth > 2:
        return None
    here = cwd or os.getcwd()
    for tokens in _segments(command):
        if tokens[0] == "cd" and len(tokens) > 1 and tokens[1] not in ("-", "~") and not tokens[1].startswith("$"):
            here = os.path.normpath(os.path.join(here, os.path.expanduser(tokens[1])))
            continue
        index = _git_call(tokens)
        if index is not None:
            reason = _check_git(tokens[index:], here)
            if reason:
                return reason
            continue
        # sh -c "git stash" and friends: look inside the quoted script.
        if os.path.basename(tokens[0]) in SHELLS:
            flags = [i for i, t in enumerate(tokens[1:-1], 1) if t.startswith("-") and not t.startswith("--") and "c" in t]
            if flags:
                reason = check(tokens[flags[0] + 1], here, _depth + 1)
                if reason:
                    return reason
    return None


BASH_TOOLS = {"bash", "shell", "exec_command", "local_shell", "run_shell_command"}


def command_of(event: dict) -> str:
    """The shell command of a PreToolUse event from any native runtime, or an empty string."""
    if str(event.get("tool_name") or event.get("tool") or "").lower() not in BASH_TOOLS:
        return ""
    data = event.get("tool_input") or event.get("args") or {}
    value = data.get("command") or data.get("cmd") or ""
    if isinstance(value, list):
        value = " ".join(str(part) for part in value)
    return value if isinstance(value, str) else ""


if __name__ == "__main__":
    import json
    import sys
    event = json.loads(sys.stdin.read() or "{}")
    reason = check(command_of(event), str(event.get("cwd") or os.getcwd()))
    print(json.dumps({"decision": "block", "reason": reason}) if reason else "")
