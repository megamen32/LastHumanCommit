"""Every LHC tool still compiles and imports.

Background mechanisms (outcome, milestone, spawn budgets, factory) keep only
this smoke check; their behaviour is not part of the core contract.
"""
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"


@pytest.mark.parametrize("tool", sorted(p.stem for p in TOOLS.glob("lhc_*.py")))
def test_tool_imports(tool):
    result = subprocess.run([sys.executable, "-c", f"import {tool}"], cwd=TOOLS,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr[-2000:]
