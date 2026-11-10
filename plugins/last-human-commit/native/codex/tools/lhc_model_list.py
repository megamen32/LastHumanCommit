#!/usr/bin/env python3
"""The models available now, grouped by class (fast, middle, frontier).

Usage: lhc_model_list.py [--class fast|middle|frontier] [--no-herder]
Classes go by model family (config/models.json); Agent Herder, when it answers, adds the live catalog and quotas.
Config: ~/.config/lhc/models.json overrides it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
from pathlib import Path

try:
    from lhc_coding_benchmark import benchmark_thresholds, classify_model
except ImportError:  # package import from a bundled common.tools tree
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from lhc_coding_benchmark import benchmark_thresholds, classify_model

CLASSES = ("fast", "middle", "frontier")
EMPTY_NOTE = {
    "middle": "middle: no models listed; use fast, and frontier only after a measured fast failure",
    "fast": "fast: no models listed; use frontier",
    "frontier": "frontier: no models listed; use fast and say so",
}


def tokens(text: str) -> set[str]:
    """Pure: lowercase alphanumeric tokens of an id or a rule."""
    return set(re.findall(r"[a-z0-9]+", str(text).lower()))


def class_of(config: dict, model_id: str) -> str | None:
    """Pure: resolve an explicit curated ID before legacy family fallbacks."""
    candidate = str(model_id).strip().lower()
    curated = config.get("curated", {})
    if isinstance(curated, dict):
        for cls, ids in curated.items():
            if not isinstance(ids, list):
                continue
            for configured_id in ids:
                target = str(configured_id).strip().lower()
                if target and (candidate == target or candidate.endswith("/" + target)
                               or candidate.endswith("-" + target)):
                    return str(cls)
    have = tokens(model_id)
    for rule in config.get("families", []):
        if tokens(rule.get("match", "")) <= have and tokens(rule.get("match", "")):
            return rule.get("class")
    return None


def _from_herder(config: dict, available: list, benchmark: dict | None = None) -> tuple[dict, list, dict]:
    """Pure: Herder catalog -> {class: [{id, harnesses, source}]}, unclassified."""
    seen: dict[str, list] = {}
    for harness in available:
        for model_id in harness.get("models", []):
            names = seen.setdefault(model_id, [])
            if harness.get("harness") not in names:
                names.append(harness.get("harness"))
    grouped: dict[str, list] = {}
    unclassified = []
    classification = benchmark_thresholds(config, benchmark)
    for model_id, harnesses in seen.items():
        cls, source, score = classify_model(config, model_id, benchmark)
        if cls is None:
            unclassified.append({"id": model_id, "harnesses": harnesses,
                                 "classification_source": source,
                                 **({"coding_score": score} if score is not None else {})})
        else:
            grouped.setdefault(cls, []).append({
                "id": model_id,
                "harnesses": harnesses,
                "source": "herder",
                "classification_source": source,
                **({"coding_score": score} if score is not None else {}),
            })
    return grouped, unclassified, classification


def list_models(config: dict, cls: str | None, available: list | None = None,
                quotas: list | None = None, status: str = "unavailable",
                benchmark: dict | None = None) -> dict:
    """Pure: the answer for one class or all; Herder data is optional."""
    if cls is not None and cls not in CLASSES:
        return {"ok": False, "error": f"unknown class {cls!r}; allowed: {', '.join(CLASSES)}"}
    described = config.get("classes", {})
    examples = config.get("examples", {})
    grouped, unclassified, classification = (
        _from_herder(config, available, benchmark) if available is not None else ({}, [], benchmark_thresholds(config, benchmark))
    )
    out = []
    for name in (cls,) if cls else CLASSES:
        members = grouped.get(name) or [{"id": i, "source": "config"} for i in examples.get(name, [])]
        entry = {"class": name, "description": described.get(name, ""), "models": members}
        if not members:
            entry["note"] = EMPTY_NOTE[name]
        out.append(entry)
    result = {"ok": True, "classes": out, "herder": "ok" if available is not None else status,
              "classification": classification}
    if available is not None:
        result["unclassified"] = unclassified
        result["quotas"] = quotas or []
    return result


def herder_snapshot(timeout: float = 3.0, client_factory=None) -> dict | None:
    """Shell: Herder's live catalog and quotas, or None on any problem. Never raises."""
    if os.environ.get("LHC_HERDER", "").strip().lower() == "off":
        return None
    try:
        if client_factory is None:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from lhc_execution_transport import HerderMcpClient as client_factory
        client = client_factory(timeout=timeout)
        catalog = client.call("list_models", {})
        harnesses = catalog["harnesses"]
        if not isinstance(harnesses, list) or not all(
                isinstance(h, dict) and isinstance(h.get("models", []), list) for h in harnesses):
            return None
        quotas = []
        try:
            raw_quotas = client.call("model_quotas", {}).get("providers", [])
            if isinstance(raw_quotas, list):
                for p in raw_quotas:
                    if not isinstance(p, dict) or not isinstance(p.get("provider"), str):
                        continue
                    quotas.append({"provider": p["provider"], "state": p.get("state", "unknown"),
                                   "checked_at": p.get("checkedAt")})
        except Exception:
            # A quota outage must not hide a valid live model catalog.
            quotas = []
        return {"harnesses": harnesses, "quotas": quotas}
    except Exception:
        return None


def load_coding_manifest(config: dict, timeout: float = 3.0,
                         opener=None) -> dict | None:
    """Best-effort loader for a compact manifest or models-supplement JSON.

    The model catalog remains usable when the benchmark source is unavailable;
    callers receive ``None`` and the pure classifier reports family fallbacks.
    ``opener`` is injectable so tests never need a network request.
    """
    benchmark = config.get("coding_benchmark", {})
    if not isinstance(benchmark, dict):
        return None
    if os.environ.get("LHC_CODING_BENCHMARK", "").strip().lower() == "off":
        return None
    path_value = os.environ.get("LHC_CODING_BENCHMARK_MANIFEST", "").strip()
    path_value = path_value or str(benchmark.get("manifest_path", "")).strip()
    if path_value:
        paths = [Path(path_value)]
        if not Path(path_value).is_absolute():
            here = Path(__file__).resolve().parent
            paths.insert(0, here.parent / "config" / path_value)
        for path in paths:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
    url = os.environ.get("LHC_CODING_BENCHMARK_URL", "").strip()
    url = url or str(benchmark.get("manifest_url", "")).strip()
    if not url:
        return None
    try:
        open_url = opener or urllib.request.urlopen
        request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "lhc/1"})
        with open_url(request, timeout=timeout) as response:
            payload = response.read()
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        data.setdefault("source", url)
        data.setdefault("metric", benchmark.get("metric", "swebench_pro"))
        return data
    except (OSError, ValueError, TimeoutError):
        return None


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
    return {"classes": {}, "families": [], "examples": {}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--class", dest="cls", choices=CLASSES)
    parser.add_argument("--no-herder", action="store_true", help="skip Agent Herder")
    args = parser.parse_args(argv)
    snap = None if args.no_herder else herder_snapshot()
    config = load_config()
    benchmark = load_coding_manifest(config)
    status = "off" if args.no_herder or os.environ.get("LHC_HERDER", "").lower() == "off" else "unavailable"
    print(json.dumps(list_models(config, args.cls, snap and snap["harnesses"],
                                 snap and snap["quotas"], status, benchmark), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
