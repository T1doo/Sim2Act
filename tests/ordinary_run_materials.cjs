'use strict';
// Full served JS and authenticated ASGI; synthetic SQLite/mock, not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],observations=[],mutations=[],pending=new Map();
let serial=0,active=0,dom,w,$,hold=null,release=null,lose=false,failList=false,omitOnce=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const wait=async(fn,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const posts=()=>requests.filter(r=>r.method==='POST');
const chosen=()=>[...$('run-materials').selectedOptions].map(o=>o.value);
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el));assert(!el.matches(':disabled'));const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
async function choose(ids){for(const option of $('run-materials').options)option.selected=ids.includes(option.value);await action('run-materials','change');}
const project=async id=>{$('project-select').value=id;await action('project-select','change');};
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
   if(hold&&path===hold.path&&request.method===hold.method){hold=null;await new Promise(resolve=>{release=resolve;});}
   if(lose&&request.method==='POST'&&path.endsWith('/runs')){lose=false;throw TypeError('Synthetic receipt loss after actual durable acceptance');}
   if(request.method==='GET'&&path.endsWith('/resources')){
    if(failList){failList=false;request.delivery_error='Synthetic resource-list delivery failure after actual GET200';mutations.push({path,kind:request.delivery_error});throw TypeError(request.delivery_error);}
    if(omitOnce){const id=omitOnce;omitOnce=null;request.delivered_response=request.response.filter(m=>m.id!==id);mutations.push({path,kind:'Synthetic one-response catalog omission; permissions unchanged, not revocation',resource_id:id});return new Response(JSON.stringify(request.delivered_response),{status:r.status,headers:{'Content-Type':'application/json'}});}
   }
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);$('goal').value='读取明确选择的这一份合成材料';
}
async function flow(){
 const target=info.materials[info.case==='exact'?1:5],path=`/api/projects/${info.project}/runs`;
 if(info.case==='use'){
  if($('run-materials')){
   for(const option of $('goal-card-resources').options)option.selected=option.value===info.materials[2].id;
   await action('goal-card-resources','change');
   check($('run-materials').multiple&&$('run-materials').options.length===9&&chosen().length===0,'nine eligible materials are visible and none implicitly attached');
   check(!$('run-submit').disabled,'zero explicitly attached materials is a valid UI choice');
   await choose(info.materials.slice(0,8).map(m=>m.id));check(!$('run-submit').disabled&&chosen().length===8,'eight selected materials remain explicit without truncation');
   await choose(info.materials.map(m=>m.id));const count=posts().length;check($('run-submit').disabled&&chosen().length===9,'ninth selection is preserved but submission is disabled');
   $('run-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setImmediate(r));check(posts().length===count,'over-limit submit is rejected locally with zero POST');
   await choose([target.id]);
   check($('goal-card-resources').selectedOptions.length===1&&$('goal-card-resources').value===info.materials[2].id,'ordinary selection leaves independent GoalCard material choice unchanged');
  }
  await action('run-submit');const sent=posts().filter(r=>r.path===path).at(-1);observations.push({kind:'actual_submission',picker_present:!!$('run-materials'),request:sent});
  if(sent.status!==202)assert.equal((await rpc({command:'rejected-readonly'})).status,200);
  check(sent.status===202,'project with nine materials can actually submit a one-material Run');
  check(sent.body.resource_refs.length===1&&sent.body.resource_refs[0]===target.id,'POST contains only explicitly selected material');
  const rid=sent.response.run_id;assert.equal((await rpc({command:'worker',run:rid,resource:target.id})).status,200);
  await action('run-history-refresh');await action($('runs').querySelector('button'));
  const result=JSON.parse($('raw-result').textContent),input=result.contract.snapshot.goal.resource_refs;check(result.id===rid&&input.length===1&&input[0]===target.id,'actual persistent Run and frozen input retain selected ID only');
  check(result.status==='PARTIAL'&&result.result.mode==='MOCK'&&result.result.receipts[0].data.content===target.content,'normal mock Worker reads selected text; whole-goal acceptance is not promoted');
  check(info.materials.filter(m=>m.id!==target.id).every(m=>!$('raw-result').textContent.includes(m.content)),'unselected material bodies are absent from selected Run readback');
  check(posts().filter(r=>r.path===path).length===1,'entire selected-input execution has one explicit Run POST');
  for(const ids of [[],info.materials.slice(0,8).map(m=>m.id)]){
   await choose(ids);$('goal').value=`仅冻结 ${ids.length} 份材料的合成目标，不声称完成目标验收`;await action('run-submit');const queued=posts().at(-1);
   check(queued.status===202&&JSON.stringify(queued.body.resource_refs)===JSON.stringify(ids),`actual API accepts exact ${ids.length}-material new Run without executing it`);
   observations.push({kind:'queued_boundary_input',request:queued});
  }
  check(posts().filter(r=>r.path===path).length===3,'three explicit Runs accepted, only the one-material Run actually executed');
 }else if(info.case==='refresh'){
  await choose([target.id]);const before=posts().length;assert.equal((await rpc({command:'new-material'})).status,200);await action('run-history-refresh');
  check($('run-materials').options.length===10&&chosen().length===1&&chosen()[0]===target.id,'newly authorized tenth material appears without automatic selection');
  failList=true;await action('run-history-refresh');
  check(chosen()[0]===target.id&&!$('run-materials').disabled&&$('run-submit').disabled,'failed list delivery preserves original ID while allowing explicit deselection');
  await choose([]);check(!$('run-submit').disabled,'user can explicitly remove unavailable materials and submit a Goal-only task');
  await action('run-history-refresh');await choose([target.id]);
  hold={method:'GET',path:`/api/projects/${info.project}/resources`};const delayed=action('run-history-refresh');await wait(()=>!!release,'old material list held');
  await project(info.other);check(chosen().length===0&&!$('run-materials').textContent.includes(target.name),'project switch clears old material selection and labels');
  await project(info.project);check(chosen().length===0,'return to A starts with no silently restored material selection');
  const deliver=release;release=null;deliver();await delayed;check(chosen().length===0,'late old material list cannot restore prior selection');
  await choose([target.id]);await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');
  check(chosen().length===0&&!$('run-materials').textContent.includes(target.name),'identity switch clears prior choices and protected names');
  check(posts().length===before,'all selection/list/navigation operations issue zero product POST');
 }else if(info.case==='exact'){
  const select=$('run-acceptance');check(!!select,'normal task form exposes an explicit finite-goal choice');
  $('goal').value='A private synthetic draft';select.value='exact-resource-read.v1';await action(select,'change');
  await choose([info.materials[0].id]);check($('run-submit').disabled,'CSV cannot enter text verbatim contract');
  await choose([info.materials[3].id]);check($('run-submit').disabled,'JSON cannot enter text verbatim contract');
  await choose([target.id]);check(!$('run-submit').disabled&&$('goal').readOnly,'single TXT explicitly selects the fixed goal');
  await project(info.other);check(select.value===''&&select.dataset.freeGoal===undefined&&$('goal').value==='','project switch clears exact choice and former free goal');
  await project(info.project);await choose([target.id]);select.value='exact-resource-read.v1';await action(select,'change');
  lose=true;hold={method:'POST',path};const started=action('run-submit');await wait(()=>!!release,'actual exact Run reply held');
  const original=structuredClone(posts().at(-1).body);
  check(original.acceptance==='exact-resource-read.v1'&&original.request_key.startsWith('exact-read:'),'finite selection and original request key are submitted together');
  select.value='';select.dispatchEvent(new w.Event('change',{bubbles:true}));check(select.value==='exact-resource-read.v1'&&select.disabled,'pending intent cannot silently change acceptance mode');
  const deliver=release;release=null;deliver();await started;
  check(w.eval('runSubmissionEntry().state')==='unknown','lost reply keeps original finite intent unknown');
  await project(info.other);await project(info.project);
  check(select.value==='exact-resource-read.v1'&&JSON.stringify(w.eval('runSubmissionEntry().body'))===JSON.stringify(original),'project ABA restores only original UNKNOWN body and key');
  await action('run-submit-recover');check(posts().length===2&&JSON.stringify(posts()[1].body)===JSON.stringify(original)&&posts()[1].response.run_id===posts()[0].response.run_id,'explicit recovery uses same finite intent and durable Run');
  const rid=posts()[0].response.run_id;assert.equal((await rpc({command:'worker',run:rid,resource:target.id})).status,200);
  await action('run-history-refresh');await action($('runs').querySelector('button'));
  const result=JSON.parse($('raw-result').textContent);w.__candidate=result;
  check(w.eval('exactReadPassed(__candidate)')&&$('run-goal-acceptance').textContent.includes('完整读取合同 PASS'),'served UI displays actual independently accepted finite goal');
  const escaped=structuredClone(result);escaped.result.answer='{"\\u0063ontent":'+JSON.stringify(result.result.read_result.content)+'}';w.__candidate=escaped;check(w.eval('exactReadPassed(__candidate)')===true,'legal JSON escaped key matches backend semantics');
  const legacy=structuredClone(result);delete legacy.contract.snapshot.exact_read.request_protocol;legacy.contract.snapshot.exact_read.request_timeout_seconds=8;w.__candidate=legacy;check(w.eval('exactReadPassed(__candidate)')===true,'original eight-second finite contract is still displayed');
  const directV1=structuredClone(result);directV1.contract.snapshot.exact_read.request_protocol='exact-read-direct.v1';w.__candidate=directV1;check(w.eval('exactReadPassed(__candidate)')===true,'original direct v1 contract stays readable');
  const faults=[r=>r.contract.snapshot.resources=[null],r=>delete r.result.receipts,r=>r.result.receipts[0].receipt_ref='op_wrong',r=>r.result.receipts[0].check_results[0].status='FAIL',r=>delete r.contract.snapshot.exact_read.source_hash,r=>r.result.answer='{"content":"wrong","content":'+JSON.stringify(result.result.read_result.content)+'}'];
  faults.push(r=>r.contract.snapshot.exact_read.request_timeout_seconds=8,r=>r.contract.snapshot.exact_read.request_protocol='unknown-profile');
  for(const damage of faults){const r=structuredClone(result);damage(r);w.__candidate=r;check(w.eval('exactReadPassed(__candidate)')===false,'malformed result fails closed without a PASS label');}
  await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');
  check(select.value===''&&select.dataset.freeGoal===undefined&&!$('run-materials').textContent.includes(target.name),'identity switch clears finite choice and former material labels');
 }else{
  await choose([target.id]);lose=true;hold={method:'POST',path};const started=action('run-submit');await wait(()=>!!release,'actual accepted Run reply held');
  $('run-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setImmediate(r));check(posts().length===1&&$('run-materials').disabled,'sending locks picker and blocks a duplicate submit');
  const deliver=release;release=null;deliver();await started;check(w.eval('runSubmissionEntry().state')==='unknown'&&$('run-materials').disabled,'lost actual receipt preserves UNKNOWN and locked selection');
  const original=structuredClone(posts()[0].body);assert.equal((await rpc({command:'new-material'})).status,200);omitOnce=target.id;await action('run-history-refresh');
  check(chosen().length===1&&chosen()[0]===target.id&&JSON.stringify(w.eval('runSubmissionEntry().body'))===JSON.stringify(original),'refresh with new material preserves frozen selection/body/key');
  check($('run-materials').disabled&&!$('run-materials').textContent.includes(target.name)&&$('run-materials-status').textContent.includes('不可用'),'synthetic catalog omission keeps locked original ID without stale name; no revocation claim');
  await action('run-submit-recover');check(posts().length===2&&JSON.stringify(posts()[1].body)===JSON.stringify(original)&&posts()[1].response.run_id===posts()[0].response.run_id,'explicit recovery returns same durable Run with exact original material/body/key');
  check(w.eval('runSubmissionEntry().state')==='accepted'&&!$('run-materials').disabled,'known acceptance unlocks editing for a separately explicit next task');
 }
 assert.equal((await rpc({command:'verify',case:info.case})).status,200);
}
(async()=>{let status='FAIL',error;try{await boot();await flow();status='PASS';}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}finally{
 if(release){release();release=null;}try{await wait(()=>active===0&&pending.size===0,'HTTP drained');dom?.window.close();}catch(e){error=error||e.stack;process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,case:info.case,checks,observations,requests,assets,mutations,scope:'Actual served JS/JSDOM + authenticated ASGI synthetic SQLite. Two labelled response-delivery controls; no actual revocation. Mock Worker only in use; no real model/native/PG.'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');}})();
