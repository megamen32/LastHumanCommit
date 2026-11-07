"""Bugs found by the full suite on 2026-11-07, each reproduced before its fix."""
import http.server
import importlib.util
import json
import os
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_plan_mirror as mirror  # noqa: E402

spec = importlib.util.spec_from_file_location("install_runtime_found", ROOT / "plugins/last-human-commit/scripts/install_runtime.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


def test_a_slow_render_on_the_server_is_not_a_lost_snapshot(tmp_path):
    """The server renders every revision before it answers; the upload waited only as long
    as a status probe (0.15 s in tests, 3 s live) and recorded «источник недоступен»."""

    class Slow(http.server.BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers["Content-Length"]))
            time.sleep(0.6)
            body = json.dumps({"seq": 1}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Slow)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    token = tmp_path / "token"
    token.write_text("t" * 32)
    os.chmod(token, 0o600)
    cfg = {"endpoint": f"http://127.0.0.1:{server.server_address[1]}", "token_file": str(token),
           "timeout_seconds": 0.15}
    try:
        assert mirror._post_snapshot(cfg, {"identity": "x"}) == {"seq": 1}
    finally:
        server.shutdown()


def test_a_foreign_skill_link_is_kept_when_its_path_merely_passes_a_lasthumancommit_folder(tmp_path):
    """A dangling link to somewhere/else was deleted because the absolute path contained
    «LastHumanCommit» (the checkout folder), not because it pointed into an LHC package."""
    base = tmp_path / "LastHumanCommit" / "work"
    home = base / "home"
    skills = home / ".config/opencode/skills"
    skills.mkdir(parents=True)
    (skills / "foreign").symlink_to(base / "somewhere/else")
    (skills / "old-lhc").symlink_to(base / "cache/last-human-commit/1.0.0/skills/old-lhc")
    root = base / "pkg"
    (root / "common/agents").mkdir(parents=True)
    (root / "opencode").mkdir()
    (root / "scripts").mkdir()
    (root / "AGENTS.md").write_text("router")
    (root / "scripts/plan_mcp.py").write_text("")
    (root / "opencode/lhc-v2.ts").write_text("export const X = 1")
    (root / "skills/last-human-commit").mkdir(parents=True)
    (root / "skills/last-human-commit/SKILL.md").write_text("skill")
    for name in ("Lead", "Worker"):
        (root / "common/agents" / f"{name}.md").write_text(f"# {name}")
    installer.configure(home, root, "opencode")
    assert (skills / "foreign").is_symlink()
    assert not (skills / "old-lhc").is_symlink()
