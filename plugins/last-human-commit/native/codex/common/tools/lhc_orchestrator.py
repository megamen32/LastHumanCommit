#!/usr/bin/env python3
"""Pre-1.10 name of lhc_dispatcher.py, kept so that running sessions and old hooks work.

Importing this module gives lhc_dispatcher itself; running it runs lhc_dispatcher.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lhc_dispatcher  # noqa: E402

if __name__ == "__main__":
    lhc_dispatcher.main()
else:
    sys.modules[__name__] = lhc_dispatcher
