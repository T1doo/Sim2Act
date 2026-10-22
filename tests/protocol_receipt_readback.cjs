'use strict';
// Fresh controller contexts and serialized actual API replies; no native DOM.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const root=process.argv[2],web=path.join(__dirname,'../src/sim2act/web'),source=fs.readFileSync(path.join(web,'protocol.js'),'utf8');
const ids=[...fs.readFileSync(path.join(web,'index.html'),'utf8').matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
const cases=JSON.parse(fs.readFileSync(path.join(root,'cases.json'),'utf8')),checks=[];
let context,elements,calls,respond,allowCompletionProbe=false;
const ev=code=>vm.runInContext(code,context);
function check(ok,name){assert.ok(ok,name);checks.push(name);}
function setup(item,handler){
 elements=new Map(ids.map(id=>[id,{hidden:false,disabled:false,checked:false,value:'',textContent:'',replaceChildren(){this.textContent='';},querySelectorAll(){return [];}}]));
 elements.get('project-select').value='project'; calls=[];allowCompletionProbe=false;
 respond=handler||((url)=>({data:url.endsWith('/review-receipt')?item.locator:item.run}));
 context=vm.createContext({token:'owner',activeRun:item.run.run_id,workspaceSelectionGeneration:0,Option:function(){},safe:fn=>fn,
  crypto:{randomUUID(){throw Error('Readback must never allocate a key');}},
  document:{getElementById(id){assert(elements.has(id),id);return elements.get(id);}},
  fetch:async(url,options={})=>{calls.push({url,method:options.method||'GET'});assert(calls.length<=12,'bounded VM reads');assert(options.method==='GET'||allowCompletionProbe&&options.method==='POST'&&url.endsWith('/complete-source'));const r=await respond(url,options);return {ok:(r.status||200)<400,status:r.status||200,json:async()=>r.data};}});
 context.$=id=>context.document.getElementById(id);vm.runInContext(source,context);context.selected=item.run;
 ev('protocolContext={token,project:"project",generation:protocolGeneration,selection:0,intent:0,busy:false,run:selected};renderProtocolRun(protocolContext);');
}
const locate=()=>elements.get('protocol-review-locate').onclick();
const entry=()=>ev('protocolContext&&protocolReviewIntents.get(protocolCompletionKey(protocolContext,activeRun))');
(async()=>{
 for(const item of cases){
  setup(item);check(!entry(),'new page has no in-memory key '+item.run.phase);await locate();
  check(entry().state==='accepted'&&entry().body.request_key===item.locator.request.request_key&&calls.length===2,'cold '+item.run.phase+' locates original key and verifies fresh Run using two GETs');
  check(elements.get('protocol-review-submit').hidden&&elements.get('protocol-review-locate-receipt').textContent.includes(item.locator.request.request_key),'original receipt visible; accepted command cannot obtain another key');
  await ev('requestProtocolReview(true)');check(calls.length===2,'accepted retry cannot POST');
 }
 const item=cases[0];
 setup(item);context.unicodeLocator={...item.locator,request:{...item.locator.request,request_key:'🙂'.repeat(70)}};check(ev('protocolReviewLocated(unicodeLocator,selected)!==null'),'key length follows server Unicode codepoints');
 setup(item,(url)=>url.endsWith('/review-receipt')?{data:item.locator}:{status:403,data:{error:{code:'REVOKED'}}});await locate();
 check(entry().state==='accepted-read-error'&&elements.get('protocol-extract').hidden&&!elements.get('protocol-review-locate-receipt').textContent,'failed fresh GET retains original receipt but clears output and closes routes');
 respond=()=>({data:item.run});await ev('requestProtocolReview(true)');
 check(entry().state==='accepted'&&calls.length===3,'known receipt recovers by GET only');
 setup(item);await locate();const acceptedKey=entry().body.request_key;
 respond=()=>({data:{...item.locator,state:'NOT_FOUND',request:null,receipt:null}});await locate();
 check(entry().body.request_key===acceptedKey&&elements.get('protocol-extract').hidden&&!elements.get('protocol-review-locate-receipt').textContent&&!elements.get('protocol-result').textContent,'NOT_FOUND clears former PASS and visible receipt without losing original key');
 const pending={...item.run,status:'WAITING_APPROVAL',version:item.locator.request.expected_version,semantic_status:'UNKNOWN',semantic_review:'WAITING_APPROVAL'};
 setup({...item,run:pending},()=>({data:{...item.locator,state:'NOT_FOUND',request:null,receipt:null}}));await locate();
 check(!entry()&&ev('protocolContext.reviewLocateClosed===activeRun')&&elements.get('protocol-review-submit').disabled,'absence is closed and never manufactures a request key');
 await ev('$("protocol-review-confirm").checked=true;requestProtocolReview()');check(calls.length===1,'missing evidence cannot turn recovery into a fresh command');
 for(const corrupt of [{namespace:'unknown'},{request:{...item.locator.request,expected_version:true}},{receipt:{...item.locator.receipt,model_requests:false}},{extra:true}]){
  setup(item,()=>({data:{...item.locator,...corrupt}}));await locate();
  check(!entry()&&elements.get('protocol-extract').hidden&&!elements.get('protocol-result').textContent,'malformed discovery stays closed '+JSON.stringify(corrupt));
 }
 setup(item);context.oldBody={...item.locator.request,request_key:'original-unknown-key'};
 ev('protocolReviewIntents.set(protocolCompletionKey(protocolContext,activeRun),{rid:activeRun,phase:selected.phase,body:oldBody,state:"unknown",uncertain:true});');await locate();
 check(entry().body.request_key==='original-unknown-key'&&entry().state==='unknown'&&calls.length===1,'different accepted key cannot replace in-memory UNKNOWN');
 for(const aba of ['workspace','run','project','identity']){
  let release;setup(item,()=>new Promise(resolve=>release=()=>resolve({data:item.locator})));
  const promise=locate();await Promise.resolve();
  if(aba==='workspace')ev('workspaceSelectionGeneration++;$("projects").hidden=true;protocolCompletionWorkspaceChanged();workspaceSelectionGeneration++;$("projects").hidden=false;protocolCompletionWorkspaceChanged();');
  else if(aba==='run')ev('protocolSelectRun("other");protocolSelectRun(activeRun);protocolContext.run=selected;');
  else {ev('clearProtocol()');if(aba==='identity')context.token='other';else elements.get('project-select').value='other';}
  release();await promise;check(!entry()&&calls.length===1,'late discovery cannot restore key or content after '+aba+' context change');
 }
 // A review lookup failure must not restrict the separate existing completion contract.
 const incomplete={...item.run,status:'RUNNING',version:1,fence:1,result:null,result_fingerprint:null,semantic_status:'UNKNOWN',semantic_review:'WAITING_APPROVAL'};
 setup({...item,run:incomplete},()=>({status:409,data:{error:{code:'INCOMPLETE_REVIEW'}}}));await locate();
 check(ev('protocolContext.reviewLocateClosed===activeRun'),'review lookup fails closed for an incomplete Source');
 allowCompletionProbe=true;context.crypto.randomUUID=()=> 'explicit-completion-VM-only';
 const completed={...incomplete,status:'WAITING_APPROVAL',version:2,fence:2,result:item.run.result,result_fingerprint:item.run.result_fingerprint};
 respond=(url,options)=>({data:options.method==='POST'?{namespace:'protocol-source-completion.v2',run_id:item.run.run_id,status:'WAITING_APPROVAL',version:2,fence:2,result_fingerprint:item.run.result_fingerprint,provider_requests:0,automatic_resend:false,cached:false}:completed});
 await ev('$("protocol-completion-confirm").checked=true;completeProtocolExtraction()');
 check(calls.filter(c=>c.method==='POST').length===1&&ev('protocolCompletionIntents.get(protocolCompletionKey(protocolContext,activeRun)).state==="accepted"'),'separate explicitly confirmed Source completion remains unchanged after failed review discovery (VM only)');
 const report={status:'PASS',scope:'fresh controller VM, not native DOM',checks,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),discovery_new_keys:0,discovery_posts:0,completion_compatibility_vm_posts:1,real_network_posts:0};
 fs.writeFileSync(path.join(root,'controller-result.json'),JSON.stringify(report,null,2));console.log(checks.length+' readonly recovery checks PASS');
})().catch(e=>{console.error(e);process.exitCode=1;});
