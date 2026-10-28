#!/usr/bin/env python3
"""The owner's directives of one project: live ones with a term, ended ones in history.

One store per project lives on the plan mirror server, so the owner edits it in
the web page and every agent on every host reads the same list. A directive is
either permanent or has an end time; when the end time passes it moves to the
history and agents stop seeing it. Agents read only the live list.

Commands (client): show | add | end   (project defaults to the current repository)
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import html
import json
import os
from pathlib import Path
import sys
import urllib.error
import urllib.request

RECENT = timedelta(hours=24)  # an ended directive stays visible this long, with its on_expire
CACHE = Path.home() / ".cache/lhc/directives"


def utc(value=None):
    value = value or datetime.now(timezone.utc)
    return value.astimezone(timezone.utc)


def stamp(value):
    return utc(value).isoformat(timespec="seconds")


def parse_time(value):
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.astimezone()


def parse_until(value, now=None):
    """'permanent', an ISO time, or '+<n>h' / '+<n>d' from now. Anything else is an error."""
    now = utc(now)
    text = str(value or "").strip().lower()
    if text in {"permanent", "бессрочно"}:
        return None
    if text.startswith("+") and text[-1] in "hd" and text[1:-1].isdigit():
        amount = int(text[1:-1])
        return stamp(now + (timedelta(hours=amount) if text[-1] == "h" else timedelta(days=amount)))
    if not text:
        raise ValueError("a directive needs an end time or 'permanent'")
    return stamp(parse_time(text))


def empty():
    return {"active": [], "history": []}


def load(path):
    path = Path(path)
    if not path.exists():
        return empty()
    value = json.loads(path.read_text(encoding="utf-8"))
    return {"active": list(value.get("active", [])), "history": list(value.get("history", []))}


def save(path, doc):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def next_id(doc):
    used = {item["id"] for item in doc["active"] + doc["history"]}
    number = 1
    while f"d{number}" in used:
        number += 1
    return f"d{number}"


def end(doc, ident, reason, now=None):
    for item in doc["active"]:
        if item["id"] == ident:
            doc["active"].remove(item)
            doc["history"].insert(0, {**item, "ended": stamp(now), "reason": reason})
            return item
    raise KeyError(ident)


def sweep(doc, now=None):
    """Move every directive whose end time has passed to the history."""
    now = utc(now)
    moved = [item for item in doc["active"] if item.get("until") and parse_time(item["until"]) <= now]
    for item in moved:
        end(doc, item["id"], "expired", now)
    return moved


def add(doc, text, until, on_expire="", now=None):
    text = str(text or "").strip()
    if not text:
        raise ValueError("empty directive")
    item = {"id": next_id(doc), "text": text, "added": stamp(now),
            "until": parse_until(until, now), "on_expire": str(on_expire or "").strip()}
    doc["active"].insert(0, item)
    return item


def update(doc, ident, **fields):
    for item in doc["active"]:
        if item["id"] == ident:
            if "text" in fields and str(fields["text"]).strip():
                item["text"] = str(fields["text"]).strip()
            if "until" in fields:
                item["until"] = parse_until(fields["until"])
            if "on_expire" in fields:
                item["on_expire"] = str(fields["on_expire"] or "").strip()
            return item
    raise KeyError(ident)


def view(doc, now=None):
    """What an agent or the page sees: live directives and the ones that ended in the last day."""
    now = utc(now)
    recent = [item for item in doc["history"]
              if item.get("reason") == "expired" and now - parse_time(item["ended"]) <= RECENT]
    return {"active": doc["active"], "just_ended": recent, "history": doc["history"]}


def apply(doc, request, now=None):
    """One owner action: add | update | end | done. Returns the new view."""
    now = utc(now)
    action = request.get("action")
    if action == "add":
        add(doc, request.get("text"), request.get("until"), request.get("on_expire", ""), now)
    elif action == "update":
        fields = {key: request[key] for key in ("text", "until", "on_expire") if key in request}
        update(doc, str(request.get("id")), **fields)
    elif action in {"end", "done"}:
        end(doc, str(request.get("id")), "cancelled" if action == "end" else "done", now)
    else:
        raise ValueError("unknown action")
    sweep(doc, now)
    return view(doc, now)


def context(snapshot):
    """The text an agent reads. Empty when there is nothing live and nothing just ended."""
    lines = []
    for item in snapshot["active"]:
        term = "permanent" if not item.get("until") else "until " + item["until"]
        lines.append(f"- [{item['id']}] {item['text']} ({term})")
    ended = [f"- [{item['id']}] {item['text']} -> {item.get('on_expire') or 'the directive has ended: undo what it changed'}"
             for item in snapshot["just_ended"]]
    if not lines and not ended:
        return ""
    text = "LHC owner directives (live; they win over older notes, ended ones are in history and not binding):\n"
    text += "\n".join(lines) if lines else "- none live"
    if ended:
        text += "\nJust ended: do what it says now.\n" + "\n".join(ended)
    return text


# --- web page ---------------------------------------------------------------

PAGE = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Указания: __PROJECT__</title><style>
:root{color-scheme:light dark;--bg:#f6f7f9;--card:#fff;--ink:#171a21;--mute:#667085;--line:#e3e6ec;--acc:#2563eb;--warn:#b45309}
@media(prefers-color-scheme:dark){:root{--bg:#0f1115;--card:#171a21;--ink:#e7e9ee;--mute:#98a2b3;--line:#2a2f3a;--acc:#6ea0ff;--warn:#f5a54a}}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,sans-serif}main{max-width:760px;margin:0 auto;padding:20px 16px 60px}
h1{font-size:20px;margin:0 0 4px}.sub{color:var(--mute);margin:0 0 18px}a{color:var(--acc)}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 14px;margin:10px 0}
.card .t{white-space:pre-wrap;word-break:break-word}.meta{color:var(--mute);font-size:13px;margin-top:6px}.meta b{color:var(--ink);font-weight:600}
.soon{color:var(--warn)}textarea,input,select,button{font:inherit;color:inherit}textarea,input,select{width:100%;box-sizing:border-box;background:var(--bg);border:1px solid var(--line);border-radius:8px;padding:8px}
button{border:1px solid var(--line);background:var(--card);border-radius:8px;padding:6px 12px;cursor:pointer}button.go{background:var(--acc);border-color:var(--acc);color:#fff}
.row{display:flex;gap:8px;flex-wrap:wrap;margin-top:8px}.row>*{flex:1 1 160px}.row .fit{flex:0 0 auto}h2{font-size:16px;margin:24px 0 4px}details summary{cursor:pointer;color:var(--mute)}
</style></head><body><main>
<h1>Указания · __PROJECT__</h1><p class="sub">Агенты читают только то, что здесь действует. Просроченное уходит в историю само. <a href="/directives/">все проекты</a> · <a href="/">планы</a></p>
<div class="card"><textarea id="text" rows="3" placeholder="Новое указание, например: сервис X выключен, не включать"></textarea>
<div class="row"><select id="mode"><option value="permanent">бессрочно</option><option value="+6h">6 часов</option><option value="+1d">1 день</option><option value="+2d">2 дня</option><option value="+7d">неделя</option><option value="at">до даты…</option></select>
<input id="at" type="datetime-local" hidden><input id="exp" placeholder="Когда срок выйдет, агент должен: …"><button class="go fit" id="add">Добавить</button></div></div>
<h2>Действует</h2><div id="live"></div><h2>Только что закончилось</h2><div id="ended"></div>
<details><summary>История указаний</summary><div id="hist"></div></details>
<script>
const P=__PROJECT_JSON__,U='/directives/'+P+'/',$=i=>document.getElementById(i);
const esc=s=>String(s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const fmt=s=>s?new Date(s).toLocaleString('ru-RU',{dateStyle:'short',timeStyle:'short'}):'бессрочно';
async function call(b){const r=await fetch(U,{method:'POST',headers:{'Content-Type':'application/json','X-LHC-Directives':'1'},body:JSON.stringify(b)});if(r.status===401){location.reload();return}if(!r.ok){alert((await r.json()).error||'ошибка');return}draw(await r.json())}
function card(i,live){const left=i.until?Math.round((new Date(i.until)-Date.now())/36e5):null;
 return '<div class="card"><div class="t">'+esc(i.text)+'</div><div class="meta">'+(live?'до <b class="'+(left!==null&&left<6?'soon':'')+'">'+fmt(i.until)+'</b>':'закончилось <b>'+fmt(i.ended)+'</b> · '+esc(i.reason||''))+(i.on_expire?' · потом: '+esc(i.on_expire):'')+'</div>'+
 (live?'<div class="row"><button class="fit" data-a="edit" data-id="'+i.id+'">Изменить</button><button class="fit" data-a="done" data-id="'+i.id+'">Выполнено</button><button class="fit" data-a="end" data-id="'+i.id+'">Отменить</button></div>':'')+'</div>'}
let cur={active:[]};
function draw(v){cur=v;$('live').innerHTML=v.active.map(i=>card(i,1)).join('')||'<p class="sub">Ничего не действует.</p>';$('ended').innerHTML=v.just_ended.map(i=>card(i,0)).join('')||'<p class="sub">—</p>';$('hist').innerHTML=v.history.map(i=>card(i,0)).join('')||'<p class="sub">Пусто.</p>'}
$('mode').onchange=()=>{$('at').hidden=$('mode').value!=='at'};
$('add').onclick=async()=>{let u=$('mode').value;if(u==='at'){if(!$('at').value){alert('Укажи дату');return}u=new Date($('at').value).toISOString()}
 await call({action:'add',text:$('text').value,until:u,on_expire:$('exp').value});$('text').value='';$('exp').value=''};
document.body.onclick=async e=>{const b=e.target.closest('button[data-a]');if(!b)return;const id=b.dataset.id,a=b.dataset.a,it=cur.active.find(x=>x.id===id);
 if(a==='edit'){const t=prompt('Текст указания',it.text);if(t===null)return;const w=prompt('Срок: permanent, +2d, +6h или дата ISO',it.until||'permanent');if(w===null)return;await call({action:'update',id,text:t,until:w})}
 else if(confirm(a==='done'?'Отметить выполненным?':'Отменить указание?'))await call({action:a,id})};
draw(__VIEW__);
</script></main></body></html>
"""

INDEX = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Указания</title><style>:root{color-scheme:light dark}body{margin:0;font:15px/1.5 system-ui,sans-serif;background:Canvas;color:CanvasText}
main{max-width:640px;margin:0 auto;padding:20px 16px}a{display:block;padding:12px 14px;margin:8px 0;border:1px solid color-mix(in srgb,CanvasText 18%,transparent);border-radius:12px;text-decoration:none;color:inherit}
small{opacity:.65}</style></head><body><main><h1>Указания владельца</h1><p><a href="/" style="display:inline;border:0;padding:0">← планы</a></p>__ROWS__
<form onsubmit="location='/directives/'+encodeURIComponent(this.p.value.trim().toLowerCase())+'/';return false"><p><input name="p" placeholder="новый проект" style="padding:8px"> <button>Открыть</button></p></form></main></body></html>
"""


def page(project, snapshot):
    return (PAGE.replace("__PROJECT_JSON__", json.dumps(project)).replace("__PROJECT__", html.escape(project))
            .replace("__VIEW__", json.dumps(snapshot, ensure_ascii=False).replace("</", "<\\/")))


def index(counts):
    rows = "".join(f'<a href="/directives/{html.escape(name)}/">{html.escape(name)} <small>— действует: {count}</small></a>'
                   for name, count in sorted(counts.items()))
    return INDEX.replace("__ROWS__", rows or "<p><small>Проектов пока нет.</small></p>")


# --- client -----------------------------------------------------------------

def client_config():
    path = Path(os.environ.get("LHC_PLAN_MIRROR_CONFIG", Path.home() / ".config/lhc/plan-mirror/client.json")).expanduser()
    cfg = json.loads(path.read_text(encoding="utf-8"))
    token = Path(cfg["token_file"]).expanduser().read_text(encoding="utf-8").strip()
    return cfg, token


def request(project, body=None, timeout=3):
    cfg, token = client_config()
    url = cfg["endpoint"].rstrip("/") + "/v1/directives/" + project
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers={"Authorization": "Bearer " + token,
                                                          "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read())


def fetch(project, timeout=2):
    """The live view from the server; the last answer from disk when the server cannot be reached."""
    cache = CACHE / (project + ".json")
    try:
        snapshot = request(project, timeout=timeout)
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(snapshot, ensure_ascii=False), encoding="utf-8")
        return snapshot
    except (OSError, ValueError, KeyError, urllib.error.URLError):
        if cache.exists():
            try:
                snapshot = json.loads(cache.read_text(encoding="utf-8"))
                # The cache can be old: drop what has ended since it was written.
                doc = {"active": snapshot["active"], "history": snapshot.get("history", [])}
                sweep(doc)
                return view(doc)
            except (OSError, ValueError, KeyError):
                return None
        return None


def project_of(cwd):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import lhc_plan_publish as pub
    return pub.project_slug(cwd)


def session_context(cwd):
    """Directive text for a session hook; empty on any failure, never raises."""
    try:
        snapshot = fetch(project_of(cwd))
        return context(snapshot) if snapshot else ""
    except Exception:  # noqa: BLE001 - a hook must not fail a session
        return ""


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("show", "add", "end"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--project")
        if name == "add":
            cmd.add_argument("text")
            cmd.add_argument("--until", required=True, help="permanent, +2d, +6h or an ISO time")
            cmd.add_argument("--on-expire", default="")
        if name == "end":
            cmd.add_argument("id")
            cmd.add_argument("--done", action="store_true")
    args = parser.parse_args(argv)
    project = args.project or project_of(Path.cwd())
    try:
        if args.command == "show":
            snapshot = fetch(project, timeout=5)
            print(context(snapshot) or "No live directives." if snapshot is not None else "Server unreachable and no cache.")
        elif args.command == "add":
            request(project, {"action": "add", "text": args.text, "until": args.until, "on_expire": args.on_expire}, 10)
            print("added")
        else:
            request(project, {"action": "done" if args.done else "end", "id": args.id}, 10)
            print("ended")
        return 0
    except (OSError, ValueError, KeyError, urllib.error.URLError) as error:
        print(f"directives: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
