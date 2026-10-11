'use strict';
// Full product DOM, controlled replies from an actual SQLite/Worker candidate fixture.
// No actual HTTP, native browser, or semantic claim; the real HTTP suite is separate.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('/workspace/node-tools/node_modules/jsdom');
const out='/tmp/pa-text-handoff-review-20261011',web='/workspace/Sim2Act/src/sim2act/web';
const fixture=JSON.parse(fs.readFileSync(path.join(out,'ui-fixture.json'))),appId=fixture.run.result.candidate.manifest.app_id,otherApp='app_'+'9'.repeat(32);
const clone=v=>JSON.parse(JSON.stringify(v));
const accepted={...clone(fixture.accepted),goal_acceptance:'NOT_RUN',candidate_generated:false,generation_policy:clone(fixture.run.contract.snapshot.application_generation)};
const app={id:appId,project_id:fixture.card.project_id,name:'Exact generated text application',runtime_id:'appruntime_'+'7'.repeat(32),fingerprint:'a'.repeat(64),
 candidate:{...clone(fixture.run.result.candidate),goal_application:{run_id:fixture.run.id,candidate_fingerprint:fixture.run.result.candidate_fingerprint}},
 input_guidance:{mode:'REGISTERED_LITERAL'},history:[]};
const other={...clone(app),id:otherApp,name:'Other explicitly selected application'};other.candidate.manifest.app_id=otherApp;
let dom,w,$,calls,hold,lostConfirm,internalHold,acceptedMode;const results=[];
const settle=()=>new Promise(r=>setImmediate(r));
function visible(e){
 if(!e?.isConnected)return false;
 for(let n=e;n;n=n.parentElement){
  if(n.hidden||n.hasAttribute('inert')||n.getAttribute('aria-hidden')==='true')return false;
  const style=w.getComputedStyle(n);if(style.display==='none'||['hidden','collapse'].includes(style.visibility))return false;
  if(n.tagName==='DETAILS'&&!n.open&&!n.querySelector('summary')?.contains(e))return false;
 }
 return true;
}
const selected=()=>w.document.querySelector('#workspace-nav [aria-current="true"]').dataset.tab;
async function click(e){assert(visible(e),'User click target must have no hidden/inert ancestor: '+e?.id);assert(!e.matches(':disabled'),'User click target must be enabled: '+e.id);e.focus();const previous=e.onclick;let task;e.onclick=function(event){task=previous?.call(this,event);return task;};e.click();e.onclick=previous;await task;}
async function setup(mode='normal'){
 dom?.window.close();dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://synthetic.invalid',runScripts:'dangerously'});
 w=dom.window;const style=w.document.createElement('style');style.textContent=fs.readFileSync(path.join(web,'app.css'),'utf8');w.document.head.append(style);$=id=>w.document.getElementById(id);calls=[];hold=null;lostConfirm=false;internalHold=null;acceptedMode=mode;
 w.setInterval=()=>0;w.crypto.randomUUID=()=>crypto.randomUUID();w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,'subtle',{value:crypto.webcrypto.subtle});
 w.fetch=async(url,opts={})=>{
  const method=opts.method||'GET';calls.push({url,method,body:opts.body&&JSON.parse(opts.body)});let value;
  if(hold&&!hold.used&&hold.url===url){hold.used=true;value=await new Promise(resolve=>hold.resolve=resolve);}
  if(value===undefined){
   if(method==='POST'&&url.endsWith('/confirm-application-candidate')){if(lostConfirm){lostConfirm=false;throw Error('Controlled lost accepted confirmation receipt');}value={id:appId,state:'PREVIEW_ONLY'};}
   else if(method==='POST'){value=clone(accepted);if(acceptedMode==='object-id')value.run_id={unexpected:'object'};if(acceptedMode==='wrong-legal-id')value.run_id='run_'+'9'.repeat(32);}
   else if(url.includes('/confirmed-application-candidate?'))value={id:appId,state:'PREVIEW_ONLY',recovered:true};
   else if(url===`/api/goal-cards/${fixture.card.id}`)value=clone(fixture.card);
   else if(url===`/api/runs/${fixture.run.id}`)value=clone(fixture.run);
   else if(url.includes('/application-runs?request_key='))value=clone(fixture.run);
   else if(url==='/api/apps')value={items:[clone(other),clone(app)]};
   else if(url===`/api/apps/${appId}`)value=clone(app);
   else if(url===`/api/apps/${otherApp}`)value=clone(other);
   else if(url.endsWith('/candidate-options'))value={goal_version:1,items:[],materials:[],capabilities:[]};
   else if(url.endsWith('/goal-cards')||url.endsWith('/candidates'))value={items:[]};
   else value=[];
  }
  return {ok:true,status:200,json:async()=>value};
 };
 for(const name of ['app.js','goal-application.js']){const script=w.document.createElement('script');script.textContent=fs.readFileSync(path.join(web,name),'utf8');w.document.body.append(script);}
 $('project-select').append(new w.Option('Project',fixture.card.project_id));$('project-select').value=fixture.card.project_id;w.eval('token="synthetic-A"');$('login').hidden=true;
 await w.showGoalCard(fixture.card.id);await w.refreshApps();
 $('goal-card-goal').value='PREEXISTING UNSAVED GOAL MUST REMAIN';await click($('goal-application-start'));
 if(mode==='normal'){$('goal-application-ack').checked=true;$('goal-application-ack').dispatchEvent(new w.Event('change'));assert(visible($('goal-application-confirm'))&&!$('goal-application-confirm').disabled);}
}
const confirmPath=()=>`/api/runs/${fixture.run.id}/confirm-application-candidate`;
const readPath=()=>`/api/apps/${appId}`;
const pause=async(url,fn)=>{hold={url,used:false};const task=fn();while(!hold.used)await settle();return {task,resolve:hold.resolve};};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab="${id}"]`));
async function test(name,fn){try{await fn();results.push({name,status:'PASS'});}catch(e){results.push({name,status:'FAIL',error:e.message});}}
function checkShown(){assert.equal(selected(),'apps');assert(visible($('app-agent-term')));assert.equal(w.eval('activeApp'),appId);assert($('app-title').textContent.includes(app.name));assert([$('app-agent-term'),$('app-title')].includes(w.document.activeElement)&&visible(w.document.activeElement),'Exact visible app input or title receives focus');assert.equal($('goal-card-goal').value,'PREEXISTING UNSAVED GOAL MUST REMAIN');}
(async()=>{try{
 await test('successful explicit confirmation shows and focuses exact app, preserves prior goal draft',async()=>{await setup();await click($('goal-application-confirm'));checkShown();await nav('projects');assert.equal($('goal-card-goal').value,'PREEXISTING UNSAVED GOAL MUST REMAIN');});
 await test('lost accepted confirmation keyed GET visibly opens exact app without a second POST',async()=>{await setup();lostConfirm=true;await click($('goal-application-confirm'));assert.equal(selected(),'projects');await click($('goal-application-confirm-read'));checkShown();assert.equal(calls.filter(c=>c.method==='POST'&&c.url===confirmPath()).length,1);});
 for(const edge of ['confirm','app-read']){
  await test(edge+' delay plus navigation ABA never auto-navigates',async()=>{await setup();const p=await pause(edge==='confirm'?confirmPath():readPath(),()=>click($('goal-application-confirm')));await nav('resources');await nav('projects');p.resolve(edge==='confirm'?{id:appId,state:'PREVIEW_ONLY'}:clone(app));await p.task;assert.equal(selected(),'projects');assert.equal($('goal-card-goal').value,'PREEXISTING UNSAVED GOAL MUST REMAIN');});
  await test(edge+' delay plus later goal edit preserves active draft and workspace',async()=>{await setup();const p=await pause(edge==='confirm'?confirmPath():readPath(),()=>click($('goal-application-confirm')));$('goal-card-goal').value='NEWER EDIT WHILE CONFIRMING';$('goal-card-goal').dispatchEvent(new w.Event('input'));p.resolve(edge==='confirm'?{id:appId,state:'PREVIEW_ONLY'}:clone(app));await p.task;assert.equal(selected(),'projects');assert.equal($('goal-card-goal').value,'NEWER EDIT WHILE CONFIRMING');});
  await test(edge+' delay cannot replace a later explicitly chosen application',async()=>{await setup();const p=await pause(edge==='confirm'?confirmPath():readPath(),()=>click($('goal-application-confirm')));await nav('apps');const button=[...$('app-list').querySelectorAll('button')].find(b=>b.parentNode.textContent.includes(other.name));await click(button);p.resolve(edge==='confirm'?{id:appId,state:'PREVIEW_ONLY'}:clone(app));await p.task;assert.equal(selected(),'apps');assert.equal(w.eval('activeApp'),otherApp);assert($('app-title').textContent.includes(other.name));});
  await test(edge+' delay cannot overwrite an explicitly created new goal draft',async()=>{await setup();const p=await pause(edge==='confirm'?confirmPath():readPath(),()=>click($('goal-application-confirm')));await click($('goal-card-new'));$('goal-card-title').value='NEW GOAL DRAFT';p.resolve(edge==='confirm'?{id:appId,state:'PREVIEW_ONLY'}:clone(app));await p.task;assert.equal(selected(),'projects');assert.equal($('goal-card-title').value,'NEW GOAL DRAFT');assert.equal(w.eval('activeGoalCard'),null);});
 }
 await test('internal-read delay after app paint cannot override navigation ABA',async()=>{await setup();w.openInternal=async()=>new Promise(resolve=>internalHold=resolve);const task=click($('goal-application-confirm'));while(!internalHold)await settle();await nav('resources');await nav('projects');internalHold();await task;assert.equal(selected(),'projects');assert.equal($('goal-card-goal').value,'PREEXISTING UNSAVED GOAL MUST REMAIN');});
 await test('keyed confirmation recovery delay respects later navigation ABA',async()=>{await setup();lostConfirm=true;await click($('goal-application-confirm'));const entry=w.eval('goalApplications.get(goalApplicationKey())');const url=`/api/runs/${fixture.run.id}/confirmed-application-candidate?request_key=${encodeURIComponent(entry.confirmBody.request_key)}`;const p=await pause(url,()=>click($('goal-application-confirm-read')));await nav('resources');await nav('projects');p.resolve({id:appId,state:'PREVIEW_ONLY',recovered:true});await p.task;assert.equal(selected(),'projects');assert.equal(calls.filter(c=>c.method==='POST'&&c.url===confirmPath()).length,1);});
 for(const mode of ['object-id','wrong-legal-id'])await test('accepted '+mode+' cannot poison original-key recovery',async()=>{
   await setup(mode);assert.equal(selected(),'projects');assert.equal($('goal-application-confirm').disabled,true);
   const body=calls.find(c=>c.method==='POST'&&c.url.endsWith('/application-runs')).body;
   await click($('goal-application-read'));
   const proof=JSON.parse($('goal-application-proof').textContent);assert.equal(proof.run_id,fixture.run.id);
   assert(calls.some(c=>c.method==='GET'&&c.url.includes('/application-runs?request_key='+encodeURIComponent(body.request_key))));
   assert.equal(calls.filter(c=>c.method==='POST'&&c.url.endsWith('/application-runs')).length,1);
   assert(!calls.some(c=>c.url.includes('[object Object]')));
 });
 const hashes=Object.fromEntries(['app.js','goal-application.js','index.html','app.css'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(web,n))).digest('hex')]));
 const output={status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',api:'CONTROLLED_NOT_HTTP',fixture:'ACTUAL_SQLITE_NORMAL_WORKER_MOCK',native:'NOT_RUN',semantic:'NOT_RUN',visibility:'ACTUAL_CSS_ANCESTORS_HIDDEN_INERT_DETAILS_ENABLED_JSDOM',loaded_source_sha256:hashes,results};
 fs.writeFileSync(path.join(out,process.argv[2]||'handoff-independent.json'),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));if(output.status==='FAIL')process.exitCode=1;
}finally{dom?.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
