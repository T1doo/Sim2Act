"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,"info.json"))),checks=[],requests=[],hashes={};
let dom,w,$,page,mode="",release;
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async fn=>{const until=Date.now()+6000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error("bounded DOM wait expired");};
async function idle(){if(!page)return;await wait(()=>page.requests===0&&page.actions.size===0);await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];}
async function close(){if(dom){await idle();dom.window.close();dom=null;}}
function track(window,current){
  for(const name of ["onclick","onchange","onsubmit"]){const descriptor=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...descriptor,set(fn){descriptor.set.call(this,typeof fn==="function"?function(...args){const result=fn.apply(this,args);if(result&&typeof result.then==="function"){const action=Promise.resolve(result);current.actions.add(action);action.then(()=>current.actions.delete(action),e=>{current.actions.delete(action);current.errors.push(e);});}return result;}:fn);}});}
  window.addEventListener("error",e=>current.errors.push(e.error||Error(e.message)));
}
async function setup(){
  await close();const html=await(await fetch(info.base)).text();hashes["index.html"]=crypto.createHash("sha256").update(html).digest("hex");
  dom=new JSDOM(html,{url:info.base,runScripts:"dangerously"});w=dom.window;$=id=>w.document.getElementById(id);page={requests:0,actions:new Set(),errors:[]};track(w,page);w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();const current=page;
  w.fetch=async(url,opts={})=>{current.requests++;try{
    const target=new URL(url,info.base);assert.equal(target.origin,info.base);const request={path:target.pathname,method:opts.method||"GET",body:opts.body&&JSON.parse(opts.body)};requests.push(request);
    const response=await fetch(target,opts);
    if(mode==="lost"&&request.method==="POST"&&request.path.includes("/csv-dag")){mode="";throw Error("owned lost accepted response");}
    if(mode==="hold"&&request.method==="GET"&&/^\/api\/csv-dag\/runs\/run_[a-f0-9]+$/.test(request.path)){mode="";await new Promise(r=>release=r);release=null;}
    if(mode==="tamper"&&request.method==="GET"&&/^\/api\/csv-dag\/runs\/run_[a-f0-9]+$/.test(request.path)){mode="";const data=await response.json();data.result.output.sum="999";return {ok:true,status:200,json:async()=>data};}
    return new Response(await response.arrayBuffer(),{status:response.status,headers:response.headers});
  }finally{current.requests--;}};
  const names=Array.from(w.document.querySelectorAll("script[src]")).map(s=>s.getAttribute("src").slice(1));
  for(const name of names){const code=await(await fetch(info.base+"/"+name)).text();hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const script=w.document.createElement("script");script.textContent=code;w.document.body.append(script);}
  $("token").value="synthetic-test-A";$("connect").click();await wait(()=>$("login").hidden&&$("project-select").value===info.project);await idle();await w.showApp(info.app);
}
const headers={Authorization:"Bearer synthetic-test-A","Content-Type":"application/json"};
async function work(runId,oneStep=false){const r=await fetch(info.base+"/__fixture__/work",{method:"POST",headers,body:JSON.stringify({run_id:runId,one_step:oneStep})});assert(r.ok,await r.text());}
(async()=>{try{
  await setup();check(!$("csv-dag-panel").hidden,"fixed DAG controls are inside the existing CSV app");check($("csv-dag-run").disabled,"run is initially blocked without a confirmed plan");
  $("csv-dag-column").value="quantity";mode="lost";await w.csvDagSubmit("plan");check(!$("csv-dag-retry").hidden&&!$("csv-dag-definition").textContent,"lost accepted plan clears proof and preserves request intent");
  await w.csvDagSubmit(null,true);check($("csv-dag-retry").hidden&&$("csv-dag-definition").textContent.includes("quantity"),"plan recovery reads the same saved definition");
  const definitions=requests.filter(r=>r.method==="POST"&&r.path.endsWith("/csv-dag"));check(definitions.length===2&&JSON.stringify(definitions[0].body)===JSON.stringify(definitions[1].body),"plan recovery freezes key column and baseline fingerprints");
  check($("csv-dag-run").disabled&&!$("csv-dag-confirm").checked,"saved plan does not auto-confirm execution");
  $("csv-dag-confirm").checked=true;$("csv-dag-confirm").dispatchEvent(new w.Event("change"));check(!$("csv-dag-run").disabled,"explicit exact-plan confirmation enables a run");
  mode="lost";await w.csvDagSubmit("run");check(!$("csv-dag-retry").hidden&&!$("csv-dag-result").textContent,"lost accepted run preserves its original request");
  await w.csvDagSubmit(null,true);check($("csv-dag-retry").hidden&&$("csv-dag-result").textContent.includes("QUEUED"),"run recovery reads durable queued status without creating a duplicate");
  const submissions=requests.filter(r=>r.method==="POST"&&r.path.includes("/csv-dag/")&&r.path.endsWith("/runs"));check(submissions.length===2&&JSON.stringify(submissions[0].body)===JSON.stringify(submissions[1].body),"run retry preserves confirmation fingerprint and request key");
  const queued=JSON.parse($("csv-dag-result").textContent),runId=queued.id;
  const wrong=await fetch(info.base+submissions[0].path,{method:"POST",headers,body:JSON.stringify({...submissions[0].body,request_key:"wrong-version",expected_plan_fingerprint:"0".repeat(64)})});check(wrong.status===409,"real API refuses wrong plan confirmation");
  await work(runId,true);await w.csvDagRead();const preview=JSON.parse($("csv-dag-result").textContent);check(preview.steps.length===1&&preview.steps[0].step_id==="preview"&&preview.result===null,"first real step has a verified receipt and no final result");
  await w.csvDagCommand("pause");await work(runId);await w.csvDagRead();check($("csv-dag-result").textContent.includes("PAUSED"),"pause settles at a committed step boundary");
  await w.csvDagCommand("resume");await work(runId);await w.csvDagRead();const completed=JSON.parse($("csv-dag-result").textContent);check(completed.status==="SUCCEEDED"&&completed.steps.length===3,"explicit resume executes only the two remaining steps");
  check(completed.steps[0].operation_id===preview.steps[0].operation_id,"resume preserves the committed predecessor operation");
  check(completed.result.output.sum==="15"&&completed.result.output.text==="列 quantity；行数 2；合计 15","actual synthetic CSV produces independently frozen report text and sum");
  check(completed.steps.every(s=>s.artifact_refs.length===0)&&completed.model_requests===0&&completed.business_writes===0,"report remains a run result with zero artifacts models or business writes");
  check(!$("csv-dag-confirm").checked&&completed.owner_acceptance==="PENDING"&&completed.semantic_status==="UNKNOWN"&&completed.formal_publication_enabled===false,"engineering success leaves owner semantic and publication gates honest");
  const posts=requests.filter(r=>r.method==="POST").length;await setup();await w.csvDagHistory();const buttons=Array.from($("csv-dag-history").querySelectorAll("button"));check(buttons.some(b=>b.textContent==="核对运行回执"),"cold page lists saved plans and accepted runs");buttons.find(b=>b.textContent==="核对运行回执").click();await idle();check($("csv-dag-result").textContent.includes("SUCCEEDED")&&requests.filter(r=>r.method==="POST").length===posts,"cold history recovery verifies receipts without any new submission");
  mode="tamper";let rejected=false;try{await w.csvDagRead();}catch{rejected=true;}check(rejected&&!$("csv-dag-result").textContent&&!$("csv-dag-definition").textContent,"tampered final result clears all current proof");
  await w.csvDagHistory();Array.from($("csv-dag-history").querySelectorAll("button")).find(b=>b.textContent==="核对运行回执").click();await idle();
  mode="hold";const late=w.csvDagRead();await wait(()=>release);const resume=release;$("project-select").value=info.other;w.clearApp();$("project-select").value=info.project;await w.showApp(info.app);resume();await late;check(!$("csv-dag-result").textContent,"project ABA rejects a late protected run response");
  await w.csvDagHistory();Array.from($("csv-dag-history").querySelectorAll("button")).find(b=>b.textContent==="核对运行回执").click();await idle();
  const revoked=await fetch(info.base+`/api/grants/${info.revoke.id}/revoke`,{method:"POST",headers,body:JSON.stringify({command:"revoke",version:info.revoke.version})});check(revoked.ok,"only the existing owned source grant is revoked");
  rejected=false;try{await w.csvDagRead();}catch{rejected=true;}check(rejected&&!$("csv-dag-result").textContent&&!$("csv-dag-definition").textContent,"revocation invalidates saved result and plan proof");
  const result={status:"PASS",checks,requests,loaded_source_sha256:hashes,model_requests:0,business_writes:0,native:"NOT_RUN",owner_acceptance:"PENDING",semantic:"UNKNOWN",publication:false};fs.writeFileSync(path.join(root,"results.json"),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,"failure.json"),JSON.stringify({status:"FAIL",checks,error:e.message,requests,loaded_source_sha256:hashes},null,2));console.error(e.stack);process.exitCode=1;}finally{await close();}})();
