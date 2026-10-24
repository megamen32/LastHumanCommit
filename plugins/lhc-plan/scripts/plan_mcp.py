#!/usr/bin/env python3
"""Thin MCP facade over the LHC plan CLI: create a leaf, edit a leaf, rebuild the plan, price it.

Why this exists: the plan is edited through native hooks today, and hooks are
installed only for Claude, Codex and Zcode. Qoder and Opencode are not covered,
so a person working through those harnesses could not create or edit a task leaf
or rebuild the plan at all. This server puts the same four operations on MCP.

The one rule this file lives by (PRODUCT-PHILOSOPHY.md 13): **it is a facade, not
a second planner.** Every tool equals exactly one call of the existing CLI with
the same argument vector a human would type, and returns that CLI's stdout,
stderr and exit code verbatim. There is no plan parsing here, no pricing, no
graph building, no second storage and no server state: the single source of truth
stays ``leaves/<ID>.json``, read and written by ``lhc_plan_json.py``.

Tools and the exact command each one runs:

    create_leaf     write leaves/<ID>.json, then  lhc_plan_json.py check <plan_dir>
    update_leaf     merge into leaves/<ID>.json, then lhc_plan_json.py check <plan_dir>
    build_plan      lhc_plan_json.py build <plan_dir>
                    then lhc_grid.py check-plan <report> <graph>
    estimate_cost   lhc_models.py cost --model <M> --minutes <N> [--tier <T>]

Writing the leaf file is data marshalling, not plan logic: the field names come
from ``lhc_plan_json.LEAF_FIELDS`` (imported, never copied), so when the collector
gains or drops a field this facade follows it automatically, and the collector's
own ``check`` is what decides whether the leaf is acceptable. If the collector
rejects a freshly created leaf, the file is removed again, because a leaf the
build cannot collect stops every other leaf of the plan.

Transport is plain line-delimited JSON-RPC over stdio, the MCP standard-IO
shape, with no dependency on an MCP SDK: initialize, tools/list and tools/call
are the whole surface the four tools need.

Usage:
    python3 plugins/lhc-plan/scripts/plan_mcp.py          # stdio server
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 plan_mcp.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, Optional

SERVER_NAME = "LhcPlan"
SERVER_VERSION = "1.0.0"
DEFAULT_PROTOCOL_VERSION = "2024-11-05"
SUPPORTED_PROTOCOL_VERSIONS = ("2024-11-05", "2025-03-26", "2025-06-18")

# Error codes of JSON-RPC, used so a bad call is visible as a protocol error
# rather than as a tool that quietly returned nothing.
INVALID_REQUEST = -32600
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


def _load_tool(filename: str) -> Any:
    """Import one sibling CLI as a module, read-only, for its schema constants."""

    path = TOOLS_DIR / filename
    spec = importlib.util.spec_from_file_location(f"lhc_plan_mcp_{path.stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - broken checkout
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


REPO_ROOT = Path(__file__).resolve().parents[3]
TOOLS_DIR = REPO_ROOT / "src" / "common" / "tools"
PLAN_JSON_CLI = TOOLS_DIR / "lhc_plan_json.py"
GRID_CLI = TOOLS_DIR / "lhc_grid.py"
MODELS_CLI = TOOLS_DIR / "lhc_models.py"

# The layout the operations act on: one leaf per file. This is the address of the
# source of truth, not a second definition of it - the *content* rule below is.
LEAVES_DIRNAME = "leaves"

_collector: Any = None
_collector_failed = False


def collector() -> Any:
    """The plan collector, asked for its leaf schema and never copied.

    Loaded lazily and allowed to fail: this file is a facade over a CLI that
    another worker may be editing right now, and a broken sibling must not take
    the whole server down. When the collector cannot be imported, the schema
    pre-check is skipped and the collector's own ``check`` stays the only
    authority either way.
    """

    global _collector, _collector_failed
    if _collector is not None or _collector_failed:
        return _collector
    try:
        _collector = _load_tool("lhc_plan_json.py")
    except (Exception, SystemError) as error:  # a mid-edit CLI is the normal case here
        _collector_failed = True
        print(f"lhc-plan: collector schema unavailable, deferring to `lhc_plan_json.py check`: {error}",
              file=sys.stderr)
        return None
    return _collector


def leaf_fields() -> Optional[tuple[str, ...]]:
    """The collector's leaf field list, or None when the collector cannot be read."""

    module = collector()
    return tuple(module.LEAF_FIELDS) if module is not None else None


# --------------------------------------------------------------------------
# the single seam: one CLI call, its output returned unchanged
# --------------------------------------------------------------------------


def run_cli(argv: list[str]) -> dict[str, Any]:
    """Run one existing CLI and hand back its raw stdout, stderr and exit code."""

    completed = subprocess.run(argv, cwd=str(REPO_ROOT), capture_output=True, text=True, check=False)
    return {
        "argv": list(argv),
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "returncode": completed.returncode,
    }


def _render(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """Turn the CLI results into an MCP tool result, verbatim, nothing added."""

    stdout = "".join(call["stdout"] for call in calls)
    stderr = "".join(call["stderr"] for call in calls)
    failed = next((call for call in calls if call["returncode"] != 0), None)
    returncode = failed["returncode"] if failed else 0
    # Success is the CLI's own words only; a failure adds its stderr, because the
    # collector and the checker report the reason there.
    text = stdout + ("" if not failed else stderr)
    return {
        "content": [{"type": "text", "text": text}],
        "isError": failed is not None,
        "structuredContent": {
            "argv": [call["argv"] for call in calls],
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr,
        },
    }


# --------------------------------------------------------------------------
# the four operations
# --------------------------------------------------------------------------


def _plan_dir(arguments: dict[str, Any]) -> Path:
    raw = arguments.get("plan_dir")
    if not raw:
        raise ValueError("plan_dir is required: the directory holding leaves/<ID>.json")
    return Path(str(raw)).expanduser()


def _leaf_path(plan_dir: Path, leaf_id: str) -> Path:
    if not leaf_id or Path(leaf_id).name != leaf_id:
        raise ValueError(f"leaf id {leaf_id!r} is not a plain file name")
    return plan_dir / plan_json.LEAVES_DIRNAME / f"{leaf_id}.json"


def _validated_fields(fields: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise ValueError(f"{where} must be an object of leaf fields")
    unknown = sorted(set(fields) - set(LEAF_FIELDS))
    if unknown:
        raise ValueError(
            f"{where} has fields the collector schema does not know: {', '.join(unknown)}. "
            f"Allowed: {', '.join(LEAF_FIELDS)}"
        )
    return dict(fields)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + ".tmp-lhc-mcp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def create_leaf(arguments: dict[str, Any]) -> dict[str, Any]:
    """Write a new leaves/<ID>.json, then let the collector itself approve it."""

    plan_dir = _plan_dir(arguments)
    payload = _validated_fields(arguments.get("leaf"), where="leaf")
    leaf_id = str(payload.get("id") or "").strip()
    if not leaf_id:
        raise ValueError("leaf.id is required and must match the file name")
    if payload.get("id") != leaf_id:
        raise ValueError("leaf.id must be the plain leaf id, without spaces")
    path = _leaf_path(plan_dir, leaf_id)
    if path.exists():
        raise FileExistsError(f"{path} already exists; use update_leaf to change it")
    _write(path, payload)
    call = run_cli([sys.executable, str(PLAN_JSON_CLI), "check", str(plan_dir)])
    if call["returncode"] != 0:
        # A leaf the build cannot collect stops the whole plan, so a leaf this
        # facade just created and the collector rejected is taken back out.
        path.unlink(missing_ok=True)
    return _render([call])


def update_leaf(arguments: dict[str, Any]) -> dict[str, Any]:
    """Change fields of one named leaf and of no other leaf."""

    plan_dir = _plan_dir(arguments)
    leaf_id = str(arguments.get("leaf_id") or "").strip()
    if not leaf_id:
        raise ValueError("leaf_id is required")
    fields = _validated_fields(arguments.get("fields"), where="fields")
    if not fields:
        raise ValueError("fields must name at least one leaf field to change")
    path = _leaf_path(plan_dir, leaf_id)
    if not path.is_file():
        raise FileNotFoundError(f"no leaf {path}; use create_leaf to add one")
    current = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(current, dict):
        raise ValueError(f"{path} is not a JSON object")
    merged = {**current, **fields}
    merged["id"] = leaf_id
    _write(path, merged)
    return _render([run_cli([sys.executable, str(PLAN_JSON_CLI), "check", str(plan_dir)])])


def build_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    """Rebuild plan.graph.json from the leaves, then run the plan guardian on it."""

    plan_dir = _plan_dir(arguments)
    calls = [run_cli([sys.executable, str(PLAN_JSON_CLI), "build", str(plan_dir)])]
    if calls[0]["returncode"] == 0:
        report = str(arguments.get("report") or plan_dir / "plan.md")
        graph = str(arguments.get("graph") or plan_dir / plan_json.GRAPH_FILE)
        calls.append(run_cli([sys.executable, str(GRID_CLI), "check-plan", report, graph]))
    return _render(calls)


def estimate_cost(arguments: dict[str, Any]) -> dict[str, Any]:
    """Ask the existing estimator CLI; this facade invents no price."""

    model = str(arguments.get("model") or "").strip()
    if not model:
        raise ValueError("model is required: the exact model string to price")
    minutes = arguments.get("minutes")
    if minutes is None or str(minutes).strip() == "":
        raise ValueError("minutes is required: the leaf's estimated active minutes")
    argv = [sys.executable, str(MODELS_CLI)]
    if arguments.get("offline"):
        argv.append("--offline")
    if arguments.get("catalog"):
        argv += ["--catalog", str(arguments["catalog"])]
    argv += ["cost", "--model", model, "--minutes", str(minutes).strip()]
    tier = str(arguments.get("tier") or "").strip()
    if tier:
        argv += ["--tier", tier]
    return _render([run_cli(argv)])


OPERATIONS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "create_leaf": create_leaf,
    "update_leaf": update_leaf,
    "build_plan": build_plan,
    "estimate_cost": estimate_cost,
}


# --------------------------------------------------------------------------
# tool declarations: descriptions say which CLI line each tool equals
# --------------------------------------------------------------------------

_FIELD_DOC = "Leaf fields, exactly the collector schema of lhc_plan_json.py: " + ", ".join(LEAF_FIELDS)

TOOLS: list[dict[str, Any]] = [
    {
        "name": "create_leaf",
        "description": (
            "Create one task leaf as plan_dir/leaves/<id>.json, then validate it with "
            "`python3 src/common/tools/lhc_plan_json.py check <plan_dir>` and return that CLI's "
            "output verbatim. Equal to a human writing the file and running that check."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_dir": {"type": "string", "description": "Directory holding the leaves/ folder."},
                "leaf": {
                    "type": "object",
                    "description": _FIELD_DOC,
                    "required": ["id", "label"],
                },
            },
            "required": ["plan_dir", "leaf"],
            "additionalProperties": False,
        },
    },
    {
        "name": "update_leaf",
        "description": (
            "Change fields of one existing leaf (and only of that leaf), then validate with "
            "`python3 src/common/tools/lhc_plan_json.py check <plan_dir>`; the CLI output is returned "
            "verbatim. The usual call is {\"status\": \"done\", \"finished_at\": \"07:20\"}."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_dir": {"type": "string", "description": "Directory holding the leaves/ folder."},
                "leaf_id": {"type": "string", "description": "The leaf to change, e.g. L09."},
                "fields": {"type": "object", "description": _FIELD_DOC},
            },
            "required": ["plan_dir", "leaf_id", "fields"],
            "additionalProperties": False,
        },
    },
    {
        "name": "build_plan",
        "description": (
            "Rebuild the plan: `python3 src/common/tools/lhc_plan_json.py build <plan_dir>` collecting "
            "the leaves into plan.graph.json, then `python3 src/common/tools/lhc_grid.py check-plan "
            "<report> <graph>` comparing the graph with the written report. Both outputs are returned "
            "verbatim; report and graph default to plan.md and plan.graph.json inside plan_dir."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_dir": {"type": "string", "description": "Directory holding the leaves/ folder."},
                "report": {"type": "string", "description": "Canonical plan report markdown (default <plan_dir>/plan.md)."},
                "graph": {"type": "string", "description": "Graph JSON to compare (default <plan_dir>/plan.graph.json)."},
            },
            "required": ["plan_dir"],
            "additionalProperties": False,
        },
    },
    {
        "name": "estimate_cost",
        "description": (
            "Price one leaf with the existing estimator: `python3 src/common/tools/lhc_models.py cost "
            "--model <model> --minutes <n> [--tier <fast|frontier>]`. The catalog answer is returned "
            "verbatim; this facade never computes or guesses a price itself."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model string to resolve in the live catalog."},
                "minutes": {"type": ["number", "string"], "description": "Estimated active minutes of the leaf."},
                "tier": {"type": "string", "enum": list(plan_json.TIERS),
                         "description": "Optional tier gate the estimator applies."},
                "offline": {"type": "boolean", "description": "Price from the cached catalog only."},
                "catalog": {"type": "string", "description": "Pin the catalog to this JSON file."},
            },
            "required": ["model", "minutes"],
            "additionalProperties": False,
        },
    },
]

TOOLS_BY_NAME = {tool["name"]: tool for tool in TOOLS}


# --------------------------------------------------------------------------
# JSON-RPC over stdio
# --------------------------------------------------------------------------


def handle(message: dict[str, Any]) -> Optional[dict[str, Any]]:
    """Answer one MCP message. Returns None for a notification."""

    if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
        return {"jsonrpc": "2.0", "id": message.get("id") if isinstance(message, dict) else None,
                "error": {"code": INVALID_REQUEST, "message": "expected a JSON-RPC 2.0 object"}}

    method = message.get("method")
    identifier = message.get("id")
    params = message.get("params") or {}
    is_request = identifier is not None

    if method == "initialize":
        requested = str(params.get("protocolVersion") or DEFAULT_PROTOCOL_VERSION)
        version = requested if requested in SUPPORTED_PROTOCOL_VERSIONS else DEFAULT_PROTOCOL_VERSION
        if not is_request:
            return None
        return {"jsonrpc": "2.0", "id": identifier, "result": {
            "protocolVersion": version,
            "capabilities": {"tools": {}},
            "serverInfo": {"name": SERVER_NAME, "version": SERVER_VERSION},
        }}

    if method in ("notifications/initialized", "initialized"):
        return None

    if method == "ping":
        return None if not is_request else {"jsonrpc": "2.0", "id": identifier, "result": {}}

    if method == "tools/list":
        if not is_request:
            return None
        return {"jsonrpc": "2.0", "id": identifier, "result": {"tools": TOOLS}}

    if method == "tools/call":
        if not is_request:
            return None
        name = str(params.get("name") or "")
        operation = OPERATIONS.get(name)
        if operation is None:
            return {"jsonrpc": "2.0", "id": identifier, "error": {
                "code": INVALID_PARAMS,
                "message": f"unknown tool {name!r}; this facade exposes only "
                           + ", ".join(OPERATIONS),
            }}
        arguments = params.get("arguments") or {}
        if not isinstance(arguments, dict):
            return {"jsonrpc": "2.0", "id": identifier, "error": {
                "code": INVALID_PARAMS, "message": "arguments must be an object"}}
        try:
            result = operation(arguments)
        except (ValueError, OSError, json.JSONDecodeError) as error:
            return {"jsonrpc": "2.0", "id": identifier, "error": {
                "code": INVALID_PARAMS, "message": f"{type(error).__name__}: {error}"}}
        return {"jsonrpc": "2.0", "id": identifier, "result": result}

    if not is_request:
        return None
    return {"jsonrpc": "2.0", "id": identifier, "error": {
        "code": INVALID_PARAMS, "message": f"method {method!r} is not supported"}}


def serve(stdin: Any = None, stdout: Any = None) -> int:
    """Read line-delimited JSON-RPC from stdin until it closes."""

    stdin = stdin or sys.stdin
    stdout = stdout or sys.stdout
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            message = json.loads(line)
        except json.JSONDecodeError as error:
            reply = {"jsonrpc": "2.0", "id": None,
                     "error": {"code": INVALID_REQUEST, "message": f"invalid JSON: {error}"}}
            stdout.write(json.dumps(reply) + "\n")
            stdout.flush()
            continue
        reply = handle(message)
        if reply is not None:
            stdout.write(json.dumps(reply, ensure_ascii=False) + "\n")
            stdout.flush()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--print-tools", action="store_true", help="print the tool list and exit (no server)")
    args = parser.parse_args(sys.argv[1:] if argv is None else argv)
    if args.print_tools:
        print(json.dumps({"tools": TOOLS}, ensure_ascii=False, indent=2))
        return 0
    return serve()


if __name__ == "__main__":
    raise SystemExit(main())
