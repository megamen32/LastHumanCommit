#!/usr/bin/env python3
"""Development entrypoint for the versioned HTTP capability installer."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
from install_http_capabilities import main


if __name__ == "__main__":
    raise SystemExit(main())
