"""The owner's plan catalog and the public plan link."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/common/tools"))

import lhc_plan_catalog as catalog  # noqa: E402
import lhc_plan_mirror as mirror  # noqa: E402

NOW = datetime(2026, 10, 27, 12, 0, tzinfo=timezone.utc)


def entry(tasks, updated_hours_ago=0.1, created_hours_ago=5, project="herder", name="plan-20261027-0700-aa"):
    stamp = lambda h: (NOW - timedelta(hours=h)).isoformat()
    return {"snapshot": {"project": project, "name": name, "last_file_event": stamp(updated_hours_ago),
                         "revisions": [{"id": "r001", "created_at": stamp(created_hours_ago)}],
                         "document": {"title": "План", "slots": 1, "tasks": tasks}},
            "receipt": {"received_at": stamp(updated_hours_ago)}}


def leaf(i, status, minutes=10, after=(), **extra):
    return {"id": f"L{i}", "label": f"Шаг {i}", "status": status,
            "estimate_minutes": minutes, "depends_on": list(after), **extra}


def test_states_follow_leaves_and_idle_time():
    running = entry([leaf(1, "done"), leaf(2, "running", started_at=NOW.isoformat())])
    assert catalog.summarize(running, NOW)["state"] == "active"
    assert catalog.summarize(entry([leaf(1, "done"), leaf(2, "queued")], updated_hours_ago=5), NOW)["state"] == "stalled"
    assert catalog.summarize(entry([leaf(1, "blocked", blocker="нет доступа")]), NOW)["state"] == "blocked"
    done = catalog.summarize(entry([leaf(1, "done"), leaf(2, "deferred")]), NOW)
    assert done["state"] == "completed" and (done["done"], done["total"]) == (1, 1)


def test_stage_and_eta_use_the_critical_path():
    item = catalog.summarize(entry([leaf(1, "running", 20, started_at=NOW.isoformat()),
                                    leaf(2, "queued", 10, ["L1"]), leaf(3, "queued", 5)]), NOW)
    assert item["stage"] == "Сейчас: Шаг 1"
    # one slot: all 35 minutes of work run one after another
    assert item["eta"] == NOW + timedelta(minutes=35)
    blocked = catalog.summarize(entry([leaf(1, "waiting", wait_reason="ответ владельца")]), NOW)
    assert blocked["stage"] == "Ждёт: ответ владельца" and blocked["eta"] is None


def test_page_has_filters_and_every_plan_once():
    page = catalog.render([entry([leaf(1, "running")]),
                           entry([leaf(1, "done")], project="noticeplace", name="plan-20261026-0900-bb")],
                          legacy=[("old", "plan-20261024-1600-cc", "Старый план")], now=NOW)
    assert page.count('<article class="plan') == 3
    for marker in ('id="project"', 'data-filter="active"', 'data-filter="stalled"', 'data-filter="completed"',
                   '<option value="noticeplace">', 'href="/old/plan-20261024-1600-cc/"', 'data-lhc-catalog="1"'):
        assert marker in page


def test_titles_are_escaped():
    hostile = entry([leaf(1, "done")])
    hostile["snapshot"]["document"]["title"] = '<script>alert(1)</script>'
    assert "<script>alert(1)</script>" not in catalog.render([hostile], now=NOW)


def test_plan_in_agents_tasks_gets_a_public_link_once(tmp_path, monkeypatch):
    config = tmp_path / "client.json"
    config.write_text(json.dumps({"mode": "mirror", "endpoint": "http://127.0.0.1:9", "base_url": "https://plans.example",
                                  "token_file": str(tmp_path / "t"), "data_dir": str(tmp_path / "data")}))
    monkeypatch.setenv("LHC_PLAN_MIRROR_CONFIG", str(config))
    plan = tmp_path / "repo/.agents/tasks/20261027-x"
    (plan / "leaves").mkdir(parents=True)
    (plan / "plan.json").write_text("{}")
    assert mirror.binding(plan) == config.resolve()
    url = mirror.link(plan)
    assert url.startswith("https://plans.example/") and url.endswith("/") and "plan-" in url
    assert mirror.link(plan) == url
    assert mirror.announce_once(plan) is True
    assert mirror.announce_once(plan) is False
    other = tmp_path / "elsewhere/plan"
    other.mkdir(parents=True)
    assert mirror.binding(other) is None
