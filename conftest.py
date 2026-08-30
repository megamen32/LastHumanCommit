"""Keep every pytest invocation in its own project-local temporary root."""

from __future__ import annotations

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


def pytest_configure(config) -> None:
    basetemp = _new_pytest_basetemp()
    config.option.basetemp = str(basetemp)
    config._lhc_project_basetemp = basetemp


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
