#!/usr/bin/env python3
"""Launch the bundled publishing facade; no source-checkout dependency.

The server lives in the Last Human Commit package, next to the tools it
calls, so the marketplace keeps exactly one plugin.
"""
from plan_mcp import main

if __name__ == "__main__":
    raise SystemExit(main())
