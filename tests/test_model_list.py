# LHC:COVERS src/common/tools/lhc_model_list.py src/common/tools/lhc_coding_benchmark.py src/common/tools/lhc_plan_mcp.py
"""list_models: the three classes and the models available now, offline."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src" / "common" / "tools"
sys.path.insert(0, str(TOOLS))


def _load(name):
    spec = importlib.util.spec_from_file_location(name + "_t", TOOLS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ml = _load("lhc_model_list")
coding = _load("lhc_coding_benchmark")
plan_mcp = _load("lhc_plan_mcp")
CONFIG = {
    "classes": {"fast": "routine", "middle": "code by plan", "frontier": "hard"},
    "families": [
        {"match": "flash", "class": "fast"},
        {"match": "big", "class": "frontier"},
    ],
    "examples": {"fast": ["a-flash"], "middle": [], "frontier": ["b-big"]},
}
SNAPSHOT = {
    "harnesses": [
        {"harness": "codex", "models": ["gpt-6.1-sol", "gpt-6-luna", "glm-5.3-flash"]},
        {"harness": "opencode", "models": ["z-ai/glm-5.3", "gpt-6-luna", "upstage/solar-pro4"]},
    ],
    "quotas": [{"provider": "glm", "state": "reported", "checked_at": "t1"}],
}
BENCHMARK = {
    "metric": "swebench_pro",
    "source": "fixture",
    "frontier_anchors": [
        "openai/gpt-6-astra", "openai/gpt-6.1-sol",
        "anthropic/claude-fable-5.2", "anthropic/claude-opus-5.5",
    ],
    "frontier_families": ["fable", "opus"],
    "fast_families": ["flash", "fast", "haiku"],
    "scores": {
        "openai/gpt-6-astra": 0.90,
        "openai/gpt-6.1-sol": 0.85,
        "anthropic/claude-fable-5.2": 0.80,
        "anthropic/claude-opus-5.5": 0.75,
        "glm-5.3-flash": 0.20,
        "minimax-3.1-flash": 0.25,
        "claude-haiku-5.5": 0.30,
        "grok-4.7-fast": 0.35,
        "gpt-6-luna": 0.50,
        "glm-5.3": 0.60,
        "gpt-6.1-terra": 0.55,
    },
}


def test_tokens_split_on_non_alphanumerics():
    assert ml.tokens("openai/gpt-6.1-sol") == {"openai", "gpt", "6", "1", "sol"}
    assert ml.tokens("z-ai/glm-5.3-flash") == {"z", "ai", "glm", "5", "3", "flash"}


@pytest.mark.parametrize("model_id,cls", [
    ("claude-fable-5", "frontier"), ("claude-fable-5.2", "frontier"),
    ("anthropic/claude-fable-9", "frontier"), ("claude-opus-4.1", "frontier"),
    ("glm-5.3-flash", "fast"), ("glm-5.3", "middle"), ("z-ai/glm-5.3", "middle"),
    ("grok-4.7-fast", "fast"), ("grok-4.7", "middle"), ("openai/gpt-6.1-sol", "frontier"),
    ("upstage/solar-pro4", None), ("gpt-6-luna", None), ("mystery-model", None),
])
def test_class_of_goes_by_family(model_id, cls):
    assert ml.class_of(ml.load_config(), model_id) == cls


def test_coding_thresholds_and_dynamic_classification():
    config = ml.load_config()
    assert ml.benchmark_thresholds(config, BENCHMARK) == {
        "frontier_min": 0.75, "fast_max": 0.35,
        "frontier_anchor_scores": {
            "openai/gpt-6-astra": 0.90,
            "openai/gpt-6.1-sol": 0.85,
            "anthropic/claude-fable-5.2": 0.80,
            "anthropic/claude-opus-5.5": 0.75,
        },
        "missing_frontier_anchors": [],
    }
    assert ml.classify_model(config, "gpt-6.1-sol", BENCHMARK) == ("frontier", "frontier_anchor", 0.85)
    assert ml.classify_model(config, "gpt-6-luna", BENCHMARK) == ("middle", "coding_score_middle", 0.50)
    assert ml.classify_model(config, "glm-5.3-flash", BENCHMARK) == ("fast", "coding_score_fast", 0.20)
    assert ml.classify_model(config, "claude-fable-unknown", BENCHMARK) == ("frontier", "frontier_family", None)
    assert ml.classify_model(config, "mystery-model", BENCHMARK) == (None, "unclassified", None)


def test_compact_manifest_keeps_only_the_primary_metric():
    manifest = {
        "metric": "swebench_pro",
        "models": {
            "vendor/pro": {"source": "swebench_pro", "score": 0.4},
            "vendor/verified": {"source": "swe_bench_verified", "score": 0.99},
        },
    }
    assert coding.extract_scores(manifest) == {"vendor/pro": 0.4}


def test_coding_manifest_loader_accepts_local_supplement(tmp_path, monkeypatch):
    manifest = tmp_path / "supplement.json"
    manifest.write_text(json.dumps({
        "models": {"openai/gpt-6.1-sol": {"swebench_pro": {"score": 0.85}}}
    }))
    monkeypatch.setenv("LHC_CODING_BENCHMARK_MANIFEST", str(manifest))
    loaded = ml.load_coding_manifest({"coding_benchmark": {"metric": "swebench_pro"}})
    assert ml.benchmark_thresholds({"coding_benchmark": {"frontier_anchors": ["openai/gpt-6.1-sol"]}}, loaded)["frontier_min"] == 0.85


def test_coding_manifest_accepts_normalized_score_field():
    from lhc_coding_benchmark import extract_scores
    assert extract_scores({"metric": "swebench_pro", "scores": {
        "openai/gpt-6.1-sol": {"score": 85},
        "openai/gpt-6-astra": {"normalized_score": 0.9},
    }}) == {"openai/gpt-6.1-sol": 0.85, "openai/gpt-6-astra": 0.9}


def test_missing_manifest_keeps_only_named_frontier_anchors():
    config = ml.load_config()
    assert ml.classify_model(config, "gpt-6-astra", None)[:2] == ("frontier", "frontier_anchor")
    assert ml.classify_model(config, "gpt-6.1-sol", None)[:2] == ("frontier", "frontier_anchor")
    assert ml.classify_model(config, "claude-opus-5.5", None)[:2] == ("frontier", "frontier_family")
    assert ml.classify_model(config, "gpt-6-luna", None)[:2] == (None, "unclassified")


def test_examples_agree_with_family_rules():
    config = ml.load_config()
    for cls, ids in config["examples"].items():
        for model_id in ids:
            assert ml.class_of(config, model_id) == cls, model_id


def test_shipped_examples_are_the_owners_classes():
    assert ml.load_config()["examples"] == {
        "fast": ["glm-5.3-flash", "minimax-3.1-flash", "claude-haiku-5.5", "grok-4.7-fast"],
        "middle": ["glm-5.3", "gpt-6.1-terra", "claude-sonnet-5.5", "grok-4.7"],
        "frontier": ["gpt-6-astra", "gpt-6.1-sol", "claude-fable-5.2", "claude-opus-5.5"],
    }


def test_list_models_with_snapshot_classifies_and_reports_quotas():
    config = ml.load_config()
    out = ml.list_models(config, None, available=SNAPSHOT["harnesses"], quotas=SNAPSHOT["quotas"], benchmark=BENCHMARK)
    by = {c["class"]: c["models"] for c in out["classes"]}
    assert out["herder"] == "ok"
    luna = next(m for c in out["classes"] for m in c["models"] if m["id"] == "gpt-6-luna")
    assert luna["classification_source"] == "coding_score_middle"
    assert luna["coding_score"] == 0.50
    assert out["classification"]["frontier_min"] == 0.75
    assert out["classification"]["fast_max"] == 0.35
    assert {m["id"] for m in by["frontier"]} == {"gpt-6.1-sol"}
    assert {m["id"] for m in by["fast"]} == {"glm-5.3-flash"}
    assert {m["id"] for m in by["middle"]} == {"gpt-6-luna", "z-ai/glm-5.3"}
    assert out["unclassified"] == [{"id": "upstage/solar-pro4", "harnesses": ["opencode"]}]
    assert out["quotas"] == SNAPSHOT["quotas"]


def test_list_models_without_snapshot_uses_examples():
    out = ml.list_models(CONFIG, "fast", status="unavailable")
    assert out["herder"] == "unavailable"
    assert out["classes"][0]["models"] == [{"id": "a-flash", "source": "config"}]
    assert "unclassified" not in out


def test_all_classes_grouped_with_descriptions():
    out = ml.list_models(CONFIG, None)
    assert out["ok"] is True
    assert [c["class"] for c in out["classes"]] == ["fast", "middle", "frontier"]
    assert out["classes"][0]["description"] == "routine"


def test_empty_middle_says_which_class_to_use_instead():
    middle = ml.list_models(CONFIG, "middle")["classes"][0]
    assert middle["models"] == []
    assert "use fast" in middle["note"]


def test_unknown_class_is_refused_with_allowed_values():
    out = ml.list_models(CONFIG, "huge")
    assert out["ok"] is False and "frontier" in out["error"]


class _Boom:
    def __init__(self, **kw):
        pass

    def call(self, name, args):
        raise RuntimeError("down")


class _Fake:
    def __init__(self, **kw):
        pass

    def call(self, name, args):
        if name == "list_models":
            return {"structuredContent": None, "harnesses": [
                {"harness": "codex", "name": "Codex", "models": ["gpt-6.1-sol"]}]}
        return {"checkedAt": "t0", "providers": [
            {"provider": "glm", "state": "quota_exhausted", "checkedAt": "t1", "details": {"x": 1}}]}


def test_herder_snapshot_none_on_any_failure(monkeypatch):
    monkeypatch.delenv("LHC_HERDER", raising=False)
    assert ml.herder_snapshot(client_factory=_Boom) is None


def test_herder_snapshot_off_never_builds_a_client(monkeypatch):
    monkeypatch.setenv("LHC_HERDER", "off")

    def factory(**kw):
        raise AssertionError("must not connect")
    assert ml.herder_snapshot(client_factory=factory) is None


def test_herder_snapshot_reads_catalog_and_quotas(monkeypatch):
    monkeypatch.delenv("LHC_HERDER", raising=False)
    snap = ml.herder_snapshot(client_factory=_Fake)
    assert snap["harnesses"][0]["models"] == ["gpt-6.1-sol"]
    assert snap["quotas"] == [{"provider": "glm", "state": "quota_exhausted", "checked_at": "t1"}]


def test_herder_snapshot_malformed_is_none(monkeypatch):
    monkeypatch.delenv("LHC_HERDER", raising=False)

    class Bad(_Fake):
        def call(self, name, args):
            return {"harnesses": "nope"}
    assert ml.herder_snapshot(client_factory=Bad) is None


def test_herder_snapshot_keeps_catalog_when_quota_read_is_malformed(monkeypatch):
    monkeypatch.delenv("LHC_HERDER", raising=False)

    class CatalogOnly(_Fake):
        def call(self, name, args):
            if name == "list_models":
                return {"harnesses": [{"harness": "codex", "models": ["gpt-6-luna"]}]}
            return {"providers": "malformed"}

    snap = ml.herder_snapshot(client_factory=CatalogOnly)
    assert snap == {"harnesses": [{"harness": "codex", "models": ["gpt-6-luna"]}], "quotas": []}


def test_user_config_overrides_package(tmp_path):
    (tmp_path / "lhc").mkdir()
    (tmp_path / "lhc" / "models.json").write_text(json.dumps(CONFIG))
    assert ml.load_config(config_home=tmp_path) == CONFIG


def _call(args):
    response = plan_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                                "params": {"name": "list_models", "arguments": args}})
    assert "error" not in response, response
    return response["result"]


def test_mcp_tool_declared_and_callable():
    tools = plan_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})["result"]["tools"]
    tool = next(t for t in tools if t["name"] == "list_models")
    assert "Call it before choosing a model" in tool["description"]
    assert "class" in tool["inputSchema"]["properties"]
    result = _call({"class": "fast"})
    assert "Agent Herder" in tool["description"]
    payload = json.loads(result["content"][0]["text"])
    assert payload["classes"][0]["class"] == "fast"


def test_mcp_tool_works_fast_with_herder_unreachable(monkeypatch):
    import time
    monkeypatch.setenv("AGENT_HERDER_HTTP_URL", "http://127.0.0.1:9/mcp")
    monkeypatch.setenv("AGENT_HERDER_HTTP_TOKEN", "x")
    monkeypatch.delenv("LHC_HERDER", raising=False)
    started = time.time()
    payload = json.loads(_call({"class": "fast"})["content"][0]["text"])
    assert time.time() - started < 8
    assert payload["herder"] == "unavailable"
    assert {m["id"] for m in payload["classes"][0]["models"]} >= {"glm-5.3-flash"}


def test_leaf_accepts_model_class_middle():
    plan_json = _load("lhc_plan_json")
    assert "middle" in plan_json.TIERS


def test_cost_accepts_middle_tier():
    models = _load("lhc_models")
    parser = models.build_parser()
    args = parser.parse_args(["cost", "--model", "x", "--minutes", "5", "--tier", "middle"])
    assert args.tier == "middle"
    assert models.PROVISIONAL_TPM.get("middle", models.PROVISIONAL_TPM["unknown"])
