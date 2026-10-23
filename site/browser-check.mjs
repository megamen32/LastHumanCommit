// Optional real-browser smoke, Node 22 + local Chrome; no npm dependencies.
import { spawn } from 'node:child_process';
import { createServer } from 'node:http';
import { readFile, mkdtemp, mkdir, writeFile, rm } from 'node:fs/promises';
import path from 'node:path';
import assert from 'node:assert/strict';
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const root = path.resolve('site/dist');
await mkdir('.tmp', {recursive:true});
const profile = await mkdtemp(path.resolve('.tmp/landing-chrome-'));
let chrome, server, socket, failData = false;
const runtimeErrors = [];
try {
  server = createServer(async (req,res) => {
    try {
      const pathname = decodeURIComponent(new URL(req.url,'http://localhost').pathname);
      if (failData && pathname === '/data.json') {res.writeHead(503); res.end('unavailable'); return;}
      const filename = path.resolve(root, '.' + (pathname === '/' ? '/index.html' : pathname));
      if (!filename.startsWith(root + path.sep)) {res.writeHead(403);res.end();return;}
      const mime = {'.html':'text/html; charset=utf-8','.js':'application/javascript','.css':'text/css','.json':'application/json'};
      const bytes = await readFile(filename);
      res.writeHead(200, {'Content-Type':mime[path.extname(filename)] || 'application/octet-stream','Cache-Control':'no-store'});
      res.end(bytes);
    } catch (_) {res.writeHead(404);res.end('not found');}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const base = 'http://127.0.0.1:' + server.address().port + '/';
  chrome = spawn(process.env.CHROME || 'google-chrome', ['--headless=new','--no-sandbox','--disable-dev-shm-usage','--no-first-run','--no-default-browser-check','--remote-debugging-port=0','--user-data-dir='+profile,'about:blank'], {stdio:['ignore','ignore','pipe']});
  const browserURL = await new Promise((resolve,reject)=>{
    const timer=setTimeout(()=>reject(new Error('Chrome startup timeout')),12000);let output='';
    chrome.stderr.on('data',chunk=>{output+=chunk;const match=output.match(/DevTools listening on (ws:\/\/[^\s]+)/);if(match){clearTimeout(timer);resolve(match[1]);}});
    chrome.on('exit',code=>{clearTimeout(timer);reject(new Error('Chrome exited '+code));});
  });
  const origin = new URL(browserURL).origin.replace('ws:','http:');
  const targets=await (await fetch(origin+'/json/list')).json();
  const target=targets.find(t=>t.type==='page');
  socket=new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((resolve,reject)=>{socket.onopen=resolve;socket.onerror=reject;});
  let id=0;const pending=new Map();
  socket.onmessage=event=>{const message=JSON.parse(event.data);if(message.method==='Runtime.exceptionThrown') runtimeErrors.push(message.params.exceptionDetails.text);if(message.id && pending.has(message.id)){const job=pending.get(message.id);pending.delete(message.id);clearTimeout(job.timer);message.error?job.reject(new Error(message.error.message)):job.resolve(message.result);}};
  const send=(method,params={})=>new Promise((resolve,reject)=>{const current=++id;const timer=setTimeout(()=>{pending.delete(current);reject(new Error('CDP timeout '+method));},15000);pending.set(current,{resolve,reject,timer});socket.send(JSON.stringify({id:current,method,params}));});
  const evaluate=async expression=>{const result=await send('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(result.exceptionDetails)throw new Error(JSON.stringify(result.exceptionDetails));return result.result.value;};
  const until=async expression=>{for(let n=0;n<60;n++){if(await evaluate(expression))return;await delay(70);}throw new Error('Page condition timeout: '+expression);};
  const visit=async url=>{await send('Page.navigate',{url});await until('document.readyState === "complete"');await until('document.querySelectorAll(".journey-stage").length > 0 || document.querySelector(".role-error") !== null');};
  const viewport=async width=>send('Emulation.setDeviceMetricsOverride',{width,height:950,deviceScaleFactor:1,mobile:false});
  await send('Page.enable');await send('Runtime.enable');
  const data=JSON.parse(await readFile(path.join(root,'data.json'),'utf8'));
  for(const language of ['en','ru']) {
    await viewport(1440);await visit(base+'?lang='+language);
    assert.equal(await evaluate('document.documentElement.lang'),language);
    assert.equal(await evaluate('document.querySelectorAll(".role-card").length'),data.roles.length);
    const originals=await evaluate('Array.from(document.querySelectorAll(".role-details pre"),el=>el.textContent)');
    assert.deepEqual(originals,data.roles.map(role=>role.details));
    for(const mode of ['full','quick']) {
      await evaluate('document.querySelector("[data-mode='+mode+']").click()');
      assert.equal(await evaluate('document.querySelectorAll(".journey-stage").length'),data.story[mode].length);
      for(const width of [320,390,768,1024,1440]) {
        await viewport(width);
        const layout=await evaluate('({w:innerWidth,scroll:document.documentElement.scrollWidth,overflow:Array.from(document.querySelectorAll(".site-nav,.hero h1,.journey-stage,.step-detail,.role-card,.mission,.schedule")).filter(el=>{const r=el.getBoundingClientRect();return r.width>0 && (r.left< -1 || r.right>innerWidth+1)}).map(el=>el.className)})');
        assert.ok(layout.scroll<=layout.w+1,language+' '+mode+' '+width+' overflow '+JSON.stringify(layout));
        assert.deepEqual(layout.overflow,[],language+' '+mode+' '+width+' clipped components');
      }
      const last=data.story[mode].at(-1);
      await evaluate('document.querySelectorAll(".journey-stage")[document.querySelectorAll(".journey-stage").length-1].click()');
      assert.equal(await evaluate('document.getElementById("stage-source").textContent'),last.sourceExcerpt);
      assert.equal(await evaluate('document.getElementById("stage-link").href'),last.source);
    }
  }
  console.log('PASS: EN/RU, Full 14 stages, Quick 6 stages, exact Git roles and stage sources, 20 responsive layouts (320–1440px).');
  await viewport(1440);await visit(base+'?lang=en');
  await evaluate('document.querySelector("[data-stage=yagni]").click();document.querySelector(".role-toggle").click();document.querySelector("[data-lang=ru]").click()');
  assert.equal(await evaluate('document.querySelector(".journey-stage.is-selected").dataset.stage'),'yagni');
  assert.equal(await evaluate('document.querySelector(".role-toggle").getAttribute("aria-expanded")'),'true');
  assert.equal(await evaluate('new URL(location.href).searchParams.get("lang")'),'ru');
  await visit(base);assert.equal(await evaluate('document.documentElement.lang'),'ru');
  await evaluate('document.getElementById("full-tab").focus()');
  await send('Input.dispatchKeyEvent',{type:'keyDown',key:'ArrowRight',code:'ArrowRight'});
  assert.equal(await evaluate('document.getElementById("quick-tab").getAttribute("aria-selected")'),'true');
  console.log('PASS: selected stage, expanded role and language persistence; keyboard mode switch.');
  const injected=await send('Page.addScriptToEvaluateOnNewDocument',{source:'Object.defineProperty(window,"localStorage",{get(){throw new DOMException("denied","SecurityError")}});Object.defineProperty(Navigator.prototype,"language",{get:()=>"ru-RU"});'});
  await visit(base);assert.equal(await evaluate('document.documentElement.lang'),'ru');
  await evaluate('document.querySelector("[data-lang=en]").click()');assert.equal(await evaluate('document.documentElement.lang'),'en');
  await send('Page.removeScriptToEvaluateOnNewDocument',{identifier:injected.identifier});
  failData=true;await visit(base+'?lang=ru');
  assert.ok(await evaluate('document.getElementById("roles-count").textContent.includes("НЕДОСТУПЕН")'));
  await evaluate('document.querySelector("[data-lang=en]").click()');
  assert.ok(await evaluate('document.getElementById("roles-count").textContent.includes("UNAVAILABLE")'));
  failData=false;
  console.log('PASS: browser-language default, unavailable storage, translated honest data-failure state.');
  for(const [language,width] of [['en',1440],['ru',1440],['ru',390]]) {
    await viewport(width);await visit(base+'?lang='+language);await evaluate('scrollTo(0,0)');
    const image=await send('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
    await writeFile(path.resolve('.tmp/landing-'+language+'-'+width+'.png'),Buffer.from(image.data,'base64'));
  }
  await viewport(1440); await visit(base+"?lang=ru");
  await evaluate('document.querySelector("#plan").scrollIntoView();document.querySelector("#plan iframe").loading="eager"');
  await until('Boolean(document.querySelector("#plan iframe").contentDocument?.querySelector(".task-details-trigger"))');
  assert.equal(await evaluate('document.querySelector("#plan iframe").contentDocument.querySelectorAll(".task-details-trigger").length'),16);
  await evaluate('document.querySelector("#plan iframe").contentDocument.querySelector(".task-details-trigger").click()');
  assert.equal(await evaluate('document.querySelector("#plan iframe").contentDocument.querySelector(".task-details-trigger").getAttribute("aria-expanded")'),"true");
  await evaluate('document.querySelector("#plan iframe").contentDocument.querySelector("[data-filter=running]").click()');
  assert.equal(await evaluate('document.querySelector("#plan iframe").contentDocument.querySelector(".chip.active").dataset.filter'),"running");
  for (const width of [320,390,768,1440]) {
    await viewport(width);
    assert.ok(await evaluate('document.documentElement.scrollWidth <= innerWidth + 1'));
  }
  assert.equal(await evaluate('document.querySelector("#plan a[download]").getAttribute("download")'),"lhc-example-plan.html");
  console.log("PASS: real embedded Gantt, sixteen tasks, detail opening, running filter, download link and four viewport widths.");
  assert.deepEqual(runtimeErrors,[]);
  console.log('PASS: no uncaught browser exceptions. Screenshots saved under .tmp/.');
} finally {
  if(socket)socket.close();
  if(chrome){chrome.kill('SIGTERM');await new Promise(resolve=>{if(chrome.exitCode!==null)return resolve();chrome.once('exit',resolve);setTimeout(resolve,2000);});}
  if(server)await new Promise(resolve=>server.close(resolve));
  await rm(profile,{recursive:true,force:true,maxRetries:5,retryDelay:200});
}
