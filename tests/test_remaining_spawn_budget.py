#!/usr/bin/env python3
"""Budget tests for the process spawns that are left in the LHC tools.

The active-interval ledger asked the kernel for its boot time by starting the
``sysctl`` program, and it asked on every call of the ledger.  The ledger is
called by the entry point of every native event, so that one question was the
single most expensive thing in the test suite on macOS, where the program
costs 15-25 ms.

The kernel keeps the boot time in the ``kern.boottime`` system control, and
the ledger now reads it inside its own process: through libc on macOS and from
``/proc/stat`` on Linux.  The ``sysctl`` program stays as the honest fallback
for a kernel that refuses the question.

These tests hold three properties of that change:

* the ledger starts no process at all for the boot time,
* the ledger answers exactly what the ``sysctl`` program answers, and
* the ledger still answers the same when the process free read is refused.

The last section records the git processes the worktree and the mailbox still
start.  They are measured, not yet reduced: the budget is the fact of today,
so a change that makes them worse is caught.
"""

from __future__ import annotations

import importlib.util
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest

from _repos import prepared_repo


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))


def _load(name: str, module_name: str):
    """Load one tool by path, the way the tests load it."""

    spec = importlib.util.spec_from_file_location(module_name, TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TIMER = _load("lhc_active_time", "lhc_active_time_spawn_budget")

# Measured after the change: one boot identity starts no process at all.
SPAWN_BUDGET = 0

# Measured today: a plan of the canonical worktree starts four git processes
# (the common directory, the worktree listing, the git directory of the
# primary checkout and the resolved base commit).
WORKTREE_GIT_BUDGET = 4

# Measured today: the primary checkout of the mailbox starts three git
# processes (the common directory, the worktree listing and the git
# directory of the primary checkout).
CHAT_GIT_BUDGET = 3

IS_DARWIN = sys.platform == "darwin"


@pytest.fixture
def spawns(monkeypatch) -> list[list[str]]:
    """Record every process the code under test starts."""

    started: list[list[str]] = []
    original_run = subprocess.run

    def counting_run(arguments, *positional, **keywords):
        if isinstance(arguments, (list, tuple)) and arguments:
            started.append([str(value) for value in arguments])
        elif isinstance(arguments, str):
            started.append([arguments])
        return original_run(arguments, *positional, **keywords)

    monkeypatch.setattr(subprocess, "run", counting_run)
    return started


def _sysctl_program() -> str:
    """Ask the kernel for its boot time the way the ledger used to."""

    completed = subprocess.run(["/usr/sbin/sysctl", "-n", "kern.boottime"],
                               capture_output=True, text=True, check=True)
    return completed.stdout


def _program_identity(output: str) -> str:
    """Read the boot identity out of the output of the program."""

    match = re.search(r"sec\s*=\s*(\d+),\s*usec\s*=\s*(\d+)", output)
    assert match is not None, output
    return ":".join(match.groups())


def _repository(root: Path, name: str) -> Path:
    """Create one plain repository with a committed head.

    The checkout is a copy of a prepared template: the same branch, the same
    identity and the same committed head a checkout built by hand would have
    had, without every case paying for the build again.
    """

    return prepared_repo(
        root / name,
        config=(("user.name", "Fixture"),
                ("user.email", "fixture@example.test")),
        files=(("owned.py", "value = 1\n"),),
        message="fixture",
    )


# --------------------------------------------------------------------------
# The boot time
# --------------------------------------------------------------------------


def test_boot_identity_starts_no_process(spawns) -> None:
    """The boot identity is a kernel fact, so it is read, not asked for."""

    identity = TIMER.boot_identity()

    assert identity["id"]
    assert len(spawns) <= SPAWN_BUDGET, (
        f"boot_identity started {len(spawns)} processes, budget is {SPAWN_BUDGET}: {spawns}"
    )


def test_boot_identity_answers_what_the_sysctl_program_answers(spawns) -> None:
    """The answer has to be the answer of the program, byte for byte."""

    if not IS_DARWIN:
        pytest.skip("kern.boottime is a macOS system control")
    expected = _program_identity(_sysctl_program())
    spawns.clear()

    identity = TIMER.boot_identity()

    assert identity["id"].split(":", 1)[1] == expected
    assert identity["source"] == "sysctl kern.boottime + hostname (fallback)"
    assert len(spawns) <= SPAWN_BUDGET, (
        f"boot_identity started {len(spawns)} processes, budget is {SPAWN_BUDGET}: {spawns}"
    )


def test_the_ledger_never_starts_the_sysctl_program(tmp_path, spawns) -> None:
    """A whole ledger cycle - start, status, stop - starts no program."""

    state = tmp_path / "state.json"

    TIMER.operate("start", state, actor="lead", task="spawn-budget")
    TIMER.operate("status", state)
    TIMER.operate("stop", state)

    started = [entry for entry in spawns if Path(entry[0]).name == "sysctl"]
    assert not started, f"the ledger started the sysctl program: {started}"


def test_the_program_still_answers_when_the_kernel_read_is_refused(monkeypatch, spawns) -> None:
    """A kernel that refuses the question is still answered by the program."""

    if not IS_DARWIN:
        pytest.skip("kern.boottime is a macOS system control")
    expected = _program_identity(_sysctl_program())
    monkeypatch.setattr(TIMER, "kernel_boot_time", lambda: None)

    identity = TIMER.boot_identity()

    assert identity["id"].split(":", 1)[1] == expected
    assert identity["source"] == "sysctl kern.boottime + hostname (fallback)"


def test_the_linux_boot_time_agrees_with_the_running_kernel() -> None:
    """On Linux the boot time comes from /proc/stat and agrees with /proc/uptime."""

    if IS_DARWIN:
        pytest.skip("/proc is a Linux interface")
    match = re.search(r"^btime (\d+)$", Path("/proc/stat").read_text(), re.M)
    assert match is not None
    uptime = float(Path("/proc/uptime").read_text().split()[0])
    assert abs((time.time() - uptime) - int(match[1])) < 2.0


# --------------------------------------------------------------------------
# The git processes that are left
# --------------------------------------------------------------------------


def test_the_worktree_plan_starts_only_the_git_processes_it_needs(tmp_path, spawns) -> None:
    """The plan of a canonical worktree still asks git four times."""

    worktree = _load("lhc_worktree", "lhc_worktree_spawn_budget")
    repository = _repository(tmp_path, "primary")
    spawns.clear()

    plan = worktree.assignment(repository, "lane-one", None, False)

    assert plan["primary"] == str(repository)
    assert len(spawns) <= WORKTREE_GIT_BUDGET, (
        f"the worktree plan started {len(spawns)} git processes, budget is "
        f"{WORKTREE_GIT_BUDGET}: {spawns}"
    )


def test_the_mailbox_starts_only_the_git_processes_it_needs(tmp_path, spawns) -> None:
    """The primary checkout of the mailbox still asks git three times."""

    chat = _load("lhc_chat", "lhc_chat_spawn_budget")
    repository = _repository(tmp_path, "primary")
    spawns.clear()

    primary = chat.project_root(repository)

    assert primary == repository
    assert len(spawns) <= CHAT_GIT_BUDGET, (
        f"the mailbox started {len(spawns)} git processes, budget is "
        f"{CHAT_GIT_BUDGET}: {spawns}"
    )
