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
    if not isinstance(words[0], str) or words[0] != sys.executable:
        return False
    script = words[1]
    return isinstance(script, str) and not script.startswith("-")


def _missing_script(script: str) -> tuple[int, bytes, bytes]:
    """What an interpreter prints when it cannot open the script."""

    path = os.path.abspath(script)
    diagnostic = (f"{sys.executable}: can't open file '{path}': "
                  f"[Errno 2] No such file or directory\n")
    return 2, b"", diagnostic.encode(_encoding(), "replace")


def _run_script(script: str, arguments, stdin_data, want_stdout: bool,
                want_stderr: bool, stdout_file, stderr_file):
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
    code = 0
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
        sys.argv = [script, *arguments]
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
            code = 1
        elif not isinstance(code, int):
            code = 1
    except Exception:  # noqa: BLE001 - the interpreter would have died with a traceback
        if err_stream is not None:
            traceback.print_exc(file=err_stream)
        code = 1
    finally:
        sys.argv = saved_argv
        sys.path[:] = saved_path
        sys.stdin = saved_stdin
        if out_stream is not None and want_stdout:
            out_stream.flush()
        if err_stream is not None and want_stderr:
            err_stream.flush()
    return code, out_buffer.getvalue() if out_buffer else b"", \
        err_buffer.getvalue() if err_buffer else b""


def _answer(words, stdin_data=None, want_stdout=True, want_stderr=True,
            stdout_file=None, stderr_file=None):
    """The answer of the command, or ``None`` when it is not our own."""

    if not _own_interpreter(words):
        return None
    script = words[1]
    if not os.path.isfile(script):
        code, stdout, stderr = _missing_script(script)
        if not want_stderr and stderr_file is None:
            sys.stderr.write(stderr.decode(_encoding(), "replace"))
            stderr = b""
        elif not want_stderr:
            stderr_file.write(stderr.decode(_encoding(), "replace"))
            stderr = b""
        return code, stdout, stderr
    return _run_script(script, [str(item) for item in words[2:]], stdin_data,
                       want_stdout, want_stderr, stdout_file, stderr_file)


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
                         None if stderr in (subprocess.PIPE, None) else stderr)
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
        # check_output captures stdout and leaves stderr alone, exactly as the
        # real one does.
        result = _answer(args, kwargs.get("input"), stdout == subprocess.PIPE,
                         stderr == subprocess.PIPE,
                         None if stdout in (subprocess.PIPE, None) else stdout,
                         None if stderr in (subprocess.PIPE, None) else stderr)
        if result is None:
            return real_check_output(args, *pargs, **kwargs)
        code, out, err = result
        if kwargs.get("text") or kwargs.get("universal_newlines"):
            out = out.decode(_encoding(), "replace")
            err = err.decode(_encoding(), "replace")
        if code != 0:
            raise subprocess.CalledProcessError(code, args, output=out, stderr=err)
        return out

    subprocess.run = run
    subprocess.check_output = check_output
    try:
        yield
    finally:
        subprocess.run = real_run
        subprocess.check_output = real_check_output


def cat_file(path) -> tuple[int, bytes, bytes]:
    """What ``cat`` answers for one file: its content, or its own complaint."""

    target = Path(path)
    try:
        if target.is_dir():
            return 1, b"", (f"cat: {path}: Is a directory\n").encode(_encoding(), "replace")
        content = target.read_bytes()
    except FileNotFoundError:
        return 1, b"", (f"cat: {path}: No such file or directory\n").encode(_encoding(), "replace")
    except PermissionError:
        return 1, b"", (f"cat: {path}: Permission denied\n").encode(_encoding(), "replace")
    except OSError as error:
        return 1, b"", (f"cat: {path}: {error.strerror}\n").encode(_encoding(), "replace")
    return 0, content, b""
