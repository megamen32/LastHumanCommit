"""The OpenCode installer deletes what an older install wrote, and only that."""
import importlib.util
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("install_runtime_prune", ROOT / "plugins/last-human-commit/scripts/install_runtime.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

ORCHESTRATOR = "---\ndescription: LastHumanCommit Orchestrator: carries sessions.\nmode: primary\n---\n\n# Orchestrator\n"


def package(tmp_path, skills=("plan", "release")):
    root = tmp_path / "pkg"
    (root / "common/agents").mkdir(parents=True, exist_ok=True)
    (root / "opencode").mkdir(exist_ok=True)
    (root / "scripts").mkdir(exist_ok=True)
    (root / "AGENTS.md").write_text("router")
    (root / "scripts/plan_mcp.py").write_text("")
    (root / "opencode/lhc-v2.ts").write_text("export const X = 1")
    (root / "skills/last-human-commit").mkdir(parents=True, exist_ok=True)
    (root / "skills/last-human-commit/SKILL.md").write_text("skill")
    for name in ("Lead", "Worker"):
        (root / "common/agents" / f"{name}.md").write_text(f"# {name}")
    for name in skills:
        (root / "skills" / name).mkdir(parents=True, exist_ok=True)
        (root / "skills" / name / "SKILL.md").write_text(name)
    return root


def test_first_install_removes_only_the_known_list_and_a_manifest_removes_the_rest_later(tmp_path):
    home = tmp_path / "home"
    config = home / ".config/opencode"
    (config / "agents").mkdir(parents=True)
    (config / "plugin").mkdir(parents=True)
    (config / "skills").mkdir(parents=True)
    (config / "agents/orchestrator.md").write_text(ORCHESTRATOR)
    (config / "agents/foo.md").write_text("---\ndescription: mine\n---\n")
    (config / "plugin/lhc-old.ts").write_text("old")
    (config / "plugin/other.ts").write_text("mine")
    (config / "skills/gone").symlink_to(tmp_path / "old/last-human-commit/1.0.0/skills/gone")
    (config / "skills/foreign-dangling").symlink_to(tmp_path / "somewhere/else")
    (config / "skills/own").mkdir()
    root = package(tmp_path)
    result = installer.configure(home, root, "opencode")
    removed = {Path(p).name for p in result["removed"]}
    assert removed == {"orchestrator.md", "lhc-old.ts", "gone"}, result
    assert not (config / "agents/orchestrator.md").exists()
    assert (config / "agents/foo.md").read_text().startswith("---")
    assert (config / "plugin/other.ts").exists() and (config / "skills/foreign-dangling").is_symlink() and (config / "skills/own").is_dir()
    assert (config / "agents/lead.md").is_file() and (config / "plugin/lhc-v2.ts").is_file()
    backups = [p.read_text() for p in (home / ".local/state/last-human-commit/backups").glob("*-removed-orchestrator.md*")]
    assert backups and "Orchestrator" in backups[0]
    manifest = json.loads((home / ".local/state/last-human-commit/install-manifest-opencode.json").read_text())
    names = {Path(r["path"]).name for r in manifest["files"]}
    assert {"lead.md", "worker.md", "lhc-v2.ts", "plan", "release"} <= names and all(r["sha256"] for r in manifest["files"])
    # the next package has no 'release' skill and no Worker profile: both are deleted by the manifest diff
    (config / "agents/own-edited.md").write_text("mine")
    (root / "common/agents/Worker.md").unlink()
    (root / "skills/release/SKILL.md").unlink()
    (root / "skills/release").rmdir()
    again = installer.configure(home, root, "opencode")
    assert {Path(p).name for p in again["removed"]} == {"release", "worker.md"}, again
    assert (config / "agents/own-edited.md").exists() and (config / "agents/foo.md").exists()


def test_a_listed_file_the_owner_edited_is_kept(tmp_path):
    home = tmp_path / "home"
    root = package(tmp_path)
    installer.configure(home, root, "opencode")
    agent = home / ".config/opencode/agents/worker.md"
    agent.write_text(agent.read_text() + "\nmy edit\n")
    (root / "common/agents/Worker.md").unlink()
    result = installer.configure(home, root, "opencode")
    assert result["removed"] == [] and agent.exists()
    assert str(agent) in result["plugin"]["kept_modified"]

