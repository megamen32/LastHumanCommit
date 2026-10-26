"""The two hook forms of the Ask Human plugin: the codex one and the zcode one.

The plugin ships two hook documents for the same event. `hooks/hooks.json` is
the codex form (the timeout is in seconds), `hooks/zcode-hooks.json` is the
zcode form (the timeout is in milliseconds). Both must point at the script of
this plugin, never at the script of another package.

The zcode form is checked structurally here: the event, the command, the
timeout key of its own form and the `${...}` chain that resolves the script.
No network and no harness are involved.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[1]
HOOKS = PLUGIN / "hooks"
CODEX_HOOKS = HOOKS / "hooks.json"
ZCODE_HOOKS = HOOKS / "zcode-hooks.json"
SCRIPT = PLUGIN / "scripts" / "ask_human_hook.py"
sys.path.insert(0, str(PLUGIN / "scripts"))

import setup_mcp  # noqa: E402

EVENT = "PermissionRequest"


# ---------------------------------------------------------------------------
# the shell chain of the plugin root
# ---------------------------------------------------------------------------


def split_chain(template: str) -> tuple[str, str]:
    """The `${...}` prefix of the template and the rest of the path."""
    if not template.startswith("${"):
        return "", template
    depth = 0
    for index, char in enumerate(template):
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return template[: index + 1], template[index + 1:]
    raise AssertionError(f"unbalanced chain: {template}")


def parse_chain(template: str) -> tuple[list[str], str]:
    """The variable names and the fallback of a `${A:-${B:-fallback}}` chain."""
    chain, _suffix = split_chain(template)
    names: list[str] = []
    inner = chain
    while True:
        match = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-(.*)\}", inner, re.S)
        if match:
            names.append(match.group(1))
            inner = match.group(2)
            continue
        # a tail without a default of its own, such as `${CLAUDE_PLUGIN_ROOT}`
        tail = re.fullmatch(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}", inner, re.S)
        if tail:
            names.append(tail.group(1))
            return names, ""
        break
    return names, inner


def expand(template: str, env: dict[str, str]) -> str:
    """The value the shell gives the chain under the environment."""
    chain, suffix = split_chain(template)
    names, fallback = parse_chain(template)
    for name in names:
        value = env.get(name) or ""
        if value:
            return value + suffix
    return fallback + suffix


def command_of(document: dict) -> str:
    """The command of the one handler of the one event of a hook document."""
    handlers = document["hooks"][EVENT]
    assert len(handlers) == 1, handlers
    entries = handlers[0]["hooks"]
    assert len(entries) == 1, entries
    return entries[0]["command"]


def path_template(command: str) -> str:
    """The quoted path of the script inside the command."""
    match = re.search(r'"([^"]+)"', command)
    assert match, command
    return match.group(1)


# ---------------------------------------------------------------------------
# both forms
# ---------------------------------------------------------------------------


def test_both_forms_register_the_permission_request():
    for path in (CODEX_HOOKS, ZCODE_HOOKS):
        document = json.loads(path.read_text(encoding="utf-8"))
        assert list(document["hooks"]) == [EVENT], path.name
        entry = document["hooks"][EVENT][0]["hooks"][0]
        assert entry["type"] == "command", path.name
        assert "--event PermissionRequest" in entry["command"], path.name
        assert "ask_human_hook.py" in entry["command"], path.name


def test_the_command_points_at_the_script_of_this_plugin():
    for path in (CODEX_HOOKS, ZCODE_HOOKS):
        template = path_template(command_of(json.loads(path.read_text(encoding="utf-8"))))
        names, _fallback = parse_chain(template)
        assert names, path.name
        for name in names:
            resolved = expand(template, {name: str(PLUGIN)})
            assert resolved == str(SCRIPT), (path.name, name, resolved)
            assert Path(resolved).is_file(), (path.name, name)


def test_the_zcode_form_uses_the_chain_of_the_zcode_package():
    template = path_template(command_of(json.loads(ZCODE_HOOKS.read_text(encoding="utf-8"))))
    names, fallback = parse_chain(template)
    assert names == ["CLAUDE_PLUGIN_ROOT", "CODEX_PLUGIN_ROOT", "PLUGIN_ROOT",
                     "ZCODE_PLUGIN_ROOT"], names
    # the fallback of the chain is the installed copy of this plugin, and it is
    # the plugin itself: never the script of the last-human-commit package
    _chain, suffix = split_chain(template)
    assert suffix == "/scripts/ask_human_hook.py", suffix
    assert fallback.endswith("/plugins/ask-human"), fallback
    assert "last-human-commit" not in fallback, fallback
    # the same chain, read with no plugin root in the environment
    assert expand(template, {}).endswith("/plugins/ask-human/scripts/ask_human_hook.py")


def test_the_codex_form_keeps_its_own_chain():
    template = path_template(command_of(json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))))
    names, _fallback = parse_chain(template)
    # the codex runtime exports PLUGIN_ROOT and CLAUDE_PLUGIN_ROOT, and only them
    assert names == ["PLUGIN_ROOT", "CLAUDE_PLUGIN_ROOT"], names


def test_no_form_points_at_the_script_of_another_package():
    for path in (CODEX_HOOKS, ZCODE_HOOKS):
        text = path.read_text(encoding="utf-8")
        assert "last-human-commit" not in text, path.name
        assert "lhc_entry.py" not in text, path.name


def test_each_form_declares_the_timeout_in_its_own_unit():
    codex = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))["hooks"][EVENT][0]["hooks"][0]
    zcode = json.loads(ZCODE_HOOKS.read_text(encoding="utf-8"))["hooks"][EVENT][0]["hooks"][0]
    # the codex form counts seconds, the zcode form counts milliseconds
    assert "timeout" in codex and "timeoutMs" not in codex, codex
    assert "timeoutMs" in zcode and "timeout" not in zcode, zcode
    assert codex["timeout"] == 120, codex
    assert zcode["timeoutMs"] == codex["timeout"] * 1000, zcode


def test_the_two_forms_differ_only_in_the_timeout_unit_and_the_root():
    codex = json.loads(CODEX_HOOKS.read_text(encoding="utf-8"))["hooks"][EVENT][0]["hooks"][0]
    zcode = json.loads(ZCODE_HOOKS.read_text(encoding="utf-8"))["hooks"][EVENT][0]["hooks"][0]
    assert codex["statusMessage"] == zcode["statusMessage"]
    assert codex["type"] == zcode["type"]
    codex_without = {k: v for k, v in codex.items() if k not in ("timeout", "command")}
    zcode_without = {k: v for k, v in zcode.items() if k not in ("timeoutMs", "command")}
    assert codex_without == zcode_without


def test_the_codex_form_is_still_the_one_the_codex_manifests_declare():
    for manifest in (PLUGIN / "plugin.json", PLUGIN / ".codex-plugin" / "plugin.json",
                     PLUGIN / ".claude-plugin" / "plugin.json"):
        document = json.loads(manifest.read_text(encoding="utf-8"))
        declared = document.get("hooks") or document.get("extensions", {})["com.openai"]["hooks"]
        assert declared == "./hooks/hooks.json", (manifest.name, declared)


def test_no_form_carries_a_credential():
    pattern = re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}")
    for path in (CODEX_HOOKS, ZCODE_HOOKS):
        assert not pattern.search(path.read_text(encoding="utf-8")), path.name


# ---------------------------------------------------------------------------
# the MCP snippet of every harness
# ---------------------------------------------------------------------------


def snippets_of(output: str) -> dict[str, dict]:
    """The MCP snippet that the dry run prints for every other harness."""
    decoder = json.JSONDecoder()
    found: dict[str, dict] = {}
    for chunk in output.split("snippet for ")[1:]:
        name = chunk.split(" ", 1)[0]
        start = chunk.index("{")
        found[name] = decoder.raw_decode(chunk[start:])[0]["mcpServers"]["AskHuman"]
    return found


def test_every_other_harness_gets_the_same_endpoint_and_the_same_bearer(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TEST_TOKEN", "secret-token")
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    code = setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp",
                           "--token-env", "TEST_TOKEN"])
    out = capsys.readouterr().out
    assert code == 0

    found = snippets_of(out)
    assert set(found) == set(setup_mcp.OTHER_HARNESSES), sorted(found)
    for harness, server in found.items():
        assert server["url"] == "https://notify.example/mcp", harness
        assert server["headers"]["Authorization"] == "Bearer secret-token", harness
        assert server["type"] == "http", harness
