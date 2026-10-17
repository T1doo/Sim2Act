'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],checks=[],assets=[];let serial=0,dom,w,$,drop=false,dropAdoption=false,hold=null,release=null,directoryAudit=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(fn,label,timeout=15000)=>{const end=Date.now()+timeout;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el),'visible '+(el?.id||el?.textContent));assert(!el.matches(':disabled'),'enabled '+el.id);
 const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=suffix=>requests.filter(r=>r.method==='POST'&&r.path.endsWith(suffix));
async function nav(tab){await action(w.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));}
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function open(){await nav('apps');await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance).querySelector('button'));}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={path,method:options.method||'GET',body:options.body?JSON.parse(options.body):undefined};requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}
  if(drop&&request.method==='POST'&&path.endsWith('/csv-goal-revisions/checks')){drop=false;assert.equal(r.status,202);request.delivery='ACTUAL_202_LOST';throw Error('synthetic lost CHECK response');}
  if(dropAdoption&&request.method==='POST'&&path.includes('/switch-approvals/')&&path.endsWith('/commit')){dropAdoption=false;assert.equal(r.status,200);request.delivery='ACTUAL_CAS_200_LOST';throw Error('synthetic lost original CAS response');}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);await open();
 check(visible($('csv-goal-edit'))&&$('use-info').textContent.includes('CSV'),'saved CSV instance exposes Goal revision entry');
 check(posts('/previews').length===0&&posts('/checks').length===0,'opening instance only reads and never submits revision');
}
async function revise(){
 await action('csv-goal-edit');check(visible($('goal-card-goal'))&&$('goal-card-status').textContent.includes('v1'),'original same Goal card opens for explicit editing');
 $('goal-card-title').value='数量目标 v2';$('goal-card-goal').value='明确汇总 quantity，保留原材料与历史';await action($('goal-card-save'));
 check($('goal-card-status').textContent.includes('v2'),'explicit save creates same card v2');await open();await action('csv-goal-baseline');
 check($('csv-goal-revision-proof').textContent.includes('明确汇总 quantity'),'authorized exact new Goal is visible before mapping');
 $('csv-goal-from').value='amount';$('csv-goal-to').value='quantity';await action('csv-goal-to','change');
 const button=$('csv-goal-preview'),sending=action(button);await button.onclick(new w.Event('click'));await sending;
 check(posts('/csv-goal-revisions/previews').length===1&&$('csv-goal-check').disabled,'one explicit revision POST and CHECK awaits separate consent');
}
async function confirmationReturn(stage,ack,submit){
 const suffix={preview:'/previews',release:'/version-approvals',adoption:'/adoption-approvals'}[stage];
 const hint=posts('/csv-goal-revisions'+suffix).at(-1).response,preview=posts('/csv-goal-revisions/previews').at(-1).response;
 const frozen=stage==='adoption'?requests.filter(x=>x.method==='GET'&&x.path.endsWith(suffix+'/'+preview.request_key)&&x.status===200).at(-1).response:hint;
 assert.equal(frozen.id,hint.id);assert.equal(frozen.fingerprint,hint.fingerprint);
 await action(ack);check(!$(submit).disabled,stage+' original explicit consent enables exact next action');
 const count=requests.filter(x=>x.method==='POST').length,before=$('csv-goal-revision');
 await nav('resources');await nav('apps');
 await wait(()=>visible($('csv-goal-revision'))&&$('csv-goal-revision')!==before&&!$(ack).disabled,stage+' confirmation return is ready');
 check(requests.filter(x=>x.method==='POST').length===count,stage+' navigation and revalidation never POST');
 const shown=JSON.parse($('csv-goal-revision-proof').textContent);
 assert.deepEqual(shown[stage==='preview'?'preview':stage==='release'?'release_approval':'adoption_approval'],frozen);
 checks.push(stage+' return displays the complete exact server-frozen confirmation payload');
 assert.deepEqual(shown.preview,preview);
 check(shown.context.instance_id===info.instance&&shown.context.app_id===info.app&&shown.context.project_id===info.project,stage+' proof retains current instance/app/project ownership');
 check($('csv-goal-from').value==='amount'&&$('csv-goal-to').value==='quantity'&&$('csv-goal-from').disabled&&$('csv-goal-to').disabled,stage+' frozen amount to quantity mapping is restored and locked');
 check(!$(ack).checked&&$(submit).disabled,stage+' navigation clears prior consent and requires a fresh visible confirmation');
 const key=posts('/csv-goal-revisions/previews').at(-1).body.request_key;
 check(requests.some(x=>x.method==='GET'&&x.path.endsWith('/csv-goal-revisions/context'))&&requests.some(x=>x.method==='GET'&&x.path.endsWith('/previews/'+key)),stage+' return rereads current context and original preview');
 if(stage==='release')check(requests.some(x=>x.method==='GET'&&x.path===`/api/internal/approvals/${frozen.id}`),stage+' return checks live approval rather than only historical acceptance');
 if(stage==='adoption')check(requests.some(x=>x.method==='GET'&&x.path.endsWith('/adoption-approvals/'+key)),stage+' return rereads exact CAS preflight');
}
async function checkRun(){
 await action('csv-goal-check-ack');if(info.case==='lost')drop=true;
 if(['deliver','lost'].includes(info.case))hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`;
 const b=$('csv-goal-check'),sending=action(b);await b.onclick(new w.Event('click'));
 if(['deliver','lost'].includes(info.case)){
  await wait(()=>release,'actual CHECK acceptance held');const before=$('csv-goal-revision');
  if(info.case==='deliver'){
   await w.readApplicationUse(w.eval('applicationUse'));check($('csv-goal-revision')===before&&$('csv-goal-check').disabled,'same-view polling preserves in-flight revision controller');
  }else{
   await nav('resources');await nav('apps');await wait(()=>visible($('csv-goal-revision')),'workspace return rebuilt current controller');
   check($('csv-goal-revision')!==before&&$('csv-goal-check').disabled,'same instance new workspace controller keeps original sending intent locked');
  }
  const done=release;release=null;done();
 }
 await sending;
 if(info.case==='lost'){
  check(visible($('csv-goal-recover'))&&$('csv-goal-check').disabled,'lost actual202 freezes original CHECK intent');
  await action('csv-goal-recover');
  check(posts('/csv-goal-revisions/checks').length===1&&requests.some(x=>x.method==='GET'&&x.path.endsWith('/checks/'+posts('/csv-goal-revisions/checks')[0].body.request_key)),'navigation return recovers original CHECK by GET only');
 }
 check(posts('/csv-goal-revisions/checks').length===(['rejected','return-stale'].includes(info.case)?2:1),'double click creates exactly one CHECK per explicit accepted intent');
 const accepted=posts('/csv-goal-revisions/checks').find(x=>x.status===202),jid=accepted.response.run_id;
 await rpc({command:'worker',run:jid});await action('csv-goal-outcome');
 check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"')&&$('csv-goal-revision-status').textContent.includes('人工 PENDING'),'actual original Worker check passes separately from human acceptance');
 if(info.case==='deliver'){
  // Refresh through visible project selection after CHECK really exists. The
  // old list predates CHECK and cannot prove its business-directory exclusion.
  await nav('projects');await project(info.other);await project(info.project);await nav('apps');
  const fresh=requests.filter(x=>x.method==='GET'&&x.path===`/api/internal/apps/${info.app}/instances`&&x.status===200).at(-1),checkId=accepted.response.check_instance_id;
  const serverCheck=fresh.response.items.find(x=>x.id===checkId),visibleIds=[...$('use-list').children].map(x=>x.dataset.instanceId).filter(Boolean);
  directoryAudit={check_instance_id:checkId,server_items:fresh.response.items,visible_instance_ids:visibleIds};
  check(serverCheck?.switch_policy?.roles?.includes('csv_goal_check'),'fresh actual server list includes isolated CHECK with role pin');
  check(visibleIds.includes(info.instance)&&visibleIds.includes(info.instance2)&&!visibleIds.includes(checkId),'fresh business directory includes both business instances and filters actual CHECK');
  await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance).querySelector('button'));
  check(w.eval('applicationUse.id')===info.instance&&visible($('csv-goal-version')),'explicit original business selection restores same checked intent before release approval');
 }
}
(async()=>{try{
 await boot();await revise();
 if(info.case==='return-preview')await confirmationReturn('preview','csv-goal-check-ack','csv-goal-check');
 if(info.case==='return-stale'){
  const key=posts('/csv-goal-revisions/previews')[0].body.request_key;
  await nav('resources');await rpc({command:'drift'});const count=requests.filter(x=>x.method==='POST').length;
  await nav('apps');await wait(()=>visible($('csv-goal-revision'))&&!$('csv-goal-check-ack').disabled,'stale return finishes current baseline validation');
  const shown=JSON.parse($('csv-goal-revision-proof').textContent);
  check(shown.review_status==='FROZEN_BASELINE_RESULTS_CHANGED'&&shown.current_context.data_version>shown.context.data_version&&shown.preview.request_key===key&&$('csv-goal-check').disabled,'changed baseline displays exact frozen preview and current result version without retaining consent');
  check($('csv-goal-version').disabled&&$('csv-goal-release').disabled&&$('csv-goal-adopt').disabled,'stale read never enables Release or CAS');
  check(requests.filter(x=>x.method==='POST').length===count&&!visible($('csv-goal-reset')),'stale read does not create a replacement key or POST');
  check(w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).key')===key,'stale proof retains exact original accepted preview key');
  await action('csv-goal-check-ack');await action('csv-goal-check');
  check(posts('/csv-goal-revisions/checks')[0].status===409&&posts('/csv-goal-revisions/checks')[0].body.request_key===key,'explicit original CHECK obtains server-proved NOT_ACCEPTED for stale baseline');
  await open();await action('csv-goal-reset');await action('csv-goal-baseline');$('csv-goal-from').value='amount';$('csv-goal-to').value='quantity';await action('csv-goal-to','change');await action('csv-goal-preview');
  check(posts('/csv-goal-revisions/previews').at(-1).body.request_key!==key,'only proved rejection enables explicit fresh proposal');
 }
 if(info.case==='navigation'){
  await action('csv-goal-check-ack');hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`;const sending=action('csv-goal-check');await wait(()=>release,'accepted CHECK held');
  await nav('projects');await project(info.other);const done=release;release=null;done();await sending;
  check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late CHECK cannot populate another project');
  const key=posts('/csv-goal-revisions/checks')[0].body.request_key;
  check(!requests.some(x=>x.method==='GET'&&x.path.endsWith('/checks/'+key)),'late accepted callback sends no original-project GET');
  await project(info.project);await open();await action('csv-goal-recover');check(posts('/csv-goal-revisions/checks').length===1,'same-owner return recovers the one accepted CHECK');
  await action('csv-goal-outcome');
  // A second instance has its own UI selection fence; delayed baseline cannot
  // replace its visible source or install an old approval.
  hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks/${key}`;const reading=action('csv-goal-outcome');await wait(()=>release,'outcome held');
  await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance2).querySelector('button'));const doneRead=release;release=null;doneRead();await reading;
  check(w.eval('applicationUse.id')===info.instance2&&!$('csv-goal-revision-proof').textContent.includes(posts('/csv-goal-revisions/checks')[0].response.run_id),'late outcome cannot replace another selected instance');
  hold=`/api/internal/instances/${info.instance2}/csv-goal-revisions/context`;const baseline=action('csv-goal-baseline');await wait(()=>release,'other instance baseline held');
  await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const finish=release;release=null;finish();await baseline;
  check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late CHECK read cannot populate another account');
 }else{
  if(info.case==='rejected'){
   await rpc({command:'drift'});await action('csv-goal-check-ack');await action('csv-goal-check');
   check(posts('/csv-goal-revisions/checks').length===1&&posts('/csv-goal-revisions/checks')[0].status===409,'intervening real Run rejects CHECK before acceptance');
   await open();check(visible($('csv-goal-reset'))&&!visible($('csv-goal-recover')),'proved absent rolled-back request exposes explicit fresh preparation');
   await action('csv-goal-reset');await action('csv-goal-baseline');$('csv-goal-from').value='amount';$('csv-goal-to').value='quantity';await action('csv-goal-to','change');await action('csv-goal-preview');
   check(posts('/csv-goal-revisions/previews').length===2&&posts('/csv-goal-revisions/previews')[0].body.request_key!==posts('/csv-goal-revisions/previews')[1].body.request_key,'explicit fresh proposal uses a new key while old rejected key remains recorded');
  }
  await checkRun();await action('csv-goal-version');check($('csv-goal-release').disabled&&!$('csv-goal-release-ack').checked,'new Release requires fresh explicit confirmation');
  if(info.case==='return-release')await confirmationReturn('release','csv-goal-release-ack','csv-goal-release');
  await action('csv-goal-release-ack');await action('csv-goal-release');check($('csv-goal-adopt').disabled&&posts('/switch-approvals').length===0,'saving Release has not adopted business instance');
  await action('csv-goal-adopt-prepare');check($('csv-goal-revision-proof').textContent.includes(info.instance)&&$('csv-goal-adopt').disabled,'CAS adoption proof names original instance and awaits consent');
  if(info.case==='return-adoption')await confirmationReturn('adoption','csv-goal-adopt-ack','csv-goal-adopt');
  await action('csv-goal-adopt-ack');
  if(info.case==='lost-adoption'){
   const a=posts('/csv-goal-revisions/adoption-approvals').at(-1).response;
   hold=`/api/internal/instances/${info.instance}/switch-approvals/${a.id}/commit`;dropAdoption=true;
   const sending=action('csv-goal-adopt');await wait(()=>release,'actual original CAS200 held',45000);
   await nav('resources');await nav('apps');await wait(()=>visible($('csv-goal-revision')),'adopted instance return retains unresolved original CAS');
   const done=release;release=null;done();await sending;
   await wait(()=>visible($('csv-goal-recover'))&&!$('csv-goal-recover').disabled,'unknown original CAS exposes GET-only recovery');
   await action('csv-goal-recover');
   check(requests.filter(x=>x.method==='POST'&&x.path.includes('/switch-approvals/')&&x.path.endsWith('/commit')).length===1,'lost actual CAS recovers one exact approval from original instance history without second POST');
   check(w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).steps.adoptCommit.state')==='accepted','original CAS UNKNOWN resolves to its exact accepted history');
  }else await action('csv-goal-adopt');
  check([...$('use-column').options].map(x=>x.value).join() === 'quantity'&&$('use-info').textContent.includes('Goal v2'),'same instance now exposes only verified new Release column and Goal');
  $('use-csv-review-optin').checked=true;await action('use-submit');const run=posts('/runs').at(-1).response.run_id;
  await rpc({command:'worker',run});await action('use-refresh');
  check($('use-output').textContent.includes('合计 5')&&$('use-output').textContent.includes(run),'same new Run shows actual different typed result');
  await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING')&&$('csv-owner-body').textContent.includes('5'),'new Run human acceptance opens PENDING on exact new result');
  const record=await rpc({command:'proof',run});check(record.status===200,'cold server proof verifies same app runtime, original provenance, old result and Goal v2');
 }
 await wait(()=>requests.every(x=>Number.isInteger(x.status)),'all actual API replies settle');
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',checks,requests,assets,directoryAudit},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(0);
}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,requests,assets,directoryAudit},null,2));if(dom)dom.window.close();process.stderr.write(error.stack+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(1);}})();
