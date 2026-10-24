#!/usr/bin/env python3
"""Optional stateless stdio facade. Every tool invokes the public native CLI.

Preserves create_leaf/update_leaf/build_plan/estimate_cost from the initial
cost-first-plan-kernel facade; no pricing or alternate plan engine is copied.
"""
from __future__ import annotations
import json
from pathlib import Path
import subprocess
import sys

TOOLS_DIR = Path(__file__).resolve().parent


def schema(name, description, properties, required):
    return {"name": name, "description": description, "inputSchema": {
        "type": "object", "properties": properties, "required": required, "additionalProperties": False}}


TEXT = {"type": "string"}
PLAN = {"plan_dir": TEXT}
EDIT = {**PLAN, "leaf_id": TEXT, "fields": {"type": "object"}, "expected_hash": TEXT, "note": TEXT}
TOOLS = [
    schema("create_leaf", "lhc_plan_json.py create-leaf PLAN ID --fields JSON", {**PLAN, "leaf": {"type": "object"}}, ["plan_dir", "leaf"]),
    schema("update_leaf", "lhc_plan_json.py update-leaf PLAN ID --fields JSON [--expected-hash HASH]", EDIT, ["plan_dir", "leaf_id", "fields"]),
    schema("update_progress", "lhc_plan_json.py progress PLAN ID --note TEXT [--fields JSON]", EDIT, ["plan_dir", "leaf_id", "note"]),
    schema("build_plan", "lhc_plan_json.py build-plan PLAN [--report FILE --graph FILE]", {**PLAN, "report": TEXT, "graph": TEXT}, ["plan_dir"]),
    schema("publish_html", "lhc_plan_publish.py publish-html PLAN [--config FILE --autopublish]", {**PLAN, "config": TEXT, "autopublish": {"type": "boolean"}}, ["plan_dir"]),
    schema("revise_plan", "lhc_plan_publish.py revise PLAN --reason TEXT", {**PLAN, "reason": TEXT}, ["plan_dir", "reason"]),
    schema("estimate_cost", "Existing lhc_models.py cost; explicitly unavailable if not bundled", {"model": TEXT, "minutes": {"type": "number"}, "tier": TEXT, "offline": {"type": "boolean"}, "catalog": TEXT}, ["model", "minutes"]),
]


def command(name, a):
    argv = [sys.executable]
    if name == "estimate_cost":
        if not (TOOLS_DIR / "lhc_models.py").exists():
            raise ValueError("estimate_cost unavailable: lhc_models.py is not part of this package")
        argv += [str(TOOLS_DIR / "lhc_models.py")]
        if a.get("offline"):
            argv += ["--offline"]
        if a.get("catalog"):
            argv += ["--catalog", a["catalog"]]
        argv += ["cost", "--model", a["model"], "--minutes", str(a["minutes"])]
        if a.get("tier"):
            argv += ["--tier", a["tier"]]
        return argv
    plan = str(Path(a["plan_dir"]).expanduser().resolve())
    if name in {"publish_html", "revise_plan"}:
        argv += [str(TOOLS_DIR / "lhc_plan_publish.py"), "publish-html" if name == "publish_html" else "revise", plan]
        for key in ("config", "reason"):
            if a.get(key):
                argv += ["--" + key, str(a[key])]
        if a.get("autopublish"):
            argv += ["--autopublish"]
    elif name == "build_plan":
        argv += [str(TOOLS_DIR / "lhc_plan_json.py"), "build-plan", plan]
        for key in ("report", "graph"):
            if a.get(key):
                argv += ["--" + key, str(a[key])]
    else:
        fields = a["leaf"] if name == "create_leaf" else a.get("fields", {})
        identity = fields["id"] if name == "create_leaf" else a["leaf_id"]
        argv += [str(TOOLS_DIR / "lhc_plan_json.py"), {"create_leaf": "create-leaf", "update_leaf": "update-leaf", "update_progress": "progress"}[name], plan, identity, "--fields", json.dumps(fields, ensure_ascii=False)]
        for key in ("expected_hash", "note"):
            if a.get(key):
                argv += ["--" + key.replace("_", "-"), str(a[key])]
    return argv


def call(name, arguments):
    spec = next((t for t in TOOLS if t["name"] == name), None)
    if not spec or not isinstance(arguments, dict):
        raise ValueError("unknown tool or invalid arguments")
    shape = spec["inputSchema"]
    if set(arguments) - set(shape["properties"]) or set(shape["required"]) - set(arguments):
        raise ValueError("invalid tool arguments")
    argv = command(name, arguments)
    result = subprocess.run(argv, capture_output=True, text=True, timeout=60)
    return {"content": [{"type": "text", "text": result.stdout + (result.stderr if result.returncode else "")}], "isError": result.returncode != 0,
            "structuredContent": {"argv": [argv], "returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}}


def main():
    for line in sys.stdin:
        message = None
        try:
            message = json.loads(line)
            if not isinstance(message, dict):
                raise ValueError("request must be object")
            if "id" not in message:
                continue
            method = message.get("method")
            if method == "initialize":
                requested = message.get("params", {}).get("protocolVersion")
                result = {"protocolVersion": requested if requested in {"2024-11-05", "2025-03-26", "2025-06-18"} else "2024-11-05", "capabilities": {"tools": {}}, "serverInfo": {"name": "LhcPlan", "version": "1.0.0"}}
            elif method == "tools/list":
                result = {"tools": TOOLS}
            elif method == "ping":
                result = {}
            elif method == "tools/call":
                params = message.get("params", {})
                try:
                    result = call(params.get("name"), params.get("arguments", {}))
                except (ValueError, KeyError, TypeError, OSError, subprocess.SubprocessError) as error:
                    result = {"content": [{"type": "text", "text": str(error)}], "isError": True}
            else:
                print(json.dumps({"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "method not found"}}), flush=True)
                continue
            response = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        except (ValueError, TypeError) as error:
            response = {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None, "error": {"code": -32700, "message": str(error)}}
        print(json.dumps(response, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
