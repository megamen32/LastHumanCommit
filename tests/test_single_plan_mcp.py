"""Consumer regressions for the single optional planning server."""
import json
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from test_lhc_plan_mcp import PLUGIN, PLAN_JSON, call_tool, read_leaf, write_catalog


def request(identifier, method, params=None):
    return {"jsonrpc": "2.0", "id": identifier, "method": method, "params": params or {}}


@pytest.mark.parametrize("flavour", ["", "native/codex"])
def test_standalone_default_entrypoint_calls_all_seven_tools(tmp_path, flavour):
    package = tmp_path / "package"
    shutil.copytree(PLUGIN / flavour, package)
    home = tmp_path / "home"
    home.mkdir()
    plan = tmp_path / "plan"
    config = tmp_path / "publish.json"
    config.write_text(json.dumps({"webroot": str(tmp_path / "web"), "base_url": "https://example.invalid"}))
    catalog = write_catalog(tmp_path / "catalog.json")
    operations = [
        ("create_leaf", {"plan_dir": str(plan), "leaf": {"id": "A", "label": "Проверка"}}),
        ("update_leaf", {"plan_dir": str(plan), "leaf_id": "A", "fields": {"note": "Изменено"}}),
        ("update_progress", {"plan_dir": str(plan), "leaf_id": "A", "note": "Проверено"}),
        ("build_plan", {"plan_dir": str(plan)}),
        ("estimate_cost", {"model": "acme-flash", "minutes": "15", "offline": True, "catalog": str(catalog)}),
        ("publish_html", {"plan_dir": str(plan), "config": str(config)}),
        ("revise_plan", {"plan_dir": str(plan), "reason": "Уточнение"}),
    ]
    messages = [request(0, "initialize"), request(1, "tools/list")]
    messages += [request(i + 2, "tools/call", {"name": name, "arguments": args})
                 for i, (name, args) in enumerate(operations)]
    env = {**os.environ, "HOME": str(home), "PYTHONPATH": ""}
    proc = subprocess.run([sys.executable, str(package / "scripts/plan_mcp.py")],
                          input="\n".join(map(json.dumps, messages)) + "\n",
                          cwd=home, env=env, text=True, capture_output=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert len(replies) == len(messages)
    assert {t["name"] for t in replies[1]["result"]["tools"]} == {n for n, _ in operations}
    for reply in replies[2:]:
        result = reply["result"]
        assert not result["isError"], result
        assert all(Path(argv[1]).is_relative_to(package) for argv in result["structuredContent"]["argv"])
    leaf = read_leaf(plan, "A")
    assert leaf["created_at"]
    assert len(leaf["progress_events"]) == 3
    assert (plan / "plan.graph.json").is_file()


def test_cli_mutations_and_default_mcp_preserve_the_same_data(tmp_path):
    via_mcp, via_cli = tmp_path / "mcp", tmp_path / "cli"
    operations = [
        ("create_leaf", "create-leaf", {"id": "A", "label": "Проверка"}, None),
        ("update_leaf", "update-leaf", {"note": "Изменено"}, None),
        ("update_progress", "progress", {}, "Проверено"),
    ]
    for tool, command, fields, note in operations:
        args = {"plan_dir": str(via_mcp)}
        args.update({"leaf": fields} if tool == "create_leaf" else {"leaf_id": "A", "fields": fields})
        if note:
            args["note"] = note
        result = call_tool(tool, args)
        assert not result["isError"], result
        argv = [sys.executable, str(PLAN_JSON), command, str(via_cli), "A", "--fields", json.dumps(fields)]
        if note:
            argv += ["--note", note]
        direct = subprocess.run(argv, capture_output=True, text=True, timeout=10)
        assert direct.returncode == 0, direct.stderr
        left, right = read_leaf(via_mcp, "A"), read_leaf(via_cli, "A")
        for leaf in (left, right):
            leaf.pop("created_at")
            leaf.pop("updated_at")
            for event in leaf["progress_events"]:
                event.pop("at")
        assert left == right


def test_stdio_recovers_after_invalid_requests_and_arguments(tmp_path):
    messages = [
        "{",
        "[]",
        json.dumps(request(1, "initialize", ["invalid"])),
        json.dumps(request(2, "tools/call", {"name": "update_leaf", "arguments": []})),
        json.dumps(request(3, "tools/call", {"name": "create_leaf", "arguments": {"plan_dir": [], "leaf": {}}})),
        json.dumps(request(4, "unknown")),
        json.dumps(request(5, "ping")),
    ]
    proc = subprocess.run([sys.executable, str(PLUGIN / "scripts/plan_mcp.py")],
                          input="\n".join(messages) + "\n", capture_output=True, text=True, timeout=10)
    replies = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [r["error"]["code"] for r in replies[:-1]] == [-32700, -32600, -32602, -32602, -32602, -32601]
    assert replies[-1] == {"jsonrpc": "2.0", "id": 5, "result": {}}


def test_failed_update_and_stale_hash_leave_original_bytes_unchanged(tmp_path):
    plan = tmp_path / "plan"
    assert not call_tool("create_leaf", {"plan_dir": str(plan), "leaf": {"id": "A", "label": "Проверка"}})["isError"]
    path = plan / "leaves/A.json"
    before = path.read_bytes()
    for fields, expected_hash in [
        ({"status": "invalid"}, hashlib.sha256(before).hexdigest()),
        ({"note": "Устаревшая запись"}, "0" * 64),
    ]:
        result = call_tool("update_leaf", {"plan_dir": str(plan), "leaf_id": "A",
                           "fields": fields, "expected_hash": expected_hash})
        assert result["isError"]
        assert path.read_bytes() == before
