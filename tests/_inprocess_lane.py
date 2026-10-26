"""Run the LHC command line tools inside the test process.

The tools under ``src/common/tools`` are command line scripts: each one parses
``sys.argv``, reads its payload from ``stdin`` and writes one JSON document to
``stdout``.  Every case that used to spawn ``python3 <tool>.py ...`` paid one
interpreter start (0.2-0.9 s on this machine) plus, for some cases, a fresh
``git init``.  The cases in this lane made hundreds of those calls, which is
why the lane used to take minutes.

This module runs the very same tool code inside the current interpreter and
keeps the observable contract intact:

* the argument vector the CLI would have received,
* the stdin the CLI would have read,
* the environment and the working directory the CLI would have seen,
* stdout, stderr and the exit code the CLI would have produced.

**How the tool body is executed.**  The cached code object of every tool is
executed in a fresh namespace with ``__name__ == "__main__"``.  The tool's own
``if __name__ == "__main__":`` guard therefore runs exactly as it does in a
process: its error text, its exit codes and its ``SystemExit`` all behave the
same, and no guard has to be re-implemented here.  Re-executing the module
body costs 0.02-0.08 ms, so no case pays for a reload and no case inherits the
module state of the case before it.

**Which state leaks.**  The tools keep no call scoped state in their module
globals: the only mutable module level objects are constant lookup tables
(status labels, word lists, stage dependencies) and three lazy caches in
``lhc_time_guard`` (``_GRID_TOOL``, ``_PARALLEL_TOOL``, ``_ACTIVE_TOOL``)
that memoize stateless sibling modules.  The state that a fresh interpreter
would have prevented is therefore the *process* state - argv, stdin, the
environment and the working directory - and that is exactly what
:func:`reset_tool_state` restores.  The learning state of a case lives inside
the case checkout, so it is isolated by the checkout itself.

**Git repositories.**  ``git init`` costs about 27 ms; copying one prepared
template repository costs about 6 ms and produces the same checkout (same
``.git`` layout, same unborn branch, same worktree answers, because the main
worktree of a repository is derived from the location of its ``.git``
directory).  :func:`git_repo` copies that template.

**The git binary.**  The tools spawn git a few thousand times per lane, and on
this machine ``/usr/bin/git`` is an ``xcrun`` stub that spends about 21 ms on
every spawn to resolve the developer directory, while the git it forwards to
needs about 7 ms.  The lane uses that forwarded binary, but only after
proving that it reports the same version and produces byte identical output
for every git command the tools use, so the git under test does not change.
When no such binary can be proven the lane simply keeps the git of the PATH
(see ``tests/_fast_git.py``).

The helpers here are private to this lane.  No other test file may depend on
them.
"""

from __future__ import annotations

import atexit
import contextlib
import io
import json
import os
import runpy
import shlex
import shutil
import subprocess
import sys
import tempfile
import traceback
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from _fast_git import git_environment, use_fast_git
from _fixture_process import cat_file, missing_script_in_process

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "src" / "common" / "tools"

# The sibling tools import each other by bare module name ("import
# lhc_time_guard"), so the tools directory has to be importable.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


class CliResult:
    """The part of ``subprocess.CompletedProcess`` the assertions read."""

    __slots__ = ("args", "returncode", "stdout", "stderr")

    def __init__(self, args, returncode: int, stdout: str, stderr: str) -> None:
        self.args = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self) -> str:
        return (f"CliResult(returncode={self.returncode!r}, "
                f"stdout={self.stdout!r}, stderr={self.stderr!r})")

    def check_returncode(self) -> None:
        if self.returncode:
            raise subprocess.CalledProcessError(
                self.returncode, self.args, self.stdout, self.stderr)


# --------------------------------------------------------------------------
# Tool bodies
# --------------------------------------------------------------------------

_CODE_CACHE: dict[str, object] = {}


def tool_path(name: str) -> Path:
    """The file of one tool under ``src/common/tools``."""

    return TOOLS_DIR / (name + ".py")


def tool_code(name: str):
    """The cached code object of one tool."""

    code = _CODE_CACHE.get(name)
    if code is None:
        path = tool_path(name)
        code = compile(path.read_text(encoding="utf-8"), str(path), "exec")
        _CODE_CACHE[name] = code
    return code


def _fresh_module(name: str) -> types.ModuleType:
    """Execute the tool body in a fresh namespace that looks like ``__main__``.

    The module is registered under its canonical bare name while it runs, so a
    sibling tool that imports it by bare name ("import lhc_time_guard")
    resolves to the very same instance, and so that dataclasses can find their
    own module in ``sys.modules``.

    The body ends with the tool's own ``if __name__ == "__main__":`` guard, so
    executing it is what runs the tool - exactly as in a process.
    """

    path = tool_path(name)
    module = types.ModuleType(name)
    module.__dict__["__name__"] = "__main__"
    module.__dict__["__file__"] = str(path)
    module.__dict__["__package__"] = None
    module.__dict__["__loader__"] = None
    module.__dict__["__spec__"] = None
    previous = sys.modules.get(name)
    sys.modules[name] = module
    try:
        exec(tool_code(name), module.__dict__)
    finally:
        if previous is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = previous
    return module


def _exit_code(code) -> int:
    """Map a ``main()`` result onto the exit code the interpreter would use."""

    if code is None:
        return 0
    if isinstance(code, bool):
        return int(code)
    if isinstance(code, int):
        return code
    return 1


def run_tool(name: str, argv=(), *, stdin=None, env=None, cwd=None) -> CliResult:
    """Run one LHC CLI tool in-process and return its observable result.

    ``argv`` is the argument vector *after* the program name, exactly as it
    would have been passed on the command line.
    """

    argv = [str(item) for item in argv]
    program = str(tool_path(name))
    out, err = io.StringIO(), io.StringIO()
    saved_argv = list(sys.argv)
    saved_stdin = sys.stdin
    saved_environ = dict(os.environ)
    saved_cwd = os.getcwd()
    code = 0
    try:
        if env:
            os.environ.update({str(key): str(value) for key, value in env.items()})
        os.environ.update(git_environment())
        if cwd is not None:
            os.chdir(cwd)
        sys.argv = [program, *argv]
        sys.stdin = io.StringIO(stdin if isinstance(stdin, str) else (stdin or b"").decode())
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            _fresh_module(name)
        code = 0
    except SystemExit as exit_request:
        code = exit_request.code
        if isinstance(code, str):
            err.write(code + "\n")
            code = 1
        else:
            code = _exit_code(code)
    except Exception:  # noqa: BLE001 - the CLI would have died with a traceback
        err.write(traceback.format_exc())
        code = 1
    finally:
        sys.argv = saved_argv
        sys.stdin = saved_stdin
        os.chdir(saved_cwd)
        os.environ.clear()
        os.environ.update(saved_environ)
    return CliResult([program, *argv], code, out.getvalue(), err.getvalue())


# --------------------------------------------------------------------------
# Process state
# --------------------------------------------------------------------------

#: Environment variables the tools read to find their runtime.
TOOL_ENVIRONMENT = ("HOME", "CODEX_HOME", "CLAUDE_PROJECT_DIR", "ZCODE_PLUGIN_ROOT",
                    "CLAUDE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "PLUGIN_ROOT")

_ENVIRONMENT_SNAPSHOT: dict[str, str] | None = None


def reset_tool_state() -> None:
    """Restore the process state a fresh interpreter would have had.

    The tools keep no mutable module state, so the state that leaks between
    cases is the process state: the argument vector, stdin and the environment
    the tools read.  ``run_tool`` already restores all of it around every
    call; this function is the belt and braces reset for a case that reaches
    the tools by another route.
    """

    sys.argv = [sys.argv[0]] if sys.argv else [""]
    for name in TOOL_ENVIRONMENT:
        os.environ.pop(name, None)
    if _ENVIRONMENT_SNAPSHOT is not None:
        os.environ.clear()
        os.environ.update(_ENVIRONMENT_SNAPSHOT)


@contextlib.contextmanager
def tool_environment(root):
    """Give one tool call the HOME/CODEX_HOME its own process would have had."""

    saved = {name: os.environ.get(name) for name in ("HOME", "CODEX_HOME")}
    os.environ["HOME"] = str(Path(root) / "native-home")
    os.environ["CODEX_HOME"] = str(Path(root) / "native-home/.codex")
    try:
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


@pytest.fixture(autouse=True)
def _isolated_tool_state():
    """Give every case of this lane the environment case one started with."""

    global _ENVIRONMENT_SNAPSHOT
    _ENVIRONMENT_SNAPSHOT = dict(os.environ)
    reset_tool_state()
    yield
    reset_tool_state()
    _ENVIRONMENT_SNAPSHOT = None


# --------------------------------------------------------------------------
# Git repositories
# --------------------------------------------------------------------------

_GIT_TEMPLATES: dict[tuple, Path] = {}
_GIT_TEMPLATE_ROOT: Path | None = None


# --------------------------------------------------------------------------
# The git binary
# --------------------------------------------------------------------------

#: Every git of this process uses the binary that was proven to be the same
#: git; see ``tests/_fast_git.py``.
use_fast_git()


def prepare_git_template(repo) -> None:
    """Drop the inert hook samples of a prepared template repository.

    ``git init`` writes fourteen sample hooks that no test ever runs. Copying
    them per case costs four times more than copying the repository without
    them; the default ignore rules in ``info/exclude`` stay untouched, so the
    checkout behaves exactly as before.
    """

    hooks = Path(repo) / ".git" / "hooks"
    if hooks.is_dir():
        for sample in hooks.glob("*.sample"):
            sample.unlink()


def git_template(branch=None, config=()) -> Path:
    """A ready-made Git repository every case copies from.

    The template is prepared once per (branch, config) pair, so a case that
    needs its own branch name or its own identity pays for neither ``git init``
    nor ``git config``.
    """

    global _GIT_TEMPLATE_ROOT
    key = (branch, tuple(config))
    template = _GIT_TEMPLATES.get(key)
    if template is not None:
        return template
    if _GIT_TEMPLATE_ROOT is None:
        _GIT_TEMPLATE_ROOT = Path(tempfile.mkdtemp(prefix="lhc-lane-git-template-"))
        atexit.register(shutil.rmtree, _GIT_TEMPLATE_ROOT, True)
    template = _GIT_TEMPLATE_ROOT / ("repo-" + str(len(_GIT_TEMPLATES)))
    template.mkdir()
    command = ["git", "init", "-q"]
    if branch is not None:
        command += ["-b", branch]
    command.append(str(template))
    subprocess.run(command, check=True, capture_output=True)
    for name, value in config:
        subprocess.run(["git", "-C", str(template), "config", name, value],
                       check=True, capture_output=True)
    prepare_git_template(template)
    _GIT_TEMPLATES[key] = template
    return template


def git_repo(path, branch=None, config=()) -> Path:
    """Give the case its own Git checkout by copying the template."""

    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    template = git_template(branch, config)
    shutil.copytree(template / ".git", target / ".git", dirs_exist_ok=True)
    return target


# --------------------------------------------------------------------------
# The native entry and the outcome CLI
# --------------------------------------------------------------------------

def native_invoke(root, event, **fields):
    """Advance one native session event through the entry CLI.

    The native transcript fixture stays aligned with a real UserPromptSubmit:
    LHC may bind permission only to a role=user message in this journal.
    """

    root = Path(root)
    native_session = root / "native-home/.codex/sessions/leader.jsonl"
    native_session.parent.mkdir(parents=True, exist_ok=True)
    if not native_session.exists():
        native_session.write_text(json.dumps({"type": "session_meta", "payload": {
            "id": "leader", "cwd": str(root.resolve()),
            "timestamp": datetime.now(timezone.utc).isoformat()}}) + "\n")
    if event == "UserPromptSubmit" and isinstance(fields.get("prompt"), str):
        native_row = {"type": "response_item",
                      "timestamp": datetime.now(timezone.utc).isoformat(),
                      "payload": {"type": "message", "role": "user",
                                  "content": [{"type": "input_text", "text": fields["prompt"]}],
                                  "internal_chat_message_metadata_passthrough": {
                                      "turn_id": fields.get("turn_id", "one")}}}
        with native_session.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(native_row, ensure_ascii=False) + "\n")
    payload = {"cwd": str(root), "session_id": "leader", "turn_id": "one",
               "transcript_path": str(native_session), **fields}
    result = run_tool("lhc_entry", ["--root", str(REPO_ROOT), "--runtime", "codex",
                                    "--event", event, "--session"],
                      stdin=json.dumps(payload),
                      env={"HOME": str(root / "native-home"),
                           "CODEX_HOME": str(root / "native-home/.codex")})
    result.check_returncode()
    return json.loads(result.stdout) if result.stdout.strip() else {}


def outcome_cli(root, *args, ok=True):
    """Run the outcome CLI of one case and return its JSON or its error text."""

    result = run_tool("lhc_outcome", ["--cwd", str(root), "--runtime", "codex",
                                       "--session-id", "leader", *args],
                      env={"HOME": str(Path(root) / "native-home"),
                           "CODEX_HOME": str(Path(root) / "native-home/.codex")})
    assert (result.returncode == 0) == ok, result.stderr
    return json.loads(result.stdout) if result.returncode == 0 else result.stderr


def outcome_process(cwd, *args, home=None, codex_home=None, session_id="leader",
                    runtime="codex"):
    """Run the outcome CLI of one case and return its raw result."""

    env = {}
    if home is not None:
        env["HOME"] = str(home)
    if codex_home is not None:
        env["CODEX_HOME"] = str(codex_home)
    return run_tool("lhc_outcome", ["--cwd", str(cwd), "--runtime", runtime,
                                    "--session-id", session_id, *args], env=env)


def learning_state(root):
    """The shared learning state of one case."""

    path = next((Path(root) / ".agents/shared-session/learning").glob("*.json"))
    return json.loads(path.read_text())


def anchored_outcome(root, goal="Fix the small total CLI. Verify the empty basket returns 0.",
                     coverage=(), canary=None):
    """A confirmed quickfix contract in a fresh checkout."""

    root = Path(root)
    git_repo(root)
    (root / "total.py").write_text("print(0)\n")
    (root / "test_total.py").write_text(
        "import unittest, subprocess, sys\nclass TotalTest(unittest.TestCase):\n"
        " def test_empty(self): self.assertEqual(subprocess.check_output([sys.executable, 'total.py']).strip(), b'0')\n")
    native_invoke(root, "UserPromptSubmit", prompt=goal)
    scenario, target, expected = canary or ("Empty basket total", "python3 total.py", "0")
    args = ["contract", "--scenario", scenario, "--target", target, "--expected", expected]
    task_class = learning_state(root)["business"]["outcome"]["task_class"]
    if task_class in {"quickfix", "fullcycle"}:
        args += ["--owned-path", "total.py"]
    if task_class == "fullcycle":
        for stage, stage_target, stage_expected in [
                ("deploy", "https://demo.test/version", "v2"),
                ("publication", "https://github.com/owned/project/pull/1", "a" * 40),
                ("integration", "https://github.com/owned/project/pull/1", "b" * 40)]:
            args += ["--stage-target", stage + "=" + stage_target,
                     "--stage-expected", stage + "=" + stage_expected]
    for item in coverage:
        args += ["--coverage", item]
    return outcome_cli(root, *args)


# --------------------------------------------------------------------------
# Local fixture commands
# --------------------------------------------------------------------------

def _unittest_command(cwd: Path):
    """``python3 -m unittest discover -q`` without a new interpreter."""

    saved_path = list(sys.path)
    saved_modules = set(sys.modules)
    out = io.StringIO()
    err = io.StringIO()
    try:
        sys.path.insert(0, str(cwd))
        suite = unittest.TestLoader().discover(str(cwd))
        runner = unittest.TextTestRunner(stream=out, verbosity=0)
        with contextlib.redirect_stderr(err), missing_script_in_process():
            result = runner.run(suite)
    except Exception:  # noqa: BLE001 - the CLI would have died with a traceback
        err.write(traceback.format_exc())
        return 1, out.getvalue(), err.getvalue()
    finally:
        sys.path[:] = saved_path
        # The discovered test module belongs to this case alone. unittest keeps
        # it in sys.modules, and a later discovery in another directory refuses
        # to import the same module name from its own path.
        for name in set(sys.modules) - saved_modules:
            del sys.modules[name]
        # unittest keeps the directory of the last discovery on its shared loader.
        unittest.defaultTestLoader._top_level_dir = None
    return (0 if result.wasSuccessful() else 1), out.getvalue(), err.getvalue()


def _script_command(script: Path, cwd: Path):
    """``python3 <script>`` without a new interpreter."""

    out, err = io.StringIO(), io.StringIO()
    saved_path = list(sys.path)
    saved_modules = set(sys.modules)
    code = 0
    try:
        sys.path.insert(0, str(cwd))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            runpy.run_path(str(script), run_name="__main__")
    except SystemExit as exit_request:
        code = _exit_code(exit_request.code)
    except Exception:  # noqa: BLE001 - the CLI would have died with a traceback
        err.write(traceback.format_exc())
        code = 1
    finally:
        sys.path[:] = saved_path
        for name in set(sys.modules) - saved_modules:
            del sys.modules[name]
    return code, out.getvalue(), err.getvalue()


def local_command(command: str, cwd):
    """Run one local fixture command and return (returncode, stdout, stderr).

    The command of a fixture is ordinary shell text.  The Python ones are
    ordinary scripts, so they run here instead of in a new interpreter; the
    reading of a file is the reading of a file.  Every other command keeps its
    own process.

    The interpreter a fixture asks for from *inside* its own test keeps its
    process too: in this lane the fixture's script is not found next to the
    process, and the observation of such a case is the interpreter's own
    diagnostic.  Answering it here would change what the review reads.
    """

    cwd = Path(cwd)
    parts = shlex.split(command)
    if parts[:3] == ["python3", "-m", "unittest"]:
        return _unittest_command(cwd)
    if len(parts) == 2 and parts[0] == "python3":
        return _script_command(cwd / parts[1], cwd)
    if len(parts) == 2 and parts[0] == "cat":
        code, stdout, stderr = cat_file(cwd / parts[1], parts[1])
        return code, stdout.decode("utf-8", "replace"), stderr.decode("utf-8", "replace")
    completed = subprocess.run(parts, cwd=str(cwd), capture_output=True, text=True)
    return completed.returncode, completed.stdout, completed.stderr


# --------------------------------------------------------------------------
# The native review export
# --------------------------------------------------------------------------

def review_export_manifest(root, outcome, *, product="pass",
                           stage_names=("technical", "consumer"), sid="reviewer",
                           target=None, command=None, revision=None, coverage=None,
                           compared=True, coverage_compared=True, consumer_workdir=None,
                           raw_final=None, bad_deploy=False):
    """Write the native reviewer transcript of one case and return its manifest.

    The technical and consumer rows run their local command for real, so the
    evidence stays a real readback; only the interpreter start is saved.
    """

    root = Path(root)
    now = (datetime.now(timezone.utc) + timedelta(seconds=1)).isoformat()
    native_path = root / "native-home/.codex/sessions" / (sid + ".jsonl")
    native_path.parent.mkdir(parents=True, exist_ok=True)
    commands = {"technical": "python3 -m unittest discover -q", "consumer": "python3 total.py",
                "deploy": "curl https://demo.test/version",
                "publication": "gh pr view https://github.com/owned/project/pull/1 --json url,state,headRefOid",
                "integration": "gh pr view https://github.com/owned/project/pull/1 --json url,state,mergedAt,mergeCommit"}
    rows = [{"type": "session_meta", "payload": {"id": sid, "cwd": str(root), "timestamp": now}},
            {"type": "response_item", "payload": {"type": "message", "role": "user",
             "content": [{"text": "Independent review of outcome " + outcome["id"]
                          + ": compare actual operation/target/revision/results. Original scope: "
                          + outcome["original_goal"]}]}}]
    report = {"outcome_id": outcome["id"], "revision": revision or outcome["revision"],
              "target": target or outcome["canary"]["target"],
              "scenario": outcome["canary"]["scenario"],
              "expected": outcome["canary"]["expected"], "assignment_verdict": "complete",
              "product_verdict": product,
              "comparison": "Observed CLI output compared with empty basket requirement.",
              "coverage": coverage or {}, "stages": {}}
    for index, stage in enumerate(stage_names):
        cmd = command if stage == "consumer" and command else commands[stage]
        # Actually run local technical/consumer commands for this fixture; remote
        # stage rows below are deliberately fake and never release acceptance.
        if stage in {"technical", "consumer"}:
            workdir = consumer_workdir if stage == "consumer" and consumer_workdir else root
            _, stdout, stderr = local_command(cmd, workdir)
            output = stdout + stderr
        else:
            # Explicit native-format fixtures, NOT live release receipts. Unlike
            # a generic nonempty string, the readback binds target and version.
            output = json.dumps({"version": "v2"} if stage == "deploy" else
                                {"url": "https://github.com/owned/project/pull/1", "state": "OPEN",
                                 "headRefOid": "a" * 40, "baseRefName": "main"} if stage == "publication" else
                                {"url": "https://github.com/owned/project/pull/1", "state": "MERGED",
                                 "mergedAt": now, "mergeCommit": {"oid": "b" * 40}, "baseRefName": "main"})
            if stage == "deploy" and bad_deploy:
                cmd = "git rev-parse HEAD"
                proc = subprocess.run(cmd.split(), cwd=root, capture_output=True, text=True)
                output = proc.stdout + proc.stderr
        call = "call-" + str(index)
        rows += [{"type": "response_item", "payload": {"type": "function_call", "name": "exec_command",
                   "call_id": call, "arguments": json.dumps(
                       {"cmd": cmd, **({"workdir": str(consumer_workdir)}
                                       if stage == "consumer" and consumer_workdir else {})})}},
                 {"type": "response_item", "payload": {"type": "function_call_output",
                   "call_id": call, "output": output}}]
        report["stages"][stage] = {"evidence_calls": [call], "observed": output.strip()}
        if compared:
            report["stages"][stage]["expected"] = (outcome["canary"]["expected"]
                                                   if stage == "consumer"
                                                   else "Successful " + stage + " readback for this scope")
            if stage in outcome.get("stage_claims", {}):
                report["stages"][stage].update(outcome["stage_claims"][stage])
    if coverage_compared and coverage:
        consumer = report["stages"]["consumer"]
        report["coverage"] = {item: {"verdict": verdict, "expected": outcome["canary"]["expected"],
                                     "observed": consumer["observed"],
                                     "evidence_calls": consumer["evidence_calls"]}
                              for item, verdict in coverage.items()}
    rows.append({"type": "response_item", "payload": {"type": "message", "role": "assistant",
                 "phase": "final",
                 "content": [{"text": raw_final if raw_final is not None else
                              "Compared the actual observed CLI behavior.\nLHC_OUTCOME_REVIEW "
                              + json.dumps(report)}]}})
    for row in rows:
        row["timestamp"] = now
    native_path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    export = root / (sid + "-export.jsonl")
    export.write_bytes(native_path.read_bytes())
    manifest = root / (sid + ".manifest.json")
    manifest.write_text(json.dumps({"format": "agent-herder-transcript-manifest-v1", "target": {
        "path": str(export), "harness": "codex", "complete": True, "sessionId": sid,
        "source": {"kind": "native-file", "location": str(native_path)}}}))
    return manifest
