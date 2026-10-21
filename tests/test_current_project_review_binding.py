"""An exact product assignment may bind review when reviewer CWD differs."""
import json
from pathlib import Path

from test_product_root_review import bound_quickfix, cli, native_review, state
from test_outcome_product_root import guard, review
import pytest

pytestmark = pytest.mark.nightly


def _reverse_layout(tmp_path, *, workdir="product", assigned_root=None):
    # The live tooling compares resolved roots, so the fixture keeps one
    # canonical path for the session, the product and the assignment.
    tmp_path = Path(tmp_path).resolve()
    session_root, external_root, outcome = bound_quickfix(tmp_path)
    # Recreate the reported reverse layout: the current product is the review
    # command's root, while the independent native reviewer lives in ExManager.
    outcome["cwd"] = str(external_root)
    owner_source = Path(outcome["native_source"])
    owner_rows = [json.loads(line) for line in owner_source.read_text().splitlines()]
    owner_rows[0]["payload"]["cwd"] = str(external_root)
    owner_source.write_text("".join(json.dumps(row) + "\n" for row in owner_rows))
    state_path = guard.learning_path(session_root, "codex", "worker")
    saved = json.loads(state_path.read_text())
    saved["business"]["outcome"] = outcome
    guard.write_state(guard.learning_path(external_root, "codex", "worker"), saved)

    reviewer_root = session_root
    manifest, source, rows = native_review(
        tmp_path, session_root, external_root, outcome,
        workdir=workdir, native_cwd=reviewer_root,
    )
    assignment_root = assigned_root or external_root
    user_text = rows[1]["payload"]["content"][0]["text"]
    # The native assignment declares exactly one product root. A wrong declared
    # root replaces the real one instead of being appended next to it, so the
    # assignment genuinely stops naming the exact product root under review.
    rows[1]["payload"]["content"][0]["text"] = (
        user_text.replace(str(external_root), str(assignment_root))
        + "\nAssigned product root: " + str(assignment_root))
    raw = "".join(json.dumps(row) + "\n" for row in rows)
    source.write_text(raw)
    (tmp_path / ".codex/sessions/reviewer.jsonl").write_text(raw)
    return external_root, reviewer_root, outcome, manifest


def test_independent_reviewer_in_other_native_cwd_can_review_exact_current_product(tmp_path):
    tmp_path = tmp_path.resolve()
    product_root, _, outcome, _ = _reverse_layout(tmp_path)

    result = cli(tmp_path, product_root, "review", "--native-reviewer", "reviewer")

    assert result.returncode == 0, result.stderr
    accepted = json.loads(result.stdout)
    assert accepted["finish_verdict"] == "complete"
    assert accepted["verification_level"] == "independent-review"
    assert accepted["canary"]["status"] == "complete"


def test_reverse_layout_still_requires_exact_product_assignment_and_product_workdir(tmp_path):
    tmp_path = tmp_path.resolve()
    product_root, _, _, _ = _reverse_layout(tmp_path, assigned_root=tmp_path / "neighbor")
    before = state(product_root)

    wrong_assignment = cli(tmp_path, product_root, "review", "--native-reviewer", "reviewer")

    assert wrong_assignment.returncode != 0
    assert state(product_root) == before

    omitted_case = tmp_path / "omitted-case"
    omitted_case.mkdir()
    product_root, _, _, _ = _reverse_layout(omitted_case, workdir="omitted")
    before = state(product_root)

    omitted_workdir = cli(omitted_case, product_root, "review", "--native-reviewer", "reviewer")

    assert omitted_workdir.returncode != 0
    assert state(product_root) == before
