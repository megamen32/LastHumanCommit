"""Answer the commands a case fixture runs, without a second interpreter.

The files a case writes into its checkout are ordinary project files.  When
such a file runs its CLI it uses the interpreter of the process that started
it.  The harness starts the fixture in *this* process, so the interpreter the
fixture asks for is this one, and the call can be answered here: the same
interpreter, the same working directory, the same environment, the same
stdout, stderr and exit code - without a second interpreter start, which on
this machine costs about 220 ms.

Only the commands that ask for *this* interpreter are answered here.  Every
other command - a foreign interpreter, a git, a shell - keeps its own process,
so a fixture that drives a foreign interpreter still drives a foreign
interpreter.

A script that is not there is answered by the interpreter's own complaint,
with the interpreter's own exit code and the interpreter's own name.  The
answer is given through the pipes of a process, so the code that reads them
reads the same bytes and the traceback of a failure keeps the frames of
``subprocess`` itself.

Reading a file is the other thing a fixture does that needs no process: the
stdout of ``cat`` is the content of the file, and the content of a file is
read from the file.

The helpers here are private to the test suite.  No test file may depend on
them.
"""

from __future__ import annotations

import contextlib
import io
import locale
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import traceback


def _encoding() -> str:
    """The encoding a fresh interpreter would use for its output."""

    return locale.getpreferredencoding(False) or "utf-8"


def _own_interpreter(words) -> bool:
    """True when the command asks for the interpreter of this very process."""

    if not isinstance(words, (list, tuple)) or len(words) < 2:
        return False
    if not isinstance(words[0], str):
        return False
    if words[0] != sys.executable and _resolved_program(words[0]) != sys.executable:
        return False
    script = words[1]
    return isinstance(script, str) and not script.startswith("-")


_PROGRAM_CACHE: dict[str, str | None] = {}


def _resolved_program(program: str) -> str | None:
    """The program the PATH names, remembered once per name."""

    if program not in _PROGRAM_CACHE:
        _PROGRAM_CACHE[program] = shutil.which(program)
    return _PROGRAM_CACHE[program]


def _run_script(script: str, argv0: str, arguments, stdin_data, want_stdout: bool,
                want_stderr: bool, stdout_file, stderr_file, cwd=None):
    """Run ``script`` with this interpreter and return (code, stdout, stderr).

    ``want_stdout`` and ``want_stderr`` say whether the streams are captured
    here; a stream that is not captured goes to the file the caller named, or
    to the stream of this process when no file was named - exactly as a child
    process would treat it.
    """

    encoding = _encoding()
    out_buffer = io.BytesIO() if want_stdout else None
    err_buffer = io.BytesIO() if want_stderr else None
    out_stream = (io.TextIOWrapper(out_buffer, encoding=encoding, newline="")
                  if want_stdout else stdout_file)
    err_stream = (io.TextIOWrapper(err_buffer, encoding=encoding, newline="")
                  if want_stderr else stderr_file)
    saved_argv = list(sys.argv)
    saved_path = list(sys.path)
    saved_stdin = sys.stdin
    saved_cwd = os.getcwd()
    code = 0
    try:
        if cwd is not None:
            os.chdir(cwd)
        sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
        sys.argv = [argv0, *arguments]
        if stdin_data is not None:
            sys.stdin = io.StringIO(stdin_data if isinstance(stdin_data, str)
                                    else stdin_data.decode())
        with contextlib.ExitStack() as stack:
            if out_stream is not None:
                stack.enter_context(contextlib.redirect_stdout(out_stream))
            if err_stream is not None:
                stack.enter_context(contextlib.redirect_stderr(err_stream))
            runpy.run_path(script, run_name="__main__")
    except SystemExit as exit_request:
        code = exit_request.code
        if code is None:
            code = 0
        elif isinstance(code, str):
            if err_stream is not None:
                err_stream.write(code + "\n")
            else:
                sys.stderr.write(code + "\n")
            code = 1
        elif not isinstance(code, int):
            code = 1
    except Exception:  # noqa: BLE001 - the interpreter would have died with a traceback
        if err_stream is not None:
            traceback.print_exc(file=err_stream)
        else:
            traceback.print_exc()
        code = 1
    finally:
        os.chdir(saved_cwd)
        sys.argv = saved_argv
        sys.path[:] = saved_path
        sys.stdin = saved_stdin
        for stream, wanted in ((out_stream, want_stdout), (err_stream, want_stderr)):
            if stream is None or not wanted:
                continue
            try:
                stream.flush()
                stream.detach()
            except ValueError:
                pass
    return code, out_buffer.getvalue() if out_buffer else b"", \
        err_buffer.getvalue() if err_buffer else b""


def _answer(words, stdin_data=None, want_stdout=True, want_stderr=True,
            stdout_file=None, stderr_file=None, cwd=None):
    """The answer of the command, or ``None`` when it is not our own.

    A script that is not there is left to :func:`missing_script_in_process`,
    which answers it the way the interpreter answers it.
    """

    if not _own_interpreter(words):
        return None
    script = words[1]
    target = script if os.path.isabs(script) else os.path.join(
        cwd if cwd is not None else os.getcwd(), script)
    if not os.path.isfile(target):
        return None
    return _run_script(target, script, [str(item) for item in words[2:]], stdin_data,
                       want_stdout, want_stderr, stdout_file, stderr_file, cwd)


# --------------------------------------------------------------------------
# The interpreter that cannot open its script
# --------------------------------------------------------------------------

def program_name() -> str:
    """The name the interpreter gives itself in its own complaint.

    A framework build of Python runs the real interpreter under its own
    name, and that is the name the complaint carries.
    """

    candidate = Path(sys.prefix) / "Resources/Python.app/Contents/MacOS/Python"
    if candidate.is_file():
        return str(candidate)
    return sys.executable


def missing_script_complaint(script: str, cwd=None) -> bytes:
    """The complaint an interpreter makes when it cannot open its script."""

    path = os.path.abspath(script) if os.path.isabs(script) else os.path.join(
        cwd if cwd is not None else os.getcwd(), script)
    complaint = (f"{program_name()}: can't open file '{path}': "
                 f"[Errno 2] No such file or directory\n")
    return complaint.encode(_encoding(), "replace")


class _ComplaintProcess:
    """The process of an interpreter that cannot open the script it was given.

    The interpreter is not started for it: the complaint it makes is the one
    it always makes, and the exit code is the one it always gives.  The pipes
    answer the way the real ones answer, so the code that reads them reads
    the same bytes - and the traceback of the failure keeps the frames of
    ``subprocess`` itself, because the complaint is raised inside it.
    """

    def __init__(self, args, stdout=None, stderr=None, text=False,
                 universal_newlines=False, encoding=None, errors=None,
                 cwd=None, **kwargs):
        self.args = args
        self.pid = os.getpid()
        self.returncode = 2
        self.stdin = None
        self.text_mode = bool(text or universal_newlines or encoding or errors)
        self._text_encoding = encoding or _encoding()
        self._errors = errors or "strict"
        self._out = io.BytesIO()
        self._err = io.BytesIO()
        complaint = missing_script_complaint(args[1], cwd)
        if stderr == subprocess.PIPE:
            self._err.write(complaint)
            self._err.seek(0)
            self.stderr = (io.TextIOWrapper(self._err, encoding=self._text_encoding,
                                            errors=self._errors)
                           if self.text_mode else self._err)
        elif stderr is not None:
            stderr.write(complaint)
            self.stderr = None
        else:
            # stderr is inherited: the child writes to the terminal of the
            # machine, not to a pipe of this process.
            try:
                os.write(2, complaint)
            except OSError:
                pass
            self.stderr = None
        if stdout == subprocess.PIPE:
            self.stdout = (io.TextIOWrapper(self._out, encoding=self._text_encoding,
                                            errors=self._errors)
                           if self.text_mode else self._out)
        else:
            self.stdout = None

    def communicate(self, input=None, timeout=None):
        out = self.stdout.read() if self.stdout is not None else None
        err = self.stderr.read() if self.stderr is not None else None
        return out, err

    def poll(self):
        return self.returncode

    def wait(self, timeout=None):
        return self.returncode

    def kill(self):
        return None

    def terminate(self):
        return None

    def __enter__(self):
        return self

    def __exit__(self, *exception):
        return False


def _complaint_for(args, kwargs):
    """The process of the complaint, or ``None`` when it is not our own."""

    if not isinstance(args, (list, tuple)) or len(args) < 2:
        return None
    if not isinstance(args[0], str) or not _own_interpreter(args):
        return None
    script = args[1]
    if not isinstance(script, str) or script.startswith("-"):
        return None
    cwd = kwargs.get("cwd")
    target = script if os.path.isabs(script) else os.path.join(
        cwd if cwd is not None else os.getcwd(), script)
    if os.path.exists(target):
        return None
    return _ComplaintProcess(args, cwd=cwd, **kwargs)


@contextlib.contextmanager
def missing_script_in_process():
    """Let the interpreter answer for a script that is not there.

    The patch is on the process itself, so the frames of ``subprocess`` stay
    in the traceback of a failure and the complaint is the one the machine
    gives.  Every other command keeps its own process.
    """

    real_popen = subprocess.Popen

    def popen(args, *pargs, **kwargs):
        complaint = _complaint_for(args, kwargs)
        if complaint is None:
            return real_popen(args, *pargs, **kwargs)
        return complaint

    subprocess.Popen = popen
    try:
        yield
    finally:
        subprocess.Popen = real_popen


@contextlib.contextmanager
def own_interpreter_in_process():
    """Let a fixture's own interpreter call run in this process.

    The patch is narrow: it answers a command only when the command asks for
    the interpreter of this very process.  Every other command keeps its own
    process, and the patch is gone again as soon as the block ends.
    """

    real_run = subprocess.run
    real_check_output = subprocess.check_output

    def run(args, *pargs, **kwargs):
        capture = bool(kwargs.get("capture_output"))
        stdout = kwargs.get("stdout")
        stderr = kwargs.get("stderr")
        want_stdout = capture or stdout == subprocess.PIPE
        want_stderr = capture or stderr == subprocess.PIPE
        stdin_data = kwargs.get("input")
        result = _answer(args, stdin_data, want_stdout, want_stderr,
                         None if stdout in (subprocess.PIPE, None) else stdout,
                         None if stderr in (subprocess.PIPE, None) else stderr,
                         kwargs.get("cwd"))
        if result is None:
            return real_run(args, *pargs, **kwargs)
        code, out, err = result
        if kwargs.get("text") or kwargs.get("universal_newlines"):
            out = out.decode(_encoding(), "replace")
            err = err.decode(_encoding(), "replace")
        completed = subprocess.CompletedProcess(args, code, out, err)
        if kwargs.get("check") and code != 0:
            raise subprocess.CalledProcessError(code, args, out, err)
        return completed

    def check_output(args, *pargs, **kwargs):
        stdout = kwargs.get("stdout")
        stderr = kwargs.get("stderr")
        # check_output always captures stdout and leaves stderr alone, exactly
        # as the real one does.
        captured_stderr = stderr == subprocess.PIPE
        result = _answer(args, kwargs.get("input"), True,
                         captured_stderr,
                         None if stdout in (subprocess.PIPE, None) else stdout,
                         None if stderr in (subprocess.PIPE, None) else stderr,
                         kwargs.get("cwd"))
        if result is None:
            return real_check_output(args, *pargs, **kwargs)
        code, out, err = result
        if kwargs.get("text") or kwargs.get("universal_newlines"):
            out = out.decode(_encoding(), "replace")
            err = err.decode(_encoding(), "replace")
        if code != 0:
            # The real check_output leaves stderr alone, so the error it
            # reports carries no stderr of its own.
            raise subprocess.CalledProcessError(code, args, output=out,
                                                stderr=err if captured_stderr else None)
        return out

    subprocess.run = run
    subprocess.check_output = check_output
    try:
        yield
    finally:
        subprocess.run = real_run
        subprocess.check_output = real_check_output


def cat_file(path, name=None) -> tuple[int, bytes, bytes]:
    """What ``cat`` answers for one file: its content, or its own complaint.

    ``name`` is the name the command used; ``cat`` names the file the way it
    was asked for, not the way the path resolved.
    """

    target = Path(path)
    label = name if name is not None else str(path)
    try:
        if target.is_dir():
            return 1, b"", (f"cat: {label}: Is a directory\n").encode(_encoding(), "replace")
        content = target.read_bytes()
    except FileNotFoundError:
        return 1, b"", (f"cat: {label}: No such file or directory\n").encode(_encoding(), "replace")
    except PermissionError:
        return 1, b"", (f"cat: {label}: Permission denied\n").encode(_encoding(), "replace")
    except OSError as error:
        return 1, b"", (f"cat: {label}: {error.strerror}\n").encode(_encoding(), "replace")
    return 0, content, b""
