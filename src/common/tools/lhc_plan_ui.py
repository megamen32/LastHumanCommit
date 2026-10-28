"""Shared, dependency-free navigation for standalone and published plan views."""

import json
import re
from html import escape
from datetime import datetime, timezone
from urllib.parse import quote


def brand_link():
    """Shared home destination; the verified brand artwork is supplied here."""
    return ('<a class="lhc-brand" href="https://lhc.bezrabotnyi.com/" aria-label="Главная Last Human Commit">'
            '<span class="brand-mark lhc-brand-mark">L<span>／</span>H</span>'
            '<span class="brand-name lhc-brand-name">Last Human<br>Commit</span></a>')


# Original typographic identity from site/index.html and site/styles.css,
# commit 87be2e4459b154be35b6b3e4862d88398d5dfe81.
BRAND_STYLE = '.lhc-brand{display:inline-flex;align-items:center;gap:15px}.lhc-brand .brand-mark{font-size:27px;font-weight:850;letter-spacing:-.12em;flex:none}.lhc-brand .brand-mark span{color:#f5b38a;font-weight:400}.lhc-brand .brand-name{font-size:11px;line-height:1.25;font-weight:850;letter-spacing:.08em;text-transform:uppercase}@media(max-width:640px){.lhc-brand .brand-mark{font-size:23px}}'


def herder_panel(tasks):
    """Open only an explicitly bound, supported native session; never guess one."""
    sessions = {}
    for task in sorted(tasks, key=lambda task: task.get('status') not in ('running', 'in_progress')):
        session = str(task.get('session') or '')
        harness = task.get('harness')
        if (harness not in ('codex', 'zcode', 'opencode') or session.lower() in ('unknown', 'none', 'null') or
                not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,199}', session)):
            continue
        key = harness + ':' + session
        sessions.setdefault(key, (task.get('label') or session, task.get('status') in ('running', 'in_progress')))
    options = ''.join('<option value="' + escape('https://agent.bezrabotnyi.com/?from=lhc#/session/' + quote(key, safe=''), quote=True) + '">' +
                      escape(('В работе · ' if running else '') + label) + '</option>'
                      for key, (label, running) in sessions.items())
    disabled = '' if sessions else ' disabled title="В плане не записана поддерживаемая сессия исполнителя"'
    first_url = 'https://agent.bezrabotnyi.com/?from=lhc#/session/' + quote(next(iter(sessions)), safe='') if sessions else ''
    return ('<button type="button" id="herder-launch" aria-controls="herder-panel" aria-expanded="false"' + disabled + '>Agent Herder</button>'
            '<aside id="herder-panel" role="dialog" aria-label="Сессия исполнителя в Agent Herder" hidden>'
            '<div class="herder-heading"><label class="herder-selection"><select id="herder-session" aria-label="Сессия исполнителя">' + options + '</select></label>'
            '<a id="herder-direct" href="' + escape(first_url, quote=True) + '" target="_blank" rel="noopener noreferrer" title="Открыть отдельно — в том числе для входа">Открыть отдельно ↗</a>'
            '<button type="button" id="herder-close" aria-label="Закрыть Agent Herder">×</button></div>'
            '<p id="herder-plan-update" role="status" hidden>Есть обновления плана. Они применятся после закрытия панели.</p>'
            '<iframe id="herder-frame" title="Рабочая сессия Agent Herder" referrerpolicy="no-referrer"></iframe></aside>'
            '<div id="herder-divider" role="separator" tabindex="0" aria-label="Размер области плана" aria-controls="herder-plan-pane herder-panel" aria-orientation="vertical" aria-valuemin="0" aria-valuemax="100" aria-valuenow="50" hidden></div>'
            '<div id="herder-split-controls" role="group" aria-label="Расположение плана и чата" hidden>'
            '<button type="button" data-herder-ratio="100">План</button><button type="button" data-herder-ratio="50" aria-label="Разделить поровну">½</button>'
            '<button type="button" data-herder-ratio="0">Чат</button><button type="button" data-herder-close aria-label="Закрыть Agent Herder">×</button></div>'
            '<div id="herder-drag-shield" hidden></div>')


def display_time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")


def time_rail(frame):
    qualifier = {'file_birthtime': 'восстановлено по файлам',
                 'leaf_created_at': 'создание первого листа',
                 'recorded_start': 'по записанному началу работы'}.get(frame.get('start_source'), '')
    start = ("Начало плана: " + display_time(frame["start"]) if frame["start"] else
             "Начало плана: " + frame["legacy_start"] + " · дата не записана"
             if frame["legacy_start"] else "Начало плана не зафиксировано")
    if qualifier:
        start += ' · ' + qualifier
    snapshot = display_time(frame["snapshot"]) if frame.get("snapshot") else "неизвестно"
    return ('<div class="time-rail" data-time-frame="' + escape(json.dumps(frame), quote=True) + '">'
            '<div class="time-rail-start">' + escape(start) + '</div>'
            '<div class="time-rail-times" aria-label="Временные границы плана">'
            '<span class="time-rail-minimum">Минимум —</span>'
            '<span class="time-rail-maximum">Максимум —</span>'
            '<span class="time-rail-now">На момент снимка ' + escape(snapshot) + '</span></div>'
            '<div class="time-rail-clock sr-only">На момент снимка ' + escape(snapshot) + '</div>'
            '<div class="time-rail-status" role="status"></div>'
            '<div class="time-rail-note">Время показано отдельно от доли выполненных задач; цветная полоса считает статусы. Часовой пояс указан в датах.</div></div>')

SECTIONS = (("dashboard", "Дашборд"), ("outcome", "Цель и результат"),
            ("work-plan", "План работ"), ("comparison", "План и факт"),
            ("tasks", "Задачи"), ("history", "История"))

STYLE = '''<style id="plan-app-style">
html{scroll-behavior:smooth}body{margin:0;padding:0;overflow-wrap:anywhere;background:var(--bg);background-image:none}
@media(prefers-reduced-motion:reduce){html{scroll-behavior:auto}}
body .page{max-width:1600px;margin:0 auto;padding:28px 36px 48px 240px;min-width:0}
.page>header{margin:0 0 14px;align-items:flex-start}.page>header h1{font-size:clamp(24px,3vw,36px);line-height:1.15;letter-spacing:-.035em}
.page>header .sub{font-size:11px;max-width:700px;color:var(--muted);opacity:1}.head-count{display:none}
.now-count{color:var(--text)!important;background:var(--panel-2)!important;border:1px solid var(--line)}
body>footer{margin:0 36px 24px 240px;max-width:1324px;padding:12px 0;color:var(--muted)}
.plan-sidebar{position:fixed;inset:0 auto 0 0;width:208px;padding:36px 16px;background:var(--panel);border-right:1px solid var(--line);z-index:30;display:flex;flex-direction:column;gap:5px}
.plan-brand{font-size:12px;font-weight:800;letter-spacing:.14em;color:var(--muted);padding:0 14px 28px}
.plan-sidebar .plan-brand .lhc-brand{display:flex;align-items:center;gap:8px;padding:0;min-height:44px;color:var(--text);text-decoration:none}.lhc-brand-mark{flex:none}.lhc-brand-name{font-size:11px;letter-spacing:0;line-height:1.2}
.plan-sidebar a{color:var(--muted);text-decoration:none;padding:12px 14px;border-radius:10px;font-size:14px;min-height:44px;box-sizing:border-box;display:flex;align-items:center;gap:10px}
.plan-sidebar a[aria-current=location]{background:var(--accent);color:white;font-weight:650}
.plan-sidebar a:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.plan-section{min-width:0;scroll-margin-top:var(--plan-anchor-offset,24px)}.plan-section [id]{scroll-margin-top:var(--plan-anchor-offset,24px)}.plan-section>h2{font-size:23px;margin:22px 0 18px}
.revision-strip{display:flex;gap:6px;overflow-x:auto;max-width:100%;padding:2px 0 16px;margin-bottom:6px;align-items:center}
.revision-strip a,.revision-strip span{flex:none;white-space:nowrap;padding:7px 13px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;text-decoration:none}
.revision-strip [aria-current=page]{color:var(--text);border-color:var(--accent);background:var(--panel);font-weight:650}
body .progress-strip{position:relative;top:auto;margin:0 0 18px;box-shadow:none}
.time-rail{margin-top:9px;cursor:default;min-width:0}
.time-rail-start{font-size:11px;line-height:1.4;color:var(--muted);overflow-wrap:anywhere}
.time-rail-times{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:7px;font-size:12px;line-height:1.4}
.time-rail-times>span{min-width:0;overflow-wrap:anywhere}.time-rail-minimum{text-align:left;color:#687386}.time-rail-maximum{text-align:right;color:#687386}.time-rail-now{text-align:center;font-weight:700;color:var(--text)}
.time-rail-clock.sr-only{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}
.time-rail-note,.time-rail-status{font-size:12px;line-height:1.5;margin-top:7px}.time-rail-note{font-size:11px;color:var(--muted)}
.time-rail-status{min-height:18px;color:var(--text);font-weight:600}.time-rail[data-state=early-passed] .time-rail-status{color:#9a6700}.time-rail[data-state=overdue] .time-rail-status{color:#b42318}
@media(max-width:650px){.time-rail-times{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:5px}.time-rail-now{grid-column:1/-1;text-align:left}}
body .kpis{grid-template-columns:repeat(4,minmax(0,1fr));gap:10px;margin:0 0 18px}
body .kpi{padding:15px 16px;min-width:0;border-radius:12px}body .kpi-value{font-size:clamp(22px,2.5vw,32px)}body .kpi-hint{font-size:11px;line-height:1.4}
body .panel{border-radius:14px;padding:20px;margin-bottom:16px}body .brief{gap:12px}body .brief-card{min-width:0}
body .panel-now{margin-top:12px}
.compare-scroll,.table-scroll,.gantt{max-width:100%;overflow-x:auto!important}.comparison-empty:has(+*){font-size:13px}
#comparison:has(#plan-comparison) .comparison-empty{display:none}
body #publication,body #plan-comparison{margin:0 0 16px;padding:20px;max-width:none;background:var(--panel);color:var(--text);border-color:var(--line);font:inherit}
body #publication a{color:var(--accent)}body .comparison td,body .comparison th{padding:12px;min-width:180px;font-size:13px}
.plan-section p,.brief-card p{white-space:pre-wrap}#history #lhc-forecast{max-width:900px}
@media(max-width:900px){body .page{padding:20px 20px 40px 200px}.plan-sidebar{width:176px;padding:24px 12px}body .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}body>footer{margin-left:200px}}
@media(max-width:650px){body .page{padding:14px 12px 30px}.plan-sidebar{position:sticky;inset:0;flex-direction:row;width:auto;padding:8px 10px;gap:4px;overflow-x:auto;border-right:0;border-bottom:1px solid var(--line)}.plan-brand{display:none}.plan-sidebar a{flex:none;padding:10px 12px;font-size:12px}.page>header{gap:12px}.page>header .sub{font-size:10px}.head-actions{flex-shrink:0}.theme-toggle{max-width:94px;font-size:11px}body .kpis{grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}body .kpi{padding:12px}body .panel{padding:14px}body .brief{grid-template-columns:1fr}body .progress-strip{font-size:11px}.toolbar{flex-wrap:wrap}.toolbar input{width:100%;min-width:0}.revision-strip{padding-bottom:12px}body .gantt-inner{min-width:600px}}
@media(max-width:650px){body>footer{margin:0 12px 24px}}
@media print{.plan-sidebar,.revision-strip,.theme-toggle{display:none!important}body .page{padding:0!important;max-width:none}.plan-section{break-before:auto}body .kpis{grid-template-columns:repeat(4,1fr)}details>*{display:block!important}.compare-scroll,.gantt,.table-scroll{overflow:visible!important}.gantt-inner{min-width:0!important}.panel{break-inside:avoid}#plan-content{display:block}body>footer{margin:12px 0}}
#herder-launch{position:fixed;z-index:45;top:20px;right:24px;border:1px solid var(--accent);background:var(--panel);color:var(--text);padding:10px 14px;border-radius:10px;font:inherit;cursor:pointer;min-height:44px;box-shadow:0 4px 24px #0005}#herder-launch:disabled{opacity:.55;cursor:default}
@media(min-width:651px){body:has(#herder-launch) .head-actions{padding-right:140px}}
#herder-workspace,#herder-plan-pane{display:contents}body.herder-open{overflow:hidden}body.herder-open #herder-workspace{position:fixed;inset:0;display:grid;grid-template-columns:var(--herder-plan-size,calc(50vw - 6px)) 12px minmax(0,1fr);grid-template-rows:minmax(0,1fr)}body.herder-open #herder-plan-pane{display:block;overflow:auto;min-width:0;min-height:0;overscroll-behavior:contain}body.herder-open #herder-launch{display:none}
body.herder-open #herder-plan-pane .page{padding:18px 18px 54px;box-sizing:border-box;width:100%}body.herder-open #herder-plan-pane .head-actions{padding-right:0}body.herder-open #herder-plan-pane .plan-sidebar{position:sticky;inset:0;flex-direction:row;width:auto;padding:6px;gap:4px;overflow-x:auto;border-right:0;border-bottom:1px solid var(--line);box-sizing:border-box}body.herder-open .plan-brand{display:none}body.herder-open .plan-sidebar a{flex:none;padding:8px;font-size:12px}#herder-plan-pane>footer{margin:12px 24px}body.herder-open #herder-plan-pane .kpis{grid-template-columns:repeat(2,minmax(0,1fr))}
#herder-panel{background:var(--panel);color:var(--text);display:flex;flex-direction:column;overflow:hidden;min-width:0;min-height:0}#herder-panel[hidden],#herder-plan-update[hidden],#herder-divider[hidden],#herder-split-controls[hidden],#herder-drag-shield[hidden]{display:none!important}
.herder-heading{display:flex;align-items:center;gap:6px;padding:4px 6px;min-height:44px;box-sizing:border-box;white-space:nowrap;flex-shrink:0;overflow:hidden}.herder-heading button,#herder-split-controls button{min-height:36px;padding:4px 8px;border:1px solid var(--line);border-radius:7px;background:var(--panel-2);color:var(--text);font:inherit;cursor:pointer}.herder-selection{flex:1;min-width:0;display:flex;font-size:12px}.herder-selection select{width:100%;min-width:0;min-height:36px;background:var(--panel);color:var(--text);border:1px solid var(--line);border-radius:7px}#herder-direct{color:var(--accent);font-size:11px;flex-shrink:0}#herder-plan-update{margin:4px 8px;font-size:11px}#herder-frame{flex:1;width:100%;min-height:0;border:0;background:var(--bg)}
#herder-divider{position:relative;z-index:61;cursor:col-resize;touch-action:none;background:var(--line)}#herder-divider:after{content:'';position:absolute;inset:calc(50% - 24px) 4px;border-radius:4px;background:var(--accent)}#herder-divider:focus-visible{outline:3px solid var(--accent);outline-offset:-3px}#herder-split-controls{position:fixed;z-index:65;display:flex;gap:2px;padding:2px;background:var(--panel);border:1px solid var(--line);border-radius:8px;white-space:nowrap}#herder-split-controls button{font-size:11px;padding:2px 7px;min-height:32px}#herder-drag-shield{position:fixed;inset:0;z-index:64;cursor:col-resize;touch-action:none}body.herder-dragging{user-select:none}body.herder-dragging #herder-frame{pointer-events:none}
@media(max-width:650px){body:has(#herder-launch) .page{padding-bottom:88px}#herder-launch{top:auto;right:14px;bottom:calc(14px + env(safe-area-inset-bottom))}body.herder-open #herder-workspace{grid-template-columns:minmax(0,1fr);grid-template-rows:var(--herder-plan-size,calc(50dvh - 6px)) 12px minmax(0,1fr)}#herder-divider,#herder-drag-shield{cursor:row-resize}#herder-divider:after{inset:4px calc(50% - 24px)}}
@media print{#herder-launch,#herder-panel,#herder-divider,#herder-split-controls,#herder-drag-shield{display:none!important}body.herder-open #herder-workspace,body.herder-open #herder-plan-pane{position:static;display:block;overflow:visible}}
@media(max-width:650px){.plan-sidebar .plan-brand{display:flex;flex:none;padding:0}.plan-brand .lhc-brand-name{display:none}.plan-sidebar .plan-brand .lhc-brand{padding:0 8px}}
body.herder-open .plan-sidebar .plan-brand{display:flex;flex:none;padding:0}body.herder-open .plan-brand .lhc-brand-name{display:none}
</style>'''

STYLE = STYLE.replace('</style>', BRAND_STYLE + '</style>')

HERDER_SCRIPT = '''<script id="lhc-herder-panel">
(()=>{const launch=document.getElementById('herder-launch'),panel=document.getElementById('herder-panel');
if(!launch||!panel||launch.disabled)return;
const select=document.getElementById('herder-session'),frame=document.getElementById('herder-frame'),direct=document.getElementById('herder-direct'),close=document.getElementById('herder-close');
const divider=document.getElementById('herder-divider'),controls=document.getElementById('herder-split-controls'),shield=document.getElementById('herder-drag-shield');
// Move the frame once, before its first src assignment. Resizing never moves it.
document.body.append(launch,panel,divider,controls,shield);
const workspace=document.createElement('div'),plan=document.createElement('div');workspace.id='herder-workspace';plan.id='herder-plan-pane';
for(const child of [...document.body.children])if(![launch,panel,divider,controls,shield].includes(child))plan.append(child);
workspace.append(plan,divider,panel);document.body.append(workspace);
const mobile=matchMedia('(max-width:650px)');
const storage='lhc-herder:'+location.pathname;
let saved={};try{saved=JSON.parse(sessionStorage.getItem(storage)||'{}')}catch(e){}
if(!saved||typeof saved!=='object')saved={};
if([...select.options].some(option=>option.value===saved.url))select.value=saved.url;
const ratios={desktop:Number.isFinite(saved.desktop)?Math.max(0,Math.min(100,saved.desktop)):50,mobile:Number.isFinite(saved.mobile)?Math.max(0,Math.min(100,saved.mobile)):50};
function persist(){try{sessionStorage.setItem(storage,JSON.stringify({open:!panel.hidden,url:select.value,...ratios}))}catch(e){}}
function mode(){return mobile.matches?'mobile':'desktop'}
function layout(){const rect=workspace.getBoundingClientRect(),vertical=mobile.matches,size=(vertical?rect.height:rect.width)-12,ratio=ratios[mode()],position=Math.max(0,size)*ratio/100;
workspace.style.setProperty('--herder-plan-size',position+'px');divider.setAttribute('aria-orientation',vertical?'horizontal':'vertical');divider.setAttribute('aria-valuenow',String(Math.round(ratio)));divider.setAttribute('aria-valuetext','План '+Math.round(ratio)+'%, чат '+Math.round(100-ratio)+'%');
const box=controls.getBoundingClientRect();controls.style.left=Math.max(0,Math.min(innerWidth-box.width,vertical?(innerWidth-box.width)/2:position+6-box.width/2))+'px';controls.style.top=Math.max(0,Math.min(innerHeight-box.height,vertical?position+6-box.height/2:8))+'px';persist()}
function setRatio(value){ratios[mode()]=Math.max(0,Math.min(100,value));layout()}
function choose(){const url=select.value;if(![...select.options].some(option=>option.value===url))return;direct.href=url;if(!panel.hidden&&frame.getAttribute('src')!==url)frame.src=url;persist()}
function open(){const scroll=window.scrollY;panel.hidden=false;divider.hidden=false;controls.hidden=false;document.body.classList.add('herder-open');plan.scrollTop=scroll;launch.setAttribute('aria-expanded','true');layout();choose();close.focus({preventScroll:true});persist();window.dispatchEvent(new Event('resize'))}
function shut(){const scroll=plan.scrollTop;finishDrag();panel.hidden=true;divider.hidden=true;controls.hidden=true;document.body.classList.remove('herder-open');launch.setAttribute('aria-expanded','false');persist();window.scrollTo({top:scroll,behavior:'instant'});launch.focus({preventScroll:true});window.dispatchEvent(new Event('lhc-herder-closed'))}
let dragging=null;
function point(event){const rect=workspace.getBoundingClientRect();setRatio(((mobile.matches?event.clientY-rect.top:event.clientX-rect.left)-6)/Math.max(1,(mobile.matches?rect.height:rect.width)-12)*100)}
function finishDrag(){dragging=null;shield.hidden=true;document.body.classList.remove('herder-dragging')}
divider.addEventListener('pointerdown',event=>{if(event.button!==0&&event.pointerType!=='touch')return;event.preventDefault();dragging=event.pointerId;divider.setPointerCapture(event.pointerId);shield.hidden=false;document.body.classList.add('herder-dragging');point(event)});
window.addEventListener('pointermove',event=>{if(dragging===event.pointerId){event.preventDefault();point(event)}},{passive:false});
window.addEventListener('pointerup',finishDrag);window.addEventListener('pointercancel',finishDrag);window.addEventListener('blur',finishDrag);
divider.addEventListener('keydown',event=>{let next=ratios[mode()],step=event.shiftKey?10:2;if(event.key==='Home')next=0;else if(event.key==='End')next=100;else if(['ArrowLeft','ArrowUp'].includes(event.key))next-=step;else if(['ArrowRight','ArrowDown'].includes(event.key))next+=step;else return;event.preventDefault();setRatio(next)});
controls.querySelectorAll('[data-herder-ratio]').forEach(button=>button.addEventListener('click',()=>setRatio(Number(button.dataset.herderRatio))));
controls.querySelector('[data-herder-close]').addEventListener('click',shut);
window.addEventListener('resize',()=>{if(!panel.hidden)layout()});
launch.addEventListener('click',open);close.addEventListener('click',shut);select.addEventListener('change',choose);
document.addEventListener('keydown',event=>{if(event.key==='Escape'&&!panel.hidden){event.preventDefault();shut()}});
choose();if(saved.open)open();
})();
</script>'''

SCRIPT = '''<script id="plan-app">
(()=>{
if(window.__lhcUI)window.__lhcUI.abort();window.__lhcUI=new AbortController();const signal=window.__lhcUI.signal;
const rail=document.querySelector('.time-rail');
if(rail){
const f=JSON.parse(rail.dataset.timeFrame),start=Date.parse(f.start),end=Date.parse(f.end),early=Date.parse(f.end_min);
const live=f.live&&/^https?:$/.test(location.protocol)&&!f.completed;
const frozen=Date.parse(f.snapshot),zone=Intl.DateTimeFormat().resolvedOptions().timeZone;
const fmt=n=>new Date(n).toLocaleString('ru-RU',{year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',hourCycle:'h23'});
const fmtClock=n=>new Date(n).toLocaleTimeString('ru-RU',{hour:'2-digit',minute:'2-digit',hourCycle:'h23',timeZone:zone});
const fmtDate=n=>new Date(n).toLocaleDateString('ru-RU',{day:'2-digit',month:'2-digit',timeZone:zone});
const duration=ms=>{const total=Math.max(0,Math.round(ms/60000)),h=Math.floor(total/60),m=total%60;return h?`${h}ч${String(m).padStart(2,'0')}мин`:`${m}мин`};
const qualifier=({file_birthtime:'восстановлено по файлам',leaf_created_at:'создание первого листа',recorded_start:'по записанному началу работы'})[f.start_source];
if(Number.isFinite(start))rail.querySelector('.time-rail-start').textContent='Начало плана: '+fmt(start)+(qualifier?' · '+qualifier:'');
const forecast=document.querySelector('[data-tile="forecast"] .kpi-value');
if(forecast&&Number.isFinite(end))forecast.textContent=(f.completed?'Завершено: ':'≈ ')+(early!==end?fmt(early)+' — ':'')+fmt(end)+' · '+zone;
const forecastHint=document.querySelector('[data-tile="forecast"] .kpi-hint');
if(forecastHint&&f.anchor)forecastHint.textContent=(f.completed?'Фактический финиш записан':(f.anchor_source==='plan_origin'?'Отсчёт от начала плана ':'Оценка по состоянию на ')+fmt(Date.parse(f.anchor)))+' · '+zone;
rail.querySelector('.time-rail-note').textContent='Цветная полоса показывает статусы задач; время указано под ней и не задаёт долю выполнения. Часовой пояс: '+zone+(f.completed?' · Завершённый план':'');
function clock(){
const now=live?Date.now():frozen,overdue=!f.completed&&Number.isFinite(end)&&now>end;
const text=(live?'Сейчас ':'На момент снимка ')+fmt(now)+(overdue?' · Прогнозный срок прошёл':'');
rail.dataset.overdue=String(overdue);rail.querySelector('.time-rail-clock').textContent=text;
const valid=Number.isFinite(end)&&end>0&&Number.isFinite(now);
const status=rail.querySelector('.time-rail-status'),minLabel=rail.querySelector('.time-rail-minimum'),maxLabel=rail.querySelector('.time-rail-maximum'),nowLabel=rail.querySelector('.time-rail-now');
const endText=f.end_label||'Прогноз неизвестен';
nowLabel.textContent=(live?'Сейчас ':'На момент снимка ')+fmt(now);
if(!valid){
minLabel.textContent='Минимум не оценён';maxLabel.textContent='Максимум не оценён';
rail.dataset.state='unknown';status.textContent=endText;return;
}
const min=Number.isFinite(early)?Math.min(early,end):end;
minLabel.textContent='Минимум ≈'+fmtClock(min)+' · '+fmtDate(min);
maxLabel.textContent=(f.completed?'Финиш ':'Максимум ≈')+fmtClock(end)+' · '+fmtDate(end);
nowLabel.title=fmt(now)+' · '+zone;
if(f.completed){status.textContent='План завершён · '+fmt(end);rail.dataset.state='complete';}
else if(now<min){status.textContent='До ранней оценки '+duration(min-now)+' · до верхней границы '+duration(end-now);rail.dataset.state='before';}
else if(now<=end){status.textContent='Ранняя оценка пройдена на '+duration(now-min)+' · до верхней границы '+duration(end-now);rail.dataset.state='early-passed';}
else{status.textContent='Верхняя оценка превышена на '+duration(now-end);rail.dataset.state='overdue';}
}
clock();
if(live){const timer=setInterval(clock,15000);signal.addEventListener('abort',()=>clearInterval(timer),{once:true})}
}
const sections=[...document.querySelectorAll('.plan-section')];
const links=[...document.querySelectorAll('.plan-sidebar a[href^="#"]')];
const key='lhc-ui:'+location.pathname;let saved={};
try{saved=JSON.parse(sessionStorage.getItem(key)||'{}')}catch(e){}
const nav=document.querySelector('.plan-sidebar');
let offset=24;
function measure(){offset=matchMedia('(max-width:650px)').matches||document.body.classList.contains('herder-open')?nav.getBoundingClientRect().height+12:24;document.documentElement.style.setProperty('--plan-anchor-offset',offset+'px')}
function scrollHost(){return document.body.classList.contains('herder-open')?document.getElementById('herder-plan-pane'):window}
function readingTop(){const host=scrollHost();return host===window?window.scrollY:host.scrollTop}
function readingTo(top){scrollHost().scrollTo({top,behavior:'instant'})}
function select(id){links.forEach(a=>{if(a.hash==='#'+id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')})}
function spy(){let active=sections[0];for(const s of sections){if(s.getBoundingClientRect().top<=offset+2)active=s}if(active)select(active.id)}
let frame=0;function schedule(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;if(!signal.aborted)spy()})}
function hashTarget(){try{return document.getElementById(decodeURIComponent(location.hash.slice(1)))}catch(e){return null}}
function fromHash(){const target=hashTarget();if(target){target.scrollIntoView();const section=target.closest('.plan-section');if(section)select(section.id)}}
links.forEach((a,i)=>{a.addEventListener('keydown',e=>{if(['ArrowDown','ArrowRight','ArrowUp','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?links.length-1:(i+(['ArrowDown','ArrowRight'].includes(e.key)?1:-1)+links.length)%links.length;links[n].focus();links[n].click()}},{signal})});
measure();window.addEventListener('resize',()=>{measure();schedule()},{signal});
window.addEventListener('scroll',schedule,{signal,passive:true});window.addEventListener('hashchange',fromHash,{signal});
document.addEventListener('scroll',schedule,{signal,passive:true,capture:true});
const search=document.getElementById('search');if(search&&saved.search){search.value=saved.search;search.dispatchEvent(new Event('input'))}
const chip=[...document.querySelectorAll('[data-filter]')].find(c=>c.dataset.filter===saved.filter);if(chip)chip.click();
// A live swap preserves the actual reading position even when the URL still
// contains an earlier clicked anchor. A deliberately opened hash wins on load.
const swap=window.__lhcReadingPosition;delete window.__lhcReadingPosition;
let reload=null;try{const publication=JSON.parse(sessionStorage.getItem('lhc-scroll:'+location.pathname)||'null');sessionStorage.removeItem('lhc-scroll:'+location.pathname);if(publication&&publication.hash===location.hash)reload=publication.scroll}catch(e){}
requestAnimationFrame(()=>{if(signal.aborted)return;if(swap!=null||reload!=null)readingTo(swap??reload);else if(hashTarget())fromHash();else if(saved.scroll!=null)readingTo(saved.scroll);spy()});
function save(){try{sessionStorage.setItem(key,JSON.stringify({search:search?.value||'',filter:document.querySelector('[data-filter].active')?.dataset.filter,scroll:readingTop()}))}catch(e){}}
window.addEventListener('lhc-before-swap',()=>{window.__lhcReadingPosition=readingTop()},{signal});
window.addEventListener('pagehide',save,{signal});window.addEventListener('lhc-before-swap',save,{signal});
let folded=[];window.addEventListener('beforeprint',()=>{folded=[...document.querySelectorAll('details:not([open])')];folded.forEach(d=>d.open=true)},{signal});
window.addEventListener('afterprint',()=>{folded.forEach(d=>d.open=false);folded=[]},{signal});
// Long notes remain readable without turning every section into a wall of text.
document.querySelectorAll('.brief-card p').forEach(p=>{if(p.textContent.length<700)return;const d=document.createElement('details'),s=document.createElement('summary');s.textContent='Читать полностью';p.before(d);d.append(s,p)});
})();
</script>'''


def decorate(document):
    nav = '<nav class="plan-sidebar" aria-label="Разделы плана"><div class="plan-brand">' + brand_link() + '</div>'
    nav += ''.join(f'<a href="#{key}">{label}</a>' for key, label in SECTIONS) + '</nav>'
    revisions = '<nav class="revision-strip" aria-label="Ревизии плана"><span aria-current="page">Текущий план</span></nav>'
    return (document.replace('</head>', STYLE + '</head>', 1)
            .replace('<body>', '<body>' + nav, 1)
            .replace('<!-- plan-revisions -->', '<!-- plan-revisions -->' + revisions, 1)
            .replace('</body>', SCRIPT + '</body>', 1))
