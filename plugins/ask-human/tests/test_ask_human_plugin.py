"""The tests of the Ask Human plugin: no network, no real recipient.

A local HTTP server on 127.0.0.1 stands in for the Notice Place service, so
the delivery path is exercised for real while the Telegram side stays out of
it.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPTS = PLUGIN / "scripts"
sys.path.insert(0, str(SCRIPTS))

import ask_human_hook as hook  # noqa: E402
import setup_mcp  # noqa: E402

HOOK = SCRIPTS / "ask_human_hook.py"

PERMISSION_PAYLOAD = {
    "hook_event_name": "PermissionRequest",
    "session_id": "sess-42",
    "cwd": "/tmp/work",
    "model": "gpt-5",
    "permission_mode": "default",
    "turn_id": "turn-1",
    "transcript_path": None,
    "tool_name": "Bash",
    "tool_input": {"command": "rm -rf /tmp/scratch", "justification": "clean the scratch dir"},
}


# ---------------------------------------------------------------------------
# the local stand-in for the Notice Place service
# ---------------------------------------------------------------------------


class Service:
    """A local stand-in for the human-request intake."""

    def __init__(self, state: str = "resolved", answer: str = "yes, go ahead"):
        self.state = state
        self.answer = answer
        self.requests: list[tuple[str, str, dict, bytes]] = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep the test output clean
                pass

            def _record(self):
                length = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(length) if length else b""
                owner.requests.append((self.command, self.path, dict(self.headers), body))

            def _reply(self, status: int, payload: dict):
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_POST(self):
                self._record()
                body = json.loads(owner.requests[-1][3] or b"{}")
                self._reply(201, {"schema": "ask_human.response.v1", "state": "pending",
                                  "request_id": body.get("request_id")})

            def do_GET(self):
                self._record()
                self._reply(200, {"schema": "ask_human.response.v1", "state": owner.state,
                                  "response_value": owner.answer if owner.state == "resolved" else None,
                                  "response_actor": "telegram:42" if owner.state == "resolved" else None})

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    def __enter__(self) -> "Service":
        self.thread.start()
        return self

    def __exit__(self, *exc):
        self.server.shutdown()
        self.server.server_close()

    @property
    def url(self) -> str:
        host, port = self.server.server_address[:2]
        return f"http://{host}:{port}/v1/human-requests"

    def created(self) -> dict:
        """The body of the create call."""
        for method, path, _headers, body in self.requests:
            if method == "POST" and path.endswith("/v1/human-requests"):
                return json.loads(body)
        raise AssertionError("the hook never created a human request")


def run_hook(payload: dict, service_url: str, tmp_path: Path, timeout: str = "5",
             extra_env: dict | None = None) -> tuple[dict, str]:
    """Run the hook as the harness runs it, and return its stdout."""
    env_file = tmp_path / "env"
    env_file.write_text("", encoding="utf-8")
    env = {
        "PATH": os.environ.get("PATH", ""),
        "ASK_HUMAN_URL": service_url,
        "NOTIFY_CENTER_TOKEN": "test-token",
        "NOTIFY_CENTER_PROJECT": "test-project",
        "NOTIFY_CENTER_RECIPIENT": "operator",
        "ASK_HUMAN_ALLOWED_ACTORS": "telegram:42",
        "ASK_HUMAN_HOOK_TIMEOUT": timeout,
    }
    env.update(extra_env or {})
    result = subprocess.run(
        [sys.executable, str(HOOK), "--event", "PermissionRequest",
         "--env-file", str(env_file)],
        input=json.dumps(payload), capture_output=True, text=True, env=env, timeout=60,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip(), "the hook printed nothing"
    return json.loads(result.stdout), result.stdout


# ---------------------------------------------------------------------------
# the question
# ---------------------------------------------------------------------------


def test_the_permission_request_payload_yields_the_question():
    question = hook.extract_question(PERMISSION_PAYLOAD, "PermissionRequest")
    assert question["mode"] == "question"
    assert "Bash" in question["text"]
    assert "rm -rf /tmp/scratch" in question["text"]
    assert "clean the scratch dir" in question["text"]
    assert question["tool_name"] == "Bash"


def test_the_question_names_the_arguments_the_human_needs():
    question = hook.extract_question(
        {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x", "content": "hello"}},
        "PermissionRequest")
    assert "file_path: /tmp/x" in question["text"]
    assert "content: hello" in question["text"]


def test_offered_choices_become_a_choice_question():
    payload = dict(PERMISSION_PAYLOAD)
    payload["permission_suggestions"] = [{"label": "allow it", "mode": "allow"},
                                          {"label": "do not", "mode": "deny"}]
    question = hook.extract_question(payload, "PermissionRequest")
    assert question["mode"] == "choice"
    assert question["choices"] == [{"label": "allow it", "value": "allow"},
                                   {"label": "do not", "value": "deny"}]


def test_one_suggestion_is_not_a_choice_question():
    payload = dict(PERMISSION_PAYLOAD)
    payload["permission_suggestions"] = [{"label": "allow it", "mode": "allow"}]
    question = hook.extract_question(payload, "PermissionRequest")
    assert question["mode"] == "question"


def test_a_refusal_is_told_apart_from_an_approval():
    assert hook.is_denial("no, do not run that", hook.DEFAULT_DENY_WORDS)
    assert hook.is_denial("НЕТ, не надо", hook.DEFAULT_DENY_WORDS)
    assert hook.is_denial("stop", hook.DEFAULT_DENY_WORDS)
    assert not hook.is_denial("yes, go ahead", hook.DEFAULT_DENY_WORDS)
    assert not hook.is_denial("nothing to refuse here", hook.DEFAULT_DENY_WORDS)


# ---------------------------------------------------------------------------
# the delivery
# ---------------------------------------------------------------------------


def test_the_question_goes_to_the_intake_and_the_answer_comes_back(tmp_path):
    with Service(answer="yes, go ahead") as service:
        output, _raw = run_hook(PERMISSION_PAYLOAD, service.url, tmp_path)

    created = service.created()
    assert created["schema"] == "ask_human.request.v1"
    assert created["project"] == "test-project"
    assert created["recipient"] == "operator"
    assert created["allowed_actors"] == ["telegram:42"]
    assert created["mode"] == "question"
    assert "Bash" in created["message"]
    assert created["request_id"].startswith("ask-")

    method, path, headers, _body = service.requests[0]
    assert method == "POST" and path.endswith("/v1/human-requests")
    assert headers["Authorization"] == "Bearer test-token"
    assert headers["Content-Type"] == "application/json"
    assert headers["Idempotency-Key"] == f"human-request:{created['request_id']}"

    assert output["continue"] is True
    assert output["systemMessage"] == "Ask Human: yes, go ahead"
    decision = output["hookSpecificOutput"]
    assert decision["hookEventName"] == "PermissionRequest"
    assert decision["decision"]["behavior"] == "allow"
    # the reserved fields of the decision fail the hook closed, so they stay out
    assert set(decision["decision"]) == {"behavior"}


def test_a_refusal_does_not_allow_the_tool(tmp_path):
    with Service(answer="no, do not run that") as service:
        output, _raw = run_hook(PERMISSION_PAYLOAD, service.url, tmp_path)
    assert output["hookSpecificOutput"]["decision"]["behavior"] == "deny"
    assert output["hookSpecificOutput"]["decision"]["message"] == "no, do not run that"


def test_the_answer_is_read_from_the_request_itself(tmp_path):
    with Service(answer="proceed") as service:
        output, _raw = run_hook(PERMISSION_PAYLOAD, service.url, tmp_path)
        reads = [path for method, path, _h, _b in service.requests if method == "GET"]
    assert reads and reads[0].endswith("/" + service.created()["request_id"])
    assert output["systemMessage"] == "Ask Human: proceed"


def test_without_an_answer_the_hook_says_so_instead_of_printing_nothing(tmp_path):
    with Service(state="pending") as service:
        output, _raw = run_hook(PERMISSION_PAYLOAD, service.url, tmp_path, timeout="1")
    assert output["continue"] is True
    assert "no answer yet" in output["systemMessage"]
    assert service.created()["request_id"] in output["systemMessage"]
    assert "hookSpecificOutput" not in output


def test_a_broken_configuration_fails_open_with_a_message(tmp_path):
    env_file = tmp_path / "env"
    env_file.write_text("", encoding="utf-8")
    env = {"PATH": os.environ.get("PATH", "")}
    result = subprocess.run(
        [sys.executable, str(HOOK), "--event", "PermissionRequest", "--env-file", str(env_file)],
        input=json.dumps(PERMISSION_PAYLOAD), capture_output=True, text=True, env=env, timeout=60,
    )
    assert result.returncode == 0
    output = json.loads(result.stdout)
    assert output["continue"] is True
    assert "could not be reached" in output["systemMessage"]


def test_an_unreachable_service_fails_open_with_a_message(tmp_path):
    output, _raw = run_hook(PERMISSION_PAYLOAD, "http://127.0.0.1:1/v1/human-requests", tmp_path)
    assert output["continue"] is True
    assert "could not be reached" in output["systemMessage"]


def test_the_events_url_is_rewritten_to_the_human_request_intake():
    base = "http://127.0.0.1" + ":8091"
    assert hook.human_requests_url(base + "/v1/events") == base + "/v1/human-requests"
    assert hook.human_requests_url(base + "/v1/human-requests") == base + "/v1/human-requests"


def test_the_protected_env_file_is_read_when_the_process_has_nothing(tmp_path, monkeypatch):
    env_file = tmp_path / "env"
    intake = "http://127.0.0.1" + ":8091/v1/human-requests"
    env_file.write_text(
        f"ASK_HUMAN_URL={intake}\n"
        "NOTIFY_CENTER_TOKEN=file-token\n"
        "NOTIFY_CENTER_PROJECT=file-project\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("ASK_HUMAN_URL", raising=False)
    monkeypatch.delenv("NOTIFY_CENTER_TOKEN", raising=False)
    monkeypatch.delenv("NOTIFY_CENTER_PROJECT", raising=False)
    settings = hook.resolve_settings(env_file)
    assert settings["endpoint"] == intake
    assert settings["token"] == "file-token"
    assert settings["project"] == "file-project"


# ---------------------------------------------------------------------------
# the registration
# ---------------------------------------------------------------------------


def test_the_dry_run_writes_nothing(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    config.write_text('[model]\nname = "gpt-5"\n', encoding="utf-8")
    before = hashlib.sha256(config.read_bytes()).hexdigest()

    code = setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp"])
    out = capsys.readouterr().out
    assert code == 0
    assert hashlib.sha256(config.read_bytes()).hexdigest() == before
    assert list(home.rglob("*.bak-lhc-mcp-*")) == []
    assert "DRY RUN" in out
    assert "[mcp_servers.AskHuman]" in out


def test_the_apply_patches_codex_and_keeps_a_backup_and_the_other_sections(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    original = '[model]\nname = "gpt-5"\n\n[mcp_servers.Other]\nurl = "https://other.example/mcp"\n'
    config.write_text(original, encoding="utf-8")

    code = setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp",
                           "--token-env", "TEST_TOKEN", "--apply"])
    capsys.readouterr()
    assert code == 0

    backups = list((home / ".codex").glob("config.toml.bak-lhc-mcp-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == original


def test_the_apply_writes_the_section_with_the_token(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("TEST_TOKEN", "secret-token")
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    config.write_text('[model]\nname = "gpt-5"\n\n[mcp_servers.Other]\nurl = "https://other.example/mcp"\n',
                      encoding="utf-8")

    code = setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp",
                           "--token-env", "TEST_TOKEN", "--apply"])
    capsys.readouterr()
    assert code == 0
    text = config.read_text(encoding="utf-8")
    assert '[mcp_servers.AskHuman]' in text
    assert 'url = "https://notify.example/mcp"' in text
    assert 'Authorization = "Bearer secret-token"' in text
    # the sections of other servers are untouched
    assert '[mcp_servers.Other]' in text
    assert 'url = "https://other.example/mcp"' in text
    assert text.index("[model]") < text.index("[mcp_servers.AskHuman]")


def test_the_apply_replaces_only_its_own_section(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    config = home / ".codex" / "config.toml"
    config.write_text('[mcp_servers.AskHuman]\nurl = "https://old.example/mcp"\n\n'
                      '[mcp_servers.Other]\nurl = "https://other.example/mcp"\n', encoding="utf-8")
    setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp", "--apply"])
    capsys.readouterr()
    text = config.read_text(encoding="utf-8")
    assert "https://old.example/mcp" not in text
    assert "https://notify.example/mcp" in text
    assert '[mcp_servers.Other]' in text


def test_the_endpoint_is_found_in_the_protected_env_file(tmp_path, monkeypatch, capsys):
    base = "http://127.0.0.1" + ":8091"
    env_file = tmp_path / "env"
    env_file.write_text(f"ASK_HUMAN_URL={base}/v1/human-requests\n", encoding="utf-8")
    for key in ("LHC_ASKHUMAN_MCP_URL", "ASK_HUMAN_MCP_URL", "ASK_HUMAN_URL"):
        monkeypatch.delenv(key, raising=False)
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    code = setup_mcp.main(["--home", str(home), "--env-file", str(env_file)])
    out = capsys.readouterr().out
    assert code == 0
    # the human-request intake is not the MCP endpoint, so the MCP URL is derived
    assert base + "/mcp" in out
    assert "derived from ASK_HUMAN_URL" in out


def test_without_any_endpoint_the_script_says_so(tmp_path, monkeypatch, capsys):
    for key in ("LHC_ASKHUMAN_MCP_URL", "ASK_HUMAN_MCP_URL", "ASK_HUMAN_URL"):
        monkeypatch.delenv(key, raising=False)
    env_file = tmp_path / "env"
    env_file.write_text("", encoding="utf-8")
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    code = setup_mcp.main(["--home", str(home), "--env-file", str(env_file)])
    assert code == 1
    assert "FAIL" in capsys.readouterr().err


def test_every_other_harness_gets_its_snippet(tmp_path, capsys):
    home = tmp_path / "home"
    (home / ".codex").mkdir(parents=True)
    setup_mcp.main(["--home", str(home), "--url", "https://notify.example/mcp"])
    out = capsys.readouterr().out
    for harness in setup_mcp.OTHER_HARNESSES:
        assert f"snippet for {harness}" in out
    assert '"AskHuman"' in out
    assert '"type": "http"' in out


# ---------------------------------------------------------------------------
# the manifests
# ---------------------------------------------------------------------------


def test_the_manifests_declare_the_server_the_way_the_harnesses_read_it():
    codex = json.loads((PLUGIN / ".codex-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert codex["name"] == "ask-human"
    assert codex["version"] == "1.0.0"
    assert codex["mcpServers"] == "./.mcp.json"
    assert codex["hooks"] == "./hooks/hooks.json"
    server = json.loads((PLUGIN / ".mcp.json").read_text(encoding="utf-8"))["mcpServers"]["AskHuman"]
    assert server["type"] == "http"
    assert server["url"].endswith("/mcp")
    # the credential is the name of an environment variable, never a value
    assert server["bearer_token_env_var"] == "NOTIFY_CENTER_TOKEN"
    assert "headers" not in server


def test_the_root_manifest_keeps_the_agent_plugin_shape():
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "ask-human"
    assert manifest["version"] == "1.0.0"
    assert manifest["extensions"]["com.openai"]["hooks"] == "./hooks/hooks.json"
    assert "mcpServers" not in manifest


def test_the_hook_manifest_registers_the_permission_request():
    hooks = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    entry = hooks["hooks"]["PermissionRequest"][0]["hooks"][0]
    assert entry["type"] == "command"
    assert "ask_human_hook.py" in entry["command"]
    assert 0 < entry["timeout"] <= 300


# ---------------------------------------------------------------------------
# the secrets
# ---------------------------------------------------------------------------


def _plugin_files() -> list[Path]:
    return [path for path in PLUGIN.rglob("*") if path.is_file()]


def test_the_plugin_holds_no_token():
    pattern = re.compile(r"Bearer\s+[A-Za-z0-9._-]{16,}")
    for path in _plugin_files():
        if path.suffix in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not pattern.search(text), f"a token leaked in {path.name}"


def test_the_plugin_holds_no_long_hex_secret():
    pattern = re.compile(r"\b[0-9a-f]{32,}\b")
    for path in _plugin_files():
        if path.suffix in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert not pattern.search(text), f"a hex secret leaked in {path.name}"


def test_the_plugin_holds_no_absolute_host_path():
    needles = ("/" + "Users" + "/", "/" + "home" + "/", "/" + "root" + "/")
    for path in _plugin_files():
        if path.suffix in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for needle in needles:
            assert needle not in text, f"an absolute host path leaked in {path.name}"


def test_the_plugin_holds_no_ask_human_url_of_one_host():
    needle = "127.0.0.1" + ":8091"
    for path in _plugin_files():
        if path.suffix in {".pyc"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        assert needle not in text, f"a host endpoint leaked in {path.name}"
