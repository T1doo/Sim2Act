'use strict';
// Actual served page + HTTP via Python bridge; synthetic data and NoModel Worker.
// JSDOM does not qualify Windows/native browser or real semantic acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),actions=[],static_resource_loads=[],checks=[];
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null,lose=null,first_owner_history=null;
const run_ids=[];
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+20000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const visible=el=>{if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;};
async function click(value,double=false){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();if(double)el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=()=>actions.filter(r=>r.method==='POST');
const endpoint=rid=>`/api/internal/instances/${info.instance}/runs/${rid}/text-owner-review`;
const entry=()=>$('use-list').querySelector(`[data-use-family="CLOSED_TEXT_WORKFLOW"][data-app-id="${info.app}"] button`);
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);static_resource_loads.push({boot:boots,status:r.status,path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};actions.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response_text=r.text;
   if(hold&&path===hold.path&&request.method==='GET'&&--hold.remaining===0){hold=null;request.controlled_delivery='HELD_AFTER_ACTUAL_HTTP';await new Promise(resolve=>{releaseRead=resolve;});}
   if(lose&&path===lose.path&&request.method==='POST'&&request.body?.command===lose.command){lose=null;request.controlled_delivery='RECEIPT_LOST_AFTER_ACTUAL_HTTP';throw new TypeError('controlled receipt loss after accepted actual HTTP');}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');await nav('apps');await wait(()=>!!entry(),'four-step directory entry');
}
async function open(iid=info.instance){
 await click(entry());check(w.eval('engineering?.workflow')&&visible($('internal-panel')),'directory opens existing four-step controller');
 const item=[...$('internal-instances').children].find(r=>r.textContent.includes(iid));assert(item);await click(item.querySelector('button'));
 check(w.eval('engineering.instance.id')===iid&&visible($('internal-workflow-a'))&&visible($('internal-workflow-b')),'explicit instance selection exposes two terms and report input');
}
async function openRun(rid){const item=[...$('internal-runs').children].find(r=>r.textContent.includes(rid));assert(item);await click(item.querySelector('button'));}
const currentOwner=()=>w.eval('ownerView?.state');
function terms(a,b,emit){
 for(const [side,value]of [['a',a],['b',b]]){$('internal-workflow-'+side).value=value;$('internal-workflow-'+side).dispatchEvent(new w.Event('input',{bubbles:true}));}
 $('internal-workflow-report').checked=emit;$('internal-workflow-report').dispatchEvent(new w.Event('input',{bubbles:true}));
}
async function run(a,b,emit,version){
 terms(a,b,emit);const n=posts().length;await click('internal-run-submit',true);
 check(posts().length===n+1&&posts().at(-1).path===`/api/internal/instances/${info.instance}/runs`,'double click submits exactly one new Run through original controller');
 assert.deepEqual(posts().at(-1).body.input,{term_a:a,term_b:b,emit_report:emit});
 const rid=w.eval('engineering.run.id');const worker=await rpc({command:'worker',run:rid});assert.equal(worker.status,200,worker.text);await click('internal-refresh');
 const saved=w.eval('engineering.run');check(saved.id===rid&&saved.status===(emit?'SUCCEEDED':'PARTIAL'),'normal NoModel Worker and visible history return the same Run');
 check(saved.steps.length===4&&saved.steps.slice(0,3).every(s=>s.status==='VERIFIED')&&saved.steps[3].status===(emit?'VERIFIED':'SKIPPED'),'same Run exposes four independently retained step outcomes');
 if(emit){
  check(saved.result_version===version&&w.eval('ownerView.rid')===rid&&currentOwner()?.content_access===true,'successful same Run auto-selects its own qualified report and owner state');
  check(currentOwner().owner_acceptance==='PENDING'&&currentOwner().sequence===0&&!$('owner-status').textContent.includes('ACCEPTED'),'a new successful Run starts a distinct empty PENDING owner ledger');
  const expected=saved.result,body=$('owner-natural-evidence');
  check(body.textContent.includes(rid)&&body.textContent.includes(expected.term_a)&&body.textContent.includes(expected.term_b)&&body.textContent.includes(expected.source_hash),'readable report identifies exact Run, both terms and source hash');
  check([...body.querySelectorAll('blockquote')].map(n=>n.textContent).join('\n')===[...expected.citations_a,...expected.citations_b].map(c=>c.quote).join('\n'),'all citation text is displayed in full');
  check([...body.querySelectorAll('pre')].some(n=>n.textContent===expected.text),'full saved report text is displayed without truncation');
  check(expected.citations_a.every(c=>body.textContent.includes(`第 ${c.start_line}—${c.end_line} 行`))&&expected.citations_b.every(c=>body.textContent.includes(`第 ${c.start_line}—${c.end_line} 行`)),'each citation retains its exact line location');
  check(!$('owner-proof').closest('details').open&&$('correction-panel').hidden,'raw proof stays in details and natural correction is not enabled for this family');
 }else{
  check(saved.result===null&&saved.result_version===null&&w.eval('ownerView.rid')==='','PARTIAL has no typed report or selected owner Run');
  check(!$('owner-natural-evidence').textContent&&!$('owner-criteria').textContent&&$('owner-form').hidden&&$('owner-prepare').disabled,'PARTIAL clears previous report, declaration form and signing ability');
 }
 return rid;
}
async function flow(){
 check(posts().length===0,'cold directory discovery creates no writes');await open();check(posts().length===0,'explicit app and instance selection are read-only');
 assert(info.input_a&&info.input_b&&typeof info.input_a.term_a==='string'&&typeof info.input_a.term_b==='string');
 const baseline=w.eval('engineering.instance.data_version'),a=info.input_a.term_a,b=info.input_a.term_b;
 assert.deepEqual(info.input_b,{term_a:b,term_b:a,emit_report:true});
 const first=await run(a,b,true,baseline+1),beforePrepare=posts().length;
 await click('owner-prepare',true);
 check(posts().length===beforePrepare+1&&posts().at(-1).path===endpoint(first)+'-requests'&&posts().at(-1).body.command==='PREPARE','double click freezes exactly one explicit per-Run PREPARE');
 check(currentOwner().sequence===1&&currentOwner().record.kind==='PREPARE'&&visible($('owner-form')),'only explicit PREPARE opens the per-item decision form');
 const items=currentOwner().record.payload.contract.items;check(items.length>2&&items.every(item=>$('owner-choice-'+item.id)&&$('owner-reason-'+item.id)),'all saved Goal criteria are separately represented for manual decision');
 for(const item of items){$('owner-choice-'+item.id).value='ACCEPT';$('owner-choice-'+item.id).dispatchEvent(new w.Event('change',{bubbles:true}));$('owner-reason-'+item.id).value='Synthetic human test: compared exact complete source and report for '+item.id;$('owner-reason-'+item.id).dispatchEvent(new w.Event('input',{bubbles:true}));}
 $('owner-ack').checked=true;$('owner-ack').dispatchEvent(new w.Event('change',{bubbles:true}));
 const beforeDecide=posts().length,requestOffset=actions.length;lose={path:endpoint(first)+'-requests',command:'DECIDE'};await click('owner-submit',true);
 const decision=posts().at(-1),key=decision.body.request_key;check(posts().length===beforeDecide+1&&decision.body.command==='DECIDE'&&decision.status===201,'double click issues one DECIDE and real server accepts before controlled receipt loss');
 check(w.eval('ownerPending.size')===1&&$('owner-key').value===key&&$('owner-submit').disabled,'lost accepted receipt retains original key and blocks duplicate submission');
 check(!actions.slice(requestOffset).some(r=>r.method==='GET'&&r.path.startsWith(endpoint(first))),'unknown accepted DECIDE is not automatically retried or read');
 const beforeRecovery=posts().length;await click('owner-recover');
 check(posts().length===beforeRecovery&&actions.at(-1).method==='GET'&&actions.at(-1).path===endpoint(first)+'?request_key='+encodeURIComponent(key),'manual recovery uses only original-key GET without another POST');
 check(currentOwner().owner_acceptance==='ACCEPTED'&&currentOwner().sequence===2&&currentOwner().recovered.request_key===key&&w.eval('ownerPending.size')===0,'original-key recovery returns the exact accepted per-Run declaration');
 first_owner_history=JSON.parse(JSON.stringify(currentOwner().history));const originalHistory=JSON.stringify(first_owner_history),beforeCold=posts().length;await boot();await open();await openRun(first);
 check(posts().length===beforeCold&&currentOwner().owner_acceptance==='ACCEPTED'&&currentOwner().sequence===2,'cold page reopens the same completed Run and immutable declaration without writes');
 check(JSON.stringify(currentOwner().history)===originalHistory,'cold page preserves the exact original owner history');
 const second=await run(b,a,true,baseline+2);check(first!==second,'different explicit input creates a distinct Run');
 const old=await rpc({method:'GET',path:endpoint(first),headers:{Authorization:'Bearer synthetic-test-A'}});assert.equal(old.status,200,old.text);const stale=JSON.parse(old.text);
 check(stale.owner_acceptance==='STALE'&&stale.content_access===false&&!stale.current&&!stale.record&&JSON.stringify(stale.history)===originalHistory,'old accepted Run becomes metadata-only STALE while original history is preserved');
 const third=await run(a,b,false,null);run_ids.push(first,second,third);check(third!==second&&third!==first,'explicit report-off input creates its own PARTIAL Run');
 check(w.eval('engineering.instance.data_version')===baseline+2&&$('internal-data').querySelectorAll('[data-text-workflow-action="review"]').length===baseline+2,'PARTIAL creates no report version and every saved report has a same-Run review entry');
 check(posts().filter(r=>r.path.endsWith('/runs')).length===3&&posts().filter(r=>r.path.endsWith('/text-owner-review-requests')).length===2,'page writes are bounded to three explicit Runs and PREPARE/DECIDE');
}
async function holdOwner(change,label){
 const beforePosts=posts().length,beforeNode=$('owner-natural-evidence').firstChild;hold={path:endpoint(info.seed_run),remaining:1};
 const reading=click('owner-refresh');await wait(()=>!!releaseRead,'held '+label);await change();const afterNode=$('owner-natural-evidence').firstChild,afterStatus=$('owner-status').textContent;
 const release=releaseRead;releaseRead=null;release();await reading;
 check($('owner-natural-evidence').firstChild===afterNode&&$('owner-status').textContent===afterStatus,label+' discards late actual owner response');
 check(posts().length===beforePosts,label+' performs no POST');return beforeNode;
}
async function navigation(){
 await open();await openRun(info.seed_run);check(currentOwner()?.content_access===true,'real fixture seed Run opens its verified report without page Worker');
 await holdOwner(async()=>{await nav('resources');await nav('apps');},'workspace ABA');
 await holdOwner(async()=>{$('owner-run').value='';await $('owner-run').onchange(new w.Event('change'));},'Run deselection');
 check(w.eval('ownerView.rid')===''&&!$('owner-natural-evidence').textContent,'explicit Run deselection leaves no prior report');
 await openRun(info.seed_run);
 await holdOwner(async()=>{const item=[...$('internal-instances').children].find(r=>r.textContent.includes(info.second_instance));assert(item);await click(item.querySelector('button'));},'instance selection');
 check(w.eval('engineering.instance.id')===info.second_instance&&!$('owner-natural-evidence').textContent,'new selected instance keeps its own empty owner state');
 await open();await openRun(info.seed_run);
 await holdOwner(async()=>{for(const project of [info.other,info.project]){$('project-select').value=project;await $('project-select').onchange(new w.Event('change'));}},'project ABA');
 check(!w.eval('engineering')&&!$('owner-natural-evidence').textContent,'project change clears old engineering and report state');
 await open();await openRun(info.seed_run);
 await holdOwner(async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');await nav('apps');},'same-account reconnect');
 check(!w.eval('engineering')&&!$('owner-natural-evidence').textContent,'same-account reconnect clears old report and owner context');
 check(posts().length===0,'all navigation and real held reads create zero writes');
}
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='navigation')await navigation();else await flow();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,actions,static_resource_loads,boots,
   classification:info.scenario==='navigation'?'ACTUAL_HTTP_JSDOM_NAVIGATION_NO_WORKER':'ACTUAL_HTTP_JSDOM_NO_MODEL_FLOW',qualification_role:'UI_AUTHOR',run_ids,first_owner_history,
   fixture_seed_run:info.seed_run,scope:'Actual served JavaScript and ASGI HTTP; controlled receipt delivery only, synthetic material and human choices',pg:'NOT_RUN',native_browser:'NOT_RUN',real_model:'NOT_RUN',real_semantic_owner_acceptance:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
