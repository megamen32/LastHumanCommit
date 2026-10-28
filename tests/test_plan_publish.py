"""Business invariants of the native CLI and optional publication facade."""
import concurrent.futures
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "src/common/tools"
sys.path.insert(0, str(TOOLS))
import lhc_plan_json as leaves
import lhc_plan_publish as publication
import lhc_plan_transport as transport


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False))


def test_herder_panel_uses_current_session_and_keeps_selection_safe():
    import lhc_plan_ui as ui
    tasks = [
        {'session': '01a182ff-be14-7171-9b7d-a4965f7363cd', 'harness': 'codex', 'status': 'queued', 'label': '<План>'},
        {'session': '01a182b0-5520-7e81-8d75-51bbe361d85b', 'harness': 'codex', 'status': 'running', 'label': 'Работа'},
        {'session': 'javascript:alert(1)', 'harness': 'codex', 'status': 'running'},
    ]
    panel = ui.herder_panel(tasks)
    assert 'https://agent.bezrabotnyi.com/?from=lhc#/session/codex%3A01a182b0-5520-7e81-8d75-51bbe361d85b' in panel
    assert panel.index('01a182b0-') < panel.index('01a182ff-')
    assert '&lt;План&gt;' in panel
    assert 'javascript:' not in panel
    assert '<iframe' in panel and '<iframe src=' not in panel
    assert 'Открыть отдельно' in panel
    assert 'herder-panel' in publication.POLLER


def test_herder_panel_does_not_guess_missing_or_remote_sessions():
    import lhc_plan_ui as ui
    panel = ui.herder_panel([{'session': 'unknown', 'harness': 'codex'},
                             {'session': 'codex:remote:host:01a182ff-be14-7171-9b7d-a4965f7363cd', 'harness': 'codex'}])
    assert 'disabled' in panel
    assert '#/session/' not in panel


@pytest.mark.parametrize('harness,session', [('codex', '01a182ff-be14-7171-9b7d-a4965f7363cd'),
                                          ('zcode', 'native-session_1'), ('opencode', 'ses_123Abc')])
def test_herder_panel_preserves_supported_native_harness(harness, session):
    import lhc_plan_ui as ui
    panel = ui.herder_panel([{'session': session, 'harness': harness, 'label': 'Исполнитель'}])
    assert f'https://agent.bezrabotnyi.com/?from=lhc#/session/{harness}%3A{session}' in panel
    assert ' disabled' not in panel


def test_herder_panel_does_not_default_unknown_harness():
    import lhc_plan_ui as ui
    assert 'disabled' in ui.herder_panel([{'session': 'ses_123Abc', 'harness': 'other'}])


def test_historical_view_opens_current_working_session(plan):
    import copy
    path, _ = plan
    baseline = leaves.build_document(path)
    current = copy.deepcopy(baseline)
    current['tasks'][0].update(session='01a182ff-be14-7171-9b7d-a4965f7363cd', harness='codex', status='running')
    revisions = [{'id': 'r001', 'document': baseline, 'reason': 'Исходный план', 'created_at': '2026-10-28T12:00:00Z'}]
    page = publication.page(baseline, baseline, current, revisions, 'r001', '2026-10-28T12:00:00Z', False)
    assert 'codex%3A01a182ff-be14-7171-9b7d-a4965f7363cd' in page
    assert page.count('id="herder-launch"') == 1
    assert 'id="lhc-herder-panel"' in page


@pytest.fixture
def plan(tmp_path):
    path = tmp_path / "safe-plan"
    write(path / "plan.json", {"title": "Проверка публикации", "goal": "Читать план на телефоне", "slots": 2, "updated_at": "2026-10-24T10:00:00Z"})
    for identity, parents in (("L01", []), ("L02", []), ("L03", ["L01", "L02"])):
        write(path / "leaves" / (identity + ".json"), {"id": identity, "label": "Работа " + identity, "depends_on": parents, "status": "queued", "estimate_minutes": 10})
    config = tmp_path / "publish.json"
    write(config, {"webroot": str(tmp_path / "web"), "base_url": "https://lhc.example"})
    return path, config


def destination(path, config):
    state = json.loads((path / publication.STATE_DIR / "state.json").read_text())
    return Path(json.loads(config.read_text())["webroot"]) / state["project"] / state["name"]


def cli(script, *args):
    return subprocess.run([sys.executable, str(TOOLS / script), *map(str, args)], capture_output=True, text=True)


def test_baseline_progress_replan_and_idempotency(plan):
    path, config = plan
    first = publication.publish(path, config, autopublish=True)
    dest = destination(path, config)
    frozen = (dest / "r001.html").read_bytes()
    baseline_json = (path / publication.STATE_DIR / "revisions/r001.json").read_bytes()
    assert publication.publish(path, config)["changed"] is False
    assert len(first["url"].rstrip("/").split("-")[-1]) == 24
    leaves.update_leaf(path, "L01", {"status": "running", "started_at": "2026-10-24T10:00:00Z"}, note="Сборка началась")
    leaves.build_graph(path)
    assert "Сборка началась" in (dest / "index.html").read_text()
    assert (dest / "r001.html").read_bytes() == frozen
    assert len(publication.load_revisions(path / publication.STATE_DIR)) == 1
    leaves.update_leaf(path, "L01", {"estimate_minutes": 50, "actual_minutes": 30, "status": "done", "finished_at": "2026-10-24T10:20:00Z"})
    publication.publish(path, config, reason="Изменилась оценка оставшейся работы")
    assert (dest / "r001.html").read_bytes() == frozen
    assert (path / publication.STATE_DIR / "revisions/r001.json").read_bytes() == baseline_json
    assert (dest / "r002.html").exists()
    page = (dest / "index.html").read_text()
    assert "Ошибка оценки усилия: 20 мин" in page
    assert "Превышение длительности: 10 мин" in page
    assert "L01, L02" in page
    assert json.loads(baseline_json)["document"]["tasks"][-1]["depends_on"] == ["L01", "L02"]


def test_last_good_on_invalid_leaf(plan):
    path, config = plan
    publication.publish(path, config, autopublish=True)
    dest = destination(path, config)
    before = dest.resolve()
    (path / "leaves/L01.json").write_text("{")
    with pytest.raises(ValueError):
        publication.publish(path, config)
    assert dest.resolve() == before


def test_atomic_updates_conflict_and_concurrency(plan):
    path, _ = plan
    original = (path / "leaves/L01.json").read_bytes()
    stale = hashlib.sha256(original).hexdigest()
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda n: leaves.update_leaf(path, "L01", {}, note=f"note-{n}"), range(16)))
    current = json.loads((path / "leaves/L01.json").read_text())
    assert len(current["progress_events"]) == 16
    assert len({e["note"] for e in current["progress_events"]}) == 16
    with pytest.raises(ValueError, match="конфликт"):
        leaves.update_leaf(path, "L01", {"note": "stale"}, expected_hash=stale)
    with pytest.raises(ValueError):
        leaves.update_leaf(path, "L01", {"depends_on": ["missing"]})
    assert json.loads((path / "leaves/L01.json").read_text()) == current


def test_iso_midnight_unknown_and_delay():
    task = {"started_at": "2026-10-24T23:55:00+03:00", "finished_at": "2026-10-25T00:10:00+03:00"}
    assert publication.duration(task) == 15
    assert publication.duration({"started_at": "23:55", "finished_at": "00:10"}) is None
    assert publication.duration({"status": "done", "actual_minutes": 80}) is None
    assert publication.duration({"status": "running", "started_at": "2026-10-24T00:00:00Z"}, "2026-10-24T01:00:00Z") == 60
    leaves.task_from_leaf({"id": "L01", "label": "x", **task}, Path("L01.json"))


def test_public_safety_and_offline_snapshot(plan):
    path, config = plan
    leaves.update_leaf(path, "L01", {"note": '</script><script>alert("x")</script> /home/private/file token=hidden-value', "affected_files": ["/home/private/source.py"]})
    publication.publish(path, config)
    dest = destination(path, config)
    page = (dest / "index.html").read_text()
    assert '<script>alert("x")' not in page
    assert "&lt;script&gt;" in page
    assert "/home/private" not in page and "hidden-value" not in page
    assert 'content="noindex,nofollow,noarchive"' in page
    assert "cache:'no-store'" in page and "12000" in page
    assert 'id="lhc-live"' not in page
    frozen = (dest / "r001.html").read_text()
    assert "fetch(" not in frozen
    assert "Исходный план" in frozen and "Gantt" in page or "gantt" in page


@pytest.mark.parametrize("identity", ["../escape", "a/b", "x;touch x", "/root", ".hidden"])
def test_path_traversal(plan, identity):
    path, _ = plan
    with pytest.raises(ValueError):
        leaves.update_leaf(path, identity, {"label": "unsafe"}, create=True)


def test_collision_rejected(plan):
    path, config = plan
    publication.publish(path, config)
    dest = destination(path, config)
    (dest / ".lhc-owner").write_text("another-owner")
    leaves.update_leaf(path, "L01", {}, note="changed")
    with pytest.raises(ValueError, match="collision"):
        publication.publish(path, config)


def test_native_cli_and_mcp_stdio_parity(plan):
    path, config = plan
    direct = cli("lhc_plan_publish.py", "publish-html", path, "--config", config)
    assert direct.returncode == 0, direct.stderr
    expected = cli("lhc_plan_publish.py", "publish-html", path)
    messages = [
        {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-03-26"}},
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "publish_html", "arguments": {"plan_dir": str(path)}}},
        {"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "update_progress", "arguments": {"plan_dir": str(path), "leaf_id": "L02", "note": "из MCP"}}},
    ]
    result = subprocess.run([sys.executable, str(TOOLS / "lhc_plan_mcp.py")], input="\n".join(map(json.dumps, messages)) + "\n", capture_output=True, text=True)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(replies) == 4, result.stderr
    assert replies[0]["result"]["protocolVersion"] == "2025-03-26"
    assert "publish_html" in {t["name"] for t in replies[1]["result"]["tools"]}
    assert replies[2]["result"]["structuredContent"]["stdout"] == expected.stdout
    assert replies[3]["result"]["isError"] is False
    assert json.loads((path / "leaves/L02.json").read_text())["progress_events"][-1]["note"] == "из MCP"


def test_project_slug_uses_primary_root():
    root = TOOLS.parents[2]
    if root.name.lower() != "lasthumancommit":
        pytest.skip("checkout folder is not named after the repository")
    assert publication.project_slug(root) == "lasthumancommit"


def test_public_modes_private_umask_and_bounded_generations(plan):
    path, config = plan
    old_mask = os.umask(0o077)
    try:
        publication.publish(path, config)
        dest = destination(path, config)
        assert dest.parent.stat().st_mode & 0o777 == 0o755
        assert dest.stat().st_mode & 0o777 == 0o755
        assert (dest / "index.html").stat().st_mode & 0o777 == 0o644
        assert (dest / ".lhc-owner").stat().st_mode & 0o777 == 0o600
        original = (dest / "r001.html").read_bytes()
        for n in range(4):
            leaves.update_leaf(path, "L01", {}, note=f"update {n}")
            publication.publish(path, config)
        assert len(list(dest.parent.glob(".bundle-*"))) == 2
        assert (dest / "r001.html").read_bytes() == original
    finally:
        os.umask(old_mask)


def test_untrusted_history_fields_are_not_published(plan):
    path, config = plan
    raw_path = path / "leaves/L01.json"
    raw = json.loads(raw_path.read_text())
    raw["progress_events"] = [{"at": "now", "note": "safe", "changes": {"password": "plainvalue", "private_payload": {"credential": "another-value"}, "estimate_minutes": {"maximum": 10, "password": "nested-value"}}}]
    write(raw_path, raw)
    publication.publish(path, config)
    page = (destination(path, config) / "index.html").read_text()
    for value in ("plainvalue", "another-value", "nested-value"):
        assert value not in page
    with pytest.raises(ValueError):
        leaves.update_leaf(path, "L01", {"password": "bad"})


def test_unrevised_planning_and_unknown_forecast(plan):
    path, config = plan
    publication.publish(path, config)
    leaves.update_leaf(path, "L01", {"estimate_minutes": 50})
    publication.publish(path, config)
    page = (destination(path, config) / "index.html").read_text()
    assert "Есть изменения плана без новой ревизии" in page
    assert "Выбранный план: 50 мин" in page
    assert len(publication.load_revisions(path / publication.STATE_DIR)) == 1
    raw_path = path / "leaves/L01.json"
    raw = json.loads(raw_path.read_text())
    raw.pop("estimate_minutes")
    write(raw_path, raw)
    publication.publish(path, config)
    assert "длительность неизвестно" in (destination(path, config) / "index.html").read_text()


def test_queued_start_delay_requires_explicit_schedule_anchor(plan):
    path, config = plan
    raw = json.loads((path / "plan.json").read_text())
    raw["planned_start_at"] = "2026-01-01T00:00:00Z"
    write(path / "plan.json", raw)
    publication.publish(path, config)
    page = (destination(path, config) / "index.html").read_text()
    assert "опоздание старта: не менее" in page
    assert "2026-01-01T00:00:00+00:00" in page


def test_comparison_uses_absolute_origin_and_dependency_schedule():
    doc = {'schema_version': 2, 'slots': 2,
           'plan_origin': {'at': '2026-10-25T16:30:00+03:00', 'source': 'file_birthtime'},
           'tasks': [{'id': name, 'label': name, 'status': 'queued',
                      'depends_on': deps, 'estimate_minutes': 15}
                     for name, deps in [('L01', []), ('L02', []), ('L03', ['L01', 'L02'])]]}
    revisions = [{'document': doc}]
    page = publication.comparison(doc, doc, doc, revisions, '2026-10-25T16:35:00+03:00')
    assert 'плановый финиш неизвестен' not in page
    assert page.count('плановый финиш 2026-10-25T17:00:00+03:00') == 2
    assert 'Текущий прогноз: длительность 30 мин, остаток 30 мин; прогноз финиша 2026-10-25T17:00:00+03:00' in page
    assert 'по началу плана' in page
    assert '2026-10-25T16:45:00+03:00' in page
    doc['planned_start_at'] = '2026-10-25T17:00:00+03:00'
    explicit = publication.comparison(doc, doc, doc, revisions, '2026-10-25T16:35:00+03:00')
    assert explicit.count('плановый финиш 2026-10-25T17:30:00+03:00') == 2
    del doc['planned_start_at']
    doc['plan_origin']['at'] = '2026-10-27T00:00:00Z'
    future = publication.comparison(doc, doc, doc, revisions, '2026-10-25T16:35:00+03:00')
    assert future.count('плановый финиш неизвестен') == 2


def test_comparison_current_forecast_matches_dashboard_after_progress():
    doc = {'schema_version': 2, 'updated_at': '2026-10-25T16:50:00+03:00',
           'plan_origin': {'at': '2026-10-25T16:30:00+03:00', 'source': 'file_birthtime'},
           'tasks': [{'id': 'L01', 'label': 'Работа', 'status': 'running', 'estimate_minutes': 20}]}
    expected = publication.forecast(doc)['time_frame']['end']
    assert expected == '2026-10-25T17:10:00+03:00'
    page = publication.comparison(doc, doc, doc, [{'document': doc}], '2026-10-25T16:55:00+03:00')
    assert f'Текущий прогноз: длительность 20 мин, остаток 20 мин; прогноз финиша {expected}' in page


def test_removed_leaf_keeps_last_observed_fact_and_reset_keeps_completion(plan):
    path, config = plan
    publication.publish(path, config, autopublish=True)
    r1 = (destination(path, config) / "r001.html").read_bytes()
    leaves.update_leaf(path, "L01", {"status": "done", "actual_minutes": 20,
                       "started_at": "2026-10-24T10:00:00Z", "finished_at": "2026-10-24T10:30:00Z"})
    leaves.build_graph(path)  # The last observed fact, after r001.
    leaves.update_leaf(path, "L03", {"depends_on": ["L02"], "supersedes": ["L01"]})
    (path / "leaves/L01.json").unlink()
    publication.publish(path, config, reason="Лист разделён после завершения")
    dest = destination(path, config)
    page = (dest / "index.html").read_text()
    assert "удалён из текущего плана" in page
    assert "последний наблюдённый факт" in page
    assert "Сохранённый завершённый факт: усилие 20 мин, по часам 30 мин" in page
    assert "ошибка исходной оценки 10 мин" in page
    assert (dest / "r001.html").read_bytes() == r1
    r2 = publication.load_revisions(path / publication.STATE_DIR)[-1]
    assert r2["observed"]["L01"]["task"]["actual_minutes"] == 20
    assert r2["observed"]["L01"]["task"]["status"] == "done"
    leaves.update_leaf(path, "L01", {"label": "Повторная работа", "status": "queued"}, create=True)
    publication.publish(path, config)
    assert "Сохранённый завершённый факт: усилие 20 мин" in (dest / "index.html").read_text()


def test_separate_effort_and_iso_delivery_window():
    import lhc_grid
    item = lhc_grid.Leaf(id="L01", label="test", started_at="2026-10-24T23:55:00+03:00", finished_at="2026-10-26T00:10:00+03:00")
    assert item.actual_span_minutes == 1455
    graph = lhc_grid.parse_graph_json({"schema_version": 2, "slots": 2, "tasks": [{"id": "L01", "label": "one", "status": "running", "harness": "codex", "session": "same"}, {"id": "L02", "label": "two", "status": "running", "harness": "codex", "session": "same"}]})
    graph.resolve_dependencies()
    assert lhc_grid.build_metrics(graph)["current_parallel"] == 1


def test_remote_transport_same_core_safe_arguments(plan, monkeypatch):
    path, config = plan
    raw = json.loads(config.read_text())
    raw["ssh_host"] = "existing-alias"
    raw["webroot"] += " space;literal"
    write(config, raw)
    native_run = subprocess.run
    calls = []
    def remote(argv, **kwargs):
        if argv[0] != "ssh":
            return native_run(argv, **kwargs)
        import shlex
        calls.append(argv)
        assert argv[3] == "existing-alias"
        return native_run(shlex.split(argv[4]), **kwargs)
    monkeypatch.setattr(subprocess, "run", remote)
    publication.publish(path, config)
    assert calls and (destination(path, config) / "index.html").exists()


def test_packaged_stdio_outside_source_checkout(plan, tmp_path):
    import shutil
    path, config = plan
    package = tmp_path / "portable"
    shutil.copytree(TOOLS.parents[2] / "plugins/last-human-commit", package)
    messages = [{"jsonrpc": "2.0", "id": 1, "method": "initialize"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "publish_html", "arguments": {"plan_dir": str(path), "config": str(config)}}}]
    env = {**os.environ, "PYTHONPATH": ""}
    result = subprocess.run([sys.executable, str(package / "scripts/plan_publish_mcp.py")], cwd=tmp_path, env=env,
                            input="\n".join(map(json.dumps, messages)) + "\n", text=True, capture_output=True)
    replies = [json.loads(line) for line in result.stdout.splitlines()]
    assert len(replies) == 3, result.stderr
    assert not replies[-1]["result"]["isError"], replies[-1]
    assert (destination(path, config) / "index.html").exists()
