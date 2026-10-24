"""Run the LHC command line tools inside the test process.

The tools under test are CLIs. Every case that used to spawn
``python3 <tool>.py ...`` paid one interpreter start (about 0.2-0.4 s on this
machine) plus, for some cases, a fresh ``git init``. The fast lane spawns
hundreds of those, which is why the whole suite used to take minutes.

This module runs the very same entry functions in-process and keeps the
observable contract intact:

* the argument vector the CLI would have received,
* stdin the CLI would have read,
* the environment and the working directory the CLI would have seen,
* stdout, stderr and the exit code the CLI would have produced.

Nothing in the production tree is changed: only *where* the code runs.
Reloading a module per case is deliberately avoided - a reload costs as much
as the subprocess it replaced - so the tools keep their module-level state
between cases. The tools under ``src/common/tools`` hold no mutable module
state (the only module globals are pure lazy caches of stateless sibling
modules), so the state that actually leaks is the *process* state: argv,
stdin, the environment and the working directory. ``reset_state()`` restores
exactly that.

**The git binary.**  The tools start git thousands of times per run, and on
this machine ``/usr/bin/git`` is an ``xcrun`` stub that spends about 21 ms on
every start, while the git it forwards to needs about 7 ms.  The lane uses
the forwarded binary, but only after proving that it is the same git: the
same version and byte identical answers for every git command the tools use
(see ``tests/_fast_git.py``).  When no such binary can be proven, the git of
the PATH stays in use.

The helpers here are private to the fast lane. No other test file may depend
on them.
"""

from __future__ import annotations

import atexit
import contextlib
import importlib.util
import inspect
import io
import os
import re
import shutil
import subprocess
import sys
import traceback
from pathlib import Path

from _fast_git import git_path, use_fast_git


REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_DIR = REPO_ROOT / "src" / "common" / "tools"

# The sibling tools import each other by bare module name ("import
# lhc_time_guard"). The tools themselves add their directory to sys.path on
# import, but the tools that are only imported as data (for example the graph
# validator) need it up front.
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


# Every git the tools start in this lane must use the git that was proven to
# be the same git; see the module docstring.
use_fast_git()


class CliResult:
    """The part of ``subprocess.CompletedProcess`` that the assertions read."""

    __slots__ = ("args", "returncode", "stdout", "stderr")

    def __init__(self, args, returncode: int, stdout: str, stderr: str) -> None:
        self.args = list(args)
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __repr__(self) -> str:
        return (f"CliResult(returncode={self.returncode!r}, "
                f"stdout={self.stdout!r}, stderr={self.stderr!r})")


# --------------------------------------------------------------------------
# Module loading
# --------------------------------------------------------------------------

_MODULES: dict[tuple[str, str], object] = {}


def load_module(path, *, name: str | None = None):
    """Import one script once per process and reuse the module object.

    The module is registered under its canonical bare name so that the
    sibling tools that import each other by bare name resolve to the very
    same module instance the test drives. Registering it before executing it
    is required: the dataclasses of the graph tool look their own module up
    in ``sys.modules`` while the class body runs.
    """
    path = Path(path)
    key = (str(path), name or path.stem)
    module = _MODULES.get(key)
    if module is not None:
        return module
    existing = sys.modules.get(key[1])
    if existing is not None and getattr(existing, "__file__", None) == str(path):
        # Another module already imported this very file under this name.
        _MODULES[key] = existing
        return existing
    spec = importlib.util.spec_from_file_location(key[1], path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[key[1]] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        sys.modules.pop(key[1], None)
        raise
    _MODULES[key] = module
    return module


# --------------------------------------------------------------------------
# Process state
# --------------------------------------------------------------------------

# The state a fresh interpreter would have had. The tools under
# ``src/common/tools`` keep no mutable module-level state - their only module
# globals are pure lazy caches of stateless sibling modules - so the state a
# new process would have prevented is the *process* state: the argument
# vector, stdin, the environment and the working directory.
_BASELINE_ARGV = list(sys.argv)
_BASELINE_ENV = {name: os.environ.get(name) for name in (
    "HOME", "CODEX_HOME", "CLAUDE_PROJECT_DIR", "ZCODE_PLUGIN_ROOT",
    "CLAUDE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "PLUGIN_ROOT")}


def reset_state() -> None:
    """Restore the process state a fresh interpreter would have had.

    Every CLI call runs through :func:`run_cli`, which restores the argument
    vector and the environment itself. This also undoes what the tool itself
    changed while it ran, so case N starts where case 1 started.
    """

    sys.argv = list(_BASELINE_ARGV)
    for name, value in _BASELINE_ENV.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


@contextlib.contextmanager
def _environment(overrides):
    saved = dict(os.environ)
    try:
        if overrides:
            os.environ.update({str(key): str(value) for key, value in overrides.items()})
        yield
    finally:
        os.environ.clear()
        os.environ.update(saved)


@contextlib.contextmanager
def _working_directory(path):
    if path is None:
        yield
        return
    saved = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(saved)


def _accepts_argv(main) -> bool:
    try:
        parameters = inspect.signature(main).parameters
    except (TypeError, ValueError):
        return False
    return any(parameter.kind in (parameter.POSITIONAL_ONLY,
                                   parameter.POSITIONAL_OR_KEYWORD,
                                   parameter.VAR_POSITIONAL)
               for parameter in parameters.values())


def _exit_code(code) -> int:
    """Map a ``main()`` result onto the exit code the interpreter would use."""

    if code is None:
        return 0
    if isinstance(code, bool):
        return int(code)
    if isinstance(code, int):
        return code
    return 1


def _with_fast_git(env):
    """The environment of one call, with the proven git binary on the PATH.

    A call that names its own PATH still gets the proven git in front of it;
    a call that names none inherits the PATH of this process, which already
    holds it.
    """

    if not env or "PATH" not in env:
        return env
    return {**env, "PATH": git_path(env["PATH"])}


def run_cli(module, argv, *, env=None, cwd=None, stdin=None, program=None, text=True):
    """Run ``module.main()`` in-process and return its observable result.

    ``argv`` is the argument vector *after* the program name, exactly as it
    would have been passed on the command line. A tool whose ``main()``
    accepts an argument vector receives it directly; a tool that parses
    ``sys.argv`` gets a patched ``sys.argv``. Either way the process state is
    restored afterwards, and the exit code, stdout and stderr are the ones the
    CLI would have produced.

    ``text=False`` returns the captured output as bytes, the way a
    ``subprocess.run`` without ``text=True`` would.
    """

    argv = [str(item) for item in argv]
    program = program or getattr(module, "__file__", "lhc-tool")
    out, err = io.StringIO(), io.StringIO()
    saved_argv = list(sys.argv)
    saved_stdin = sys.stdin
    try:
        with _environment(_with_fast_git(env)), _working_directory(cwd):
            if stdin is not None:
                sys.stdin = io.StringIO(stdin if isinstance(stdin, str) else stdin.decode())
            else:
                sys.stdin = io.StringIO("")
            if _accepts_argv(module.main):
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = module.main(argv)
            else:
                sys.argv = [program, *argv]
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    code = module.main()
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
        reset_state()
    stdout, stderr = out.getvalue(), err.getvalue()
    if not text:
        stdout = stdout.encode("utf-8", "replace")
        stderr = stderr.encode("utf-8", "replace")
    return CliResult([program, *argv], _exit_code(code), stdout, stderr)


def isolate_case_modules(root) -> None:
    """Drop modules that a sibling case imported, so this case imports its own.

    A fresh interpreter never had another case's module in ``sys.modules``.
    unittest discovery imports a test module by name, so a leftover copy from
    a sibling case would be found first and the case would read the wrong
    file. The cases are siblings under the pytest temporary root, so a module
    that lives in a sibling case directory is removed.
    """

    root = Path(root).resolve()
    prefix = str(root.parent) + os.sep
    for name, module in list(sys.modules.items()):
        path = getattr(module, "__file__", None)
        if not path:
            continue
        if not str(path).startswith(prefix):
            continue
        try:
            resolved = Path(path).resolve()
        except OSError:
            continue
        if resolved.parent == root or resolved.parent.parent != root.parent:
            continue
        sys.modules.pop(name, None)


# --------------------------------------------------------------------------
# Git repositories
# --------------------------------------------------------------------------

_GIT_TEMPLATE: Path | None = None


def git_template() -> Path:
    """The one ready-made Git repository every case copies from.

    The template is created with an empty Git template directory, so the
    repository holds nothing but ``HEAD`` and ``config``. Git creates the rest
    on demand, and every Git command the tools under test run answers exactly
    as it does for a freshly initialised repository.
    """

    global _GIT_TEMPLATE
    if _GIT_TEMPLATE is None:
        # The name carries the process id: two pytest runs may share the
        # project-local temporary root and must not share the template.
        root = REPO_ROOT / ".tmp" / f"lhc-fastlane-git-template-{os.getpid()}"
        shutil.rmtree(root, ignore_errors=True)
        root.mkdir(parents=True, exist_ok=True)
        empty = root / ".empty-template"
        empty.mkdir(exist_ok=True)
        subprocess.run(["git", "init", "-q", "--template", str(empty), str(root)],
                       check=True, capture_output=True)
        shutil.rmtree(empty, ignore_errors=True)
        atexit.register(shutil.rmtree, root, True)
        _GIT_TEMPLATE = root
    return _GIT_TEMPLATE


def git_repo(path) -> Path:
    """Make ``path`` a Git repository by copying the template.

    ``git init`` costs about 23 ms and the copy about 2.5 ms, and the copy is
    observationally identical: same ``.git`` layout, same unborn branch, same
    ``rev-parse --git-common-dir`` and ``worktree list`` answers, because the
    main worktree of a repository is derived from the location of its
    ``.git`` directory.
    """

    target = Path(path)
    target.mkdir(parents=True, exist_ok=True)
    shutil.copytree(git_template() / ".git", target / ".git", dirs_exist_ok=True)
    return target


# --------------------------------------------------------------------------
# The plugin hook shell command
# --------------------------------------------------------------------------

_HOOK_COMMAND = re.compile(
    r"python3\s+\"(?P<script>[^\"]+)\"(?P<args>[^\"]*?)\s*\|\|\s*\{(?P<fallback>[^}]*)\}",
)


def _resolve_shell_vars(text: str, env) -> str:
    """Resolve ``${VAR:-default}`` chains the way a POSIX shell does.

    The hook command picks the first plugin root that the environment names
    and falls back to the last default. ``os.path.expandvars`` does not know
    the ``:-`` form, so the chain is resolved here.
    """

    while True:
        start = text.find("${")
        if start == -1:
            return os.path.expandvars(text)
        depth = 0
        end = -1
        for index in range(start, len(text)):
            if text[index] == "{":
                depth += 1
            elif text[index] == "}":
                depth -= 1
                if depth == 0:
                    end = index
                    break
        if end == -1:
            return os.path.expandvars(text)
        name, separator, default = text[start + 2:end].partition(":-")
        if separator and env.get(name):
            value = env[name]
        elif separator:
            value = _resolve_shell_vars(default, env)
        else:
            value = env.get(name, "")
        text = text[:start] + value + text[end + 1:]


def run_hook_command(command: str, *, env=None, cwd=None, stdin="") -> CliResult:
    """Run a plugin hook command in-process, keeping its shell contract.

    The hook command is shell text: it runs the entry script and falls back to
    an advisory message when the script cannot run, so the harness is never
    blocked. This helper resolves the same script and arguments the shell
    would have used and calls the same entry function in-process; the
    ``||`` fallback is reproduced exactly, including its exit code of zero.
    """

    match = _HOOK_COMMAND.search(command)
    if match is None:
        raise ValueError(f"unrecognised hook command: {command!r}")

    environment = dict(os.environ)
    environment.update({str(key): str(value) for key, value in (env or {}).items()})
    script = Path(_resolve_shell_vars(match.group("script"), environment))
    arguments = match.group("args").split()

    advisory = re.findall(r"'([^']*)'", match.group("fallback"))
    # The fallback is a printf: its format string comes first, the message
    # last.
    fallback = (advisory[-1] if advisory else "") + "\n"

    if not script.is_file():
        # The interpreter cannot open the script: it reports the failure on
        # stderr and the shell takes the fallback branch, still exiting zero.
        diagnostic = (f"{sys.executable}: can't open file '{script}': "
                      f"[Errno 2] No such file or directory\n")
        return CliResult([str(script), *arguments], 0, "", diagnostic + fallback)

    module = load_module(script)
    result = run_cli(module, arguments, env=env, cwd=cwd, stdin=stdin)
    if result.returncode != 0:
        return CliResult(result.args, 0, result.stdout, result.stderr + fallback)
    return result
