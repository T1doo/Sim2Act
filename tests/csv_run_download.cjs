'use strict';
// Real loopback API + loaded product JS. Blob/anchor capture is a DOM adapter,
// never native browser download, PG, or the four-step ordinary-user acceptance.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {createHash,randomUUID}=require('node:crypto'),{JSDOM}=require('jsdom');
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,'info.json')));
const checks=[],requests=[],blobs=[],anchors=[];let w,$,dom,mode=null,finishRead=null,failClick=false;
const state={pending:0,actions:new Set(),errors:[]};
const check=(ok,name)=>{assert.ok(ok,name);checks.push(name);};
const wait=async(fn,name)=>{const until=Date.now()+8000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error('Timeout '+name);};
const idle=()=>wait(()=>state.pending===0&&state.actions.size===0,'HTTP and UI actions complete');
const navigationIdle=()=>wait(()=>state.pending===(finishRead?1:0)&&state.actions.size===(finishRead?1:0),'navigation complete apart from held download');
function trackHandlers(){
 for(const name of ['onclick','onchange','onsubmit']){
  const descriptor=Object.getOwnPropertyDescriptor(w.HTMLElement.prototype,name);
  Object.defineProperty(w.HTMLElement.prototype,name,{...descriptor,set(fn){descriptor.set.call(this,typeof fn==='function'?function(...args){
   const value=fn.apply(this,args);
   if(value?.then){const promise=Promise.resolve(value);state.actions.add(promise);promise.then(()=>state.actions.delete(promise),error=>{state.errors.push(error);state.actions.delete(promise);});}
   return value;
  }:fn);}});
 }
 w.addEventListener('error',e=>state.errors.push(e.error||Error(e.message)));
}
const runPath=id=>`/api/internal/instances/${info.instance}/runs/${id}`;
const button=()=>[...$('use-output').querySelectorAll('button')].find(b=>b.textContent==='下载此运行结果 JSON');
async function connect(identity='synthetic-test-A'){
 $('token').value=identity;$('connect').click();
 await wait(()=>$('project-select').selectedOptions[0]?.textContent===(identity==='synthetic-test-B'?'Other identity project':'中文 空格工程'),'connect identity');
 await navigationIdle();
}
async function openInstance(id=info.instance){
 const row=[...$('use-list').children].find(r=>r.textContent.includes(id.slice(0,18)));
 assert(row,'directory instance visible');row.querySelector('button').click();
 await wait(()=>w.eval('applicationUse?.id')===id&&!$('use-form').hidden,'open directory instance');
 await navigationIdle();
}
async function selectRun(id){
 const row=[...$('use-history').children].find(r=>r.textContent.startsWith(id.slice(0,18)));
 assert(row,'history Run visible');row.querySelector('button').click();
 await wait(()=>$('use-output').textContent.includes(id),'selected Run rendered');
 await navigationIdle();
}
async function setup(){
 dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:'dangerously'});w=dom.window;$=id=>w.document.getElementById(id);
 trackHandlers();w.setInterval=()=>0;w.crypto.randomUUID=randomUUID;w.Blob=Blob;
 w.URL.createObjectURL=blob=>{const url='blob:synthetic-'+blobs.length;blobs.push({url,blob,revoked:false});return url;};
 w.URL.revokeObjectURL=url=>{const record=blobs.find(r=>r.url===url);assert(record);record.revoked=true;};
 w.HTMLAnchorElement.prototype.click=function(){if(failClick)throw Error('synthetic anchor failure');anchors.push({url:this.href,filename:this.download});};
 w.fetch=async(url,options={})=>{
  state.pending++;try{
   const target=new URL(url,info.base);assert.equal(target.origin,info.base);
   const entry={method:options.method||'GET',path:target.pathname,no_body:options.body===undefined,cache:options.cache};requests.push(entry);
   const exact=/^\/api\/internal\/instances\/[^/]+\/runs\/[^/]+$/.test(target.pathname);
   const action=exact?mode:null;if(action)mode=null;
   if(action?.before)await new Promise(resolve=>{finishRead=resolve;});
   const response=await fetch(target,options);entry.actual_status=response.status;
   let body=await response.text();
   if(action?.hold)await new Promise(resolve=>{finishRead=resolve;});
   if(action?.transport)throw TypeError('synthetic network failure after actual GET');
   if(action?.mutate){const value=JSON.parse(body);action.mutate(value);body=JSON.stringify(value);}
   return new Response(body,{status:action?.status||response.status,headers:response.headers});
  }finally{state.pending--;}
 };
 for(const name of ['app.js','internal.js','protocol.js','use.js']){
  const text=await(await fetch(info.base+'/'+name)).text();
  assert.equal(createHash('sha256').update(text).digest('hex'),info.web_hashes[name]);
  const script=w.document.createElement('script');script.textContent=text;w.document.body.append(script);
 }
 await connect();w.selectWorkspace('apps');await openInstance();await idle();
 check(!button(),'no selected Run has no download');
 await selectRun(info.runs[2]);await idle();check(!button(),'failed Run has no download');
 await selectRun(info.runs[1]);await idle();assert(button());
}
async function captured(index,output){
 await wait(()=>blobs[index]?.revoked,'Blob URL promptly revoked');
 const bytes=Buffer.from(await blobs[index].blob.arrayBuffer());
 const expected={instance_id:info.instance,run_id:output.id,release_id:output.release_id,result_version:output.result_version,
  result:{resource_id:output.result.resource_id,column:output.result.column,sum:output.result.sum,count:output.result.count}};
 assert.deepEqual(bytes,Buffer.from(JSON.stringify(expected,null,2)+'\n','utf8'));
 assert.equal(blobs[index].blob.type,'application/json;charset=utf-8');
 assert.deepEqual(JSON.parse(bytes),expected);assert.equal(typeof JSON.parse(bytes).result.sum,'string');
 assert(!bytes.includes(Buffer.from('PRIVATE_SYNTHETIC_ROW'))&&!bytes.includes(Buffer.from('synthetic-test-A')));
 assert(anchors.some(a=>a.url===blobs[index].url&&a.filename===`sim2act-${info.instance}-${output.id}-v${output.result_version}.json`));
 fs.writeFileSync(path.join(root,`captured-blob-${index}.json`),bytes);
 check(true,`exact whitelist UTF-8 Blob bytes, string sum and matching filename v${output.result_version}`);
}
async function reject(action,label){
 const before=blobs.length,n=requests.length;mode=action;button().click();await idle();
 check(blobs.length===before&&$('use-output').textContent.includes('未下载文件'),label+' rejects without Blob');
 check(requests.length===n+1&&requests[n].path===runPath(info.runs[1])&&requests[n].method==='GET',label+' uses one actual authenticated GET');
}
async function versions(){
 let n=requests.length;button().click();button().click();await idle();await captured(0,info.outputs[1]);
 check(requests.length===n+1&&requests[n].path===runPath(info.runs[1])&&requests[n].cache==='no-store','v2 duplicate click yields one fresh no-store GET');
 button().click();await idle();await captured(1,info.outputs[1]);check(requests.length===n+2,'each later explicit click reads server again');
 await selectRun(info.runs[0]);await idle();button().click();await idle();await captured(2,info.outputs[0]);
 check(JSON.parse(await blobs[2].blob.text()).result.sum==='9007199254740993.123456790','historical v1 retains exact digits beyond JS Number precision');
 await selectRun(info.runs[1]);await idle();
 const changes={
  'wrong instance':v=>v.instance_id=info.other_instance,'wrong Run':v=>v.id=info.runs[0],
  'wrong typed AppRun':v=>v.app_run_id='iapprun_synthetic_wrong','wrong Release':v=>v.release_id='irelease_synthetic_wrong',
  'wrong result version':v=>v.result_version=1,'failed fresh status':v=>v.status='FAILED',
  'missing result':v=>v.result=null,'changed sum':v=>v.result.sum='0.4',
  'numeric sum':v=>v.result.sum=0.3,'changed resource':v=>v.result.resource_id='res_synthetic_wrong',
  'changed column':v=>v.result.column='amount','changed count':v=>v.result.count=3,
  'missing typed evidence':v=>v.known_effects=[],'wrong typed record binding':v=>v.known_effects[0].run_id='iapprun_synthetic_wrong',
  'wrong typed instance':v=>v.known_effects[0].instance_id=info.other_instance,
  'wrong typed Release':v=>v.known_effects[0].release_id='irelease_synthetic_wrong',
  'wrong typed version':v=>v.known_effects[0].version=1,'inconsistent typed result':v=>v.known_effects[0].data.result.sum='999',
 };
 for(const [label,mutate]of Object.entries(changes))await reject({mutate},label);
 await reject({transport:true},'lost GET');
 const before=blobs.length;failClick=true;button().click();await idle();failClick=false;
 await wait(()=>blobs.at(-1).revoked,'failed anchor URL cleanup');
 check(blobs.length===before+1&&anchors.length===3&&$('use-output').textContent.includes('未下载文件')&&!$('use-output').querySelector('a[download]'),'anchor failure removes link and revokes URL');
 button().click();await idle();await captured(blobs.length-1,info.outputs[1]);
 check(w.eval('applicationUseDownloads.size')===0,'failed requests and click failure release download lock');
}
async function navigation(){
 const scenarios={
  workspace:async()=>{w.selectWorkspace('resources');w.selectWorkspace('apps');},
  Run:async()=>{await selectRun(info.runs[0]);await selectRun(info.runs[1]);},
  instance:async()=>{await openInstance(info.other_instance);await openInstance();await selectRun(info.runs[1]);},
  project:async()=>{
   for(const project of [info.other,info.project]){$('project-select').value=project;await $('project-select').onchange(new w.Event('change'));}
   await openInstance();await selectRun(info.runs[1]);
  },
  identity:async()=>{await connect('synthetic-test-B');await connect();await openInstance();await selectRun(info.runs[1]);},
  'same identity reconnect':async()=>{await connect();await openInstance();await selectRun(info.runs[1]);},
  'refresh and repeat click':async()=>{
   $('use-refresh').click();await wait(()=>state.pending===1&&state.actions.size===1,'redraw complete with old GET pending');
   const n=requests.length;button().click();await new Promise(r=>setImmediate(r));
   check(requests.length===n,'same Run refreshed control shares in-flight deduplication');
  },
 };
 for(const [label,change]of Object.entries(scenarios)){
  const before=blobs.length;mode={hold:true};button().click();await wait(()=>!!finishRead,'held actual GET200');
  await change();const release=finishRead;finishRead=null;release();await idle();
  check(blobs.length===before,label+' away and back rejects late response before Blob creation');
  check(w.eval('applicationUseDownloads.size')===0,label+' frees old download lock');
 }
 button().click();await idle();await captured(0,info.outputs[1]);
 check(true,'current selection can explicitly download after stale request settles');
}
async function revocation(){
 mode={before:true};button().click();await wait(()=>!!finishRead,'GET held before actual authorization');
 const response=await fetch(info.base+'/test-only-revoke',{method:'POST',headers:{Authorization:'Bearer synthetic-test-A','Content-Type':'application/json'},body:'{}'});
 assert.equal(response.status,200);const release=finishRead;finishRead=null;release();await idle();
 check(blobs.length===0&&anchors.length===0,'real grant revocation yields no Blob or anchor');
 check(requests.at(-1).actual_status===403,'explicit download reauthorizes and receives real HTTP403');
 check($('use-form').hidden&&$('use-output').textContent===''&&$('use-history').textContent==='','403 clears protected cached result and download control');
 check(w.eval('applicationUseDownloads.size')===0,'403 frees download lock');
}
(async()=>{
 let result;
 try{
  await setup();
  if(info.case==='versions-and-rejections')await versions();else if(info.case==='navigation')await navigation();else await revocation();
  await idle();await wait(()=>blobs.every(b=>b.revoked),'all Blob URLs revoked');
  check(requests.every(r=>r.method==='GET'&&r.no_body),'all product page actions are GET without bodies; no Run/permission writes');
  check(state.errors.length===0&&state.pending===0&&state.actions.size===0,'no late HTTP/actions/page errors before DOM close');
  check(!w.document.querySelector('a[download]'),'all temporary anchors removed');
  result={status:'PASS',case:info.case,checks,requests,blobs:await Promise.all(blobs.map(async b=>({bytes:(await b.blob.arrayBuffer()).byteLength,sha256:createHash('sha256').update(Buffer.from(await b.blob.arrayBuffer())).digest('hex'),revoked:b.revoked}))),
   anchors,browser_download:'NOT_RUN',pg:'NOT_RUN',four_step_acceptance:'NOT_RUN',model_requests:0,adapter:'JSDOM + Node Blob byte capture, actual synthetic loopback HTTP',loaded_source_sha256:info.web_hashes};
 }catch(error){result={status:'FAIL',case:info.case,error:error.stack,checks,requests,browser_download:'NOT_RUN',pg:'NOT_RUN'};process.exitCode=1;}
 finally{
  fs.writeFileSync(path.join(root,'results.json'),JSON.stringify(result,null,2)+'\n');
  if(finishRead){finishRead();finishRead=null;}try{await idle();}finally{dom?.window.close();}
 }
 console.log(JSON.stringify(result));
})();
