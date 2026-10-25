#!/usr/bin/env python3
"""Budget tests for the process spawns of the worktree, the mailbox and the hook.

Three places of the tools used to start a process for a question that the
files on the disk already answer:

* the worktree tool asked the git binary for the shared git directory, for the
  listing of the worktrees and for the git directory of a checkout,
* the mailbox asked the git binary for the same three questions, and
* the time guard started a second interpreter to read the report of the
  interval ledger, although the ledger is a neighbour that answers the same
  report from this process.

The answers are facts about the directories on the disk, so they are read from
there.  These tests hold three properties of that change:

* the questions start no process at all,
* the answers are the answers of git, path for path, for every shape of a
  repository, and
* the answers are never stale: they follow the layout of the moment, not the
  layout of an earlier call.

One question is still asked of the git binary: the base of a worktree is a
revision expression that git parses with its own revision grammar, so that
one answer keeps coming from git.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import types

import pytest

from _repos import prepared_repo


ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src/common/tools"

if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))
if str(ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(ROOT / "tests"))


def _load(name: str, module_name: str):
    """Load one tool by path, the way the tests load it."""

    spec = importlib.util.spec_from_file_location(module_name, TOOLS / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _git(*arguments: str, cwd: Path | None = None) -> str:
    """Run one git command and return its output."""

    completed = subprocess.run(
        ["git", *arguments],
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


# Measured after the change: the plan of the canonical worktree asks git for
# one question only - the base commit, which is a revision expression.
WORKTREE_PLAN_BUDGET = 1

# Measured after the change: the creation asks git for the base commit and
# for the four changes it makes to the repository.
WORKTREE_CREATE_BUDGET = 5

# Measured after the change: the mailbox asks git for nothing at all.
CHAT_BUDGET = 0

# Measured after the change: the hook starts no interpreter for the report of
# the interval ledger and no process of any kind.
HOOK_BUDGET = 0


# The answers about the layout of a repository.  The canon defines each of
# them once, in the reader of the layout; the tools that need one ask it.
LAYOUT_ANSWERS = (
    "common_dir_of",
    "absolute_git_dir",
    "worktree_list_porcelain",
    "primary_worktree",
    "worktree_root",
    "current_branch",
    "discover_git_dir",
    "discover",
)

# The class that names a repository.  It belongs to the reader of the layout
# for the same reason the answers do.
LAYOUT_CLASSES = ("Repository",)

# The module that owns the answers about the layout.
CANON_READER = "lhc_gitlayout.py"

# The modules that answer questions about a repository.  A second
# implementation of one of the answers in any of them is a copy that drifts.
REPOSITORY_MODULES = ("lhc_gitlayout.py", "lhc_time_guard.py", "lhc_git_facts.py",
                      "lhc_milestone.py")


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


def _git_spawns(started: list[list[str]]) -> list[list[str]]:
    """The git processes out of the recorded ones."""

    return [entry for entry in started if entry and Path(entry[0]).name == "git"]


def _interpreter_spawns(started: list[list[str]]) -> list[list[str]]:
    """The interpreter processes out of the recorded ones."""

    return [entry for entry in started if entry and Path(entry[0]).name.startswith("python")]


def _repository(root: Path, name: str) -> Path:
    """Create one plain repository with a committed head.

    The checkout is a copy of a prepared template: the same branch, the same
    identity and the same committed head a checkout built by hand would have
    had, without every case paying for the build again.
    """

    return prepared_repo(
        root / name,
        branch="main",
        config=(("user.name", "Fixture"),
                ("user.email", "fixture@example.test")),
        files=(("owned.py", "value = 1\n"),),
        message="fixture",
    )


def _repository_shapes(root: Path) -> list[tuple[str, Path]]:
    """Create every shape of a repository the tools have to answer for."""

    main = _repository(root, "main")
    linked = root / "linked"
    _git("-C", str(main), "worktree", "add", "-q", str(linked), "-b", "feature")
    detached = root / "detached"
    _git("-C", str(main), "worktree", "add", "-q", "--detach", str(detached))
    nested = main / "nested" / "deeper"
    nested.mkdir(parents=True)
    separate_work = root / "separate-work"
    separate_work.mkdir()
    _git("init", "-q", "--separate-git-dir", str(root / "separate.git"), str(separate_work))
    bare = root / "bare.git"
    _git("init", "-q", "--bare", str(bare))
    unborn = root / "unborn"
    _git("init", "-q", "-b", "main", str(unborn))
    outside = root / "outside"
    outside.mkdir()
    return [("main", main), ("nested", nested), ("linked", linked), ("detached", detached),
            ("separate", separate_work), ("bare", bare), ("unborn", unborn), ("outside", outside)]


# --------------------------------------------------------------------------
# The questions that start no process
# --------------------------------------------------------------------------


def test_the_plan_of_a_worktree_asks_git_for_the_base_only(tmp_path, spawns) -> None:
    """The layout of the repository is read from the disk."""

    worktree = _load("lhc_worktree", "lhc_worktree_spawn_budget")
    repository = _repository(tmp_path, "primary")
    spawns.clear()

    plan = worktree.assignment(repository, "lane-one", None, False)

    assert plan["primary"] == str(repository)
    started = _git_spawns(spawns)
    assert len(started) <= WORKTREE_PLAN_BUDGET, (
        f"the worktree plan started {len(started)} git processes, budget is "
        f"{WORKTREE_PLAN_BUDGET}: {started}"
    )


def test_the_creation_of_a_worktree_asks_git_for_the_base_only(tmp_path, spawns) -> None:
    """The creation keeps the four processes that change the repository."""

    worktree = _load("lhc_worktree", "lhc_worktree_create_spawn_budget")
    repository = _repository(tmp_path, "primary")
    (repository / ".gitignore").write_text(".worktrees/\n", encoding="utf-8")
    _git("-C", str(repository), "add", ".gitignore")
    _git("-C", str(repository), "commit", "-qm", "ignore")
    spawns.clear()

    result = worktree.assignment(repository, "lane-one", "HEAD", True)

    assert result["action"] == "created"
    started = _git_spawns(spawns)
    assert len(started) <= WORKTREE_CREATE_BUDGET, (
        f"the worktree creation started {len(started)} git processes, budget is "
        f"{WORKTREE_CREATE_BUDGET}: {started}"
    )


def test_the_mailbox_asks_git_for_nothing(tmp_path, spawns) -> None:
    """The primary checkout of the mailbox is found on the disk."""

    chat = _load("lhc_chat", "lhc_chat_spawn_budget")
    repository = _repository(tmp_path, "primary")
    spawns.clear()

    primary = chat.project_root(repository)

    assert primary == repository
    started = _git_spawns(spawns)
    assert len(started) <= CHAT_BUDGET, (
        f"the mailbox started {len(started)} git processes, budget is {CHAT_BUDGET}: {started}"
    )


def test_the_hook_reads_the_interval_ledger_without_an_interpreter(tmp_path, spawns) -> None:
    """The report of the ledger is read in this process, not in a second one."""

    from _inprocess_lane import run_tool

    project = _repository(tmp_path, "primary")
    card = project / ".agents/tasks/work-spawn-budget.md"
    card.parent.mkdir(parents=True)
    started_at = datetime.now(timezone.utc) - timedelta(seconds=2)
    card.write_text(
        "# Spawn budget\nStatus: in progress\n"
        f"- Started at: {started_at.isoformat()}\n"
        "- Initial estimate: 5 / 120 active minutes\n", encoding="utf-8")
    session = "spawn-budget-session"
    ledger = (project / ".agents/shared-session/time" /
              f"{card.stem}-{hashlib.sha256(session.encode()).hexdigest()[:12]}.active.json")
    ledger.parent.mkdir(parents=True, exist_ok=True)
    opened = run_tool("lhc_active_time", ["start", "--state", str(ledger), "--actor", session,
                                          "--task", card.stem], cwd=project)
    opened.check_returncode()
    spawns.clear()

    hook = run_tool("lhc_time_guard", ["hook", "--runtime", "codex", "--event", "UserPromptSubmit"],
                    stdin=json.dumps({"cwd": str(project), "session_id": session,
                                      "hook_event_name": "UserPromptSubmit",
                                      "prompt": "Report actual active time and coverage."}),
                    cwd=project)

    hook.check_returncode()
    assert "source=interval-ledger" in hook.stdout, hook.stdout
    interpreters = _interpreter_spawns(spawns)
    assert not interpreters, f"the hook started an interpreter: {interpreters}"
    assert len(spawns) <= HOOK_BUDGET, (
        f"the hook started {len(spawns)} processes, budget is {HOOK_BUDGET}: {spawns}"
    )


# --------------------------------------------------------------------------
# The answers are the answers of git
# --------------------------------------------------------------------------


def test_the_layout_answers_are_the_answers_of_git(tmp_path) -> None:
    """Every shape of a repository answers exactly what git answers."""

    layout = _load("lhc_gitlayout", "lhc_gitlayout_spawn_budget")
    for name, directory in _repository_shapes(tmp_path):
        common = _git("-C", str(directory), "rev-parse", "--path-format=absolute",
                      "--git-common-dir")
        if common.strip():
            assert layout.common_dir_of(directory) == Path(common.strip()).resolve(), name
        absolute = _git("-C", str(directory), "rev-parse", "--absolute-git-dir")
        if absolute.strip():
            assert layout.absolute_git_dir(directory) == Path(absolute.strip()).resolve(), name
        listing = _git("-C", str(directory), "worktree", "list", "--porcelain")
        answer = layout.worktree_list_porcelain(layout.common_dir_of(directory))
        assert answer is not None, name
        assert answer.strip() == listing.strip(), name


def test_the_plan_answers_what_git_answers(tmp_path) -> None:
    """The plan of a worktree answers the paths of the repository."""

    worktree = _load("lhc_worktree", "lhc_worktree_plan_answer")
    repository = _repository(tmp_path, "primary")
    common = _git("-C", str(repository), "rev-parse", "--path-format=absolute",
                  "--git-common-dir").strip()
    listing = _git("--git-dir", common, "worktree", "list", "--porcelain")
    primary = next(line.removeprefix("worktree ") for line in listing.splitlines()
                   if line.startswith("worktree "))
    base = _git("-C", str(repository), "rev-parse", "--verify", "--end-of-options",
                "HEAD^{commit}").strip()

    plan = worktree.assignment(repository, "lane-one", None, False)

    assert plan["primary"] == str(Path(primary).resolve())
    assert plan["common_dir"] == str(Path(common).resolve())
    assert plan["base"] == base
    assert plan["branch"] == "lhc/lane-one"
    assert plan["path"] == str(Path(primary).resolve() / ".worktrees/lane-one")


def test_the_layout_follows_a_repointed_git_directory(tmp_path) -> None:
    """A lookup must never answer from the layout of an earlier call."""

    layout = _load("lhc_gitlayout", "lhc_gitlayout_stale")
    repository = _repository(tmp_path, "primary")
    other = _repository(tmp_path, "other")
    before = layout.common_dir_of(repository)
    assert before == (repository / ".git").resolve()

    shutil.rmtree(repository / ".git")
    (repository / ".git").write_text(f"gitdir: {other / '.git'}\n", encoding="utf-8")

    after = layout.common_dir_of(repository)
    assert after == (other / ".git").resolve()
    assert after != before
    assert after == Path(_git("-C", str(repository), "rev-parse", "--path-format=absolute",
                              "--git-common-dir").strip()).resolve()


def test_the_layout_follows_a_removed_git_directory(tmp_path) -> None:
    """A directory that stops being a repository is read the way git reads it."""

    layout = _load("lhc_gitlayout", "lhc_gitlayout_removed")
    repository = _repository(tmp_path, "primary")
    before = layout.common_dir_of(repository)
    assert before is not None

    shutil.rmtree(repository / ".git")

    after = layout.common_dir_of(repository)
    expected = _git("-C", str(repository), "rev-parse", "--path-format=absolute",
                    "--git-common-dir").strip()
    assert after == Path(expected).resolve()
    assert after != before


def test_a_locked_worktree_is_answered_by_the_git_binary(tmp_path, spawns) -> None:
    """A layout the reader does not model keeps the answer of the git binary."""

    worktree = _load("lhc_worktree", "lhc_worktree_locked")
    repository = _repository(tmp_path, "primary")
    locked = tmp_path / "locked"
    _git("-C", str(repository), "worktree", "add", "-q", str(locked), "-b", "locked")
    _git("-C", str(repository), "worktree", "lock", str(locked))
    spawns.clear()

    plan = worktree.assignment(repository, "lane-one", None, False)

    assert plan["primary"] == str(repository)
    started = _git_spawns(spawns)
    assert len(started) <= WORKTREE_PLAN_BUDGET + 2, (
        f"the worktree plan started {len(started)} git processes for a locked "
        f"worktree: {started}"
    )


def test_the_tools_work_without_the_reader(tmp_path, spawns, monkeypatch) -> None:
    """A package without the reader keeps the answer of the git binary.

    The reader is a separate file, so a package that does not carry it yet
    still answers every question - it only asks the git binary for it.
    """

    stage = tmp_path / "stage"
    stage.mkdir()
    shutil.copy(TOOLS / "lhc_worktree.py", stage / "lhc_worktree.py")
    repository = _repository(tmp_path, "primary")
    expected_base = _git("-C", str(repository), "rev-parse", "--verify",
                         "--end-of-options", "HEAD^{commit}").strip()
    # The reader must not be found anywhere: the name is blocked, so the
    # import fails even when another test left a copy of it on the path.
    monkeypatch.setitem(sys.modules, "lhc_gitlayout", None)
    saved_path = sys.path[:]
    sys.path[:] = [entry for entry in sys.path if entry != str(TOOLS)]
    try:
        spec = importlib.util.spec_from_file_location(
            "lhc_worktree_without_reader", stage / "lhc_worktree.py")
        assert spec is not None and spec.loader is not None
        worktree = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(worktree)
        spawns.clear()

        plan = worktree.assignment(repository, "lane-one", None, False)
    finally:
        sys.path[:] = saved_path

    assert worktree.git_layout() is None
    assert plan["primary"] == str(repository)
    assert plan["base"] == expected_base
    started = _git_spawns(spawns)
    assert len(started) <= 4, (
        f"the worktree plan without the reader started {len(started)} git "
        f"processes: {started}"
    )


def _asks_the_reader(node: ast.FunctionDef, module) -> bool:
    """Whether a definition only asks the reader of the layout for an answer.

    A definition outside the reader is a request when it does nothing but
    return the answer of the reader: its body is a docstring and one return,
    and the return asks the reader for the very same answer.  A body with
    any other statement is a second implementation of the answer.
    """

    body = list(node.body)
    if (body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    if len(body) != 1 or not isinstance(body[0], ast.Return):
        return False
    value = body[0].value
    if isinstance(value, ast.IfExp):
        # `return reader.answer(...) if reader is not None else None`
        value = value.body
    if not isinstance(value, ast.Call) or not isinstance(value.func, ast.Attribute):
        return False
    if value.func.attr != node.name:
        return False
    base = value.func.value
    if not isinstance(base, ast.Name):
        return False
    reader = getattr(module, base.id, None)
    if not isinstance(reader, types.ModuleType):
        return False
    return Path(getattr(reader, "__file__", "")).name == CANON_READER


def test_the_layout_answers_are_defined_once_in_the_canon(tmp_path) -> None:
    """One canon, one implementation of the answers about the layout.

    The reader of the layout owns these answers.  A second definition in any
    other module of the canon is a copy that drifts from the answers of git,
    so the canon does not carry one: a module that needs an answer asks the
    reader for it and returns what the reader answered.
    """

    for name in REPOSITORY_MODULES:
        module = _load(name.replace(".py", ""), f"lhc_consolidation_{name[:-3]}")
        tree = ast.parse((TOOLS / name).read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in LAYOUT_CLASSES:
                assert name == CANON_READER, (
                    f"{name} defines the class {node.name} itself; the canon has "
                    f"one such class, in {CANON_READER}"
                )
            if isinstance(node, ast.FunctionDef) and node.name in LAYOUT_ANSWERS:
                if name == CANON_READER:
                    continue
                assert _asks_the_reader(node, module), (
                    f"{name} answers {node.name} itself; the canon has one answer "
                    f"for it, in {CANON_READER}"
                )

    tree = ast.parse((TOOLS / CANON_READER).read_text(encoding="utf-8"))
    defined = sorted(node.name for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef) and node.name in LAYOUT_ANSWERS)
    assert defined == sorted(LAYOUT_ANSWERS), (
        f"the reader of the layout must define every answer exactly once, it "
        f"defines {defined}"
    )
    classes = sorted(node.name for node in ast.walk(tree)
                     if isinstance(node, ast.ClassDef) and node.name in LAYOUT_CLASSES)
    assert classes == sorted(LAYOUT_CLASSES), (
        f"the reader of the layout must define the class of a repository, it "
        f"defines {classes}"
    )

    # The repository the milestone works on is the repository of the reader,
    # not a copy of it that answers the same questions on its own.
    milestone = _load("lhc_milestone", "lhc_consolidation_milestone")
    assert milestone.layout is not None, "the milestone must ask the reader of the layout"
    assert Path(milestone.layout.__file__).name == CANON_READER
    repository = _repository(tmp_path, "primary")
    found = milestone.discover(repository)
    assert found is not None
    assert isinstance(found, milestone.layout.Repository), (
        "the milestone must work on the repository of the reader, it works on "
        f"{type(found).__name__}"
    )
    assert found.gitdir == repository / ".git"
