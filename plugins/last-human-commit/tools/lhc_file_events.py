"""Small directory-only inotify source; unavailable coverage is explicit.

Callers own discovery and reconciliation. This module never traverses a tree.
"""
from __future__ import annotations

import ctypes
from dataclasses import dataclass, field
import os
from pathlib import Path
import select
import struct
import sys


@dataclass
class FileChanges:
    paths: set[Path] = field(default_factory=set)
    overflow: bool = False


_HEADER = struct.Struct("iIII")
_IN_Q_OVERFLOW = 0x00004000
_IN_IGNORED = 0x00008000
_MASK = (0x00000002 | 0x00000004 | 0x00000008 | 0x00000040 |
         0x00000080 | 0x00000100 | 0x00000200 | 0x00000400 |
         0x00000800 | _IN_IGNORED | 0x01000000)  # IN_ONLYDIR


class FileEvents:
    """Watch explicitly added directories, reporting any lost coverage.

    Initialization/add/read errors disable the source rather than silently
    dropping changes. ``poll`` then returns ``overflow=True`` until replaced.
    No system watch limits are modified.
    """

    def __init__(self):
        self.available = False
        self._fd = -1
        self._dirs: dict[int, Path] = {}
        self._paths: dict[Path, int] = {}
        self._libc = None
        if not sys.platform.startswith("linux"):
            return
        try:
            libc = ctypes.CDLL(None, use_errno=True)
            libc.inotify_init1.argtypes = [ctypes.c_int]
            libc.inotify_init1.restype = ctypes.c_int
            libc.inotify_add_watch.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_uint32]
            libc.inotify_add_watch.restype = ctypes.c_int
            fd = libc.inotify_init1(os.O_NONBLOCK | os.O_CLOEXEC)
            if fd < 0:
                return
            self._libc = libc
            self._fd = fd
            self.available = True
        except (AttributeError, OSError):
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def add(self, directory: Path) -> bool:
        if not self.available:
            return False
        try:
            path = Path(directory).resolve()
            if path in self._paths:
                return True
            wd = self._libc.inotify_add_watch(self._fd, os.fsencode(path), _MASK)
            if wd < 0:
                self.close()
                return False
            self._dirs[wd] = path
            self._paths[path] = wd
            return True
        except (OSError, ValueError):
            self.close()
            return False

    def poll(self, timeout: float = 0) -> FileChanges:
        changes = FileChanges()
        if not self.available:
            changes.overflow = True
            return changes
        try:
            if not select.select([self._fd], [], [], max(0, timeout))[0]:
                return changes
            while True:
                try:
                    data = os.read(self._fd, 65536)
                except BlockingIOError:
                    break
                except InterruptedError:
                    continue
                if not data:
                    raise OSError("inotify source closed")
                offset = 0
                while offset + _HEADER.size <= len(data):
                    wd, mask, _cookie, length = _HEADER.unpack_from(data, offset)
                    offset += _HEADER.size
                    if offset + length > len(data):
                        changes.overflow = True
                        break
                    name = data[offset:offset + length].split(b"\0", 1)[0]
                    offset += length
                    if mask & _IN_Q_OVERFLOW:
                        changes.overflow = True
                    parent = self._dirs.get(wd)
                    if parent is not None:
                        changes.paths.add(parent / os.fsdecode(name) if name else parent)
                        if mask & _IN_IGNORED:
                            self._dirs.pop(wd, None)
                            self._paths.pop(parent, None)
                if offset != len(data):
                    changes.overflow = True
        except InterruptedError:
            # A signal can interrupt the readiness check; retry on next poll.
            pass
        except (OSError, ValueError):
            self.close()
            changes.overflow = True
        return changes

    def close(self):
        fd, self._fd = self._fd, -1
        self.available = False
        self._dirs.clear()
        self._paths.clear()
        if fd >= 0:
            os.close(fd)
