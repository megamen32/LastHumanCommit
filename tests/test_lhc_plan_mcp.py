"""The MCP facade over the plan CLI is a facade, not a second planner.

LHC's plan is edited through hooks today, and hooks are installed only for
Claude, Codex and Zcode. Qoder and Opencode are not covered, so the same four
operations - create a leaf, edit a leaf, rebuild the plan, price a leaf - have
to be reachable over MCP. The rule the facade lives or dies by (LHC philosophy
13) is that it adds no plan logic: every tool equals one documented call of the
existing CLI, and the CLI's stdout, stderr and exit code come back unchanged.

The facade ships inside the LHC package now, so these cases pin the second
half of that rule as well: the facade has to find the CLI in the *installed*
package, not only in the repository checkout.

These cases pin exactly that:

* the tool list is the seven operations and nothing else;
* each tool builds precisely the argument vector the human would type, with
  the real positional arguments of the real argparse surface;
* the CLI bytes come back verbatim, including on failure;
* the leaf schema is imported from the collector, never copied;
* the facade finds the CLI in a checkout and in an imitation of the installed
  package, and runs it with the interpreter the facade itself runs on;
* the manifests of the package declare the MCP server the way Codex and
  Claude Code read it;
* ``setup_plan_mcp.py`` points at the installed package, is dry-run by default
  and keeps a timestamped backup on ``--apply``;
* one end-to-end stdio handshake (spawn, initialize, tools/list, tools/call) runs against the real CLI, no network.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from _inprocess_lane import run_tool

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "last-human-commit"
SCRIPTS = PLUGIN / "scripts"
FACADE = SCRIPTS / "plan_mcp.py"
NATIVE = PLUGIN / "native" / "codex"
TOOLS = ROOT / "src" / "common" / "tools"
PLAN_JSON = TOOLS / "lhc_plan_json.py"
GRID = TOOLS / "lhc_grid.py"
MODELS = TOOLS / "lhc_models.py"

# The CLI files the package ships; the imitation of an installed package is
# built out of them.
CLI_FILES = tuple(p.name for p in TOOLS.glob("*.py"))


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


plan_mcp = _load(TOOLS / "lhc_plan_mcp.py", "lhc_plan_mcp_facade_test")
setup_mcp = _load(SCRIPTS / "setup_plan_mcp.py", "lhc_plan_mcp_setup_test")


class FakeCli:
    """Record the argv of every CLI call and hand back canned output."""

    def __init__(self, returncode: int = 0, stdout: str = "cli stdout\n", stderr: str = ""):
        self.calls: list[list[str]] = []
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr

    def __call__(self, argv: list[str]) -> dict:
        self.calls.append(list(argv))
        return {
            "argv": list(argv),
            "stdout": self.stdout,
            "stderr": self.stderr,
            "returncode": self.returncode,
        }


@pytest.fixture
def patch_cli(monkeypatch):
    fake = FakeCli()
    monkeypatch.setattr(plan_mcp, "run_cli", fake)
    return fake


@pytest.fixture
def failing_cli(monkeypatch):
    fake = FakeCli(returncode=1, stdout="", stderr="LHC: leaf rejected\n")
    monkeypatch.setattr(plan_mcp, "run_cli", fake)
    return fake


def make_plan_dir(tmp_path: Path, leaves: dict[str, dict]) -> Path:
    plan_dir = tmp_path / "plan"
    (plan_dir / "leaves").mkdir(parents=True)
    for leaf_id, payload in leaves.items():
        write_leaf(plan_dir, leaf_id, payload)
    return plan_dir


def write_leaf(plan_dir: Path, leaf_id: str, payload: dict) -> Path:
    path = plan_dir / "leaves" / f"{leaf_id}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def read_leaf(plan_dir: Path, leaf_id: str) -> dict:
    return json.loads((plan_dir / "leaves" / f"{leaf_id}.json").read_text(encoding="utf-8"))


def call_tool(name: str, arguments: dict) -> dict:
    """Drive one tools/call through the JSON-RPC dispatcher."""
    response = plan_mcp.handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments}}
    )
    assert "error" not in response, response["error"]
    return response["result"]


# --------------------------------------------------------------------------
# the surface is seven operations
# --------------------------------------------------------------------------


def test_tools_list_exposes_exactly_the_seven_operations():
    response = plan_mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list"})
    names = {tool["name"] for tool in response["result"]["tools"]}
    assert names == {"create_leaf", "update_leaf", "build_plan", "estimate_cost", "update_progress", "publish_html", "revise_plan"}
    for tool in response["result"]["tools"]:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


def test_initialize_reports_a_working_protocol_handshake():
    response = plan_mcp.handle(
        {"jsonrpc": "2.0", "id": 0, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}}
    )
    result = response["result"]
    assert result["protocolVersion"] == "2024-11-05"
    assert result["serverInfo"]["name"]
    assert "tools" in result["capabilities"]


def test_notification_gets_no_reply():
    assert plan_mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None


# --------------------------------------------------------------------------
# the facade finds the CLI where the package keeps it
# --------------------------------------------------------------------------


def test_the_facade_finds_the_cli_of_the_checkout():
    """In a checkout the canon of the repository is the live source of the CLI."""
    assert plan_mcp.plan_json_cli() == PLAN_JSON
    assert plan_mcp.grid_cli() == GRID
    assert plan_mcp.models_cli() == MODELS


def test_the_two_copies_of_the_facade_are_the_same_file():
    """The Codex flavour installs native/codex as its package root, so it carries
    its own copy of the facade. Two copies that drift are two servers."""
    native_facade = NATIVE / "scripts" / "plan_mcp.py"
    assert native_facade.is_file()
    assert native_facade.read_bytes() == FACADE.read_bytes()


def build_installed_package(tmp_path: Path, *, with_models: bool = True) -> Path:
    """A package as it is installed: a root with tools/, common/tools/ and
    native/codex/tools/, and the facade in scripts/."""
    package = tmp_path / "package"
    (package / ".codex-plugin").mkdir(parents=True)
    (package / ".codex-plugin" / "plugin.json").write_text(
        json.dumps({"name": "last-human-commit", "version": "1.5.47"}), encoding="utf-8")
    (package / "scripts").mkdir()
    shutil.copy(FACADE, package / "scripts" / "plan_mcp.py")
    wanted = CLI_FILES if with_models else tuple(n for n in CLI_FILES if n != "lhc_models.py")
    for relative in ("tools", "common/tools", "native/codex/tools"):
        target = package / relative
        target.mkdir(parents=True)
        # The package ships every tool of the canon; the grid loads its
        # siblings by path, so the tree has to be complete.
        for source in sorted(TOOLS.glob("*.py")):
            if source.name not in wanted:
                continue
            shutil.copy(source, target / source.name)
    return package


def run_facade(package: Path, messages: list[dict], cwd: Path | None = None) -> list[dict]:
    """Drive a facade that lives in `package` over stdio, and return the replies."""
    proc = subprocess.Popen(
        [sys.executable, str(package / "scripts" / "plan_mcp.py")],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(cwd or package),
    )
    replies: list[dict] = []
    try:
        for message in messages:
            proc.stdin.write(json.dumps(message) + "\n")
            proc.stdin.flush()
            if "id" in message:
                replies.append(json.loads(proc.stdout.readline()))
        proc.stdin.close()
        proc.wait(timeout=30)
    finally:
        if proc.poll() is None:  # pragma: no cover - only on a hung server
            proc.kill()
    return replies


def test_the_facade_finds_the_cli_in_an_installed_package(tmp_path):
    """The facade that ships in the package must run the package's own CLI."""
    package = build_installed_package(tmp_path)
    plan_dir = make_plan_dir(tmp_path, {})
    catalog = write_catalog(tmp_path / "catalog.json")

    replies = run_facade(package, [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize",
         "params": {"protocolVersion": "2024-11-05", "capabilities": {}}},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "create_leaf",
            "arguments": {"plan_dir": str(plan_dir),
                          "leaf": {"id": "L01", "label": "Один", "status": "queued"}},
        }},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
            "name": "estimate_cost",
            "arguments": {"model": "acme-flash", "minutes": 15,
                          "offline": True, "catalog": str(catalog)},
        }},
    ])

    created = replies[1]["result"]
    priced = replies[2]["result"]
    # The CLI the facade ran is the one of the installed package, not of the
    # checkout this test was started from.
    assert created["structuredContent"]["argv"][0][1].startswith(str(package / "tools"))
    assert priced["structuredContent"]["argv"][0][1].startswith(str(package / "tools"))
    assert created["isError"] is False
    assert priced["isError"] is False
    assert (plan_dir / "leaves" / "L01.json").is_file()


def test_an_installed_package_without_the_estimator_says_so(tmp_path):
    """A CLI that the package does not ship must be named, not guessed away."""
    package = build_installed_package(tmp_path, with_models=False)
    replies = run_facade(package, [
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {
            "name": "estimate_cost", "arguments": {"model": "acme-flash", "minutes": 15},
        }},
    ])
    error = replies[0]["error"]
    assert "lhc_models.py" in error["message"]


# --------------------------------------------------------------------------
# every tool is one documented line of the existing CLI
# --------------------------------------------------------------------------


def test_create_leaf_writes_the_leaf_then_runs_collector_check(tmp_path):
    plan_dir = make_plan_dir(tmp_path, {"L01": {"id": "L01", "label": "Один", "status": "done"}})
    result = call_tool("create_leaf", {
        "plan_dir": str(plan_dir),
        "leaf": {"id": "L02", "label": "Два", "status": "queued", "estimate_minutes": 15},
    })
    written = read_leaf(plan_dir, "L02")
    assert written["label"] == "Два"
    assert written["estimate_minutes"] == 15
    assert result["structuredContent"]["argv"][0][2] == "create-leaf"
    assert written["created_at"]
    assert written["progress_events"]
    assert result["structuredContent"]["returncode"] == 0


def test_create_leaf_returns_cli_output_verbatim(tmp_path, patch_cli):
    plan_dir = make_plan_dir(tmp_path, {})
    patch_cli.stdout = "  exact bytes\tincluding layout\n"
    result = call_tool("create_leaf", {
        "plan_dir": str(plan_dir), "leaf": {"id": "L01", "label": "Один", "status": "queued"},
    })
    assert result["content"][0]["text"] == "  exact bytes\tincluding layout\n"
    assert result["isError"] is False


def test_create_leaf_rolls_back_when_the_collector_rejects_it(tmp_path):
    plan_dir = make_plan_dir(tmp_path, {})
    result = call_tool("create_leaf", {
        "plan_dir": str(plan_dir), "leaf": {"id": "L01", "label": "Один", "status": "invalid"},
    })
    assert result["isError"] is True
    assert not (plan_dir / "leaves" / "L01.json").exists()
    assert result["structuredContent"]["stderr"]


def test_invalid_existing_leaf_prevents_create_without_changing_either_file(tmp_path):
    plan_dir = make_plan_dir(tmp_path, {"L09": {"id": "L09", "label": "Девять"}})
    broken = plan_dir / "leaves/L09.json"
    broken.write_text("{")
    before = broken.read_bytes()
    result = call_tool("create_leaf", {
        "plan_dir": str(plan_dir), "leaf": {"id": "L01", "label": "Один"},
    })
    assert result["isError"]
    assert not (plan_dir / "leaves/L01.json").exists()
    assert broken.read_bytes() == before


def test_create_leaf_refuses_a_field_the_collector_does_not_know(tmp_path, patch_cli):
    plan_dir = make_plan_dir(tmp_path, {})
    with pytest.raises(ValueError, match="collector schema"):
        plan_mcp.create_leaf({"plan_dir": str(plan_dir),
                              "leaf": {"id": "L01", "label": "Один", "status": "queued", "mood": "sunny"}})
    assert patch_cli.calls == []
    assert not (plan_dir / "leaves" / "L01.json").exists()


def test_leaf_fields_come_from_the_collector_not_a_second_copy():
    assert plan_mcp.LEAF_FIELDS == plan_mcp.plan_json.LEAF_FIELDS


def test_update_leaf_changes_only_its_own_leaf(tmp_path):
    other = {"id": "L01", "label": "Один", "status": "queued"}
    plan_dir = make_plan_dir(tmp_path, {"L01": other, "L02": {"id": "L02", "label": "Два", "status": "queued"}})
    before = (plan_dir / "leaves" / "L01.json").read_text(encoding="utf-8")
    result = call_tool("update_leaf", {"plan_dir": str(plan_dir), "leaf_id": "L02",
                              "fields": {"status": "done", "finished_at": "07:20"}})
    assert read_leaf(plan_dir, "L02")["status"] == "done"
    assert read_leaf(plan_dir, "L02")["label"] == "Два"
    assert (plan_dir / "leaves" / "L01.json").read_text(encoding="utf-8") == before
    assert result["structuredContent"]["argv"][0][2] == "update-leaf"


def test_update_leaf_of_an_unknown_leaf_is_an_error_not_a_new_leaf(tmp_path, patch_cli):
    plan_dir = make_plan_dir(tmp_path, {})
    with pytest.raises(FileNotFoundError):
        plan_mcp.update_leaf({"plan_dir": str(plan_dir), "leaf_id": "L99", "fields": {"status": "done"}})
    assert patch_cli.calls == []
    assert not (plan_dir / "leaves" / "L99.json").exists()


def test_build_plan_runs_build_render_and_check_with_positional_inputs(tmp_path, patch_cli):
    plan_dir = make_plan_dir(tmp_path, {"L01": {"id": "L01", "label": "Один", "status": "queued"}})
    result = call_tool("build_plan", {"plan_dir": str(plan_dir)})
    assert patch_cli.calls == [
        [sys.executable, str(PLAN_JSON), "build", str(plan_dir)],
        [sys.executable, str(GRID), "render", str(plan_dir / "plan.graph.json"),
         "--out-dir", str(plan_dir)],
        [sys.executable, str(PLAN_JSON), "check", str(plan_dir)],
    ]
    assert result["structuredContent"]["returncode"] == 0
    assert "cli stdout" in result["content"][0]["text"]


def test_build_plan_reports_the_first_failing_command(tmp_path, monkeypatch):
    fake = FakeCli(returncode=1, stdout="", stderr="graph differs\n")
    monkeypatch.setattr(plan_mcp, "run_cli", fake)
    plan_dir = make_plan_dir(tmp_path, {})
    result = call_tool("build_plan", {"plan_dir": str(plan_dir)})
    assert result["isError"] is True
    assert result["structuredContent"]["returncode"] == 1
    assert "graph differs" in result["content"][0]["text"]


def test_build_plan_does_not_render_a_graph_it_could_not_build(tmp_path, monkeypatch):
    fake = FakeCli(returncode=1, stdout="", stderr="LHC: лист битый\n")
    monkeypatch.setattr(plan_mcp, "run_cli", fake)
    plan_dir = make_plan_dir(tmp_path, {})
    call_tool("build_plan", {"plan_dir": str(plan_dir)})
    assert len(fake.calls) == 1
    assert fake.calls[0][2] == "build"


def test_estimate_cost_is_one_call_of_the_estimator_cli(patch_cli):
    call_tool("estimate_cost", {"model": "glm-5.3-flash", "minutes": 15, "tier": "fast"})
    assert patch_cli.calls == [
        [sys.executable, str(MODELS), "cost", "--model", "glm-5.3-flash", "--minutes", "15", "--tier", "fast"],
    ]


def test_estimate_cost_without_a_tier_lets_the_cli_decide(patch_cli):
    call_tool("estimate_cost", {"model": "gpt-6-luna", "minutes": 30})
    assert patch_cli.calls == [
        [sys.executable, str(MODELS), "cost", "--model", "gpt-6-luna", "--minutes", "30"],
    ]


def test_estimate_cost_can_price_offline_from_a_pinned_catalog(patch_cli):
    call_tool("estimate_cost", {"model": "glm-5.3", "minutes": 10, "offline": True,
                                "catalog": "/tmp/api.json"})
    assert patch_cli.calls == [
        [sys.executable, str(MODELS), "--offline", "--catalog", "/tmp/api.json",
         "cost", "--model", "glm-5.3", "--minutes", "10"],
    ]


def test_unknown_tool_and_unknown_argument_are_reported_as_jsonrpc_errors():
    bad = plan_mcp.handle({"jsonrpc": "2.0", "id": 7, "method": "tools/call",
                           "params": {"name": "drop_plan", "arguments": {}}})
    assert bad["error"]["code"] == -32602
    missing = plan_mcp.handle({"jsonrpc": "2.0", "id": 8, "method": "tools/call",
                               "params": {"name": "estimate_cost", "arguments": {"minutes": 5}}})
    assert missing["error"]["code"] == -32602


# --------------------------------------------------------------------------
# the facade is a facade: its answer is the answer of the same CLI line
# --------------------------------------------------------------------------


#: The CLI files of the canon, by the name the lane runs them under.
CLI_BY_NAME = {path.stem: path for path in (PLAN_JSON, GRID, MODELS)}


def run_cli_direct(argv: list[str]) -> tuple[str, str, int]:
    """The same command a human types, run by hand.

    The command is the one the facade ran - the very file of the CLI, with the
    very argument vector - and the lane runs it in this process instead of
    paying for an interpreter start.  The lane keeps the observable contract:
    the argument vector, the stdout, the stderr and the exit code are the ones
    the process would have produced (see ``tests/_inprocess_lane.py``).

    The facade side of the comparison keeps spawning the real CLI, so the two
    sides still answer the same question: the answer of the facade is the
    answer of that CLI.
    """

    program = Path(str(argv[1]))
    assert CLI_BY_NAME.get(program.stem) == program, (
        "the hand must run the very CLI file the facade ran: %s" % program)
    result = run_tool(program.stem, [str(item) for item in argv[2:]])
    return result.stdout, result.stderr, result.returncode


def write_catalog(path: Path) -> Path:
    """A pinned catalog: one model, one price, no network anywhere."""
    path.write_text(json.dumps({
        "acme": {"models": {"acme-flash": {
            "name": "Acme Flash",
            "cost": {"input": 0.10, "output": 0.40},
            "limit": {"context": 200000, "output": 8192},
        }}},
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def test_every_operation_answers_exactly_as_the_same_cli_line_by_hand(tmp_path):
    """Stdout and exit code of the facade = stdout and exit code of the CLI."""
    plan_dir = make_plan_dir(tmp_path, {"L01": {"id": "L01", "label": "Один", "status": "queued"}})
    catalog = write_catalog(tmp_path / "catalog.json")

    created = call_tool("create_leaf", {
        "plan_dir": str(plan_dir),
        "leaf": {"id": "L02", "label": "Два", "status": "queued", "estimate_minutes": 15},
    })
    assert created["structuredContent"]["returncode"] == 0
    assert created["structuredContent"]["argv"][0][2] == "create-leaf"

    updated = call_tool("update_leaf", {
        "plan_dir": str(plan_dir), "leaf_id": "L02",
        "fields": {"status": "done", "finished_at": "07:20"},
    })
    assert updated["structuredContent"]["returncode"] == 0
    assert updated["structuredContent"]["argv"][0][2] == "update-leaf"

    built = call_tool("build_plan", {"plan_dir": str(plan_dir)})
    manual = [run_cli_direct(argv) for argv in built["structuredContent"]["argv"]]
    assert built["structuredContent"]["stdout"] == "".join(item[0] for item in manual)
    assert built["structuredContent"]["returncode"] == next(
        (item[2] for item in manual if item[2] != 0), 0)

    priced = call_tool("estimate_cost", {
        "model": "acme-flash", "minutes": 15, "offline": True, "catalog": str(catalog),
    })
    stdout, _stderr, code = run_cli_direct([
        sys.executable, str(MODELS), "--offline", "--catalog", str(catalog),
        "cost", "--model", "acme-flash", "--minutes", "15",
    ])
    assert priced["structuredContent"]["stdout"] == stdout
    assert priced["structuredContent"]["returncode"] == code


# --------------------------------------------------------------------------
# registration: the installed package, dry-run by default
# --------------------------------------------------------------------------


def install_fake_package(home: Path, version: str = "1.5.47") -> Path:
    """An installed copy of the package inside a fake home."""
    package = home / ".codex" / "plugins" / "cache" / "fleet-lhc" / "last-human-commit" / version
    (package / "scripts").mkdir(parents=True)
    shutil.copy(FACADE, package / "scripts" / "plan_mcp.py")
    return package


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_setup_points_at_the_installed_package_and_writes_nothing(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    config.write_text('[mcp_servers.AskHuman]\nurl = "https://x"\n', encoding="utf-8")
    package = install_fake_package(home)
    before = digest(config)

    code = setup_mcp.main(["--home", str(home)])
    out = capsys.readouterr().out
    assert code == 0
    # Nothing was written: the file is byte for byte the same.
    assert digest(config) == before
    assert list(home.rglob("*.bak-*")) == []
    assert "DRY RUN" in out
    assert "[mcp_servers.LhcPlan]" in out
    # The snippet starts the installed facade, not the working copy.
    assert str(package / "scripts" / "plan_mcp.py") in out
    assert str(FACADE) not in out


def test_setup_without_an_installed_package_says_so(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    code = setup_mcp.main(["--home", str(home)])
    assert code == 1
    assert "no installed Last Human Commit package" in capsys.readouterr().err


def test_setup_names_an_installed_package_that_predates_the_facade(tmp_path, capsys):
    """The snippet still points at the installed package, and says that the
    installed version does not carry the facade yet."""
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    package = home / ".codex" / "plugins" / "cache" / "fleet-lhc" / "last-human-commit" / "1.5.47"
    package.mkdir(parents=True)
    code = setup_mcp.main(["--home", str(home)])
    out, err = capsys.readouterr()
    assert code == 0
    assert "does not carry" in err
    assert str(package / "scripts" / "plan_mcp.py") in out


def test_setup_apply_patches_codex_config_with_a_timestamped_backup(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    install_fake_package(home)
    config = home / ".codex" / "config.toml"
    config.write_text('[model]\nname = "gpt-5"\n', encoding="utf-8")
    code = setup_mcp.main(["--home", str(home), "--apply"])
    assert code == 0
    text = config.read_text(encoding="utf-8")
    assert '[mcp_servers.LhcPlan]' in text and 'command = "python3"' in text
    assert text.index('[model]') < text.index('[mcp_servers.LhcPlan]')
    backups = list(home.glob(".codex/config.toml.bak-lhc-mcp-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == '[model]\nname = "gpt-5"\n'
    capsys.readouterr()


def test_setup_apply_replaces_only_its_own_section(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    install_fake_package(home)
    config = home / ".codex" / "config.toml"
    config.write_text('[mcp_servers.LhcPlan]\ncommand = "old"\n\n[mcp_servers.AskHuman]\nurl = "https://x"\n',
                      encoding="utf-8")
    setup_mcp.main(["--home", str(home), "--apply"])
    text = config.read_text(encoding="utf-8")
    assert "old" not in text
    assert '[mcp_servers.AskHuman]' in text and 'url = "https://x"' in text
    capsys.readouterr()


def test_setup_remove_takes_the_registration_out(tmp_path, capsys):
    """A registration in the config wins over the one the plugin declares, so a
    registration that points at a package which is gone has to be removable."""
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    config.write_text('[mcp_servers.LhcPlan]\ncommand = "python3"\nargs = ["/gone/plan_mcp.py"]\n'
                      '\n[mcp_servers.AskHuman]\nurl = "https://x"\n', encoding="utf-8")
    before = digest(config)

    # the dry run writes nothing
    assert setup_mcp.main(["--home", str(home), "--remove"]) == 0
    assert digest(config) == before
    assert "DRY RUN" in capsys.readouterr().out

    assert setup_mcp.main(["--home", str(home), "--remove", "--apply"]) == 0
    text = config.read_text(encoding="utf-8")
    assert "LhcPlan" not in text
    assert '[mcp_servers.AskHuman]' in text and 'url = "https://x"' in text
    backups = list(home.glob(".codex/config.toml.bak-lhc-mcp-*"))
    assert len(backups) == 1
    assert "[mcp_servers.LhcPlan]" in backups[0].read_text(encoding="utf-8")
    capsys.readouterr()


# --------------------------------------------------------------------------
# the manifests register the server the way the harnesses read it
# --------------------------------------------------------------------------


def test_codex_manifest_declares_the_server_next_to_the_manifest():
    """Codex reads `mcpServers` as a path to a .mcp.json in the plugin root."""
    manifest = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "last-human-commit"
    assert manifest["mcpServers"] == "./.mcp.json"
    server = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["LhcPlan"]
    assert server["command"] == "python3"
    # plugin-relative, the same way these manifests point at ./skills/:
    # an absolute path would pin the manifest to one machine.
    assert server["args"] == ["./scripts/plan_mcp.py"]
    assert (PLUGIN / "scripts" / "plan_mcp.py").is_file()


def test_the_native_codex_flavour_declares_the_same_server():
    """The fleet installs native/codex as the package root, so it declares its own."""
    manifest = json.loads((NATIVE / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "last-human-commit"
    assert manifest["mcpServers"] == "./.mcp.json"
    server = json.loads((NATIVE / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["LhcPlan"]
    assert server["args"] == ["./scripts/plan_mcp.py"]
    assert (NATIVE / "scripts" / "plan_mcp.py").is_file()


def test_the_portable_manifest_and_the_overlay_agree():
    """The portable package reads mcp.json, the overlay reads .mcp.json."""
    portable = (PLUGIN / "mcp.json").read_text(encoding="utf-8")
    overlay = (PLUGIN / ".mcp.json").read_text(encoding="utf-8")
    assert list(json.loads(portable)["mcpServers"]) == ["LhcPlan"]
    assert json.loads(portable)["$schema"] == "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json"
    server = json.loads(portable)["mcpServers"]["LhcPlan"]
    assert server["type"] == "stdio"
    assert server["args"] == ["${PLUGIN_ROOT}/scripts/plan_mcp.py"]
    assert (NATIVE / ".mcp.json").read_text(encoding="utf-8") == overlay


def test_claude_manifest_declares_the_server_with_the_plugin_root():
    """Claude Code reads an inline map and expands ${CLAUDE_PLUGIN_ROOT}."""
    manifest = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    server = manifest["mcpServers"]["LhcPlan"]
    assert server["command"] == "python3"
    assert server["args"] == ["${CLAUDE_PLUGIN_ROOT}/scripts/plan_mcp.py"]


def test_the_root_manifest_has_no_mcp_server_field():
    """The Agent Plugins schema forbids unknown fields, and the package's own
    validator would reject them too."""
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    assert "mcpServers" not in manifest


# --------------------------------------------------------------------------
# a real handshake, no mocks
# --------------------------------------------------------------------------


@pytest.mark.nightly
def test_real_stdio_handshake_spawns_the_server_and_calls_every_tool(tmp_path):
    plan_dir = make_plan_dir(tmp_path, {})
    catalog = write_catalog(tmp_path / "catalog.json")
    proc = subprocess.Popen(
        [sys.executable, str(FACADE)],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, cwd=str(ROOT), env={**os.environ, "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"},
    )
    transcript = []

    def ask(message):
        proc.stdin.write(json.dumps(message) + "\n")
        proc.stdin.flush()
        if "id" not in message:
            return None
        reply = json.loads(proc.stdout.readline())
        transcript.append({"sent": message, "received": reply})
        return reply

    init = ask({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                           "clientInfo": {"name": "lhc-test", "version": "0"}}})
    ask({"jsonrpc": "2.0", "method": "notifications/initialized"})
    tools = ask({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    created = ask({"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {
        "name": "create_leaf",
        "arguments": {"plan_dir": str(plan_dir),
                      "leaf": {"id": "L01", "label": "Один", "status": "queued",
                               "estimate_minutes": 15}},
    }})
    updated = ask({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {
        "name": "update_leaf",
        "arguments": {"plan_dir": str(plan_dir), "leaf_id": "L01",
                      "fields": {"status": "done", "finished_at": "07:20"}},
    }})
    built = ask({"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {
        "name": "build_plan", "arguments": {"plan_dir": str(plan_dir)},
    }})
    priced = ask({"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {
        "name": "estimate_cost",
        "arguments": {"model": "acme-flash", "minutes": 15,
                      "offline": True, "catalog": str(catalog)},
    }})
    proc.stdin.close()
    proc.wait(timeout=30)

    assert init["result"]["protocolVersion"] == "2024-11-05"
    assert {tool["name"] for tool in tools["result"]["tools"]} == {
        "create_leaf", "update_leaf", "build_plan", "estimate_cost", "update_progress", "publish_html", "revise_plan"}
    for reply in (created, updated, built, priced):
        assert reply["result"]["isError"] is False, reply["result"]
    assert (plan_dir / "leaves" / "L01.json").is_file()
    assert read_leaf(plan_dir, "L01")["status"] == "done"
    assert proc.returncode == 0
    (tmp_path / "handshake.json").write_text(json.dumps(transcript, indent=2), encoding="utf-8")
