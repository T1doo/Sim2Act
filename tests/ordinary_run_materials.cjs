'use strict';
// Full served JS and authenticated ASGI; synthetic SQLite/mock, not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),requests=[],checks=[],assets=[],observations=[],pending=new Map();
let serial=0,active=0,dom,w,$,hold=null,release=null,lose=false;
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
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);$('goal').value='读取明确选择的这一份合成材料';
}
async function flow(){
 const target=info.materials[5],path=`/api/projects/${info.project}/runs`;
 if(info.case==='use'){
  if($('run-materials')){
   check($('run-materials').multiple&&$('run-materials').options.length===9&&chosen().length===0,'nine eligible materials are visible and none implicitly attached');
   check(!$('run-submit').disabled,'zero explicitly attached materials is a valid UI choice');
   await choose(info.materials.slice(0,8).map(m=>m.id));check(!$('run-submit').disabled&&chosen().length===8,'eight selected materials remain explicit without truncation');
   await choose(info.materials.map(m=>m.id));const count=posts().length;check($('run-submit').disabled&&chosen().length===9,'ninth selection is preserved but submission is disabled');
   $('run-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setImmediate(r));check(posts().length===count,'over-limit submit is rejected locally with zero POST');
   await choose([target.id]);
  }
  await action('run-submit');const sent=posts().filter(r=>r.path===path).at(-1);observations.push({kind:'actual_submission',picker_present:!!$('run-materials'),request:sent});
  if(sent.status!==202)assert.equal((await rpc({command:'rejected-readonly'})).status,200);
  check(sent.status===202,'project with nine materials can actually submit a one-material Run');
  check(sent.body.resource_refs.length===1&&sent.body.resource_refs[0]===target.id,'POST contains only explicitly selected material');
  const rid=sent.response.run_id;assert.equal((await rpc({command:'worker',run:rid,resource:target.id})).status,200);
  await action('run-history-refresh');await action($('runs').querySelector('button'));
  const result=JSON.parse($('raw-result').textContent);check(result.id===rid&&result.resource_refs.length===1&&result.resource_refs[0]===target.id,'actual persistent Run and frozen input retain selected ID only');
  check(result.status==='PARTIAL'&&result.result.mode==='MOCK'&&result.result.receipts[0].data.content===target.content,'normal mock Worker reads selected text; whole-goal acceptance is not promoted');
  check(info.materials.filter(m=>m.id!==target.id).every(m=>!$('raw-result').textContent.includes(m.content)),'unselected material bodies are absent from selected Run readback');
  check(posts().filter(r=>r.path===path).length===1,'entire selected-input execution has one explicit Run POST');
 }else if(info.case==='refresh'){
  await choose([target.id]);const before=posts().length;assert.equal((await rpc({command:'new-material'})).status,200);await action('run-history-refresh');
  check($('run-materials').options.length===10&&chosen().length===1&&chosen()[0]===target.id,'newly authorized tenth material appears without automatic selection');
  hold={method:'GET',path:`/api/projects/${info.project}/resources`};const delayed=action('run-history-refresh');await wait(()=>!!release,'old material list held');
  await project(info.other);check(chosen().length===0&&!$('run-materials').textContent.includes(target.name),'project switch clears old material selection and labels');
  await project(info.project);check(chosen().length===0,'return to A starts with no silently restored material selection');
  const deliver=release;release=null;deliver();await delayed;check(chosen().length===0,'late old material list cannot restore prior selection');
  await choose([target.id]);await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');
  check(chosen().length===0&&!$('run-materials').textContent.includes(target.name),'identity switch clears prior choices and protected names');
  check(posts().length===before,'all selection/list/navigation operations issue zero product POST');
 }else{
  await choose([target.id]);lose=true;hold={method:'POST',path};const started=action('run-submit');await wait(()=>!!release,'actual accepted Run reply held');
  $('run-form').dispatchEvent(new w.Event('submit',{cancelable:true}));await new Promise(r=>setImmediate(r));check(posts().length===1&&$('run-materials').disabled,'sending locks picker and blocks a duplicate submit');
  const deliver=release;release=null;deliver();await started;check(w.eval('runSubmissionEntry().state')==='unknown'&&$('run-materials').disabled,'lost actual receipt preserves UNKNOWN and locked selection');
  const original=structuredClone(posts()[0].body);assert.equal((await rpc({command:'new-material'})).status,200);await action('run-history-refresh');
  check(chosen().length===1&&chosen()[0]===target.id&&JSON.stringify(w.eval('runSubmissionEntry().body'))===JSON.stringify(original),'refresh with new material preserves frozen selection/body/key');
  await action('run-submit-recover');check(posts().length===2&&JSON.stringify(posts()[1].body)===JSON.stringify(original)&&posts()[1].response.run_id===posts()[0].response.run_id,'explicit recovery returns same durable Run with exact original material/body/key');
  check(w.eval('runSubmissionEntry().state')==='accepted'&&!$('run-materials').disabled,'known acceptance unlocks editing for a separately explicit next task');
 }
 assert.equal((await rpc({command:'verify',case:info.case})).status,200);
}
(async()=>{let status='FAIL',error;try{await boot();await flow();status='PASS';}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}finally{
 if(release){release();release=null;}try{await wait(()=>active===0&&pending.size===0,'HTTP drained');dom?.window.close();}catch(e){error=error||e.stack;process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,case:info.case,checks,observations,requests,assets,scope:'Actual served JS/JSDOM + authenticated ASGI synthetic SQLite. Mock Worker only in use; no real model/native/PG.'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');}})();
