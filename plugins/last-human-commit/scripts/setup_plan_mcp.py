#!/usr/bin/env python3
"""Register the LhcPlan MCP server (the plan CLI facade) into a harness config.

Same shape as plugins/ask-human/scripts/setup_mcp.py, because that is the
registration form this repository already uses: dry-run by default, printing the
snippet; ``--apply`` is the separate permission that writes someone else's config
and it keeps a timestamped backup. The server is a stdio server, so what gets
registered is the command line that starts it - no second transport is invented.

The command line points at the **installed** package, not at the working copy:
the facade of a checkout is not what a harness has to start, and a snippet
with the path of a developer's checkout would be wrong on every other host.
The installed package is found under the plugin caches of the harnesses that
install it (``~/.codex/plugins/cache`` and ``~/.claude/plugins/cache``); the
newest version that carries the facade wins. ``--server`` overrides the search.

Usage:
  python3 setup_plan_mcp.py                       # dry-run, prints the snippet
  python3 setup_plan_mcp.py --apply               # patch ~/.codex/config.toml (+ backup)
  python3 setup_plan_mcp.py --remove --apply      # take the registration out (+ backup)
  python3 setup_plan_mcp.py --name LhcPlan --server /abs/path/plan_mcp.py --apply

Other harnesses (Claude Code, Qoder, Opencode, Zcode): add an MCP server with the
same name and the same command/args in their MCP settings; the dry-run prints both
the TOML block and the equivalent JSON snippet.
"""

from __future__ import annotations

import argparse
import datetime
import json
import sys
from pathlib import Path
from typing import Optional

DEFAULT_NAME = "LhcPlan"
SERVER_RELATIVE = Path("scripts") / "plan_mcp.py"

# Where the harnesses keep an installed plugin. The package of this repository
# is installed under its marketplace name and its version.
CACHE_ROOTS = (
    Path(".codex") / "plugins" / "cache",
    Path(".claude") / "plugins" / "cache",
)
PLUGIN_DIR_NAME = "last-human-commit"


def version_key(name: str) -> tuple[int, ...]:
    """The version of a cache directory, as numbers; a name that is not one sorts first."""

    parts: list[int] = []
    for piece in name.split("."):
        if not piece.isdigit():
            return ()
        parts.append(int(piece))
    return tuple(parts)


def installed_packages(home: Path) -> list[Path]:
    """Every installed copy of the LHC package, newest version first."""

    found: list[Path] = []
    for root in CACHE_ROOTS:
        base = home / root
        if not base.is_dir():
            continue
        for marketplace in sorted(base.iterdir()):
            if not marketplace.is_dir():
                continue
            plugin = marketplace / PLUGIN_DIR_NAME
            if not plugin.is_dir():
                continue
            for version in sorted(plugin.iterdir(), key=lambda p: version_key(p.name), reverse=True):
                if version.is_dir():
                    found.append(version)
    return found


def default_server(home: Path) -> Path | None:
    """The facade of the newest installed package, or None when none is installed."""

    packages = installed_packages(home)
    return packages[0] / SERVER_RELATIVE if packages else None


def server_command(server: Path, python: str) -> tuple[str, list[str]]:
    """The exact command line that starts the facade over the plan CLI."""
    return python, [str(server)]


def toml_block(name: str, command: str, args: list[str]) -> str:
    rendered = json.dumps(args)
    return f"[mcp_servers.{name}]\ncommand = \"{command}\"\nargs = {rendered}\n"


def json_block(name: str, command: str, args: list[str]) -> str:
    return json.dumps({"mcpServers": {name: {"command": command, "args": args}}}, indent=2) + "\n"


def section_span(text: str, name: str) -> Optional[tuple[int, int]]:
    """The span of the section of that MCP server, with its subsections."""

    header = f"[mcp_servers.{name}]"
    start = text.find(header)
    if start == -1:
        return None
    nxt = text.find("\n[", start + 1)
    end = len(text) if nxt == -1 else nxt + 1
    return start, end


def remove_codex(name: str, apply: bool, home: Path) -> int:
    """Take the registration out again, the way it went in.

    A server registered in the config wins over the one the plugin manifest
    declares, so a registration that points at a package which is gone would
    shadow the server of the installed plugin.
    """

    path = home / ".codex" / "config.toml"
    if not path.is_file():
        print(f"no codex config at {path}; nothing to remove")
        return 0
    text = path.read_text(encoding="utf-8")
    span = section_span(text, name)
    if span is None:
        print(f"no [mcp_servers.{name}] in {path}; nothing to remove")
        return 0
    start, end = span
    if not apply:
        print(f"DRY RUN — nothing written. Section that would be removed from {path}:\n")
        print(text[start:end])
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak-lhc-mcp-{stamp}")
    backup.write_text(text, encoding="utf-8")
    path.write_text(text[:start] + text[end:], encoding="utf-8")
    print(f"removed [mcp_servers.{name}] from {path} (backup: {backup.name})")
    return 0


def patch_codex(name: str, command: str, args: list[str], apply: bool, home: Path) -> int:
    path = home / ".codex" / "config.toml"
    block = toml_block(name, command, args)
    if not path.is_file():
        print(f"no codex config at {path}; add this snippet manually:\n\n{block}")
        return 0
    text = path.read_text(encoding="utf-8")
    span = section_span(text, name)
    if span is not None:
        start, end = span
        updated = text[:start] + block.rstrip("\n") + "\n" + text[end:]
    else:
        updated = text.rstrip("\n") + "\n\n" + block
    if not apply:
        print("DRY RUN — nothing written. Block that would be applied to "
              f"{path}:\n")
        print(block)
        print("snippet for other harnesses (add an MCP server with this name, command and args):")
        print(json_block(name, command, args))
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak-lhc-mcp-{stamp}")
    backup.write_text(text, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")
    print(f"patched {path} (backup: {backup.name})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default=DEFAULT_NAME, help=f"MCP server name (default: {DEFAULT_NAME})")
    parser.add_argument("--server", default=None,
                        help="absolute path to plan_mcp.py (default: the newest installed package)")
    parser.add_argument("--python", default="python3",
                        help="interpreter the harness starts (default: python3)")
    parser.add_argument("--home", default=None, help="home directory to patch (default: $HOME)")
    parser.add_argument("--apply", action="store_true", help="write the config (default: dry-run)")
    parser.add_argument("--remove", action="store_true",
                        help="take the registration out instead of writing one")
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser() if args.home else Path.home()
    if args.remove:
        return remove_codex(args.name, args.apply, home)
    if args.server:
        server = Path(args.server).expanduser()
        if not server.is_absolute():
            server = server.resolve()
    else:
        server = default_server(home)
        if server is None:
            print("FAIL: no installed Last Human Commit package found under "
                  + ", ".join(str(home / root) for root in CACHE_ROOTS)
                  + "; install the plugin or pass --server PATH", file=sys.stderr)
            return 1
        if not server.is_file():
            # The installed version is older than the facade: the snippet still
            # points at the installed package, and the file arrives with the
            # release that ships it.
            print(f"warning: the installed package {server.parent.parent.name} does not carry "
                  f"{SERVER_RELATIVE} yet; the server starts once that version is installed",
                  file=sys.stderr)
    if not server.is_file() and args.server:
        print(f"FAIL: no MCP server at {server}", file=sys.stderr)
        return 1
    command, cli_args = server_command(server, args.python)
    return patch_codex(args.name, command, cli_args, args.apply, home)


if __name__ == "__main__":
    raise SystemExit(main())
