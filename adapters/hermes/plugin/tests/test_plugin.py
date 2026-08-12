from pathlib import Path
import importlib.util
import json

SPEC = importlib.util.spec_from_file_location(
    "lhc_plugin", Path(__file__).parents[1] / "__init__.py"
)
lhc = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(lhc)


def test_marker_reader_is_outside_text_safe(tmp_path):
    (tmp_path / "AGENTS.md").write_text(
        "original\n<!-- last-human-commit:begin -->\ncanonical\n"
        "<!-- last-human-commit:end -->\ntail\n", encoding="utf-8"
    )
    assert lhc.load_marked_project_block(tmp_path).splitlines() == [
        "<!-- last-human-commit:begin -->", "canonical",
        "<!-- last-human-commit:end -->",
    ]


def test_middleware_rewrites_single_delegate_without_touching_other_tools(tmp_path, monkeypatch):
    (tmp_path / "AGENTS.md").write_text(
        "<!-- last-human-commit:begin -->\nrouter\n"
        "<!-- last-human-commit:end -->\n", encoding="utf-8"
    )
    role = tmp_path / "common/agents/Worker.md"
    role.parent.mkdir(parents=True)
    role.write_text("# Worker\ncomplete role body", encoding="utf-8")
    monkeypatch.setenv("LAST_HUMAN_COMMIT_ROOT", str(tmp_path))
    monkeypatch.chdir(tmp_path)
    result = lhc.rewrite_delegate_task(
        "delegate_task", {"goal": "[LHC_ROLE=worker] implement", "context": "facts"}
    )
    assert result is not None and "# Worker" in result["args"]["context"]
    assert result["args"]["context"].endswith("facts")
    assert lhc.rewrite_delegate_task("terminal", {"command": "echo ok"}) is None


def test_middleware_rewrites_batch_and_rejects_unknown_role():
    args = {"tasks": [{"goal": "[LHC_ROLE=coder] no-op"}]}
    result = lhc.rewrite_delegate_task("delegate_task", args)
    assert result == {"args": args}


def test_conflicting_marker_files_fail_closed(tmp_path):
    (tmp_path / "AGENTS.md").write_text(
        "<!-- last-human-commit:begin -->\na\n<!-- last-human-commit:end -->\n",
        encoding="utf-8",
    )
    (tmp_path / "CLAUDE.md").write_text(
        "<!-- last-human-commit:begin -->\nb\n<!-- last-human-commit:end -->\n",
        encoding="utf-8",
    )
    assert lhc.load_marked_project_block(tmp_path) == ""


def test_tester_is_a_known_role():
    assert lhc.ROLES["tester"] == "Tester"


def test_profile_bundle_replaces_clarify_with_ask_human_and_secret():
    base = Path(__file__).parents[2] / "profile"
    current = (base / "LHC.md").read_text(encoding="utf-8")
    versioned = (base / "LHC.v1.md").read_text(encoding="utf-8")
    assert "native `clarify` tool is disabled" in versioned
    assert "Use AskHuman" in versioned
    assert "through AskSecret/SSS" in versioned
    assert "LHC Ask Secret semantics" in versioned
    assert "Preserve Hermes native identity" in versioned
    assert "For the normative bundle content, see `LHC.v1.md`." in current
    assert "disables native `clarify`" in current
    assert "replaces it with AskHuman" in current
    assert "substitutes LHC Ask Secret semantics" in current


def test_registers_middleware_and_pre_llm_hook():
    registered = {"middleware": [], "hooks": []}

    class Context:
        def register_middleware(self, name, callback):
            registered["middleware"].append((name, callback))

        def register_hook(self, name, callback):
            registered["hooks"].append((name, callback))

    lhc.register(Context())

    assert registered["middleware"] == [("tool_request", lhc.rewrite_delegate_task)]
    assert registered["hooks"] == [("pre_llm_call", lhc.observe_pre_llm)]


def test_pre_llm_counts_each_native_summary_once_and_injects_handoff(tmp_path, monkeypatch):
    (tmp_path / ".agents").mkdir()
    source_root = Path(__file__).parents[4]
    monkeypatch.setenv("LAST_HUMAN_COMMIT_ROOT", str(source_root / "src"))
    monkeypatch.chdir(tmp_path)
    history = [
        {
            "role": "assistant",
            "content": "[CONTEXT COMPACTION — REFERENCE ONLY]\nBusiness route A",
            "_compressed_summary": True,
        }
    ]

    first = lhc.observe_pre_llm(
        session_id="hermes-one",
        user_message="continue",
        conversation_history=history,
    )
    duplicate = lhc.observe_pre_llm(
        session_id="hermes-one",
        user_message="continue",
        conversation_history=history,
    )
    history[0]["content"] += " then route B"
    second = lhc.observe_pre_llm(
        session_id="hermes-one",
        user_message="continue",
        conversation_history=history,
    )

    state_path = tmp_path / ".agents/shared-session/compaction/hermes-one/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert first is not None and "Compaction count: 1" in first["context"]
    assert duplicate is None
    assert second is not None and "Compaction count: 2" in second["context"]
    assert state["compaction_count"] == 2


def test_rotated_hermes_session_keeps_one_compaction_lineage(tmp_path, monkeypatch):
    (tmp_path / ".agents").mkdir()
    source_root = Path(__file__).parents[4]
    monkeypatch.setenv("LAST_HUMAN_COMMIT_ROOT", str(source_root / "src"))
    monkeypatch.chdir(tmp_path)

    lhc.observe_pre_llm(
        session_id="parent",
        user_message="first",
        conversation_history=[{"content": "[CONTEXT COMPACTION]\none"}],
    )
    result = lhc.observe_pre_llm(
        session_id="child",
        parent_session_id="parent",
        user_message="second",
        conversation_history=[{"content": "[CONTEXT COMPACTION]\ntwo"}],
    )

    state_path = tmp_path / ".agents/shared-session/compaction/parent/state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert result is not None and "Compaction count: 2" in result["context"]
    assert state["compaction_count"] == 2


def test_hermes_session_alias_map_is_bounded(tmp_path):
    agents_root = tmp_path / ".agents"
    agents_root.mkdir()

    for index in range(lhc._MAX_SESSION_ALIASES + 3):
        lhc._logical_session_id(agents_root, f"session-{index}", "")

    mapping = json.loads(
        (agents_root / "shared-session/compaction/hermes-session-map.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(mapping["aliases"]) == lhc._MAX_SESSION_ALIASES
    assert len(mapping["recent"]) == lhc._MAX_SESSION_ALIASES
    assert "session-0" not in mapping["aliases"]
