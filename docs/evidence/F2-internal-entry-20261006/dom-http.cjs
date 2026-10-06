// Actual HTTP + Node/jsdom integration. NOT Chromium, render/visual/mobile acceptance.
const {JSDOM,VirtualConsole}=require('jsdom');
const fs=require('node:fs');
const {execFileSync}=require('node:child_process');
const results=[];
const check=(name,truth)=>{if(!truth)throw Error(name);results.push({name,status:'PASS'});};
async function wait(fn){for(let i=0;i<160;i++){if(fn())return;await new Promise(r=>setTimeout(r,25));}throw Error('DOM wait timeout');}
async function page(){
 const errors=[];const vc=new VirtualConsole();vc.on('jsdomError',e=>errors.push(e.message));
 const dom=await JSDOM.fromURL('http://127.0.0.1:8073',{resources:'usable',runScripts:'dangerously',virtualConsole:vc,beforeParse(w){w.fetch=(url,opts)=>fetch(new URL(url,'http://127.0.0.1:8073'),opts);w.crypto.randomUUID=require('node:crypto').randomUUID;}});
 const w=dom.window,d=w.document;await wait(()=>d.getElementById('connect').onclick && d.getElementById('internal-prepare').onclick);
 d.getElementById('token').value='synthetic-e19-ui';d.getElementById('connect').click();await wait(()=>d.getElementById('app-list').children.length);
 return {dom,w,d,errors};
}
(async()=>{
 const {dom,w,d,errors}=await page();const $=id=>d.getElementById(id),realFetch=w.fetch;
 const list=await w.eval('api("/api/apps")');const app=list.items.find(a=>a.project_id===$('project-select').value);
 await w.eval(`showApp('${app.id}')`);w.eval('selectWorkspace("apps")');
 check('internal entry visibly marked formal deployment disabled',!$('internal-panel').hidden && $('internal-panel').textContent.includes('正式发布与部署仍关闭'));
 let prepares=0,prepared=false,releasePrepare;const prepareGate=new Promise(r=>releasePrepare=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/release-approvals')){prepares++;prepared=true;await prepareGate;}return response;};
 $('internal-prepare').click();await wait(()=>prepared);$('internal-prepare').click();
 check('duplicate prepare blocked while receipt pending',prepares===1 && $('internal-prepare').disabled);
 releasePrepare();await wait(()=>!$('internal-approval').hidden);w.fetch=realFetch;
 check('exact snapshot/check evidence shown before confirmation',$('internal-approval-detail').textContent.includes('csv.exact_integer_sum.v1') && $('internal-approval-label').textContent.includes('到期'));
 check('unacknowledged approval cannot commit',$('internal-commit').disabled);
 $('internal-approval-ack').checked=true;$('internal-approval-ack').dispatchEvent(new w.Event('change'));$('internal-commit').click();
 await wait(()=>$('internal-releases').querySelector('button') && !w.eval('engineering.busy'));
 check('approved immutable internal release history returned',$('internal-releases').textContent.includes('正式发布关闭'));
 let creates=0,createAccepted=false,releaseCreate;const createGate=new Promise(r=>releaseCreate=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/instances') && opts?.method==='POST'){creates++;createAccepted=true;await createGate;}return response;};
 $('internal-releases').querySelector('button').click();await wait(()=>createAccepted);$('internal-releases').querySelector('button').click();check('duplicate instance click blocked while busy',creates===1);
 releaseCreate();await wait(()=>w.eval('engineering.instance') && !w.eval('engineering.busy'));w.fetch=realFetch;
 const first=w.eval('engineering.instance.id');check('fresh independent instance data initially empty',$('internal-data').children.length===0);
 // Accepted POST response lost once: retain exact key, explicit retry returns cached same Run.
 let accepted,drop=true,runPosts=0;
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/runs') && opts?.method==='POST'){runPosts++;if(drop){drop=false;accepted=await response.clone().json();throw Error('synthetic accepted response delivery lost');}}return response;};
 $('internal-run-form').requestSubmit();await wait(()=>$('internal-retry').hidden===false && !w.eval('engineering.busy'));
 check('accepted receipt loss retains exact request key and explicit retry',!!accepted && $('internal-run-submit').disabled);
 $('internal-retry').click();await wait(()=>w.eval('engineering.run') && !w.eval('engineering.busy'));w.fetch=realFetch;
 check('explicit retry same accepted persistent Run once',runPosts===2 && w.eval('engineering.run.id')===accepted.run_id && $('internal-runs').children.length===1);
 $('internal-controls').querySelector('button').click();await wait(()=>$('internal-run-status').textContent.includes('PAUSED') && !w.eval('engineering.busy'));
 check('pause persisted and current control status returned',$('internal-controls').textContent.includes('继续'));
 const cancel=Array.from($('internal-controls').querySelectorAll('button')).find(b=>b.textContent.includes('取消'));
 cancel.click();await wait(()=>$('internal-run-status').textContent.includes('CANCELLED') && !w.eval('engineering.busy'));
 check('cancel accepted terminal and intent retained',$('internal-run-detail').textContent.includes('"cancel_intent": true'));
 // Another process changes the existing instance revision; actual POST must reject stale view.
 const selectedRelease=w.eval('engineering.instance.release_id'),revision=w.eval('engineering.instance.revision');
 execFileSync('/workspace/sim2act-pb-venv/bin/python',['-c',`from pathlib import Path; from sim2act.db import Store; from sim2act.config import Settings; from sim2act.contracts import Limits; from sim2act.lifecycle import prepare_switch,commit_switch; s=Store('sqlite:////tmp/sim2act-e19-ui/fixture.db',test_only=True); cfg=Settings(str(s.engine.url),Path('/tmp/sim2act-e19-ui'),mode='mock'); u=s.authenticate('synthetic-e19-ui'); limits=Limits(**{k:getattr(cfg,k) for k in Limits.model_fields}); a=prepare_switch(s,u,'${first}','${selectedRelease}',${revision},limits); commit_switch(s,u,a['id'],a['fingerprint'],limits)`],{cwd:process.cwd()});
 $('internal-run-form').requestSubmit();await wait(()=>!w.eval('engineering.busy') && !$('internal-new-intent').hidden);
 check('actual revision change rejects stale submission and retains old intent',$('internal-status').textContent.includes('VERSION_CONFLICT'));
 $('internal-new-intent').click();await wait(()=>!w.eval('engineering.busy') && $('internal-new-intent').hidden);
 check('explicit history read resolves old intent without cancelling accepted history',w.eval('engineering.instance.revision')===revision+1 && !$('internal-run-submit').disabled && $('internal-runs').textContent.includes('CANCELLED'));
 // User makes a genuinely new run. Independent worker process performs existing trusted tool.
 $('internal-run-form').requestSubmit();await wait(()=>w.eval('engineering.run?.status')==='QUEUED' && !w.eval('engineering.busy'));
 const newRun=w.eval('engineering.run.id');
 execFileSync('/workspace/sim2act-pb-venv/bin/python',['-c',`from pathlib import Path; from sim2act.db import Store; from sim2act.config import Settings; from sim2act.worker import Worker; s=Store('sqlite:////tmp/sim2act-e19-ui/fixture.db',test_only=True); cfg=Settings(str(s.engine.url),Path('/tmp/sim2act-e19-ui'),mode='mock'); Worker(s,cfg).once()`],{cwd:process.cwd()});
 await w.eval(`showInternalRun('${newRun}',engineering,engineering.instance)`);
 check('actual worker new result 40 not static UI template',$('internal-run-status').textContent.includes('40'));
 check('terminal refresh reopens instance new result version',$('internal-data').textContent.includes('结果 v1'));
 await w.eval(`showRun('${newRun}')`);
 check('project task readback labels internal no model rather than real model',$('result').textContent.includes('内部工程只读任务') && $('result').textContent.includes('0 模型请求') && !$('result').textContent.includes('书生运行记录'));
 let mainHeld=false,releaseMain;const mainGate=new Promise(r=>releaseMain=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url)===`/api/runs/${newRun}`){mainHeld=true;await mainGate;}return response;};
 const oldMain=w.eval(`showRun('${newRun}')`);await wait(()=>mainHeld);w.eval('activeRun=null');$('result').textContent='新任务选择';releaseMain();await oldMain;w.fetch=realFetch;
 check('project task late read cannot override cleared selection',$('result').textContent==='新任务选择');
 // Another instance from same frozen release, no data inheritance.
 let lateCreated=false,createdInstance,releaseLateCreate;const lateCreateGate=new Promise(r=>releaseLateCreate=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/instances') && opts?.method==='POST'){createdInstance=await response.clone().json();lateCreated=true;await lateCreateGate;}return response;};
 $('internal-releases').querySelector('button').click();await wait(()=>lateCreated);
 await w.eval(`showInternalInstance('${first}')`);releaseLateCreate();await wait(()=>!w.eval('engineering.busy'));w.fetch=realFetch;
 check('late create receipt cannot steal newer instance selection',w.eval('engineering.instance.id')===first);
 const second=createdInstance.id;await w.eval('refreshInternal()');await w.eval(`showInternalInstance('${second}')`);
 check('second instance independent result ledger',$('internal-data').children.length===0);
 await w.eval(`showInternalInstance('${first}')`);
 let listHeld=false,releaseList;const listGate=new Promise(r=>releaseList=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/releases')){listHeld=true;await listGate;}return response;};
 $('internal-refresh').click();await wait(()=>listHeld);await w.eval(`showInternalInstance('${second}')`);releaseList();await wait(()=>!w.eval('engineering.busy'));w.fetch=realFetch;
 check('late history refresh cannot reopen old instance',w.eval('engineering.instance.id')===second && !$('internal-data').children.length);
 // Same-instance stale read, then pick another before it arrives.
 let held=false,releaseRead;const readGate=new Promise(r=>releaseRead=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url)===`/api/internal/instances/${first}`){held=true;await readGate;}return response;};
 const oldRead=w.eval(`showInternalInstance('${first}')`);await wait(()=>held);
 await w.eval(`showInternalInstance('${second}')`);releaseRead();await oldRead;w.fetch=realFetch;
 check('late instance response cannot overwrite new selection',w.eval('engineering.instance.id')===second && !$('internal-data').children.length);
 // A delayed Run read is also scoped to exact instance/selection, not merely project.
 await w.eval(`showInternalInstance('${first}')`);
 let heldRun=false,releaseRun;const runGate=new Promise(r=>releaseRun=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith(`/runs/${newRun}`)){heldRun=true;await runGate;}return response;};
 const oldRun=w.eval(`showInternalRun('${newRun}')`);await wait(()=>heldRun);
 await w.eval(`showInternalInstance('${second}')`);releaseRun();await oldRun;w.fetch=realFetch;
 check('late run result cannot leak into another instance',!$('internal-run-detail').textContent && !$('internal-data').children.length && w.eval('engineering.instance.id')===second);
 // Accept a new Run, navigate away before receipt: accepted server work preserved, no late panel.
 let queueHeld=false,releaseQueue;const queueGate=new Promise(r=>releaseQueue=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/runs') && opts?.method==='POST'){queueHeld=true;await queueGate;}return response;};
 $('internal-run-form').requestSubmit();await wait(()=>queueHeld);$('internal-back').click();releaseQueue();await wait(()=>w.eval('engineering')===null);w.fetch=realFetch;
 check('return discards selection but not accepted backend task',$('internal-panel').hidden);
 await w.eval(`showApp('${app.id}')`);await w.eval(`showInternalInstance('${second}')`);
 check('reopen after accepted return finds persistent queued history',$('internal-runs').textContent.includes('QUEUED'));
 // Release prepare response for prior project cannot populate current project panel.
 let latePrepared=false,releaseLate;const lateGate=new Promise(r=>releaseLate=r);
 w.fetch=async(url,opts)=>{const response=await realFetch(url,opts);if(String(url).endsWith('/release-approvals')){latePrepared=true;await lateGate;}return response;};
 $('internal-prepare').click();await wait(()=>latePrepared);
 const other=list.items.find(a=>a.project_id!==app.project_id);$('project-select').value=other.project_id;await w.eval(`showApp('${other.id}','${other.project_id}')`);releaseLate();await new Promise(r=>setTimeout(r,60));w.fetch=realFetch;
 check('cross-project late approval cannot overwrite new app',w.eval('engineering.app')===other.id && $('internal-approval').hidden && !$('internal-approval-detail').textContent);
 // Authenticated new page reads server history, not original JS memory.
 dom.window.close();const cold=await page();const coldD=cold.d;const coldList=await cold.w.eval('api("/api/apps")');coldD.getElementById('project-select').value=app.project_id;
 await cold.w.eval(`showApp('${app.id}','${app.project_id}')`);await cold.w.eval(`showInternalInstance('${first}')`);
 check('cold page independent result readback',coldD.getElementById('internal-data').textContent.includes('40') && coldD.getElementById('internal-runs').textContent.includes('CANCELLED'));
 // Revoke current app read grant: content GET is refused, minimal owner stop remains usable.
 await cold.w.eval(`showInternalInstance('${second}')`);
 const queued=cold.w.eval('engineering.instance.runs.find(r=>r.status==="QUEUED").id');
 await cold.w.eval(`showInternalRun('${queued}')`);
 const grantList=await cold.w.eval(`api('/api/projects/${app.project_id}/grants')`);
 const grant=grantList.find(g=>g.principal_id.startsWith('appruntime_') && g.tool_ref==='resource.read' && !g.revoked);
 await cold.w.eval(`api('/api/grants/${grant.id}/revoke','POST',{command:'revoke',version:${grant.revision}})`);
 await cold.w.eval(`showInternalRun('${queued}')`);
 check('revocation clears protected content but shows only stop metadata',coldD.getElementById('internal-data').children.length===0 && coldD.getElementById('internal-run-form').hidden && coldD.getElementById('internal-run-detail').textContent.includes('"content_access": false') && !coldD.getElementById('internal-run-detail').textContent.includes('"result"'));
 const stop=Array.from(coldD.getElementById('internal-controls').querySelectorAll('button')).find(b=>b.textContent.includes('取消'));stop.click();
 await wait(()=>coldD.getElementById('internal-run-status').textContent.includes('CANCELLED') && !cold.w.eval('engineering.busy'));
 check('revoked owner can cancel accepted run without restored grant',coldD.getElementById('internal-run-detail').textContent.includes('"cancel_intent": true'));
 check('no script/runtime errors',errors.length===0 && cold.errors.length===0);
 cold.dom.window.close();
 fs.writeFileSync('docs/evidence/F2-internal-entry-20261006/dom-results.json',JSON.stringify({kind:'Node/jsdom + real authenticated HTTP + separate worker process, NOT browser visual verification',checks:results.length,results},null,2)+'\n');
 console.log(results.length+' DOM/HTTP checks PASS');
})().catch(e=>{console.error(e);process.exit(1);});
