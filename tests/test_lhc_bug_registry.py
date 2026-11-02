"""File-backed bug register: preserve discovered failures, including pre-existing ones."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import multiprocessing
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "src/common/tools/lhc_bug_register.py"
MCP = ROOT / "src/common/tools/lhc_plan_mcp.py"


def cli(*args):
    return subprocess.run([sys.executable, str(TOOL), *map(str, args)],
                          capture_output=True, text=True)


def good(*args):
    run = cli(*args)
    assert run.returncode == 0, run.stderr
    return json.loads(run.stdout)


def bad(*args):
    run = cli(*args)
    assert run.returncode != 0, run.stdout
    return run.stderr


def project(tmp_path):
    root = tmp_path / "task"
    root.mkdir()
    return root


def new(root, title="Broken baseline", bug_id="B01", reporter="workerA"):
    return good("register", root, "--bug-id", bug_id, "--title", title,
                "--details", "reproducible failure before my task",
                "--source", "pytest tests/test_existing.py", "--reporter", reporter)


def test_register_lists_and_retains_baseline(tmp_path):
    p = project(tmp_path)
    r = new(p)
    assert r["bug"]["id"] == "B01" and r["bug"]["status"] == "open"
    assert r["bug"]["events"][0]["actor"] == "workerA"
    assert good("list", p)["total"] == 1
    assert good("get", p, "--bug-id", "B01")["bug"]["title"] == "Broken baseline"
    assert "B01" in bad("check", p)
    assert "already" in bad("register", p, "--bug-id", "B01", "--title", "other", "--details", "failure", "--reporter", "other")
    assert good("get", p, "--bug-id", "B01")["bug"]["title"] == "Broken baseline"


def test_update_history_and_stale_compare_and_swap(tmp_path):
    p = project(tmp_path)
    before = new(p)
    sha = before["sha256"]
    changed = good("update", p, "--bug-id", "B01", "--actor", "workerB",
                   "--expected-sha256", sha, "--fields", '{"owner":"workerB","status":"blocked","blocker":"Denied by host"}',
                   "--reason", "Host refused privileged change")
    assert changed["bug"]["status"] == "blocked"
    assert changed["bug"]["events"][0]["actor"] == "workerA"
    assert changed["bug"]["events"][1]["actor"] == "workerB"
    assert "conflict" in bad("update", p, "--bug-id", "B01", "--actor", "workerC",
                            "--expected-sha256", sha, "--fields", '{"details":"stale"}')
    assert good("get", p, "--bug-id", "B01")["sha256"] == changed["sha256"]


def test_fixed_requires_existing_evidence_file_and_passing_test(tmp_path):
    p = project(tmp_path)
    bug = new(p)
    args = ["resolve", p, "--bug-id", "B01", "--actor", "workerA",
            "--expected-sha256", bug["sha256"], "--status", "fixed"]
    assert "evidence" in bad(*args)
    assert "evidence" in bad(*args, "--evidence", '{"proof_path":"missing.log","test_command":"pytest -q","result":"PASS"}')
    receipt = p / "receipts" / "regression.txt"
    receipt.parent.mkdir()
    receipt.write_text("2 passed; reproduced failing test then fixed")
    evidence = json.dumps({"proof_path":"receipts/regression.txt",
                           "test_command":"pytest -q tests/test_existing.py",
                           "result":"2 passed"})
    resolved = good(*args, "--evidence", evidence)
    assert resolved["bug"]["status"] == "fixed"
    assert resolved["bug"]["resolution"]["evidence"]["sha256"] == hashlib.sha256(receipt.read_bytes()).hexdigest()
    assert resolved["bug"]["events"][0]["action"] == "register"
    assert resolved["bug"]["events"][-1]["action"] == "resolve"
    assert good("check", p)["unresolved"] == 0
    assert receipt.read_text().startswith("2 passed")


def test_duplicate_and_false_positive_need_reason_no_deletion(tmp_path):
    p = project(tmp_path)
    new(p, "Original", "B01")
    dupe = new(p, "Duplicate", "B02")
    args=["resolve", p, "--bug-id", "B02", "--actor", "reviewer",
          "--expected-sha256", dupe["sha256"], "--status", "duplicate"]
    assert "reason" in bad(*args)
    assert "duplicate" in bad(*args, "--reason", "Same failure", "--duplicate-of", "absent")
    closed = good(*args, "--reason", "Identical failure to B01", "--duplicate-of", "B01")
    assert closed["bug"]["resolution"]["duplicate_of"] == "B01"
    assert good("list", p)["total"] == 2
    assert "B01" in bad("check", p)
    false_bug = new(p, "False report", "B03")
    fake = good("resolve", p, "--bug-id", "B03", "--actor", "reviewer",
                "--expected-sha256", false_bug["sha256"],
                "--status", "false_positive", "--reason", "Specification permits the observed behavior")
    assert fake["bug"]["status"] == "false_positive"
    assert good("list", p)["total"] == 3


def test_cannot_delete_or_replace_history_or_fake_fixed(tmp_path):
    p = project(tmp_path)
    r=new(p)
    assert "unknown" in bad("delete", p, "--bug-id", "B01")
    assert "immutable" in bad("update", p, "--bug-id", "B01", "--actor", "other",
                              "--expected-sha256", r["sha256"], "--fields", '{"events":[]}')
    assert "invalid" in bad("update", p, "--bug-id", "B01", "--actor", "other",
                            "--expected-sha256", r["sha256"], "--fields", '{"status":"fixed"}')
    assert good("list", p)["total"] == 1


def test_path_traversal_and_symlink_registry_rejected(tmp_path):
    p=project(tmp_path)
    err=bad("register", p, "--bug-id", "../escape", "--title", "escape",
            "--details", "Bad", "--reporter", "worker")
    assert "id" in err
    outside=tmp_path/"outside"
    outside.mkdir()
    (p/"bugs").symlink_to(outside, target_is_directory=True)
    err=bad("register", p, "--bug-id", "B01", "--title", "escape",
            "--details", "Bad", "--reporter", "worker")
    assert "symlink" in err and not list(outside.iterdir())


def test_multiple_processes_register_without_lost_records(tmp_path):
    p=project(tmp_path)
    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        jobs=[pool.submit(cli, "register", p, "--bug-id", f"B{i:02d}",
                          "--title", f"Test failure {i}",
                          "--details", "Existing regression", "--reporter", f"worker{i}")
              for i in range(25)]
    assert all(job.result().returncode==0 for job in jobs), [x.result().stderr for x in jobs if x.result().returncode]
    records=good("list", p)
    assert records["total"]==25
    assert len({x["bug"]["id"] for x in records["bugs"]})==25
    assert good("list", p, "--status", "open")["total"]==25


def test_mcp_stdio_exposes_bug_crud_and_unresolved_gate(tmp_path):
    p=project(tmp_path)
    def rpc(n, method, params):
        return {"jsonrpc":"2.0", "id":n, "method":method, "params":params}
    requests=[
      rpc(1, "initialize", {"protocolVersion":"2024-11-05"}),
      rpc(2, "tools/list", {}),
      rpc(3, "tools/call", {"name":"bug_register", "arguments":{
          "plan_dir":str(p), "bug_id":"B55", "title":"Pre-existing failure",
          "details":"failed before feature started", "reporter":"first-observer", "source":"pytest"}}),
      rpc(4, "tools/call", {"name":"bug_list", "arguments":{"plan_dir":str(p)}}),
      rpc(5, "tools/call", {"name":"bug_check", "arguments":{"plan_dir":str(p)}})
    ]
    result = subprocess.run([sys.executable,str(ROOT/"plugins/last-human-commit/scripts/plan_mcp.py")],
                            input="\n".join(json.dumps(v) for v in requests)+"\n",
                            text=True,capture_output=True,timeout=30)
    assert result.returncode==0,result.stderr
    replies=[json.loads(v) for v in result.stdout.splitlines()]
    assert len(replies)==5
    names={x["name"] for x in replies[1]["result"]["tools"]}
    assert {"bug_register","bug_get","bug_list","bug_update","bug_resolve","bug_check"} <= names
    assert replies[2]["result"]["isError"] is False
    assert replies[3]["result"]["isError"] is False
    assert replies[4]["result"]["isError"] is True
    assert "B55" in replies[4]["result"]["content"][0]["text"]


def test_package_contains_identical_registry_and_mcp_projections():
    for rel in ("plugins/last-human-commit/tools/lhc_bug_register.py",
                "plugins/last-human-commit/common/tools/lhc_bug_register.py",
                "plugins/last-human-commit/native/codex/tools/lhc_bug_register.py"):
        path=ROOT/rel
        assert path.read_bytes()==TOOL.read_bytes()
    for rel in ("plugins/last-human-commit/tools/lhc_plan_mcp.py",
                "plugins/last-human-commit/common/tools/lhc_plan_mcp.py"):
        expected = MCP.read_bytes()
        if "/common/tools/" in rel:
            expected = expected.replace(b"src/common/", b"common/")
        assert (ROOT/rel).read_bytes() == expected


def test_a_deleted_record_cannot_forge_green(tmp_path):
    p=project(tmp_path)
    new(p)
    journal=p/".lhc-bugs.jsonl"
    assert journal.is_file()
    (p/"bugs/B01.json").unlink()
    assert "missing" in bad("check", p)
    assert "B01" in journal.read_text()


def test_claimed_fix_matches_proof_and_disappearing_proof_blocks_green(tmp_path):
    p=project(tmp_path)
    r=new(p)
    receipt=p/"receipts/test.txt"
    receipt.parent.mkdir()
    receipt.write_text("2 failed")
    evidence=json.dumps({"proof_path":"receipts/test.txt","test_command":"pytest -q",
                         "result":"2 passed"})
    base=["resolve",p,"--bug-id","B01","--actor","tester",
          "--expected-sha256",r["sha256"],"--status","fixed","--evidence",evidence]
    assert "proof" in bad(*base)
    receipt.write_text("2 passed")
    assert good(*base)["bug"]["status"]=="fixed"
    receipt.unlink()
    assert "evidence" in bad("check",p)


def test_competing_updates_are_serialized_and_journaled(tmp_path):
    p=project(tmp_path)
    r=new(p)
    import concurrent.futures
    def change(owner):
        return cli("update",p,"--bug-id","B01","--actor",owner,
                   "--expected-sha256",r["sha256"],
                   "--fields",json.dumps({"owner":owner}))
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        outcomes=list(pool.map(change,("first","second")))
    assert sorted(c.returncode for c in outcomes)==[0,2]
    journal=[json.loads(v) for v in (p/".lhc-bugs.jsonl").read_text().splitlines()]
    assert len(journal)==2
    assert journal[0]["action"]=="register" and journal[1]["action"]=="update"
    assert journal[1]["sha256"]==good("get",p,"--bug-id","B01")["sha256"]


def test_corrupt_journal_never_counts_as_green(tmp_path):
    p=project(tmp_path)
    r=new(p)
    good("resolve",p,"--bug-id","B01","--actor","reviewer",
         "--expected-sha256",r["sha256"],"--status","false_positive",
         "--reason","Documented expected behavior")
    assert good("check",p)["unresolved"]==0
    (p/".lhc-bugs.jsonl").write_text("corrupt\n")
    assert "journal" in bad("check",p)


def test_duplicate_cycle_cannot_hide_all_open_bugs(tmp_path):
    p=project(tmp_path)
    first=new(p, "First", "B01")
    second=new(p, "Second", "B02")
    good("resolve",p,"--bug-id","B01","--actor","reviewer",
         "--expected-sha256",first["sha256"],"--status","duplicate",
         "--reason","Same defect from another angle","--duplicate-of","B02")
    good("resolve",p,"--bug-id","B02","--actor","reviewer",
         "--expected-sha256",second["sha256"],"--status","duplicate",
         "--reason","Same root bug as earlier ticket","--duplicate-of","B01")
    assert "cycle" in bad("check",p)
