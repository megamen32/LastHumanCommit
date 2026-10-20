"""Bounded preflight for explicit native task-directory restrictions.

This is not an OS sandbox or a general shell/permission parser. Only built-in
file writes and literal shell redirections are recognized. Ambiguous source
instructions do not invent a boundary or authorize an operation.
"""
from pathlib import Path
import re
import shlex


DIRECTORY_ONLY = re.compile(
    r'(?:^|[.!?\n])\s*(?:work only (?:in this directory|here)|'
    r'работай только (?:в этом каталоге|здесь))\s*(?:[.!?\n]|$)', re.I)


def directory_bound(sources):
    # Sources are the native original goal and accepted human corrections,
    # never tool output. Other named absolute locations/exceptions require
    # semantic scope resolution; this narrow guard does not override them.
    raw = '\n'.join(sources)
    if re.search(r'(?<![\w:])/(?:[^\s`\"\']+)|\b(?:except|unless|allow|кроме|разреш|можно)\b', raw, re.I):
        return False
    prose = re.sub(r'```[\s\S]*?```|`[^`]*`|"[^"\n]*"|«[^»]*»', '', raw)
    return bool(DIRECTORY_ONLY.search(prose))


def outside(path, directory):
    if path == '/dev/null':
        return False  # Discarding a stream creates no external task artifact.
    if any(mark in path for mark in ('$', '`', '~')):
        return True  # Do not guess an expanded output location.
    return not (directory / path).resolve().is_relative_to(directory)


def write_denial(sources, cwd, tool, arguments):
    if not isinstance(arguments, dict) or not directory_bound(sources):
        return None
    directory = Path(cwd).resolve()
    paths = []
    if tool in {'write', 'edit', 'multiedit'}:
        entries = arguments.get('edits', []) if tool == 'multiedit' else [arguments]
        paths = [row.get('path') or row.get('filePath') for row in entries if isinstance(row, dict)]
    elif tool == 'shell':
        command = arguments.get('command')
        if not isinstance(command, str):
            return None
        try:
            words = shlex.split(command)
            if len(words) == 3 and Path(words[0]).name in {'sh', 'bash'} and words[1] in {'-c', '-lc'}:
                command = words[2]
            lexer = shlex.shlex(command, posix=True, punctuation_chars=';&|<>')
            lexer.whitespace_split = True
            words = list(lexer)
        except ValueError:
            return None  # Native shell validation still applies.
        paths = [words[i + 1] for i, word in enumerate(words[:-1])
                 if word in {'>', '>>', '>|', '&>'} and words[i + 1] != '/dev/null']
        # Relative redirects after an unknown cwd change cannot be resolved
        # safely by interpreting only a literal redirection.
        if paths and any(word == 'cd' and i + 1 < len(words) and outside(words[i + 1], directory)
                         for i, word in enumerate(words)):
            return 'The native user restricted this task to its assigned directory; this write changes cwd outside it. Use an in-directory output.'
    if any(isinstance(path, str) and outside(path, directory) for path in paths):
        return ('The native user restricted this task to its assigned directory, including temporary outputs. '
                'This write is outside it or has an unresolved output path. Use an explicit relative path under .tmp/ '
                'when writing is allowed. No permission request or external write was performed.')
    return None
