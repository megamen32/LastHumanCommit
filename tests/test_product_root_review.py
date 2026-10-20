"""Independent review stays bound to both native and product roots."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from test_outcome_contract import review_export, state
from test_outcome_product_root import cli, review, stored_assignment


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


def native_review(tmp_path, session_root, product_root, outcome, *, workdir="product", native_cwd=None):
    consumer_root = product_root
    if workdir == "foreign":
        consumer_root = tmp_path / "foreign"
        consumer_root.mkdir()
        (consumer_root / "owned.py").write_text("print('before')\n")
    elif workdir == "omitted":
        consumer_root = session_root
        (session_root / "owned.py").write_text("print('wrong-root')\n")
    manifest = review_export(session_root, outcome, sid="reviewer", stage_names=("technical", "consumer"),
                             command="python3 owned.py", consumer_workdir=consumer_root)
    data = json.loads(manifest.read_text())
    source = Path(data["target"]["source"]["location"])
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    tech_args = json.loads(rows[2]["payload"]["arguments"])
    tech_args["workdir"] = str(product_root)
    rows[2]["payload"]["arguments"] = json.dumps(tech_args)
    tech = subprocess.run(["python3", "-m", "unittest", "discover", "-q"],
                          cwd=product_root, capture_output=True, text=True)
    rows[3]["payload"]["output"] = tech.stdout + tech.stderr
    if native_cwd is not None:
        rows[0]["payload"]["cwd"] = str(native_cwd)
        if Path(native_cwd) == product_root:
            rows[1]["payload"]["content"][0]["text"] += "\nAssigned product root: " + str(product_root)
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


def test_native_reviewer_root_must_match_state_root(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    native_review(tmp_path, session_root, product_root, outcome, native_cwd=tmp_path / "foreign-native")
    before = state(session_root)

    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode != 0
    assert state(session_root) == before


def test_reviewer_in_product_root_requires_exact_product_root_assignment(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    native_review(tmp_path, session_root, product_root, outcome, native_cwd=product_root)
    result = cli(tmp_path, session_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode == 0, result.stderr


def test_product_root_assignment_does_not_accept_neighbor_prefix(tmp_path):
    session_root, product_root, outcome = bound_quickfix(tmp_path)
    _, source, rows = native_review(tmp_path, session_root, product_root, outcome, native_cwd=product_root)
    rows[1]["payload"]["content"][0]["text"] = rows[1]["payload"]["content"][0]["text"].replace(
        "Assigned product root: " + str(product_root), "Assigned product root: " + str(product_root) + "-neighbor")
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
