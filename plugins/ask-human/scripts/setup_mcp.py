#!/usr/bin/env python3
"""Register the AskHuman MCP endpoint into the harness configs.

Same shape as plugins/last-human-commit/scripts/setup_plan_mcp.py, because that is
the registration form this repository already uses: dry-run by default, printing the
snippet; ``--apply`` is the separate permission that writes someone else's config
and it keeps a timestamped backup.

The endpoint comes from the environment of the host, because a marketplace install
cannot take parameters. The keys that really exist on a host are read:

    ASK_HUMAN_URL          the human-request intake of the Notice Place service
    LHC_ASKHUMAN_MCP_URL   the MCP URL of the same service
    ASK_HUMAN_MCP_URL      the MCP URL of the same service

The protected env file of the host (``~/.config/ask-human/env``) and a plain
``.env`` are read as well, so a host that keeps its producer identity there is
registered without exporting anything first. The token is read from
``NOTIFY_CENTER_TOKEN`` and becomes a Bearer header; it is never written to the
repository, only to the config of the harness on this machine.

When the URL comes from ``ASK_HUMAN_URL`` it is the human-request intake, not the
MCP endpoint, so the MCP URL of the same service is derived from it. The
derivation is printed, so nothing is registered that was not shown first.

Usage:
  python3 setup_mcp.py                                   # dry-run, AskHuman
  python3 setup_mcp.py --apply                           # patch ~/.codex/config.toml (+ backup)
  python3 setup_mcp.py --name AskSecret --url-env LHC_ASKSECRET_MCP_URL --apply
  python3 setup_mcp.py --home /tmp/fake-home --apply      # patch another home

Codex is patched automatically (a timestamped backup is kept, and the sections of
other servers are left alone). Other harnesses (hermes, zcode, opencode, minimax):
add an MCP server with the same name and URL in their MCP settings; the dry-run
prints the equivalent JSON snippet for each of them.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from pathlib import Path

DEFAULT_NAME = "AskHuman"
ENV_FILE = Path("~/.config/ask-human/env")
DOTENV_FILES = (Path(".env"), Path("~/.env"))
OTHER_HARNESSES = ("hermes", "zcode", "opencode", "minimax")


# ---------------------------------------------------------------------------
# the endpoint
# ---------------------------------------------------------------------------


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a KEY=VALUE env file."""
    values: dict[str, str] = {}
    try:
        contents = path.expanduser().read_text(encoding="utf-8")
    except OSError:
        return values
    for raw in contents.splitlines():
        line = raw.strip().removeprefix("export ").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            values[key] = value
    return values


def merged_settings(env_file: Path | None = None) -> dict[str, str]:
    """The settings of the host: dotenv, then the protected env file, then the process."""
    values: dict[str, str] = {}
    for candidate in DOTENV_FILES:
        values.update(parse_env_file(candidate))
    candidates = (env_file,) if env_file is not None else (ENV_FILE,)
    for candidate in candidates:
        values.update(parse_env_file(candidate))
    values.update(dict(os.environ))
    return values


def first_value(settings: dict[str, str], keys: tuple[str, ...]) -> tuple[str, str]:
    """The first nonempty value of the keys, with the key it came from."""
    for key in keys:
        value = str(settings.get(key) or "").strip()
        if value:
            return value, key
    return "", ""


def url_keys(name: str) -> tuple[str, ...]:
    """The keys that carry the endpoint of this server, in the order of preference."""
    keys = [f"LHC_{name.upper()}_MCP_URL"]
    if name.lower() == "askhuman":
        keys += ["ASK_HUMAN_MCP_URL", "ASK_HUMAN_URL"]
    return tuple(keys)


def token_keys(name: str) -> tuple[str, ...]:
    """The keys that carry the token of this server, in the order of preference."""
    keys = [f"LHC_{name.upper()}_MCP_TOKEN"]
    if name.lower() == "askhuman":
        keys += ["NOTIFY_CENTER_TOKEN", "ASK_HUMAN_MCP_TOKEN"]
    return tuple(keys)


def mcp_url(url: str) -> str:
    """The MCP URL of the service that serves a human-request intake URL."""
    base = url.strip().rstrip("/")
    if base.endswith("/v1/human-requests"):
        return base[: -len("/v1/human-requests")] + "/mcp"
    if base.endswith("/human-requests"):
        return base[: -len("/human-requests")] + "/mcp"
    return base


def resolve_endpoint(name: str, settings: dict[str, str], url_env: str | None,
                     explicit_url: str | None) -> tuple[str, str, str]:
    """The endpoint of the server, with the key it came from and a note about it."""
    if explicit_url:
        return explicit_url.strip(), "--url", ""
    if url_env:
        url = str(settings.get(url_env) or "").strip()
        if url:
            return mcp_url(url), url_env, ""
        return "", url_env, ""
    url, key = first_value(settings, url_keys(name))
    if not url:
        return "", "", ""
    if url.endswith("/human-requests"):
        derived = mcp_url(url)
        return derived, key, f"derived from {key} (the human-request intake of the same service)"
    return url, key, ""


def resolve_token(name: str, settings: dict[str, str], token_env: str | None) -> tuple[str, str]:
    """The Bearer token of the server, with the key it came from."""
    if token_env:
        return str(settings.get(token_env) or "").strip(), token_env
    token, key = first_value(settings, token_keys(name))
    return token, key


# ---------------------------------------------------------------------------
# the snippets
# ---------------------------------------------------------------------------


def toml_block(name: str, url: str, token: str) -> str:
    """The codex TOML block of one MCP server."""
    block = f'[mcp_servers.{name}]\nurl = "{url}"\n'
    if token:
        block += f'\n[mcp_servers.{name}.http_headers]\nAuthorization = "Bearer {token}"\n'
    return block


def json_block(name: str, url: str, token: str) -> str:
    """The MCP settings snippet of one server."""
    server: dict[str, object] = {"type": "http", "url": url}
    if token:
        server["headers"] = {"Authorization": f"Bearer {token}"}
    return json.dumps({"mcpServers": {name: server}}, indent=2) + "\n"


def patch_codex(name: str, url: str, token: str, apply: bool, home: Path) -> int:
    """Patch the codex config of one home, keeping a backup and the other sections."""
    path = home / ".codex" / "config.toml"
    block = toml_block(name, url, token)
    if not path.is_file():
        print(f"no codex config at {path}; add this snippet manually:\n\n{block}")
        print_harness_snippets(name, url, token)
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
        print(f"DRY RUN — nothing written. Block that would be applied to {path}:\n")
        print(block)
        print_harness_snippets(name, url, token)
        return 0
    stamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    backup = path.with_name(f"{path.name}.bak-lhc-mcp-{stamp}")
    backup.write_text(text, encoding="utf-8")
    path.write_text(updated, encoding="utf-8")
    print(f"patched {path} (backup: {backup.name})")
    print_harness_snippets(name, url, token)
    return 0


def print_harness_snippets(name: str, url: str, token: str) -> None:
    """The snippet every other harness needs, one per harness."""
    snippet = json_block(name, url, token)
    for harness in OTHER_HARNESSES:
        print(f"snippet for {harness} (add an MCP server named {name} to its MCP settings):")
        print(snippet)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--name", default=DEFAULT_NAME,
                        help=f"MCP server name (default: {DEFAULT_NAME})")
    parser.add_argument("--url", default=None,
                        help="explicit MCP URL (wins over every environment key)")
    parser.add_argument("--url-env", default=None,
                        help="environment variable that holds the URL (default: the known keys)")
    parser.add_argument("--token-env", default=None,
                        help="environment variable that holds the Bearer token")
    parser.add_argument("--env-file", default=None,
                        help="protected env file (default: ~/.config/ask-human/env)")
    parser.add_argument("--home", default=None, help="home directory to patch (default: $HOME)")
    parser.add_argument("--apply", action="store_true", help="write the config (default: dry-run)")
    args = parser.parse_args(argv)

    home = Path(args.home).expanduser() if args.home else Path.home()
    env_file = Path(args.env_file) if args.env_file else None
    settings = merged_settings(env_file)

    url, url_key, note = resolve_endpoint(args.name, settings, args.url_env, args.url)
    if not url:
        print(
            f"FAIL: no endpoint for {args.name}. Set one of "
            f"{', '.join(url_keys(args.name))} in the environment, in "
            f"{ENV_FILE}, or in a .env file.\n"
            "Example: export LHC_ASKHUMAN_MCP_URL=\"https://notify.example/mcp\"",
            file=sys.stderr,
        )
        return 1
    token, token_key = resolve_token(args.name, settings, args.token_env)
    if url_key:
        print(f"endpoint from {url_key}" + (f" ({note})" if note else ""))
    if token and token_key:
        print(f"bearer token from {token_key}")
    elif not token:
        print("no bearer token found; the server is registered without one")
    return patch_codex(args.name, url, token, args.apply, home)


if __name__ == "__main__":
    raise SystemExit(main())
