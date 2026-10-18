'use strict';
// Actual served page and ASGI IPC; synthetic data, never native-browser qualification.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[];
let serial=0,dom,w,$,boots=0;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);fs.writeFileSync(info.output+'.live.json',JSON.stringify({status:'RUNNING',checks,requests,assets,boots},null,2)+'\n');};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(value,type='click'){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible '+value);assert(!el.matches(':disabled'),'enabled '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=suffix=>requests.filter(r=>r.method==='POST'&&r.path.endsWith(suffix));
const nav=tab=>action(w.document.querySelector(`[data-tab="${tab}"]`));
async function open(){await nav('apps');const entry=[...$('use-list').children].find(x=>x.dataset.instanceId===info.instance);assert(entry);await action(entry.querySelector('button'));}
async function boot(){
 if(dom)dom.window.close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const r={path,method:options.method||'GET',body:options.body?JSON.parse(options.body):undefined};requests.push(r);const response=await rpc({...r,headers:options.headers});r.status=response.status;r.response=JSON.parse(response.text);return new Response(response.text,{status:response.status,headers:{'Content-Type':response.content_type||'application/json'}});};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await open();
}
async function editGoal(version){
 await action('csv-goal-edit');check(visible($('goal-card-goal')),'original Goal editor used for v'+version);
 $('goal-card-title').value='保留 amount 的目标 v'+version;$('goal-card-goal').value='汇总 amount，保留材料、列和历史 v'+version;
 $('goal-card-acceptance_checks').value=info.acceptance+'\n'+info.newCheck+' v'+version;
 await action('goal-card-save');check($('goal-card-status').textContent.includes('v'+version),'same card explicitly saves next Goal v'+version);
 await open();await action('csv-goal-baseline');
 $('csv-goal-from').value='amount';$('csv-goal-to').value='amount';await action('csv-goal-to','change');
 check(!$('csv-goal-preview').disabled,'new content permits explicit amount to amount v'+version);
}
function previewProof(){const r=posts('/csv-goal-revisions/previews').at(-1);assert.equal(r.status,201);return r.response;}
(async()=>{
 let status='FAIL',error;
 try{
  await boot();
  if(!info.continuation){
  check(posts('/previews').length===0&&posts('/checks').length===0,'opening existing instance submits no revision');
  await editGoal(2);const count=posts('/previews').length,sending=action('csv-goal-preview');$('csv-goal-preview').click();await sending;
  check(posts('/previews').length===count+1,'double click creates one explicit preview');
  const preview=previewProof(),goalNode=preview.baseline_graph.graph.nodes.find(n=>n.kind==='GOAL');
  check(preview.baseline_input.column==='amount'&&preview.input.column==='amount'&&preview.impact.changed_nodes.join()===goalNode.id,'initial selected baseline column retained and only Goal marked explicit change');
  check(preview.impact.revalidation_scope==='APP'&&preview.impact.revalidation_nodes.length===preview.baseline_graph.graph.nodes.length,'original unknown application scope fully revalidated');
  check(preview.effective_candidate.manifest.input_schema.properties.column.enum.join()==='amount'&&preview.effective_candidate.actions[0].executor.ref==='data.aggregate_csv','exact preview shows first binding restriction and original tool');
  check($('csv-goal-check').disabled,'CHECK requires its own explicit consent');await action('csv-goal-check-ack');await action('csv-goal-check');
  const queued=posts('/csv-goal-revisions/checks').at(-1);check(queued.status===202&&posts('/csv-goal-revisions/checks').length===1,'one original isolated CHECK queued');
  assert.equal((await rpc({command:'worker',run:queued.response.run_id})).status,200);await action('csv-goal-outcome');
  check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"')&&$('csv-goal-revision-status').textContent.includes('人工 PENDING'),'actual CHECK PASS remains separate from human acceptance');
  await action('csv-goal-version');check($('csv-goal-release').disabled,'new immutable Release separately confirmed');await action('csv-goal-release-ack');await action('csv-goal-release');
  check(posts('/adoption-approvals').length===0&&$('csv-goal-adopt').disabled,'saving Release does not adopt old instance');
  await action('csv-goal-adopt-prepare');await action('csv-goal-adopt-ack');await action('csv-goal-adopt');
  check(w.eval('applicationUse.id')===info.instance&&$('use-info').textContent.includes('Goal v2')&&[...$('use-column').options].map(o=>o.value).join()==='amount','same instance adopts new Goal while keeping fixed amount');
  await action('use-csv-review-optin');await action('use-submit');const run=w.eval('applicationUse.selected');assert(run);
  assert.equal((await rpc({command:'worker',run})).status,200);await action('use-refresh');
  check($('use-output').textContent.includes('amount 合计 30')&&$('use-output').textContent.includes(run),'new actual Run returns original calculation under new Goal');
  await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING'),'new Run owner declaration remains PENDING');
  assert.equal((await rpc({command:'delivery-proof',run,preview_key:preview.request_key})).status,200);
  const totalPost=requests.filter(r=>r.method==='POST').length;await boot();
  check(requests.filter(r=>r.method==='POST').length===totalPost&&$('use-info').textContent.includes('Goal v2'),'cold page reads adopted version without POST');
  }else{
   check($('use-info').textContent.includes('Goal v2')&&requests.every(r=>r.method==='GET'),'same original database cold page reads adopted Goal v2 without writes');
   const fresh=[...$('use-history').children].find(n=>n.textContent.includes(info.newRun.slice(0,18))&&n.querySelector('button'));assert(fresh);await action(fresh.querySelector('button'));await action('csv-owner-read');
   check($('use-output').textContent.includes('amount 合计 30')&&$('csv-owner-status').textContent.includes('PENDING'),'same new Run cold read retains amount 30 and separate PENDING');
   assert.equal((await rpc({command:'delivery-proof',run:info.newRun})).status,200);
  }
  const old=[...$('use-history').children].find(n=>n.textContent.includes(info.old.slice(0,18))&&n.querySelector('button'));assert(old);await action(old.querySelector('button'));await action('csv-owner-read');
  check($('csv-owner-status').textContent.includes('STALE')&&$('csv-owner-history').textContent.includes('ACCEPTED'),'old accepted record retained while current-owner gate correctly marks it STALE');
  await open();
  await action('csv-goal-next');await action('csv-goal-baseline');
  $('csv-goal-to').value='amount';await action('csv-goal-to','change');check($('csv-goal-preview').disabled,'unchanged adopted Goal plus same column is disabled');
  assert.equal((await rpc({command:'noop-proof'})).status,200);
  await editGoal(3);await action('csv-goal-preview');const next=previewProof();
  check(next.namespace==='csv-column-revision.v2'&&next.context.parent.column==='amount'&&next.spec_revision===3,'existing successive revision accepts next Goal with fixed parent binding');
  const nextGoal=next.parent_graph.graph.nodes.find(n=>n.kind==='GOAL');
  check(next.impact.changed_nodes.join()===nextGoal.id&&next.impact.revalidation_scope==='APP'&&next.input.column==='amount','successive request changes only Goal and keeps conservative application checks');
  assert.equal((await rpc({command:'final-proof',key:next.request_key})).status,200);status='PASS';
 }catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(dom)dom.window.close();fs.writeFileSync(info.output,JSON.stringify({status,error,checks,requests,assets,boots,scope:'Actual ASGI TestClient and served page in JSDOM; synthetic CSV capability and explicit NoModel Workers; synthetic old ACCEPTED is not human validation',real_model:'NOT_RUN',native_browser:'NOT_RUN',windows:'NOT_RUN',pg:'NOT_RUN',remote_ci:'NOT_RUN',new_lock_scenario:'NOT_RUN'},null,2)+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
