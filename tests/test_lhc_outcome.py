"""Focused checks for Lead-owned short/full mode selection.

The classifier is a conservative scope hint. The canonical workflow owns the
plan and tester gates; a worker leaf cannot select or waive those gates.
"""
import importlib.util
from pathlib import Path


MODULE = Path(__file__).parents[1] / "src/common/tools/lhc_outcome.py"
spec = importlib.util.spec_from_file_location("lhc_outcome_under_test", MODULE)
outcome = importlib.util.module_from_spec(spec)
spec.loader.exec_module(outcome)


def test_bounded_repair_is_quickfix_with_consumer_proof():
    task = "Fix the small export bug in one module and verify a real export."
    assert outcome.classify(task) == "quickfix"
    assert [name for name, stage in outcome.applicable("quickfix", task).items()
            if stage["status"] == "pending"] == ["technical", "consumer"]


def test_small_behavior_change_is_quickfix():
    assert outcome.classify("Make a small change to the save button behavior.") == "quickfix"


def test_new_feature_and_broad_or_risky_repair_are_fullcycle():
    for task in (
        "Implement a new feature for account recovery.",
        "Fix the risky authentication repair across several services.",
        "Small fix: redesign the architecture of all services.",
    ):
        assert outcome.classify(task) == "fullcycle"
        assert all(stage["status"] == "pending"
                   for stage in outcome.applicable("fullcycle", task).values())


def test_assigned_leaf_does_not_choose_a_smaller_parent_mode():
    assert outcome.classify(
        "Implement one assigned leaf of the new feature across several modules."
    ) == "fullcycle"

