"""Native LHC activation must be instruction-only and state-free."""

from __future__ import annotations

import builtins
import importlib.util
import io
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "src/common/tools/lhc_entry.py"
HOOK_CONFIGS = (
    ROOT / "plugins/last-human-commit/hooks/hooks.json",
    ROOT / "plugins/last-human-commit/native/codex/hooks/hooks.json",
)
SUPPLEMENTAL_HOOK_CONFIGS = (
    ROOT / "plugins/last-human-commit/hooks/zcode-hooks.json",
    ROOT / "plugins/last-human-commit/native/codex/hooks/zcode-hooks.json",
)


@pytest.mark.parametrize("config_path", HOOK_CONFIGS)
def test_native_hook_templates_register_only_instruction_lifecycle(config_path: Path) -> None:
    hooks = json.loads(config_path.read_text(encoding="utf-8"))["hooks"]
    assert set(hooks) == {"SessionStart", "PostCompact", "PostToolUse"}
    for event in ("SessionStart", "PostCompact"):
        for registrations in (hooks[event],):
            for registration in registrations:
                command = registration["hooks"][0]["command"]
                assert "--instructions-only" in command
    for registration in hooks["PostToolUse"]:
        command = registration["hooks"][0]["command"]
        assert "--heartbeat-only" in command
        assert "--instructions-only" not in command


@pytest.mark.parametrize("config_path", SUPPLEMENTAL_HOOK_CONFIGS)
def test_zcode_hook_templates_allow_only_instruction_and_time_events(config_path: Path) -> None:
    hooks = json.loads(config_path.read_text(encoding="utf-8"))["hooks"]
    assert set(hooks) == {"SessionStart", "PostCompact", "PostToolUse"}
    assert "--instructions-only" in hooks["SessionStart"][0]["hooks"][0]["command"]
    assert "--instructions-only" in hooks["PostCompact"][0]["hooks"][0]["command"]
    assert "--heartbeat-only" in hooks["PostToolUse"][0]["hooks"][0]["command"]


def test_opencode_compatibility_adapters_are_inert_and_config_is_skills_only(tmp_path: Path) -> None:
    import importlib.util

    script = ROOT / "plugins/last-human-commit/scripts/opencode-config.py"
    spec = importlib.util.spec_from_file_location("lhc_opencode_config_test", script)
    assert spec is not None and spec.loader is not None
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    for output_format in ("native", "v2"):
        config = config_module.build_config(ROOT / "plugins/last-human-commit", output_format)
        assert "plugin" not in config and "plugins" not in config
        assert "skills" in config
    assert "ctx.session.hook" not in (ROOT / "plugins/last-human-commit/opencode/lhc-v2.ts").read_text()
    assert "ctx.tool.hook" not in (ROOT / "plugins/last-human-commit/opencode/lhc-v2.ts").read_text()
    validator = ROOT / "plugins/last-human-commit/scripts/validate.py"
    sys.path.insert(0, str(validator.parent))
    validator_spec = importlib.util.spec_from_file_location("lhc_opencode_validator_test", validator)
    assert validator_spec is not None and validator_spec.loader is not None
    validator_module = importlib.util.module_from_spec(validator_spec)
    validator_spec.loader.exec_module(validator_module)
    validator_module.check_opencode_helper(ROOT / "plugins/last-human-commit")


def test_legacy_opencode_migration_removes_but_never_readds_lhc_adapter(tmp_path: Path) -> None:
    import subprocess

    home = tmp_path / "home"
    config = home / ".config/opencode/opencode.json"
    config.parent.mkdir(parents=True)
    config.write_text(json.dumps({"plugin": ["/old/lhc-time-guard.ts", "other-plugin"]}), encoding="utf-8")
    subprocess.run([
        sys.executable,
        str(ROOT / "plugins/last-human-commit/scripts/migrate_registration.py"),
        "--plugin-root", str(ROOT / "plugins/last-human-commit"),
        "--home", str(home), "--backup-root", str(tmp_path / "backup"), "--apply",
    ], check=True, capture_output=True, text=True)
    migrated = json.loads(config.read_text(encoding="utf-8"))
    assert migrated["plugin"] == ["other-plugin"]


def test_hermes_keeps_only_explicit_role_middleware() -> None:
    for index, adapter in enumerate((
        ROOT / "adapters/hermes/plugin/__init__.py",
        ROOT / "plugins/last-human-commit/com.nousresearch.hermes/__init__.py",
    )):
        spec = importlib.util.spec_from_file_location(f"lhc_hermes_instruction_test_{index}", adapter)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        registrations = {"middleware": [], "hooks": []}

        class Context:
            def register_middleware(self, name, callback):
                registrations["middleware"].append((name, callback))

            def register_hook(self, name, callback):
                registrations["hooks"].append((name, callback))

        module.register(Context())
        assert registrations["middleware"] == [("tool_request", module.rewrite_delegate_task)]
        assert registrations["hooks"] == []
        assert "hooks:" not in (adapter.parent / "plugin.yaml").read_text()


def _time_guard():
    spec = importlib.util.spec_from_file_location("lhc_time_guard_heartbeat_test", ROOT / "src/common/tools/lhc_time_guard.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_native_heartbeat_initializes_only_its_timer_record_and_deduplicates_due_ids(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    guard = _time_guard()
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)

    initial = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start)
    assert initial is not None and initial["due"] == [] and initial["prompt"] == ""
    state_path = Path(initial["state"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert set(state) <= {"native_heartbeat", "schema_version", "started_at",
                          "clock_source", "due_at", "last_observed_at", "last_checkpoint"}
    assert not {"business", "outcome", "milestone"} & set(state)
    assert state["native_heartbeat"]["cwd"] == str(tmp_path.resolve())

    due_30 = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=30))
    again_30 = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=31))
    assert due_30["due"] == ["plan:1"]
    assert "30-minute plan report" in due_30["prompt"]
    assert "PLAN_REPORT.md" in due_30["prompt"]
    assert again_30["due"] == [] and again_30["prompt"] == ""

    due_60 = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=60))
    assert due_60["due"] == ["plan:2", "goal:1"]
    assert "original direct user goal" in due_60["prompt"]
    saved = json.loads(state_path.read_text(encoding="utf-8"))["native_heartbeat"]
    assert saved["last_plan_bucket"] == 2 and saved["last_goal_bucket"] == 1

    due_90 = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=90))
    due_120 = guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=120))
    assert due_90["due"] == ["plan:3"]
    assert due_120["due"] == ["plan:4", "goal:2"]
    assert guard.native_heartbeat(tmp_path, "codex", "sid-1", now=start + timedelta(minutes=121))["due"] == []


def test_native_heartbeat_combines_overdue_reminders_and_preserves_outcome_and_hold(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    guard = _time_guard()
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    initial = guard.native_heartbeat(tmp_path, "codex", "sid-2", now=start)
    state_path = Path(initial["state"])
    state = json.loads(state_path.read_text(encoding="utf-8"))
    state["business"] = {"outcome": {"task_class": "quickfix", "revision": 3, "stages": {"technical": {"status": "pending"}}}}
    state["native_entry"] = {"finish_hold": "Interrupt", "stop_prompt": {"text": "held"}}
    state_path.write_text(json.dumps(state), encoding="utf-8")

    skipped = guard.native_heartbeat(tmp_path, "codex", "sid-2", now=start + timedelta(minutes=61))
    assert skipped is None
    held = json.loads(state_path.read_text(encoding="utf-8"))
    assert held["business"] == state["business"]
    assert held["native_entry"] == state["native_entry"]
    assert held["native_heartbeat"]["last_plan_bucket"] == 0
    assert held["native_heartbeat"]["last_goal_bucket"] == 0

    state["native_entry"] = {}
    state_path.write_text(json.dumps(state), encoding="utf-8")
    due = guard.native_heartbeat(tmp_path, "codex", "sid-2", now=start + timedelta(minutes=61))
    assert due["due"] == ["plan:2", "goal:1"]
    assert "30-minute" in due["prompt"] and "60-minute" in due["prompt"]
    after = json.loads(state_path.read_text(encoding="utf-8"))
    assert after["business"] == state["business"]
    assert after["native_heartbeat"]["last_plan_bucket"] == 2
    assert after["native_heartbeat"]["last_goal_bucket"] == 1

    state["native_entry"] = {"stop_prompt": {"text": "old automatic continuation notice"}}
    state["native_heartbeat"]["last_plan_bucket"] = 0
    state["native_heartbeat"]["last_goal_bucket"] = 0
    state_path.write_text(json.dumps(state), encoding="utf-8")
    reminder = guard.native_heartbeat(tmp_path, "codex", "sid-2", now=start + timedelta(minutes=61))
    assert reminder["due"] == ["plan:2", "goal:1"]
    after_notice = json.loads(state_path.read_text(encoding="utf-8"))
    assert after_notice["native_entry"] == state["native_entry"]
    assert after_notice["business"] == state["business"]


@pytest.mark.parametrize("cwd,session_id", [
    (Path("relative/path"), "sid"),
    (Path("/definitely/not/a/native/cwd"), "sid"),
    (Path("/tmp"), "unknown-session"),
    (Path("/tmp"), ""),
])
def test_native_heartbeat_rejects_unvalidated_identity_without_state(cwd: Path, session_id: str, tmp_path: Path) -> None:
    guard = _time_guard()
    if cwd == Path("/tmp"):
        cwd = tmp_path
    assert guard.native_heartbeat(cwd, "codex", session_id) is None
    assert list(tmp_path.iterdir()) == []


def test_native_heartbeat_rejects_cwd_mismatch_and_malformed_existing_state(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    guard = _time_guard()
    start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)
    initial = guard.native_heartbeat(tmp_path, "codex", "sid-cwd", now=start)
    subdir = tmp_path / "nested"
    subdir.mkdir()
    assert guard.native_heartbeat(subdir, "codex", "sid-cwd", now=start + timedelta(minutes=1)) is None

    malformed = tmp_path / "malformed"
    malformed.mkdir()
    subprocess.run(["git", "init", "-q", str(malformed)], check=True)
    path = guard.learning_path(malformed, "codex", "sid-bad-json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")
    original = path.read_bytes()
    assert guard.native_heartbeat(malformed, "codex", "sid-bad-json", now=start) is None
    assert path.read_bytes() == original

    for index, invalid_row in enumerate((
        {"business": []},
        {"native_entry": []},
        {"milestone": []},
        {"native_heartbeat": []},
    )):
        session_id = f"sid-malformed-{index}"
        row_path = guard.learning_path(malformed, "codex", session_id)
        row_path.write_text(json.dumps(invalid_row), encoding="utf-8")
        row_bytes = row_path.read_bytes()
        assert guard.native_heartbeat(malformed, "codex", session_id, now=start) is None
        assert row_path.read_bytes() == row_bytes


def test_instruction_only_branch_does_not_import_or_touch_state(tmp_path: Path, monkeypatch, capsys) -> None:
    spec = importlib.util.spec_from_file_location("lhc_entry_instructions_test", ENTRY)
    assert spec is not None and spec.loader is not None
    entry = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(entry)

    original_import = builtins.__import__

    def guarded_import(name, *args, **kwargs):
        if name in {"lhc_time_guard", "lhc_outcome", "lhc_milestone"}:
            raise AssertionError(f"instructions-only path imported {name}")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", guarded_import)
    monkeypatch.setattr(sys, "argv", [str(ENTRY), "--root", str(tmp_path), "--event", "SessionStart", "--instructions-only"])
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps({"cwd": str(tmp_path)})))
    entry.main()

    output = json.loads(capsys.readouterr().out)
    context = output["hookSpecificOutput"]["additionalContext"]
    assert context == f"LHC: read {tmp_path.resolve() / 'AGENTS.md'} for current instructions."
    assert list(tmp_path.iterdir()) == []


def test_post_compact_instruction_only_uses_the_same_side_effect_free_path(tmp_path: Path) -> None:
    import subprocess

    completed = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(tmp_path), "--event", "PostCompact", "--instructions-only"],
        input="{}",
        text=True,
        capture_output=True,
        check=True,
    )
    result = json.loads(completed.stdout)
    assert result["hookSpecificOutput"]["hookEventName"] == "PostCompact"
    assert result["hookSpecificOutput"]["additionalContext"] == f"LHC: read {tmp_path.resolve() / 'AGENTS.md'} for current instructions."
    assert list(tmp_path.iterdir()) == []


def test_post_tool_heartbeat_cli_creates_only_validated_timer_state(tmp_path: Path) -> None:
    import subprocess

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    completed = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(tmp_path), "--event", "PostToolUse", "--heartbeat-only"],
        input=json.dumps({"cwd": str(tmp_path), "session_id": "native-sid"}),
        text=True,
        capture_output=True,
        check=True,
    )
    assert completed.stdout == ""
    states = list((tmp_path / ".agents/shared-session/learning").glob("*.json"))
    assert len(states) == 1
    state = json.loads(states[0].read_text(encoding="utf-8"))
    assert set(state) == {"native_heartbeat"}
    assert state["native_heartbeat"]["session_id"] == "native-sid"


@pytest.mark.parametrize("event", ["UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop", "Interrupt", "SessionEnd"])
def test_legacy_control_event_invocation_is_inert_without_flag(tmp_path: Path, event: str) -> None:
    import subprocess

    completed = subprocess.run(
        [sys.executable, str(ENTRY), "--root", str(tmp_path), "--event", event],
        input=json.dumps({"cwd": str(tmp_path), "session_id": "legacy-session", "prompt": "Build and deploy an app"}),
        text=True,
        capture_output=True,
        check=True,
    )
    assert completed.stdout == ""
    assert list(tmp_path.iterdir()) == []

