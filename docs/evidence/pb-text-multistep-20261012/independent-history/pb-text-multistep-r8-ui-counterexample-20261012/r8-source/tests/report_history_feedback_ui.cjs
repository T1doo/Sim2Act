'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'))),checks=[],requests=[],hashes={};
let dom,w,$,page,release,held=false,hold=false,damage=false,damageRelease,damageHeld=false,awayState;
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async(fn,label)=>{const end=Date.now()+6000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+label);};
const idle=async()=>{await wait(()=>page.requests===0&&page.actions.size===0,'HTTP and actions drained');await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];};
function track(window){for(const name of ['onclick','onchange','onsubmit']){const d=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==='function'?function(...args){const r=fn.apply(this,args);if(r?.then){page.actions.add(r);r.then(()=>page.actions.delete(r),e=>{page.errors.push(e);page.actions.delete(r);});}return r;}:fn);}});}window.addEventListener('error',e=>page.errors.push(e.error||Error(e.message)));}
const button=()=>w.document.querySelector('.report-presentation-propose'),confirm=()=>w.document.querySelector('.report-presentation-confirm'),texts=()=>[...w.document.querySelectorAll('.report-view-text')].map(n=>n.textContent);
async function reconnect(token,drain=true){$('login').hidden=false;$('token').value=token;$('connect').click();await wait(()=>$('login').hidden,'real identity connect handler');if(drain)await idle();else await wait(()=>(held||damageHeld)&&page.requests===1&&page.actions.size===1,'identity requests drained except deliberately held old proof');}
(async()=>{try{
 dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};track(w);w.setInterval=()=>0;
 w.fetch=async(url,opts={})=>{page.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);const entry={path:target.pathname,method:opts.method||'GET',body:opts.body&&JSON.parse(opts.body)};requests.push(entry);const response=await fetch(target,opts);entry.status=response.status;
 const selected=info.phase==='checks'?entry.path.endsWith('/checks'):entry.path.endsWith('/report-presentations');
 if(hold&&selected&&entry.method==='POST'){hold=false;held=true;entry.held=true;check(response.status===201,'held POST was accepted by real server');await new Promise(r=>release=r);held=false;throw TypeError('Controlled loss after accepted late response');}
 if(damage&&entry.method==='GET'&&entry.path.endsWith(info.stage==='manifest'?'/history':'/report-presentations')){
 damage=false;const data=await response.json();check(response.status===200,'damaged proof is real HTTP200 valid JSON');entry.injected=info.stage;
 if(info.stage==='manifest'){assert(data.history.length);data.history[0].run.namespace='invalid-proof';}
 else if(info.stage==='envelope')data.namespace='invalid-proof';
 else{assert(data.items.length);data.items[0].patch.namespace='invalid-proof';}
 if(info.away){damageHeld=true;await new Promise(r=>damageRelease=r);damageHeld=false;}
 return{ok:true,status:200,json:async()=>data};
 }
 return response;}finally{page.requests--;}};
 for(const name of ['app.js','internal.js','protocol.js','use.js','conditional-runs.js','conditional-apps.js','report-manifest.js']){const code=await(await fetch(info.base+'/'+name)).text();hashes[name]=crypto.createHash('sha256').update(code).digest('hex');const s=w.document.createElement('script');s.textContent=code;w.document.body.append(s);}
 await reconnect('synthetic-test-A');await w.refreshApps();await w.showApp(info.app,info.project);check(texts().join('|')==='ALLOW','initial registered decision display');
 if(info.phase==='checks'){button().click();await idle();check(confirm()&&!confirm().disabled,'exact saved definition ready');}
 const targetButton=info.phase==='checks'?confirm():button();hold=true;targetButton.click();await wait(()=>held,'held accepted selected response');
 w.clearApp();await w.showApp(info.app,info.project);check(texts().join('|')==='ALLOW','new same-app page history returned before late release');
 const exactIntent=()=>w.eval('JSON.stringify(Array.from(presentationIntents.values()).map(v=>({deriveKey:v.deriveKey,planKey:v.planKey,definitionKey:v.definitionKey,checkKey:v.checkKey,body:v.body})))');
 const originalIntent=exactIntent();
 const postsBefore=requests.filter(r=>r.method==='POST').length,readsBefore=requests.length;
 damage=true;release();release=null;
 if(info.away){await wait(()=>damageHeld,'controlled damaged history held after server read');
  if(info.away==='identity'){await reconnect('synthetic-test-B',false);}else await w.showApp(info.peer,info.project);
  awayState=JSON.stringify({active:w.eval('activeApp'),project:$('project-select').value,title:$('app-title').textContent,manifest:$('app-manifest').textContent,error:$('error').textContent});
  damageRelease();damageRelease=null;
 }
 await idle();check(requests.filter(r=>r.method==='POST').length===postsBefore,'late completion never repeats or continues a write');
 check(exactIntent()===originalIntent,'damaged read preserves exact UNKNOWN body and original keys');
 if(info.away){check(JSON.stringify({active:w.eval('activeApp'),project:$('project-select').value,title:$('app-title').textContent,manifest:$('app-manifest').textContent,error:$('error').textContent})===awayState,'foreign selection state survives old damaged history unchanged');check(!button()&&!texts().includes(info.explanation),'damaged old read never clears or paints foreign Report content');check(!$('error').textContent.includes('当前展示回读失败'),'old damaged read cannot show feedback in foreign selection');
  if(info.away==='identity'){await reconnect('synthetic-test-A');await w.showApp(info.app,info.project);}else await w.showApp(info.app,info.project);
 }else{check(!button()&&texts().length===0,'invalid current proof clears all protected presentation content');check($('error').textContent.includes('当前展示回读失败'),'current invalid HTTP200 read provides guarded feedback');await w.showApp(info.app,info.project);}
 check(requests.filter(r=>r.method==='POST').length===postsBefore,'explicit reopening restores history without POST');
 check(requests.slice(readsBefore).some(r=>r.method==='GET'&&r.path.endsWith('/report-presentations')),'fresh protected history restores exact accepted receipt');
 check(exactIntent()===originalIntent,'history recovery preserves original keys and body');
 if(info.phase==='checks'){check(texts().join('|')==='ALLOW|'+info.explanation,'fresh own checked explanation restored');check(confirm().disabled,'checked receipt recovered without new write');}
 else{check(texts().join('|')==='ALLOW','definition recovery cannot invent checked content');check(confirm()&&!confirm().hidden&&!confirm().disabled,'exact saved definition is ready for explicit confirmation');confirm().click();await idle();check(texts().join('|')==='ALLOW|'+info.explanation,'explicit check renders fresh explanation');}
 check(!w.reportExecuted,'script-shaped result remains inert text');check(Object.keys(hashes).length===7,'actual product script hashes captured');
 fs.writeFileSync(path.join(root,'results.json'),JSON.stringify({status:'PASS',case:info.phase+'_'+info.stage+'_'+(info.away||'current'),checks,requests,hashes,polling:'NOT_RUN',native:'NOT_RUN',overall:'NOT_ACCEPTED'},null,2));
 }catch(e){fs.writeFileSync(path.join(root,'failure.json'),JSON.stringify({error:e.stack,checks,requests,hashes,texts:w?texts():[],buttons:w?[button()?.disabled,confirm()?.disabled]:[],pending_requests:page?.requests,pending_actions:page?.actions.size},null,2));console.error(e.stack);process.exitCode=1;}
 finally{if(release){release();release=null;}if(damageRelease){damageRelease();damageRelease=null;}if(page)await idle();dom?.window.close();}})();
