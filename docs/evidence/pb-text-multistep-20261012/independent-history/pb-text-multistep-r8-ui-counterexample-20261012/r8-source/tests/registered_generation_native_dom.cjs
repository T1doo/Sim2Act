'use strict';
// Direct actual HTTP-backed jsdom flow. Does not emulate Playwright or run the native module.
// No browser, renderer, layout, PNG or security claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict'),path=require('node:path');
const {execFile}=require('node:child_process'),execAsync=require('node:util').promisify(execFile),{JSDOM}=require('jsdom');
const root=process.argv[2],python=process.argv[3],info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8')),base=`http://127.0.0.1:${info.port}`;
const injectPollRace=process.argv[4]==='--inject-poll-race',pollRace={enabled:injectPollRace,events:[],observedNull:false,recovered:false};
let raceArmed=false,heldPollRun=false,releasePollRun,releasePollInstance,holdPollInstance=false,refreshStarted=false,raceIid,raceRid,raceApp;
function raceEvent(name){pollRace.events.push({name,...w.eval('({iid:engineering?.instance?.id||null,rid:engineering?.run?.id||null,status:engineering?.run?.status||null,instanceGeneration:engineering?.instanceGeneration,runGeneration:engineering?.runGeneration,busy:engineering?.busy})')});}
let dom,w,hold=false,releaseHeld,drop=false,lostBody,lostApp;const calls=[],checks=[];
const $=id=>w.document.getElementById(id);
function check(name,value){assert.ok(value,name);checks.push({name,status:'PASS'});}
async function wait(fn){const end=Date.now()+12000;while(!fn()){assert.ok(Date.now()<end,'DOM wait timeout');await new Promise(r=>setTimeout(r,15));}}
async function create(){
 dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:base,runScripts:'outside-only'});w=dom.window;
 w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;w.crypto.randomUUID=require('node:crypto').randomUUID;
 w.fetch=async(url,options={})=>{
  // Test-only response barriers preserve the normal poll and actual HTTP payloads.
  if(holdPollInstance&&url===`/api/internal/instances/${raceIid}`){
   raceEvent('poll terminal transition cleared selections');const gate=new Promise(resolve=>releasePollInstance=resolve);
   const r=await fetch(new URL(url,base),options);await gate;raceEvent('instance receipt released');return r;
  }
  const r=await fetch(new URL(url,base),options);calls.push({url,method:options.method||'GET',body:options.body&&JSON.parse(options.body)});
  if(raceArmed&&url===`/api/internal/instances/${raceIid}/runs/${raceRid}`&&options.method!== 'POST'){
   const actual=await r.clone().json();if(actual.status==='SUCCEEDED'){
    raceArmed=false;heldPollRun=true;raceEvent('normal poll terminal receipt held');await new Promise(resolve=>releasePollRun=resolve);raceEvent('poll receipt released');
   }
  }
  if(refreshStarted&&url===`/api/apps/${raceApp}`){refreshStarted=false;holdPollInstance=true;raceEvent('manual refresh released pending poll');releasePollRun();}
if(hold&&url.endsWith('/extraction-options')){hold=false;await new Promise(resolve=>releaseHeld=resolve);}if(drop&&options.method==='POST'&&url.endsWith('/extract')){drop=false;assert.equal(r.status,201);lostBody=JSON.parse(options.body);lostApp=(await r.clone().json()).id;throw Error('Injected delivery loss after actual accepted generation');}return r;};
 for(const file of ['app.js','internal.js'])vm.runInContext(fs.readFileSync('src/sim2act/web/'+file,'utf8'),dom.getInternalVMContext());
 $('token').value='synthetic-agent-ui-A';$('connect').click();await wait(()=>$('login').hidden);
}
async function action(name,args=[]){return (await execAsync(python,['scripts/agent-ui/fixture.py','--root',root,'--action',name,...args],{cwd:process.cwd(),env:{...process.env,PYTHONPATH:'src'}})).stdout.trim();}
async function project(pid){$('project-select').value=pid;await $('project-select').onchange();w.eval('selectWorkspace("apps")');}
async function open(id){assert.ok(await w.eval(`showApp(${JSON.stringify(id)})`));}
function select(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('change'));}
function fill(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('input'));}
async function instance(column){select('app-column',column);await $('internal-prepare').onclick();check('sample independently verified before explicit acknowledgement',$('internal-approval-detail').textContent.includes('"status": "PASS"')&&$('internal-commit').disabled);$('internal-approval-ack').checked=true;$('internal-approval-ack').onchange();await $('internal-commit').onclick();const release=w.eval('engineering.releases.at(-1).id');const b=[...$('internal-releases').querySelectorAll('button')].find(b=>b.parentElement.textContent.includes(release));b.click();await wait(()=>w.eval('engineering.instance && !engineering.busy'));return w.eval('engineering.instance.id');}
async function run(column){
 const app=w.eval('engineering.app'),iid=w.eval('engineering.instance?.id');
 await wait(()=>w.eval(`engineering?.app===${JSON.stringify(app)} && engineering.instance?.id===${JSON.stringify(iid)} && !engineering.busy`)&&!$('internal-run-form').hidden);
 select('internal-column',column);await $('internal-run-form').onsubmit({preventDefault(){}});
 await wait(()=>w.eval(`engineering?.app===${JSON.stringify(app)} && engineering.instance?.id===${JSON.stringify(iid)} && engineering.run?.id && !engineering.busy`));
 const id=w.eval('engineering.run.id');
 if(injectPollRace&&column==='quantity'){raceIid=iid;raceRid=id;raceApp=app;raceArmed=true;raceEvent('await normal poll after real worker');}
 await action('worker');
 if(injectPollRace&&column==='quantity'){await wait(()=>heldPollRun);refreshStarted=true;raceEvent('manual refresh while poll receipt pending');}
 await $('internal-refresh').onclick();await w.eval(`showInternalRun(${JSON.stringify(id)})`);
 if(injectPollRace&&column==='quantity'){
  raceEvent('manual read returned');pollRace.observedNull=w.eval('engineering.run===null && engineering.instance===null');
  check('injected normal poll/refresh order actually reaches both null selections',pollRace.observedNull);
  await wait(()=>!!releasePollInstance);holdPollInstance=false;releasePollInstance();
 }
 // A completed handler can coexist with an already in-flight poll's instance read.
 // Read only the exact app/instance/run after that authoritative readback finishes.
 await wait(()=>w.eval(`engineering?.app===${JSON.stringify(app)} && engineering.instance?.id===${JSON.stringify(iid)} && engineering.run?.id===${JSON.stringify(id)} && !engineering.busy && ['SUCCEEDED','FAILED','CANCELLED'].includes(engineering.run.status)`)&&!$('internal-run-form').hidden);
 if(injectPollRace&&column==='quantity'){pollRace.recovered=true;raceEvent('exact selections recovered before final result read');check('precise wait recovers original instance/run after injected latency',pollRace.recovered);}
 return w.eval('({id:engineering.run.id,instance:engineering.instance.id,status:engineering.run.status,result:engineering.run.result,resultVersion:engineering.run.result_version})');
}

async function sourceView(source){await open(info.registered_source_app);await w.eval(`showInternalInstance(${JSON.stringify(source.instance)})`);await w.eval(`showInternalRun(${JSON.stringify(source.id)})`);}
async function options(){await $('registered-extraction-open').onclick();}
async function target(name){select('registered-extraction-target',info.registered_target_app);fill('registered-extraction-name',name);}
async function extract(name){await options();await target(name);await $('registered-extraction-form').onsubmit({preventDefault(){}});return w.eval('activeApp');}
async function raw(url,method='GET',body,auth='synthetic-agent-ui-A'){const r=await fetch(base+url,{method,headers:{Authorization:'Bearer '+auth,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,data:await r.json()};}
(async()=>{
 try{
  await create();await project(info.project);const before=JSON.parse(await action('generation-counts'));await open(info.registered_source_app);await instance('amount');const source=await run('amount');
  check('source task actually reaches SUCCEEDED through real HTTP and cold worker',source.status==='SUCCEEDED'&&source.result.sum==='3');
  await options();check('proof and target scopes come from service',$('registered-extraction-proof').textContent.includes('completed_registered_csv_apprun.v1'));await target('真实成功任务的新资料汇总');
  drop=true;await $('registered-extraction-form').onsubmit({preventDefault(){}});check('lost real acceptance exposes manual retry',!$('registered-extraction-retry').hidden);
  fill('registered-extraction-name','different input');check('edited body cannot reuse prior pending key',$('registered-extraction-retry').hidden);fill('registered-extraction-name',lostBody.name);await $('registered-extraction-retry').onclick();
  const submits=calls.filter(c=>c.method==='POST'&&c.url.endsWith('/extract'));check('manual retry preserves original accepted body/key',JSON.stringify(submits.at(-2).body)===JSON.stringify(submits.at(-1).body)&&w.eval('activeApp')===lostApp);
  const generated=lostApp;check('generated draft exposes genuine Run origin and NOT_RUN',$('app-origin').textContent.includes(source.id)&&$('app-origin').textContent.includes('NOT_RUN'));await instance('quantity');const fresh=await run('quantity');
  check('fresh column cold Run writes new result15 rather than source3',fresh.status==='SUCCEEDED'&&fresh.result.sum==='15'&&fresh.id!==source.id&&fresh.resultVersion===1);check('new material hash differs from source',fresh.result.source_hash!==source.result.source_hash);
  const after=JSON.parse(await action('generation-counts'));check('normal generation retains complete existing authority',before.grant_fingerprint===after.grant_fingerprint&&before.principal_fingerprint===after.principal_fingerprint);
  const metadata={source:{app:info.registered_source_app,...source},generated:{app:generated,...fresh}};
  dom.window.close();await create();await project(info.project);await open(generated);await w.eval(`showInternalInstance(${JSON.stringify(fresh.instance)})`);check('cold page reopens genuine persisted new result',$('internal-data').textContent.includes('15'));
  check('other identity cannot access proof',(await raw(`/api/internal/instances/${source.instance}/runs/${source.id}/extraction-options`,'GET',null,'synthetic-agent-ui-B')).status===403);
  const foreign=(await raw('/api/apps/'+info.empty_target_source_app)).data;check('cross-project target extraction denied',(await raw(`/api/internal/instances/${source.instance}/runs/${source.id}/extract`,'POST',{...lostBody,target_app_id:foreign.id,expected_target_draft_fingerprint:foreign.fingerprint,request_key:'cross-project-negative'})).status===403);
  for(const mode of ['app','project','identity']){
   await project(info.project);await sourceView(source);hold=true;const pending=$('registered-extraction-open').onclick();await wait(()=>!!releaseHeld);
   if(mode==='app')await open(info.registered_target_app);if(mode==='project')await project(info.other_project);if(mode==='identity')w.eval('token="synthetic-agent-ui-B";clearApp()');
   releaseHeld();releaseHeld=null;await pending;check(`late ${mode} options cannot render source proof`,$('registered-extraction-proof').textContent===''&&$('registered-extraction-form').hidden);if(mode==='identity')w.eval('token="synthetic-agent-ui-A"');
  }
  await project(info.project);await sourceView(source);const corrupted=await extract('second candidate explicit tamper');check('second negative draft also generated via real POST',corrupted!==generated&&corrupted!==info.registered_source_app);await action('generation-corrupt',['--app-id',corrupted]);await $('internal-refresh').onclick();check('rehashed candidate mismatch clears protected content',$('app-manifest').textContent==='');
  await open(generated);await action('generation-revoke');await $('internal-refresh').onclick();check('target current revoke rejects healthy generated app',$('app-manifest').textContent===''&&$('internal-run-form').hidden);
  await sourceView(source);await options();check('revoked target causes needs-input rather than new Grant',$('registered-extraction-form').hidden&&$('registered-extraction-status').textContent.includes('Existing authorized app'));await action('generation-source-revoke');await $('internal-refresh').onclick();check('source revoke clears extraction state',$('registered-extraction').hidden&&$('app-manifest').textContent==='');
  await project(info.empty_target_project);await open(info.empty_target_source_app);await instance('amount');const empty=await run('amount');await options();check('third project actual successful task has explicit empty-target outcome',(await raw(`/api/internal/instances/${empty.instance}/runs/${empty.id}/extraction-options`)).data.error.code==='NEEDS_INPUT'&&$('registered-extraction-form').hidden);
  console.log(JSON.stringify({driver:'direct actual HTTP-backed jsdom UI events',browser:'NOT_RUN',visual:'NOT_RUN',result:{status:'PASS',checks,metadata,pollRace}}));
 }finally{dom?.window.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
