'use strict';
// Actual protocol.js controller in a minimal element adapter, not a DOM/browser.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const out=process.argv[2],mode=process.argv[3]||'logic',web=path.join(__dirname,'../src/sim2act/web');
const source=fs.readFileSync(path.join(web,'protocol.js'),'utf8'),html=fs.readFileSync(path.join(web,'index.html'),'utf8');
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
for(const id of ['protocol-completion','protocol-completion-confirm','protocol-completion-submit','protocol-completion-retry','protocol-completion-status'])assert.equal(ids.filter(v=>v===id).length,1,id);
const rid='run_'+'1'.repeat(32),otherRid='run_'+'2'.repeat(32),project='proj_'+'3'.repeat(32),otherProject='proj_'+'4'.repeat(32),fp='a'.repeat(64);
const checks=[];let calls=[],respond,ctx,elements;
function check(value,name){assert.ok(value,name);checks.push(name);}
function entry(){return vm.runInContext('protocolCompletionIntents.get(protocolCompletionKey(protocolContext,activeRun))',ctx);}
function runData(overrides={}){return {namespace:'protocol_jobs.v1',run_id:rid,phase:'extract',status:'WAITING_RESOURCE',result:null,error:null,version:2,fence:1,...overrides};}
function receipt(body,overrides={}){return {namespace:'protocol-extract-completion.v2',run_id:rid,status:'SUCCEEDED',version:body.expected_version+1,fence:body.expected_fence+1,plan_fingerprint:fp,provider_requests:0,automatic_resend:false,cached:false,...overrides};}
function completed(body){return runData({status:'SUCCEEDED',version:body.expected_version+1,fence:body.expected_fence+1,result:{compiled_plan:{plan_fingerprint:fp,candidate:{resources:{}}}}});}
function evaluate(code){return vm.runInContext(code,ctx);}
function setup(run=runData(),handler){
 calls=[];elements=new Map(ids.map(id=>[id,{id,hidden:false,disabled:false,checked:false,value:'',textContent:'',replaceChildren(){this.textContent='';},querySelectorAll(){return [];}}]));
 elements.get('project-select').value=project;
 respond=handler||((url,options)=>options.method==='POST'?{data:receipt(JSON.parse(options.body))}:{data:completed(entry().body)});
 ctx=vm.createContext({token:'synthetic-A',activeRun:run.run_id,console,crypto:{randomUUID:crypto.randomUUID},Option:function(){},safe:fn=>fn,
  document:{getElementById(id){assert(elements.has(id),'real HTML id required: '+id);return elements.get(id);}},
  fetch:async(url,options={})=>{const call={url,method:options.method||'GET',body:options.body?JSON.parse(options.body):null};calls.push(call);const value=await respond(url,options);return {ok:(value.status||200)<400,status:value.status||200,json:async()=>value.data};}});
 ctx.$=id=>ctx.document.getElementById(id);vm.runInContext(source,ctx,{filename:'protocol.js'});
 choose(run,false);
}
function choose(run,selection=true){
 if(selection)evaluate(`protocolSelectRun(${JSON.stringify(run.run_id)});`);
 ctx.activeRun=run.run_id;
 ctx.nextRun=run;
 evaluate('if(!protocolContext)protocolContext={token,project:$("project-select").value,generation:protocolGeneration,selection:0,intent:0,busy:false};protocolContext.run=nextRun;renderProtocolRun(protocolContext);');
}
async function start(){elements.get('protocol-completion-confirm').checked=true;elements.get('protocol-completion-confirm').onchange();return elements.get('protocol-completion-submit').onclick();}
async function retry(){return elements.get('protocol-completion-retry').onclick();}
function postCalls(){return calls.filter(c=>c.method==='POST');}
async function logic(){
 setup();await elements.get('protocol-completion-submit').onclick();check(calls.length===0,'unchecked explicit completion sends nothing');
 for(const changed of [{phase:'source'},{phase:'cold'},{namespace:'bounded-check.v1'},{status:'PAUSED'},{status:'CANCELLED'},{error:{code:'OUTCOME_UNKNOWN'}},{version:true},{fence:false}]){
  setup(runData(changed));await start();check(calls.length===0,'unsupported current state cannot submit '+JSON.stringify(changed));
 }
 setup();await start();check(entry().state==='accepted'&&postCalls().length===1&&calls.length===2,'confirmed completion uses existing endpoint then reads same Run');
 check(Object.keys(postCalls()[0].body).sort().join(',')==='expected_fence,expected_version,request_key'&&postCalls()[0].url.endsWith('/complete-extraction'),'completion uploads only closed command fields');
 check(elements.get('protocol-completion').hidden&&!elements.get('protocol-cold-form').hidden,'successful actual controller reveals existing completed-plan route');
 const count=calls.length;await start();check(calls.length===count,'completed command cannot create a second completion intent');
 for(const bad of [{version:true},{fence:true},{provider_requests:false},{automatic_resend:0},{cached:0},{run_id:otherRid},{namespace:'protocol-recovery.v1'},{plan_fingerprint:'bad'},{extra:true}]){
  setup(runData(),(url,options)=>({data:receipt(JSON.parse(options.body),bad)}));await start();const body=JSON.stringify(postCalls()[0].body);
  check(entry().state==='unknown'&&!elements.get('protocol-completion-retry').hidden&&calls.length===1,'malformed 200 stays UNKNOWN '+JSON.stringify(bad));
  await start();check(calls.length===1,'UNKNOWN prevents fresh ordinary click '+JSON.stringify(bad));
  respond=()=>({status:422,data:{error:{code:'INVALID_INPUT'}}});await retry();
  check(entry().state==='unknown'&&JSON.stringify(postCalls()[1].body)===body,'later 4xx preserves original UNKNOWN body/key '+JSON.stringify(bad));
 }
 setup(runData(),()=>({status:403,data:{error:{code:'PERMISSION_DENIED'}}}));await start();check(entry().state==='rejected'&&elements.get('protocol-completion-retry').hidden,'definite initial refusal cannot claim successful completion');
 setup(runData(),(url,options)=>{if(options.method==='POST')throw Error('controlled lost receipt');return {data:{}};});await start();const original=JSON.stringify(postCalls()[0].body);
 respond=(url,options)=>({data:options.method==='POST'?receipt(JSON.parse(options.body),{cached:true}):completed(entry().body)});await retry();
 check(entry().state==='accepted'&&JSON.stringify(postCalls()[1].body)===original,'manual UNKNOWN retry uses exact original command and accepts cached receipt');
 setup(runData(),(url,options)=>options.method==='POST'?{data:receipt(JSON.parse(options.body))}:{status:403,data:{error:{code:'GRANT_REVOKED'}}});await start();
 check(entry().state==='accepted-read-error'&&!elements.get('protocol-completion-retry').hidden&&!elements.get('protocol-result').textContent,'accepted response plus failed read clears output and exposes read-only recovery');
 const posts=postCalls().length;respond=()=>({data:completed(entry().body)});await retry();
 check(postCalls().length===posts&&entry().state==='accepted','known accepted recovery performs only GET');
 for(const kind of ['run-ABA','project-ABA','identity-ABA']){
  let release;setup(runData(),(url,options)=>options.method==='POST'?new Promise(r=>release=()=>r({data:receipt(JSON.parse(options.body))})):{data:completed(entry().body)});
  const pending=start();await Promise.resolve();check(postCalls().length===1,'in-flight command started once '+kind);
  await start();check(postCalls().length===1,'busy command blocks double click '+kind);
  if(kind==='run-ABA'){choose(runData({run_id:otherRid}));choose(runData());}
  else{
   evaluate('clearProtocol();');
   if(kind==='project-ABA'){elements.get('project-select').value=otherProject;evaluate('clearProtocol();');elements.get('project-select').value=project;}
   else{ctx.token='synthetic-B';evaluate('clearProtocol();');ctx.token='synthetic-A';}
   choose(runData(),false);
  }
  release();await pending;
  check(calls.length===1&&evaluate('protocolContext.run.result===null')&&!elements.get('protocol-result').textContent.includes('compiled_plan'),'late accepted response cannot read/paint after '+kind);
  check(entry().state==='accepted-read-error','original owner/Run retains known receipt '+kind);
  evaluate('renderProtocolRun(protocolContext);');check(!elements.get('protocol-completion-retry').hidden,'fresh selected-view render exposes original read-only receipt '+kind);respond=()=>({data:completed(entry().body)});await retry();check(postCalls().length===1&&entry().state==='accepted','returned selection recovers known receipt by GET '+kind);
 }
 let releaseRead;setup(runData(),(url,options)=>options.method==='POST'?{data:receipt(JSON.parse(options.body))}:new Promise(r=>releaseRead=()=>r({data:completed({expected_version:2,expected_fence:1})})));
 const pending=start();for(let n=0;n<10&&!releaseRead;n++)await Promise.resolve();assert(releaseRead);choose(runData({run_id:otherRid}));choose(runData());releaseRead();await pending;
 check(evaluate('protocolContext.run.result===null')&&!elements.get('protocol-result').textContent.includes('compiled_plan'),'late detail GET cannot repaint after Run ABA');
 setup(runData(),(url)=>({data:{recovery:'CONTINUATION_NOT_IMPLEMENTED',provider_requests:0,global_send_blocked:false}}));
 // Old state-only action remains independent; avoid its separate GET by changing selection after response.
 respond=async()=>{choose(runData({run_id:otherRid}));return {data:{recovery:'CONTINUATION_NOT_IMPLEMENTED',provider_requests:0,global_send_blocked:false}};};
 await evaluate('recoverProtocol()');check(postCalls().length===1&&postCalls()[0].url.endsWith('/recover')&&!postCalls()[0].url.endsWith('/complete-extraction'),'existing state-only recover retains its own route');
}
async function http(){
 const info=JSON.parse(fs.readFileSync(path.join(out,'http-info.json'),'utf8'));
 const base=new URL(info.base);assert.equal(base.hostname,'127.0.0.1');
 const initial=await fetch(`${info.base}/api/projects/${info.project}/protocol/runs/${info.run}`,{headers:{Authorization:'Bearer secret test token'}});assert.equal(initial.status,200);
 setup(await initial.json(),async(url,options)=>{const target=new URL(url,info.base);assert.equal(target.origin,base.origin);const response=await fetch(target,options);return {status:response.status,data:await response.json()};});
 // Use the genuine persisted project/Run; token stays only in request headers, never report.
 elements.get('project-select').value=info.project;ctx.token='secret test token';
 evaluate('protocolContext.project=$("project-select").value;protocolContext.token=token;');
 await start();check(entry().state==='accepted','real loopback completion button reached original API and verified returned Run');
 check(postCalls().length===1&&calls.length===2,'actual HTTP controller made one completion POST and one result GET');
 const shown=evaluate('protocolContext.run');
 function canonical(value){if(Array.isArray(value))return value.map(canonical);if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));return value;}
 assert.equal(JSON.stringify(canonical(shown.result.compiled_plan)),JSON.stringify(canonical(info.captured.compiled)));
 check(shown.result.compiled_plan.candidate_receipt.namespace==='protocol-attempt-receipt.v2','real original V2 receipt preserved by page readback');
 fs.writeFileSync(path.join(out,'http-calls.json'),JSON.stringify(calls,null,2));
}
(async()=>{try{await (mode==='http'?http():logic());const result={status:'PASS',mode,checks,adapter:'MINIMAL_ELEMENT_VM_NOT_DOM_BROWSER',model_requests:0,source_sha256:crypto.createHash('sha256').update(source).digest('hex'),html_sha256:crypto.createHash('sha256').update(html).digest('hex')};fs.writeFileSync(path.join(out,mode+'-result.json'),JSON.stringify(result,null,2));console.log(JSON.stringify(result));}catch(error){fs.writeFileSync(path.join(out,mode+'-failure.json'),JSON.stringify({checks,error:error.stack},null,2));console.error(error.stack);process.exitCode=1;}})();
