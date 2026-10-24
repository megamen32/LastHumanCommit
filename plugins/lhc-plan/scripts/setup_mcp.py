#!/usr/bin/env python3
"""Print stdio registration; does not alter any harness/user configuration."""
import json
from pathlib import Path

if __name__ == "__main__":
    print(json.dumps({"mcpServers": {"LhcPlan": {"command": "python3", "args": [str(Path(__file__).resolve().with_name("plan_mcp.py"))]}}}, indent=2))
