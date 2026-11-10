"""Subagents are on unless refused: the priority of the owner's word, PROJECT.md, the user config and the default."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_subagents as subagents  # noqa: E402


def setup(tmp_path, project=None, user=None, package=None):
    repo = tmp_path / "repo"
    (repo / ".agents").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    if project:
        (repo / ".agents/PROJECT.md").write_text(f"owner: me\ntarget: main\nsubagents: {project}\n")
    config = tmp_path / "cfg"
    if user:
        (config / "lhc").mkdir(parents=True)
        (config / "lhc/workflow.json").write_text(json.dumps({"subagents": user}))
    pkg = tmp_path / "pkg"
    (pkg / "config").mkdir(parents=True)
    (pkg / "config/workflow.json").write_text(json.dumps({"pr_stage": "on", "subagents": package or "off"}))
    return repo, config, pkg


def mode(tmp_path, task="", **layers):
    repo, config, pkg = setup(tmp_path, **layers)
    return subagents.resolve(repo, task, config_home=config, package=pkg)


def test_default_is_on_and_the_source_config_says_so(tmp_path):
    assert mode(tmp_path, package="on") == {"subagents": "on", "source": "package config"}
    assert json.loads((ROOT / "src/common/config/workflow.json").read_text())["subagents"] == "on"
    assert subagents.resolve(tmp_path, "", config_home=tmp_path / "none", package=tmp_path / "none")["subagents"] == "on"


def test_user_config_beats_the_package_and_project_beats_the_user(tmp_path):
    assert mode(tmp_path, user="on")["subagents"] == "on"
    assert mode(tmp_path / "a", user="on", project="off") == {"subagents": "off", "source": ".agents/PROJECT.md"}
    assert mode(tmp_path / "b", user="off", project="on") == {"subagents": "on", "source": ".agents/PROJECT.md"}


def test_the_owners_word_in_the_task_beats_everything(tmp_path):
    for task in ("сделай через воркеры", "запусти субагентов", "проверь параллельно", "собери council", "use subagents"):
        assert mode(tmp_path / task[:4], task, project="off", user="off")["subagents"] == "on", task
    assert mode(tmp_path / "x", "fix the worker queue bug", user="off")["subagents"] == "off"
    assert mode(tmp_path / "y", "сделай без субагентов", project="on", user="on") == {"subagents": "off", "source": "task"}


def test_an_invalid_value_is_ignored(tmp_path):
    assert mode(tmp_path, user="maybe", package="on")["subagents"] == "on"


def test_the_cli_prints_the_effective_mode(tmp_path):
    repo, config, pkg = setup(tmp_path, project="on")
    done = subprocess.run([sys.executable, str(ROOT / "src/common/tools/lhc_subagents.py"), "--repo", str(repo)],
                          capture_output=True, text=True)
    assert json.loads(done.stdout)["subagents"] == "on", done.stderr



def test_the_owner_can_refuse_agents_in_the_task(tmp_path):
    for n, task in enumerate(("сделай без агентов", "do it without agents", "не используй агентов")):
        assert mode(tmp_path / str(n), task, package="on") == {"subagents": "off", "source": "task"}, task
    assert mode(tmp_path / "plain", "почини агента рассылки", package="on")["subagents"] == "on"
