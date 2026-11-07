"""A malformed leaf can be repaired without dropping data or weakening validation."""
import contextlib
import hashlib
import json
from pathlib import Path

import pytest
from _inprocess import load_module

plan = load_module(Path(__file__).resolve().parents[1] / "src/common/tools/lhc_plan_json.py")


@pytest.fixture
def broken(tmp_path):
    path = tmp_path / "leaves/L01.json"
    path.parent.mkdir()
    raw = {"id": "L01", "label": "Сохранить данные", "status": "done",
           "result": "Existing result\n", "note": "Existing note\n",
           "created_at": "2026-11-07T18:15:35+03:00",
           "updated_at": "2099-11-07T18:55:00+03:00",
           "progress_events": [{"at": "2099-11-07T18:55:00+03:00",
                                "changes": {"evidence": ["/original/path"]}}],
           "evidence": ["/original/path"]}
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n")
    return path


def repair(path, **kwargs):
    return plan.repair_move_field(path.parent.parent, path.stem,
                                 source="evidence", target="note",
                                 expected_hash=hashlib.sha256(path.read_bytes()).hexdigest(),
                                 **kwargs)


@pytest.mark.parametrize("value", [["/original/path"], {"nested": [None, False, 42, "Юникод\n"]}, "", None])
@pytest.mark.parametrize("target", ["result", "note"])
def test_cli_repairs_malformed_leaf_preserving_value_history_and_bytes(broken, capsys, value, target):
    raw = json.loads(broken.read_bytes())
    raw["evidence"] = value
    broken.write_text(json.dumps(raw, ensure_ascii=False) + "\n")
    before = broken.read_bytes()
    digest = hashlib.sha256(before).hexdigest()
    with pytest.raises(plan.LeafError):
        plan.update_leaf(broken.parent.parent, "L01", {"status": "waiting"})
    assert plan.main(["repair-move-field", str(broken.parent.parent), "L01",
                      "--source", "evidence", "--target", target,
                      "--expected-hash", digest]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert Path(receipt["backup_path"]).read_bytes() == before
    assert receipt["before_sha256"] == digest
    assert receipt["sha256"] == hashlib.sha256(broken.read_bytes()).hexdigest()
    after = json.loads(broken.read_bytes())
    assert "evidence" not in after
    assert after[target].startswith(raw[target])
    assert json.loads(after[target][len(raw[target]):].strip()) == {"evidence": value}
    assert {k: v for k, v in after.items() if k != target} == {
        k: v for k, v in raw.items() if k not in (target, "evidence")}
    plan.update_leaf(broken.parent.parent, "L01", {"status": "waiting"})
    updated = json.loads(broken.read_bytes())
    assert updated["status"] == "waiting"
    assert updated["progress_events"][:-1] == raw["progress_events"]


@pytest.mark.parametrize("source,target,digest,message", [
    ("evidence", "note", "0" * 64, "конфликт"),
    ("status", "note", None, "known"),
    ("evidence", "status", None, "target"),
    ("missing", "note", None, "missing"),
    ("evidence", "note", "", "hash"),
])
def test_rejects_unsafe_requests_without_writes(broken, source, target, digest, message):
    before = broken.read_bytes()
    with pytest.raises(plan.LeafError, match=message):
        plan.repair_move_field(broken.parent.parent, "L01", source=source, target=target,
                               expected_hash=digest if digest is not None else hashlib.sha256(before).hexdigest())
    assert broken.read_bytes() == before
    assert not (broken.parent.parent / ".lhc-repair-backups").exists()


def test_cas_reads_inside_existing_plan_lock(broken, monkeypatch):
    before = broken.read_bytes()
    changed = before + b"\n"
    @contextlib.contextmanager
    def competing_writer(lock):
        assert lock == broken.parent.parent / ".lhc-leaves.lock"
        broken.write_bytes(changed)
        yield
    monkeypatch.setattr(plan, "file_lock", competing_writer)
    with pytest.raises(plan.LeafError, match="конфликт"):
        repair(broken)
    assert broken.read_bytes() == changed


def test_backup_failure_leaves_original_untouched(broken):
    before = broken.read_bytes()
    (broken.parent.parent / ".lhc-repair-backups").write_text("not a directory")
    with pytest.raises(OSError):
        repair(broken)
    assert broken.read_bytes() == before


def test_other_unknown_field_is_not_silently_dropped(broken):
    raw = json.loads(broken.read_bytes())
    raw["another_unknown"] = 7
    broken.write_text(json.dumps(raw))
    before = broken.read_bytes()
    with pytest.raises(plan.LeafError):
        repair(broken)
    assert broken.read_bytes() == before
