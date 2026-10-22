'use strict';
// Executes the real controller with minimal elements, not a DOM/native browser.
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const out=process.argv[2],mode=process.argv[3]||'logic',web=path.join(__dirname,'../src/sim2act/web');
const source=fs.readFileSync(path.join(web,'protocol.js'),'utf8'),html=fs.readFileSync(path.join(web,'index.html'),'utf8');
const ids=[...html.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]),checks=[];
for(const id of ['protocol-review','protocol-review-confirm','protocol-review-submit','protocol-review-retry','protocol-review-status'])assert.equal(ids.filter(v=>v===id).length,1);
const rid='run_'+'1'.repeat(32),project='proj_'+'2'.repeat(32),fp='a'.repeat(64);
let ctx,elements,calls,respond;
function check(value,name){assert.ok(value,name);checks.push(name);}
function evaluate(code){return vm.runInContext(code,ctx);}
function entry(){return evaluate('protocolReviewIntents.get(protocolCompletionKey(protocolContext,activeRun))');}
function pending(phase='source',extra={}){return {namespace:'protocol_jobs.v1',run_id:rid,phase,status:'WAITING_APPROVAL',contract_id:`protocol.synthetic.a-${phase}.v1`,result:{protocol_result:{semantic_status:'UNKNOWN'}},result_fingerprint:fp,error:null,version:2,fence:2,semantic_status:'UNKNOWN',semantic_review:'WAITING_APPROVAL',owner_semantic_acceptance:'PENDING',formal_publication_enabled:false,...extra};}
function receipt(run,extra={}){return {id:'review_'+'3'.repeat(32),run_id:run.run_id,contract_id:run.contract_id,namespace:'protocol-review.v1',decision:'PASS',reason:'registered independent synthetic oracle',fingerprint:'b'.repeat(64),publishable:false,model_requests:0,...extra};}
function approved(run){return {...run,status:'SUCCEEDED',version:run.version+1,semantic_status:'PASS',semantic_review:'APPROVED'};}
function choose(run,selection=true){
 if(selection)evaluate(`protocolSelectRun(${JSON.stringify(run.run_id)});`);
 ctx.activeRun=run.run_id;ctx.nextRun=run;
 evaluate('if(!protocolContext)protocolContext={token,project:$("project-select").value,generation:protocolGeneration,selection:0,intent:0,busy:false};protocolContext.run=nextRun;renderProtocolRun(protocolContext);');
}
function setup(run=pending(),handler){
 calls=[];respond=handler||((url,options)=>({data:options.method==='POST'?receipt(run):approved(run)}));
 elements=new Map(ids.map(id=>[id,{id,hidden:false,disabled:false,checked:false,value:'',textContent:'',replaceChildren(){this.textContent='';},querySelectorAll(){return [];}}]));elements.get('project-select').value=project;
 ctx=vm.createContext({token:'synthetic-A',activeRun:run.run_id,workspaceSelectionGeneration:0,crypto:{randomUUID:crypto.randomUUID},Option:function(){},safe:fn=>fn,
 document:{getElementById(id){assert(elements.has(id),id);return elements.get(id);}},
 fetch:async(url,options={})=>{calls.push({url,method:options.method||'GET',body:options.body?JSON.parse(options.body):null});assert(calls.length<=32,'bounded controller requests');const result=await respond(url,options);return {ok:(result.status||200)<400,status:result.status||200,json:async()=>result.data};}});
 ctx.$=id=>ctx.document.getElementById(id);vm.runInContext(source,ctx,{filename:'protocol.js'});choose(run,false);
}
async function start(){elements.get('protocol-review-confirm').checked=true;elements.get('protocol-review-confirm').onchange();return elements.get('protocol-review-submit').onclick();}
async function retry(){return elements.get('protocol-review-retry').onclick();}
function posts(){return calls.filter(v=>v.method==='POST');}
function closeReturn(){evaluate('workspaceSelectionGeneration++;$("projects").hidden=true;protocolCompletionWorkspaceChanged();workspaceSelectionGeneration++;$("projects").hidden=false;protocolCompletionWorkspaceChanged();');}
async function logic(){
 setup();await elements.get('protocol-review-submit').onclick();check(calls.length===0,'unchecked confirmation sends nothing');
 for(const extra of [{phase:'extract'},{contract_id:'unregistered'},{contract_id:'protocol.synthetic.a-cold.v1'},{result:null},{status:'SUCCEEDED'},{namespace:'bounded-check.v1'},{version:true},{fence:false},{semantic_status:'PASS'},{owner_semantic_acceptance:'APPROVED'},{formal_publication_enabled:true}]){
  setup(pending('source',extra));await start();check(calls.length===0,'unsupported state is closed '+JSON.stringify(extra));
 }
 for(const phase of ['source','cold']){
  const run=pending(phase);setup(run);await start();
  check(entry().state==='accepted'&&posts().length===1&&calls.length===2,'registered '+phase+' request then verified Run GET');
  check(Object.keys(posts()[0].body).sort().join(',')==='contract_id,expected_fence,expected_result_fingerprint,expected_version,request_key','only frozen references and fresh random key; no decision/gold');
  check(posts()[0].body.contract_id===run.contract_id&&posts()[0].body.expected_result_fingerprint===fp,'accepted contract and original fingerprint bound');
  check(elements.get('protocol-extract').hidden===(phase!=='source')&&elements.get('protocol-cold-form').hidden,'only existing approved Source route unlocks; no auto extraction/Cold');
  check(evaluate('protocolContext.run.owner_semantic_acceptance==="PENDING"&&!protocolContext.run.formal_publication_enabled'),'owner and publication remain closed');
  await start();check(posts().length===1,'known final review cannot submit another key');
 }
 for(const bad of [{decision:'INVALID'},{model_requests:false},{publishable:0},{contract_id:'protocol.synthetic.b-source.v1'},{run_id:'other'},{fingerprint:'bad'},{extra:true}]){
  const run=pending();setup(run,()=>({data:receipt(run,bad)}));await start();check(entry().state==='unknown'&&calls.length===1&&elements.get('protocol-extract').hidden,'malformed receipt cannot unlock '+JSON.stringify(bad));
 }
 const run=pending();
 for(const decision of ['FAIL','UNKNOWN']){
  let failRead=true;setup(run,(url,options)=>options.method==='POST'?{data:receipt(run,{decision})}:failRead?{status:403,data:{error:{code:'TEST_READ_FAILURE'}}}:{data:run});await start();
  check(entry().state==='accepted-read-error'&&posts().length===1&&elements.get('protocol-extract').hidden,'known business '+decision+' receipt with failed GET is distinct from lost receipt');
  failRead=false;await retry();check(entry().state==='accepted'&&posts().length===1&&elements.get('protocol-extract').hidden&&elements.get('protocol-review-submit').hidden,'business '+decision+' restores by GET only and cannot unlock or re-evaluate');
 }
 setup(run,()=>{throw Error('lost response');});await start();const body=JSON.stringify(posts()[0].body);closeReturn();choose(run);
 respond=()=>({status:403,data:{error:{code:'GRANT_REVOKED'}}});await retry();check(entry().state==='unknown'&&JSON.stringify(posts()[1].body)===body,'later rejection cannot replace an uncertain original key');
 respond=(url,options)=>({data:options.method==='POST'?receipt(run):approved(run)});await retry();check(entry().state==='accepted'&&posts().every(p=>JSON.stringify(p.body)===body),'UNKNOWN original-key replay succeeds after close/return');
 setup(run,(url,options)=>options.method==='POST'?{data:receipt(run)}:{status:403,data:{error:{code:'GRANT_REVOKED'}}});await start();
 check(entry().state==='accepted-read-error'&&elements.get('protocol-extract').hidden&&!elements.get('protocol-result').textContent,'known receipt plus failed GET clears content and keeps route closed');
 respond=()=>({data:approved(run)});await retry();check(posts().length===1&&entry().state==='accepted','known receipt recovery only reads original Run');
 for(const extra of [{version:4},{fence:3},{result_fingerprint:'c'.repeat(64)},{contract_id:'protocol.synthetic.b-source.v1'},{semantic_review:'WAITING_APPROVAL'}]){
  setup(run,(url,options)=>({data:options.method==='POST'?receipt(run):{...approved(run),...extra}}));await start();check(entry().state==='accepted-read-error'&&elements.get('protocol-extract').hidden,'mismatched approved GET cannot unlock '+JSON.stringify(extra));
 }
 for(const aba of ['run','workspace','project','identity']){
  let release;setup(run,(url,options)=>options.method==='POST'?new Promise(resolve=>release=()=>resolve({data:receipt(run)})):{data:approved(run)});
  const inflight=start();await Promise.resolve();await start();check(posts().length===1,'double click sends once '+aba);
  if(aba==='run'){choose(pending('source',{run_id:'run_'+'4'.repeat(32)}));choose(run);}
  else if(aba==='workspace')closeReturn();
  else{evaluate('clearProtocol();');if(aba==='project'){elements.get('project-select').value='other';evaluate('clearProtocol();');elements.get('project-select').value=project;}else{ctx.token='synthetic-B';evaluate('clearProtocol();');ctx.token='synthetic-A';}choose(run,false);}
  release();await inflight;check(calls.length===1&&evaluate('protocolContext.run.status==="WAITING_APPROVAL"')&&elements.get('protocol-extract').hidden,'late receipt cannot read/paint after '+aba+' ABA');
  evaluate('renderProtocolRun(protocolContext)');respond=()=>({data:approved(run)});await retry();check(posts().length===1&&entry().state==='accepted','original owner returns to known receipt with GET '+aba);
 }
 // A late non-PASS receipt must not treat the old pre-review Run as a fresh GET.
 for(const decision of ['FAIL','UNKNOWN']){
  let releasePost;setup(run,()=>new Promise(resolve=>releasePost=()=>resolve({data:receipt(run,{decision})})));
  const pendingPost=start();await Promise.resolve();closeReturn();releasePost();await pendingPost;choose(run);
  check(entry().state==='accepted-read-error'&&calls.length===1&&!elements.get('protocol-review-retry').hidden,'late '+decision+' receipt cannot be confirmed by pre-review Run render');
  respond=()=>({data:run});await retry();check(entry().state==='accepted'&&posts().length===1&&calls.length===2,'late '+decision+' requires explicit fresh GET');
 }
 // A new selected context may finish a newer read while the former context is pending.
 let releaseOld;setup(run,(url,options)=>options.method==='POST'?{data:receipt(run)}:new Promise(resolve=>releaseOld=()=>resolve({status:403,data:{error:{code:'OLD_READ_FAILURE'}}})));
 const oldRead=start();for(let n=0;n<10&&!releaseOld;n++)await Promise.resolve();assert(releaseOld);
 evaluate('clearProtocol()');choose(run,false);respond=()=>({data:approved(run)});await retry();check(entry().state==='accepted','new selected context completes newer authenticated GET');
 releaseOld();await oldRead;check(entry().state==='accepted'&&!elements.get('protocol-extract').hidden,'older failed GET cannot overwrite newer accepted command state');
 let release;setup(run,(url,options)=>options.method==='POST'?{data:receipt(run)}:new Promise(resolve=>release=()=>resolve({data:approved(run)})));
 const inflight=start();for(let n=0;n<10&&!release;n++)await Promise.resolve();assert(release);closeReturn();release();await inflight;
 check(elements.get('protocol-extract').hidden&&evaluate('protocolContext.run.result===null'),'late approved GET cannot restore hidden output after workspace close/return');
}
async function http(){
 const info=JSON.parse(fs.readFileSync(path.join(out,'http-info.json'),'utf8')),base=new URL(info.base);assert.equal(base.hostname,'127.0.0.1');
 const seen=[];let first=true,failRead=true;
 const send=async(url,options={})=>{const target=new URL(url,base);assert.equal(target.origin,base.origin);const response=await fetch(target,options);return {status:response.status,data:await response.json()};};
 const initial=await send(`/api/projects/${info.project}/protocol/runs/${info.run}`,{headers:{Authorization:'Bearer secret test token'}});assert.equal(initial.status,200);const run=initial.data;
 setup(run,async(url,options)=>{
  if(options.method==='POST'){
   const result=await send(url,options);seen.push(result.data);assert.equal(result.status,201);
   if(first){first=false;throw Error('intentionally discarded original review reply');}return result;
  }
  if(failRead){failRead=false;return {status:403,data:{error:{code:'TEST_READ_FAILURE'}}};}
  return send(url,options);
 });elements.get('project-select').value=info.project;ctx.token='secret test token';evaluate('protocolContext.project=$("project-select").value;protocolContext.token=token;');
 check(run.contract_id==='protocol.synthetic.a-source.v1','HTTP exposes only verified frozen contract ID');
 await start();check(entry().state==='unknown'&&posts().length===1&&elements.get('protocol-extract').hidden,'real accepted review reply lost: UNKNOWN, no route unlock');
 const original=JSON.stringify(posts()[0].body);closeReturn();choose(run);await retry();
 check(entry().state==='accepted-read-error'&&posts().length===2&&posts().every(p=>JSON.stringify(p.body)===original),'same page returns and replays exact original real review key');
 assert.deepEqual(seen[0],seen[1]);check(elements.get('protocol-extract').hidden,'real receipt alone plus controlled failed GET stays closed');
 await retry();check(posts().length===2&&entry().state==='accepted'&&!elements.get('protocol-extract').hidden,'GET-only recovery authenticates persisted PASS and enables existing explicit extraction button');
 check(evaluate('protocolContext.run.owner_semantic_acceptance==="PENDING"&&!protocolContext.run.formal_publication_enabled')&&elements.get('protocol-cold-form').hidden,'no owner acceptance, publication, plan or Cold auto-unlock');
 fs.writeFileSync(path.join(out,'http-receipts.json'),JSON.stringify({bodies:posts().map(p=>p.body),receipts:seen,read:evaluate('protocolContext.run')},null,2));
}
(async()=>{await (mode==='http'?http():logic());fs.writeFileSync(path.join(out,mode+'-result.json'),JSON.stringify({status:'PASS',scope:'actual controller minimal element VM; not DOM/browser',source_sha256:crypto.createHash('sha256').update(source).digest('hex'),checks,controller_requests:calls.length,model_requests:0},null,2));console.log(`${checks.length} ${mode} review checks PASS`);})().catch(error=>{console.error(error);process.exitCode=1;});
