'use strict';
// Product page + actual ASGI HTTP via IPC. JSDOM is not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[];
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=()=>requests.filter(r=>r.method==='POST');
const entry=()=>$('use-list').querySelector(`[data-use-family="CLOSED_TEXT_WORKFLOW"][data-app-id="${info.app}"] button`);
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;if(request.method==='POST'||/\/runs\/run_/.test(path))request.response=JSON.parse(r.text);
   if(hold&&path===hold.path&&--hold.remaining===0){hold=null;await new Promise(resolve=>{releaseRead=resolve;});}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');await nav('apps');
 await wait(()=>!!entry(),'closed text directory entry');
}
async function open(){await click(entry());check(w.eval('engineering?.workflow')&&visible($('internal-panel')),'directory opens existing four-step controller');
 const row=[...$('internal-instances').children].find(r=>r.textContent.includes(info.instance));assert(row);await click(row.querySelector('button'));
 check(w.eval('engineering.instance.id')===info.instance&&visible($('internal-workflow-a'))&&visible($('internal-workflow-b')),'explicit instance selection exposes two terms and report input');
}
async function readonly(){assert.equal((await rpc({command:'readonly'})).status,200);}
async function use(){
 check(posts().length===0&&!requests.some(r=>r.path===`/api/apps/${info.app}`),'cold directory is metadata-only without implicit open or write');
 const description=entry().parentElement.textContent;
 check(['四步文本流程','固定 TXT/MD','PARTIAL','0 模型请求','未发布','人工 PENDING'].every(s=>description.includes(s)),'directory states supported scope and pending acceptance');
 check($('app-list').textContent.includes('四步文本流程'),'draft list uses same classification');
 check(info.unsupported.every(id=>!$('use-list').querySelector(`[data-app-id="${id}"]`))&&!requests.some(r=>info.unsupported.some(id=>r.path===`/api/apps/${id}`)),'unsupported namespace/check are neither offered nor inspected');
 await readonly();await open();check(posts().length===0,'explicit open and instance selection are read-only');await readonly();
 const runs=[];
 for(const emit of [true,false]){
  for(const [side,term] of [['a',emit?'Violet':'Amber'],['b',emit?'Amber':'Violet']]){$('internal-workflow-'+side).value=term;$('internal-workflow-'+side).dispatchEvent(new w.Event('input',{bubbles:true}));}
  $('internal-workflow-report').checked=emit;$('internal-workflow-report').dispatchEvent(new w.Event('change',{bubbles:true}));
  const n=posts().length,work=click('internal-run-submit');$('internal-run-submit').click();await work;
  check(posts().length===n+1&&posts().at(-1).path===`/api/internal/instances/${info.instance}/runs`,'explicit double click accepts one existing Run POST');
  const input=posts().at(-1).body.input;check(input.term_a===(emit?'Violet':'Amber')&&input.term_b===(emit?'Amber':'Violet')&&input.emit_report===emit,'exact two terms and boolean reach original controller');
  const id=w.eval('engineering.run.id');runs.push(id);assert.equal((await rpc({command:'worker'})).status,200);await click('internal-refresh');
  const state=emit?'SUCCEEDED':'PARTIAL',run=w.eval('engineering.run');check(run.id===id&&run.status===state&&run.steps.length===4,'same Run exposes actual four step receipts and '+state);
  check(run.steps.slice(0,3).every(s=>s.status==='VERIFIED')&&run.steps[3].status===(emit?'VERIFIED':'SKIPPED'),'report branch preserves existing step semantics');
  if(emit)check(run.result.term_a==='Violet'&&run.result.citations_a.length===1&&run.result.citations_b.length===2&&run.result_version===1,'actual complete source citations persisted in result v1');
  else check(run.result===null&&run.result_version===null,'PARTIAL current Run never borrows previous success');
  check($('internal-data').textContent.includes('历史结果 v1')&&!$('internal-data').textContent.includes('历史结果 v2'),'successful history retained without extra partial result');
  check($('owner-status').textContent.includes('PENDING')&&$('owner-form').hidden,'existing manual status remains pending without unsupported declaration form');await readonly();
 }
 check(runs[0]!==runs[1],'different explicit inputs use distinct Runs');
 const before=posts().length;await boot();await open();await readonly();
 check(posts().length===before,'cold page reopens saved history with zero writes');
 check(runs.every(id=>$('internal-runs').textContent.includes(id))&&$('internal-data').textContent.includes('历史结果 v1'),'cold directory reaches both original Runs and saved v1');
 const partial=[...$('internal-runs').children].find(r=>r.textContent.includes(runs[1]));await click(partial.querySelector('button'));
 check(w.eval('engineering.run.id')===runs[1]&&w.eval('engineering.run.status')==='PARTIAL'&&!w.eval('engineering.run.result'),'explicit partial history opens same Run with no borrowed result');await readonly();
}
async function guards(){
 await readonly();
 for(const scenario of [
  {path:`/api/apps/${info.app}`,remaining:2,change:async()=>{await nav('resources');await nav('apps');},label:'second app read workspace ABA'},
  {path:`/api/internal/apps/${info.app}/instances`,remaining:1,change:async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');},label:'instance list same-account reconnect'},
  {path:`/api/apps/${info.app}`,remaining:1,change:async()=>{
   for(const project of [info.other,info.project]){$('project-select').value=project;await $('project-select').onchange(new w.Event('change'));}
  },label:'initial app read project ABA'},
 ]){
  hold={path:scenario.path,remaining:scenario.remaining};const opening=click(entry());await wait(()=>!!releaseRead,'held '+scenario.label);
  await scenario.change();const release=releaseRead;releaseRead=null;release();await opening;
  check(!w.eval('engineering')&&!$('internal-data').textContent&&!$('internal-instances').textContent,scenario.label+' rejects late open chain');
  check(posts().length===0,scenario.label+' performs no write');await readonly();
 }
 await open();hold={path:`/api/internal/instances/${info.instance}`,remaining:1};
 const first=[...$('internal-instances').children].find(r=>r.textContent.includes(info.instance));const opening=click(first.querySelector('button'));await wait(()=>!!releaseRead,'held instance read');
 const second=[...$('internal-instances').children].find(r=>r.textContent.includes(info.second_instance));await click(second.querySelector('button'));
 const release=releaseRead;releaseRead=null;release();await opening;
 check(w.eval('engineering.instance.id')===info.second_instance,'late original instance cannot replace explicit second selection');await readonly();
 // A malicious discovery hint must not bypass the authoritative app family.
 const fake=JSON.parse(JSON.stringify((await rpc({method:'GET',path:'/api/apps?metadata_only=true'}))));
 const items=JSON.parse(fake.text).items.filter(r=>r.project_id===info.project);const csv=items.find(r=>r.id===info.csv_app);assert(csv);csv.use_family='CLOSED_TEXT_WORKFLOW';
 await w.refreshApplicationUse(items);
 const wrong=$('use-list').querySelector(`[data-use-family="CLOSED_TEXT_WORKFLOW"][data-app-id="${info.csv_app}"] button`);assert(wrong);await click(wrong);
 check($('error').textContent==='VERSION_CONFLICT'&&!w.eval('engineering'),'misleading metadata cannot open CSV as a four-step app');
 await w.refreshApps();await open();await readonly();
 const before=requests.length;assert.equal((await rpc({command:'revoke'})).status,200);
 await click(entry());
 check(requests.slice(before).some(r=>r.path===`/api/apps/${info.app}`&&r.status===403),'stale directory entry reauthorizes and receives real403 after explicit revoke');
 check(!w.eval('engineering')&&!$('internal-data').textContent&&!$('internal-instances').textContent,'revoked open leaves no protected cached content');
 check(posts().length===0,'all navigation, rejected hints and revoked opens create zero Run or grant POST');await readonly();
}
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='use')await use();else await guards();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,requests,assets,boots,
   scope:'Actual ASGI TestClient HTTP + full served JS in JSDOM, cold SQLite NoModel four-step Worker',pg:'NOT_RUN',native_browser:'NOT_RUN',real_model:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
