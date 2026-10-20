"""Pytest LHC state must remain under this invocation's temporary Git root."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
import lhc_time_guard as guard


def test_fake_learning_state_resolves_inside_per_run_basetemp(tmp_path, request):
    basetemp = Path(request.config._lhc_project_basetemp).resolve(strict=True)
    project_agents = Path(__file__).resolve().parents[1] / ".agents"

    path = guard.learning_path(tmp_path, "codex", "pytest-state-isolation-sentinel")

    assert path.is_relative_to(basetemp)
    assert not path.is_relative_to(project_agents)
    top = subprocess.run(
        ["git", "-C", str(tmp_path), "rev-parse", "--show-toplevel"],
        check=True, capture_output=True, text=True,
    ).stdout.strip()
    assert Path(top).resolve() == basetemp
