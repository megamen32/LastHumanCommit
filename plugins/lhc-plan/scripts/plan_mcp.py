#!/usr/bin/env python3
"""Launch the bundled CLI facade; no source-checkout dependency."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "common/tools"))
from lhc_plan_mcp import main

if __name__ == "__main__":
    main()
