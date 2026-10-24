"""Tests for the live-catalog price resolver ``lhc_models.py``.

What these cases protect, in the owner's words: a new frontier model must be
selectable next week without editing this repository. So every assertion here
runs against a fixture catalog built in the test (no network), and every rule
that would need a hand-maintained model list is asserted to be data-derived:

* resolution is by normalized id/name, never by an enumerated alias map;
* the one naming tolerance that exists - a family letter glued to a version
  number - is tested to be narrow: it joins two spellings of the same model and
  never bridges two models, and it never promotes a free SKU out of `variant`;
* a `Vendor/model` request is a hard requirement: a route that never mentions
  the requested vendor cannot come back as exact/variant/prefix;
* an unknown price is never invented — it is excluded and labelled;
* a 0/0 flat "coding plan" route is a real marginal-cost signal that must be
  labelled ``plan-included``, not silently allowed to win every comparison;
* tiers come from name markers plus the price distribution of the catalog;
* the cache honours its TTL, survives a network failure as ``stale: true``
  and fails loudly when there is neither cache nor network.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest


ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "src" / "common" / "tools" / "lhc_models.py"


def load_tool():
    spec = importlib.util.spec_from_file_location("lhc_models", TOOL)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


tool = load_tool()


# --------------------------------------------------------------------- fixture


def mk_model(
    model_id,
    name,
    *,
    input_price=None,
    output_price=None,
    cache_read=None,
    context=1_000_000,
    tool_call=True,
    reasoning=True,
    structured_output=True,
    attachment=False,
    open_weights=False,
    family=None,
    status=None,
    release_date=None,
    modalities=("text",),
):
    model = {
        "id": model_id,
        "name": name,
        "tool_call": tool_call,
        "reasoning": reasoning,
        "structured_output": structured_output,
        "attachment": attachment,
        "open_weights": open_weights,
        "temperature": True,
        "limit": {"context": context, "output": 32_000},
        "modalities": {"input": list(modalities), "output": ["text"]},
    }
    if family is not None:
        model["family"] = family
    if status is not None:
        model["status"] = status
    if release_date is not None:
        model["release_date"] = release_date
    if input_price is not None or output_price is not None:
        cost = {"input": input_price, "output": output_price}
        if cache_read is not None:
            cost["cache_read"] = cache_read
        model["cost"] = cost
    return model


def mk_provider(provider_id, **models):
    return {"id": provider_id, "name": provider_id, "models": dict(models)}


def catalog_payload():
    """A miniature models.dev catalog with every awkward case in it."""
    return {
        "boundless": mk_provider(
            "boundless",
            # Two live routes for the same fast model: cheapest wins.
            **{"glm-5.3-flash": mk_model("glm-5.3-flash", "GLM-5.3-Flash",
                                        input_price=0.12, output_price=0.4,
                                        cache_read=0.024, family="glm-flash")},
        ),
        "vivgrid": mk_provider(
            "vivgrid",
            **{"glm-5.3-flash": mk_model("glm-5.3-flash", "GLM-5.3-Flash",
                                        input_price=0.15, output_price=0.5,
                                        cache_read=0.04, family="glm-flash"),
               # The non-flash sibling: a prefix request for it must never be
               # answered with the flash model.
               "glm-5.3": mk_model("glm-5.3", "GLM-5.3",
                                   input_price=1.12, output_price=3.52,
                                   cache_read=0.14, family="glm"),
               # Dotted/dashed/space variants of the same family, as catalogs write them.
               "gpt-6-luna": mk_model("gpt-6-luna", "GPT-6 Luna",
                                      input_price=0.1, output_price=0.5,
                                      cache_read=0.01, family="gpt-luna"),
               "gpt-6.1-sol": mk_model("gpt-6.1-sol", "GPT-6.1 Sol",
                                       input_price=2.0, output_price=10.0,
                                       cache_read=0.2, family="gpt-sol")},
        ),
        "volcengine": mk_provider(
            # Same model, differently formatted id with a date tail.
            "volcengine",
            **{"glm-5-3-flash-260828": mk_model("glm-5-3-flash-260828", "GLM-5.3-Flash",
                                                input_price=0.11, output_price=0.42,
                                                family="glm-flash")},
        ),
        "minimax-coding-plan": mk_provider(
            "minimax-coding-plan",
            **{"MiniMax-M3.1-Flash": mk_model("MiniMax-M3.1-Flash",
                                              "MiniMax-M3.1-Flash",
                                              input_price=0.0, output_price=0.0,
                                              cache_read=0.0, family="minimax"),
               "MiniMax-M3.1-Flash-Preview": mk_model(
                   "MiniMax-M3.1-Flash-Preview", "MiniMax-M3.1-Flash-Preview",
                   input_price=0.0, output_price=0.0, family="minimax",
                   status="deprecated")},
        ),
        "aixy": mk_provider(
            "aixy",
            # Free route: a real 0 price, but a variant suffix lowers confidence.
            **{"gpt-6-luna-free": mk_model("gpt-6-luna-free", "GPT-6 Luna (free)",
                                           input_price=0.0, output_price=0.0,
                                           family="gpt-luna")},
        ),
        "noPriceProvider": mk_provider(
            # No cost block at all: the price is unknown, never zero.
            "noPriceProvider",
            **{"glm-5.3-flash": mk_model("glm-5.3-flash", "GLM-5.3-Flash",
                                         family="glm-flash")},
        ),
        "smallcontext": mk_provider(
            "smallcontext",
            **{"glm-5.3-flash": mk_model("glm-5.3-flash", "GLM-5.3-Flash",
                                        input_price=0.01, output_price=0.02,
                                        context=8_000, attachment=False,
                                        family="glm-flash")},
        ),
        # A model that did not exist when this file was written. Nothing here
        # is enumerated by name, so it must be selectable on its data alone.
        "newvendor": mk_provider(
            "newvendor",
            **{"brand-new-9-flash": mk_model("brand-new-9-flash", "Brand New 9 Flash",
                                            input_price=0.05, output_price=0.2,
                                            family="brand-new")},
        ),
        "premiumvendor": mk_provider(
            "premiumvendor",
            **{"brand-new-9-opus": mk_model("brand-new-9-opus", "Brand New 9 Opus",
                                            input_price=3.0, output_price=15.0,
                                            family="brand-new"),
               "quiet-worker": mk_model("quiet-worker", "Quiet Worker",
                                        input_price=1.0, output_price=4.0,
                                        reasoning=False, family="quiet")},
        ),
        # The same new model as an exact-name flat route: a 0 USD marginal price
        # must not be able to outrank the metered route of the same confidence.
        "opencode-go": mk_provider(
            "opencode-go",
            **{"brand-new-9-flash": mk_model("brand-new-9-flash", "Brand New 9 Flash",
                                             input_price=0.0, output_price=0.0,
                                             family="brand-new")},
        ),
    }


@pytest.fixture()
def catalog_file(tmp_path):
    path = tmp_path / "api.json"
    path.write_text(json.dumps(catalog_payload()), encoding="utf-8")
    return path


def letter_catalog_payload():
    """How real catalogs spell one model: the family letter is glued to the version.

    ``vendor-3.1-flash`` (what a policy writes) and ``vendor-m3.1-flash`` (what the
    catalog writes) are the same model, so resolution must not depend on the
    letter - while a foreign-vendor model with the same version digits, and a
    neighbouring model whose name differs by more than that one letter, must stay
    out of reach.
    """
    return {
        "empiriolabs": mk_provider(
            "empiriolabs",
            **{"minimax-m3-1-flash": mk_model("minimax-m3-1-flash", "MiniMax M3.1 Flash",
                                              input_price=0.2, output_price=0.6,
                                              family="minimax")},
        ),
        "gatewayx": mk_provider(
            # The vendor lives in the model id instead of the provider id.
            "gatewayx",
            **{"minimax/m3.1-flash": mk_model("minimax/m3.1-flash", "MiniMax-M3.1-Flash",
                                              input_price=0.3, output_price=1.2,
                                              family="minimax")},
        ),
        "opencode": mk_provider(
            # A free SKU of the same model: still a different SKU, so `variant`.
            "opencode",
            **{"minimax-m3.1-flash-free": mk_model("minimax-m3.1-flash-free",
                                                   "MiniMax M3.1 Flash Free",
                                                   input_price=0.0, output_price=0.0,
                                                   family="minimax")},
        ),
        "commandcode": mk_provider(
            # Another vendor's model with the same version digits and the same
            # "flash" word: the cheapest route in the file, and never an answer
            # to a MiniMax request.
            "commandcode",
            **{"inclusionai/ling-3.1-flash:free": mk_model(
                "inclusionai/ling-3.1-flash:free", "Ling-3.1 Flash (free)",
                input_price=0.02, output_price=0.06, family="ling")},
        ),
        "openrouter": mk_provider(
            # The same foreign model metered, under a gateway provider id: the
            # vendor only appears in the model id, which is where a hint may
            # legitimately be found.
            "openrouter",
            **{"inclusionai/ling-3.1-flash": mk_model("inclusionai/ling-3.1-flash",
                                                      "Ling-3.1 Flash",
                                                      input_price=0.05, output_price=0.15,
                                                      family="ling")},
        ),
        "vendorfour": mk_provider(
            "vendorfour",
            **{"gpt-4": mk_model("gpt-4", "GPT-4", input_price=1.0, output_price=3.0,
                                 family="gpt"),
               # A letter that belongs to the model's own name, not to a version:
               # it must never be treated as a spelling variant of gpt-4.
               "gpt-4o": mk_model("gpt-4o", "GPT-4o", input_price=2.5, output_price=10.0,
                                  family="gpt")},
        ),
    }


@pytest.fixture()
def letter_catalog_file(tmp_path):
    path = tmp_path / "letter-catalog.json"
    path.write_text(json.dumps(letter_catalog_payload()), encoding="utf-8")
    return path


def cli(args, capsys):
    code = tool.main([str(a) for a in args])
    captured = capsys.readouterr()
    payload = json.loads(captured.out) if captured.out.strip() else None
    return code, payload, captured


# ------------------------------------------------------------------- resolving


def test_resolve_ranks_live_routes_by_effective_price(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "resolve", "glm-5.3-flash"], capsys)
    assert code == 0
    assert payload["ok"] is True
    resolved = payload["resolved"]
    # 0.11*0.8 + 0.42*0.2 = 0.172 is the cheapest priced route in the fixture.
    assert resolved["provider"] == "volcengine"
    assert resolved["confidence"] in ("exact", "variant", "prefix")
    assert resolved["cost"]["input"] == pytest.approx(0.11)
    assert resolved["cost"]["output"] == pytest.approx(0.42)
    assert resolved["effective_price_per_mtok"] == pytest.approx(0.172, abs=1e-9)
    assert resolved["context_limit"] == 1_000_000
    assert resolved["capabilities"]["tool_call"] is True
    ranked_prices = [alt["effective_price_per_mtok"] for alt in payload["alternatives"]
                     if alt["rankable"]]
    assert ranked_prices == sorted(ranked_prices)
    assert payload["alternatives"][0]["rankable"] is True
    assert payload["resolved"]["pricing_kind"] == "per-token"


def test_resolve_reads_cache_read_price_and_catalog_provenance(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "resolve", "vivgrid/gpt-6-luna",
         "--input-share", "0.5"], capsys)
    assert code == 0
    resolved = payload["resolved"]
    # The request named a vendor that really serves this model, so the hint holds.
    assert resolved["provider"] == "vivgrid"
    assert resolved["model_id"] == "gpt-6-luna"
    assert resolved["provider_hint_match"] is True
    assert resolved["cost"]["cache_read"] == 0.01
    assert resolved["effective_price_per_mtok"] == pytest.approx(0.3)
    assert payload["catalog"]["sha256"]
    assert payload["catalog"]["retrieved_at"]
    assert payload["stale"] is False


def test_an_explicit_vendor_hint_is_a_hard_requirement_not_a_preference(catalog_file, capsys):
    # The same model name under a vendor that does not serve it: the resolver must
    # refuse, not quietly answer with another vendor's route (project law: no
    # silent substitution). The route stays visible as a labelled `nearest` line.
    code, payload, captured = cli(
        ["--catalog", catalog_file, "resolve", "openai/gpt-6-luna"], capsys)
    assert code == 2
    assert payload["ok"] is False
    assert payload["resolved"] is None
    assert payload["matches"] == []
    assert "hard requirement" in payload["error"]
    nearest = {item["model_id"]: item for item in payload["nearest"]}
    assert "gpt-6-luna" in nearest
    assert nearest["gpt-6-luna"]["vendor_hint_match"] is False
    assert "different vendor" in nearest["gpt-6-luna"]["reason"]
    assert "different vendor" in captured.err


def test_resolve_matches_by_normalized_name_not_by_alias_list(catalog_file, capsys):
    for query in ("MiniMax-M3.1-Flash", "minimax m3.1 flash", "MiniMax_M3_1_Flash",
                  "minimax/minimax-m3.1-flash"):
        code, payload, _ = cli(["--catalog", catalog_file, "resolve", query], capsys)
        assert code == 0, query
        assert payload["resolved"]["model_id"] == "MiniMax-M3.1-Flash"
        assert payload["resolved"]["confidence"] == "exact"


def test_resolve_variant_suffix_is_a_separate_lower_confidence_bucket(catalog_file, capsys):
    code, payload, _ = cli(["--catalog", catalog_file, "resolve", "gpt-6-luna"], capsys)
    assert code == 0
    by_confidence = {row["confidence"]: row for row in payload["matches"]}
    assert "exact" in by_confidence
    assert "variant" in by_confidence
    assert by_confidence["variant"]["model_id"] == "gpt-6-luna-free"
    # The free variant is cheaper but may not displace the exact match.
    assert payload["resolved"]["confidence"] == "exact"
    assert by_confidence["variant"]["effective_price_per_mtok"] < \
        by_confidence["exact"]["effective_price_per_mtok"]
    assert payload["alternatives"][0]["confidence"] == "variant"


def test_resolve_prints_the_rejection_reason_for_a_human(catalog_file, capsys):
    code, payload, captured = cli(
        ["--catalog", catalog_file, "resolve", "totally-made-up-model"], capsys)
    assert code != 0
    assert "no catalog entry matches" in captured.err
    assert "nearest" in captured.err


def test_resolve_without_match_exits_nonzero_and_shows_nearest(catalog_file, capsys):
    code, payload, captured = cli(
        ["--catalog", catalog_file, "resolve", "totally-made-up-model"], capsys)
    assert code != 0
    assert payload["ok"] is False
    assert "nearest" in payload
    scores = [c["score"] for c in payload["nearest"]]
    assert scores and scores == sorted(scores, reverse=True)
    assert payload["resolved"] is None
    assert "substitute" in captured.err.lower() or "no catalog" in captured.err.lower()


def test_unknown_price_is_never_invented(catalog_file, capsys):
    code, payload, _ = cli(["--catalog", catalog_file, "resolve", "glm-5.3-flash"], capsys)
    assert code == 0
    # The costless route exists but carries no price and cannot become the
    # chosen one, and it must not appear as a 0-price candidate.
    assert payload["resolved"]["provider"] != "noPriceProvider"
    unpriced = [alt for alt in payload["alternatives"] + [payload["resolved"]]
                if alt["provider"] == "noPriceProvider"]
    assert len(unpriced) == 1
    assert unpriced[0]["pricing_kind"] == "unknown"
    assert unpriced[0]["cost"] is None
    assert payload["excluded"]["price_unknown"] == 1


def test_flat_zero_price_route_is_labelled_not_silently_preferred(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "resolve", "MiniMax-M3.1-Flash"], capsys)
    assert code == 0
    assert payload["resolved"]["pricing_kind"] == "plan-included"
    assert payload["resolved"]["plan_included"] is True
    assert payload["resolved"]["pricing_note"]
    assert payload["resolved"]["status"] == "current"
    # The deprecated preview sibling never reaches the candidate list.
    ids = {alt["model_id"] for alt in payload["alternatives"]}
    assert "MiniMax-M3.1-Flash-Preview" not in ids
    assert payload["excluded"]["deprecated"] == 1


def test_flat_routes_can_be_excluded_by_flag(catalog_file, capsys):
    code, payload, captured = cli(
        ["--catalog", catalog_file, "resolve", "MiniMax-M3.1-Flash",
         "--exclude-flat-routes"], capsys)
    assert code != 0
    assert payload["ok"] is False
    assert payload["excluded"]["plan_included"] == 1
    # a refused request still names the closest catalog entries, with scores
    assert payload["nearest"]
    assert all(row["score"] > 0 and row["model_id"] for row in payload["nearest"])
    assert "nearest" in captured.err


def test_a_flat_route_does_not_outrank_a_metered_route_of_equal_confidence(
        catalog_file, capsys):
    # Two exact-name routes for brand-new-9-flash: $0.08/Mtok metered and a 0/0
    # plan route. The plan route is shown, labelled and placed after the
    # metered one, and the payload says why.
    code, payload, _ = cli(["--catalog", catalog_file, "resolve",
                           "brand-new-9-flash"], capsys)
    assert code == 0
    assert payload["resolved"]["provider"] == "newvendor"
    assert payload["resolved"]["pricing_kind"] == "per-token"
    flat = [row for row in payload["matches"] if row["plan_included"]]
    assert [(row["provider"], row["effective_price_per_mtok"]) for row in flat] == \
        [("opencode-go", 0.0)]
    assert "flat subscription" in payload["flat_route_note"]


def test_a_prefix_match_is_a_different_model_and_is_never_auto_selected(catalog_file, capsys):
    # Asking for glm-5.3 must not silently answer with the cheaper glm-5.3-flash
    # routes that merely start with that name.
    code, payload, _ = cli(["--catalog", catalog_file, "resolve", "glm-5.3"], capsys)
    assert code == 0
    assert payload["resolved"]["model_id"] == "glm-5.3"
    assert payload["resolved"]["confidence"] == "exact"
    assert payload["resolved"]["auto_selectable"] is True
    prefix = payload["needs_human_confirmation"]
    assert prefix and all(row["confidence"] == "prefix" for row in prefix)
    assert all(row["auto_selectable"] is False for row in prefix)
    assert any(row["model_id"] == "glm-5.3-flash" for row in prefix)
    assert "different" in payload["confirmation_note"]
    # prefix rows are priced and listed, but never promoted into the chosen route
    assert all(row["effective_price_per_mtok"] is not None for row in prefix)
    assert payload["matches"][0] == payload["resolved"]


def test_a_request_that_itself_carries_a_variant_suffix_stays_in_its_bucket(
        catalog_file, capsys):
    code, payload, _ = cli(["--catalog", catalog_file, "resolve",
                            "glm-5.3-flash-free"], capsys)
    assert code == 0
    assert payload["resolved"]["confidence"] == "variant"


def test_deprecated_routes_are_hidden_unless_asked_for(catalog_file, capsys):
    code, payload, _ = cli(["--catalog", catalog_file, "resolve",
                            "MiniMax-M3.1-Flash-Preview", "--include-deprecated"], capsys)
    assert code == 0
    assert payload["resolved"]["status"] == "deprecated"
    assert payload["resolved"]["model_id"] == "MiniMax-M3.1-Flash-Preview"
    # Without the flag the deprecated SKU is not offered at all; the request
    # falls back to the current sibling, visibly as a lower-confidence variant,
    # and the hidden route is counted rather than lost.
    code, payload, _ = cli(["--catalog", catalog_file, "resolve",
                            "MiniMax-M3.1-Flash-Preview"], capsys)
    assert code == 0
    assert payload["resolved"]["model_id"] == "MiniMax-M3.1-Flash"
    assert payload["resolved"]["confidence"] == "variant"
    assert payload["excluded"]["deprecated"] == 1
    assert "MiniMax-M3.1-Flash-Preview" not in {row["model_id"] for row in payload["matches"]}


def test_needs_gate_filters_on_context_and_vision(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "resolve", "glm-5.3-flash",
         "--needs", "context:200000,tool_call"], capsys)
    assert code == 0
    assert payload["resolved"]["context_limit"] >= 200_000
    cheap_small = [alt for alt in payload["alternatives"]
                   if alt["provider"] == "smallcontext"]
    assert cheap_small[0]["passes_needs"] is False


# ------------------------------------- name matching and its single tolerance


def test_a_family_letter_glued_to_the_version_number_is_the_same_model(
        letter_catalog_file, capsys):
    # The whole point of the resolver: an alias written without the catalog's
    # family letter must still find the model, with a real price and no human
    # intervention, because it is the same model and nothing else.
    code, payload, _ = cli(
        ["--catalog", letter_catalog_file, "resolve", "minimax-3.1-flash"], capsys)
    assert code == 0
    resolved = payload["resolved"]
    assert resolved["confidence"] == "exact"
    assert resolved["effective_price_per_mtok"] == pytest.approx(0.28)
    assert resolved["match_note"], "the naming difference must be visible, not silent"
    assert all("minimax" in (str(row["model_id"]) + str(row["name"])).lower()
               for row in payload["matches"])
    # another vendor's flash route is not a match, so nothing has to be filtered
    # out of the answer afterwards
    assert "inclusionai/ling-3.1-flash:free" not in {row["model_id"]
                                                     for row in payload["matches"]}
    assert payload["nearest"] == []
    # a free SKU of the same model stays in the lower bucket: a letter never
    # promotes it into the exact route a plan may auto-select
    buckets = {row["model_id"]: row["confidence"] for row in payload["matches"]}
    assert buckets["minimax-m3.1-flash-free"] == "variant"


def test_the_same_model_resolves_identically_whichever_way_the_version_is_spelled(
        letter_catalog_file, capsys):
    seen = set()
    for query in ("minimax-3.1-flash", "minimax-m3.1-flash", "MiniMax M3.1 Flash",
                  "MiniMax-M3.1-Flash"):
        code, payload, _ = cli(["--catalog", letter_catalog_file, "resolve", query], capsys)
        assert code == 0, query
        assert payload["resolved"]["confidence"] == "exact", query
        seen.add((payload["resolved"]["provider"],
                  payload["resolved"]["effective_price_per_mtok"]))
    assert len(seen) == 1, f"one model, one answer whatever the spelling: {seen}"


def test_a_trailing_letter_that_is_part_of_the_name_is_not_a_spelling_variant(
        letter_catalog_file, capsys):
    # gpt-4 and gpt-4o are two models: the tolerance may never bridge them, so
    # the other one is only ever reported as a prefix a human has to confirm.
    code, payload, _ = cli(["--catalog", letter_catalog_file, "resolve", "gpt-4"], capsys)
    assert code == 0
    assert payload["resolved"]["model_id"] == "gpt-4"
    assert payload["resolved"]["confidence"] == "exact"
    assert payload["resolved"]["match_note"] is None
    unconfirmed = {row["model_id"]: row["confidence"]
                   for row in payload["needs_human_confirmation"]}
    assert unconfirmed == {"gpt-4o": "prefix"}
    assert all(row["auto_selectable"] is False for row in payload["needs_human_confirmation"])
    # and the request for the lettered model never borrows the unlettered one
    code, payload, _ = cli(["--catalog", letter_catalog_file, "resolve", "gpt-4o"], capsys)
    assert code == 0
    assert payload["resolved"]["model_id"] == "gpt-4o"
    assert "gpt-4" not in {row["model_id"] for row in payload["matches"]
                           if row["confidence"] in ("exact", "variant")}


def test_a_wrong_vendor_hint_cannot_borrow_another_vendors_route(letter_catalog_file, capsys):
    # positive control: the hint is satisfied, here by the vendor part of the
    # catalog model id rather than by the provider id.
    code, payload, _ = cli(
        ["--catalog", letter_catalog_file, "resolve", "inclusionai/ling-3.1-flash"], capsys)
    assert code == 0
    assert payload["resolved"]["provider"] == "openrouter"
    assert payload["resolved"]["model_id"] == "inclusionai/ling-3.1-flash"
    assert payload["resolved"]["confidence"] == "exact"
    assert payload["resolved"]["provider_hint_match"] is True
    # negative: the model name is requested with a vendor that does not serve it,
    # so nothing resolves - exit 2 - and the foreign route appears only as a
    # nearest line that says its vendor does not match.
    code, payload, _ = cli(
        ["--catalog", letter_catalog_file, "resolve", "minimax/ling-3.1-flash"], capsys)
    assert code == 2
    assert payload["resolved"] is None
    assert payload["matches"] == []
    foreign = [row for row in payload["nearest"]
               if row["model_id"] == "inclusionai/ling-3.1-flash:free"]
    assert foreign, "the human still gets to see the closest name in the catalog"
    assert foreign[0]["vendor_hint_match"] is False
    assert "different vendor" in foreign[0]["reason"]
    # the inverse: a MiniMax model with a vendor that serves no MiniMax model
    code, payload, _ = cli(
        ["--catalog", letter_catalog_file, "resolve",
         "not-a-real-vendor/minimax-3.1-flash"], capsys)
    assert code == 2
    assert payload["matches"] == []
    assert payload["resolved"] is None
    assert all(row["vendor_hint_match"] is False for row in payload["nearest"])


def test_the_family_letter_rule_is_one_letter_and_nothing_looser():
    runs, differs = tool.runs, tool.differs_by_family_letter
    assert differs(runs("minimax-3.1-flash"), runs("minimax-m3.1-flash"))
    assert differs(runs("vendor-2.1-big"), runs("vendor-x2-1-big"))
    assert differs(runs("model-3-1-flash"), runs("model-m-3-1-flash"))
    assert not differs(runs("gpt-4"), runs("gpt-4o"))
    assert not differs(runs("gpt-4o"), runs("gpt-4"))
    assert not differs(runs("minimax-3.1-flash"), runs("minimax-m3.1-flash-lite"))
    assert not differs(runs("glm-5.3"), runs("glm-5-3-flash"))
    assert not differs(runs("model-3-1-flash"), runs("model-pro3-1-flash"))
    assert not differs(runs("kimi-2-0905"), runs("kimi-k2-0905-preview"))
    assert not differs(runs("minimax-3-1-flash"), runs("ling-3-1-flash"))


# ---------------------------------------------------------------------- tiers


def test_suggest_fast_is_derived_from_markers_and_price_distribution(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "suggest", "--tier", "fast",
         "--needs", "tool_call,reasoning,context:200000"], capsys)
    assert code == 0
    assert payload["ok"] is True
    names = [c["model_id"] for c in payload["candidates"]]
    assert "brand-new-9-flash" in names, "a model nobody listed must be selectable"
    assert "gpt-6.1-sol" not in names
    assert "brand-new-9-opus" not in names
    metered = [c["effective_price_per_mtok"] for c in payload["candidates"]
               if not c["plan_included"]]
    flats = [c["effective_price_per_mtok"] for c in payload["candidates"] if c["plan_included"]]
    assert metered == sorted(metered)
    assert flats and all(price == 0 for price in flats)
    # metered routes are ranked first, labelled plan routes follow them
    assert payload["candidates"][len(metered):][0]["plan_included"] is True
    assert all(c["reason"] for c in payload["candidates"])
    assert payload["policy"]["median_effective_price_per_mtok"] > max(metered)


def test_suggest_fast_excludes_a_cheap_non_flash_frontier_shaped_route(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "suggest", "--tier", "fast",
         "--needs", "tool_call,context:200000"], capsys)
    assert code == 0
    names = [c["model_id"] for c in payload["candidates"]]
    # 'quiet-worker' is neither flash-class nor cheap relative to the band.
    assert "quiet-worker" not in names


def test_suggest_frontier_excludes_flash_class_and_unreasoning_routes(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "suggest", "--tier", "frontier",
         "--needs", "tool_call,reasoning"], capsys)
    assert code == 0
    names = [c["model_id"] for c in payload["candidates"]]
    assert "brand-new-9-opus" in names
    assert "quiet-worker" not in names
    assert not any("flash" in n for n in names)
    assert all(c["tier"] == "frontier" for c in payload["candidates"])


def test_suggest_policy_is_overridable_and_reported(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "suggest", "--tier", "fast",
         "--fast-markers", "opus", "--fast-ratio", "40"], capsys)
    assert code == 0
    assert payload["policy"]["fast_markers"] == ["opus"]
    assert payload["policy"]["fast_ratio"] == pytest.approx(40.0)
    names = [c["model_id"] for c in payload["candidates"]]
    assert names == ["brand-new-9-opus"]


def test_suggest_without_any_passing_route_is_a_blocker_not_an_empty_pass(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "suggest", "--tier", "fast",
         "--needs", "context:9000000"], capsys)
    assert code != 0
    assert payload["ok"] is False
    assert payload["candidates"] == []


# ----------------------------------------------------------------------- cost


def test_cost_with_explicit_tpm_reports_a_range(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "cost", "--model", "glm-5.3-flash",
         "--minutes", "15", "--tokens-per-minute", "2000"], capsys)
    assert code == 0
    assert payload["ok"] is True
    assert payload["tokens_total"] == 30_000
    assert payload["basis"] == "explicit-tpm"
    blend = 0.172
    assert payload["usd"] == pytest.approx(blend * 30_000 / 1e6, abs=1e-4)
    low, high = payload["usd_range"]
    assert low <= payload["usd"] <= high
    assert high > low, "a single number without a spread is fake precision"
    # no more than two significant digits are printed
    assert len(str(payload["usd"]).lstrip("0.").split("e")[0].lstrip("0")) <= 2


def test_cost_without_tpm_is_marked_provisional(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "cost", "--model", "gpt-6.1-sol",
         "--minutes", "15", "--tier", "frontier"], capsys)
    assert code == 0
    assert payload["basis"] == "provisional-tpm"
    assert payload["tokens_per_minute"] == tool.PROVISIONAL_TPM["frontier"]
    assert payload["provisional_note"]


def test_cost_of_a_flat_route_says_the_subscription_is_not_modeled(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "cost", "--model", "MiniMax-M3.1-Flash",
         "--minutes", "10", "--tokens-per-minute", "1000"], capsys)
    assert code == 0
    assert payload["pricing_kind"] == "plan-included"
    assert payload["usd"] == 0
    assert payload["flat_plan_note"]


def test_cost_for_unknown_model_fails(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "cost", "--model", "no-such-thing",
         "--minutes", "5"], capsys)
    assert code != 0
    assert payload["ok"] is False


def test_provisional_tpm_widens_the_reported_range(catalog_file, capsys):
    code, payload, _ = cli(
        ["--catalog", catalog_file, "cost", "--model", "gpt-6.1-sol",
         "--minutes", "10", "--tier", "frontier"], capsys)
    assert code == 0
    low, high = payload["usd_range"]
    assert low < payload["usd"] < high, "an assumed rate must show its own uncertainty"
    assert payload["tokens_per_minute_band"] == [600, 2400]
    assert payload["usd_range_kind"].startswith("provisional_tpm_band")


def test_equal_prices_break_toward_the_newer_route_not_alphabetically(tmp_path, capsys):
    tie = {
        "aaa-oldvendor": mk_provider(
            "aaa-oldvendor",
            **{"tie-model": mk_model("tie-model", "Tie Model", input_price=1.0,
                                     output_price=2.0, release_date="2024-01-01")},
        ),
        "zzz-newvendor": mk_provider(
            "zzz-newvendor",
            **{"tie-model": mk_model("tie-model", "Tie Model", input_price=1.0,
                                     output_price=2.0, release_date="2027-06-01")},
        ),
    }
    path = tmp_path / "tie.json"
    path.write_text(json.dumps(tie), encoding="utf-8")
    code, payload, _ = cli(["--catalog", path, "resolve", "tie-model"], capsys)
    assert code == 0
    assert payload["resolved"]["provider"] == "zzz-newvendor"
    assert payload["resolved"]["release_date"] == "2027-06-01"


# ---------------------------------------------------------------------- cache


def test_cache_is_reused_inside_ttl_and_refetched_outside(tmp_path):
    cache = tmp_path / "cache"
    payload = json.dumps(catalog_payload()).encode()
    calls = []

    def fetcher(url):
        calls.append(url)
        return payload

    first = tool.load_catalog(cache_dir=cache, fetcher=fetcher, now=1_000.0)
    assert first.stale is False and first.source == "network"
    assert len(calls) == 1
    second = tool.load_catalog(cache_dir=cache, fetcher=fetcher, now=1_000.0)
    assert len(calls) == 1, "a fresh cache must not be refetched"
    assert second.sha256 == first.sha256
    third = tool.load_catalog(cache_dir=cache, fetcher=fetcher,
                              now=1_000.0 + tool.DEFAULT_TTL_SECONDS + 1)
    assert len(calls) == 2, "an expired cache must be refetched"
    assert third.source == "network"


def test_tighter_max_age_forces_a_refetch_even_for_a_fresh_cache(tmp_path):
    cache = tmp_path / "cache"
    payload = json.dumps(catalog_payload()).encode()
    calls = []

    def fetcher(url):
        calls.append(url)
        return payload

    tool.load_catalog(cache_dir=cache, fetcher=fetcher, now=1_000.0)
    assert len(calls) == 1
    tool.load_catalog(cache_dir=cache, fetcher=fetcher, now=1_000.0 + 120,
                      max_age_seconds=60)
    assert len(calls) == 2, "--max-age tighter than the cache age must refetch"


def test_network_failure_falls_back_to_cache_and_is_marked_stale(tmp_path):
    cache = tmp_path / "cache"
    payload = json.dumps(catalog_payload()).encode()
    tool.load_catalog(cache_dir=cache, fetcher=lambda url: payload, now=1_000.0)

    def broken(url):
        raise OSError("network down")

    stale = tool.load_catalog(cache_dir=cache, fetcher=broken,
                              now=1_000.0 + tool.DEFAULT_TTL_SECONDS * 2)
    assert stale.stale is True
    assert stale.source == "cache"
    assert stale.providers["boundless"]["models"]["glm-5.3-flash"]["cost"]["input"] == 0.12


def test_no_cache_and_no_network_is_a_hard_failure(tmp_path):
    def broken(url):
        raise OSError("network down")

    with pytest.raises(tool.CatalogUnavailable):
        tool.load_catalog(cache_dir=tmp_path / "absent", fetcher=broken, now=1_000.0)


def test_offline_without_a_cache_never_touches_the_network(tmp_path):
    calls = []

    def fetcher(url):
        calls.append(url)
        raise AssertionError("offline must not fetch")

    with pytest.raises(tool.CatalogUnavailable):
        tool.load_catalog(cache_dir=tmp_path / "absent", offline=True, fetcher=fetcher)
    assert calls == []


def test_cli_reports_stale_catalog_from_cache(tmp_path, capsys):
    cache = tmp_path / "cache"
    payload = json.dumps(catalog_payload()).encode()
    tool.load_catalog(cache_dir=cache, fetcher=lambda url: payload, now=1_000.0)

    code = tool.main(["--cache-dir", str(cache), "--now", str(
        1_000.0 + tool.DEFAULT_TTL_SECONDS * 2), "resolve", "glm-5.3-flash"],
        fetcher=broken_fetcher())
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["stale"] is True
    assert payload["resolved"]["provider"] == "volcengine"


def broken_fetcher():
    def fetch(url):
        raise OSError("network down")

    return fetch


def test_cli_without_cache_or_network_fails_loudly(tmp_path, capsys):
    code = tool.main(["--cache-dir", str(tmp_path / "absent"), "resolve",
                      "glm-5.3-flash"], fetcher=broken_fetcher())
    assert code != 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["ok"] is False
    assert "cache" in captured.err.lower() or "network" in captured.err.lower()


# ------------------------------------------------------------------- snapshot


def test_snapshot_writes_only_referenced_entries_with_provenance(catalog_file, tmp_path, capsys):
    out = tmp_path / "prices.json"
    code, _, _ = cli(["--catalog", catalog_file, "snapshot", "-o", out,
                      "--model", "glm-5.3-flash", "--model", "gpt-6.1-sol"], capsys)
    assert code == 0
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert snap["catalog"]["sha256"]
    assert snap["catalog"]["retrieved_at"]
    assert snap["catalog"]["ttl_seconds"] == tool.DEFAULT_TTL_SECONDS
    keys = {(e["provider"], e["model_id"]) for e in snap["entries"]}
    assert ("volcengine", "glm-5-3-flash-260828") in keys
    assert ("vivgrid", "gpt-6.1-sol") in keys
    assert ("newvendor", "brand-new-9-flash") not in keys
    assert all("cost" in e and "limit" in e for e in snap["entries"])


def test_snapshot_records_a_suggest_query(catalog_file, tmp_path, capsys):
    out = tmp_path / "prices.json"
    code, _, _ = cli(["--catalog", catalog_file, "snapshot", "-o", out,
                      "--tier", "fast", "--needs", "tool_call"], capsys)
    assert code == 0
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert snap["queries"] == [{"command": "suggest", "tier": "fast",
                               "needs": "tool_call"}]
    assert {e["provider"] for e in snap["entries"]}


def test_any_query_can_pin_its_own_snapshot(catalog_file, tmp_path, capsys):
    out = tmp_path / "prices.json"
    code, _, _ = cli(["--catalog", catalog_file, "resolve", "glm-5.3-flash",
                      "--snapshot-out", out], capsys)
    assert code == 0
    snap = json.loads(out.read_text(encoding="utf-8"))
    assert snap["queries"] == [{"command": "resolve", "query": "glm-5.3-flash"}]
