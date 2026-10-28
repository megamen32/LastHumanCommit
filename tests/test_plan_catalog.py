"""The owner's plan catalog and the public plan link."""
import json
import sys
import subprocess
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


def test_catalog_tabs_share_all_plans_and_group_every_project():
    page = catalog.render([entry([leaf(1, 'running')], project='herder'),
                           entry([leaf(1, 'done')], project='airlock', name='plan-second')],
                          legacy=[('old', 'plan-20261024-1600-cc', 'Старый план')], now=NOW)
    assert 'role="tablist"' in page
    assert 'id="catalog-tab-plans"' in page and 'id="catalog-tab-projects"' in page
    assert page.count('<article class="plan') == 3
    for project in ('herder', 'airlock', 'old'):
        assert f'data-project-group="{project}"' in page
    assert 'aria-label="Главная Last Human Commit"' in page


def test_plan_brand_links_home_even_for_downloaded_page():
    import lhc_plan_ui as ui
    page = ui.decorate('<html><head></head><body><!-- plan-revisions --></body></html>')
    assert 'href="https://lhc.bezrabotnyi.com/"' in page
    assert 'aria-label="Главная Last Human Commit"' in page


def test_catalog_view_switches_keep_all_67_plans_and_common_filters():
    script = catalog.PAGE.split('const match=', 1)[1].split("$('#chips').addEventListener", 1)[0]
    harness = r'''
const assert=require('assert');
function node(){return {children:[],hidden:false,attrs:{},setAttribute(k,v){this.attrs[k]=v},appendChild(child){if(child.parentNode)child.parentNode.children=child.parentNode.children.filter(x=>x!==child);this.children.push(child);child.parentNode=this}}}
const flat=node(),projectsPanel=node(),count=node(),project={value:'',options:[{value:''},{value:'p0'},{value:'p1'},{value:'p2'}]};
const chips=['all','open','active','completed'].map(filter=>{const chip=node();chip.dataset={filter};chip.n={textContent:''};chip.querySelector=()=>chip.n;return chip});
const groups=['p0','p1','p2'].map(name=>{const group=node();group.dataset={projectGroup:name};group.grid=node();group.count={};group.querySelector=selector=>selector==='.project-plans'?group.grid:group.count;return group});
const tabs=['plans','projects'].map(view=>{const tab=node();tab.dataset={view};return tab});
const cards=Array.from({length:67},(_,i)=>{const card=node(),name='p'+(i%3);card.dataset={project:name,state:i%2?'completed':'active',rank:i%2,search:name+' plan '+i,created:new Date(1700000000000+i*1000).toISOString(),updated:new Date(1700000000000+i*1000).toISOString()};flat.appendChild(card);return card});
const nodes={'#catalog-plans':flat,'#catalog-projects':projectsPanel,'#no-matches':count,'#project':project,'#sort':{},'#search':{}};
global.document={querySelector:selector=>nodes[selector],querySelectorAll:selector=>({'.plan':cards,'.chip':chips,'[data-project-group]':groups,'[data-view]':tabs}[selector]||[])};
const $=selector=>document.querySelector(selector),state={view:'plans',filter:'all',q:'',project:'',sort:'rank'};
global.localStorage={setItem(key,value){this.saved=JSON.parse(value)}};global.history={replaceState(){}};global.location={pathname:'/',search:''};
'''
    checks = r'''
apply();assert.equal(flat.children.length,67);
state.view='projects';apply();
assert.equal(flat.children.length,0);assert.equal(groups.reduce((sum,g)=>sum+g.grid.children.length,0),67);
assert.equal(new Set(groups.flatMap(g=>g.grid.children)).size,67);
state.filter='active';state.q='p1';state.sort='created';apply();
const visible=cards.filter(card=>!card.hidden);assert(visible.length>0);assert(visible.every(card=>card.dataset.project==='p1'&&card.dataset.state==='active'));
assert.equal(groups.filter(group=>!group.hidden).length,1);
const groupOrder=groups[1].grid.children.map(card=>card.dataset.created);assert.deepEqual(groupOrder,[...groupOrder].sort().reverse());
const expected=visible.map(card=>card.dataset.created);
state.view='plans';apply();assert.equal(flat.children.length,67);
const flatOrder=flat.children.map(card=>card.dataset.created);assert.deepEqual(flatOrder,[...flatOrder].sort().reverse());
assert.deepEqual(cards.filter(card=>!card.hidden).map(card=>card.dataset.created),expected);
assert.equal(localStorage.saved.q,'p1');assert.equal(localStorage.saved.view,'plans');
state.filter='all';state.q='';state.view='projects';apply();assert.equal(cards.filter(card=>!card.hidden).length,67);
assert.equal(tabs[1].attrs['aria-selected'],'true');assert(groups.every(group=>!group.hidden));
'''
    result = subprocess.run(['node', '-e', harness + 'const match=' + script + checks], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, result.stderr


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
