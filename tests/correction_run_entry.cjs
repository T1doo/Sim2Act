'use strict';
// Actual page/controllers with synthesized responses and one explicit cancel POST. No HTTP, Worker,
// model execution, real human judgement or native browser is exercised here.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {JSDOM}=require('jsdom'),durable=require('./durable_browser.cjs')();
const web=path.resolve(__dirname,'../src/sim2act/web');
const p='proj_'+'1'.repeat(32),q='proj_'+'2'.repeat(32),a='app_'+'3'.repeat(32),i='instance_'+'4'.repeat(32),j='instance_'+'5'.repeat(32);
const parent='run_'+'6'.repeat(32),child='run_'+'7'.repeat(32),release='irelease_'+'8'.repeat(32),f='a'.repeat(64),key='synthetic-correction-key';
const app={id:a,name:'synthetic saved natural',project_id:p,fingerprint:f,runtime_id:'synthetic-runtime',candidate:{namespace:'pa-natural-spec-app.v1',goal_application:{},goal:{title:'synthetic'},spec_recipe:{steps:[]},manifest:{data_bindings:[]}},input_guidance:{mode:'MODEL_SPEC_CHECKLIST'}};
let dom,w,$,calls,gate,receipt,childAvailable,childStatus,denied,controlState,controlBody,allowCancel;
const result={classification:'ACTUAL_PAGE_CONTROLLERS_SYNTHESIZED_NAVIGATION_AND_CANCEL',checks:[],cases:[],worker:'NOT_RUN',real_model:'NOT_RUN',native_browser:'NOT_RUN',real_human_semantics:'NOT_RUN'};
const check=(ok,label)=>{assert(ok,label);result.checks.push(label);};
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function wait(test){for(let n=0;n<300;n++){if(test())return;await tick();}throw Error('synthetic GET gate not reached');}
function instance(id){return {id,principal_id:'synthetic-A',source_app_id:a,project_id:p,runtime_id:'synthetic-runtime',release_id:release,release_fingerprint:f,revision:1,data_version:childAvailable&&childStatus==='SUCCEEDED'?2:1,runs:[{id:parent,status:'SUCCEEDED',result_version:1},...(childAvailable?[{id:child,status:childStatus,result_version:childStatus==='SUCCEEDED'?2:null}]:[])],data:[],formal_publication_enabled:false};}
function ownerState(rid){const contract={principal_id:'synthetic-A',project_id:p,instance_id:i,app_id:a,run_id:rid,version:'owner.natural-spec.v1',formal_publication_enabled:false,technical_semantic_status:'UNKNOWN'};return {...contract,sequence:0,history:[],latest:null,record:null,recovered:null,content_access:true,current:contract,owner_acceptance:'PENDING'};}
async function setup(){
 dom?.window.close();calls=[];gate=null;childAvailable=false;childStatus='SUCCEEDED';denied=false;allowCancel=false;controlBody=null;controlState={namespace:'INTERNAL_ENGINEERING_ONLY',id:child,instance_id:i,status:'QUEUED',version:1,cancel_intent:false,content_access:false,formal_publication_enabled:false};
 dom=new JSDOM(fs.readFileSync(path.join(web,'index.html'),'utf8'),{url:'http://synthetic.invalid/',runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 w.setInterval=()=>1;durable.install(w);w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});
 w.fetch=async(url,options={})=>{
  const method=options.method||'GET';calls.push({url,method});if(method!=='GET'){assert(allowCancel&&url===`/api/internal/instances/${i}/runs/${child}/commands`);assert.deepEqual(JSON.parse(options.body),{command:'cancel',version:1});controlState={...controlState,status:'CANCELLED',version:2,cancel_intent:true};}
  if(gate&&!gate.used&&url===gate.url){gate.used=true;await new Promise(resolve=>gate.resolve=resolve);}
  if(denied&&url===`/api/internal/instances/${i}`)return {ok:false,status:403,json:async()=>({error:{code:'GRANT_REVOKED'}})};
  let value;
  if(url===`/api/internal/instances/${i}/runs/${child}/control-status`)value=controlBody||controlState;
  else if(method==='POST')value={namespace:'INTERNAL_ENGINEERING_ONLY',formal_publication_enabled:false,status:'CANCELLED'};
  else if(url===`/api/apps/${a}`)value=app;
  else if(url===`/api/internal/apps/${a}/instances`)value={items:[instance(i),instance(j)]};
  else if(url.endsWith('/releases'))value={items:[]};
  else if(url===`/api/internal/instances/${i}`)value=instance(i);
  else if(url===`/api/internal/instances/${j}`)value=instance(j);
  else if(url===`/api/internal/releases/${release}`)value={id:release,fingerprint:f};
  else if(url===`/api/internal/instances/${i}/runs/${parent}/correction-requests/${key}`)value=receipt;
  else if(url.endsWith('/spec-owner-review'))value=ownerState(url.includes(child)?child:parent);
  else if(url===`/api/internal/instances/${i}/runs/${child}`)value={id:child,instance_id:i,status:childStatus,result_version:childStatus==='SUCCEEDED'?2:null};
  else if(url===`/api/internal/instances/${i}/runs/${parent}`)value={id:parent,instance_id:i,status:'SUCCEEDED',result_version:1};
  else value=[];
  return {ok:true,status:200,json:async()=>structuredClone(value)};
 };
 for(const name of ['app.js','internal.js','use.js','owner-review.js']){const script=w.document.createElement('script');script.textContent=fs.readFileSync(path.join(web,name),'utf8');w.document.body.append(script);}
 w.eval('renderSwitch=()=>{};renderPBUse=async()=>{};openNaturalLogic=async()=>{};');
 $('project-select').append(new w.Option('P',p),new w.Option('Q',q));$('project-select').value=p;w.eval('token="synthetic-A";selectWorkspace("apps");');
 await w.openSavedNaturalUse(a,i,'NATURAL_PA');await w.showInternalRun(parent);
 const context={run_id:parent,instance_id:i,goal:{goal:'unchanged synthetic Goal'},items:[{id:'one',text:'unchanged criterion'}],release_id:release,release_fingerprint:f,instance_revision:1,result_version:1};
 const candidate={synthetic:true};context.effective_plan_fingerprint=await w.ownerHash(candidate);
 const metadata={id:'synthetic-declaration',kind:'DECIDE',status:'REJECTED'};
 const payload={metadata,choices:[{item_id:'one',decision:'REJECT',reason:'synthetic judgement'}],contract:{goal:context.goal,items:context.items}};
 const review={namespace:'natural-spec-correction.v1',principal_id:'synthetic-A',project_id:p,instance_id:i,parent_run_id:parent,request_key:key,formal_publication_enabled:false,semantic_status:'UNKNOWN',owner_acceptance:'PENDING',real_model_allowance:0,proposed_artifact_writes_at_most:1,consent:'RUN_NEW_BOUNDED_CORRECTION_KEEP_ORIGINAL_GOAL_AND_CRITERIA',context,effective_candidate:candidate,declaration:{...metadata,payload,fingerprint:await w.ownerHash(payload)}};
 review.review_fingerprint=await w.ownerHash(review);
 receipt={namespace:'natural-spec-correction.v1',principal_id:'synthetic-A',project_id:p,instance_id:i,parent_run_id:parent,run_id:child,request_key:key,formal_publication_enabled:false,semantic_status:'UNKNOWN',owner_acceptance:'PENDING',status:'SUCCEEDED',result_version:2,review};
}
async function recover(){const promise=w.eval(`correctionRecover(ownerView,${JSON.stringify(key)},"RUN")`);await promise;childAvailable=true;return promise;}
const open=()=>$('correction-open-run').onclick();
function navigate(kind){
 if(kind==='workspace'){w.selectWorkspace('resources');w.selectWorkspace('apps');}
 else if(kind==='project'){$('project-select').value=q;w.clearApp();$('project-select').value=p;w.clearApp();}
 else if(kind==='identity'){w.eval('identityConnectionGeneration++;clearIdentityView();token="synthetic-A";');$('project-select').append(new w.Option('P',p));$('project-select').value=p;}
 else if(kind==='instance')return w.showInternalInstance(j);
 else if(kind==='run')return w.showInternalRun(parent);
}
(async()=>{try{
 await setup();check($('correction-open-run').hidden,'no entry without a verified accepted receipt');
 await recover();check(!$('correction-open-run').hidden&&!$('correction-open-run').disabled,'verified receipt exposes an explicit entry');
 check(w.eval('engineering.run.id')===parent,'receipt never navigates automatically');
 const at=calls.length;await open();
 check(w.eval('engineering.run.id')===child&&$('owner-run').value===child,'entry selects exact child Run and same-Run owner review');
 check($('owner-status').textContent.includes('PENDING'),'new Run keeps independent PENDING judgement');
 check(calls.slice(at).filter(c=>c.url===`/api/internal/instances/${i}`).length===1,'refreshes instance selector once before reading child');
 check(calls.slice(at).at(-1).url===`/api/internal/instances/${i}/runs/${child}/spec-owner-review`,'existing controller reads exact child owner endpoint');
 check(calls.every(c=>c.method==='GET'),'entry creates no Run, prepare, decision or submission');
 await setup();await recover();childStatus='QUEUED';await open();
 check(w.eval('engineering.run.id')===child&&w.eval('engineering.run.status')==='QUEUED'&&$('owner-run').value==='','queued child opens progress without claiming an acceptable result');
 await setup();await recover();gate={url:`/api/internal/instances/${i}`,used:false};
 const first=open();await wait(()=>gate.used);const atDouble=calls.length;await open();check(calls.length===atDouble,'double click cannot start a second navigation');gate.resolve();await first;
 await setup();gate={url:`/api/internal/instances/${i}/runs/${parent}/correction-requests/${key}`,used:false};
 const delayed=recover();await wait(()=>gate.used);navigate('workspace');gate.resolve();await delayed;
 check($('correction-open-run').hidden&&w.eval('engineering.run.id')===parent,'late receipt after workspace navigation cannot expose an entry');
 for(const nav of ['workspace','project','identity','instance']){
  await setup();await recover();gate={url:`/api/internal/instances/${i}`,used:false};
  const opening=open();await wait(()=>gate.used);await navigate(nav);const atNav=calls.length;$('internal-run-detail').textContent='CURRENT CLEAN';gate.resolve();await opening;
  check(calls.slice(atNav).every(c=>!c.url.includes(`/runs/${child}`)),`${nav}: stale instance refresh cannot follow child`);
  check($('internal-run-detail').textContent==='CURRENT CLEAN',`${nav}: stale opening cannot paint new selection`);
  result.cases.push({nav,calls:structuredClone(calls)});
 }
 await setup();await recover();gate={url:`/api/internal/releases/${release}`,used:false};
 const choosing=open();await wait(()=>gate.used);await w.showInternalRun(parent);const atChoice=calls.length;gate.resolve();await choosing;
 check(w.eval('engineering.run.id')===parent&&calls.slice(atChoice).every(c=>!c.url.includes(`/runs/${child}`)),'new Run selection during visible instance refresh prevents child followup');
 await setup();await recover();gate={url:`/api/internal/instances/${i}/runs/${child}`,used:false};
 const opening=open();await wait(()=>gate.used);await navigate('instance');const atRun=calls.length;$('internal-run-detail').textContent='CURRENT CLEAN';gate.resolve();await opening;
 check($('internal-run-detail').textContent==='CURRENT CLEAN'&&calls.slice(atRun).every(c=>!c.url.endsWith('/spec-owner-review')),'late child GET cannot paint or start owner read after instance selection');
 for(const bad of [{project_id:q},{run_id:parent},{run_id:'invalid'}]){
  await setup();Object.assign(receipt,bad);await assert.rejects(recover(),/新Run回执绑定不一致/);check($('correction-open-run').hidden,'incorrect receipt never exposes navigation');
 }
 await setup();await recover();denied=true;allowCancel=true;await open();
 check(!$('projects').hidden&&$('apps').hidden&&$('internal-run-detail').textContent===''&&w.eval('engineering')===null,'revoked content enters separate Projects stop panel with private application cleared');
 check($('known-internal-stop-status').textContent.includes(child)&&!$('known-internal-stop-cancel').disabled,'owner metadata status enables exact known-child cancellation');
 gate={url:`/api/internal/instances/${i}/runs/${child}/commands`,used:false};
 const cancelling=$('known-internal-stop-cancel').onclick();await wait(()=>gate.used);await $('known-internal-stop-cancel').onclick();gate.resolve();await cancelling;
 check(calls.filter(c=>c.method==='POST').length===1&&$('known-internal-stop-status').textContent.includes('CANCELLED'),'explicit double click cancels exactly once then only reads metadata');
 await setup();await recover();denied=true;gate={url:`/api/internal/instances/${i}/runs/${child}/control-status`,used:false};
 const stopping=open();await wait(()=>gate.used);navigate('identity');$('result').textContent='CURRENT CLEAN';gate.resolve();await stopping;
 check($('result').textContent==='CURRENT CLEAN'&&calls.every(c=>c.method==='GET'),'late owner metadata cannot paint another connection or send commands');
 await setup();await recover();denied=true;await open();w.selectWorkspace('apps');w.selectWorkspace('projects');await tick();
 check($('known-internal-stop-read').disabled&&$('known-internal-stop-cancel').disabled&&$('known-internal-stop-status').textContent.includes('已失效'),'workspace return visibly invalidates old stop controls');
 await setup();await recover();denied=true;controlBody={...controlState,instance_id:j};await open();
 check($('known-internal-stop-cancel').disabled&&$('known-internal-stop-status').textContent.includes('绑定不一致'),'wrong metadata instance never enables cancellation');
 result.status='PASS';
}catch(error){result.status='FAIL';result.error=error.stack;process.exitCode=1;}finally{
 result.assets=Object.fromEntries(['index.html','app.js','internal.js','use.js','owner-review.js'].map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(web,name))).digest('hex')]));
 fs.writeFileSync(process.argv[2],JSON.stringify(result,null,2));dom?.window.close();console.log(JSON.stringify({status:result.status,checks:result.checks.length,error:result.error}));
}})();
