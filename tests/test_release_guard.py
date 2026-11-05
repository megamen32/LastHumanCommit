"""The fallback release lease (Herder unavailable): a git ref on origin taken by compare-and-swap."""
import importlib.util
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_worktree.py"


def load():
    sys.path.insert(0, str(TOOL.parent))
    spec = importlib.util.spec_from_file_location("lhc_worktree_guard_test", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sh(cwd, *args):
    return subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def project(tmp_path, monkeypatch):
    for key in ("AUTHOR", "COMMITTER"):
        monkeypatch.setenv(f"GIT_{key}_NAME", "t")
        monkeypatch.setenv(f"GIT_{key}_EMAIL", "t@example.com")
    origin = tmp_path / "origin.git"
    sh(tmp_path, "git", "init", "--bare", "-b", "main", str(origin))
    work = tmp_path / "work"
    sh(tmp_path, "git", "clone", "-q", str(origin), str(work))
    sh(work, "git", "checkout", "-q", "-b", "main")
    (work / "VERSION").write_text("1.0.0\n")
    sh(work, "git", "add", "VERSION")
    sh(work, "git", "commit", "-q", "-m", "one")
    sh(work, "git", "push", "-q", "origin", "main")
    live = sh(work, "git", "rev-parse", "HEAD")
    (work / "VERSION").write_text("1.1.0\n")
    sh(work, "git", "commit", "-q", "-am", "two")
    sh(work, "git", "push", "-q", "origin", "main")
    return origin, work, live, sh(work, "git", "rev-parse", "HEAD")


def test_lease_is_acquired_refused_for_a_live_foreign_one_taken_when_expired_and_released(tmp_path, monkeypatch):
    origin, work, live, cand = project(tmp_path, monkeypatch)
    wt = load()
    ref = "refs/lhc/release/demo"
    first = wt.guard_acquire(work, "demo", "s1", cand, "h1")
    assert first["ok"] and sh(origin, "git", "rev-parse", ref) == first["commit"]
    payload = json.loads(sh(origin, "git", "show", "-s", "--format=%B", ref))
    assert payload["session"] == "s1" and payload["candidate"] == cand and payload["expires"] > time.time() + 800
    foreign = wt.guard_acquire(work, "demo", "s2", cand, "h2")
    assert not foreign["ok"] and foreign["reason"] == "foreign lease" and foreign["owner"] == "s1"
    assert wt.guard_acquire(work, "demo", "s1", cand, "h1")["ok"]  # the owner renews
    refused = wt.guard_release(work, "demo", "s2")
    assert not refused["ok"] and refused["reason"] == "foreign lease"
    assert wt.guard_release(work, "demo", "s1")["released"]
    assert sh(origin, "git", "for-each-ref", ref) == ""
    # an expired lease is taken over by the same compare-and-swap
    assert wt.guard_acquire(work, "demo", "s1", cand, "h1", now=time.time() - 7200)["ok"]
    taken = wt.guard_acquire(work, "demo", "s2", cand, "h2")
    assert taken["ok"] and taken["took_over_expired"]
    assert json.loads(sh(origin, "git", "show", "-s", "--format=%B", ref))["session"] == "s2"
    assert wt.guard_release(work, "demo", "s2")["released"]


def test_checks_before_mutation_are_made_in_code(tmp_path, monkeypatch):
    origin, work, live, cand = project(tmp_path, monkeypatch)
    wt = load()
    assert not wt.guard_check(work, "demo", "s1", cand, live, live)["ok"]  # no lease yet
    assert wt.guard_acquire(work, "demo", "s1", cand)["ok"]
    good = wt.guard_check(work, "demo", "s1", cand, live, live)
    assert good["ok"], good
    assert not wt.guard_check(work, "demo", "s1", cand, live, cand)["checks"]["expected_revision_matches_live"]
    assert not wt.guard_check(work, "demo", "s1", live, cand, cand)["ok"]  # an older candidate, not newer than live
    sh(work, "git", "checkout", "-q", "-b", "side")
    (work / "VERSION").write_text("9.0.0\n")
    sh(work, "git", "commit", "-q", "-am", "side")
    side = sh(work, "git", "rev-parse", "HEAD")
    assert wt.guard_acquire(work, "demo", "s1", side)["ok"]
    unmerged = wt.guard_check(work, "demo", "s1", side, live, live)
    assert not unmerged["ok"] and not unmerged["checks"]["candidate_in_origin_main"]
    sh(work, "git", "checkout", "-q", "main")
    (work / "dirty.txt").write_text("x")
    assert not wt.guard_check(work, "demo", "s1", cand, live, live)["checks"]["worktree_clean"]


def test_cli_exit_codes_and_the_herder_bypass_journal(tmp_path, monkeypatch):
    origin, work, live, cand = project(tmp_path, monkeypatch)
    plan = tmp_path / "plan"
    plan.mkdir()
    (plan / "plan.json").write_text(json.dumps({"revisions": []}))
    base = [sys.executable, str(TOOL), "release-guard"]
    common = ["--repo", str(work), "--project", "demo", "--candidate", cand]
    done = subprocess.run([*base, "acquire", *common, "--session", "s1", "--plan", str(plan)], capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    rows = json.loads((plan / "plan.json").read_text())["revisions"]
    assert rows and rows[0]["reason"] == "herder-bypass"
    mails = list((work / ".agents/mail/DISPATCHER").glob("*-result.md"))
    assert mails and "herder-bypass" in mails[0].read_text()
    other = subprocess.run([*base, "acquire", *common, "--session", "s2"], capture_output=True, text=True)
    assert other.returncode == 1 and "foreign lease" in other.stdout
    free = subprocess.run([*base, "release", *common, "--session", "s1"], capture_output=True, text=True)
    assert free.returncode == 0 and json.loads(free.stdout)["released"]

