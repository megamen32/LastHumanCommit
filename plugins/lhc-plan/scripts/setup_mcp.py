#!/usr/bin/env python3
"""Register the LhcPlan MCP server (the plan CLI facade) into a harness config.

Same shape as plugins/ask-human/scripts/setup_mcp.py, because that is the
registration form this repository already uses: dry-run by default, printing the
snippet; ``--apply`` is the separate permission that writes someone else's config
and it keeps a timestamped backup. The server is a stdio server, so what gets
registered is the command line that starts it - no second transport is invented.

Usage:
  python3 setup_mcp.py                       # dry-run, prints the snippet
  python3 setup_mcp.py --apply               # patch ~/.codex/config.toml (+ backup)
  python3 setup_mcp.py --name LhcPlan --server /abs/path/plan_mcp.py --apply

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

DEFAULT_NAME = "LhcPlan"
DEFAULT_SERVER = Path(__file__).resolve().parent / "plan_mcp.py"


def server_command(server: Path, python: str) -> tuple[str, list[str]]:
    """The exact command line that starts the facade over the plan CLI."""
    return python, [str(server)]


def toml_block(name: str, command: str, args: list[str]) -> str:
    rendered = json.dumps(args)
    return f"[mcp_servers.{name}]\ncommand = \"{command}\"\nargs = {rendered}\n"


def json_block(name: str, command: str, args: list[str]) -> str:
    return json.dumps({"mcpServers": {name: {"command": command, "args": args}}}, indent=2) + "\n"


def patch_codex(name: str, command: str, args: list[str], apply: bool, home: Path) -> int:
    path = home / ".codex" / "config.toml"
    block = toml_block(name, command, args)
    if not path.is_file():
        print(f"no codex config at {path}; add this snippet manually:\n\n{block}")
        return 0
    text = path.read_text(encoding="utf-8")
    header = f"[mcp_servers.{name}]"
    if header in text:
        start = text.index(header)
        nxt = text.find("\n[", start + 1)
        end = len(text) if nxt == -1 else nxt + 1
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
    parser.add_argument("--server", default=str(DEFAULT_SERVER),
                        help="absolute path to plan_mcp.py (default: the one next to this script)")
    parser.add_argument("--python", default="python3",
                        help="interpreter the harness starts (default: python3)")
    parser.add_argument("--home", default=None, help="home directory to patch (default: $HOME)")
    parser.add_argument("--apply", action="store_true", help="write the config (default: dry-run)")
    args = parser.parse_args(argv)

    server = Path(args.server).expanduser()
    if not server.is_absolute():
        server = server.resolve()
    if not server.is_file():
        print(f"FAIL: no MCP server at {server}", file=sys.stderr)
        return 1
    command, cli_args = server_command(server, args.python)
    home = Path(args.home).expanduser() if args.home else Path.home()
    return patch_codex(args.name, command, cli_args, args.apply, home)


if __name__ == "__main__":
    raise SystemExit(main())
