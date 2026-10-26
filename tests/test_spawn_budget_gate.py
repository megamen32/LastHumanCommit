"""The spawn budget is a gate, and this proves that it still bites.

The budget in ``conftest.py`` is the only thing that keeps the suite honest
about the number of processes it starts.  A budget that nothing ever
exceeded is not a gate: it is a comment.  So this file runs a small session
on purpose, with a budget the session cannot meet, and requires that the
session fails and says why.

The proof costs one interpreter start and one Git repository of its own.  It
is the price of knowing that the gate is alive.
"""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]

#: The budget the proving session is given.  Any budget below the number of
#: processes a session starts on its own must fail the session; zero is the
#: clearest of them.
IMPOSSIBLE_BUDGET = 0


def _run_session(path: Path, budget: str) -> subprocess.CompletedProcess:
    """Run one pytest session over one file, with the given spawn budget."""

    environment = dict(os.environ)
    environment["LHC_SPAWN_BUDGET"] = budget
    # The report goes to the terminal of the child, which the parent reads.
    environment.pop("LHC_SPAWN_REPORT", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", str(path), "-q", "--no-header",
         "-p", "no:cacheprovider"],
        cwd=str(ROOT), capture_output=True, text=True, env=environment,
    )


def test_a_session_that_exceeds_the_budget_fails_the_session(tmp_path):
    """A session over the budget fails, and says that the budget is a gate.

    The file under test lives inside the project, so the session loads the
    project's own ``conftest.py`` - the very gate that has to bite.  The
    budget is one below what a session starts on its own, so the session
    cannot pass by accident.
    """

    case = ROOT / ".tmp" / "spawn-budget-proof"
    case.mkdir(parents=True, exist_ok=True)
    proof = case / "test_the_gate_bites.py"
    proof.write_text(
        "def test_the_case_itself_passes():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    try:
        completed = _run_session(proof, str(IMPOSSIBLE_BUDGET))
    finally:
        proof.unlink(missing_ok=True)

    output = completed.stdout + completed.stderr
    assert completed.returncode != 0, (
        "a session over the spawn budget must fail, but it passed:\n" + output
    )
    assert "BUDGET EXCEEDED" in output, (
        "the session must say that the budget was exceeded:\n" + output
    )


def test_a_session_within_the_budget_passes(tmp_path):
    """The same session, with a budget it can meet, passes.

    Without this, the case above would also pass for a session that simply
    cannot run - a broken session would look like a working gate.
    """

    case = ROOT / ".tmp" / "spawn-budget-proof"
    case.mkdir(parents=True, exist_ok=True)
    proof = case / "test_the_gate_bites.py"
    proof.write_text(
        "def test_the_case_itself_passes():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    try:
        completed = _run_session(proof, "100000")
    finally:
        proof.unlink(missing_ok=True)

    output = completed.stdout + completed.stderr
    assert completed.returncode == 0, (
        "a session within the spawn budget must pass:\n" + output
    )
    assert "BUDGET EXCEEDED" not in output, output
