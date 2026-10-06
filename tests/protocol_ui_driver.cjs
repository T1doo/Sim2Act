'use strict';
const fs=require('node:fs'),path=require('node:path'),cp=require('node:child_process'),assert=require('node:assert/strict');
const [root,python,engine]=process.argv.slice(2),info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[];
let browser,dom,ws,seq=0,session,pending=new Map();
const wait=async(fn,label)=>{const end=Date.now()+12000;while(Date.now()<end){if(await fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('Wait failed: '+label);};
const check=(condition,label)=>{assert(condition,label);checks.push(label);console.error("CHECK "+label);fs.writeFileSync(path.join(root,"progress.json"),JSON.stringify(checks));};
const control=action=>JSON.parse(cp.execFileSync(python,['tests/fixtures/protocol_ui_control.py',root,action],{encoding:'utf8'}));
const command=(method,params={},sid=session)=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params,...(sid?{sessionId:sid}:{})}));});
let evaluate,httpSourceHashes={},outsideOriginRequests=0;
async function setup(){
 const bodies=Object.fromEntries(await Promise.all(['index.html','app.js','internal.js','protocol.js'].map(async file=>[file,await(await fetch(info.base+(file==='index.html'?'/':'/'+file))).text()])));
 httpSourceHashes=Object.fromEntries(Object.entries(bodies).map(([name,body])=>[name,require('node:crypto').createHash('sha256').update(body).digest('hex')]));
 if(engine==='dom'){
  const {JSDOM}=require('jsdom');const html=bodies['index.html'];
  dom=new JSDOM(html,{url:info.base,runScripts:'dangerously',pretendToBeVisual:true});
  const w=dom.window;w.fetch=(url,opt)=>{const target=new URL(url,info.base);if(target.origin!==new URL(info.base).origin){outsideOriginRequests++;throw Error('Outside local HTTP origin');}return fetch(target,opt);};w.crypto.randomUUID=require('node:crypto').randomUUID;
  for(const file of ['app.js','internal.js','protocol.js']){const script=w.document.createElement('script');script.textContent=bodies[file];w.document.body.append(script);}
  evaluate=async code=>await w.eval(code);
 }else{
  const profile=path.join(root,'chromium-profile');fs.mkdirSync(profile);
  browser=cp.spawn('chromium',['--headless','--remote-debugging-port=0','--remote-debugging-address=127.0.0.1','--user-data-dir='+profile,'--no-first-run','--no-default-browser-check','--enable-automation','--disable-background-networking','about:blank'],{stdio:['ignore','ignore','pipe']});
  let stderr='';browser.stderr.on('data',x=>stderr+=x);await wait(()=>{if(browser.exitCode!==null)throw Error('Chromium exited: '+stderr.slice(-1800));return fs.existsSync(path.join(profile,'DevToolsActivePort'));},'secure Chromium startup').catch(error=>{throw Error(error.message+' '+stderr.slice(-2000));});
  const [port,endpoint]=fs.readFileSync(path.join(profile,'DevToolsActivePort'),'utf8').trim().split('\n');
  ws=new WebSocket(`ws://127.0.0.1:${port}${endpoint}`);await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
  ws.onmessage=ev=>{const m=JSON.parse(ev.data);if(m.id&&pending.has(m.id)){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}};
  const {targetId}=await command('Target.createTarget',{url:info.base},null);session=(await command('Target.attachToTarget',{targetId,flatten:true},null)).sessionId;
  evaluate=async code=>{const r=await command('Runtime.evaluate',{expression:code,awaitPromise:true,returnByValue:true});if(r.exceptionDetails)throw Error(r.exceptionDetails.exception?.description||r.exceptionDetails.text);return r.result.value;};
  await wait(()=>evaluate('typeof refreshProtocol === "function"'),'page loaded');
  const args=(await command('Browser.getBrowserCommandLine',{},null)).arguments;
  check(!args.some(a=>/^--(no-sandbox|disable-web-security|disable-setuid-sandbox|single-process)/.test(a)),'native security switches intact');
 }
 await evaluate(`$('token').value='synthetic-test-A';$('connect').click()`);
 await wait(()=>evaluate(`!!protocolContext&&protocolCatalog.length===4`),'owned catalog');
 await evaluate(`$('project-select').value=${JSON.stringify(info.project)};$('project-select').dispatchEvent(new Event('change'))`);
 await wait(()=>evaluate(`protocolContext?.project===${JSON.stringify(info.project)}&&!$('protocol-source-submit').disabled`),'source ready');
}
(async()=>{try{
 await setup();
 check(await evaluate(`!JSON.stringify(protocolCatalog).includes('expected_output')&&!JSON.stringify(protocolCatalog).includes('gold')`),'public catalog excludes oracle');
 await evaluate(`window.sent=[];window.realFetch=fetch;window.dropSource=true;window.dropRecover=false;window.holdSource=false;window.releaseSource=null;window.fetch=async(url,opt)=>{const response=await realFetch(url,opt);if(opt?.method==='POST'&&String(url).includes('/protocol/')){sent.push({url:String(url),body:JSON.parse(opt.body)});if(String(url).endsWith('/source')&&holdSource){await new Promise(r=>releaseSource=r);}if(String(url).endsWith('/source')&&dropSource){dropSource=false;throw Error('Test: accepted source receipt lost');}if(String(url).endsWith('/recover')&&dropRecover){dropRecover=false;throw Error('Test: accepted recover receipt lost');}}return response;};$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate('sent.length===1&&!protocolContext.busy'),'lost submit settled');
 check(await evaluate('protocolContext.run===null'),'lost receipt does not invent result');
 await evaluate(`$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate(`protocolContext.run?.phase==='source'&&!protocolContext.busy`),'source receipt manual retry');
 check(await evaluate('JSON.stringify(sent[0].body)===JSON.stringify(sent[1].body)'),'lost submit manual original key and body');
 check(control('worker').requests===2,'actual source two mock provider requests');
 await evaluate(`$('protocol-read').click()`);
 await wait(()=>evaluate(`protocolContext.run?.status==='WAITING_APPROVAL'`),'source awaiting review');
 check(await evaluate(`$('protocol-extract').hidden&&$('protocol-state').textContent.includes('owner PENDING')&&protocolContext.run.semantic_status==='UNKNOWN'`),'pending owner never automatic acceptance');
 check(control('review').decision==='PASS','explicit persisted independent test review');
 await evaluate(`$('protocol-read').click()`);
 await wait(()=>evaluate(`!$('protocol-extract').hidden`),'source reviewed');
 check(await evaluate(`protocolContext.run.owner_semantic_acceptance==='PENDING'`),'registered PASS retains owner pending');
 await evaluate(`$('protocol-extract').click()`);
 await wait(()=>evaluate(`protocolContext.run?.phase==='extract'&&!protocolContext.busy`),'extract queued');
 check(control('worker').requests===1,'actual extraction provider request');
 await evaluate(`$('protocol-read').click()`);
 await wait(()=>evaluate(`!$('protocol-cold-form').hidden`),'compiled plan shown');
 await evaluate(`$('protocol-cold-contract').value='protocol.synthetic.a-cold.v1';$('protocol-cold-contract').dispatchEvent(new Event('change'));$('protocol-cold-form').requestSubmit()`);
 await wait(()=>evaluate(`protocolContext.run?.phase==='cold'&&!protocolContext.busy`),'cold queued');
 check(control('worker').requests===1,'actual cold new-input provider request');
 await evaluate(`$('protocol-read').click()`);
 await wait(()=>evaluate(`protocolContext.run?.status==='WAITING_APPROVAL'`),'cold awaiting review');
 check(await evaluate(`protocolContext.run.phase==='cold'&&protocolContext.run.owner_semantic_acceptance==='PENDING'`),'cold separate pending result');
 // First submission has no protocol run selected; even a pending generic history read wins immediately.
 await evaluate(`window.coldId=protocolContext.run.run_id;clearProtocolSelection();activeRun=null;holdSource=true;releaseSource=null;$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate('typeof releaseSource=== "function"'),'first-context source held');
 await evaluate(`window.historyGate=null;window.onceHistory=true;window.beforeHistoryFetch=fetch;window.fetch=async(url,opt)=>{const response=await beforeHistoryFetch(url,opt);if(onceHistory&&String(url).endsWith('/api/runs/'+coldId)){onceHistory=false;await new Promise(r=>historyGate=r);}return response;};void showRun(coldId)`);
 await wait(()=>evaluate(`typeof historyGate==='function'`),'generic history read held');
 await evaluate(`holdSource=false;releaseSource()`);
 await wait(()=>evaluate('!protocolContext.busy'),'first-context late submit settled');
 check(await evaluate(`activeRun===coldId&&(!protocolContext.run||protocolContext.run.run_id===coldId)`),'first-context accepted response cannot steal pending history selection');
 await evaluate(`historyGate();window.fetch=beforeHistoryFetch`);
 await wait(()=>evaluate('protocolContext.run?.run_id===coldId'),'held history finished');
 // Same-project response held across an explicit task selection: accepted receipt must not steal canvas.
 await evaluate(`window.coldId=protocolContext.run.run_id;holdSource=true;releaseSource=null;$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate('typeof releaseSource=== "function"'),'real accepted source response held');
 await evaluate(`showRun(coldId)`);
 await evaluate(`holdSource=false;releaseSource()`);
 await wait(()=>evaluate('!protocolContext.busy'),'late receipt returned');
 check(await evaluate('activeRun===coldId&&protocolContext.run.run_id===coldId'),'late same-project submit does not steal selected run');
 await evaluate(`holdSource=true;dropSource=true;releaseSource=null;$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate('typeof releaseSource=== "function"'),'real accepted failed receipt held');
 await evaluate(`(async()=>{await showRun(coldId);window.selectedState=$('protocol-state').textContent;})()`);
 await evaluate(`holdSource=false;releaseSource()`);
 await wait(()=>evaluate('!protocolContext.busy'),'late failed receipt returned');
 check(await evaluate(`activeRun===coldId&&protocolContext.run.run_id===coldId&&$('protocol-state').textContent===selectedState`),'late failed submit does not overwrite selected status');
 // Changed material listing must retain edits before submission.
 await evaluate(`$('protocol-inputs').querySelector('input').value='unsubmitted private edit'`);
 await fetch(info.base+`/api/projects/${info.project}/resources`,{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:JSON.stringify({name:'extra.txt',format:'txt',content:'Extra synthetic material.'})});
 await evaluate('refreshProtocol()');
 check(await evaluate(`$('protocol-inputs').querySelector('input').value==='unsubmitted private edit'`),'material refresh retains unsent input edits');
 // Catalog delayed across another owned project: old protected evidence cannot render.
 await evaluate(`window.oldFetch=fetch;window.catalogGate=null;window.fetch=async(url,opt)=>{const response=await oldFetch(url,opt);if(String(url).includes('/protocol/contracts')&&String(url).includes(${JSON.stringify(info.project)})){await new Promise(r=>catalogGate=r);}return response;};clearProtocol();void refreshProtocol()`);
 await wait(()=>evaluate(`typeof catalogGate==='function'`),'catalog held');
 await evaluate(`$('project-select').value=${JSON.stringify(info.other_project)};$('project-select').dispatchEvent(new Event('change'))`);
 await wait(()=>evaluate(`protocolContext?.project===${JSON.stringify(info.other_project)}&&protocolCatalog.length===4`),'other project ready');
 await evaluate('catalogGate();window.fetch=oldFetch');
 check(await evaluate(`protocolContext.project===${JSON.stringify(info.other_project)}&&$('protocol-detail').hidden&&!protocolMaterials.some(r=>r.id===${JSON.stringify(info.source)}||r.id===${JSON.stringify(info.cold)})`),'late catalog cannot restore other project evidence');
 // New page intent: explicit real default Worker must wait without a provider call.
 await evaluate(`protocolIntents.clear();$('project-select').value=${JSON.stringify(info.project)};$('project-select').dispatchEvent(new Event('change'))`);
 await wait(()=>evaluate(`protocolContext?.project===${JSON.stringify(info.project)}&&!$('protocol-source-submit').disabled`),'fresh source ready');
 await evaluate(`$('protocol-source-form').requestSubmit()`);
 await wait(()=>evaluate(`protocolContext.run?.phase==='source'&&!protocolContext.busy`),'default source queued');
 check(control('default-worker').requests===0,'default worker zero provider sends');
 await evaluate(`$('protocol-read').click()`);
 await wait(()=>evaluate(`protocolContext.run?.status==='WAITING_RESOURCE'`),'default waiting resource');
 await evaluate(`dropRecover=true;$('protocol-recover').click()`);
 await wait(()=>evaluate(`!protocolContext.busy&&!$('protocol-recover-retry').hidden`),'lost metadata receipt');
 await evaluate(`$('protocol-recover-retry').click()`);
 await wait(()=>evaluate(`!protocolContext.busy&&$('protocol-recover-retry').hidden`),'manual metadata receipt retry');
 check(await evaluate(`(()=>{const r=sent.filter(x=>x.url.endsWith('/recover'));return r.length===2&&JSON.stringify(r[0].body)===JSON.stringify(r[1].body)&&protocolContext.run.status==='PAUSED';})()`),'recover original version fence key; no continuation');
 // Recovery read response delayed over a selection must not overwrite the new task.
 await evaluate(`window.recoverId=protocolContext.run.run_id;window.getGate=null;window.onceGet=true;window.beforeGetFetch=fetch;window.fetch=async(url,opt)=>{const response=await beforeGetFetch(url,opt);if(onceGet&&String(url).endsWith('/protocol/runs/'+recoverId)&&(!opt?.method||opt.method==='GET')){onceGet=false;await new Promise(r=>getGate=r);}return response;};$('protocol-recover').click()`);
 await wait(()=>evaluate(`typeof getGate==='function'`),'recovery read held');
 await evaluate(`(async()=>{await showRun(coldId);window.selectedState=$('protocol-state').textContent;})()`);
 await evaluate(`getGate();window.fetch=beforeGetFetch`);
 await wait(()=>evaluate('!protocolContext.busy'),'late recovery read finished');
 check(await evaluate(`activeRun===coldId&&protocolContext.run.run_id===coldId&&!$('protocol-state').textContent.includes('核对结果')`),'late recovery read does not overwrite another task');
 if(!/^run_[a-f0-9]{32}$/.test(info.other_run||''))throw Error('Owned other-project protocol fixture is missing; cannot claim project-bound negative coverage');
 await evaluate(`showRun(${JSON.stringify(info.other_run)}).catch(()=>{})`);
 check(await evaluate(`$('protocol-detail').hidden&&$('protocol-result').textContent===''&&protocolContext.run===null`),'generic history read must pass current-project bound recheck');
 await evaluate(`showRun(coldId)`);
 // Current identity changes while a protected read is in flight.
 await evaluate(`window.identityGate=null;window.onceIdentity=true;window.beforeIdentityFetch=fetch;window.fetch=async(url,opt)=>{const response=await beforeIdentityFetch(url,opt);if(onceIdentity&&String(url).endsWith('/protocol/runs/'+coldId)){onceIdentity=false;await new Promise(r=>identityGate=r);}return response;};void showProtocolRun(coldId)`);
 await wait(()=>evaluate(`typeof identityGate==='function'`),'protected identity read held');
 await evaluate(`token='synthetic-test-B';void refreshProtocol()`);
 await wait(()=>evaluate(`protocolContext?.token==='synthetic-test-B'`),'other identity context');
 await evaluate(`identityGate();window.fetch=beforeIdentityFetch`);
 check(await evaluate(`$('protocol-detail').hidden&&$('protocol-result').textContent===''&&protocolContext.run===null`),'late prior-identity evidence cleared');
 const unauthorized=await fetch(info.base+`/api/projects/${info.project}/protocol/contracts`,{headers:{Authorization:'Bearer synthetic-test-B'}});
 check(unauthorized.status===403||unauthorized.status===404,'other identity catalog rejected');
 if(engine==='chromium'){
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  check(await evaluate('document.documentElement.scrollWidth<=390'),'390 viewport document fits');
  const png=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:true});fs.writeFileSync(path.join(root,'protocol-native.png'),Buffer.from(png.data,'base64'));
 }
 console.log(JSON.stringify({status:'PASS',engine,checks:checks.length,labels:checks,httpSourceHashes,outsideOriginRequests,live:false,owner_semantic_acceptance:'PENDING',browser:engine==='chromium'?'installed Linux Chromium CDP':'NOT_RUN'}));
 }catch(error){console.error(error.stack);console.error(JSON.stringify({httpSourceHashes,outsideOriginRequests,native_ui:'NOT_ACCEPTED'}));process.exitCode=1;}finally{if(dom)dom.window.close();if(ws)ws.close();if(browser){browser.kill('SIGTERM');await Promise.race([new Promise(r=>browser.once('exit',r)),new Promise(r=>setTimeout(r,3000))]);if(browser.exitCode===null)browser.kill('SIGKILL');}}})();
