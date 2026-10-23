"""Independent review stays bound to both native and product roots."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from _inprocess_lane import local_command, outcome_process, review_export_manifest
from test_outcome_contract import state
from test_outcome_product_root import review, stored_assignment

pytestmark = pytest.mark.nightly


def cli(tmp_path, cwd, *args):
    """The outcome CLI of one case, without a new interpreter."""
    return outcome_process(cwd, *args, home=Path(tmp_path) / "home",
                           codex_home=Path(tmp_path) / ".codex", session_id="worker")


def bound_quickfix(tmp_path):
    session_root, product_root, source, state_path = stored_assignment(tmp_path)
    saved = json.loads(state_path.read_text())
    saved["business"]["outcome"]["started_at"] = datetime.now(timezone.utc).isoformat()
    for stage in ("deploy", "publication", "integration"):
        saved["business"]["outcome"]["stages"][stage]["status"] = "not-applicable"
    state_path.write_text(json.dumps(saved))
    command = ["contract", "--scenario", "Run owned CLI", "--target", "python3 owned.py",
               "--expected", "prints before", "--scope-source", source["source"],
               "--product-root", str(product_root), "--owned-path", "owned.py"]
    result = cli(tmp_path, session_root, *command)
    assert result.returncode == 0, result.stderr
    outcome = json.loads(state_path.read_text())["business"]["outcome"]
    return session_root, product_root, outcome


def native_review(tmp_path, session_root, product_root, outcome, *, workdir="product", native_cwd=None,
                  assigned_product_root=False):
    consumer_root = product_root
    if workdir == "foreign":
        consumer_root = tmp_path / "foreign"
        consumer_root.mkdir()
        (consumer_root / "owned.py").write_text("print('before')\n")
    elif workdir == "omitted":
        consumer_root = session_root
        (session_root / "owned.py").write_text("print('wrong-root')\n")
    manifest = review_export_manifest(session_root, outcome, sid="reviewer",
                                       stage_names=("technical", "consumer"),
                                       command="python3 owned.py",
                                       consumer_workdir=consumer_root)
    data = json.loads(manifest.read_text())
    source = Path(data["target"]["source"]["location"])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    tech_args = json.loads(rows[2]["payload"]["arguments"])
    tech_args["workdir"] = str(product_root)
    rows[2]["payload"]["arguments"] = json.dumps(tech_args)
    _, tech_stdout, tech_stderr = local_command("python3 -m unittest discover -q", product_root)
    rows[3]["payload"]["output"] = tech_stdout + tech_stderr
    if native_cwd is not None:
        rows[0]["payload"]["cwd"] = str(native_cwd)
        if Path(native_cwd) == product_root or assigned_product_root:
            rows[1]["payload"]["content"][0]["text"] += (
                "\nProduct/native review cwd " + str(product_root) + ". Scenario: run the assigned CLI.")
    raw = "".join(json.dumps(row) + "\n" for row in rows)
    source.write_text(raw)
    Path(data["target"]["path"]).write_text(raw)
    native_path = tmp_path / ".codex/sessions/reviewer.jsonl"
    native_path.parent.mkdir(parents=True, exist_ok=True)
    native_path.write_bytes(source.read_bytes())
    return manifest, source, rows


def test_existing_native_reviewer_can_review_bound_product_root(tmp_path, monkeypatch):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    manifest, _, _ = native_review(tmp_path, session_root, product_root, outcome)
    monkeypatch.setenv("CODEX_HOME", str(session_root / "native-home/.codex"))
    _, _, observations = review.load_review(manifest)
    consumer = next((call, output) for call, output in observations if call.get("call_id") == "call-1")
    assert review.real_observation(*consumer, outcome["canary"]["target"], "consumer",
                                   outcome["task_class"], product_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode == 0, result.stderr
    accepted = json.loads(result.stdout)
    assert accepted["finish_verdict"] == "complete"
    assert accepted["verification_level"] == "independent-review"
    assert accepted["canary"]["status"] == "complete"


def test_omitted_tool_workdir_remains_native_root_not_product_root(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    native_review(tmp_path, session_root, product_root, outcome, workdir="omitted")
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before


def test_reviewer_cannot_use_foreign_tool_workdir(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    native_review(tmp_path, session_root, product_root, outcome, workdir="foreign")
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before


def test_cross_cwd_native_reviewer_accepts_exact_product_assignment_and_records_identity(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    foreign_native_cwd = tmp_path / "foreign-native"
    foreign_native_cwd.mkdir()
    native_review(tmp_path, session_root, product_root, outcome, native_cwd=foreign_native_cwd,
                  assigned_product_root=True)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode == 0, result.stderr
    accepted = json.loads(result.stdout)
    evidence = accepted["stages"]["consumer"]["evidence"][-1]
    assert accepted["finish_verdict"] == "complete"
    assert evidence["reviewer"] == "reviewer"
    assert evidence["consumer_target"] == accepted["canary"]["target"]
    assert "call-1" in evidence["calls"]
    manifest = json.loads(Path(evidence["manifest"]).read_text())
    native_path = Path(manifest["target"]["source"]["location"])
    native_rows = [json.loads(line) for line in native_path.read_text().splitlines()]
    assert native_rows[0]["payload"]["cwd"] == str(foreign_native_cwd)
    consumer_call = next(row for row in native_rows if row.get("payload", {}).get("call_id") == "call-1")
    consumer_args = json.loads(consumer_call["payload"]["arguments"])
    assert consumer_args["workdir"] == str(product_root)


def test_cross_cwd_native_reviewer_still_needs_explicit_product_workdir(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    foreign_native_cwd = tmp_path / "foreign-native"
    foreign_native_cwd.mkdir()
    native_review(tmp_path, session_root, product_root, outcome, workdir="omitted",
                  native_cwd=foreign_native_cwd, assigned_product_root=True)
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before


def test_reviewer_in_product_root_requires_exact_product_root_assignment(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    native_review(tmp_path, session_root, product_root, outcome, native_cwd=product_root)
    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("suffix", ["-neighbor", ".git", "/other", "/../other"])
def test_product_root_assignment_does_not_accept_neighbor_or_path_suffix(tmp_path, suffix):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    _, source, rows = native_review(tmp_path, session_root, product_root, outcome, native_cwd=product_root)
    assignment = rows[1]["payload"]["content"][0]["text"]
    rows[1]["payload"]["content"][0]["text"] = assignment.replace(
        str(product_root), str(product_root) + suffix)
    raw = "".join(json.dumps(row) + "\n" for row in rows)
    source.write_text(raw)
    (tmp_path / ".codex/sessions/reviewer.jsonl").write_text(raw)
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before


def test_product_root_review_does_not_map_pre_cutoff_calls(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    _, source, rows = native_review(tmp_path, session_root, product_root, outcome)
    cutoff = datetime.fromisoformat(outcome["evidence_after"])
    old = (cutoff - timedelta(seconds=1)).isoformat()
    for row in rows:
        if row.get("payload", {}).get("type") in {"function_call", "function_call_output"}:
            row["timestamp"] = old
    raw = "".join(json.dumps(row) + "\n" for row in rows)
    source.write_text(raw)
    native_path = tmp_path / ".codex/sessions/reviewer.jsonl"
    native_path.write_text(raw)
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before
