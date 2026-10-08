'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[],hashes={};
let dom,w,$,page,release,held=false,hold=false,historyFailure=false;
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async(fn,label)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+label);};
const idle=async()=>{await wait(()=>page.requests===0&&page.actions.size===0,'HTTP and actions drained');await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];};
function track(window){for(const name of ['onclick','onchange','onsubmit']){const d=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==='function'?function(...args){const r=fn.apply(this,args);if(r?.then){page.actions.add(r);r.then(()=>page.actions.delete(r),e=>{page.errors.push(e);page.actions.delete(r);});}return r;}:fn);}});}window.addEventListener('error',e=>page.errors.push(e.error||Error(e.message)));}
const button=()=>w.document.querySelector('.report-presentation-propose'),confirm=()=>w.document.querySelector('.report-presentation-confirm'),texts=()=>[...w.document.querySelectorAll('.report-view-text')].map(n=>n.textContent);
async function reconnect(token){$('login').hidden=false;$('token').value=token;$('connect').click();await wait(()=>$('login').hidden,'real identity connect handler');await idle();}
(async()=>{try{
 dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};track(w);w.setInterval=()=>0;
 w.fetch=async(url,opts={})=>{page.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const entry={path:target.pathname,method:opts.method||'GET',body:opts.body&&JSON.parse(opts.body)};requests.push(entry);const response=await fetch(target,opts);entry.status=response.status;
 const selected=info.phase==='checks'?entry.path.endsWith('/checks'):entry.path.endsWith('/report-presentations');
 if(hold&&selected&&entry.method==='POST'){hold=false;held=true;entry.held=true;check(response.status===201,'held POST was accepted by real server');await new Promise(r=>release=r);held=false;if(info.action==='lost_response')throw TypeError('Controlled loss after accepted late response');}
 if(historyFailure&&entry.method==='GET'&&entry.path.endsWith('/report-presentations')){historyFailure=false;entry.injected='read_failure';return{ok:false,status:503,json:async()=>({error:{code:'CONTROLLED_READ_FAILURE'}})};}
 return response;}finally{page.requests--;}};
 for(const name of ['app.js','internal.js','protocol.js','use.js','conditional-runs.js','conditional-apps.js','report-manifest.js']){const code=await(await fetch(info.base+'/'+name)).text();hashes[name]=crypto.createHash('sha256').update(code).digest('hex');const s=w.document.createElement('script');s.textContent=code;w.document.body.append(s);}
 await reconnect('synthetic-test-A');await w.refreshApps();await w.showApp(info.app,info.project);check(texts().join('|')==='ALLOW','initial registered decision display');
 if(info.phase==='checks'){button().click();await idle();check(confirm()&&!confirm().disabled,'exact saved definition ready');}
 const targetButton=info.phase==='checks'?confirm():button();hold=true;targetButton.click();await wait(()=>held,'held accepted selected response');
 if(info.action==='other_app'){await w.showApp(info.peer,info.project);check(!button(),'other application is selected');}
 else if(info.action==='identity'){await reconnect('synthetic-test-B');check(!button(),'different identity clears Report controls');}
 else if(info.action==='refresh'){await w.readManifestHistory();check(targetButton.isConnected===false,'same context history replaces original DOM');}
 else{w.clearApp();await w.showApp(info.app,info.project);check(texts().join('|')==='ALLOW','new same-app page history returned before release');}
 const postsBefore=requests.filter(r=>r.method==='POST').length,readsBefore=requests.length;
 if(info.action==='revoke'){const response=await fetch(info.base+'/test-only-revoke',{method:'POST'});assert(response.ok);}
 if(info.action==='history_failure')historyFailure=true;
 release();release=null;await idle();check(requests.filter(r=>r.method==='POST').length===postsBefore,'late completion never repeats or continues a write');
 if(info.action==='other_app'||info.action==='identity'){check(!button()&&!texts().includes(info.explanation),'late old content never appears in foreign selection');check(!requests.slice(readsBefore).some(r=>r.path.includes('/apps/'+info.app+'/')),'foreign selection does not read old protected history');}
 else if(info.action==='revoke'||info.action==='history_failure'){check(!button()&&texts().length===0,'failed fresh authorization/read clears protected old and new content');check($('error').textContent.includes('当前展示回读失败'),'current failed read provides guarded feedback');if(info.action==='history_failure'){await w.showApp(info.app,info.project);check(button(),'explicit retry opens fresh authorized history');}}
 else{check(requests.slice(readsBefore).some(r=>r.method==='GET'&&r.path.endsWith('/report-presentations')),'new page independently rereads protected presentation history');}
 if(!['other_app','identity','revoke'].includes(info.action)){
  if(info.phase==='checks'){check(texts().join('|')==='ALLOW|'+info.explanation,'new page renders authorized checked explanation after late receipt');check(confirm().disabled,'checked receipt is reconciled without another POST');}
  else{check(texts().join('|')==='ALLOW','late definition cannot invent checked content');check(confirm()&&!confirm().hidden&&!confirm().disabled,'late definition enables exact-version confirmation on new page');confirm().click();await idle();check(texts().join('|')==='ALLOW|'+info.explanation,'explicit check renders fresh explanation');}
 }
 if(info.action==='identity'){await reconnect('synthetic-test-A');await w.showApp(info.app,info.project);check(info.phase==='checks'?texts().join('|')==='ALLOW|'+info.explanation:!confirm().disabled,'real reconnect restores only fresh own receipts');}
 check(!w.reportExecuted,'script-shaped result remains inert text');check(Object.keys(hashes).length===7,'actual product script hashes captured');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',case:info.phase+'_'+info.action,checks,requests,hashes,polling:'NOT_RUN',native:'NOT_RUN',overall:'NOT_ACCEPTED'},null,2));
 }catch(e){fs.writeFileSync(path.join(root,'failure.json'),JSON.stringify({error:e.stack,checks,requests,hashes,texts:w?texts():[],buttons:w?[button()?.disabled,confirm()?.disabled]:[],pending_requests:page?.requests,pending_actions:page?.actions.size},null,2));console.error(e.stack);process.exitCode=1;}
 finally{if(release){release();release=null;}if(page)await idle();dom?.window.close();}})();
