# LHC:COVERS src/common/tools/lhc_model_list.py src/common/tools/lhc_plan_mcp.py
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
plan_mcp = _load("lhc_plan_mcp")
CONFIG = {
    "classes": {"fast": "routine", "middle": "code by plan", "frontier": "hard"},
    "models": [
        {"id": "a-flash", "class": "fast", "description": "cheap"},
        {"id": "b-big", "class": "frontier", "description": "strong"},
    ],
}


def test_all_classes_grouped_with_descriptions():
    out = ml.list_models(CONFIG, None)
    assert out["ok"] is True
    assert [c["class"] for c in out["classes"]] == ["fast", "middle", "frontier"]
    fast = out["classes"][0]
    assert fast["description"] == "routine"
    assert fast["models"] == [{"id": "a-flash", "description": "cheap"}]


def test_empty_middle_says_which_class_to_use_instead():
    middle = ml.list_models(CONFIG, "middle")["classes"][0]
    assert middle["models"] == []
    assert "use fast" in middle["note"] and "frontier only after a measured fast failure" in middle["note"]


def test_one_class_filters():
    out = ml.list_models(CONFIG, "frontier")
    assert [c["class"] for c in out["classes"]] == ["frontier"]
    assert "note" not in out["classes"][0]


def test_unknown_class_is_refused_with_allowed_values():
    out = ml.list_models(CONFIG, "huge")
    assert out["ok"] is False
    assert "fast" in out["error"] and "middle" in out["error"] and "frontier" in out["error"]


def test_shipped_config_lists_the_five_models():
    out = ml.list_models(ml.load_config(), None)
    ids = {m["id"]: c["class"] for c in out["classes"] for m in c["models"]}
    assert ids == {"glm-5.3-flash": "fast", "minimax-3.1-flash": "fast", "gpt-6-luna": "frontier",
                   "glm-5.3": "frontier", "gpt-6.1-sol": "frontier"}


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
    payload = json.loads(result["content"][0]["text"])
    assert payload["classes"][0]["class"] == "fast"
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
