'use strict';
// Served product page + real ASGI HTTP. Blob/anchor adapter is not browser download acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[],blobs=[],anchors=[];
let serial=0,dom,w,$,active=0,action=null,releaseRead=null,failClick=false;
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
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
const runPath=id=>`/api/internal/instances/${info.instance}/runs/${id}`;
const card=(index=1)=>$('internal-data').querySelector(`[data-literal-run="${info.outputs[index].id}"]`);
const button=(index=1)=>card(index)?.querySelector('button');
async function readonly(){assert.equal((await rpc({command:'readonly'})).status,200);}
async function connect(identity='synthetic-test-A'){
 if($('connect').hidden||!visible($('connect')))await click('identity-switch');
 $('token').value=identity;await click('connect');await nav('apps');
}
async function open(id=info.instance){
 const entry=$('use-list').querySelector(`[data-use-family="LITERAL_TEXT"][data-app-id="${info.app}"] button`);assert(entry);await click(entry);
 const row=[...$('internal-instances').children].find(r=>r.textContent.includes(id));assert(row);await click(row.querySelector('button'));
 check(w.eval('engineering.instance.id')===id,'explicit saved instance '+id);
}
async function selectRun(index){
 const id=info.outputs[index].id,row=[...$('internal-runs').children].find(r=>r.textContent.includes(id));assert(row);await click(row.querySelector('button'));
 assert.equal(w.eval('engineering.run.id'),id);
}
async function setup(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;w.Blob=Blob;
 w.URL.createObjectURL=blob=>{const url='blob:synthetic-'+blobs.length;blobs.push({url,blob,revoked:false});return url;};
 w.URL.revokeObjectURL=url=>{const record=blobs.find(r=>r.url===url);assert(record);record.revoked=true;};
 w.HTMLAnchorElement.prototype.click=function(){if(failClick)throw Error('synthetic anchor failure');anchors.push({url:this.href,filename:this.download});};
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,cache:options.cache,no_body:options.body===undefined};requests.push(request);
  const mode=action&&path===runPath(info.outputs[1].id)?action:null;if(mode)action=null;
  try{
   if(mode?.before)await new Promise(resolve=>{releaseRead=resolve;});
   const r=await rpc({...request,headers:options.headers});request.actual_status=r.status;
   if(mode?.hold)await new Promise(resolve=>{releaseRead=resolve;});
   if(mode?.transport)throw TypeError('synthetic transport loss after actual GET');
   let body=r.text;if(mode?.mutate){const value=JSON.parse(body);mode.mutate(value);body=JSON.stringify(value);request.mutation=mode.label;}
   return new Response(body,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 await connect();await open();await readonly();
 check($('internal-data').querySelectorAll('[data-literal-run]').length===3,'three real successful versions have explicit download controls');
 check(!$('internal-data').querySelector('em'),'complete HTML quote remains literal text');
}
async function captured(index,output){
 await wait(()=>blobs[index]?.revoked,'Blob URL cleanup');
 const bytes=Buffer.from(await blobs[index].blob.arrayBuffer()),expected={instance_id:info.instance,run_id:output.id,release_id:output.release_id,result_version:output.result_version,result:output.result};
 assert.deepEqual(bytes,Buffer.from(JSON.stringify(expected,null,2)+'\n','utf8'));
 assert.equal(blobs[index].blob.type,'application/json;charset=utf-8');
 assert(anchors.some(a=>a.url===blobs[index].url&&a.filename===`literal-${info.instance}-${output.id}-v${output.result_version}.json`));
 assert(!bytes.includes(Buffer.from('synthetic-test-A'))&&!Object.hasOwn(JSON.parse(bytes),'events')&&!Object.hasOwn(JSON.parse(bytes),'app_run_id'));
 fs.writeFileSync(info.output.replace('result.json',`captured-blob-${index}.json`),bytes);
 check(true,'exact whitelist UTF-8 Blob bytes, full citations and filename v'+output.result_version);
}
async function reject(label,mutate){
 const before=blobs.length,n=requests.length;action={label,mutate};await click(button());
 check(blobs.length===before&&card().textContent.includes('未下载文件'),label+' rejects before Blob');
 check(requests.length===n+1&&requests[n].path===runPath(info.outputs[1].id)&&requests[n].actual_status===200,label+' tests a mutated actual200 GET response');
}
async function bytes(){
 let n=requests.length;const work=click(button());button().click();await work;await captured(0,info.outputs[1]);
 check(requests.length===n+1&&requests[n].cache==='no-store','double click yields one fresh no-store Run GET');
 await click(button());await captured(1,info.outputs[1]);check(requests.length===n+2,'each later explicit download reauthorizes');
 await click(button(0));await captured(2,info.outputs[0]);await click(button(2));await captured(3,info.outputs[2]);
 const changes={
  'wrong instance':v=>v.instance_id=info.other_instance,'wrong normal Run':v=>v.id=info.outputs[0].id,
  'wrong typed AppRun':v=>v.app_run_id='iapprun_synthetic_wrong','wrong Release':v=>v.release_id='irelease_synthetic_wrong',
  'wrong result version':v=>v.result_version=1,'non-success fresh status':v=>v.status='FAILED',
  'missing typed evidence':v=>v.known_effects=[],'wrong typed instance':v=>v.known_effects[0].instance_id=info.other_instance,
  'wrong typed Release':v=>v.known_effects[0].release_id='irelease_synthetic_wrong','wrong typed version':v=>v.known_effects[0].version=1,
  'changed source hash':v=>{v.result.source_hash='a'.repeat(64);v.known_effects[0].data.result.source_hash='a'.repeat(64);},
  'changed term':v=>{v.result.term='Alpha';v.known_effects[0].data.result.term='Alpha';},
  'changed complete quote':v=>{v.result.citations[0].quote='truncated';v.known_effects[0].data.result.citations[0].quote='truncated';},
  'inconsistent typed result':v=>v.known_effects[0].data.result.revision=2,
  'wrong semantic status':v=>{v.result.semantic_status='PASS';v.known_effects[0].data.result.semantic_status='PASS';},
 };
 for(const [label,mutate]of Object.entries(changes))await reject(label,mutate);
 const before=blobs.length;action={transport:true};await click(button());check(blobs.length===before,'lost GET creates no Blob');
 failClick=true;await click(button());failClick=false;await wait(()=>blobs.at(-1).revoked,'failed anchor cleanup');
 check(blobs.length===before+1&&anchors.length===4&&!w.document.querySelector('a[download]'),'failed anchor removes link and revokes URL');
 await click(button());await captured(blobs.length-1,info.outputs[1]);check(w.eval('literalResultDownloads.size')===0,'all failed requests release deduplication lock');
 await readonly();
}
async function navigation(){
 const changes={
  workspace:async()=>{await nav('resources');await nav('apps');},
  Run:async()=>{await selectRun(0);await selectRun(1);},
  instance:async()=>{await open(info.other_instance);await open();},
  project:async()=>{for(const project of [info.other,info.project]){$('project-select').value=project;await $('project-select').onchange(new w.Event('change'));}await open();},
  identity:async()=>{await connect('synthetic-test-B');await connect();await open();},
  'same account reconnect':async()=>{await connect();await open();},
  'refresh and repeat click':async()=>{await click('internal-refresh');const n=requests.length;await click(button());check(requests.length===n,'redrawn control shares pending download lock');},
 };
 for(const [label,change]of Object.entries(changes)){
  const before=blobs.length;action={hold:true};const work=click(button());await wait(()=>!!releaseRead,'held real GET200');
  await change();const release=releaseRead;releaseRead=null;release();await work;
  check(blobs.length===before,label+' away/back isolates late result before Blob');
  check(w.eval('literalResultDownloads.size')===0,label+' releases old lock');await readonly();
 }
 await click(button());await captured(0,info.outputs[1]);
}
async function revocation(){
 action={before:true};const work=click(button());await wait(()=>!!releaseRead,'download held before authorization');
 assert.equal((await rpc({command:'revoke'})).status,200);const release=releaseRead;releaseRead=null;release();await work;
 check(requests.at(-1).actual_status===403,'explicit download receives real403 after controlled revoke');
 check(blobs.length===0&&anchors.length===0,'revoked result never creates Blob');
 check(!$('internal-data').textContent&&!$('internal-runs').textContent&&!$('internal-instances').textContent&&$('internal-run-form').hidden,'403 clears protected results and controls');
 check(w.eval('literalResultDownloads.size')===0,'403 releases lock');await readonly();
}
(async()=>{
 let status='FAIL',error;
 try{await setup();if(info.scenario==='bytes')await bytes();else if(info.scenario==='navigation')await navigation();else await revocation();
  await wait(()=>active===0&&pending.size===0,'HTTP drained');await wait(()=>blobs.every(b=>b.revoked),'all Blob URLs released');
  check(requests.every(r=>r.method==='GET'&&r.no_body),'all product actions read only; no Run or Grant write');
  check(!w.document.querySelector('a[download]'),'temporary anchors removed');status='PASS';
 }catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await wait(()=>active===0&&pending.size===0,'final drain');}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,requests,assets,anchors,
   blobs:await Promise.all(blobs.map(async b=>({sha256:crypto.createHash('sha256').update(Buffer.from(await b.blob.arrayBuffer())).digest('hex'),revoked:b.revoked}))),
   scope:'actual synthetic ASGI HTTP, full served JS in JSDOM, Node Blob bytes, cold SQLite NoModel Worker',
   native_browser:'NOT_RUN',pg:'NOT_RUN',real_model:'NOT_RUN'},null,2)+'\n');dom?.window.close();
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
