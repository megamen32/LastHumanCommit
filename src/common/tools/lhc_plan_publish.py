#!/usr/bin/env python3
"""Unlisted static plan publication, immutable revisions, no MCP dependency."""
from __future__ import annotations
import argparse
import hashlib
import html
import importlib.util
import json
import os
from pathlib import Path
import re
import secrets
import shlex
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta

import lhc_plan_json as leaves
import lhc_plan_transport as transport

STATE_DIR = ".lhc-publication"
CONFIG = Path.home() / ".config/lhc/publish.json"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def atomic(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    leaves._write_atomic(path, encoded(value))


def slug(value):
    result = re.sub(r"[^a-z0-9-]+", "-", value.lower()).strip("-")[:48]
    return result or "project"


_GIT_LAYOUT = None
_GIT_LAYOUT_LOADED = False


def git_layout():
    """The reader of the layout of a repository, loaded from next to this file.

    The tool is loaded by path in the tests and as a neighbour in the package,
    so the neighbour cannot be found by a plain import in every environment.
    ``None`` means the neighbour is not there at all; every question is then
    answered by the git binary, the way it was answered before the reader
    existed.
    """
    global _GIT_LAYOUT, _GIT_LAYOUT_LOADED
    if not _GIT_LAYOUT_LOADED:
        _GIT_LAYOUT = _load_git_layout()
        _GIT_LAYOUT_LOADED = True
    return _GIT_LAYOUT


def _load_git_layout():
    """Load the reader of the layout of a repository from next to this file."""

    try:
        import lhc_gitlayout

        return lhc_gitlayout
    except ImportError:
        pass
    path = Path(__file__).resolve().with_name("lhc_gitlayout.py")
    try:
        spec = importlib.util.spec_from_file_location("lhc_gitlayout_sibling", path)
        if spec is None or spec.loader is None:
            return None
        module = sys.modules.get(spec.name)
        if module is None:
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
        return module
    except Exception:  # noqa: BLE001 - a missing reader is answered by git
        sys.modules.pop("lhc_gitlayout_sibling", None)
        return None


def project_slug(cwd):
    """The slug of the project that owns a directory.

    The name of the project is the name of the directory that holds the
    repository, and that is a fact about the directories on the disk, so it is
    read from there by the same reader every other tool of this package uses.
    A layout the reader does not model is answered by the git binary.
    """
    layout = git_layout()
    if layout is not None:
        try:
            common = layout.common_dir_of(Path(cwd))
        except OSError:
            common = None
        if common is not None:
            return slug(common.parent.name)
    try:
        result = subprocess.run(["git", "-C", str(cwd), "rev-parse", "--path-format=absolute", "--git-common-dir"], capture_output=True, text=True, timeout=3, check=True)
        return slug(Path(result.stdout.strip()).parent.name)
    except (OSError, subprocess.SubprocessError):
        return slug(Path(cwd).resolve().name)


def safe_text(value):
    # Publication is an allowlist of metadata, never a dump of source files.
    # Redact recognizable credentials and machine-local absolute paths even
    # when accidentally pasted into an authorized note. This is not a DLP claim.
    value = re.sub(r"(?i)\b(?:bearer\s+\S+|(?:api[_-]?key|password|token|secret)\s*[:=]\s*\S+)", "[скрыто]", value)
    value = re.sub(r"\b(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+", "[скрыто]", value)
    value = re.sub(r"(?<![\w:/])/(?:[A-Za-z0-9_.~-]+/)*[A-Za-z0-9_.~-]+", "[локальный путь]", value)
    value = re.sub(r"[A-Za-z]:\\[^\s]+", "[локальный путь]", value)
    value = re.sub(r"(https?://)[^\s/@]+:[^\s/@]+@", r"\1[скрыто]@", value)
    return value


def public_document(document):
    plan_keys = {"schema_version", "title", "goal", "business_result", "business_results", "current_progress", "external_waits", "slots", "updated_at", "leaf_count", "planned_start_at"}
    task_keys = set(leaves.LEAF_FIELDS) - {"affected_files", "blocker_details"}
    def clean(value):
        if isinstance(value, str):
            return safe_text(value)
        if isinstance(value, list):
            return [clean(v) for v in value]
        if isinstance(value, dict):
            return {k: clean(v) for k, v in value.items() if k not in {"affected_files", "blocker_details"} and not re.search(r"(?i)password|secret|credential|authorization|token|api.?key", k)}
        return value
    result = {k: clean(v) for k, v in document.items() if k in plan_keys}
    result["tasks"] = []
    for task in document["tasks"]:
        public_task = {k: clean(v) for k, v in task.items() if k in task_keys and k != "progress_events"}
        events = []
        for event in task.get("progress_events", []):
            public_event = {k: clean(v) for k, v in event.items() if k in {"at", "note", "session", "harness"}}
            public_event["changes"] = {k: clean(v) for k, v in event.get("changes", {}).items() if k in task_keys - {"progress_events"}}
            events.append(public_event)
        if events:
            public_task["progress_events"] = events
        result["tasks"].append(public_task)
    return result


def estimate(task):
    bounds = task.get("estimate_minutes")
    if isinstance(bounds, (float, int)):
        return float(bounds)
    if isinstance(bounds, dict):
        return bounds.get("maximum", bounds.get("minimum"))
    return None


def timestamp(value):
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return stamp if stamp.tzinfo else None
    except (ValueError, AttributeError):
        return None


def duration(task, at=None):
    start, end = timestamp(task.get("started_at")), timestamp(task.get("finished_at"))
    if start and not end and at and task.get("status") == "running":
        end = timestamp(at)
    return max(0, (end - start).total_seconds() / 60) if start and end and end >= start else None


def minutes(value):
    return "неизвестно" if value is None else f"{value:g} мин"


def forecast(doc):
    """Dependency-aware slot schedule via the existing renderer, never sum parallel time."""
    import lhc_grid
    graph = lhc_grid.parse_graph_json(schedule_document(doc))
    graph.resolve_dependencies()
    metrics = lhc_grid.build_metrics(graph)
    return metrics


def schedule_document(doc):
    result = json.loads(encoded(doc))
    for task in result["tasks"]:
        if task.get("duration_estimate_minutes") is not None:
            task["estimate_minutes"] = task["duration_estimate_minutes"]
    return result


def planning_facts(doc):
    keys = {"id", "label", "description", "acceptance", "depends_on", "estimate_minutes", "duration_estimate_minutes", "estimate_unknown_reason", "origin", "supersedes"}
    return {"goal": doc.get("goal"), "slots": doc.get("slots"), "planned_start_at": doc.get("planned_start_at"),
            "tasks": [{k: v for k, v in t.items() if k in keys} for t in doc["tasks"]]}


def comparison(baseline, selected, current, revisions, at, observed=None):
    esc = lambda v: html.escape(str(v), quote=True)
    by_original = {t["id"]: t for t in baseline["tasks"]}
    by_selected = {t["id"]: t for t in selected["tasks"]}
    by_actual = {t["id"]: t for t in current["tasks"]}
    # Keep removed leaves and facts as known in historical revisions visible.
    known = {}
    for revision in revisions:
        known.update({t["id"]: t for t in revision["document"]["tasks"]})
        known.update({k: v["task"] for k, v in revision.get("observed", {}).items()})
    observed = observed or {}
    known.update({k: v["task"] for k, v in observed.items()})
    known.update(by_actual)
    rows = []
    original_schedule = forecast(baseline)["schedule"]
    current_schedule = forecast(current)["schedule"]
    anchor = timestamp(baseline.get("planned_start_at"))
    for identity, historical in known.items():
        original, planned, actual = by_original.get(identity, {}), by_selected.get(identity, {}), by_actual.get(identity, historical)
        initial, revised = estimate(original), estimate(planned)
        elapsed = duration(actual, at)
        effort = actual.get("actual_minutes")
        diff = effort - initial if effort is not None and initial is not None else None
        status = {"running": "в работе", "done": "готово", "queued": "в очереди", "blocked": "заблокировано", "waiting": "ожидание", "deferred": "отложено"}.get(actual.get("status"), "неизвестно")
        if identity not in by_actual:
            status += " · удалён из текущего плана"
            status += " · последний наблюдённый факт " + observed.get(identity, {}).get("last_seen", "в снимке ревизии")
        if identity not in by_original:
            status += " · добавлен после исходного плана"
        planned_duration = original.get("duration_estimate_minutes", initial)
        delay = max(0, elapsed - planned_duration) if planned_duration is not None and elapsed is not None else None
        delay_text = "неизвестно" if delay is None else (("не менее " if actual.get("status") == "running" else "") + minutes(delay))
        original_start = original_schedule.starts.get(identity)
        original_finish = original_schedule.finishes.get(identity)
        planned_start = anchor + timedelta(minutes=original_start) if anchor and original_start is not None else None
        planned_finish = anchor + timedelta(minutes=original_finish) if anchor and original_finish is not None else None
        actual_start = timestamp(actual.get("started_at"))
        check_time = actual_start or (timestamp(at) if actual.get("status") in {"queued", "blocked", "waiting"} else None)
        start_delay = max(0, (check_time - planned_start).total_seconds() / 60) if check_time and planned_start else None
        start_delay_text = (("не менее " if not actual_start else "") + minutes(start_delay)) if start_delay is not None else "неизвестно"
        notes = "".join(f'<li>{esc(e.get("at", ""))}: {esc(e.get("note") or encoded(e.get("changes", {})))}</li>' for e in actual.get("progress_events", []))
        last_note = next((event.get("note") for event in reversed(actual.get("progress_events", [])) if event.get("note")), "")
        if last_note:
            notes = f'<p class="latest-progress">Последнее событие: {esc(last_note)}</p><details><summary>История изменений</summary><ul>{notes}</ul></details>'
        else:
            notes = f'<details><summary>История изменений</summary><ul>{notes}</ul></details>'
        completions = observed.get(identity, {}).get("completed", [])
        for completed in completions:
            old_effort = completed.get("actual_minutes")
            old_span = duration(completed)
            error = old_effort - initial if old_effort is not None and initial is not None else None
            notes += f'<p>Сохранённый завершённый факт: усилие {esc(minutes(old_effort))}, по часам {esc(minutes(old_span))}, ошибка исходной оценки {esc(minutes(error))}.</p>'
        scale = max([v for v in (initial, revised, elapsed) if v is not None] + [1])
        bars = "".join(f'<div class="compare-bar {kind}" style="width:{max(1, value / scale * 100):.2f}%">{label}: {esc(minutes(value))}</div>' for kind, label, value in (("baseline", "Оценка r001", initial), ("revised", "Выбранный план", revised), ("actual", "По часам", elapsed)) if value is not None)
        bars += f'<small>r001: +{esc(minutes(original_start))} → +{esc(minutes(original_finish))}<br>Текущий график: +{esc(minutes(current_schedule.starts.get(identity)))} → +{esc(minutes(current_schedule.finishes.get(identity)))}</small>'
        bars += f'<br><small>Исходный старт/финиш: {esc(planned_start.isoformat() if planned_start else "не заданы")} → {esc(planned_finish.isoformat() if planned_finish else "не задан")}; опоздание старта: {esc(start_delay_text)}</small>'
        rows.append(f'''<tr><td><b>{esc(identity)} · {esc(actual.get("label", ""))}</b><br>{esc(status)}
<br>{esc(actual.get("owner", "неизвестно"))} · {esc(actual.get("harness", "неизвестно"))} · {esc(actual.get("session", "неизвестно"))}
<br>{esc(actual.get("model", "неизвестно"))}<br>Зависит от: {esc(", ".join(planned.get("depends_on", [])) or "—")}
<br>Происхождение: {esc(actual.get("origin", ""))} {esc(", ".join(actual.get("supersedes", [])))}</td>
<td>{bars}</td><td>Усилие: {esc(minutes(effort))}<br>По часам: {esc(minutes(elapsed))}
<br>Ошибка оценки усилия: {esc(minutes(diff))}<br>Превышение длительности: {esc(delay_text)}
<br>{esc(actual.get("started_at", ""))} → {esc(actual.get("finished_at", ""))}</td>
<td>{esc(actual.get("note", ""))}<br>{esc(actual.get("blocker", ""))}{notes}</td></tr>''')
    def total_window(doc):
        starts = [timestamp(t.get("started_at")) for t in doc["tasks"]]
        ends = [timestamp(t.get("finished_at")) for t in doc["tasks"]]
        if not starts or not all(starts) or not all(ends) or any(t.get("status") != "done" for t in doc["tasks"]):
            return None
        return (max(ends) - min(starts)).total_seconds() / 60
    # Forecast anchored to the documented plan event, not browser wall time.
    def horizon(doc):
        m = forecast(doc)
        whole = m["delivery_minutes_max"] if m["duration_known"] else None
        remaining = m["remaining_minutes_max"] if m["remaining_known"] and not m["external_wait_unknown"] else None
        start = timestamp(doc.get("planned_start_at"))
        finish = (start + timedelta(minutes=whole)).isoformat() if start and whole is not None else "неизвестен"
        return f'длительность {minutes(whole)}, остаток {minutes(remaining)}; плановый финиш {esc(finish)}'
    return f'''<section id="plan-comparison"><h1>Исходный план → работа по факту</h1>
<p>Исходная цель: {esc(baseline.get("goal", ""))}</p>
<p>Прогноз исходного снимка: {horizon(baseline)}<br>Прогноз выбранной ревизии: {horizon(revisions[-1]['document'])}<br>Текущий прогноз: {horizon(current)}<br>Измеренная длительность всей поставки: {esc(minutes(total_window(current)))}</p>
<p>Усилие — измеренное время работы. По часам — от начала до конца, с ожиданиями; параллельные окна не складываются. Если отдельная длительность не задана, расписание опирается на оценку работы. Без дат время неизвестно.</p>
<div class="compare-scroll"><table class="comparison"><thead><tr><th>Работа / исполнитель</th><th>Оценки и время</th><th>Факт и отклонение от r001</th><th>Прогресс / ожидание</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div></section>'''


STYLE = '''<style>#publication,#plan-comparison{margin:24px auto;padding:24px;max-width:1400px;border:1px solid #64748b55;border-radius:18px;background:#101b30;color:#e2e8f0;font:15px/1.6 system-ui}#publication a{color:#7dd3fc;margin-right:14px}.compare-scroll{overflow:auto}.comparison{width:100%;border-collapse:collapse}.comparison td,.comparison th{padding:16px;text-align:left;vertical-align:top;border-bottom:1px solid #64748b55;min-width:190px}.compare-bar{border-radius:5px;padding:3px 7px;margin:6px 0;min-width:110px;color:#fff;font-size:12px}.baseline{background:#475569}.revised{background:#2563eb}.actual{background:#0f766e}#live-state{font-weight:600}#plan-comparison li{overflow-wrap:anywhere}.comparison td:first-child{overflow-wrap:anywhere}</style>'''


def page(baseline, selected, current, revisions, revision_id, updated, live, version="", observed=None):
    import lhc_grid
    graph = lhc_grid.parse_graph_json(schedule_document(selected))
    graph.resolve_dependencies()
    graph.source_path = "Публичный снимок плана"
    result = lhc_grid.render_html(graph, lhc_grid.build_metrics(graph))
    # Replace the existing self-HTML poller with metadata polling, HTTP only.
    result = re.sub(r'<script[^>]*id="lhc-live"[^>]*>.*?</script>', "", result, flags=re.S)
    links = '<a href="./">Текущий факт</a>' + ''.join(f'<a href="{r["id"]}.html">{r["id"]} · {html.escape(r["reason"])}</a>' for r in revisions)
    pending = planning_facts(current) != planning_facts(revisions[-1]["document"])
    pending_text = " · Есть изменения плана без новой ревизии" if pending else ""
    heading = ("Текущий план и факт · последняя ревизия " if live else "Снимок ") + revision_id
    panel = f'<section id="publication"><b>{heading}{pending_text}</b><p>{links}</p>Обновлено: <time id="publication-time">{html.escape(updated)}</time> · <span id="live-state">Снимок / офлайн</span><p>Доступ по ссылке: её получатель может передать её другим. Скрытие от поиска не является авторизацией.</p></section>'
    result = result.replace("</head>", '<meta name="robots" content="noindex,nofollow,noarchive">' + STYLE + "</head>")
    result = result.replace("<body>", "<body>" + panel + comparison(baseline, selected, current, revisions, updated, observed), 1)
    if live:
        result = result.replace("</body>", POLLER.replace("__VERSION__", version) + "</body>")
    return result


POLLER = '''<script id="lhc-publication-live">
(()=>{if(!/^https?:$/.test(location.protocol))return;
const badge=document.getElementById('live-state'); const version='__VERSION__';
const stamp=Date.parse(document.getElementById('publication-time').textContent);
let lastOK=0;
function status(){badge.textContent=!lastOK?'Проверка связи…':Date.now()-lastOK>30000?'Нет связи · сохранённый снимок':Date.now()-stamp>300000?'Давно не обновлялся · связь есть':'Связь есть';}
async function poll(){try{const r=await fetch('version.json',{cache:'no-store'});if(!r.ok)throw Error();const m=await r.json();lastOK=Date.now();
if(version!==m.version){try{sessionStorage.setItem('lhc-scroll:'+location.pathname,String(scrollY));}catch(e){}location.reload();return;}status();}catch(e){badge.textContent='Нет связи · сохранённый снимок';}}
try{const saved=sessionStorage.getItem('lhc-scroll:'+location.pathname);if(saved!==null){scrollTo(0,Number(saved));sessionStorage.removeItem('lhc-scroll:'+location.pathname);}}catch(e){}
poll();setInterval(poll,12000);setInterval(status,15000);})();
</script>'''


def load_revisions(directory):
    return [json.loads(p.read_text()) for p in sorted((directory / "revisions").glob("r*.json"))]


def freeze(directory, document, reason, observed=None):
    revisions = load_revisions(directory)
    revision = {"id": f"r{len(revisions)+1:03}", "reason": safe_text(reason), "created_at": now(), "document": document, "observed": observed or {}}
    path = directory / "revisions" / (revision["id"] + ".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create; the publishing lock serializes all revision changes.
    with path.open("x", encoding="utf-8") as stream:
        stream.write(encoded(revision))
    revisions.append(revision)
    snapshot = page(revisions[0]["document"], document, document, revisions, revision["id"], revision["created_at"], False, observed=observed)
    with path.with_suffix(".html").open("x", encoding="utf-8") as stream:
        stream.write(snapshot)
    return revision


def publish(plan_dir, config_path=None, *, autopublish=False, automatic=False, reason=None):
    plan_dir = Path(plan_dir).resolve()
    directory = plan_dir / STATE_DIR
    state_path = directory / "state.json"
    if automatic and not state_path.exists():
        return None
    with leaves.file_lock(directory / "publish.lock"):
        state = json.loads(state_path.read_text()) if state_path.exists() else None
        if automatic and not state.get("autopublish"):
            return None
        if automatic:
            # Tiny bounded coalescing window: subsequent builds hash the latest
            # leaves and skip unchanged delivery. No background daemon/timer.
            time.sleep(0.15)
        config_path = Path(config_path or (state or {}).get("config", CONFIG)).expanduser().resolve()
        config = json.loads(config_path.read_text())
        if set(config) - {"webroot", "base_url", "ssh_host"}:
            raise ValueError("unknown publish configuration fields")
        base_url = config["base_url"].rstrip("/")
        if not re.fullmatch(r"https?://[A-Za-z0-9.:-]+", base_url):
            raise ValueError("base_url must be an HTTP(S) origin")
        document = public_document(leaves.build_document(plan_dir))
        if state is None:
            identity = secrets.token_hex(12)
            state = {"project": project_slug(plan_dir), "name": datetime.now().strftime("plan-%Y%m%d-%H%M-") + identity, "identity": identity, "config": str(config_path), "autopublish": autopublish}
            atomic(state_path, state)  # Identity persists even if the transport fails.
        elif str(config_path) != state["config"]:
            raise ValueError("plan already bound to another config; edit the binding deliberately")
        if autopublish and not state["autopublish"]:
            state["autopublish"] = True
            atomic(state_path, state)
        revisions = load_revisions(directory)
        observed_path = directory / "observed.json"
        observed = json.loads(observed_path.read_text()) if observed_path.exists() else {}
        for task in document["tasks"]:
            previous = observed.get(task["id"], {})
            completed = list(previous.get("completed", []))
            if task.get("status") == "done":
                fact = {k: task[k] for k in ("actual_minutes", "started_at", "finished_at") if k in task}
                if fact and fact not in completed:
                    completed.append(fact)
            observed[task["id"]] = {"task": task, "last_seen": previous.get("last_seen", now()) if previous.get("task") == task else now(), "completed": completed}
        atomic(observed_path, observed)
        if not revisions:
            freeze(directory, document, "Исходный план", observed)
        elif reason:
            freeze(directory, document, reason, observed)
        revisions = load_revisions(directory)
        renderer_version = digest({p: Path(__file__).with_name(p).read_text() for p in ("lhc_plan_publish.py", "lhc_plan_transport.py", "lhc_grid.py")})
        version = digest({"document": document, "revisions": revisions, "renderer": renderer_version, "observed": observed})
        url = f'{base_url}/{state["project"]}/{state["name"]}/'
        if state.get("published_version") == version:
            return {"url": url, "version": version, "changed": False}
        updated = now()
        files = {p.name: p.read_text() for p in (directory / "revisions").glob("r*.html")}
        files["index.html"] = page(revisions[0]["document"], document, document, revisions, revisions[-1]["id"], updated, True, version, observed)
        files["version.json"] = encoded({"version": version, "updated_at": updated, "revision": revisions[-1]["id"]})
        payload = dict(webroot=config["webroot"], project=state["project"], name=state["name"], identity=state["identity"], version=version, files=files)
        host = config.get("ssh_host")
        if host:
            if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,99}", host):
                raise ValueError("ssh_host must be an existing safe SSH alias")
            source = Path(transport.__file__).read_text()
            subprocess.run(["ssh", "-oBatchMode=yes", "-oConnectTimeout=5", host, "python3 -c " + shlex.quote(source)], input=encoded(payload), text=True, capture_output=True, timeout=20, check=True)
        else:
            transport.deploy(**payload)
        state["published_version"], state["published_at"] = version, updated
        atomic(state_path, state)
        return {"url": url, "version": version, "changed": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("publish-html", "revise"):
        cmd = sub.add_parser(name)
        cmd.add_argument("plan_dir", type=Path)
        cmd.add_argument("--config", type=Path)
        cmd.add_argument("--autopublish", action="store_true")
        cmd.add_argument("--reason", required=name == "revise")
    args = parser.parse_args(argv)
    try:
        if args.command == "revise" and not (args.plan_dir / STATE_DIR / "state.json").exists():
            raise ValueError("publish r001 before revising")
        if args.command == "revise" and not args.reason.strip():
            raise ValueError("revision reason is required")
        print(encoded(publish(args.plan_dir, args.config, autopublish=args.autopublish, reason=args.reason if args.command == "revise" else None)), end="")
        return 0
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f"LHC: публикация не выполнена: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
