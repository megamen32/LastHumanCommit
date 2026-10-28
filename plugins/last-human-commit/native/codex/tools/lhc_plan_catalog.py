#!/usr/bin/env python3
"""The owner's catalog of all plans: what is moving, what is stuck, when it ends.

Pure rendering over mirror replica entries. No network, no writes. The state of
a plan is read from its leaves and the last source file event; agent liveness
is never claimed.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import html
import re
import lhc_plan_ui as ui

STALLED_AFTER = timedelta(hours=3)
UNKNOWN_LEAF_MINUTES = 15
STATE_LABELS = {
    'active': 'В работе',
    'blocked': 'Заблокирован',
    'stalled': 'Застрял',
    'completed': 'Завершён',
    'legacy': 'Без данных',
}
STATE_ORDER = ['active', 'blocked', 'stalled', 'completed', 'legacy']
LEAF_LABELS = {'done': 'готово', 'running': 'в работе', 'blocked': 'заблокировано',
               'waiting': 'ждёт', 'queued': 'в очереди', 'deferred': 'отложено'}


def parse_time(value):
    try:
        stamp = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def leaf_minutes(task):
    bounds = task.get('duration_estimate_minutes', task.get('estimate_minutes'))
    if isinstance(bounds, (int, float)) and bounds > 0:
        return float(bounds)
    if isinstance(bounds, dict):
        values = [v for v in (bounds.get('minimum'), bounds.get('maximum'))
                  if isinstance(v, (int, float)) and v > 0]
        if values:
            return sum(values) / len(values)
    return float(UNKNOWN_LEAF_MINUTES)


def remaining_minutes(tasks, slots, now):
    """Critical path over unfinished leaves, bounded below by work / slots."""
    open_tasks = {t['id']: t for t in tasks if t.get('status') not in ('done', 'deferred')}
    left = {}
    for key, task in open_tasks.items():
        minutes = leaf_minutes(task)
        started = parse_time(task.get('started_at')) if task.get('status') == 'running' else None
        if started:
            minutes -= max(0.0, (now - started).total_seconds() / 60)
        left[key] = max(minutes, 2.0)
    finish, visiting = {}, set()

    def path(key):
        if key in finish:
            return finish[key]
        if key in visiting:  # A cycle is a plan defect; do not loop on it.
            return left[key]
        visiting.add(key)
        before = [path(d) for d in open_tasks[key].get('depends_on') or [] if d in open_tasks]
        visiting.discard(key)
        finish[key] = left[key] + max(before, default=0.0)
        return finish[key]

    critical = max((path(k) for k in open_tasks), default=0.0)
    capacity = sum(left.values()) / max(1, int(slots or 1))
    return max(critical, capacity)


def summarize(entry, now):
    snap, receipt = entry['snapshot'], entry.get('receipt') or {}
    doc = snap['document']
    tasks = [t for t in doc.get('tasks') or [] if isinstance(t, dict) and t.get('id')]
    counted = [t for t in tasks if t.get('status') != 'deferred']
    done = sum(t.get('status') == 'done' for t in counted)
    running = [t for t in counted if t.get('status') == 'running']
    stopped = [t for t in counted if t.get('status') in ('blocked', 'waiting')]
    updated = parse_time(snap.get('last_file_event')) or parse_time(receipt.get('received_at'))
    revisions = snap.get('revisions') or [{}]
    created = parse_time(revisions[0].get('created_at')) or updated
    idle = now - updated if updated else timedelta(0)
    if counted and done == len(counted):
        state = 'completed'
    elif stopped and not running:
        state = 'blocked'
    elif idle > STALLED_AFTER:
        state = 'stalled'
    else:
        state = 'active'
    finished = max((parse_time(t.get('finished_at')) for t in counted
                    if parse_time(t.get('finished_at'))), default=updated)
    if running:
        stage = ('Остановился на: ' if state == 'stalled' else 'Сейчас: ') + '; '.join(
            t.get('label') or t['id'] for t in running[:2])
        if len(running) > 2:
            stage += f' и ещё {len(running) - 2}'
    elif stopped:
        task = stopped[0]
        reason = task.get('blocker') or task.get('wait_reason') or task.get('label') or task['id']
        stage = 'Ждёт: ' + str(reason)
    elif state == 'completed':
        stage = 'Все шаги выполнены'
    else:
        ids = {t['id'] for t in counted if t.get('status') == 'done'}
        ready = [t for t in counted if t.get('status') == 'queued'
                 and all(d in ids for d in t.get('depends_on') or [])]
        nxt = ready[0] if ready else next((t for t in counted if t.get('status') != 'done'), None)
        stage = 'Следующий шаг: ' + (nxt.get('label') or nxt['id']) if nxt else 'Шагов пока нет'
    eta = None
    if state == 'active' and counted:
        eta = now + timedelta(minutes=remaining_minutes(counted, doc.get('slots'), now))
    return {
        'state': state,
        'project': snap['project'],
        'title': doc.get('title') or snap['name'],
        'goal': doc.get('business_result') or doc.get('goal') or '',
        'url': '/' + snap['project'] + '/' + snap['name'] + '/',
        'created': created,
        'updated': updated,
        'finished': finished if state == 'completed' else None,
        'idle': idle,
        'done': done,
        'total': len(counted),
        'stage': stage,
        'eta': eta,
        'leaves': [(t.get('status') or 'queued', t.get('label') or t['id']) for t in tasks[:80]],
        'revision': (revisions[-1] or {}).get('id'),
    }


def legacy_summary(project, name, title):
    match = re.match(r'plan-(\d{8})-(\d{4})', name)
    created = (datetime.strptime(''.join(match.groups()), '%Y%m%d%H%M').replace(tzinfo=timezone.utc)
               if match else None)
    return {'state': 'legacy', 'project': project, 'title': title or name, 'goal': '',
            'url': '/' + project + '/' + name + '/', 'created': created, 'updated': created,
            'finished': None, 'idle': timedelta(0), 'done': 0, 'total': 0,
            'stage': 'Опубликован старым способом: прогресс не передаётся', 'eta': None,
            'leaves': [], 'revision': None}


def iso(value):
    return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ') if value else ''


def short(value):
    return value.astimezone(timezone.utc).strftime('%d.%m %H:%M UTC') if value else 'неизвестно'


def duration_text(delta):
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return f'{max(minutes, 1)} мин'
    hours = minutes // 60
    if hours < 48:
        return f'{hours} ч'
    return f'{hours // 24} дн'


def card(item):
    esc = lambda s: html.escape(str(s), quote=True)
    state = item['state']
    percent = round(100 * item['done'] / item['total']) if item['total'] else 0
    strip = ''.join(f'<i class="leaf {esc(s)}" title="{esc(label)} · {esc(LEAF_LABELS.get(s, s))}"></i>'
                    for s, label in item['leaves'])
    if state == 'active' and item['eta']:
        when = (f'Завершится ≈ <time class="rel-eta" datetime="{iso(item["eta"])}">{short(item["eta"])}</time>'
                '<span class="hint"> · оценка по шагам плана</span>')
    elif state == 'completed':
        when = f'Завершён <time class="abs" datetime="{iso(item["finished"])}">{short(item["finished"])}</time>'
    elif state == 'stalled':
        when = f'Нет изменений {duration_text(item["idle"])} · срок не оценивается'
    elif state == 'blocked':
        when = 'Срок зависит от снятия блокировки'
    else:
        when = ''
    progress = (f'<div class="progress"><div class="bar"><b style="width:{percent}%"></b></div>'
                f'<span>{item["done"]} из {item["total"]} · {percent}%</span></div>') if item['total'] else ''
    goal = f'<p class="goal">{esc(item["goal"])}</p>' if item['goal'] else ''
    return (
        f'<article class="plan s-{state}" data-state="{state}" data-project="{esc(item["project"])}" '
        f'data-created="{iso(item["created"])}" data-updated="{iso(item["updated"])}" '
        f'data-rank="{STATE_ORDER.index(state)}" '
        f'data-search="{esc((item["project"] + " " + item["title"] + " " + item["goal"]).lower())}">'
        f'<div class="top"><span class="pill {state}">{STATE_LABELS[state]}</span>'
        f'<span class="project">{esc(item["project"])}</span></div>'
        f'<h3><a href="{esc(item["url"])}">{esc(item["title"])}</a></h3>{goal}{progress}'
        + (f'<div class="strip" aria-hidden="true">{strip}</div>' if strip else '')
        + f'<p class="stage">{esc(item["stage"])}</p>'
        + (f'<p class="when">{when}</p>' if when else '')
        + f'<p class="dates">Создан <time class="abs" datetime="{iso(item["created"])}">{short(item["created"])}</time>'
        f' · обновлён <time class="ago" datetime="{iso(item["updated"])}">{short(item["updated"])}</time></p>'
        '</article>')


def render(entries, legacy=(), now=None):
    now = now or datetime.now(timezone.utc)
    items = [summarize(e, now) for e in entries] + [legacy_summary(*x) for x in legacy]
    return render_items(items, now)


def render_items(items, now=None):
    """Render already summarized items; callers may retain inactive summaries."""
    now = now or datetime.now(timezone.utc)
    items = list(items)
    items.sort(key=lambda x: (STATE_ORDER.index(x['state']),
                              -(x['updated'] or now).timestamp()))
    counts = {s: sum(i['state'] == s for i in items) for s in STATE_ORDER}
    projects = sorted({i['project'] for i in items})
    esc = lambda s: html.escape(str(s), quote=True)
    chips = ''.join(
        f'<button type="button" class="chip" data-filter="{s}" aria-pressed="false">{label}'
        f' <span class="n">{n}</span></button>'
        for s, label, n in [('all', 'Все', len(items)), ('open', 'Не завершены',
                             counts['active'] + counts['blocked'] + counts['stalled'])]
        + [(s, STATE_LABELS[s], counts[s]) for s in STATE_ORDER if s != 'legacy' or counts[s]])
    options = ''.join(f'<option value="{esc(p)}">{esc(p)}</option>' for p in projects)
    body = ''.join(card(i) for i in items)
    groups = ''.join('<section class="project-group" data-project-group="' + esc(project) + '" hidden>'
                     '<h2>' + esc(project) + ' <span class="project-count"></span></h2>'
                     '<div class="plan-grid project-plans"></div></section>' for project in projects)
    empty = ('' if items else '<p class="empty">Пока нет синхронизированных планов. '
             'Они появятся после первой успешной синхронизации источника.</p>')
    return PAGE.replace('@@BRAND@@', ui.brand_link()).replace('@@BRAND_STYLE@@', ui.BRAND_STYLE).replace('@@GROUPS@@', groups).replace('@@CHIPS@@', chips).replace('@@PROJECTS@@', options).replace(
        '@@CARDS@@', body + empty).replace('@@TOTAL@@', str(len(items))).replace(
        '@@ACTIVE@@', str(counts['active'])).replace('@@STALLED@@', str(counts['stalled'] + counts['blocked']))


PAGE = '''<!doctype html><html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow">
<meta name="color-scheme" content="light dark"><title>Планы · LHC</title>
<style>
:root{--bg:#f4f5f8;--surface:#fff;--text:#1b2130;--muted:#626c80;--line:#e1e5ec;--accent:#3355d6;
--a-bg:#e8eeff;--a-fg:#2747c2;--b-bg:#fdeceb;--b-fg:#b4321f;--s-bg:#fff2dc;--s-fg:#9a5b00;
--c-bg:#e5f4ea;--c-fg:#23784a;--l-bg:#eef0f3;--l-fg:#5d6676;--q:#d5dae3}
@media (prefers-color-scheme:dark){:root{--bg:#0e1117;--surface:#161a22;--text:#e6e9ef;--muted:#99a2b2;
--line:#252b37;--accent:#8aa2ff;--a-bg:#1d2747;--a-fg:#a9bbff;--b-bg:#3a1c1a;--b-fg:#ff9b8c;--s-bg:#3a2c12;
--s-fg:#ffc565;--c-bg:#16301f;--c-fg:#7fd6a0;--l-bg:#20242d;--l-fg:#a3abb9;--q:#343b49}}
*{box-sizing:border-box}html{background:var(--bg)}
body{margin:0 auto;max-width:1180px;padding:28px 20px 60px;font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif;
background:var(--bg);color:var(--text)}
a{color:inherit;text-decoration:none}a:focus-visible,button:focus-visible,input:focus-visible,select:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
header{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap;margin-bottom:18px}
.brand{font-size:11px;letter-spacing:.16em;color:var(--muted)}h1{font-size:30px;line-height:1.15;margin:6px 0 0}
.totals{color:var(--muted);font-size:14px}.note{margin:4px 0 0;color:var(--muted);font-size:13px}.totals b{color:var(--text)}
.toolbar{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0 12px;display:grid;gap:10px}
.row{display:flex;gap:10px;flex-wrap:wrap;align-items:center}
input,select{font:inherit;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:9px 12px}
input{flex:1 1 260px;min-width:0}select{flex:0 1 220px}
.chip{font:inherit;font-size:14px;color:var(--text);background:var(--surface);border:1px solid var(--line);border-radius:999px;padding:6px 12px;cursor:pointer}
.chip .n{color:var(--muted);font-size:12px}.chip[aria-pressed="true"]{background:var(--text);color:var(--bg);border-color:var(--text)}
.chip[aria-pressed="true"] .n{color:inherit;opacity:.7}
#connection{font-size:12px;color:var(--muted);margin:0}#signin{font-weight:600;color:var(--accent)}
.plan-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,340px),1fr));gap:12px}
.catalog-tabs{display:flex;gap:4px;border-bottom:1px solid var(--line);margin-bottom:10px}.catalog-tabs button{font:inherit;border:0;border-bottom:3px solid transparent;background:transparent;color:var(--muted);padding:10px 18px;cursor:pointer;min-height:44px}.catalog-tabs button[aria-selected="true"]{border-color:var(--accent);color:var(--text);font-weight:650}.project-group{margin:0 0 26px}.project-group h2{font-size:19px;margin:12px 0;overflow-wrap:anywhere}.project-count{font-size:12px;font-weight:400;color:var(--muted)}.lhc-brand{display:inline-flex;align-items:center;gap:8px;min-height:44px}.lhc-brand-mark{font-weight:800;font-size:18px;letter-spacing:.06em}.lhc-brand-name{font-size:12px;letter-spacing:0}
.plan{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 18px;display:flex;flex-direction:column;gap:8px;border-left:4px solid var(--q)}
.plan.s-active{border-left-color:var(--a-fg)}.plan.s-blocked{border-left-color:var(--b-fg)}.plan.s-stalled{border-left-color:var(--s-fg)}.plan.s-completed{border-left-color:var(--c-fg)}
.top{display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px}
.pill{border-radius:6px;padding:2px 8px;font-weight:600}.pill.active{background:var(--a-bg);color:var(--a-fg)}
.pill.blocked{background:var(--b-bg);color:var(--b-fg)}.pill.stalled{background:var(--s-bg);color:var(--s-fg)}
.pill.completed{background:var(--c-bg);color:var(--c-fg)}.pill.legacy{background:var(--l-bg);color:var(--l-fg)}
.project{color:var(--muted)}h3{font-size:17px;line-height:1.3;margin:0;overflow-wrap:anywhere}h3 a:hover{color:var(--accent)}
.goal{margin:0;color:var(--muted);font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.progress{display:flex;align-items:center;gap:10px;font-size:13px;color:var(--muted)}
.bar{flex:1;height:8px;border-radius:99px;background:var(--q);overflow:hidden}.bar b{display:block;height:100%;background:var(--c-fg);border-radius:99px}
.strip{display:flex;flex-wrap:wrap;gap:3px}.leaf{width:10px;height:10px;border-radius:3px;background:var(--q)}
.leaf.done{background:var(--c-fg)}.leaf.running{background:var(--a-fg)}.leaf.blocked,.leaf.waiting{background:var(--b-fg)}.leaf.deferred{background:transparent;border:1px dashed var(--q)}
.stage{margin:0;font-size:14px;overflow-wrap:anywhere}.when{margin:0;font-size:14px;font-weight:600}.hint{font-weight:400;color:var(--muted);font-size:12px}
.dates{margin:auto 0 0;font-size:12px;color:var(--muted)}
.empty{grid-column:1/-1;padding:24px;background:var(--surface);border:1px dashed var(--line);border-radius:14px;color:var(--muted)}
[hidden]{display:none!important}
@media (max-width:640px){body{padding:18px 14px 40px}h1{font-size:25px}.plan-grid{grid-template-columns:1fr}
select{flex:1 1 40%;min-width:0}#chips{flex-wrap:nowrap;overflow-x:auto;scrollbar-width:none;margin:0 -14px;padding:0 14px}.chip{flex:none}}
@@BRAND_STYLE@@
</style></head><body>
<header><div><div class="brand">@@BRAND@@</div><h1>Планы и проекты</h1><p class="note">Состояние берётся из файлов плана. Живость агента: неизвестна.</p></div>
<div class="totals">Всего <b>@@TOTAL@@</b> · в работе <b>@@ACTIVE@@</b> · требуют внимания <b>@@STALLED@@</b></div></header>
<div class="toolbar"><div class="catalog-tabs" role="tablist" aria-label="Представление каталога"><button type="button" id="catalog-tab-plans" role="tab" data-view="plans" aria-controls="catalog-plans" aria-selected="true">Планы</button><button type="button" id="catalog-tab-projects" role="tab" data-view="projects" aria-controls="catalog-projects" aria-selected="false" tabindex="-1">Проекты</button></div><div class="row"><input id="search" type="search" placeholder="Поиск по названию, цели или проекту" autocomplete="off" aria-label="Поиск">
<select id="project" aria-label="Проект"><option value="">Все проекты</option>@@PROJECTS@@</select>
<select id="sort" aria-label="Сортировка"><option value="rank">Сначала активные</option><option value="updated">Последние изменения</option><option value="created">Новые планы</option></select></div>
<div class="row" id="chips">@@CHIPS@@</div>
<p id="connection" role="status" aria-live="polite">Последний известный снимок</p><a id="signin" href="/" hidden>Войти снова через SSO</a></div>
<main data-lhc-catalog="1"><div id="catalog-plans" class="plan-grid" role="tabpanel" aria-labelledby="catalog-tab-plans">@@CARDS@@</div><div id="catalog-projects" role="tabpanel" aria-labelledby="catalog-tab-projects" hidden>@@GROUPS@@</div></main>
<p id="no-matches" class="empty" hidden>Под эти фильтры планов нет.</p>
<script>
const $=s=>document.querySelector(s),state={filter:'all',project:'',sort:'rank',q:'',view:'plans'};
try{Object.assign(state,JSON.parse(localStorage.getItem('lhc-catalog')||'{}'))}catch(e){}
new URLSearchParams(location.hash.slice(1)).forEach((v,k)=>{if(k in state)state[k]=v});
const fmt=new Intl.DateTimeFormat('ru',{day:'numeric',month:'short',hour:'2-digit',minute:'2-digit'});
const hm=new Intl.DateTimeFormat('ru',{hour:'2-digit',minute:'2-digit'});
function ago(d){const m=Math.round((Date.now()-d)/60000);if(m<1)return'только что';if(m<60)return m+' мин назад';const h=Math.round(m/60);if(h<48)return h+' ч назад';return Math.round(h/24)+' дн назад'}
function eta(d){const m=Math.round((d-Date.now())/60000),t=new Date();const same=d.toDateString()===t.toDateString();
const left=m<60?Math.max(m,1)+' мин':Math.floor(m/60)+' ч '+(m%60)+' мин';return(same?'сегодня в '+hm.format(d):fmt.format(d))+' (через '+left+')'}
function times(){document.querySelectorAll('time').forEach(t=>{const d=new Date(t.getAttribute('datetime'));if(isNaN(d))return;
t.title=d.toLocaleString('ru');t.textContent=t.classList.contains('ago')?ago(d):t.classList.contains('rel-eta')?eta(d):fmt.format(d)})}
const match=(f,s)=>f==='all'||(f==='open'?['active','blocked','stalled'].includes(s):s===f);
function apply(){if(!['plans','projects'].includes(state.view))state.view='plans';if(![...$('#project').options].some(o=>o.value===state.project))state.project='';const q=state.q.trim().toLowerCase();let shown=0;const cards=[...document.querySelectorAll('.plan')];const n={};
cards.forEach(c=>{const s=c.dataset.state,scope=(!state.project||c.dataset.project===state.project)&&(!q||c.dataset.search.includes(q));
if(scope)document.querySelectorAll('.chip').forEach(b=>{if(match(b.dataset.filter,s))n[b.dataset.filter]=(n[b.dataset.filter]||0)+1});
c.hidden=!(scope&&match(state.filter,s));if(!c.hidden)shown++});
document.querySelectorAll('.chip').forEach(b=>{b.querySelector('.n').textContent=n[b.dataset.filter]||0});
const key={rank:c=>[+c.dataset.rank,-Date.parse(c.dataset.updated||0)],updated:c=>[-Date.parse(c.dataset.updated||0)],created:c=>[-Date.parse(c.dataset.created||0)]}[state.sort]||(c=>[0]);
const groups=new Map([...document.querySelectorAll('[data-project-group]')].map(group=>[group.dataset.projectGroup,group]));
cards.sort((a,b)=>{const x=key(a),y=key(b);for(let i=0;i<x.length;i++)if(x[i]!==y[i])return x[i]-y[i];return 0}).forEach(c=>{const parent=state.view==='projects'?groups.get(c.dataset.project)?.querySelector('.project-plans'):$('#catalog-plans');(parent||$('#catalog-plans')).appendChild(c)});
groups.forEach((group,project)=>{const all=cards.filter(card=>card.dataset.project===project),visible=all.filter(card=>!card.hidden).length;group.hidden=state.view!=='projects'||visible===0;group.querySelector('.project-count').textContent=visible+' из '+all.length+' планов'});
$('#catalog-plans').hidden=state.view!=='plans';$('#catalog-projects').hidden=state.view!=='projects';
document.querySelectorAll('[data-view]').forEach(tab=>{const selected=tab.dataset.view===state.view;tab.setAttribute('aria-selected',String(selected));tab.tabIndex=selected?0:-1});
document.querySelectorAll('.chip').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.filter===state.filter)));
$('#no-matches').hidden=shown>0||!cards.length;$('#project').value=state.project;$('#sort').value=state.sort;$('#search').value=state.q;
try{localStorage.setItem('lhc-catalog',JSON.stringify(state))}catch(e){}
const h=new URLSearchParams();for(const k of['filter','project','sort','view'])if(state[k]&&!(k==='filter'&&state[k]==='all')&&!(k==='sort'&&state[k]==='rank')&&!(k==='view'&&state[k]==='plans'))h.set(k,state[k]);
history.replaceState(null,'',h.toString()?'#'+h:location.pathname+location.search)}
$('#chips').addEventListener('click',e=>{const b=e.target.closest('.chip');if(b){state.filter=b.dataset.filter;apply()}});
document.querySelectorAll('[data-view]').forEach((tab,index,tabs)=>{tab.addEventListener('click',()=>{state.view=tab.dataset.view;apply()});tab.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?tabs.length-1:(index+(event.key==='ArrowLeft'?-1:1)+tabs.length)%tabs.length;tabs[next].click();tabs[next].focus()})});
$('#project').addEventListener('change',e=>{state.project=e.target.value;apply()});
$('#sort').addEventListener('change',e=>{state.sort=e.target.value;apply()});
$('#search').addEventListener('input',e=>{state.q=e.target.value;apply()});
if(![...$('#project').options].some(o=>o.value===state.project))state.project='';
times();apply();
let busy=false;async function refresh(){if(busy)return;busy=true;const badge=$('#connection'),signin=$('#signin');
try{const r=await fetch(location.pathname,{cache:'no-store',redirect:'manual'});
if(r.status===401||r.status===403||r.type==='opaqueredirect'||(r.status>=300&&r.status<400)){signin.hidden=false;badge.textContent='Нужен вход · показан последний известный список';return}
if(!r.ok)throw Error();const doc=new DOMParser().parseFromString(await r.text(),'text/html');const next=doc.querySelector('main[data-lhc-catalog="1"]');
if(!next){signin.hidden=false;badge.textContent='Нужен вход · показан последний известный список';return}
const y=scrollY;$('main').replaceWith(next);const projects=doc.querySelector('#project');if(projects)$('#project').innerHTML=projects.innerHTML;const totals=doc.querySelector('.totals');if(totals)$('.totals').innerHTML=totals.innerHTML;times();apply();scrollTo(0,y);signin.hidden=true;badge.textContent='Обновлено в '+hm.format(new Date())}
catch(e){badge.textContent='Нет связи · показан последний известный список'}finally{busy=false}}
if(/^https?:$/.test(location.protocol))setInterval(refresh,15000);setInterval(times,60000);
</script></body></html>'''
