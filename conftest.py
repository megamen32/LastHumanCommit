"""Keep every pytest invocation in its own project-local temporary root."""

from __future__ import annotations

import collections
import inspect
import os
from pathlib import Path
import secrets
import shutil
import subprocess


PROJECT_ROOT = Path(__file__).resolve().parent


def _project_tmp_root() -> Path:
    project = PROJECT_ROOT.resolve(strict=True)
    root = project / ".tmp"
    if root.is_symlink():
        raise RuntimeError(f"{root} must not be a symlink")
    root.mkdir(parents=True, exist_ok=True)
    resolved = root.resolve(strict=True)
    try:
        resolved.relative_to(project)
    except ValueError as error:
        raise RuntimeError(f"{root} escapes project root {project}") from error
    ignored = subprocess.run(
        ["git", "-C", str(project), "check-ignore", "--quiet", "--", ".tmp/"],
        check=False,
    )
    if ignored.returncode != 0:
        raise RuntimeError(f"{project} must ignore .tmp/ before pytest starts")
    return resolved


def _new_pytest_basetemp() -> Path:
    return _project_tmp_root() / f"pytest-{os.getpid()}-{secrets.token_hex(8)}"


def _init_basetemp_git(config, basetemp: Path) -> bool:
    """Give LHC's path resolver a per-run checkout boundary before tests run."""
    factory = getattr(config, "_tmp_path_factory", None)
    if factory is None:
        return False
    # pytest may have constructed its factory before this conftest selected the
    # project-local basetemp. Bind that exact path and let the factory perform
    # its normal private-directory creation/cleanup once, before adding .git.
    factory._given_basetemp = basetemp
    factory._basetemp = None
    actual = factory.getbasetemp()
    if actual.resolve(strict=True) != basetemp.resolve(strict=True):
        raise RuntimeError(f"pytest selected unexpected basetemp: {actual}")
    subprocess.run(["git", "init", "-q", str(actual)], check=True)
    config._lhc_project_basetemp = actual
    config._lhc_pytest_git_ready = True
    return True


def pytest_configure(config) -> None:
    if _read_budget() is not None:
        _install_spawn_counter()
    basetemp = _new_pytest_basetemp()
    config.option.basetemp = str(basetemp)
    config._lhc_project_basetemp = basetemp
    _init_basetemp_git(config, basetemp)


def pytest_sessionstart(session) -> None:
    config = session.config
    if not getattr(config, "_lhc_pytest_git_ready", False):
        basetemp = getattr(config, "_lhc_project_basetemp", None)
        if not isinstance(basetemp, Path) or not _init_basetemp_git(config, basetemp):
            raise RuntimeError("pytest temporary Git boundary could not be initialized")


def pytest_unconfigure(config) -> None:
    basetemp = getattr(config, "_lhc_project_basetemp", None)
    if not isinstance(basetemp, Path):
        return
    root = _project_tmp_root()
    try:
        basetemp.resolve(strict=False).relative_to(root)
    except ValueError as error:
        raise RuntimeError(f"refusing to clean escaped pytest root: {basetemp}") from error
    if basetemp.name.startswith("pytest-") and basetemp.is_dir():
        shutil.rmtree(basetemp)


# --------------------------------------------------------------------------
# The long lane
#
# The suite has two lanes. The fast lane is the work loop: it must finish in
# seconds, because a plan is written and the work starts in the same breath.
# The long lane is the cases that drive an external process - a CLI
# subprocess, a git operation, a live reviewer chain - and are measured at or
# above half a second each.
#
# These files are the long lane, measured with `pytest tests -q --durations=0`:
#
#   test_outcome_contract.py        237 items   255 s
#   test_native_milestone_gate.py    72 items    85 s
#   test_testing_evidence_reuse.py   59 items    38 s
#   test_codex_lifecycle_delivery.py 34 items   21 s
#   test_autonomy_evidence.py        27 items   19 s
#   test_learning_checkpoint.py      11 items    16 s
#   test_product_root_review.py      11 items   12 s
#   test_project_mapping.py          29 items   11 s
#   test_main_permission_scope.py    25 items    8 s
#   test_time_guard_active_integration.py  9 items  8 s
#   test_source_publication.py       17 items    8 s
#   test_zcode_native_lifecycle.py   11 items    8 s
#   test_worktree.py                 12 items    7 s
#   test_time_guard.py                8 items    6 s
#
# None of these cases is deleted: every gate still runs, on the schedule. The
# work loop stops paying for them.
LONG_LANE_FILES = {
    "test_outcome_contract.py",
    "test_native_milestone_gate.py",
    "test_testing_evidence_reuse.py",
    "test_codex_lifecycle_delivery.py",
    "test_autonomy_evidence.py",
    "test_learning_checkpoint.py",
    "test_product_root_review.py",
    "test_project_mapping.py",
    "test_main_permission_scope.py",
    "test_time_guard_active_integration.py",
    "test_source_publication.py",
    "test_zcode_native_lifecycle.py",
    "test_worktree.py",
    "test_time_guard.py",
}


def pytest_collection_modifyitems(config, items):
    """Put the long lane into the nightly marker, by the file that owns it."""
    for item in items:
        if item.path.name in LONG_LANE_FILES:
            item.add_marker("nightly")


# --------------------------------------------------------------------------
# The spawn budget
#
# The tools under test are ordinary Python, so the cases call them in this
# process. What is left of the process starts is what the suite still pays
# for, and every start costs about 7-220 ms on this machine.
#
# This counter counts the process starts of the session per program, per call
# site and per test file, so a regression that puts the process boundary back
# is visible instead of merely slow.  The count happens where the process is
# really started, so a command that is asked for once is counted once.
#
# It is off unless ``LHC_SPAWN_BUDGET`` is set, so an ordinary run of the
# suite is untouched.  When it is set, the session fails if the budget is
# exceeded:
#
#     LHC_SPAWN_BUDGET=default python3 -m pytest tests -q --no-header
#
# The budget of the suite is the number it spends today; a larger number in
# the environment overrides it for a one-off measurement.  The report is
# written to ``LHC_SPAWN_REPORT`` (default: the terminal).
# --------------------------------------------------------------------------

SPAWN_BUDGET_ENV = "LHC_SPAWN_BUDGET"
SPAWN_REPORT_ENV = "LHC_SPAWN_REPORT"

#: The process starts the suite spends today.  A regression that puts the
#: process boundary back raises this number, and the session fails.
SPAWN_BUDGET = 900

_SPAWN_COUNTS: collections.Counter = collections.Counter()
_SPAWN_BY_FILE: collections.Counter = collections.Counter()
_SPAWN_BY_PROGRAM: collections.Counter = collections.Counter()
_SPAWN_BY_SITE: collections.Counter = collections.Counter()
_SPAWN_BY_PROGRAM_SITE: collections.Counter = collections.Counter()
_SPAWN_CURRENT_FILE = ""


def _spawn_program(args) -> str:
    """The program a subprocess call starts."""

    if isinstance(args, (list, tuple)) and args:
        first = str(args[0])
    elif isinstance(args, str):
        first = args.split()[0] if args.split() else ""
    else:
        first = ""
    return Path(first).name if first else "<empty>"


def _spawn_site() -> str:
    """The place in the tree that asked for the process start.

    The stack is walked outwards until it leaves the ``subprocess`` module and
    the harness helpers, so the site is the code that really asked for the
    process and not the plumbing that carried the request.
    """

    frame = inspect.currentframe()
    try:
        while frame is not None:
            name = Path(frame.f_code.co_filename).name
            if name not in ("subprocess.py", "conftest.py", "_fixture_process.py"):
                return "%s:%d" % (name, frame.f_lineno)
            frame = frame.f_back
        return "<unknown>"
    finally:
        del frame


def _install_spawn_counter():
    """Count every process start of this session.

    The count happens where the process is really started, so a command that
    is asked for once is counted once - whether it is asked for through
    ``run``, through ``check_output`` or through ``Popen`` itself.
    """

    real_run = subprocess.run
    real_popen = subprocess.Popen

    def counted_run(args, *pargs, **kwargs):
        return real_run(args, *pargs, **kwargs)

    def counted_popen(args, *pargs, **kwargs):
        _SPAWN_COUNTS["total"] += 1
        _SPAWN_BY_FILE[_SPAWN_CURRENT_FILE or "<session>"] += 1
        program = _spawn_program(args)
        _SPAWN_BY_PROGRAM[program] += 1
        site = _spawn_site()
        _SPAWN_BY_SITE[site] += 1
        _SPAWN_BY_PROGRAM_SITE[(program, site)] += 1
        return real_popen(args, *pargs, **kwargs)

    subprocess.run = counted_run
    subprocess.Popen = counted_popen


def _read_budget() -> int | None:
    """The budget of this session, or None when the counter is off."""

    raw = os.environ.get(SPAWN_BUDGET_ENV)
    if not raw:
        return None
    if raw == "default":
        return SPAWN_BUDGET
    try:
        return int(raw)
    except ValueError:
        return None


def _spawn_report() -> str:
    lines = ["spawns: " + str(_SPAWN_COUNTS["total"])]
    lines.append("by program:")
    for program, count in _SPAWN_BY_PROGRAM.most_common():
        lines.append("  %5d  %s" % (count, program))
    lines.append("by call site:")
    for site, count in _SPAWN_BY_SITE.most_common():
        lines.append("  %5d  %s" % (count, site))
    lines.append("by program and call site:")
    for (program, site), count in _SPAWN_BY_PROGRAM_SITE.most_common():
        lines.append("  %5d  %-12s %s" % (count, program, site))
    lines.append("by test file:")
    for name, count in _SPAWN_BY_FILE.most_common():
        lines.append("  %5d  %s" % (count, name))
    return "\n".join(lines)


def pytest_runtest_setup(item):
    global _SPAWN_CURRENT_FILE
    _SPAWN_CURRENT_FILE = item.path.name


def pytest_runtest_teardown(item, nextitem):
    global _SPAWN_CURRENT_FILE
    _SPAWN_CURRENT_FILE = ""


def pytest_terminal_summary(terminalreporter):
    budget = _read_budget()
    if budget is None:
        return
    report = _spawn_report()
    destination = os.environ.get(SPAWN_REPORT_ENV)
    if destination:
        Path(destination).write_text(report + "\n", encoding="utf-8")
    terminalreporter.write_sep("=", "spawn budget")
    terminalreporter.write_line(report)
    if _SPAWN_COUNTS["total"] > budget:
        terminalreporter.write_line(
            "BUDGET EXCEEDED: %d spawns, budget %d" % (_SPAWN_COUNTS["total"], budget))
        terminalreporter.write_line("Failing the session: the process budget is a gate.")
        terminalreporter._session.exitstatus = 1
