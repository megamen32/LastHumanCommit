"""A reassigned scope cannot reuse the predecessor review assignment."""
import hashlib
import json
from pathlib import Path

import pytest

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))
import lhc_outcome_review as review

PREDECESSOR_ID = "predecessor-id"
PREDECESSOR_GOAL = "RESEARCH ONLY: inspect the runtime; do not change code."


def _reviewer_source(tmp_path, assignment):
    home = tmp_path / ".codex"
    sessions = home / "sessions"
    sessions.mkdir(parents=True)
    path = sessions / "reviewer-native.jsonl"
    assignments = assignment if isinstance(assignment, list) else [assignment]
    rows = [{"type": "session_meta", "payload": {"id": "reviewer", "cwd": str(tmp_path)}}]
    rows.extend({"type": "response_item", "payload": {
        "type": "message", "role": "user", "content": [{"text": text}],
    }} for text in assignments)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return home, path


@pytest.mark.parametrize("assignment,reason", [
    (f"Review outcome {PREDECESSOR_ID}. Original task: {PREDECESSOR_GOAL}", "no native assignment"),
    ("Review outcome current-outcome-id for the current task.", "omits the full current task goal"),
    ("Review the complete current task text: Implement the currently authorized source-only publication task in the exact assigned files.", "omits active outcome id"),
    (["Review outcome current-outcome-id.", "Review the complete current task text: Implement the currently authorized source-only publication task in the exact assigned files."], "not together in one native assignment"),
    ("Review unrelated project changes.", "no native assignment"),
])
def test_missing_current_reviewer_pair_returns_actionable_fresh_task_boundary(tmp_path, monkeypatch, assignment, reason):
    home, source = _reviewer_source(tmp_path, assignment)
    monkeypatch.setenv("CODEX_HOME", str(home))
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    active = {
        "id": "current-outcome-id", "task_class": "fullcycle",
        "original_goal": "Implement the currently authorized source-only publication task in the exact assigned files.",
        "owner": {"session_id": "worker"},
    }

    with pytest.raises(ValueError) as error:
        review.native_reviewer_manifest(active, tmp_path, "reviewer")

    message = str(error.value)
    assert reason in message
    assert "no reviewer evidence was accepted" in message.casefold()
    assert "fresh user assignment in the existing reviewer session" in message
    assert "outcome id and current review subject digest" in message
    assert "readable exact product root, scenario, and expected result" in message
    assert "legacy assignments must include the full current goal and corrections" in message
    assert "digest identifies the subject only; it is not permission" in message
    assert hashlib.sha256(source.read_bytes()).hexdigest() == before
    assert not (tmp_path / ".tmp/lhc-native-review").exists()


def test_exact_current_pair_still_uses_existing_native_review_window(tmp_path, monkeypatch):
    assignment = "Review current-outcome-id and the complete current task text."
    home, source = _reviewer_source(tmp_path, assignment)
    monkeypatch.setenv("CODEX_HOME", str(home))
    active = {
        "id": "current-outcome-id", "task_class": "fullcycle",
        "original_goal": "the complete current task text", "owner": {"session_id": "worker"},
    }

    manifest = review.native_reviewer_manifest(active, tmp_path, "reviewer")

    data = json.loads(manifest.read_text())
    assert data["target"]["sessionId"] == "reviewer"
    assert source.read_bytes().startswith(b'{')
