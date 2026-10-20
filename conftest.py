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
