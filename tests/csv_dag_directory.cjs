'use strict';
// Product page + actual ASGI HTTP via IPC. JSDOM is not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[],mutations=[];
let unknownHint=false;
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null;
const httpReplies=[],heldWaits=[];
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
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);httpReplies.push(Date.now());
   if(hold&&path===hold.path&&--hold.remaining===0){const gate=hold;hold=null;await new Promise(resolve=>{releaseRead=resolve;});if(gate.error){mutations.push({path,kind:'synthetic late response403',actual_status:r.status});return new Response(JSON.stringify({error:{code:'PERMISSION_DENIED',message:'synthetic delayed error'}}),{status:403,headers:{'Content-Type':'application/json'}});}}
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
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='guards')await guards();else await use();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,requests,assets,boots,mutations,heldWaits,
   scope:'Actual ASGI TestClient HTTP + full served JS in JSDOM, cold SQLite NoModel DAG Worker',pg:'NOT_RUN',native_browser:'NOT_RUN',real_model:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
