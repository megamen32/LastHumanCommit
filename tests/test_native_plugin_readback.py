"""The Codex manager's exact native list output proves installed plugin state."""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src/common/tools"))
import lhc_outcome_review as review  # noqa: E402


PLUGIN_ID = "last-human-commit"
DISPLAY_NAME = "Last Human Commit"
MARKETPLACE = "megamen32-plugins"
VERSION = "1.5.12"
TARGET = "codex plugin list --marketplace megamen32-plugins --json"
EXPECTED = f"plugin:{PLUGIN_ID}@{MARKETPLACE}:{VERSION}"


def manager_call(cwd, *, command=TARGET):
    return {
        "name": "exec_command",
        "arguments": json.dumps({"cmd": command, "workdir": str(cwd)}),
        "_native_cwd": str(cwd),
        "_exit_code": 0,
    }


def entry(**overrides):
    value = {
        "pluginId": PLUGIN_ID,
        "name": DISPLAY_NAME,
        "marketplaceName": MARKETPLACE,
        "version": VERSION,
        "installed": True,
        "enabled": True,
        "source": {"marketplace": MARKETPLACE},
    }
    value.update(overrides)
    return value


def observe(cwd, payload, *, target=TARGET, expected=EXPECTED, command=TARGET, workdir=None):
    return review.real_observation(
        manager_call(cwd, command=command) if workdir is None else {
            **manager_call(cwd, command=command),
            "arguments": json.dumps({"cmd": command, "workdir": str(workdir)}),
        },
        json.dumps(payload), target, "deploy", cwd=cwd, expected=expected)


def test_exact_codex_manager_list_proves_one_installed_enabled_plugin(tmp_path):
    output = {"installed": [entry()], "available": []}

    assert observe(tmp_path, output)


@pytest.mark.parametrize("row", [
    entry(pluginId="another-plugin", name="Another Plugin"),
    entry(marketplaceName="other-marketplace"),
    entry(version="1.5.11"),
    entry(installed=False),
    entry(enabled=False),
])
def test_manager_readback_rejects_wrong_or_inactive_plugin(tmp_path, row):
    assert not observe(tmp_path, {"installed": [row], "available": []})


def test_manager_readback_rejects_available_only_and_duplicate_conflicts(tmp_path):
    assert not observe(tmp_path, {"installed": [], "available": [entry()]})
    assert not observe(tmp_path, {"installed": [entry(), entry(version="1.5.13")], "available": []})


@pytest.mark.parametrize("command,target,workdir,payload", [
    ("codex plugin list --json", TARGET, None, {"installed": [entry()], "available": []}),
    (TARGET + " --verbose", TARGET, None, {"installed": [entry()], "available": []}),
    (TARGET, "codex plugin list --marketplace another-marketplace --json", None,
     {"installed": [entry()], "available": []}),
    (TARGET, TARGET, Path("/foreign/cwd"), {"installed": [entry()], "available": []}),
])
def test_manager_readback_rejects_unbound_command_or_cwd(tmp_path, command, target, workdir, payload):
    assert not observe(tmp_path, payload, command=command, target=target, workdir=workdir)


@pytest.mark.parametrize("payload", [
    {"available": [entry()]},
    {"installed": {"pluginId": PLUGIN_ID}},
    {"installed": [entry(), {"pluginId": PLUGIN_ID, "version": VERSION}], "available": []},
])
def test_manager_readback_rejects_malformed_or_unrelated_output(tmp_path, payload):
    assert not observe(tmp_path, payload)


def test_manager_readback_rejects_malformed_json(tmp_path):
    call = manager_call(tmp_path)
    assert not review.real_observation(call, "{not json", TARGET, "deploy", cwd=tmp_path, expected=EXPECTED)


def test_manager_readback_rejects_foreign_native_cwd_even_with_explicit_local_workdir(tmp_path):
    call = manager_call(tmp_path)
    call["_native_cwd"] = str(tmp_path / "foreign")
    assert not review.real_observation(
        call, json.dumps({"installed": [entry()], "available": []}),
        TARGET, "deploy", cwd=tmp_path, expected=EXPECTED)


def test_typed_plugin_expectation_does_not_loosen_ordinary_deploy_readback(tmp_path):
    ordinary = manager_call(tmp_path, command="curl https://demo.test/version")
    assert review.real_observation(ordinary, '{"version":"v2"}',
                                   "https://demo.test/version", "deploy", cwd=tmp_path,
                                   expected="v2")
