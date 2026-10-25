"""Shared, dependency-free navigation for standalone and published plan views."""

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
.plan-sidebar a{color:var(--muted);text-decoration:none;padding:12px 14px;border-radius:10px;font-size:14px;min-height:44px;box-sizing:border-box;display:flex;align-items:center;gap:10px}
.plan-sidebar a[aria-current=location]{background:var(--accent);color:white;font-weight:650}
.plan-sidebar a:focus-visible,button:focus-visible{outline:3px solid var(--accent);outline-offset:3px}
.plan-section{min-width:0;scroll-margin-top:var(--plan-anchor-offset,24px)}.plan-section [id]{scroll-margin-top:var(--plan-anchor-offset,24px)}.plan-section>h2{font-size:23px;margin:22px 0 18px}
.revision-strip{display:flex;gap:6px;overflow-x:auto;max-width:100%;padding:2px 0 16px;margin-bottom:6px;align-items:center}
.revision-strip a,.revision-strip span{flex:none;white-space:nowrap;padding:7px 13px;border:1px solid var(--line);border-radius:8px;color:var(--muted);font-size:12px;text-decoration:none}
.revision-strip [aria-current=page]{color:var(--text);border-color:var(--accent);background:var(--panel);font-weight:650}
body .progress-strip{position:relative;top:auto;margin:0 0 18px;box-shadow:none}
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
</style>'''

SCRIPT = '''<script id="plan-app">
(()=>{
if(window.__lhcUI)window.__lhcUI.abort();window.__lhcUI=new AbortController();const signal=window.__lhcUI.signal;
const sections=[...document.querySelectorAll('.plan-section')];
const links=[...document.querySelectorAll('.plan-sidebar a')];
const key='lhc-ui:'+location.pathname;let saved={};
try{saved=JSON.parse(sessionStorage.getItem(key)||'{}')}catch(e){}
const nav=document.querySelector('.plan-sidebar');
let offset=24;
function measure(){offset=matchMedia('(max-width:650px)').matches?nav.getBoundingClientRect().height+12:24;document.documentElement.style.setProperty('--plan-anchor-offset',offset+'px')}
function select(id){links.forEach(a=>{if(a.hash==='#'+id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')})}
function spy(){let active=sections[0];for(const s of sections){if(s.getBoundingClientRect().top<=offset+2)active=s}if(active)select(active.id)}
let frame=0;function schedule(){if(!frame)frame=requestAnimationFrame(()=>{frame=0;if(!signal.aborted)spy()})}
function hashTarget(){try{return document.getElementById(decodeURIComponent(location.hash.slice(1)))}catch(e){return null}}
function fromHash(){const target=hashTarget();if(target){target.scrollIntoView();const section=target.closest('.plan-section');if(section)select(section.id)}}
links.forEach((a,i)=>{a.addEventListener('keydown',e=>{if(['ArrowDown','ArrowRight','ArrowUp','ArrowLeft','Home','End'].includes(e.key)){e.preventDefault();const n=e.key==='Home'?0:e.key==='End'?links.length-1:(i+(['ArrowDown','ArrowRight'].includes(e.key)?1:-1)+links.length)%links.length;links[n].focus();links[n].click()}},{signal})});
measure();window.addEventListener('resize',()=>{measure();schedule()},{signal});
window.addEventListener('scroll',schedule,{signal,passive:true});window.addEventListener('hashchange',fromHash,{signal});
const search=document.getElementById('search');if(search&&saved.search){search.value=saved.search;search.dispatchEvent(new Event('input'))}
const chip=[...document.querySelectorAll('[data-filter]')].find(c=>c.dataset.filter===saved.filter);if(chip)chip.click();
// A live swap preserves the actual reading position even when the URL still
// contains an earlier clicked anchor. A deliberately opened hash wins on load.
const swap=window.__lhcReadingPosition;delete window.__lhcReadingPosition;
let reload=null;try{const publication=JSON.parse(sessionStorage.getItem('lhc-scroll:'+location.pathname)||'null');sessionStorage.removeItem('lhc-scroll:'+location.pathname);if(publication&&publication.hash===location.hash)reload=publication.scroll}catch(e){}
requestAnimationFrame(()=>{if(signal.aborted)return;if(swap!=null||reload!=null)window.scrollTo({top:swap??reload,behavior:'instant'});else if(hashTarget())fromHash();else if(saved.scroll!=null)window.scrollTo({top:saved.scroll,behavior:'instant'});spy()});
function save(){try{sessionStorage.setItem(key,JSON.stringify({search:search?.value||'',filter:document.querySelector('[data-filter].active')?.dataset.filter,scroll:window.scrollY}))}catch(e){}}
window.addEventListener('lhc-before-swap',()=>{window.__lhcReadingPosition=window.scrollY},{signal});
window.addEventListener('pagehide',save,{signal});window.addEventListener('lhc-before-swap',save,{signal});
let folded=[];window.addEventListener('beforeprint',()=>{folded=[...document.querySelectorAll('details:not([open])')];folded.forEach(d=>d.open=true)},{signal});
window.addEventListener('afterprint',()=>{folded.forEach(d=>d.open=false);folded=[]},{signal});
// Long notes remain readable without turning every section into a wall of text.
document.querySelectorAll('.brief-card p').forEach(p=>{if(p.textContent.length<700)return;const d=document.createElement('details'),s=document.createElement('summary');s.textContent='Читать полностью';p.before(d);d.append(s,p)});
})();
</script>'''


def decorate(document):
    nav = '<nav class="plan-sidebar" aria-label="Разделы плана"><div class="plan-brand">LHC / ПЛАН</div>'
    nav += ''.join(f'<a href="#{key}">{label}</a>' for key, label in SECTIONS) + '</nav>'
    revisions = '<nav class="revision-strip" aria-label="Ревизии плана"><span aria-current="page">Текущий план</span></nav>'
    return (document.replace('</head>', STYLE + '</head>', 1)
            .replace('<body>', '<body>' + nav, 1)
            .replace('<!-- plan-revisions -->', '<!-- plan-revisions -->' + revisions, 1)
            .replace('</body>', SCRIPT + '</body>', 1))
