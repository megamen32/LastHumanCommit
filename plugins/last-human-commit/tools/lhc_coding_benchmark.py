#!/usr/bin/env python3
"""Pure coding-benchmark manifest parsing and model-class thresholds.

The manifest is deliberately a small value object at this boundary.  A shell
may fetch a models-supplement artifact and pass its decoded JSON here, while
tests can provide a fixture without network or filesystem access.
"""
from __future__ import annotations

import re
from typing import Any


SCORE_FIELDS = ("arena_code", "swebench_pro", "swe_bench_verified")


def _norm(model_id: str) -> str:
    """Normalize an id for exact and provider-independent manifest lookup."""
    text = str(model_id).strip().lower().lstrip("~")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def _family_tokens(model_id: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(model_id).lower()))


def _as_score(value: Any) -> float | None:
    """Accept normalized [0,1] or percentage [0,100] scores."""
    if isinstance(value, bool):
        return None
    try:
        score = float(value)
    except (TypeError, ValueError):
        return None
    if score > 1.0 and score <= 100.0:
        score /= 100.0
    return round(score, 6) if 0.0 <= score <= 1.0 else None


def _record_score(record: dict[str, Any], metric: str) -> float | None:
    """Read one record, preferring the configured coding metric."""
    # coding-benchmarks.json stores one primary row per model.  Its top-level
    # metric tells us which rows are comparable for thresholding; do not mix a
    # Verified percentage into a Pro threshold merely because both are named
    # ``score``.
    source = record.get("source")
    if source is not None:
        if str(source) != metric:
            return None
        return _as_score(record.get("normalized_score", record.get("score", record.get("raw_score"))))
    if metric == "arena_code":
        arena = record.get("arena")
        if isinstance(arena, dict) and arena.get("leaderboard") == "code":
            return _as_score(arena.get("score"))
        return None
    raw = record.get(metric)
    if isinstance(raw, dict):
        return _as_score(raw.get("normalized_score", raw.get("score", raw.get("raw_score"))))
    return _as_score(raw)


def extract_scores(manifest: dict[str, Any] | None) -> dict[str, float]:
    """Flatten either a supplement artifact or a compact ``scores`` manifest."""
    if not isinstance(manifest, dict):
        return {}
    metric = str(manifest.get("metric", "swebench_pro"))
    compact = manifest.get("scores")
    if isinstance(compact, dict):
        out: dict[str, float] = {}
        for model_id, value in compact.items():
            score = _as_score(value)
            if score is None and isinstance(value, dict):
                if value.get("source") is not None and str(value.get("source")) != metric:
                    continue
                score = _as_score(value.get("normalized_score", value.get("score", value.get("raw_score"))))
            if score is not None:
                out[str(model_id)] = score
        return out
    models = manifest.get("models")
    if not isinstance(models, dict):
        return {}
    out: dict[str, float] = {}
    for model_id, record in models.items():
        if isinstance(record, dict) and (score := _record_score(record, metric)) is not None:
            out[str(model_id)] = score
    return out


def _score_index(manifest: dict[str, Any] | None) -> dict[str, float]:
    """Index exact and normalized IDs without mutating the manifest."""
    indexed: dict[str, float] = {}
    for model_id, score in extract_scores(manifest).items():
        indexed.setdefault(str(model_id).lower(), score)
        indexed.setdefault(_norm(model_id), score)
        # Herder often returns provider-local IDs (``gpt-6.1-sol``) while the
        # supplement uses canonical ``openai/gpt-6.1-sol`` IDs.
        if "/" in str(model_id):
            indexed.setdefault(str(model_id).rsplit("/", 1)[1].lower(), score)
            indexed.setdefault(_norm(str(model_id).rsplit("/", 1)[1]), score)
    return indexed


def _configured(config: dict[str, Any], key: str, default: list[str]) -> list[str]:
    benchmark = config.get("coding_benchmark", {})
    values = benchmark.get(key, default) if isinstance(benchmark, dict) else default
    return [str(value) for value in values] if isinstance(values, list) else default


def _score_for(model_id: str, scores: dict[str, float]) -> float | None:
    score = scores.get(str(model_id).lower())
    return score if score is not None else scores.get(_norm(model_id))


def _family_score(anchor: str, scores: dict[str, float]) -> float | None:
    """Use the best scored model of an anchor family when its new ID is absent."""
    anchor_tokens = _family_tokens(anchor)
    ignored = {"openai", "anthropic", "claude", "gpt", "pro", "global"}
    family_tokens = anchor_tokens - ignored - {token for token in anchor_tokens if token.isdigit()}
    if not family_tokens:
        return None
    vendor = anchor.split("/", 1)[0].lower() if "/" in anchor else None
    candidates: list[float] = []
    for model_id, score in scores.items():
        if vendor and "/" in model_id and model_id.split("/", 1)[0] != vendor:
            continue
        if family_tokens <= _family_tokens(model_id):
            candidates.append(score)
    # A named family is an anchor family, so its weakest measured member is
    # the conservative cut.  This prevents a newer, stronger Opus from
    # making an older explicitly frontier Opus look like middle.
    return min(candidates, default=None)


def _family_match(model_id: str, families: list[str]) -> bool:
    tokens = _family_tokens(model_id)
    return any(_family_tokens(family) <= tokens for family in families if _family_tokens(family))


def _explicit_match(model_id: str, configured_id: str) -> bool:
    """Match a curated provider-local ID to canonical or provider-qualified IDs."""
    candidate = _norm(model_id)
    target = _norm(configured_id)
    return candidate == target or candidate.endswith("-" + target)


def _anchor_match(model_id: str, anchors: list[str]) -> bool:
    candidate = _family_tokens(model_id)
    for anchor in anchors:
        # Herder may omit the provider namespace while the manifest keeps it.
        # Compare the model portion of a canonical anchor in that case.
        model_part = str(anchor).split("/", 1)[-1]
        anchor_tokens = _family_tokens(model_part)
        if anchor_tokens and anchor_tokens <= candidate:
            return True
    return False


def benchmark_thresholds(config: dict[str, Any], manifest: dict[str, Any] | None) -> dict[str, Any]:
    """Compute the two cuts from named anchors and fast-family scores."""
    scores = _score_index(manifest)
    anchors = _configured(config, "frontier_anchors", [])
    anchor_scores: dict[str, float] = {}
    missing: list[str] = []
    for anchor in anchors:
        score = _score_for(anchor, scores)
        if score is None:
            score = _family_score(anchor, scores)
        if score is None:
            missing.append(anchor)
        else:
            anchor_scores[anchor] = score

    fast_families = _configured(config, "fast_families", ["fast", "haiku"])
    fast_scores = [score for model_id, score in scores.items()
                   if _family_match(model_id, fast_families)]
    for anchor in _configured(config, "fast_anchors", []):
        score = _score_for(anchor, scores)
        if score is not None:
            fast_scores.append(score)
    # The normalized index stores exact and normalized aliases.  De-duplicate
    # by score so an ID does not get to influence the ceiling twice.
    fast_max = max(fast_scores, default=None)
    frontier_min = min(anchor_scores.values(), default=None)
    return {
        "frontier_min": frontier_min,
        "fast_max": fast_max,
        "frontier_anchor_scores": anchor_scores,
        "missing_frontier_anchors": missing,
        "metric": (manifest or {}).get("metric", "swebench_pro"),
        "source": (manifest or {}).get("source", "unavailable"),
        "assignment_policy": "curated_only",
    }


def classify_model(config: dict[str, Any], model_id: str,
                   manifest: dict[str, Any] | None) -> tuple[str | None, str, float | None]:
    """Classify one model and return ``(class, source, coding_score)``.

    Benchmark values are measurements.  They are reported with a model but do
    not turn an arbitrary live catalog entry into an allowed assignment.  The
    authoritative set is the curated list, with the explicit Fable/Opus and
    Astra/Sol family rules retained for newly versioned IDs.
    """
    scores = _score_index(manifest)
    score = _score_for(model_id, scores)
    curated = config.get("curated", {})
    if isinstance(curated, dict):
        for cls, ids in curated.items():
            if isinstance(ids, list) and any(_explicit_match(model_id, str(item)) for item in ids):
                return str(cls), "curated", score
    frontier_anchors = _configured(config, "frontier_anchors", [])
    # The owner explicitly excludes Luna from frontier and from the curated
    # assignment set. Its score is telemetry only.
    never_frontier = _configured(config, "never_frontier_families", ["luna"])
    if _family_match(model_id, never_frontier):
        return None, "benchmark_only" if score is not None else "unclassified", score

    frontier_families = _configured(config, "frontier_families", ["fable", "opus"])
    # Fable and Opus are family guarantees; keep their provenance distinct
    # from the four named version anchors in the response.
    if _family_match(model_id, [family for family in frontier_families if family in {"fable", "opus"}]):
        return "frontier", "frontier_family", score
    if _anchor_match(model_id, frontier_anchors):
        return "frontier", "frontier_family", score
    if _family_match(model_id, frontier_families):
        return "frontier", "frontier_family", score
    return None, "benchmark_only" if score is not None else "unclassified", score
