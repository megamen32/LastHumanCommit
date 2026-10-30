#!/usr/bin/env python3
"""Live model-catalog prices, tier suggestion and leaf cost estimates.

LHC's economics say "routine work on a cheap model, expensive models only for
decisions", but the repository carried no price data at all. This tool closes
that gap from the preferred models-supplement catalog and models.dev baseline so that a model
shipping next week is selectable without editing this file: resolution is by
normalized id/name against the fetched catalog, tiers are inferred from the
catalog's own name markers and price distribution, and nothing here is an
enumerated list of known models. If a price is absent it stays absent - the
tool never invents a number, and it never substitutes a different model
silently (project law in AGENTS.md).

Commands
    resolve <model-string>  every provider route that serves this exact model,
                            ranked by effective price, with the alternatives.
    suggest --tier T        the cheapest catalog entries that pass a capability
                            gate for that tier, each with a one-line reason.
    cost --model M --minutes N
                            USD estimate for one leaf, always as a range.
    tpm --class C --samples A,B,C
                            record a measured token-burn distribution for one
                            class into the pinned table; the rate is the
                            median of the samples.
    snapshot -o FILE        pin the catalog subset a plan was priced with, so
                            the plan stays reproducible offline.

Catalog source and cache
    The preferred supplement contributes its explicit RouterAI reference API
    tariffs and capabilities; models.dev supplies the baseline provider routes.
    Both source receipts are pinned when merged. A reference tariff estimates
    API-equivalent work and does not attest a native subscription's billed spend
    or change the actual execution provider.
    The raw api.json is cached under the repository ``.tmp/`` directory
    (default ``<repo>/.tmp/lhc_models/api.json`` plus a ``.meta.json`` sibling)
    with a TTL of ``--max-age`` seconds, default 24 h, fetched with urllib and a
    10 s timeout. A network failure falls back to the cache and marks
    ``"stale": true``. With neither cache nor network the command exits 3 and
    says so; no price is fabricated. Use ``--catalog FILE`` to price against a
    pinned file, ``--offline`` to refuse any fetch, ``--refresh`` to ignore a
    fresh cache.

Tier inference (data, not a name list)
    ``fast`` and ``frontier`` are a policy over the live catalog, in this order:
      1. an entry is *flash-class* when any of ``FAST_NAME_MARKERS`` appears as
         a whole token of its normalized id, name or family (``flash``, ``lite``,
         ``mini``, ``nano``, ``small``, ``turbo``, ``haiku``, ``fast``,
         ``efficient``, ``instant``, ``air``, ``spark``, ``swift``, ``compact``);
      2. the *frontier band* is the set of current, priced, gate-passing entries
         that are not flash-class; its median effective price is the reference;
      3. ``fast`` candidates are flash-class entries whose blended price is at or
         below ``median * --fast-ratio`` (default 0.5);
      4. ``frontier`` candidates are non-flash-class entries whose blended price
         is at or above ``median * --frontier-ratio`` (default 1.0) and which
         declare ``reasoning`` unless ``--no-require-reasoning`` is passed;
      5. markers, ratios and the reasoning requirement are CLI-overridable, so a
         catalog whose vocabulary changes never requires a code change here.
    Every result echoes the ``policy`` block that produced it, so a plan can
    prove which rule picked the model it dispatched.

Ranking and pricing conventions
    effective price = input * ``--input-share`` + output * (1 - ``--input-share``)
    in USD per 1 000 000 tokens, default share 0.8 (a coding leaf reads far more
    than it writes). A route with both prices 0 is a flat subscription/"coding
    plan" route: that is a real marginal-cost signal, so it is kept and labelled
    ``pricing_kind: "plan-included"`` with a note, and ``--exclude-flat-routes``
    removes it when a plan must compare metered compute only. A route with no
    price data is ``pricing_kind: "unknown"`` (or ``"incomplete"`` when only one
    side is listed), is never ranked and is never shown as zero. An implicit
    ``--min-context 200000`` floor applies unless disabled, because no agent
    leaf runs on a toy window. Entries whose ``status`` is ``deprecated`` are
    removed and counted; ``--include-deprecated`` brings them back, labelled.

Name matching (one tolerance, one law)
    A request is compared to a catalog entry by normalized name, never by an
    alias table, so a model that ships next week resolves on its data alone. Two
    rules shape that comparison:
      * *family letter*: a catalog often glues the model family's letter onto the
        version number, so the entry reads ``vendor-x2-1-flash`` where a policy
        spells only the version, ``vendor-2.1-flash``. ``name_match`` accepts
        that difference and nothing else like it: exactly one extra run, a single
        ASCII letter, sitting directly in front of the digits, with every other
        letter- and digit-run identical, in either spelling direction. There is
        no similarity threshold and no dropped token, so a request for one model
        never grows into a neighbouring one, and a letter never promotes a free
        or preview SKU out of the ``variant`` bucket. Every such resolution
        carries ``match_note``, so the naming difference is visible, not silent.
      * *vendor hint*: a ``Vendor/model`` request is a hard requirement, not a
        ranking preference. The hint must appear in the provider id, in the
        vendor part of the catalog model id, or in the model's own id, name or
        family; otherwise the entry is some other vendor's model and is never
        offered as ``exact``/``variant``/``prefix``. It may only show up as a
        clearly-labelled ``nearest`` line for a human, never as a resolution.

    A matched row is "rankable" when it passes the capability gate and has a
    usable price, and "auto-selectable" when its name is an exact match or
    differs only by a variant suffix. A *prefix* match - a request for
    ``glm-5.3`` that only finds ``glm-5.3-flash`` - is a DIFFERENT model, so it
    is priced, listed under ``needs_human_confirmation`` and never auto-selected:
    silent substitution is forbidden by project law. Rankable auto-selectable
    rows come first, ordered by confidence bucket (exact name, then a name that
    differs only by a variant suffix such as ``-free``/``-preview``/``-highspeed``)
    and, inside a bucket, by effective price - with metered routes ranked before
    plan-included ones, so a 0 USD marginal price never silently wins a
    comparison it only wins on paper. Price ties go to the newer and
    larger-window route rather than to an alphabetical provider name. Everything
    else is still listed afterwards with its reason, so nothing is hidden from
    the human who has to choose.

Cost basis
    ``cost`` multiplies minutes x tokens-per-minute x blended price. Without
    ``--tokens-per-minute`` it uses ``PROVISIONAL_TPM`` (fast 2000, frontier
    1200, unknown 1600 tokens/minute) - provisional planning constants of the
    right order of magnitude for a coding agent, not measured from LHC runs -
    and marks the result ``"basis": "provisional-tpm"`` so downstream code can
    label it an estimate. Money is reported with two significant digits and as a
    range across the matched routes, never as four decimals of false precision.

    The measured rate is data, not a constant: ``load_measured_tpm`` reads a
    table of real token-burn samples (default ``<repo>/.tmp/lhc_models/tpm-measured.json``,
    overridable with ``LHC_TPM_MEASURED_FILE``) and ``tpm_for_tier`` answers with
    the measured figure and the label ``measured`` when the table carries that
    class, and with ``PROVISIONAL_TPM`` and the label ``provisional`` when it does
    not. No editing of this file is needed to retire a provisional number.
    ``leaf_estimate`` is the one call the plan kernel makes: model (declared alias
    as written, or the cheapest route the class policy picks), tokens, dollars and
    the label of every number, or a reason why there is no number.

Token burn (the measured distribution)
    The rate behind a leaf's token estimate is a measurement, and a
    measurement is data: it lives in the pinned table next to the catalog
    snapshot the plan was priced with, never as a constant in this file. The
    table carries one entry per class, so fast and frontier are estimated
    separately, and each entry says how many samples it stands on. The old
    planning constants stay as the last resort of a class nobody measured:
    such a class is priced with ``PROVISIONAL_TPM`` and labelled
    ``provisional``, because a number without a measurement behind it must not
    be shown to a human as a fact.
    ``tpm`` records a new measurement into the pinned table:
    ``lhc_models.py tpm --class fast --samples 322436,359243 --note "..."``.

Exit codes: 0 handled, 2 no matching route or no route passes the gate,
3 catalog unavailable (no network and no cache), argparse usage per argparse (2).
Stdout is one JSON object; human-facing complaints go to stderr.
"""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
import time
import urllib.error
import urllib.request


SUPPLEMENT_URL = "https://github.com/megamen32/models-supplement/raw/refs/heads/main/supplement.json"
BASELINE_CATALOG_URL = "https://models.dev/api.json"
CATALOG_URL = SUPPLEMENT_URL
DEFAULT_TTL_SECONDS = 86_400
FETCH_TIMEOUT_SECONDS = 10
USER_AGENT = "lhc-models/1.0 (Last Human Commit price resolver; +https://models.dev)"
CACHE_FILE_NAME = "api.json"
CACHE_META_NAME = "api.meta.json"

DEFAULT_INPUT_SHARE = 0.8
DEFAULT_MIN_CONTEXT = 200_000
PROVISIONAL_TPM = {"fast": 2000, "frontier": 1200, "unknown": 1600}
PROVISIONAL_NOTE = (
    "tokens-per-minute is a provisional planning constant, not a measured LHC rate; the "
    "range widens it by 0.5x..2x, and rerunning with --tokens-per-minute narrows the range "
    "to the catalog price spread alone"
)
FLAT_PLAN_NOTE = (
    "flat subscription route: the catalog lists 0 USD marginal cost, the subscription "
    "itself is not priced here, so this leaf costs 0 marginal USD and must not be read "
    "as free unlimited compute"
)

FAST_NAME_MARKERS = (
    "flash", "lite", "mini", "nano", "small", "turbo", "haiku", "fast", "efficient",
    "instant", "air", "spark", "swift", "compact",
)
VARIANT_SUFFIXES = ("free", "preview", "highspeed", "latest", "experimental")
CONFIDENCE_ORDER = {"exact": 0, "variant": 1, "prefix": 2, "catalog": 0}
# A prefix match is a DIFFERENT model whose name merely starts with the request
# (``glm-5.3`` -> ``glm-5.3-flash``), so it is reported for a human and never
# auto-selected: silent substitution is forbidden by project law.
AUTO_SELECTABLE_CONFIDENCES = ("exact", "variant", "catalog")
HIDDEN_STATUSES = ("deprecated",)
PRICE_EXCLUSION_KEYS = {"unknown": "price_unknown", "incomplete": "price_incomplete"}

_TOKEN_SPLIT = re.compile(r"[^a-z0-9]+")
_RUN_SPLIT = re.compile(r"[a-z]+|[0-9]+")
FAMILY_LETTER_NOTE = (
    "the catalog attaches a family letter to the version number, so the spelling of the "
    "version differs; every other name part matches exactly, so this is the requested model "
    "and not a substitution"
)


class CatalogUnavailable(RuntimeError):
    """No live catalog and no usable cache: pricing must stop, not guess."""


# --------------------------------------------------------------- normalization


def normalize(value: object) -> str:
    """Lower-case, and collapse ``.``/``_``/spaces/quotes/slashes into single dashes."""
    if value is None:
        return ""
    return _TOKEN_SPLIT.sub("-", str(value).strip().lower()).strip("-")


def tokenize(value: object) -> list[str]:
    return [token for token in normalize(value).split("-") if token]


def runs(value: object) -> list[str]:
    """A normalized name chopped into maximal letter-runs and digit-runs.

    ``vendor-x2-1-flash`` becomes ``[vendor, x, 2, 1, flash]`` while a request
    that spells the version without the family letter, ``vendor-2-1-flash``,
    becomes ``[vendor, 2, 1, flash]``. Token lists cannot show that difference at
    all, because the catalog glues the letter to the digits inside one token;
    splitting the runs apart is what makes the two spellings comparable.
    """
    return _RUN_SPLIT.findall(normalize(value))


def differs_by_family_letter(request_runs: list[str], own_runs: list[str]) -> bool:
    """True when ``own_runs`` is the request plus exactly one letter glued to a number.

    This is the only naming tolerance in the resolver, and it is narrow on
    purpose: the extra run must be a SINGLE ASCII letter, it must sit directly in
    front of a digit run (that is how a catalog writes a family letter onto a
    version number), and every remaining run must be identical. Nothing is ever
    dropped from the request, no multi-letter token is ignored and there is no
    similarity threshold, so a trailing letter that is part of a model's own name
    (the letter comes after the digits, not before them) never matches, and a
    neighbouring model of another vendor cannot answer for the requested one.
    """
    if len(own_runs) != len(request_runs) + 1:
        return False
    for index, run in enumerate(own_runs):
        if len(run) != 1 or not run.isalpha():
            continue
        if index + 1 >= len(own_runs) or not own_runs[index + 1].isdigit():
            continue
        if own_runs[:index] + own_runs[index + 1:] == request_runs:
            return True
    return False


def strip_vendor(value: object) -> tuple[str, str]:
    """Split ``Vendor/Model`` into a normalized vendor hint and model string."""
    text = str(value or "")
    if "/" in text:
        vendor, model = text.rsplit("/", 1)
        return normalize(vendor), normalize(model)
    return "", normalize(text)


def without_variant_suffix(normalized: str) -> str:
    tokens = [token for token in normalized.split("-") if token]
    while tokens and tokens[-1] in VARIANT_SUFFIXES:
        tokens.pop()
    return "-".join(tokens)


def round_money(value: float) -> float:
    """Two significant digits: an estimate must not look like an invoice."""
    if not value:
        return 0.0
    if abs(value) >= 1:
        return round(value, 2)
    magnitude = int(math.floor(math.log10(abs(value)))) + 1
    return round(value, max(0, 2 - magnitude))


def round_price(value) -> float | None:
    """Catalog prices are data, not estimates: keep them, drop float noise only."""
    return None if value is None else round(value, 6)


# ---------------------------------------------------------------- the capability gate


def flag(model: dict, key: str):
    value = model.get(key)
    return value if isinstance(value, bool) else None


def modalities(model: dict, direction: str) -> list[str]:
    data = model.get("modalities")
    if not isinstance(data, dict):
        return []
    values = data.get(direction)
    return [str(value).lower() for value in values] if isinstance(values, list) else []


CAPABILITY_FLAGS = {
    "tool_call": lambda model: flag(model, "tool_call"),
    "reasoning": lambda model: flag(model, "reasoning"),
    "structured_output": lambda model: flag(model, "structured_output"),
    "temperature": lambda model: flag(model, "temperature"),
    "open_weights": lambda model: flag(model, "open_weights"),
    "attachment": lambda model: flag(model, "attachment"),
    "vision": lambda model: "image" in modalities(model, "input"),
    "video": lambda model: "video" in modalities(model, "input"),
    "audio_input": lambda model: "audio" in modalities(model, "input"),
}


def positive_int(name: str, raw: str) -> int:
    try:
        value = int(str(raw))
    except ValueError as error:
        raise ValueError(f"{name}:<n> needs a whole number, got {raw!r}") from error
    if value <= 0:
        raise ValueError(f"{name}:<n> needs a positive number, got {value}")
    return value


def parse_needs(spec: str | None, *, min_context: int | None = DEFAULT_MIN_CONTEXT) -> dict:
    """Parse ``tool_call,vision,context:200000,output:32000`` into a capability gate."""
    needs = {"flags": [], "min_context": min_context, "min_output": None, "spec": spec or ""}
    for token in re.split(r"[,\s]+", (spec or "").strip()):
        if not token:
            continue
        name, separator, raw_value = token.partition(":")
        key = normalize(name).replace("-", "_")
        if separator and key in ("context", "min_context"):
            needs["min_context"] = positive_int(key, raw_value)
        elif separator and key in ("output", "min_output", "max_output"):
            needs["min_output"] = positive_int(key, raw_value)
        elif separator:
            raise ValueError(f"needs: {token!r} has a value for an unknown key {name!r}")
        elif key in CAPABILITY_FLAGS:
            needs["flags"].append(key)
        else:
            raise ValueError(
                f"unknown capability {token!r}; known: "
                + ", ".join(sorted(CAPABILITY_FLAGS))
                + ", context:<n>, output:<n>"
            )
    return needs


def numeric(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def gate_failures(model: dict, needs: dict) -> list[str]:
    failures = []
    for key in needs["flags"]:
        if CAPABILITY_FLAGS[key](model) is not True:
            failures.append(f"needs {key}")
    limit = model.get("limit") if isinstance(model.get("limit"), dict) else {}
    minimum = needs.get("min_context")
    if minimum is not None:
        context = numeric(limit.get("context"))
        if context is None or context < minimum:
            failures.append(f"needs context>={minimum}")
    minimum_output = needs.get("min_output")
    if minimum_output is not None:
        output = numeric(limit.get("output"))
        if output is None or output < minimum_output:
            failures.append(f"needs output>={minimum_output}")
    return failures


# ----------------------------------------------------------------- the catalog


def default_cache_dir() -> Path:
    """Catalog snapshots: LHC_MODELS_CACHE, else the checkout's .tmp/, else one user cache.

    A development checkout keeps its snapshots in its own .tmp/. An installed copy has no
    checkout (and every harness unpacks its own), so it shares ~/.cache/lhc/models;
    otherwise each copy would look for a snapshot nobody ever made.
    """
    override = os.environ.get("LHC_MODELS_CACHE", "").strip()
    if override:
        return Path(override).expanduser()
    repo_root = Path(__file__).resolve().parents[3]
    if (repo_root / ".git").exists():
        return repo_root / ".tmp" / "lhc_models"
    cache_home = os.environ.get("XDG_CACHE_HOME", "").strip() or str(Path.home() / ".cache")
    return Path(cache_home) / "lhc" / "models"


def fetch_raw(url: str) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=FETCH_TIMEOUT_SECONDS) as response:
        return response.read()


def iso_utc(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(epoch))


class Catalog:
    """The parsed catalog plus the provenance a plan needs in order to trust it."""

    def __init__(self, providers: dict, *, source: str, sha256: str, retrieved_at: float,
                 ttl_seconds: int, stale: bool, url: str, generated_at=None, sources=None):
        self.providers = providers
        self.source = source
        self.sha256 = sha256
        self.retrieved_at = float(retrieved_at)
        self.ttl_seconds = int(ttl_seconds)
        self.stale = stale
        self.url = url
        self.generated_at = generated_at
        self.sources = sources

    def meta(self) -> dict:
        return {
            "url": self.url,
            "source": self.source,
            "sha256": self.sha256,
            "retrieved_at": iso_utc(self.retrieved_at),
            "retrieved_at_epoch": self.retrieved_at,
            "ttl_seconds": self.ttl_seconds,
            **({"generated_at": self.generated_at} if self.generated_at else {}),
            **({"sources": self.sources} if self.sources else {}),
        }

    def entries(self):
        """Stable provider/model iteration, so ranking is reproducible."""
        for provider_id, provider in sorted(self.providers.items(), key=lambda item: str(item[0])):
            models = provider.get("models") if isinstance(provider, dict) else None
            if not isinstance(models, dict):
                continue
            for model_id in sorted(models, key=str):
                model = models[model_id]
                if isinstance(model, dict):
                    yield str(provider_id), str(model_id), provider, model


def _catalog_from_bytes(raw: bytes, *, source: str, url: str, retrieved_at: float,
                        ttl_seconds: int, stale: bool) -> Catalog:
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise CatalogUnavailable(f"catalog payload from {url} is not JSON: {error}") from error
    generated_at = None
    if isinstance(data, dict) and "schema_version" in data and isinstance(data.get("models"), dict):
        generated_at = data.get("generated_at")
        models = {}
        for canonical_id, entry in data["models"].items():
            if not isinstance(entry, dict) or not isinstance(entry.get("routerai"), dict):
                continue
            route = entry["routerai"]
            model_id = route.get("id")
            if not isinstance(model_id, str):
                continue
            models[model_id] = {
                "id": model_id, "name": entry.get("display_name", model_id),
                "canonical_model_id": entry.get("canonical_id", canonical_id),
                "cost": {"input": route.get("input_usd_per_1m"),
                         "output": route.get("output_usd_per_1m")},
                "limit": {"context": route.get("context_length")},
                "tool_call": route.get("supports_tools"), "reasoning": route.get("reasoning"),
                "structured_output": route.get("supports_structured_output"),
                "modalities": {"input": ["text", "image"] if route.get("supports_vision") else ["text"],
                               "output": ["text"]},
                "pricing_source": {"url": url, "generated_at": generated_at,
                                   "provider": "routerai", "basis": "reference-api-tariff"},
            }
        data = {"routerai": {"id": "routerai", "name": "RouterAI reference tariff", "models": models}}
    if not isinstance(data, dict) or not any(
        isinstance(provider, dict) and isinstance(provider.get("models"), dict)
        for provider in data.values()
    ):
        raise CatalogUnavailable(
            f"catalog payload from {url} has no provider/model objects; the shape changed")
    return Catalog(data, source=source, sha256=hashlib.sha256(raw).hexdigest(),
                   retrieved_at=retrieved_at, ttl_seconds=ttl_seconds, stale=stale, url=url,
                   generated_at=generated_at)


def _read_cache(raw_path: Path, meta_path: Path):
    try:
        raw = raw_path.read_bytes()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(meta, dict) or "retrieved_at" not in meta:
        return None
    if meta.get("sha256") != hashlib.sha256(raw).hexdigest():
        return None
    return raw, meta


def _write_cache(cache_dir: Path, raw_path: Path, meta_path: Path, raw: bytes, *, url: str,
                 retrieved_at: float, ttl_seconds: int) -> None:
    meta = {"url": url, "retrieved_at": float(retrieved_at),
            "sha256": hashlib.sha256(raw).hexdigest(), "ttl_seconds": int(ttl_seconds)}
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        for target, payload in ((raw_path, raw),
                                (meta_path, json.dumps(meta).encode("utf-8"))):
            temporary = target.with_name(target.name + ".tmp")
            temporary.write_bytes(payload)
            os.replace(temporary, target)
    except OSError as error:  # a read-only cache must not lose a live answer
        sys.stderr.write(f"warning: could not write the catalog cache under {cache_dir}: {error}\n")


def _load_catalog(*, cache_dir: Path | str | None = None, url: str = CATALOG_URL,
                 max_age_seconds: int = DEFAULT_TTL_SECONDS, path: str | None = None,
                 offline: bool = False, refresh: bool = False, fetcher=None,
                 now: float | None = None) -> Catalog:
    """Return the catalog, fetching at most once per TTL; raise when nothing works."""
    if path is not None:
        source_path = Path(path)
        clock = time.time() if now is None else now
        return _catalog_from_bytes(source_path.read_bytes(), source="file",
                                   url=f"file://{source_path}",
                                   retrieved_at=source_path.stat().st_mtime or clock,
                                   ttl_seconds=max_age_seconds, stale=False)

    cache_dir = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    raw_path, meta_path = cache_dir / CACHE_FILE_NAME, cache_dir / CACHE_META_NAME
    clock = time.time() if now is None else now
    fetcher = fetcher or fetch_raw
    cached = _read_cache(raw_path, meta_path)
    if cached is not None and cached[1].get("url") != url:
        cached = None

    if cached is not None:
        cached_raw, cached_meta = cached
        age = clock - float(cached_meta["retrieved_at"])
        # The requested --max-age owns freshness, so tightening it forces a refetch
        # even when the cache was written under a longer TTL.
        if not refresh and (age <= max_age_seconds or offline):
            return _catalog_from_bytes(cached_raw, source="cache",
                                       url=str(cached_meta.get("url", url)),
                                       retrieved_at=float(cached_meta["retrieved_at"]),
                                       ttl_seconds=max_age_seconds, stale=False)

    if offline:
        raise CatalogUnavailable(
            f"--offline needs a cached catalog under {cache_dir} and there is none; run "
            "once without --offline while the network is up, or pass --catalog FILE")

    try:
        raw = fetcher(url)
    except (OSError, urllib.error.URLError, ValueError) as error:
        if cached is None:
            raise CatalogUnavailable(
                f"cannot fetch {url} ({error.__class__.__name__}: {error}) and there is no "
                f"cached catalog under {cache_dir}; refusing to invent prices") from error
        sys.stderr.write(f"warning: fetch failed ({error.__class__.__name__}: {error}); "
                         "using the cached catalog and marking the result stale\n")
        cached_raw, cached_meta = cached
        return _catalog_from_bytes(cached_raw, source="cache",
                                   url=str(cached_meta.get("url", url)),
                                   retrieved_at=float(cached_meta["retrieved_at"]),
                                   ttl_seconds=max_age_seconds, stale=True)

    _write_cache(cache_dir, raw_path, meta_path, raw, url=url, retrieved_at=clock,
                 ttl_seconds=max_age_seconds)
    return _catalog_from_bytes(raw, source="network", url=url, retrieved_at=clock,
                               ttl_seconds=max_age_seconds, stale=False)


def load_catalog(*, cache_dir: Path | str | None = None, url: str = CATALOG_URL,
                 max_age_seconds: int = DEFAULT_TTL_SECONDS, path: str | None = None,
                 offline: bool = False, refresh: bool = False, fetcher=None,
                 now: float | None = None) -> Catalog:
    """Prefer supplement routes and retain the models.dev baseline routes.

    Explicit pinned files and custom URLs are self-contained and never trigger
    an additional source. Catalog routes price an API-equivalent estimate;
    resolving them does not configure or attest the execution provider.
    """
    options = dict(max_age_seconds=max_age_seconds, offline=offline, refresh=refresh,
                   fetcher=fetcher, now=now)
    fallback_dir = (Path(cache_dir) if cache_dir is not None else default_cache_dir()) / "baseline"
    try:
        preferred = _load_catalog(cache_dir=cache_dir, url=url, path=path, **options)
    except CatalogUnavailable:
        if path is not None or url != SUPPLEMENT_URL:
            raise
        return _load_catalog(cache_dir=fallback_dir, url=BASELINE_CATALOG_URL, **options)
    if path is not None or url != SUPPLEMENT_URL or preferred.generated_at is None:
        return preferred
    try:
        baseline = _load_catalog(cache_dir=fallback_dir, url=BASELINE_CATALOG_URL, **options)
    except CatalogUnavailable:
        return preferred
    # Only the same provider/model pair is overlaid. A reference tariff must
    # never replace a different provider's route or claim its billing terms.
    providers = dict(baseline.providers)
    for provider_id, provider in preferred.providers.items():
        previous = providers.get(provider_id, {})
        providers[provider_id] = {**previous, **provider,
            "models": {**previous.get("models", {}), **provider.get("models", {})}}
    preferred.sources = [preferred.meta(), baseline.meta()]
    # Memoized resolutions describe the merged data, so either source changing
    # must invalidate them. Freshness is bounded by the oldest contributing source.
    preferred.sha256 = hashlib.sha256(json.dumps(
        [(receipt["url"], receipt["sha256"]) for receipt in preferred.sources],
        separators=(",", ":"), ensure_ascii=True).encode("utf-8")).hexdigest()
    preferred.retrieved_at = min(preferred.retrieved_at, baseline.retrieved_at)
    preferred.ttl_seconds = min(preferred.ttl_seconds, baseline.ttl_seconds)
    preferred.providers = providers
    preferred.stale = preferred.stale or baseline.stale
    return preferred


# --------------------------------------------------------------- reading a price


def price_view(model: dict) -> dict:
    """The catalog's own price block, with an absent price kept absent."""
    cost = model.get("cost")
    if not isinstance(cost, dict):
        return {"pricing_kind": "unknown", "cost": None, "plan_included": False,
                "has_tiered_pricing": False, "blended": None,
                "pricing_note": "the catalog carries no cost block for this route; the "
                                "price is unknown and is never invented"}
    input_price, output_price = numeric(cost.get("input")), numeric(cost.get("output"))
    view = {
        "cost": {"input": input_price, "output": output_price,
                 "cache_read": numeric(cost.get("cache_read")),
                 "cache_write": numeric(cost.get("cache_write"))},
        "has_tiered_pricing": bool(cost.get("tiers") or cost.get("context_over_200k")),
    }
    if input_price is None and output_price is None:
        kind, note, blended = "unknown", ("the catalog lists no input/output price for this "
                                          "route, so it cannot be compared on price"), None
    elif input_price is None or output_price is None:
        kind, note, blended = "incomplete", ("only one of input/output price is listed; a "
                                             "blended leaf cost cannot be computed"), None
    elif input_price == 0 and output_price == 0:
        kind, note, blended = "plan-included", FLAT_PLAN_NOTE, 0.0
    else:
        kind, note, blended = "per-token", "", None
    view.update({"pricing_kind": kind, "plan_included": kind == "plan-included",
                 "pricing_note": note, "blended": blended})
    return view


def blended_price(view: dict, input_share: float) -> float | None:
    if view["blended"] is not None:
        return view["blended"]
    cost = view.get("cost") or {}
    input_price, output_price = cost.get("input"), cost.get("output")
    if input_price is None or output_price is None:
        return None
    return input_price * input_share + output_price * (1 - input_share)


def capability_view(model: dict) -> dict:
    limit = model.get("limit") if isinstance(model.get("limit"), dict) else {}
    return {
        "tool_call": flag(model, "tool_call"),
        "reasoning": flag(model, "reasoning"),
        "structured_output": flag(model, "structured_output"),
        "temperature": flag(model, "temperature"),
        "open_weights": flag(model, "open_weights"),
        "attachment": flag(model, "attachment"),
        "vision": "image" in modalities(model, "input"),
        "audio_input": "audio" in modalities(model, "input"),
        "context": numeric(limit.get("context")),
        "output": numeric(limit.get("output")),
    }


def has_marker(model: dict, markers) -> bool:
    tokens = set(tokenize(model.get("id"))) | set(tokenize(model.get("name"))) | set(
        tokenize(model.get("family")))
    return bool(tokens & set(markers))


def classify_tier(model: dict, effective, markers=FAST_NAME_MARKERS) -> str:
    """Marker label; ``suggest`` refines it against the live catalog median."""
    if has_marker(model, markers):
        return "fast"
    if effective is None:
        return "unpriced"
    return "frontier"


def candidate_row(provider_id: str, model_id: str, provider: dict, model: dict, *,
                  confidence: str | None, input_share: float, needs: dict,
                  markers=FAST_NAME_MARKERS) -> dict:
    view = price_view(model)
    effective = blended_price(view, input_share)
    failures = gate_failures(model, needs)
    limit = model.get("limit") if isinstance(model.get("limit"), dict) else {}
    status = model.get("status")
    return {
        "provider": provider_id,
        "provider_name": provider.get("name") if isinstance(provider, dict) else None,
        "model_id": model_id,
        "name": model.get("name"),
        "confidence": confidence,
        "pricing_kind": view["pricing_kind"],
        "plan_included": view["plan_included"],
        "pricing_note": view["pricing_note"] or None,
        "cost": view["cost"],
        "cost_unit": "USD per 1M tokens",
        "effective_price_per_mtok": round_price(effective),
        "input_price_per_mtok": (view["cost"] or {}).get("input"),
        "output_price_per_mtok": (view["cost"] or {}).get("output"),
        "cache_read_price_per_mtok": (view["cost"] or {}).get("cache_read"),
        "has_tiered_pricing": view["has_tiered_pricing"],
        "context_limit": numeric(limit.get("context")),
        "output_limit": numeric(limit.get("output")),
        "capabilities": capability_view(model),
        "family": model.get("family"),
        "status": status if isinstance(status, str) else "current",
        "release_date": model.get("release_date"),
        "passes_needs": not failures,
        "needs_failures": failures,
        "rankable": not failures and effective is not None,
        "auto_selectable": confidence in AUTO_SELECTABLE_CONFIDENCES,
        "flash_class": has_marker(model, markers),
        "tier": classify_tier(model, effective, markers),
    }


# ------------------------------------------------------------------- matching


def carries_vendor_hint(hint: str, provider_id: str | None, model_id: str, model: dict) -> bool:
    """Whether a route may answer an explicit ``Vendor/model`` request at all.

    The hint is allowed to live in the provider id, in the vendor part of the
    catalog model id (a gateway serves a vendor's model under its own provider
    name), or in the model's own id, name or family, because catalogs spell the
    vendor in all of those places. It has to live in one of them: a route whose
    data never mentions the requested vendor is some other vendor's model, and
    project law forbids answering a request with it as an exact, variant or
    prefix match. An empty hint (a request without ``Vendor/``) constrains
    nothing here - the name comparison already requires the requested tokens.
    """
    if not hint:
        return True
    for value in (provider_id, model_id, model.get("id"), model.get("name"),
                  model.get("family"), model.get("canonical_model_id")):
        text = normalize(value)
        if text and hint in text:
            return True
    return False


def name_match(query: str, model: dict, *, provider_id: str | None = None,
               model_id: str | None = None) -> tuple[str | None, str | None]:
    """``(confidence, note)`` for one catalog entry, or ``(None, None)``.

    ``exact`` - the same model, ``variant`` - the same model in another SKU
    suffix, ``prefix`` - a name that merely starts with the request, which is a
    DIFFERENT model and is only ever reported for a human to confirm.
    """
    hint, query_model = strip_vendor(query)
    if not query_model:
        return None, None
    if not carries_vendor_hint(hint, provider_id, model_id or "", model):
        return None, None
    own_values = [strip_vendor(model.get("id"))[1], strip_vendor(model.get("name"))[1]]
    own_values = [value for value in own_values if value]
    if query_model in own_values:
        return "exact", None
    if any(without_variant_suffix(value) == query_model for value in own_values):
        return "variant", None
    # A request may itself carry a variant suffix ("gpt-6-luna-free"): strip it
    # too and keep the match in the lower-confidence bucket.
    stripped_query = without_variant_suffix(query_model)
    if stripped_query and stripped_query != query_model:
        if stripped_query in own_values:
            return "variant", None
        if any(without_variant_suffix(value) == stripped_query for value in own_values):
            return "variant", None
    # The same model whose version is spelled with, or without, the family letter
    # the catalog glues onto it. The letter alone may differ, in either direction;
    # a form that only exists after a variant suffix was stripped stays in the
    # lower bucket, so a letter never buys a free route the promotion to exact.
    query_forms = [(query_model, False)]
    if stripped_query and stripped_query != query_model:
        query_forms.append((stripped_query, True))
    own_forms = [(value, False) for value in own_values]
    own_forms += [(base, True) for base in dict.fromkeys(
        without_variant_suffix(value) for value in own_values)
        if base and base not in own_values]
    for own_form, own_is_base in own_forms:
        own_runs = runs(own_form)
        for query_form, query_is_base in query_forms:
            request_runs = runs(query_form)
            if differs_by_family_letter(request_runs, own_runs) or \
                    differs_by_family_letter(own_runs, request_runs):
                return ("variant" if (own_is_base or query_is_base)
                        else "exact"), FAMILY_LETTER_NOTE
    request_runs = runs(query_model)
    for value in own_values:
        own_runs = runs(value)
        if len(own_runs) > len(request_runs) and own_runs[:len(request_runs)] == request_runs:
            return "prefix", None
    return None, None


def match_confidence(query: str, model: dict, *, provider_id: str | None = None,
                     model_id: str | None = None):
    """The confidence bucket alone, for callers that do not need the note."""
    return name_match(query, model, provider_id=provider_id, model_id=model_id)[0]


def similarity_score(query: str, model: dict) -> float:
    _, query_model = strip_vendor(query)
    best = 0.0
    for value in (model.get("id"), model.get("name")):
        own = strip_vendor(value)[1]
        if not own:
            continue
        left, right = set(query_model.split("-")), set(own.split("-"))
        jaccard = len(left & right) / len(left | right) if left | right else 0.0
        ratio = difflib.SequenceMatcher(None, query_model, own).ratio()
        best = max(best, jaccard, 0.6 * ratio)
    return round(best, 3)


def find_matches(catalog: Catalog, query: str, *, needs: dict, input_share: float,
                 include_deprecated: bool, exclude_flat: bool) -> dict:
    hint, _ = strip_vendor(query)
    rows, hidden = [], {"deprecated": 0, "plan_included": 0}
    for provider_id, model_id, provider, model in catalog.entries():
        confidence, note = name_match(query, model, provider_id=provider_id, model_id=model_id)
        if confidence is None:
            continue
        status = model.get("status")
        if isinstance(status, str) and status.lower() in HIDDEN_STATUSES and not include_deprecated:
            hidden["deprecated"] += 1
            continue
        row = candidate_row(provider_id, model_id, provider, model, confidence=confidence,
                            input_share=input_share, needs=needs)
        if row["plan_included"] and exclude_flat:
            hidden["plan_included"] += 1
            continue
        row["match_note"] = note
        row["provider_hint_match"] = bool(hint) and carries_vendor_hint(
            hint, provider_id, model_id, model)
        rows.append(row)

    # A stable pre-pass breaks price ties toward the newer and larger-window route
    # instead of an alphabetical provider name; the catalog iteration is itself
    # provider/model sorted, so the final order stays deterministic.
    rows.sort(key=lambda row: (str(row["release_date"] or ""), row["context_limit"] or 0),
              reverse=True)
    rows.sort(key=lambda row: (
        0 if (row["rankable"] and row["auto_selectable"]) else
        (1 if row["rankable"] else 2),
        CONFIDENCE_ORDER.get(row["confidence"], 9),
        1 if row["plan_included"] else 0,
        0 if row["provider_hint_match"] else 1,
        row["effective_price_per_mtok"] if row["effective_price_per_mtok"] is not None
        else float("inf")))

    excluded = {"price_unknown": 0, "price_incomplete": 0, "needs_failed": 0,
                "needs_confirmation": 0}
    for row in rows:
        if not row["passes_needs"]:
            excluded["needs_failed"] += 1
        if row["pricing_kind"] in PRICE_EXCLUSION_KEYS:
            excluded[PRICE_EXCLUSION_KEYS[row["pricing_kind"]]] += 1
        if not row["auto_selectable"]:
            excluded["needs_confirmation"] += 1
    return {"rows": rows, "hidden": hidden, "excluded": excluded}


def nearest_candidates(catalog: Catalog, query: str, rows: list[dict]) -> list[dict]:
    """What a human should look at when nothing can be resolved automatically."""
    if rows:
        scored = [{
            "provider": row["provider"], "model_id": row["model_id"], "name": row["name"],
            "score": 1.0, "effective_price_per_mtok": row["effective_price_per_mtok"],
            "pricing_kind": row["pricing_kind"], "vendor_hint_match": True,
            "reason": "; ".join(row["needs_failures"] or [row["pricing_note"] or ""])
            or ("name-prefix match: a different model, needs a human decision"
                if not row["auto_selectable"] else "matched but not rankable"),
        } for row in rows]
    else:
        scored = []
        hint, _ = strip_vendor(query)
        for provider_id, model_id, _provider, model in catalog.entries():
            score = similarity_score(query, model)
            if score <= 0:
                continue
            other_vendor = bool(hint) and not carries_vendor_hint(
                hint, provider_id, model_id, model)
            scored.append({
                "provider": provider_id, "model_id": model_id, "name": model.get("name"),
                "score": score, "effective_price_per_mtok": None,
                "pricing_kind": price_view(model)["pricing_kind"],
                "vendor_hint_match": not other_vendor,
                "reason": ("nearest name in the live catalog, but it belongs to a different "
                           "vendor than the request asked for; it is NOT the requested model"
                           if other_vendor else
                           "nearest name in the live catalog; it is NOT the requested model"),
            })
    scored.sort(key=lambda item: (-item["score"], item["provider"], item["model_id"]))
    return scored[:5]


# ----------------------------------------------------------------- resolve


def resolve_command(catalog: Catalog, query: str, *, needs: dict, input_share: float,
                    include_deprecated: bool, exclude_flat: bool, limit: int) -> dict:
    found = find_matches(catalog, query, needs=needs, input_share=input_share,
                         include_deprecated=include_deprecated, exclude_flat=exclude_flat)
    rows = found["rows"]
    ranked = [row for row in rows if row["rankable"] and row["auto_selectable"]]
    unconfirmed = [row for row in rows if row["rankable"] and not row["auto_selectable"]]
    payload = {
        "ok": bool(ranked),
        "command": "resolve",
        "query": query,
        "requested_model": strip_vendor(query)[1],
        "input_share": input_share,
        "needs": needs["spec"] or None,
        "min_context": needs["min_context"],
        "resolved": rows[0] if ranked else None,
        "alternatives": rows[1:limit],
        "matches": rows[:limit],
        "needs_human_confirmation": unconfirmed[:limit],
        "excluded": {**found["hidden"], **found["excluded"],
                     "not_rankable": sum(1 for row in rows if not row["rankable"])},
        "nearest": [] if ranked else nearest_candidates(catalog, query, rows),
        "catalog": catalog.meta(),
        "stale": catalog.stale,
    }
    flat = [row for row in rows if row["plan_included"]]
    if ranked and flat:
        payload["flat_route_note"] = (
            f"{len(flat)} flat subscription route(s) match {query!r}; they are listed after the "
            "metered ones because their catalog marginal cost is 0 USD/Mtok while the "
            "subscription itself is not priced here"
            + ("; the chosen route is one of them" if ranked[0]["plan_included"] else ""))
    if unconfirmed:
        payload["confirmation_note"] = (
            f"{len(unconfirmed)} priced route(s) match {query!r} only as a name prefix "
            "(for example a request for glm-5.3 matching glm-5.3-flash); that is a different "
            "model, so it is listed under needs_human_confirmation and never auto-selected")
    if not ranked:
        payload["resolved"] = None
        hint = strip_vendor(query)[0]
        payload["error"] = (
            f"{len(rows)} catalog routes match {query!r} but none is an exact or variant name "
            "match that is priceable and passes the capability gate; see 'excluded', 'matches' "
            "and 'needs_human_confirmation'" if rows else
            f"no catalog entry matches {query!r}"
            + (f"; the vendor hint {hint!r} in the request is a hard requirement, so a route "
               "of another vendor is not offered as a match" if hint else "")
            + "; silent substitution of a different model is forbidden, so the nearest "
              "candidates are listed for a human decision")
    return payload


# ----------------------------------------------------------------- suggest


def reason_for(row: dict, tier: str, median, fast_ratio: float, frontier_ratio: float,
               markers) -> str:
    price = row["effective_price_per_mtok"]
    parts = []
    if tier == "fast":
        marker = sorted(set(tokenize(row["model_id"])) & set(markers)) or \
            sorted({token for token in tokenize(row["family"])} & set(markers))
        parts.append(f"flash-class route ({'/'.join(marker) or 'marker'})")
        if median:
            parts.append(f"blended ${price}/Mtok = {round_money(price / median)}x the catalog "
                         f"frontier median ${round_price(median)}/Mtok, at or below "
                         f"{fast_ratio}x")
    else:
        parts.append("not flash-class by name")
        if median:
            parts.append(f"blended ${price}/Mtok >= {frontier_ratio}x the catalog frontier "
                         f"median ${round_price(median)}/Mtok")
        if row["capabilities"]["reasoning"] is True:
            parts.append("declares reasoning")
    if row["context_limit"]:
        parts.append(f"context {int(row['context_limit'])}")
    if row["plan_included"]:
        parts.append("plan-included flat route: marginal cost only")
    return "; ".join(part for part in parts if part)


def suggest_command(catalog: Catalog, tier: str, *, needs: dict, input_share: float,
                    fast_markers: list[str], fast_ratio: float, frontier_ratio: float,
                    require_reasoning: bool, include_deprecated: bool, exclude_flat: bool,
                    limit: int) -> dict:
    rows = []
    counts = {"deprecated": 0, "price_unknown": 0, "price_incomplete": 0, "needs_failed": 0,
              "plan_included": 0}
    for provider_id, model_id, provider, model in catalog.entries():
        status = model.get("status")
        if isinstance(status, str) and status.lower() in HIDDEN_STATUSES and not include_deprecated:
            counts["deprecated"] += 1
            continue
        row = candidate_row(provider_id, model_id, provider, model, confidence="catalog",
                            input_share=input_share, needs=needs, markers=fast_markers)
        if row["pricing_kind"] in PRICE_EXCLUSION_KEYS:
            counts[PRICE_EXCLUSION_KEYS[row["pricing_kind"]]] += 1
            continue
        if row["plan_included"] and exclude_flat:
            counts["plan_included"] += 1
            continue
        if not row["passes_needs"]:
            counts["needs_failed"] += 1
            continue
        rows.append(row)

    band = sorted(row["effective_price_per_mtok"] for row in rows
                  if not row["flash_class"] and row["effective_price_per_mtok"] is not None)
    median = statistics.median(band) if band else None

    if tier == "fast":
        picked = [row for row in rows if row["flash_class"] and (
            median is None or row["effective_price_per_mtok"] <= median * fast_ratio)]
    else:
        picked = [row for row in rows if not row["flash_class"] and (
            median is None or row["effective_price_per_mtok"] >= median * frontier_ratio)
            and (not require_reasoning or row["capabilities"]["reasoning"] is True)]
    # Same tie-break as resolve: newest and biggest window wins an equal price.
    picked.sort(key=lambda row: (str(row["release_date"] or ""), row["context_limit"] or 0),
                reverse=True)
    picked.sort(key=lambda row: (row["plan_included"], row["effective_price_per_mtok"] is None,
                                 row["effective_price_per_mtok"]))
    for row in picked:
        row["tier"] = tier
        row["reason"] = reason_for(row, tier, median, fast_ratio, frontier_ratio, fast_markers)

    payload = {
        "ok": bool(picked),
        "command": "suggest",
        "tier": tier,
        "needs": needs["spec"] or None,
        "min_context": needs["min_context"],
        "input_share": input_share,
        "policy": {
            "inference": "name markers plus the catalog's own price median; no model name list",
            "fast_markers": list(fast_markers),
            "fast_ratio": fast_ratio,
            "frontier_ratio": frontier_ratio,
            "require_reasoning": require_reasoning,
            "median_effective_price_per_mtok": round_price(median) if median is not None else None,
            "frontier_band_size": len(band),
            "gate_size": len(rows),
        },
        "candidates": [slim_candidate(row) for row in picked[:limit]],
        "candidates_total": len(picked),
        "excluded": {**counts,
                     "flash_class_count": sum(1 for row in rows if row["flash_class"]),
                     "non_flash_count": sum(1 for row in rows if not row["flash_class"])},
        "catalog": catalog.meta(),
        "stale": catalog.stale,
    }
    if not picked:
        payload["error"] = (
            f"no current, priced catalog entry passes the gate for tier {tier!r} (needs: "
            f"{needs['spec'] or 'none'}); that is a blocker to report, not a licence to pick "
            "a different model")
    return payload


def slim_candidate(row: dict) -> dict:
    keep = ("provider", "provider_name", "model_id", "name", "tier", "reason", "confidence",
            "effective_price_per_mtok", "input_price_per_mtok", "output_price_per_mtok",
            "cache_read_price_per_mtok", "pricing_kind", "plan_included", "pricing_note",
            "context_limit", "output_limit", "capabilities", "family", "status",
            "has_tiered_pricing", "flash_class")
    return {key: row[key] for key in keep if key in row}


# ------------------------------------------------------------------- cost


def blend_usd(tokens, price_per_mtok):
    if price_per_mtok is None:
        return None
    return round_money(tokens * price_per_mtok / 1_000_000)


# --------------------------------------------------- measured token burn (TPM)


MEASURED_TPM_FILE_NAME = "tpm-measured.json"
MEASURED_TPM_ENV = "LHC_TPM_MEASURED_FILE"

# The shape of the measured table is data, not code:
#   {"tiers": {"fast": {"tokens_per_minute": <rate>,
#                        "samples": [<rate>, ...],
#                        "note": "what was measured, where and with which gaps"}}}
# A class the table does not carry falls back to PROVISIONAL_TPM and is labelled
# `provisional`, so a plan can never present an unmeasured rate as a fact.
#
# The table is the ONLY place a measured rate lives: it is pinned next to the
# catalog snapshot the plan was priced with, and it is replaced by a newer
# measurement, never by an edit of this file. A rate that is not in the table
# does not exist here either - the constants below are the last resort of a
# class nobody measured, and every number derived from them says so.
#
# The rate of a class is read from the table: the pinned `tokens_per_minute`
# when the measurement wrote one down, and otherwise the median of the
# recorded samples - a measurement produces a distribution, and a
# distribution has a median. The sample count is the real one, so a class
# measured once is visibly measured once.



def measured_tpm_path(cache_dir: Path | str | None = None) -> Path:
    """Where the measured token-burn table lives; never a new global path."""
    override = os.environ.get(MEASURED_TPM_ENV)
    if override:
        return Path(override)
    base = Path(cache_dir) if cache_dir is not None else default_cache_dir()
    return base / MEASURED_TPM_FILE_NAME


def _measured_entry(entry: dict, *, source: str, measured_at: str) -> dict | None:
    """One class of a measured table: the rate and where it came from.

    The rate is the one the measurement wrote down; a table that carries only
    samples gets the median of them, because a measurement produces a
    distribution and a distribution has a median. The sample count is the real
    one, so a class measured once is visibly measured once.
    """

    if not isinstance(entry, dict):
        return None
    raw_samples = entry.get("samples")
    samples: list[float] = []
    counted = 0
    if isinstance(raw_samples, list):
        counted = len(raw_samples)
        for value in raw_samples:
            number = numeric(value)
            if number is not None and number > 0:
                samples.append(number)
    rate = numeric(entry.get("tokens_per_minute"))
    if rate is None and samples:
        rate = statistics.median(samples)
    if rate is None or rate <= 0:
        return None
    return {
        "tokens_per_minute": int(round(rate)),
        "samples": len(samples) or counted or 1,
        "note": str(entry.get("note") or ""),
        "measured_at": measured_at,
        "source": source,
    }


def load_measured_tpm(path: Path | str | None = None) -> dict:
    """The measured table, or ``{}`` when nothing was measured.

    A broken or missing table is not an error: the caller loses its `measured`
    label and goes back to the provisional constants, and the plan says so.
    The table is data and lives outside this file, so a newer measurement
    replaces it without a code change.
    """
    target = Path(path) if path is not None else measured_tpm_path()
    try:
        document = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(document, dict):
        return {}
    tiers = document.get("tiers")
    if not isinstance(tiers, dict):
        return {}
    table: dict[str, dict] = {}
    measured_at = str(document.get("measured_at") or "")
    source = str(document.get("source") or target)
    for tier, entry in tiers.items():
        key = normalize(tier)
        if key not in ("fast", "frontier"):
            continue
        built = _measured_entry(entry, source=source, measured_at=measured_at)
        if built:
            table[key] = built
    return table


def tpm_for_tier(tier: str | None, *, measured: dict | None = None,
                 cache_dir: Path | str | None = None,
                 measured_path: Path | str | None = None) -> dict:
    """The tokens-per-minute behind a leaf of this class, with its source label."""
    key = normalize(tier) or "unknown"
    table = measured if measured is not None else load_measured_tpm(measured_path)
    entry = table.get(key)
    if entry:
        return {
            "tokens_per_minute": entry["tokens_per_minute"],
            "label": "measured",
            "samples": entry["samples"],
            "note": entry["note"],
            "source": entry["source"],
            "measured_at": entry["measured_at"],
        }
    return {
        "tokens_per_minute": PROVISIONAL_TPM.get(key, PROVISIONAL_TPM["unknown"]),
        "label": "provisional",
        "samples": 0,
        "note": PROVISIONAL_NOTE,
        "source": "PROVISIONAL_TPM in lhc_models.py",
        "measured_at": "",
    }


def leaf_estimate(catalog: Catalog, *, model: str | None = None, tier: str | None = None,
                  minutes: float | None = None, tokens: int | None = None,
                  input_share: float = DEFAULT_INPUT_SHARE, needs: str = "",
                  min_context: int | None = DEFAULT_MIN_CONTEXT,
                  measured: dict | None = None,
                  include_deprecated: bool = False,
                  exclude_flat: bool = False) -> dict:
    """What one leaf of the plan costs: model, tokens, dollars, and their labels.

    This is the answer the plan kernel calls, and it is the only place where the
    three meet. The model comes from the resolver alone: a leaf that names its
    model gets that alias resolved as written (never a ``Vendor/model`` string
    assembled here, because an explicit vendor hint is a hard requirement), and
    a leaf that names only its class gets the cheapest current route the class
    policy picks. When neither resolves, there is no number: the caller prints
    «модель не выбрана» instead of a zero that reads like a cheap leaf.
    """
    gate = parse_needs(needs, min_context=min_context)
    chosen = None
    how = ""
    class_candidates = None
    class_median = None
    class_band = None
    if model:
        found = resolve_command(catalog, model, needs=gate, input_share=input_share,
                                include_deprecated=include_deprecated,
                                exclude_flat=exclude_flat, limit=20)
        chosen = found.get("resolved")
        how = "declared-model"
        if not chosen:
            return {"ok": False, "reason_code": "model_not_resolved", "query": model,
                    "error": found.get("error"), "nearest": found.get("nearest"),
                    "catalog": catalog.meta()}
    if chosen is None and tier:
        key = normalize(tier)
        if key not in ("fast", "frontier"):
            return {"ok": False, "reason_code": "class_unknown", "query": tier,
                    "error": f"tier {tier!r} is not one of fast/frontier; no model is "
                             "inferred from an unknown class"}
        picked = suggest_command(catalog, key, needs=gate, input_share=input_share,
                                 fast_markers=FAST_NAME_MARKERS, fast_ratio=0.5,
                                 frontier_ratio=1.0, require_reasoning=True,
                                 include_deprecated=include_deprecated,
                                 exclude_flat=exclude_flat, limit=1)
        candidates = picked.get("candidates") or []
        chosen = candidates[0] if picked.get("ok") and candidates else None
        how = "tier-suggested"
        # The class statistics come from the whole gate, never from a truncated
        # candidate window: `candidates_total` says how many routes passed and
        # `policy` carries the catalog's own median. A 20-row window is not the
        # catalog, and a price range read from it would be a made-up bound.
        class_policy = picked.get("policy") or {}
        class_candidates = picked.get("candidates_total")
        class_median = class_policy.get("median_effective_price_per_mtok")
        class_band = class_policy.get("frontier_band_size")
        if not chosen:
            return {"ok": False, "reason_code": "class_not_resolved", "query": key,
                    "error": picked.get("error"), "catalog": catalog.meta()}
    if chosen is None:
        return {"ok": False, "reason_code": "no_model_declared",
                "error": "the leaf names neither a model nor a model class"}

    price = chosen.get("effective_price_per_mtok")
    if price is None:
        return {"ok": False, "reason_code": "price_unknown", "query": chosen.get("model_id"),
                "error": chosen.get("pricing_note") or "the catalog carries no price",
                "catalog": catalog.meta()}

    rate = tpm_for_tier(chosen.get("tier") or tier, measured=measured)
    tokens_source = "leaf-declared"
    if tokens is None:
        if minutes is None:
            return {"ok": False, "reason_code": "no_duration",
                    "query": chosen.get("model_id"),
                    "error": "the leaf has neither an estimate in minutes nor a token count"}
        tokens = int(round(float(minutes) * rate["tokens_per_minute"]))
        tokens_source = "minutes-x-tpm"
    return {
        "ok": True,
        "model_query": model or chosen.get("model_id"),
        "selection": how,
        "provider": chosen.get("provider"),
        "provider_name": chosen.get("provider_name"),
        "model_id": chosen.get("model_id"),
        "name": chosen.get("name"),
        "tier": chosen.get("tier") or normalize(tier) or "unknown",
        "confidence": chosen.get("confidence"),
        "match_note": chosen.get("match_note"),
        "pricing_kind": chosen.get("pricing_kind"),
        "plan_included": chosen.get("plan_included"),
        "price_per_mtok": price,
        "input_share": input_share,
        "tokens": int(tokens),
        "tokens_source": tokens_source,
        "tokens_per_minute": rate["tokens_per_minute"],
        "tpm_label": rate["label"],
        "tpm_samples": rate["samples"],
        "tpm_note": rate["note"],
        "tpm_source": rate["source"],
        "minutes": minutes,
        "usd": blend_usd(tokens, price),
        "class_candidates": class_candidates,
        "class_median_price_per_mtok": class_median,
        "class_band_size": class_band,
        "catalog": catalog.meta(),
    }


def cost_command(catalog: Catalog, model_string: str, minutes: float, *, tpm=None, tier="unknown",
                 needs: dict, input_share: float, include_deprecated: bool,
                 exclude_flat: bool) -> dict:
    payload = resolve_command(catalog, model_string, needs=needs, input_share=input_share,
                              include_deprecated=include_deprecated, exclude_flat=exclude_flat,
                              limit=20)
    chosen = payload.get("resolved")
    if not chosen:
        payload["command"] = "cost"
        payload["model"] = model_string
        return payload

    prices = [row["effective_price_per_mtok"] for row in payload["matches"]
              if row["rankable"] and row["effective_price_per_mtok"] is not None]
    basis = "explicit-tpm" if tpm is not None else "provisional-tpm"
    used_tpm = tpm if tpm is not None else PROVISIONAL_TPM.get(tier, PROVISIONAL_TPM["unknown"])
    tokens = minutes * used_tpm
    # An explicit tokens-per-minute figure is the caller's assumption, so the only
    # spread left is the catalog's own price range. A provisional figure is an
    # assumption we made, so its 0.5x..2x band belongs in the reported range.
    low_factor = 1.0 if tpm is not None else 0.5
    high_factor = 1.0 if tpm is not None else 2.0
    payload.update({
        "ok": True,
        "command": "cost",
        "model": model_string,
        "minutes": minutes,
        "tokens_per_minute": used_tpm,
        "tokens_total": round(tokens),
        "input_share": input_share,
        "tier": chosen["tier"] if chosen["tier"] in ("fast", "frontier") else tier,
        "pricing_kind": chosen["pricing_kind"],
        "basis": basis,
        "blended_price_per_mtok": chosen["effective_price_per_mtok"],
        "usd": blend_usd(tokens, chosen["effective_price_per_mtok"]),
        "usd_range": [blend_usd(tokens * low_factor, min(prices)) if prices else None,
                      blend_usd(tokens * high_factor, max(prices)) if prices else None],
        "usd_range_kind": ("provisional_tpm_band_x0.5_x2_and_route_price_spread"
                           if tpm is None else "cheapest..most_expensive_ranked_route_for_the_same_model"),
        "tokens_per_minute_band": None if tpm is not None else [round(used_tpm * 0.5),
                                                                round(used_tpm * 2.0)],
    })
    if basis == "provisional-tpm":
        payload["provisional_note"] = PROVISIONAL_NOTE
    if chosen["plan_included"]:
        payload["flat_plan_note"] = FLAT_PLAN_NOTE
    return payload


# ----------------------------------------------------------------- snapshot


class Recorder:
    """The catalog subset a run actually looked at, so a plan can pin its prices."""

    def __init__(self):
        self.entries: dict[tuple[str, str], dict] = {}
        self.queries: list[dict] = []

    def remember(self, catalog: Catalog, rows) -> None:
        lookup = {(provider_id, model_id): model
                  for provider_id, model_id, _provider, model in catalog.entries()}
        for row in rows or []:
            model = lookup.get((row["provider"], row["model_id"]))
            if model is not None:
                self.entries[(row["provider"], row["model_id"])] = slim_entry(
                    row["provider"], row["model_id"], model)

    def add_query(self, **fields) -> None:
        self.queries.append({key: value for key, value in fields.items() if value is not None})

    def snapshot(self, catalog: Catalog) -> dict:
        return {
            "snapshot_version": 1,
            "catalog": catalog.meta(),
            "stale": catalog.stale,
            "queries": self.queries,
            "entries": [self.entries[key] for key in sorted(self.entries)],
        }


def slim_entry(provider_id: str, model_id: str, model: dict) -> dict:
    entry = {"provider": provider_id, "model_id": model_id,
             "cost": model.get("cost"), "limit": model.get("limit")}
    for key in ("name", "family", "status", "tool_call", "reasoning", "structured_output",
                "temperature", "open_weights", "attachment", "modalities", "release_date",
                "last_updated", "canonical_model_id", "pricing_source"):
        if key in model:
            entry[key] = model[key]
    return entry


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def snapshot_command(catalog: Catalog, recorder: Recorder, out: str, *, models, tier, needs,
                     input_share, fast_markers, fast_ratio, frontier_ratio, require_reasoning,
                     include_deprecated, exclude_flat, limit) -> dict:
    for model_string in models:
        payload = resolve_command(catalog, model_string, needs=needs, input_share=input_share,
                                  include_deprecated=include_deprecated,
                                  exclude_flat=exclude_flat, limit=limit)
        recorder.remember(catalog, payload.get("matches"))
        recorder.add_query(command="resolve", query=model_string)
    if tier is not None:
        payload = suggest_command(catalog, tier, needs=needs, input_share=input_share,
                                  fast_markers=fast_markers, fast_ratio=fast_ratio,
                                  frontier_ratio=frontier_ratio,
                                  require_reasoning=require_reasoning,
                                  include_deprecated=include_deprecated,
                                  exclude_flat=exclude_flat, limit=limit)
        recorder.remember(catalog, payload.get("candidates"))
        recorder.add_query(command="suggest", tier=tier, needs=needs["spec"] or None)
    snapshot = recorder.snapshot(catalog)
    write_json(Path(out), snapshot)
    return {"ok": True, "command": "snapshot", "out": str(out),
            "entries": len(snapshot["entries"]), "queries": snapshot["queries"],
            "catalog": catalog.meta(), "stale": catalog.stale}


# ------------------------------------------------------- recording a measurement


def tpm_command(tier: str, samples: list[float], *, out: str | None = None,
                note: str = "", measured_at: str = "") -> dict:
    """Record a measured token-burn distribution into the pinned table.

    The table is data, and this is the only way to write it: a measurement
    becomes a list of samples plus a note about what was measured, and the
    rate is derived from the samples every time the table is read. Classes
    the table does not carry keep the recorded distribution that ships with
    this file, so one new measurement never erases another.
    """

    key = normalize(tier)
    if key not in ("fast", "frontier"):
        return {"ok": False, "command": "tpm", "error": f"class {tier!r} is not fast/frontier"}
    if not samples:
        return {"ok": False, "command": "tpm", "error": "no samples given"}
    target = Path(out) if out else measured_tpm_path()
    document: dict = {}
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            document = loaded
    except (OSError, json.JSONDecodeError):
        document = {}
    tiers = document.get("tiers")
    if not isinstance(tiers, dict):
        tiers = {}
    entry = tiers.get(key)
    if not isinstance(entry, dict):
        entry = {}
    entry = dict(entry)
    entry["samples"] = [int(round(value)) for value in samples]
    entry["note"] = note or str(entry.get("note") or "")
    tiers[key] = entry
    document["tiers"] = tiers
    document.setdefault("measured_at", measured_at or time.strftime("%Y-%m-%d"))
    document.setdefault("source", str(target))
    write_json(target, document)
    built = _measured_entry(entry, source=str(document.get("source") or target),
                            measured_at=str(document.get("measured_at") or ""))
    return {
        "ok": True,
        "command": "tpm",
        "class": key,
        "out": str(target),
        "samples": entry["samples"],
        "tokens_per_minute": (built or {}).get("tokens_per_minute"),
        "label": "measured",
    }


# --------------------------------------------------------------------- parser


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lhc_models.py", description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--cache-dir", default=str(default_cache_dir()),
                        help="where the raw catalog is cached (default: repo .tmp/lhc_models)")
    parser.add_argument("--url", default=CATALOG_URL, help="catalog URL")
    parser.add_argument("--max-age", type=int, default=DEFAULT_TTL_SECONDS,
                        help="cache TTL in seconds (default 86400 = 24 h)")
    parser.add_argument("--offline", action="store_true",
                        help="never fetch; use the cache and fail if there is none")
    parser.add_argument("--refresh", action="store_true", help="ignore a fresh cache and refetch")
    parser.add_argument("--catalog", help="price against this api.json file instead of fetching")
    parser.add_argument("--now", type=float, default=None,
                        help="override the clock (epoch seconds) for tests and replays")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--input-share", type=float, default=DEFAULT_INPUT_SHARE,
                        help=f"input share of a leaf's tokens (default {DEFAULT_INPUT_SHARE})")
    common.add_argument("--needs", default="",
                        help="capability gate: tool_call,reasoning,vision,structured_output,"
                             "open_weights,attachment,audio_input,context:<n>,output:<n>")
    common.add_argument("--min-context", type=int, default=DEFAULT_MIN_CONTEXT,
                        help=f"implicit context window floor (default {DEFAULT_MIN_CONTEXT}; "
                             "0 disables it)")
    common.add_argument("--exclude-flat-routes", action="store_true",
                        help="drop 0/0 subscription routes instead of listing them labelled")
    common.add_argument("--include-deprecated", action="store_true",
                        help="keep catalog entries the catalog marks deprecated")
    common.add_argument("--limit", type=int, default=20, help="max listed candidates")
    common.add_argument("--snapshot-out", help="also pin the used catalog subset to this file")
    common.add_argument("--fast-markers", default=",".join(FAST_NAME_MARKERS),
                        help="comma list of name tokens that mean flash-class")
    common.add_argument("--fast-ratio", type=float, default=0.5,
                        help="fast ceiling as a multiple of the catalog frontier median")
    common.add_argument("--frontier-ratio", type=float, default=1.0,
                        help="frontier floor as a multiple of the catalog frontier median")
    common.add_argument("--require-reasoning", dest="require_reasoning", action="store_true",
                        default=True, help="a frontier route must declare reasoning (default)")
    common.add_argument("--no-require-reasoning", dest="require_reasoning", action="store_false")

    sub = parser.add_subparsers(dest="command", required=True)

    resolve = sub.add_parser("resolve", parents=[common],
                             help="every provider route for one model string, ranked by price")
    resolve.add_argument("model", help="the model string a leaf carries, e.g. glm-5.3-flash")

    suggest = sub.add_parser("suggest", parents=[common],
                             help="cheapest current routes that pass a tier's capability gate")
    suggest.add_argument("--tier", required=True, choices=("fast", "frontier"))

    cost = sub.add_parser("cost", parents=[common], help="USD range for one leaf on one model")
    cost.add_argument("--model", dest="model_string", required=True)
    cost.add_argument("--minutes", type=float, required=True)
    cost.add_argument("--tokens-per-minute", type=int, dest="tpm",
                      help="omit to get a result marked basis=provisional-tpm")
    cost.add_argument("--tier", choices=("fast", "frontier", "unknown"), default="unknown",
                      help="which provisional TPM constant to use without --tokens-per-minute")

    snap = sub.add_parser("snapshot", parents=[common],
                          help="pin the catalog subset a plan was priced with")
    snap.add_argument("-o", "--out", required=True)
    snap.add_argument("--model", dest="models", action="append", default=[])
    snap.add_argument("--tier", choices=("fast", "frontier"))

    tpm = sub.add_parser("tpm", parents=[common],
                         help="record a measured token-burn distribution for one class")
    tpm.add_argument("--class", dest="tier", required=True, choices=("fast", "frontier"),
                     help="the model class the samples were measured on")
    tpm.add_argument("--samples", required=True,
                     help="comma separated tokens-per-minute samples of active work")
    tpm.add_argument("--note", default="", help="what was measured, where and with which gaps")
    tpm.add_argument("--measured-at", default="", help="date of the measurement (YYYY-MM-DD)")
    tpm.add_argument("--out", default=None,
                     help="the pinned table to write (default: the measured table of this repo)")
    return parser


def emit(payload: dict, *, exit_code: int) -> int:
    print(json.dumps(payload, indent=2, allow_nan=False))
    if exit_code:
        sys.stderr.write(str(payload.get("error") or "no result") + "\n")
        for item in payload.get("nearest", [])[:5]:
            sys.stderr.write(f"  nearest: {item['provider']}/{item['model_id']} "
                             f"score={item['score']} ({item['reason']})\n")
    return exit_code


def main(argv: list[str] | None = None, *, fetcher=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    recorder = Recorder()
    if args.command == "tpm":
        # Recording a measurement needs no catalog: it is a fact about the
        # work, not about the prices of the day.
        samples: list[float] = []
        for chunk in re.split(r"[,\s]+", str(args.samples or "")):
            if not chunk:
                continue
            try:
                samples.append(float(chunk))
            except ValueError:
                parser.error(f"--samples: {chunk!r} is not a number")
        payload = tpm_command(args.tier, samples, out=args.out, note=args.note,
                              measured_at=args.measured_at)
        return emit(payload, exit_code=0 if payload.get("ok") else 2)
    try:
        needs = parse_needs(args.needs, min_context=(args.min_context or None))
    except ValueError as error:
        sys.stderr.write(f"bad --needs: {error}\n")
        return emit({"ok": False, "command": args.command, "error": str(error)}, exit_code=2)
    fast_markers = [normalize(marker) for marker in re.split(r"[,\s]+", args.fast_markers) if marker]

    try:
        catalog = load_catalog(cache_dir=Path(args.cache_dir), url=args.url,
                               max_age_seconds=args.max_age, path=args.catalog,
                               offline=args.offline, refresh=args.refresh, fetcher=fetcher,
                               now=args.now)
    except CatalogUnavailable as error:
        sys.stderr.write(f"catalog unavailable: {error}\n")
        return emit({"ok": False, "command": args.command, "error": str(error),
                     "hint": "no price is invented; fetch once while online, or pass "
                             "--catalog FILE from a pinned snapshot"}, exit_code=3)

    if args.command == "resolve":
        payload = resolve_command(catalog, args.model, needs=needs, input_share=args.input_share,
                                  include_deprecated=args.include_deprecated,
                                  exclude_flat=args.exclude_flat_routes, limit=args.limit)
        recorder.remember(catalog, payload.get("matches"))
        recorder.add_query(command="resolve", query=args.model)
    elif args.command == "suggest":
        payload = suggest_command(catalog, args.tier, needs=needs, input_share=args.input_share,
                                  fast_markers=fast_markers, fast_ratio=args.fast_ratio,
                                  frontier_ratio=args.frontier_ratio,
                                  require_reasoning=args.require_reasoning,
                                  include_deprecated=args.include_deprecated,
                                  exclude_flat=args.exclude_flat_routes, limit=args.limit)
        recorder.remember(catalog, payload.get("candidates"))
        recorder.add_query(command="suggest", tier=args.tier, needs=args.needs or None)
    elif args.command == "cost":
        payload = cost_command(catalog, args.model_string, args.minutes, tpm=args.tpm,
                               tier=args.tier, needs=needs, input_share=args.input_share,
                               include_deprecated=args.include_deprecated,
                               exclude_flat=args.exclude_flat_routes)
        recorder.remember(catalog, payload.get("matches"))
        recorder.add_query(command="cost", query=args.model_string)
    else:
        if not args.models and args.tier is None:
            parser.error("snapshot needs at least one --model or a --tier")
        payload = snapshot_command(catalog, recorder, args.out, models=args.models, tier=args.tier,
                                   needs=needs, input_share=args.input_share,
                                   fast_markers=fast_markers, fast_ratio=args.fast_ratio,
                                   frontier_ratio=args.frontier_ratio,
                                   require_reasoning=args.require_reasoning,
                                   include_deprecated=args.include_deprecated,
                                   exclude_flat=args.exclude_flat_routes, limit=args.limit)
        return emit(payload, exit_code=0)

    if args.snapshot_out:
        write_json(Path(args.snapshot_out), recorder.snapshot(catalog))
        payload["snapshot_out"] = str(args.snapshot_out)
    return emit(payload, exit_code=0 if payload.get("ok") else 2)


if __name__ == "__main__":
    raise SystemExit(main())
