"""Build modes must be explicit, and neither mode drops the delivery protocol."""
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("pr_stage_publisher", ROOT / "scripts/publish_package.py")
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


def test_both_generated_protocol_modes_are_valid():
    for stage in ("on", "off"):
        data = json.loads(publisher.workflow_config_bytes(stage))
        assert data == {"pr_stage": stage}
        router = (ROOT / "AGENTS.md").read_text()
        protocol = (ROOT / "src/common/protocols/SHARED_WORKTREE.md").read_text()
        assert "pr_stage" in router and "pr_stage" in protocol
        assert "merge" in router.lower() and "deploy" in router.lower()
        assert "PR" in protocol


def test_generated_package_protocols_on_and_off(tmp_path, monkeypatch):
    import sys
    for stage in ("on", "off"):
        project = tmp_path / stage
        package = project / "plugins/last-human-commit"
        (project / "src/common/config").mkdir(parents=True)
        (project / "adapters/codex/hooks").mkdir(parents=True)
        (package / "hooks").mkdir(parents=True)
        (project / "AGENTS.md").write_text((ROOT / "AGENTS.md").read_text())
        (project / "src/common/config/workflow.json").write_text('{"pr_stage":"on"}')
        (project / "adapters/codex/hooks/hooks.json").write_text('{"hooks":{}}')
        (package / "hooks/hooks.json").write_text('{"hooks":{}}')
        monkeypatch.setattr(publisher, "ROOT", project)
        monkeypatch.setattr(publisher, "PACKAGE", package)
        monkeypatch.setattr(publisher, "NATIVE", package / "native/codex")
        monkeypatch.setattr(publisher, "WORKFLOW_SOURCE", project / "src/common/config/workflow.json")
        monkeypatch.setattr(publisher, "TOOL_COPIES", ())
        monkeypatch.setattr(publisher, "TREE_FOLDERS", ())
        monkeypatch.setattr(publisher, "COPIES", (
            ("AGENTS.md", "plugins/last-human-commit/AGENTS.md", ()),
        ))
        monkeypatch.setattr(sys, "argv", ["publish_package.py", "--pr-stage", stage])
        assert publisher.main() == 0
        for root in (package, package / "native/codex"):
            assert json.loads((root / "config/workflow.json").read_text()) == {"pr_stage": stage}
        protocol = (package / "AGENTS.md").read_text()
        assert "pr_stage" in protocol and "PR-off" in protocol
        assert "integrat" in protocol and "deploy" in protocol
        monkeypatch.setattr(sys, "argv", ["publish_package.py", "--check", "--pr-stage", stage])
        assert publisher.main() == 0
        other = "off" if stage == "on" else "on"
        monkeypatch.setattr(sys, "argv", ["publish_package.py", "--check", "--pr-stage", other])
        assert publisher.main() == 1
