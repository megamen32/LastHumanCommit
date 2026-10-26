#!/usr/bin/env python3
"""Launch the single canonical LhcPlan implementation, bundled or in source."""
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[1]
for ancestor in (root, *root.parents):
    source = ancestor / "src/common/tools"
    if source.is_dir() and root.is_relative_to(ancestor / "plugins"):
        sys.path.insert(0, str(source))
        break
else:
    sys.path.insert(0, str(root / "tools"))

from lhc_plan_mcp import *  # compatibility for callers importing the launcher

if __name__ == "__main__":
    raise SystemExit(main())
