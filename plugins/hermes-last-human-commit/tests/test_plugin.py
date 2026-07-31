from pathlib import Path
import importlib.util

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
    role = tmp_path / "common/agents/Worker.md"
    role.parent.mkdir(parents=True)
    role.write_text("# Worker\ncomplete role body", encoding="utf-8")
    monkeypatch.setenv("LAST_HUMAN_COMMIT_ROOT", str(tmp_path))
    lhc.load_role_prompt.cache_clear()
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
