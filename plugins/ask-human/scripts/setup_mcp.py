#!/usr/bin/env python3
"""Register an AskHuman/AskSecret-compatible MCP endpoint into harness configs.

Marketplace installs cannot take parameters, so endpoints come from the
environment (or a plain .env): LHC_ASKHUMAN_MCP_URL / LHC_ASKSECRET_MCP_URL,
plus optional ..._MCP_TOKEN that becomes an Authorization Bearer header.

Usage:
  python3 setup_mcp.py                                   # dry-run, AskHuman
  python3 setup_mcp.py --apply                           # patch ~/.codex/config.toml
  python3 setup_mcp.py --name AskSecret --url-env LHC_ASKSECRET_MCP_URL --apply

Codex is patched automatically (timestamped backup is kept). Other harnesses:
add an MCP server with the same name and URL in their MCP settings; the
dry-run prints the snippet.
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for candidate in (Path.cwd() / ".env", Path.home() / ".env"):
        if candidate.is_file():
            for line in candidate.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, raw = line.partition("=")
                    values.setdefault(key.strip(), raw.strip().strip('"').strip("'"))
    return values


def config_block(name: str, url: str, token: str | None) -> str:
    block = f"[mcp_servers.{name}]\nurl = \"{url}\"\n"
    if token:
        block += (
            f"\n[mcp_servers.{name}.http_headers]\n"
            f"Authorization = \"Bearer {token}\"\n"
        )
    return block


def patch_codex(name: str, url: str, token: str | None, apply: bool) -> int:
    path = Path.home() / ".codex" / "config.toml"
    block = config_block(name, url, token)
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
        print("DRY RUN — nothing written. Block that would be applied:\n")
        print(block)
        print("snippet for other harnesses: add an MCP server named "
              f"{name} with url {url}" + (" and a Bearer Authorization header" if token else ""))
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak-lhc-mcp-{stamp}")
    backup.write_text(text, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")
    print(f"patched {path} (backup: {backup.name})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default="AskHuman", help="MCP server name (default: AskHuman)")
    parser.add_argument("--url-env", default=None, help="env var holding the URL (default: LHC_<NAME>_MCP_URL)")
    parser.add_argument("--token-env", default=None, help="env var holding the token (default: LHC_<NAME>_MCP_TOKEN)")
    parser.add_argument("--apply", action="store_true", help="write the config (default: dry-run)")
    args = parser.parse_args()

    url_env = args.url_env or f"LHC_{args.name.upper()}_MCP_URL"
    token_env = args.token_env or f"LHC_{args.name.upper()}_MCP_TOKEN"
    env = {**load_env(), **os.environ}
    url = env.get(url_env, "").strip()
    token = env.get(token_env, "").strip() or None
    if not url:
        print(
            f"FAIL: set {url_env} (env or .env) to your {args.name}-compatible MCP URL.\n"
            "Example: export LHC_ASKHUMAN_MCP_URL=\"https://your-notify.example/mcp\"",
            file=sys.stderr,
        )
        return 1
    return patch_codex(args.name, url, token, args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
