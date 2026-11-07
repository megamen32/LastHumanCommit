"""Plan as memory and Workers that are merged and removed before their leaf closes."""
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_plan_json as pj  # noqa: E402

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}


@pytest.fixture(autouse=True)
def isolated(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(tmp_path / "no-mirror.json"))
    monkeypatch.delenv("CODEX_THREAD_ID", raising=False)
    for key, value in GIT_ENV.items():
        monkeypatch.setenv(key, value)


def git(cwd, *args):
    return subprocess.run(["git", "-C", str(cwd), *args], check=True, capture_output=True, text=True).stdout.strip()


def make_plan(root, leaves):
    plan = root / "plan"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text(json.dumps({"title": "CI"}), encoding="utf-8")
    for leaf in leaves:
        (plan / "leaves" / f"{leaf['id']}.json").write_text(json.dumps(leaf, ensure_ascii=False), encoding="utf-8")
    return plan


def make_repo(root):
    repo = root / "task"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "task")
    (repo / "a.txt").write_text("base\n")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "base")
    return repo


def test_update_plan_appends_a_revision_and_refuses_what_it_would_drop(tmp_path):
    plan = make_plan(tmp_path, [{"id": "L01", "label": "A", "status": "queued"}])
    pj.update_plan(plan, {"goal": "CI after every deploy"}, {"reason": "L04 held five environments",
                                                             "summary": "split into one leaf per environment"})
    data = json.loads((plan / "plan.json").read_text())
    assert data["goal"] == "CI after every deploy"
    assert data["revisions"][-1]["reason"] == "L04 held five environments" and data["revisions"][-1]["at"]
    with pytest.raises(pj.LeafError, match="appended one at a time"):
        pj.update_plan(plan, {"revisions": ["Ближе: ..."]})
    with pytest.raises(pj.LeafError, match="unknown plan fields: progress"):
        pj.update_plan(plan, {"progress": "x"})
    with pytest.raises(pj.LeafError, match="revision must be"):
        pj.update_plan(plan, revision={"summary": "no reason"})
    with pytest.raises(pj.LeafError, match="slots"):
        pj.update_plan(plan, {"slots": 0})  # the reader's own check runs before writing
    assert json.loads((plan / "plan.json").read_text()) == data


def test_show_names_results_overruns_and_open_workers(tmp_path):
    began = (datetime.now().astimezone() - timedelta(minutes=190)).isoformat(timespec="seconds")
    plan = make_plan(tmp_path, [
        {"id": "L01", "label": "Codex", "status": "done", "result": "works: receipt-1.json"},
        {"id": "L02", "label": "ZCode", "status": "running", "started_at": began, "estimate_minutes": 15},
        {"id": "L03", "label": "MiniMax", "status": "queued", "worker": {"id": "w3", "branch": "lhc/w3"}},
    ])
    text = "\n".join(pj.plan_summary(plan, ["L02"]))
    assert "L01 «Codex» — works: receipt-1.json" in text
    assert "Now: L02 «ZCode»" in text and "Next: L03 «MiniMax»" in text
    assert "Past twice the estimate, split by object: L02 (190 of 15 min)" in text
    assert "Workers not merged and removed yet: L03 (lhc/w3)" in text
    state = pj.plan_state(plan)
    assert state.startswith("Plan plan: 1/3 done") and "split now: L02 190/15 min" in state
    assert "candidates by dependencies/capacity L03" in state and "Workers to merge and remove: L03" in state
    assert "dispatchable none" in state


def test_a_worker_is_registered_then_merged_and_removed_when_its_leaf_closes(tmp_path):
    repo = make_repo(tmp_path)
    worktree = tmp_path / "w-zcode"
    git(repo, "worktree", "add", "-q", "-b", "lhc/w-zcode", str(worktree))
    run_dir = tmp_path / "runs" / "ci" / "zcode"
    run_dir.mkdir(parents=True)
    plan = make_plan(tmp_path, [{"id": "L09", "label": "ZCode", "status": "queued"}])
    pj.worker_register(plan, "L09", "w-zcode", "lhc/w-zcode", str(worktree), run_dir=str(run_dir))
    leaf = json.loads((plan / "leaves/L09.json").read_text())
    assert leaf["status"] == "queued" and leaf["worker"]["branch"] == "lhc/w-zcode"
    with pytest.raises(pj.LeafError, match="already has Worker"):
        pj.worker_register(plan, "L09", "other", "lhc/w-zcode", str(worktree))

    (worktree / "zcode.txt").write_text("zcode ok\n")
    with pytest.raises(pj.LeafError, match="uncommitted changes"):
        pj.worker_finish(plan, "L09", str(repo), "ZCode passes")
    git(worktree, "add", "zcode.txt")
    git(worktree, "commit", "-q", "-m", "zcode")
    pj.worker_finish(plan, "L09", str(repo), "ZCode: 2 sessions, receipt-zcode.json")

    assert (repo / "zcode.txt").read_text() == "zcode ok\n"            # merged into the task branch
    assert not worktree.exists() and not run_dir.exists()               # worktree and run dir removed
    assert "lhc/w-zcode" not in git(repo, "branch", "--list")           # branch removed
    leaf = json.loads((plan / "leaves/L09.json").read_text())
    assert leaf["status"] == "done" and leaf["result"].startswith("ZCode: 2 sessions")
    assert leaf["worker"]["removed_at"]
    with pytest.raises(pj.LeafError, match="already merged and removed"):
        pj.worker_finish(plan, "L09", str(repo), "again")


def test_a_conflicting_worker_leaves_its_leaf_open_and_the_task_branch_clean(tmp_path):
    repo = make_repo(tmp_path)
    worktree = tmp_path / "w-claude"
    git(repo, "worktree", "add", "-q", "-b", "lhc/w-claude", str(worktree))
    plan = make_plan(tmp_path, [{"id": "L10", "label": "Claude", "status": "queued"}])
    pj.worker_register(plan, "L10", "w-claude", "lhc/w-claude", str(worktree))
    (worktree / "a.txt").write_text("worker\n")
    git(worktree, "commit", "-q", "-am", "worker")
    (repo / "a.txt").write_text("task\n")
    git(repo, "commit", "-q", "-am", "task")
    with pytest.raises(pj.LeafError, match="conflicts; the merge was aborted"):
        pj.worker_finish(plan, "L10", str(repo), "Claude passes")
    assert git(repo, "status", "--porcelain") == ""
    assert worktree.exists() and json.loads((plan / "leaves/L10.json").read_text())["status"] == "queued"


def test_the_cli_prints_the_plan_state_and_explains_errors(tmp_path):
    plan = make_plan(tmp_path, [{"id": "L01", "label": "A", "status": "queued"}])
    cli = [sys.executable, str(ROOT / "src/common/tools/lhc_plan_json.py")]
    env = {**os.environ}
    ok = subprocess.run(cli + ["update-plan", str(plan), "--revision", '{"reason": "split L04"}'],
                        capture_output=True, text=True, env=env)
    assert ok.returncode == 0 and "Plan plan: 0/1 done" in ok.stdout, ok.stderr
    bad = subprocess.run(cli + ["update-plan", str(plan), "--revision", '"Ближе: ..."'],
                         capture_output=True, text=True, env=env)
    assert bad.returncode == 1 and "revision must be" in bad.stderr and "Plan plan:" in bad.stderr
    shown = subprocess.run(cli + ["show", str(plan)], capture_output=True, text=True, env=env)
    assert "Next: L01 «A»" in shown.stdout


def test_explicit_worker_accepts_only_after_merge_and_retries_cleanup_without_reaccepting(tmp_path, monkeypatch):
    repo = make_repo(tmp_path)
    tree = tmp_path / "worker-explicit"
    git(repo, "worktree", "add", "-q", "-b", "lhc/explicit", str(tree))
    plan = make_plan(tmp_path, [{"id": "L01", "label": "explicit", "status": "queued"}])
    pj.worker_register(plan, "L01", "worker", "lhc/explicit", str(tree))
    lead = {"host_id": "test-host", "harness": "codex", "session_id": "lead"}
    executor = {**lead, "session_id": "worker"}
    pj.assign_leaf(plan, "L01", {"schema_version": 1, "attempt_id": "attempt",
        "executor_kind": "subagent", "lead": lead, "executor": executor, "parent": lead, "state": "assigned"})
    pj.transition_leaf(plan, "L01", "attempt", "dispatching",
                       receipt={"dispatch": {"request_id": "r", "status": "dispatching"}})
    pj.transition_leaf(plan, "L01", "attempt", "submitted",
                       receipt={"dispatch": {"request_id": "r", "status": "accepted", "turn_id": "t"}})
    pj.transition_leaf(plan, "L01", "attempt", "result_ready",
                       receipt={"observed_runtime": {"state": "completed", "turn_id": "t", "source": "native"}})
    (tree / "result.txt").write_text("integrated result\n")
    git(tree, "add", "result.txt")
    git(tree, "commit", "-qm", "worker result")
    original_git = pj._git
    failed = False
    def fail_first_cleanup(cwd, *args, **kwargs):
        nonlocal failed
        if args[:2] == ("worktree", "remove") and not failed:
            failed = True
            leaf = json.loads((plan / "leaves/L01.json").read_text())
            assert (repo / "result.txt").read_text() == "integrated result\n"
            assert leaf["assignment"]["state"] == "accepted"
            raise pj.LeafError("temporary cleanup failure")
        return original_git(cwd, *args, **kwargs)
    monkeypatch.setattr(pj, "_git", fail_first_cleanup)
    with pytest.raises(pj.LeafError, match="temporary cleanup failure"):
        pj.worker_finish(plan, "L01", str(repo), "result accepted")
    accepted = json.loads((plan / "leaves/L01.json").read_text())["assignment"]
    assert accepted["events"][-1]["receipt"]["integration"]["commit"]
    pj.worker_finish(plan, "L01", str(repo), "result accepted")
    final = json.loads((plan / "leaves/L01.json").read_text())
    assert final["assignment"] == accepted
    assert final["status"] == "done" and final["result"] == "result accepted"
    assert not tree.exists()
    assert final["worker"]["removed_at"]
    pj.worker_finish(plan, "L01", str(repo), "result accepted")
    assert json.loads((plan / "leaves/L01.json").read_text()) == final
