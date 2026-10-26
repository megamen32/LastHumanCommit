#!/usr/bin/env python3
"""Atomic static bundle transport. Also executed verbatim by existing SSH aliases."""
from __future__ import annotations
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import tempfile


def deploy(webroot, project, name, identity, version, files):
    for value in (project, name, identity, version):
        if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,159}", value):
            raise ValueError("unsafe publication identifier")
    if not Path(webroot).is_absolute():
        raise ValueError("webroot must be absolute")
    if any(not re.fullmatch(r"(?:index\.html|version\.json|(?:view-)?r[0-9]{3,}\.html)", n) for n in files):
        raise ValueError("unsafe bundle filename")
    root = Path(webroot).resolve()
    parent = root / project
    if parent.is_symlink():
        raise ValueError("project directory must not be symlink")
    parent.mkdir(parents=True, exist_ok=True)
    parent.chmod(parent.stat().st_mode | 0o755)
    with (parent / (".lock-" + name)).open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        target = parent / name
        if target.exists() or target.is_symlink():
            if not target.is_symlink() or target.resolve().parent != parent:
                raise ValueError("publication path collision")
            if (target / ".lhc-owner").read_text() != identity:
                raise ValueError("publication owner collision")
        generation = parent / (".bundle-" + identity + "-" + version)
        if not generation.exists():
            stage = Path(tempfile.mkdtemp(prefix=".stage-", dir=parent))
            try:
                stage.chmod(0o755)
                (stage / ".lhc-owner").write_text(identity)
                (stage / ".lhc-owner").chmod(0o600)
                # Version is written last. The entire directory becomes visible
                # only by an atomic symlink replacement after every file exists.
                for name_in, content in sorted(files.items(), key=lambda p: p[0] == "version.json"):
                    (stage / name_in).write_text(content, encoding="utf-8")
                    (stage / name_in).chmod(0o644)
                os.rename(stage, generation)
            finally:
                if stage.exists():
                    for item in stage.iterdir():
                        item.unlink()
                    stage.rmdir()
        elif (generation / ".lhc-owner").read_text() != identity:
            raise ValueError("generation collision")
        generation.chmod(0o755)
        for filename in files:
            output = generation / filename
            if output.is_symlink():
                raise ValueError("bundle file must not be symlink")
            if not output.exists():
                # Repair missing derived output on an idempotent retry. Never
                # rewrite an existing immutable revision snapshot.
                fd, pending = tempfile.mkstemp(prefix=".repair-", dir=generation)
                try:
                    with os.fdopen(fd, "w", encoding="utf-8") as stream:
                        stream.write(files[filename])
                    os.replace(pending, output)
                finally:
                    if os.path.exists(pending):
                        os.unlink(pending)
            (generation / filename).chmod(0o644)
        temporary = parent / (".link-" + identity)
        temporary.unlink(missing_ok=True)
        temporary.symlink_to(generation.name, target_is_directory=True)
        os.replace(temporary, target)
        # Only this identity's obsolete generated bundles, never revision
        # snapshots or another publisher's directories. Keep a prior generation
        # for in-flight readers and every revision in the current generation.
        old = sorted((p for p in parent.glob(".bundle-" + identity + "-*")
                      if p != generation and p.is_dir() and not p.is_symlink()),
                     key=lambda p: p.stat().st_mtime, reverse=True)
        for obsolete in old[1:]:
            if (obsolete / ".lhc-owner").read_text() == identity:
                shutil.rmtree(obsolete)


if __name__ == "__main__":
    import sys
    deploy(**json.load(sys.stdin))
