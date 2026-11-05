"""The plan of a session is found by its binding, not by cwd; a running leaf is not released silently;
a link is not a working URL while sync is pending; recon needs evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
TOOLS = ROOT / "src" / "common" / "tools"
sys.path.insert(0, str(TOOLS))
import lhc_entry as entry  # noqa: E402
import lhc_plan_json as pj  # noqa: E402
import lhc_plan_mirror as mirror  # noqa: E402

SESSION = "01a1acbc-3689-7072-b786-54600cf55fa9"


def make_repo(path: Path) -> Path:
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    return path


def make_plan(repo: Path, status="running", session=SESSION) -> Path:
    plan = repo / ".agents/tasks/20261105-x"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text("{}")
    (plan / "leaves/L01.json").write_text(json.dumps({"id": "L01", "label": "x", "status": status, "session": session}))
    return plan


@pytest.fixture
def state(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    return tmp_path


def test_plan_in_another_project_holds_the_session_by_binding(state):
    a, b = make_repo(state / "A"), make_repo(state / "B")
    plan = make_plan(b, status="queued")
    event = {"cwd": str(a), "session_id": SESSION}
    assert entry.stop_gate(event, ROOT) is None           # no binding: cwd repo has no plan
    assert pj.record_session_plan(SESSION, plan, "L01")
    text = entry.stop_gate(event, ROOT)
    assert text and "L01" in text and plan.name in text
    assert entry._plan_entry(event, ROOT)["continuation"]["plan"] == str(plan.resolve())


def test_binding_is_written_by_create_leaf_and_a_stale_index_is_ignored(state):
    b = make_repo(state / "B")
    plan = make_plan(b, status="done")
    (plan / "leaves/L01.json").unlink()
    pj.update_leaf(plan, "L02", {"label": "x", "estimate_minutes": 10, "session": SESSION}, create=True)
    assert str(plan.resolve()) in pj.session_plans(SESSION)
    a = make_repo(state / "A")
    (plan / "leaves/L02.json").write_text(json.dumps({"id": "L02", "label": "x", "status": "done", "session": SESSION}))
    assert entry._plan_entry({"cwd": str(a), "session_id": SESSION}, ROOT)["candidates"] == []
    assert pj.session_plans("other") == []


def test_a_broken_index_fails_open(state):
    a = make_repo(state / "A")
    d = state / "state/lhc/sessions"
    d.mkdir(parents=True)
    (d / (SESSION + ".json")).write_text("{not json")
    assert entry.stop_gate({"cwd": str(a), "session_id": SESSION}, ROOT) is None


def test_running_leaf_is_held_past_stop_fires_until_escalated_or_closed(state):
    repo = make_repo(state / "repo")
    plan = make_plan(repo)
    event = {"cwd": str(repo), "session_id": SESSION}
    texts = [entry.stop_gate({**event, "stop_hook_active": True}, ROOT) for _ in range(entry.STOP_MAX)]
    assert all(texts), texts                                  # held every time, also after stop_hook_active
    assert "last reminder" in texts[-1] and "escalate and stop" in texts[-1]
    assert entry.stop_gate(event, ROOT) is None               # hard limit: no loop
    # an escalation letter on file releases earlier
    ev2 = {"cwd": str(repo), "session_id": SESSION + "-b"}
    (plan / "leaves/L01.json").write_text(json.dumps({"id": "L01", "status": "running", "session": SESSION + "-b"}))
    for _ in range(entry.STOP_FIRES):
        assert entry.stop_gate(ev2, ROOT)
    assert entry.stop_gate(ev2, ROOT)                         # still running, no letter
    sys.path.insert(0, str(TOOLS))
    import lhc_mail
    lhc_mail.send(repo, "DISPATCHER", SESSION + "-b", "question", "blocked on X")
    assert entry.stop_gate(ev2, ROOT) is None
    # closing the leaf releases too
    ev3 = {"cwd": str(repo), "session_id": SESSION + "-c"}
    (plan / "leaves/L01.json").write_text(json.dumps({"id": "L01", "status": "blocked", "session": SESSION + "-c"}))
    assert entry.stop_gate(ev3, ROOT) is None


def test_link_with_pending_sync_is_not_printed_as_a_working_url(state, capsys, monkeypatch):
    plan = state / "p"
    (plan / "leaves").mkdir(parents=True)
    assert mirror.link_ready(plan, "https://example.invalid/x/", 0, probe=lambda u: False) is False
    assert "not yet published (sync pending)" in mirror.pending_text(plan) and str(plan) in mirror.pending_text(plan)
    ticks = iter(range(0, 1000))
    calls = []
    assert mirror.link_ready(plan, "u", 45, probe=lambda u: calls.append(u) or len(calls) == 3,
                             clock=lambda: next(ticks), sleeper=lambda s: None) is True
    assert not mirror.published(plan)
    mirror.pub.atomic(mirror.directory(plan) / "mirror-state.json", {"last_successful_sync": "t"})
    assert mirror.published(plan)


def test_link_command_pending_branch_without_network(state, capsys, monkeypatch):
    plan = state / "p"
    (plan / "leaves").mkdir(parents=True)
    monkeypatch.setattr(mirror, "link", lambda p, c: "https://h/proj/plan-1/")
    monkeypatch.setattr(mirror, "probe_ok", lambda url, timeout=5: False)
    monkeypatch.setenv("LHC_LINK_WAIT_SECONDS", "0")
    assert mirror.main(["link", str(plan)]) == 0
    out = capsys.readouterr().out
    assert "https://" not in out and "sync pending" in out and "status/once" in out
    monkeypatch.setattr(mirror, "probe_ok", lambda url, timeout=5: True)
    assert mirror.main(["link", str(plan)]) == 0
    assert capsys.readouterr().out.strip() == "https://h/proj/plan-1/"


def _plan(tmp, **fields):
    (tmp / "plan.json").write_text(json.dumps({"title": "T", **fields}, ensure_ascii=False))


GOOD = ["сервис vpn активен и принимает подключения на порту 443 :: systemctl is-active vpn",
        "профили клиентов лежат в каталоге и читаются сервисом :: ls /etc/vpn/profiles",
        "xray слушает порт и отвечает на проверочный запрос :: curl -sI https://host:443"]


def test_trivial_recon_without_evidence_is_refused_and_with_evidence_passes(tmp_path):
    _plan(tmp_path, mode="fullcycle", recon=["сервис активен", "Xray активен"], acceptance_scenario="замер")
    with pytest.raises(pj.LeafError, match="каждый факт с доказательством"):
        pj.update_leaf(tmp_path, "L01", {"label": "m", "estimate_minutes": 15}, create=True)
    _plan(tmp_path, mode="fullcycle", recon=["короткий факт :: cmd", GOOD[1], GOOD[2]], acceptance_scenario="замер")
    with pytest.raises(pj.LeafError, match="короче 30"):
        pj.update_leaf(tmp_path, "L01", {"label": "m", "estimate_minutes": 15}, create=True)
    _plan(tmp_path, mode="fullcycle", recon=[GOOD[0], GOOD[1]], acceptance_scenario="замер")
    with pytest.raises(pj.LeafError, match="≥3 факта для fullcycle"):
        pj.update_leaf(tmp_path, "L01", {"label": "m", "estimate_minutes": 15}, create=True)
    _plan(tmp_path, mode="fullcycle", recon=[GOOD[0], GOOD[0], GOOD[1]], acceptance_scenario="замер")
    with pytest.raises(pj.LeafError, match="повторяется"):
        pj.update_leaf(tmp_path, "L01", {"label": "m", "estimate_minutes": 15}, create=True)
    _plan(tmp_path, mode="fullcycle", recon=GOOD, acceptance_scenario="замер")
    pj.update_leaf(tmp_path, "L01", {"label": "m", "estimate_minutes": 15}, create=True)


def test_old_format_recon_of_a_running_plan_only_warns(tmp_path, capsys):
    _plan(tmp_path, mode="fullcycle", recon=["файл a: есть", "команда b: вывод c"], acceptance_scenario="замер")
    (tmp_path / "leaves").mkdir()
    (tmp_path / "leaves/L01.json").write_text(json.dumps({"id": "L01", "label": "old", "status": "queued", "estimate_minutes": 10}))
    assert pj.build_document(tmp_path)["recon"] == ["файл a: есть", "команда b: вывод c"]
    pj.check_activation(tmp_path, {"id": "L01", "estimate_minutes": 10})
    assert "старом формате" in capsys.readouterr().err
    pj.update_leaf(tmp_path, "L02", {"label": "next", "estimate_minutes": 10}, create=True)
