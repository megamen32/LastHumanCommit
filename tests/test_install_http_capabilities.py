from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]


class InstallHttpCapabilitiesTests(unittest.TestCase):
    def test_installs_native_remote_entries_without_printing_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / ".codex").mkdir()
            (home / ".codex/config.toml").write_text('[mcp_servers.sss]\nurl = "old"\n', encoding="utf-8")
            (home / ".config/opencode").mkdir(parents=True)
            (home / ".config/opencode/opencode.json").write_text(json.dumps({"mcp": {"notify": {"type": "local"}}}), encoding="utf-8")
            (home / ".hermes").mkdir()
            (home / ".hermes/config.yaml").write_text("mcp_servers:\n  notify:\n    command: old\n", encoding="utf-8")
            (home / ".claude.json").write_text(json.dumps({"mcpServers": {"ask-tools": {"command": "old"}}}), encoding="utf-8")
            secret, human = "secret-fixture-token", "human-fixture-token"
            completed = subprocess.run(
                [sys.executable, str(ROOT / "scripts/install_http_capabilities.py"), "--home", str(home)],
                input=json.dumps({"ask_secret_token": secret, "ask_human_token": human}),
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertNotIn(secret, completed.stdout + completed.stderr)
            self.assertNotIn(human, completed.stdout + completed.stderr)
            receipt = json.loads(completed.stdout)
            self.assertEqual(["AskSecret", "AskHuman"], receipt["servers"])
            for path in (home / ".codex/config.toml", home / ".config/opencode/opencode.json", home / ".hermes/config.yaml", home / ".claude.json"):
                self.assertEqual(0o600, path.stat().st_mode & 0o777)
                text = path.read_text(encoding="utf-8")
                self.assertIn("AskSecret", text)
                self.assertIn("AskHuman", text)
                self.assertNotIn("ask-tools", text)
            opencode = json.loads((home / ".config/opencode/opencode.json").read_text())
            self.assertEqual("remote", opencode["mcp"]["AskSecret"]["type"])
            hermes = yaml.safe_load((home / ".hermes/config.yaml").read_text())
            self.assertEqual("https://notify.bezrabotnyi.com/mcp", hermes["mcp_servers"]["AskHuman"]["url"])


if __name__ == "__main__":
    unittest.main()
