'use strict';
// Product page + actual ASGI HTTP via IPC. JSDOM is not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const same=require('node:util').isDeepStrictEqual;
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[],mutations=[];
let unknownHint=false;
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null;
const httpReplies=[],heldWaits=[];
const downloadBlobs=[],downloadAnchors=[];
let downloadMutation=null,anchorFailure=false;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
// Opening includes several real authorization reads. Keep the 12s no-progress
// limit while bounding the complete chain at 60s; only actual HTTP replies renew it.
const waitHeld=async label=>{
 const start=Date.now(),initial=httpReplies.length;let last=start,seen=initial;
 const record=outcome=>heldWaits.push({label,outcome,elapsed_ms:Date.now()-start,http_reply_offsets_ms:httpReplies.slice(initial).map(at=>at-start),idle_limit_ms:12000,total_limit_ms:60000});
 while(true){
  if(Date.now()-start>=60000){record('total limit');throw Error('bounded wait: '+label+' (60s total)');}
  for(;seen<httpReplies.length;seen++){
   const at=httpReplies[seen];
   if(at-last>=12000){record('HTTP reply gap');throw Error('bounded wait: '+label+' (12s HTTP reply gap)');}
   last=at;
  }
  if(Date.now()-last>=12000){record('no HTTP progress');throw Error('bounded wait: '+label+' (12s without HTTP progress)');}
  if(releaseRead){record('exact gate reached');return;}
  await new Promise(r=>setTimeout(r,5));
 }
};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=()=>requests.filter(r=>r.method==='POST');
const entry=()=>$('use-list').querySelector(`[data-use-family="CSV_DAG"][data-instance-id="${info.instance}"] button`);
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 if(info.download){
  w.Blob=Blob;
  w.URL.createObjectURL=blob=>{const url='blob:dag-test-'+downloadBlobs.length;downloadBlobs.push({url,blob,revoked:false});return url;};
  w.URL.revokeObjectURL=url=>{const value=downloadBlobs.find(b=>b.url===url);assert(value);value.revoked=true;};
  w.HTMLAnchorElement.prototype.click=function(){if(anchorFailure)throw Error('synthetic anchor failure');downloadAnchors.push({url:this.href,filename:this.download});};
 }
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);httpReplies.push(Date.now());
   if(hold&&path===hold.path&&--hold.remaining===0){const gate=hold;hold=null;await new Promise(resolve=>{releaseRead=resolve;});if(gate.error){mutations.push({path,kind:'synthetic late response403',actual_status:r.status});return new Response(JSON.stringify({error:{code:'PERMISSION_DENIED',message:'synthetic delayed error'}}),{status:403,headers:{'Content-Type':'application/json'}});}}
   if(downloadMutation&&/^\/api\/internal\/instances\/[^/]+\/runs\/[^/]+$/.test(path)){
    const action=downloadMutation;downloadMutation=null;const value=JSON.parse(r.text);action.change(value);
    mutations.push({path,kind:action.label,actual_status:r.status,returned_response:value});
    return new Response(JSON.stringify(value),{status:r.status,headers:{'Content-Type':'application/json'}});
   }
   if(unknownHint&&path.endsWith('/dag-releases')){const modified=JSON.parse(r.text);for(const rel of modified.items)rel.snapshot.execution_source.version='toString';mutations.push({path,kind:'synthetic discovery version hint',actual_status:r.status});return new Response(JSON.stringify(modified),{status:r.status,headers:{'Content-Type':'application/json'}});}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');await nav('apps');
 await wait(()=>!!entry(),'DAG directory entry');
}
async function open(){await click(entry());
 check(w.eval('csvDagContext?.savedUse&&csvDagContext.reuse.instance?.id')===info.instance&&visible($('dag-reuse-panel')),'directory opens original DAG controller and exact instance');
 check(!w.eval('applicationUse')&&$('use-form').hidden&&$('internal-panel').hidden,'DAG does not expose single-step CSV submission');
}
async function readonly(){assert.equal((await rpc({command:'readonly'})).status,200);}
async function use(){
 check(posts().length===0,'directory discovery makes no POST');
 check($('use-list').querySelectorAll('[data-use-family="CSV_DAG"]').length===2&&!!$('use-list').querySelector(`[data-use-family="CSV"][data-instance-id="${info.plain_instance}"]`),'same draft distinguishes two DAG instances from ordinary CSV');
 const description=entry().parentElement.textContent;
 check(description.includes('CSV DAG')&&description.includes('读取 → 求和')&&description.includes('0 模型请求')&&description.includes('人工 PENDING'),'directory shows exact supported flow and limits');
 await readonly();await open();check(posts().length===0,'opening exact DAG instance is GET-only');await readonly();
 const runs=[];
 for(const [column,total,version]of [['quantity','15',1],['amount','30',2]]){
  $('dag-reuse-column').value=column;$('dag-reuse-column').dispatchEvent(new w.Event('change',{bubbles:true}));check($('dag-reuse-run').disabled,'new column requires separate confirmation');
  $('dag-reuse-run-confirm').checked=true;$('dag-reuse-run-confirm').dispatchEvent(new w.Event('change',{bubbles:true}));
  const n=posts().length,work=click('dag-reuse-run');$('dag-reuse-run').click();await work;
  check(posts().length===n+1&&posts().at(-1).path===`/api/internal/instances/${info.instance}/runs`&&posts().at(-1).body.input.column===column,'explicit double click sends one exact original DAG request');
  let detail=JSON.parse($('dag-reuse-proof').textContent).instance;const queued=detail.runs.find(r=>r.status==='QUEUED');assert(queued);
  check(queued.output===null&&queued.result_version===null&&detail.data_version===version-1,'queued current Run does not copy historical result');runs.push(queued.run_id);
  assert.equal((await rpc({command:'worker'})).status,200);await click('dag-reuse-read');detail=JSON.parse($('dag-reuse-proof').textContent).instance;
  const run=detail.runs.find(r=>r.run_id===queued.run_id);check(run.status==='SUCCEEDED'&&run.result_version===version&&run.output.sum===total&&run.output.column===column,'cold Worker saves exact new-column result version '+version);
  check(run.proof.steps.length===info.nodes&&run.proof.steps.every(s=>s.status==='VERIFIED')&&run.proof.business_writes===1&&run.proof.model_requests===0,'all original operation receipts verified with one typed write and zero models');
  if(info.nodes===3)check(run.proof.result.output_by_step.formatted.text===`列 ${column}；行数 2；合计 ${total}`&&!Object.hasOwn(run.output,'text'),'report text remains in full Run proof and typed aggregate stays five fields');
  check($('dag-reuse-results').textContent.includes('结果版本 '+version)&&$('dag-reuse-results').textContent.includes('合计 '+total),'existing result history visibly reflects saved result');await readonly();
 }
 check(runs[0]!==runs[1]&&runs.every(r=>r!==info.source_run),'two new Runs are distinct from each other and source');
 const n=posts().length;await boot();await open();await readonly();const detail=JSON.parse($('dag-reuse-proof').textContent).instance;
 check(posts().length===n&&detail.runs.length===2&&runs.every(id=>detail.runs.some(r=>r.run_id===id))&&detail.data_version===2,'cold directory restores same instance, Runs and both result versions with zero POST');
 check($('dag-reuse-results').textContent.includes('合计 15')&&$('dag-reuse-results').textContent.includes('合计 30'),'both actual arithmetic results retained');
}
async function remaining(){
 const dual=info.scenario==='dual',e=info.execution;
 const expected=dual?[
  {input:{columns:{[e.aggregate_steps[0]]:'quantity',[e.aggregate_steps[1]]:'amount'}},totals:['2.250','0.3']},
  {input:{columns:{[e.aggregate_steps[0]]:'amount',[e.aggregate_steps[1]]:'quantity'}},totals:['0.3','2.250']},
 ]:[{input:{column:'amount'},totals:['30']},{input:{column:'quantity'},totals:['15']}];
 const visibleResult=(wanted,version)=>{
  const prefix=`结果版本 ${version} · `,rows=[...$('dag-reuse-results').children].filter(row=>row.textContent.startsWith(prefix));
  const columns=dual?e.aggregate_steps.map(sid=>wanted.input.columns[sid]):[wanted.input.column];
  const expectedParts=columns.map((column,i)=>`${dual?e.aggregate_steps[i]:'求和'}：列 ${column}，行数 2，合计 ${wanted.totals[i]}`).sort();
  const summary=rows[0]?.querySelector('[data-role="dag-result-summary"]');
  return rows.length===1&&visible(rows[0])&&visible(summary)&&summary.textContent.startsWith(prefix)&&same(summary.textContent.slice(prefix.length).split('；').sort(),expectedParts);
 };
 check(posts().length===0,'directory discovery makes no POST');
 check($('use-list').querySelectorAll(`[data-use-family="CSV_DAG"][data-app-id="${info.app}"]`).length===2&&!!$('use-list').querySelector(`[data-use-family="CSV"][data-instance-id="${info.plain_instance}"]`),'exact application has two DAG choices and a distinct ordinary CSV instance');
 const description=entry().parentElement.textContent;
 check(description.includes(dual?'读取 → 双求和':'项目固定读取 → 求和 → 报告')&&description.includes(info.instance),'directory names exact existing family and selected nondefault instance');
 await readonly();await open();check(posts().length===0,'selected DAG opens with zero POST');await readonly();
 check($('dag-reuse-instance').value===info.instance&&$('dag-reuse-instance').selectedIndex===1,'directory explicitly selects the non-first authoritative instance');
 check($('dag-reuse-second-label').hidden===!dual,'original controller exposes only the correct typed input fields');
 if(dual)check(['dag-reuse-column-label','dag-reuse-column-second-label'].every((id,i)=>visible($(id))&&$(id).textContent.includes(e.aggregate_steps[i])),'each visible input label names its own stable aggregate node ID');
 else check($('dag-reuse-column').value===e.default_column&&e.default_column==='quantity','fixed report starts at its approved overlay default without opening project patch history');
 const runIds=[];
 for(const [index,wanted]of expected.entries()){
  const columns=dual?e.aggregate_steps.map(sid=>wanted.input.columns[sid]):[wanted.input.column];
  for(const [i,column]of columns.entries()){
   $('dag-reuse-run-confirm').checked=true;$('dag-reuse-run-confirm').dispatchEvent(new w.Event('change'));
   const select=$(i?'dag-reuse-column-second':'dag-reuse-column');select.value=column;select.dispatchEvent(new w.Event('change'));
   check($('dag-reuse-run').disabled&&!$('dag-reuse-run-confirm').checked,'editing input '+(i+1)+' requires renewed explicit confirmation');
  }
  $('dag-reuse-run-confirm').checked=true;$('dag-reuse-run-confirm').dispatchEvent(new w.Event('change'));
  const count=posts().length,submitted=click('dag-reuse-run');$('dag-reuse-run').click();await submitted;
  const post=posts().at(-1);check(posts().length===count+1&&post.path===`/api/internal/instances/${info.instance}/runs`&&same(post.body.input,wanted.input),'double click submits one exact node-keyed input to the selected instance');
  let detail=JSON.parse($('dag-reuse-proof').textContent).instance;const queued=detail.runs.find(r=>r.status==='QUEUED');assert(queued);
  check(queued.output===null&&queued.result_version===null&&detail.data_version===index,'current queued Run has no copied historical output');runIds.push(queued.run_id);
  assert.equal((await rpc({command:'worker'})).status,200);await click('dag-reuse-read');detail=JSON.parse($('dag-reuse-proof').textContent).instance;
  const run=detail.runs.find(r=>r.run_id===queued.run_id),record=detail.data.find(v=>v.run_id===run.app_run_id),binding=run.proof.internal_instance,write=run.proof.result.instance_result;
  check(run.status==='SUCCEEDED'&&run.proof.id===run.run_id&&run.instance_id===info.instance&&run.release_id===info.release&&run.execution_version===e.version&&run.expected_revision===detail.revision&&same(run.input,wanted.input),'same actual Run binds exact instance, revision, Release, execution family and new input');
  check(record&&record.instance_id===info.instance&&record.release_id===info.release&&record.version===index+1&&run.result_version===record.version&&same(record.data.result,run.output)&&binding.instance_id===info.instance&&binding.app_run_id===run.app_run_id&&binding.version===e.version&&write.instance_id===info.instance&&write.app_run_id===run.app_run_id&&write.release_id===info.release&&write.result_version===record.version&&write.record_fingerprint===record.fingerprint,'same typed AppRun and result version bind full stored output and receipt fingerprint');
  check(run.proof.steps.length===3&&run.proof.steps.every(s=>s.status==='VERIFIED')&&run.proof.business_writes===1&&run.proof.model_requests===0,'cold original Worker verifies three Operations, one typed write and zero models');
  const values=dual?e.aggregate_steps.map(sid=>run.output[sid]):[run.output];
  check((!dual||JSON.stringify(Object.keys(run.output).sort())===JSON.stringify([...e.aggregate_steps].sort()))&&values.every((v,i)=>JSON.stringify(Object.keys(v).sort())===JSON.stringify(['column','count','resource_id','source_hash','sum'])&&v.resource_id===info.resource&&v.source_hash===e.source_hash&&v.column===columns[i]&&v.count===2&&typeof v.sum==='string'&&v.sum===wanted.totals[i]),'complete five-field results preserve node IDs, resource hash and exact string sums');
  if(!dual)check(run.proof.result.output.text===`列 ${columns[0]}；行数 2；合计 ${wanted.totals[0]}`&&!Object.hasOwn(run.output,'text'),'fixed report text belongs to this verified Run while typed aggregate retains five fields');
  check(expected.slice(0,index+1).every((value,i)=>visibleResult(value,i+1)),'each visible version row binds its own stable node, input column, count and exact sum');await readonly();
 }
 check(new Set([...runIds,info.source_run]).size===3,'both new directory Runs differ from each other and their own source');
 const count=posts().length;await boot();await open();await readonly();const detail=JSON.parse($('dag-reuse-proof').textContent).instance;
 check(posts().length===count&&detail.id===info.instance&&$('dag-reuse-instance').selectedIndex===1&&detail.runs.length===2&&detail.data_version===2&&runIds.every(id=>detail.runs.some(r=>r.run_id===id)),'cold directory restores exact non-first instance, both same Runs and v1/v2 with zero POST');
 check(expected.every((wanted,i)=>visibleResult(wanted,i+1)),'cold visible history retains each exact version-to-node/column/count/sum mapping');
}
async function guards(){
 await readonly();
 for(const scenario of [
  {path:`/api/apps/${info.app}`,remaining:2,change:async()=>{await nav('resources');await nav('apps');},label:'second app read workspace ABA'},
  {path:`/api/internal/apps/${info.app}/dag-releases`,remaining:1,change:async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');},label:'DAG release list same-account reconnect'},
  {path:`/api/apps/${info.app}`,remaining:1,change:async()=>{for(const p of [info.other,info.project]){$('project-select').value=p;await $('project-select').onchange(new w.Event('change'));}},label:'initial app read project ABA'},
 ]){
  hold={path:scenario.path,remaining:scenario.remaining};const opening=click(entry());await waitHeld('held '+scenario.label);await scenario.change();const release=releaseRead;releaseRead=null;release();await opening;
  check(!w.eval('csvDagContext')&&!$('dag-reuse-proof').textContent&&!$('dag-reuse-results').textContent,scenario.label+' rejects late opening chain');check(posts().length===0,'late opening has no write');await readonly();
 }
 for(const error of [false,true]){
  hold={path:`/api/internal/instances/${info.instance}`,remaining:1,error};const opening=click(entry());await waitHeld('held exact instance read');
  $('dag-reuse-instance').value=info.second_instance;$('dag-reuse-instance').dispatchEvent(new w.Event('change'));await click('dag-reuse-read');const before=$('dag-reuse-proof').textContent;
  const release=releaseRead;releaseRead=null;release();await opening;
  check(w.eval('csvDagContext.reuse.instance.id')===info.second_instance&&$('dag-reuse-proof').textContent===before,'late original instance '+(error?'error':'success')+' cannot replace selected second instance');await readonly();
 }
 unknownHint=true;await w.refreshApps();check(!entry()&&$('use-list').textContent.includes('不受此入口支持'),'unknown/prototype-named execution version has no runnable DAG entry');unknownHint=false;await w.refreshApps();
 let rejected=false;try{await w.openSavedDagUse(info.app,info.plain_instance);}catch(e){rejected=e.message==='VERSION_CONFLICT';}
 check(rejected&&!w.eval('csvDagContext')&&!$('dag-reuse-proof').textContent,'ordinary instance cannot be opened through DAG route');await readonly();await open();
 const stale=entry().onclick,before=requests.length,intents=w.eval('JSON.stringify([...dagReuseIntents])');assert.equal((await rpc({command:'revoke'})).status,200);await w.refreshApps();
 check(requests.slice(before).some(r=>r.path===`/api/apps/${info.app}`&&r.status===403)&&!w.eval('csvDagContext')&&!$('dag-reuse-proof').textContent&&!$('dag-reuse-results').textContent,'authoritative directory refresh403 clears cached DAG evidence');
 check(w.eval('JSON.stringify([...dagReuseIntents])')===intents,'directory invalidation preserves original intent map');
 const retried=requests.length;await stale(new w.Event('click'));
 check(requests.slice(retried).some(r=>r.status===403),'captured stale callback reauthorizes after real synthetic revoke403');
 check(!w.eval('csvDagContext')&&!$('dag-reuse-proof').textContent&&!$('dag-reuse-results').textContent,'revoked open clears protected DAG proof and results');
 check(posts().length===0,'navigation, unknown type and revoked opens create zero Run/Grant POST');await readonly();
}
async function downloads(){
 const initialPosts=posts().length;
 const proof=()=>JSON.parse($('dag-reuse-proof').textContent);
 const button=version=>$('dag-reuse-results').querySelector(`[data-result-version="${version}"] button`);
 const snapshot=proof(),detail=snapshot.instance,rel=snapshot.release,e=rel.snapshot.execution_source;
 const records=[...detail.data].sort((a,b)=>a.version-b.version);
 const runFor=record=>detail.runs.find(r=>r.app_run_id===record.run_id);
 const path=version=>`/api/internal/instances/${detail.id}/runs/${runFor(records[version-1]).run_id}`;
 async function capture(index,version){
  await wait(()=>downloadBlobs[index]?.revoked,'download URL revoked');
  const b=downloadBlobs[index],text=await b.blob.text(),value=JSON.parse(text),record=records[version-1],run=runFor(record);
  assert.equal(b.blob.type,'application/json;charset=utf-8');assert.equal(text,JSON.stringify(value,null,2)+'\n');
  assert.equal(value.namespace,'csv-dag-result.v1');assert.equal(value.instance_id,detail.id);assert.equal(value.run_id,run.run_id);assert.equal(value.app_run_id,record.run_id);
  assert.equal(value.instance_revision,run.expected_revision);assert.equal(value.release_id,record.release_id);assert.equal(value.release_fingerprint,rel.fingerprint);
  assert.equal(value.execution_version,e.version);assert.equal(value.result_version,version);assert.equal(value.record_fingerprint,record.fingerprint);
  assert(same(value.input,run.input)&&same(value.result,record.data.result)&&same(value.output,run.proof.result.output));
  assert(same(value.source,{app_id:detail.source_app_id,run_id:e.run_id,plan_key:e.plan_key,plan_fingerprint:e.plan_fingerprint,source_hash:e.source_hash}));
  assert.equal(value.run_plan_fingerprint,run.proof.plan_fingerprint);
  const ids=[...(e.aggregate_steps||[e.aggregate_step]),...(e.report_step?[e.report_step]:[])];
  assert(same(Object.keys(value.node_outputs).sort(),[...ids].sort()));
  for(const id of ids)assert(same(value.node_outputs[id],run.proof.result.steps.find(s=>s.step_id===id).data));
  for(const id of e.aggregate_steps||[e.aggregate_step])assert.equal(typeof value.node_outputs[id].sum,'string');
  if(e.report_step)assert.equal(value.node_outputs[e.report_step].text,`列 ${run.output.column}；行数 ${run.output.count}；合计 ${run.output.sum}`);
  assert.equal(value.model_requests,0);assert.equal(value.semantic_status,'UNKNOWN');assert.equal(value.owner_acceptance,'PENDING');assert.equal(value.formal_publication_enabled,false);
  assert(!text.includes('item,amount,quantity')&&!text.includes('synthetic-test-A')&&!text.includes('authorization_fingerprint'));
  assert(downloadAnchors.some(a=>a.url===b.url&&a.filename===`csv-dag-${detail.id}-${run.run_id}-v${version}.json`));
  fs.writeFileSync(info.output.replace('result.json',`download-blob-${index}.json`),text);
  check(true,`download v${version} exact Run/typed/revision/Release/source/input/version and complete stable-node outputs with string sums`);
 }
 for(const version of [2,1]){
  const start=requests.length,index=downloadBlobs.length,work=click(button(version));button(version).click();await work;await capture(index,version);
  check(requests.slice(start).filter(r=>r.path===path(version)).length===1&&requests.slice(start).every(r=>r.method==='GET'),'duplicate explicit download uses one freshly authorized Run GET and read-only plan validation');await readonly();
 }
 if(e.report_step){
  const index=downloadBlobs.length;downloadMutation={label:'synthetic missing bound report text',change:r=>{delete r.proof.result.steps.find(s=>s.step_id===e.report_step).data.text;}};
  await click(button(2));check(downloadBlobs.length===index&&$('dag-reuse-results').textContent.includes('未下载文件'),'missing report text rejects before Blob creation');await readonly();
 }
 if(info.scenario==='dual'){
  const changes={
   'wrong actual Run':r=>r.run_id=runFor(records[0]).run_id,
   'wrong typed AppRun':r=>r.app_run_id='iapprun_synthetic_wrong',
   'wrong Release':r=>r.release_id='irelease_synthetic_wrong',
   'wrong result version':r=>r.result_version=1,
   'wrong source hash':r=>r.proof.result.steps.find(s=>s.step_id===e.aggregate_steps[0]).data.source_hash='0'.repeat(64),
   'changed complete node output':r=>r.output[e.aggregate_steps[1]].sum='999',
  };
  for(const [label,change]of Object.entries(changes)){
   const count=downloadBlobs.length;downloadMutation={label:'synthetic '+label,change};await click(button(2));
   check(downloadBlobs.length===count&&$('dag-reuse-results').textContent.includes('未下载文件'),label+' rejects without Blob');await readonly();
  }
  let count=downloadBlobs.length;
  hold={path:path(1),remaining:1};let work=click(button(1));await waitHeld('held earlier history result download');
  await click(button(2));await capture(count,2);let release=releaseRead;releaseRead=null;release();await work;
  check(downloadBlobs.length===count+1,'selecting another historical result invalidates earlier late download');
  const restore=async()=>{await nav('apps');await wait(()=>!!entry(),'restored directory');await open();};
  const changesOfContext=[
   ['workspace ABA',async()=>{await nav('resources');await restore();}],
   ['project ABA',async()=>{for(const id of [info.other,info.project]){$('project-select').value=id;await $('project-select').onchange(new w.Event('change'));}await restore();}],
   ['instance ABA',async()=>{for(const id of [info.second_instance,info.instance]){$('dag-reuse-instance').value=id;$('dag-reuse-instance').dispatchEvent(new w.Event('change'));await click('dag-reuse-read');}}],
   ['identity ABA',async()=>{for(const id of ['synthetic-test-B','synthetic-test-A']){await click('identity-switch');$('token').value=id;await click('connect');}if($('project-select').value!==info.project){$('project-select').value=info.project;await $('project-select').onchange(new w.Event('change'));}await restore();}],
  ];
  for(const [label,change]of changesOfContext){
   count=downloadBlobs.length;hold={path:path(2),remaining:1};work=click(button(2));await waitHeld('held download '+label);await change();
   release=releaseRead;releaseRead=null;release();await work;
   check(downloadBlobs.length===count&&w.eval('dagReuseDownloads.size')===0,label+' suppresses late success and releases download key');await readonly();
  }
  count=downloadBlobs.length;hold={path:path(2),remaining:1,error:true};work=click(button(2));await waitHeld('held stale download error');
  await nav('resources');await restore();const currentProof=$('dag-reuse-proof').textContent;release=releaseRead;releaseRead=null;release();await work;
  check(downloadBlobs.length===count&&$('dag-reuse-proof').textContent===currentProof,'late error does not clear current restored protected view');
  anchorFailure=true;const anchors=downloadAnchors.length;await click(button(2));anchorFailure=false;
  await wait(()=>downloadBlobs.at(-1)?.revoked,'failed anchor URL revoked');
  check(downloadBlobs.length===count+1&&downloadAnchors.length===anchors&&!$('dag-reuse-results').querySelector('a[download]'),'anchor exception removes link, revokes URL and releases key');
  count=downloadBlobs.length;await click(button(1));await capture(count,1);
  assert.equal((await rpc({command:'revoke'})).status,200);count=downloadBlobs.length;const start=requests.length;await click(button(2));
  check(requests.slice(start).some(r=>r.path===path(2)&&r.status===403)&&downloadBlobs.length===count&&!w.eval('csvDagContext')&&!$('dag-reuse-results').textContent&&!$('dag-reuse-proof').textContent,'real revoked grant returns403 and clears protected results without Blob');await readonly();
 }
 check(posts().length===initialPosts&&w.eval('dagReuseDownloads.size')===0,'all download actions add zero Run/Grant POST and leave no download keys');
 check(downloadBlobs.every(b=>b.revoked),'every created Blob URL is revoked');
}
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='guards')await guards();else if(['dual','fixed'].includes(info.scenario))await remaining();else await use();if(info.download)await downloads();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,download_feature:info.download,checks,requests,assets,boots,mutations,heldWaits,
   download_blobs:downloadBlobs.map(({url,blob,revoked})=>({url,type:blob.type,bytes:blob.size,revoked})),download_anchors:downloadAnchors,
   scope:'Actual ASGI TestClient HTTP + full served JS in JSDOM, cold SQLite NoModel DAG Worker',pg:'NOT_RUN',native_browser:'NOT_RUN',real_model:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
