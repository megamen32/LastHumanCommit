#!/usr/bin/env python3
"""Install required AskSecret and AskHuman HTTP MCPs for local harnesses.

Reads capability tokens from a JSON object on stdin. Credentials are never
accepted in argv and the receipt is secret-safe.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml


ASK_SECRET_URL = "https://pswd.bezrabotnyi.com/mcp"
ASK_HUMAN_URL = "https://notify.bezrabotnyi.com/mcp"
ALIASES = {"sss", "notify", "ask-tools", "ask-secret", "ask-human", "AskSecret", "AskHuman"}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, raw = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(raw)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.replace(temporary, path)
        path.chmod(0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def mcp_entries(secret_token: str, human_token: str, style: str) -> dict[str, Any]:
    if style == "opencode":
        return {
            "AskSecret": {"type": "remote", "url": ASK_SECRET_URL, "enabled": True, "headers": {"Authorization": f"Bearer {secret_token}"}},
            "AskHuman": {"type": "remote", "url": ASK_HUMAN_URL, "enabled": True, "headers": {"Authorization": f"Bearer {human_token}"}},
        }
    if style == "claude":
        return {
            "AskSecret": {"type": "http", "url": ASK_SECRET_URL, "headers": {"Authorization": f"Bearer {secret_token}"}},
            "AskHuman": {"type": "http", "url": ASK_HUMAN_URL, "headers": {"Authorization": f"Bearer {human_token}"}},
        }
    return {
        "AskSecret": {"url": ASK_SECRET_URL, "headers": {"Authorization": f"Bearer {secret_token}"}, "enabled": True},
        "AskHuman": {"url": ASK_HUMAN_URL, "headers": {"Authorization": f"Bearer {human_token}"}, "enabled": True},
    }


def replace_json_registry(path: Path, registry_name: str, entries: dict[str, Any]) -> None:
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    registry = data.setdefault(registry_name, {})
    if not isinstance(registry, dict):
        raise ValueError(f"{path}: {registry_name} must be an object")
    for name in ALIASES:
        registry.pop(name, None)
    registry.update(entries)
    atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def replace_hermes(path: Path, entries: dict[str, Any]) -> None:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    data = data or {}
    registry = data.setdefault("mcp_servers", {})
    if not isinstance(registry, dict):
        raise ValueError(f"{path}: mcp_servers must be an object")
    for name in ALIASES:
        registry.pop(name, None)
    registry.update(entries)
    atomic_write(path, yaml.safe_dump(data, allow_unicode=True, sort_keys=False))


def replace_codex(path: Path, secret_token: str, human_token: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    names = "|".join(re.escape(name) for name in sorted(ALIASES, key=len, reverse=True))
    pattern = re.compile(rf"(?ms)^\[mcp_servers\.(?:{names})\](?:\n(?!\[)[^\n]*)*(?:\n\[mcp_servers\.(?:{names})\.[^\]]+\](?:\n(?!\[)[^\n]*)*)*\n?")
    text = pattern.sub("", text).rstrip() + "\n\n"
    for name, url, token in (("AskSecret", ASK_SECRET_URL, secret_token), ("AskHuman", ASK_HUMAN_URL, human_token)):
        text += f"[mcp_servers.{name}]\nurl = {json.dumps(url)}\n\n"
        text += f"[mcp_servers.{name}.http_headers]\nAuthorization = {json.dumps('Bearer ' + token)}\n\n"
    atomic_write(path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", type=Path, default=Path.home())
    parser.add_argument("--harness", action="append", choices=("codex", "opencode", "claude", "hermes"))
    args = parser.parse_args()
    credentials = json.load(sys.stdin)
    secret_token = str(credentials.get("ask_secret_token") or "")
    human_token = str(credentials.get("ask_human_token") or "")
    if not secret_token or not human_token:
        raise SystemExit("stdin must contain both capability tokens")
    selected = set(args.harness or ("codex", "opencode", "claude", "hermes"))
    paths: dict[str, Path] = {}
    if "codex" in selected:
        paths["codex"] = args.home / ".codex/config.toml"
        replace_codex(paths["codex"], secret_token, human_token)
    if "opencode" in selected:
        paths["opencode"] = args.home / ".config/opencode/opencode.json"
        replace_json_registry(paths["opencode"], "mcp", mcp_entries(secret_token, human_token, "opencode"))
    if "claude" in selected:
        paths["claude"] = args.home / ".claude.json"
        replace_json_registry(paths["claude"], "mcpServers", mcp_entries(secret_token, human_token, "claude"))
    if "hermes" in selected:
        paths["hermes"] = args.home / ".hermes/config.yaml"
        replace_hermes(paths["hermes"], mcp_entries(secret_token, human_token, "hermes"))
    for path in paths.values():
        if stat.S_IMODE(path.stat().st_mode) != 0o600:
            raise RuntimeError(f"{path}: expected mode 0600")
    print(json.dumps({"schema": "lhc.http-capabilities.install.v1", "status": "installed", "harnesses": sorted(paths), "servers": ["AskSecret", "AskHuman"], "credentials_logged": False}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
