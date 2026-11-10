#!/usr/bin/env python3
"""The models available now, grouped by class (fast, middle, frontier).

Usage: lhc_model_list.py [--class fast|middle|frontier]
The list is config/models.json; ~/.config/lhc/models.json overrides it.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

CLASSES = ("fast", "middle", "frontier")
EMPTY_NOTE = {
    "middle": "middle: no models listed; use fast, and frontier only after a measured fast failure",
    "fast": "fast: no models listed; use frontier",
    "frontier": "frontier: no models listed; use fast and say so",
}


def list_models(config: dict, cls: str | None) -> dict:
    """Pure: the answer for one class or all of them."""
    if cls is not None and cls not in CLASSES:
        return {"ok": False, "error": f"unknown class {cls!r}; allowed: {', '.join(CLASSES)}"}
    described = config.get("classes", {})
    models = config.get("models", [])
    out = []
    for name in (cls,) if cls else CLASSES:
        members = [{"id": m["id"], "description": m.get("description", "")}
                   for m in models if m.get("class") == name]
        entry = {"class": name, "description": described.get(name, ""), "models": members}
        if not members:
            entry["note"] = EMPTY_NOTE[name]
        out.append(entry)
    return {"ok": True, "classes": out}


def load_config(config_home=None, package=None) -> dict:
    """Shell: ~/.config/lhc/models.json if present, else the package config."""
    home = Path(config_home or os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    here = Path(__file__).resolve().parent
    candidates = [home / "lhc" / "models.json"]
    candidates += [Path(package) / "config" / "models.json"] if package else \
        [here.parent / "config" / "models.json", here / "config" / "models.json"]
    for path in candidates:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
    return {"classes": {}, "models": []}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--class", dest="cls", choices=CLASSES)
    args = parser.parse_args(argv)
    print(json.dumps(list_models(load_config(), args.cls), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
