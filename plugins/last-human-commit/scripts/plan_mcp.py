#!/usr/bin/env python3
"""Thin MCP facade over the LHC plan CLI: create a leaf, edit a leaf, rebuild the plan, price it.

Why this exists: the plan is edited through native hooks today, and hooks are
installed only for Claude, Codex and Zcode. Qoder and Opencode are not covered,
so a person working through those harnesses could not create or edit a task leaf
or rebuild the plan at all. This server puts the same four operations on MCP.

The one rule this file lives by (PRODUCT-PHILOSOPHY.md 13): **it is a facade, not
a second planner.** Every tool runs the existing CLI with the same argument
vector a human would type, and returns that CLI's stdout, stderr and exit code
verbatim. There is no plan parsing here, no pricing, no graph building, no
second storage and no server state: the single source of truth stays
``leaves/<ID>.json``, read and written by ``lhc_plan_json.py``.

Tools and the exact command each one runs:

    create_leaf     write leaves/<ID>.json, then  lhc_plan_json.py check <plan_dir>
    update_leaf     merge into leaves/<ID>.json, then lhc_plan_json.py check <plan_dir>
    build_plan      lhc_plan_json.py build <plan_dir>
                    lhc_grid.py render <plan_dir>/plan.graph.json --out-dir <plan_dir>
                    lhc_plan_json.py check <plan_dir>
    estimate_cost   lhc_models.py [--offline] [--catalog FILE] cost
                    --model <M> --minutes <N> [--tier <T>]

The CLI is run with the interpreter this server runs on, so the two always
agree on the language the CLI is written in.

Where the CLI lives: this file ships inside the LHC package, and the package
is installed in several shapes - the repository checkout, the package root
(Claude Code, Qoder, Opencode) and the native Codex flavour, whose package
root is ``native/codex/``. The CLI is next to the facade in every one of them,
but the directory that holds it is named differently:

    <package root>/tools/                the package's own copy of the CLI
    <package root>/common/tools/         the same copy, with package paths
    <package root>/native/codex/tools/   the Codex flavour's copy
    <repository>/src/common/tools/       the canon of a checkout

So the CLI is found by walking up from this file and taking the first
directory that holds it. A checkout prefers the canon of the repository, an
installed package uses the copies it ships. No absolute path is written here:
the same file runs in the checkout and in the installed package.

Writing the leaf file is data marshalling, not plan logic: the field names come
from ``lhc_plan_json.LEAF_FIELDS`` (imported, never copied), so when the collector
gains or drops a field this facade follows it automatically, and the collector's
own ``check`` is what decides whether the leaf is acceptable. If the collector
names the leaf this facade has just written as the one it cannot collect, the
file is taken back, because a leaf the build cannot collect stops every other
leaf of the plan. A defect of another leaf is not this facade's to undo.

Transport is plain line-delimited JSON-RPC over stdio, the MCP standard-IO
shape, with no dependency on an MCP SDK: initialize, tools/list and tools/call
are the whole surface the four tools need.

Usage:
    python3 plugins/last-human-commit/scripts/plan_mcp.py   # stdio server
    echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | python3 plan_mcp.py
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
from functools import lru_cache
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


# --------------------------------------------------------------------------
# where the plan CLI is
# --------------------------------------------------------------------------

HERE = Path(__file__).resolve().parent

# The directories a package keeps the CLI in, in the order they are trusted.
TOOL_DIR_NAMES = ("tools", "common/tools", "native/codex/tools")
# The canon of a checkout: the CLI is written in src/common/tools and
# projected into the package by the publisher.
CANON_DIR = Path("src") / "common" / "tools"

# The manifest that marks a directory as a package root.
MANIFESTS = (Path(".codex-plugin") / "plugin.json", Path("plugin.json"))


def _ancestors(start: Path, limit: int = 8) -> Any:
    """`start` and its parents, nearest first, at most `limit` of them."""

    current = start
    for _ in range(limit):
        yield current
        if current.parent == current:
            return
        current = current.parent


def _package_root() -> Optional[Path]:
    """The nearest ancestor of this file that carries a plugin manifest."""

    for ancestor in _ancestors(HERE.parent):
        for manifest in MANIFESTS:
            if (ancestor / manifest).is_file():
                return ancestor
    return None


def _repo_root() -> Optional[Path]:
    """The nearest ancestor of this file that carries the canon of the CLI."""

    for ancestor in _ancestors(HERE.parent):
        if (ancestor / CANON_DIR).is_dir():
            return ancestor
    return None


def _is_repository_package(package: Optional[Path], repo: Optional[Path]) -> bool:
    """True when this package is one of the plugin packages of the repository.

    Only then is the canon of the repository the live source of the CLI. An
    installed package, or a copy of one that happens to sit inside a checkout,
    runs the copies it ships.
    """

    if package is None or repo is None:
        return False
    try:
        relative = package.relative_to(repo)
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] == "plugins"


def tool_dirs() -> list[Path]:
    """Every directory that may hold the plan CLI, the likeliest first.

    A checkout of this repository prefers the canon: the copy inside the
    package is a projection of it, and a worker editing the canon must see the
    change through this facade right away. An installed package has no canon
    and uses the copies it ships.
    """

    package = _package_root()
    repo = _repo_root()
    candidates: list[Path] = []
    if _is_repository_package(package, repo):
        candidates.append(repo / CANON_DIR)
    if package is not None:
        candidates.extend(package / name for name in TOOL_DIR_NAMES)
    for ancestor in _ancestors(HERE.parent):
        candidates.extend(ancestor / name for name in TOOL_DIR_NAMES)
    ordered: list[Path] = []
    for candidate in candidates:
        if candidate not in ordered:
            ordered.append(candidate)
    return ordered


def find_cli(name: str) -> Path:
    """The CLI of that name, wherever this package keeps it."""

    searched: list[str] = []
    for directory in tool_dirs():
        candidate = directory / name
        if candidate.is_file():
            return candidate
        searched.append(str(candidate))
    raise FileNotFoundError(
        f"{name} is not in this package; looked in: " + ", ".join(searched))


@lru_cache(maxsize=None)
def plan_json_cli() -> Path:
    """The collector: it owns the leaf schema and the check."""

    return find_cli("lhc_plan_json.py")


@lru_cache(maxsize=None)
def grid_cli() -> Path:
    """The renderer: it turns the collected graph into the page."""

    return find_cli("lhc_grid.py")


@lru_cache(maxsize=None)
def models_cli() -> Path:
    """The estimator: it owns the price of a model."""

    return find_cli("lhc_models.py")


def _load_tool(filename: str) -> Any:
    """Import one sibling CLI as a module, read-only, for its schema constants."""

    path = find_cli(filename)
    spec = importlib.util.spec_from_file_location(f"lhc_plan_mcp_{path.stem}", path)
    if spec is None or spec.loader is None:  # pragma: no cover - broken checkout
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        # A half-imported sibling must not stay in the module table.
        sys.modules.pop(spec.name, None)
        raise
    return module


# The layout the operations act on: one leaf per file. These are the fallbacks
# for the collector's own names; the collector itself is the authority.
LEAVES_DIRNAME = "leaves"
GRAPH_FILE = "plan.graph.json"

_collector: Any = None
_collector_failed = False


def collector() -> Any:
    """The plan collector, asked for its leaf schema and never copied.

    Loaded lazily and allowed to fail: this file is a facade over a CLI that
    another worker may be editing right now, and a broken sibling must not take
    the whole server down. When the collector cannot be imported, the schema
    pre-check is skipped and the collector's own ``check`` stays the only
    authority either way. A failed import is tried again, because the sibling
    may be whole again while this server runs.
    """

    global _collector, _collector_failed
    if _collector is not None:
        return _collector
    try:
        _collector = _load_tool("lhc_plan_json.py")
        _collector_failed = False
    except (Exception, SystemError) as error:  # a mid-edit CLI is the normal case here
        if not _collector_failed:
            _collector_failed = True
            print(f"lhc-plan: collector schema unavailable, deferring to `lhc_plan_json.py check`: {error}",
                  file=sys.stderr)
        return None
    return _collector


# The collector as a module: every vocabulary this facade uses - the leaf
# fields, the leaves directory, the graph file, the tiers - is read from it and
# never copied, so the collector stays the single source of truth.
plan_json = collector()

# The leaf schema of the collector, read and not copied. It is empty only when
# the collector cannot be imported at all; then the collector's own `check`
# stays the authority and the pre-check below stands down.
LEAF_FIELDS: tuple[str, ...] = (
    tuple(getattr(plan_json, "LEAF_FIELDS", ()) or ()) if plan_json is not None else ()
)

_estimator: Any = None


def estimator() -> Any:
    """The estimator CLI as a module, asked for its own vocabulary only."""

    global _estimator
    if _estimator is None:
        try:
            _estimator = _load_tool("lhc_models.py")
        except (Exception, SystemError) as error:  # a mid-edit CLI is the normal case here
            print(f"lhc-plan: estimator vocabulary unavailable, the CLI decides: {error}",
                  file=sys.stderr)
            _estimator = False
    return _estimator or None


def leaf_fields() -> Optional[tuple[str, ...]]:
    """The collector's leaf field list, or None when the collector cannot be read."""

    module = collector()
    if module is not None:
        fields = tuple(getattr(module, "LEAF_FIELDS", ()) or ())
        if fields:
            return fields
    return tuple(LEAF_FIELDS) or None


def collector_name(name: str, fallback: Any) -> Any:
    """One constant of the collector, or the fallback when it cannot be read."""

    module = collector()
    value = getattr(module, name, None) if module is not None else None
    return value if value else fallback


def estimator_tiers() -> tuple[str, ...]:
    """The tier names the estimator accepts, read from the estimator's parser.

    The estimator is the authority of its own vocabulary; the facade never keeps
    a second list of the tiers it accepts.
    """

    module = estimator()
    if module is None:
        return ()
    try:
        parser = module.build_parser()
        for action in parser._actions:
            choices = getattr(action, "choices", None)
            if isinstance(choices, dict) and "cost" in choices:
                for option in choices["cost"]._actions:
                    if option.dest == "tier":
                        return tuple(option.choices or ())
    except Exception:  # a changed parser must not take the server down
        return ()
    return ()


# --------------------------------------------------------------------------
# the single seam: one CLI call, its output returned unchanged
# --------------------------------------------------------------------------


def run_cli(argv: list[str]) -> dict[str, Any]:
    """Run one existing CLI and hand back its raw stdout, stderr and exit code.

    The CLI runs in the directory this server runs in, with the interpreter
    this server runs on: the command is the command a human would type here,
    so its answer is the answer of that human's command.
    """

    completed = subprocess.run(argv, capture_output=True, text=True, check=False)
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
    leaves = str(collector_name("LEAVES_DIRNAME", LEAVES_DIRNAME))
    return plan_dir / leaves / f"{leaf_id}.json"


def _validated_fields(fields: Any, *, where: str) -> dict[str, Any]:
    if not isinstance(fields, dict):
        raise ValueError(f"{where} must be an object of leaf fields")
    known = leaf_fields()
    if known:
        unknown = sorted(set(fields) - set(known))
        if unknown:
            raise ValueError(
                f"{where} has fields the collector schema does not know: {', '.join(unknown)}. "
                f"Allowed: {', '.join(known)}"
            )
    return dict(fields)


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    temporary = path.with_name(path.name + ".tmp-lhc-mcp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _names_leaf(stderr: str, path: Path) -> bool:
    """True when the collector's own answer names this very leaf file.

    The collector names the file it cannot collect, and the facade reads that
    name instead of deciding anything about the plan by itself.
    """

    return path.name in stderr


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
    call = run_cli([sys.executable, str(plan_json_cli()), "check", str(plan_dir)])
    if call["returncode"] != 0 and _names_leaf(call["stderr"], path):
        # A leaf the collector refuses must not stay in the plan: it would stop
        # the build of every other leaf. A defect of a *different* leaf is not
        # this facade's to undo, so the file is only taken back when the
        # collector's own answer names the file this facade has just written.
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
    return _render([run_cli([sys.executable, str(plan_json_cli()), "check", str(plan_dir)])])


def build_plan(arguments: dict[str, Any]) -> dict[str, Any]:
    """Rebuild the plan: collect the leaves, regenerate the page, validate them.

    Three calls of the existing CLI, each with the argument vector a human
    types. The collector builds the graph out of the leaves; the renderer
    regenerates ``plan.html`` and ``plan.md`` of that very graph - the page is
    regenerated by the build, which is why there is no separate render tool;
    the collector's own check validates the leaves and writes nothing, and it
    is the only one that reports a leaf over the estimate cap.
    """

    plan_dir = _plan_dir(arguments)
    graph = plan_dir / str(collector_name("GRAPH_FILE", GRAPH_FILE))
    calls = [run_cli([sys.executable, str(plan_json_cli()), "build", str(plan_dir)])]
    if calls[0]["returncode"] == 0:
        calls.append(run_cli([sys.executable, str(grid_cli()), "render", str(graph),
                              "--out-dir", str(plan_dir)]))
        calls.append(run_cli([sys.executable, str(plan_json_cli()), "check", str(plan_dir)]))
    return _render(calls)


def estimate_cost(arguments: dict[str, Any]) -> dict[str, Any]:
    """Ask the existing estimator CLI; this facade invents no price."""

    model = str(arguments.get("model") or "").strip()
    if not model:
        raise ValueError("model is required: the exact model string to price")
    minutes = arguments.get("minutes")
    if minutes is None or str(minutes).strip() == "":
        raise ValueError("minutes is required: the leaf's estimated active minutes")
    argv = [sys.executable, str(models_cli())]
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


def _tier_property() -> dict[str, Any]:
    """The tier argument of the estimator, with the tiers the estimator accepts."""

    tiers = estimator_tiers()
    prop: dict[str, Any] = {"type": "string",
                             "description": "Optional tier gate the estimator applies."}
    if tiers:
        prop["enum"] = list(tiers)
        prop["description"] = f"Optional tier gate the estimator applies: {', '.join(tiers)}."
    return prop


TOOLS: list[dict[str, Any]] = [
    {
        "name": "create_leaf",
        "description": (
            "Create one task leaf as plan_dir/leaves/<id>.json, then validate it with the plan "
            "collector (`python3 lhc_plan_json.py check <plan_dir>`) and return that CLI's "
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
            "`python3 lhc_plan_json.py check <plan_dir>`; the CLI output is returned "
            "verbatim. The usual call is {\"status\": \"done\", \"finished_at\": \"07:20\"} - the clock "
            "of the leaf is «ЧЧ:ММ», the full date-time lives in updated_at."
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
            "Rebuild the plan with the three CLI lines a human types: "
            "`python3 lhc_plan_json.py build <plan_dir>` collects the leaves into "
            "plan.graph.json; `python3 lhc_grid.py render <plan_dir>/plan.graph.json "
            "--out-dir <plan_dir>` regenerates plan.html and plan.md of that graph (the page is "
            "regenerated by the build, which is why there is no separate render tool); "
            "`python3 lhc_plan_json.py check <plan_dir>` validates the leaves and "
            "writes nothing. Every output is returned verbatim."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "plan_dir": {"type": "string", "description": "Directory holding the leaves/ folder."},
            },
            "required": ["plan_dir"],
            "additionalProperties": False,
        },
    },
    {
        "name": "estimate_cost",
        "description": (
            "Price one leaf with the existing estimator: `python3 lhc_models.py "
            "[--offline] [--catalog <file>] cost --model <model> --minutes <n> [--tier <tier>]`. The "
            "catalog answer is returned verbatim; this facade never computes or guesses a price itself."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model string to resolve in the live catalog."},
                "minutes": {"type": ["number", "string"], "description": "Estimated active minutes of the leaf."},
                "tier": _tier_property(),
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
            return {"jsonrpc": "2.0", "id": identifier,
                    "error": {"code": INVALID_PARAMS, "message": "arguments must be an object"}}
        try:
            result = operation(arguments)
        except (ValueError, OSError, json.JSONDecodeError) as error:
            return {"jsonrpc": "2.0", "id": identifier, "error": {
                "code": INVALID_PARAMS, "message": f"{type(error).__name__}: {error}"}}
        except Exception as error:  # one broken call must not take the server down
            return {"jsonrpc": "2.0", "id": identifier, "error": {
                "code": INTERNAL_ERROR, "message": f"{type(error).__name__}: {error}"}}
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
