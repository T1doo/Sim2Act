'use strict';
// Full product DOM, controlled replies from an actual SQLite/Worker candidate fixture.
// No actual HTTP, native browser, or semantic claim; the real HTTP suite is separate.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('/workspace/node-tools/node_modules/jsdom');
const out='/tmp/pa-text-edit-generation-review-20261011',web='/workspace/Sim2Act/src/sim2act/web';
const fixture=JSON.parse(fs.readFileSync(path.join(out,'ui-fixture.json'))),appId=fixture.run.result.candidate.manifest.app_id,otherApp='app_'+'9'.repeat(32);
const clone=v=>JSON.parse(JSON.stringify(v));
const accepted={...clone(fixture.accepted),goal_acceptance:'NOT_RUN',candidate_generated:false,generation_policy:clone(fixture.run.contract.snapshot.application_generation)};
const app={id:appId,project_id:fixture.card.project_id,name:'Exact generated text application',runtime_id:'appruntime_'+'7'.repeat(32),fingerprint:'a'.repeat(64),
 candidate:{...clone(fixture.run.result.candidate),goal_application:{run_id:fixture.run.id,candidate_fingerprint:fixture.run.result.candidate_fingerprint}},
 input_guidance:{mode:'REGISTERED_LITERAL'},history:[]};
const other={...clone(app),id:otherApp,name:'Other explicitly selected application'};other.candidate.manifest.app_id=otherApp;
let dom,w,$,calls,hold,lostConfirm,internalHold,acceptedMode;const results=[],stageEvidence=[];
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

function selection(){return JSON.stringify(w.eval('[workspaceSelectionGeneration,appSelectionGeneration,goalSelectionGeneration,activeGoalCard.id]'));}
function inputUndo(field){
 const element=$('goal-card-'+field);assert(visible(element));assert(!element.matches(':disabled'));element.focus();
 const before=element.value, priorSelection=selection(),events=[];
 const observe=event=>events.push({type:event.type,inputType:event.inputType||null,isTrusted:event.isTrusted});
 element.addEventListener('input',observe);element.addEventListener('change',observe);
 if(field==='resources'){
   const states=[...element.options].map(o=>o.selected);assert(states.length,'Actual form select must contain a material option');
   element.options[0].selected=!states[0];element.dispatchEvent(new w.Event('input',{bubbles:true}));element.dispatchEvent(new w.Event('change',{bubbles:true}));
   [...element.options].forEach((o,i)=>o.selected=states[i]);element.dispatchEvent(new w.Event('input',{bubbles:true}));element.dispatchEvent(new w.Event('change',{bubbles:true}));
   assert.deepEqual([...element.options].map(o=>o.selected),states,'Material selection returns to exact original set');
 }else{
   const end=before.length,suffix=' INDEPENDENT EDIT THEN UNDO';
   element.setSelectionRange(end,end);element.setRangeText(suffix,end,end,'end');
   element.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:'insertText',data:suffix}));
   element.setRangeText('',end,end+suffix.length,'end');
   element.dispatchEvent(new w.InputEvent('input',{bubbles:true,inputType:'historyUndo',data:null}));
 }
 assert.equal(element.value,before,'Final value must equal original to expose ABA');assert.equal(selection(),priorSelection,'Existing workspace/app/goal generations stay unchanged');
 element.removeEventListener('input',observe);element.removeEventListener('change',observe);
 return {element,before,events};
}
async function startPaused(stage){
 if(stage==='recover'){
  lostConfirm=true;await click($('goal-application-confirm'));
  const entry=w.eval('goalApplications.get(goalApplicationKey())');
  const url=`/api/runs/${fixture.run.id}/confirmed-application-candidate?request_key=${encodeURIComponent(entry.confirmBody.request_key)}`;
  return pause(url,()=>click($('goal-application-confirm-read')));
 }
 return pause(stage==='confirm'?confirmPath():readPath(),()=>click($('goal-application-confirm')));
}
(async()=>{try{
 for(const stage of ['confirm','recover','app-read'])for(const field of ['title','goal','known','assumptions','unresolved','constraints','acceptance_checks','resources']){
  await test(stage+' delayed handoff, '+field+' edit/input-undo ABA never navigates or steals focus',async()=>{
    await setup();const p=await startPaused(stage);const evidence=inputUndo(field);
    p.resolve(stage==='app-read'?clone(app):{id:appId,state:'PREVIEW_ONLY',recovered:stage==='recover'});await p.task;
    assert.equal(selected(),'projects','Older handoff lost authority after real DOM input/select ABA');
    assert(visible(evidence.element));assert.equal(w.document.activeElement,evidence.element,'Edited visible field retains focus');
    assert.equal(evidence.element.value,evidence.before);assert.equal($('goal-card-goal').value,'PREEXISTING UNSAVED GOAL MUST REMAIN');
    assert.equal(calls.filter(c=>c.method==='POST'&&c.url===confirmPath()).length,1,'No second confirmation POST');
       stageEvidence.push({stage,field,events:evidence.events,nativeUndo:'NOT_RUN',api:'CONTROLLED_NOT_HTTP'});
  });
 }
 for(const stage of ['confirm','recover'])await test(stage+' unchanged saved selection still visibly opens exact app',async()=>{
    await setup();if(stage==='recover'){lostConfirm=true;await click($('goal-application-confirm'));await click($('goal-application-confirm-read'));}else await click($('goal-application-confirm'));checkShown();
 });
 const hashes=Object.fromEntries(['app.js','goal-application.js','index.html','app.css'].map(n=>[n,crypto.createHash('sha256').update(fs.readFileSync(path.join(web,n))).digest('hex')]));
 const output={status:results.every(r=>r.status==='PASS')?'PASS':'FAIL',tests:results.length,passed:results.filter(r=>r.status==='PASS').length,failed:results.filter(r=>r.status==='FAIL').length,api:'CONTROLLED_NOT_HTTP',fixture:'PREVIOUS_ACTUAL_SQLITE_NORMAL_WORKER_MOCK',liveRequests:0,nativeBrowserUndo:'NOT_RUN',events:'JSDOM synthesized InputEvent insertText/historyUndo and select input/change',loaded_source_sha256:hashes,results,successful_event_evidence:stageEvidence};
 fs.writeFileSync(path.join(out,process.argv[2]||'controlled-final.json'),JSON.stringify(output,null,2));console.log(JSON.stringify(output,null,2));if(output.status==='FAIL')process.exitCode=1;
}finally{dom?.window.close();}})().catch(e=>{console.error(e.stack);process.exitCode=1;});
