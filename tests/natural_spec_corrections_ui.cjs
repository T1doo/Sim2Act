"use strict";
// Normal visible flow only: actual TestClient HTTP and cold Worker via IPC.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],actions=[],requests=[],assets=[],runViews=[],pending=new Map();
let serial=0,dom,w,$,boots=0,activeFetches=0,intervals=new Set(),dropGoal=false,dropDecision=false,dropCorrection=info.scenario==="run-lost",generated=null,finalView=null;
readline.createInterface({input:process.stdin}).on("line",line=>{const value=JSON.parse(line),resolve=pending.get(value.id);pending.delete(value.id);resolve(value);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
async function wait(test){const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("page wait elapsed");}
function visible(el){if(!el?.isConnected)return false;for(let node=el;node;node=node.parentElement){const s=w.getComputedStyle(node);if(node.hidden||node.hasAttribute("inert")||s.display==="none"||s.visibility==="hidden")return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(el))return false;}return true;}
async function gesture(el,perform,bindings){assert(visible(el),`visible ${el?.id||el?.textContent}`);assert(!el.matches(":disabled"),`enabled ${el.id}`);el.focus();const work=[],restore=[];for(const [node,property] of bindings){const original=node?.[property];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[property]=wrapper;restore.push(()=>{if(node[property]===wrapper)node[property]=original;});}actions.push({id:el.id||el.textContent,visible:true,enabled:true});try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const el=typeof value==="string"?$(value):value;return gesture(el,()=>el.click(),[[el,"onclick"],[el.form,"onsubmit"]]);};
const edit=(id,value)=>{const el=$(id);return gesture(el,()=>{el.value=value;el.dispatchEvent(new w.Event("input",{bubbles:true}));el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"oninput"],[el,"onchange"]]);};
const confirm=id=>{const el=$(id);return gesture(el,()=>{el.checked=true;el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const appButton=name=>[...$("app-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(name));
async function closePage(){if(!dom)return;for(const id of intervals)w.clearInterval(id);intervals.clear();await wait(()=>activeFetches===0&&pending.size===0);await new Promise(resolve=>setTimeout(resolve,0));await wait(()=>activeFetches===0&&pending.size===0);finalView={selected_owner_run:$("owner-run").value,owner_status:$("owner-status").textContent,run_detail:$("internal-run-detail").textContent,error:$("error").textContent};dom.window.close();dom=null;}
async function boot(){await closePage();const boot=++boots;const load=async path=>{const r=await rpc({method:"GET",path});assert.equal(r.status,200);assets.push({boot,path,status:r.status,sha256:crypto.createHash("sha256").update(r.text).digest("hex")});return r.text;};dom=new JSDOM(await load("/"),{url:"http://testserver/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;const originalInterval=w.setInterval.bind(w);w.setInterval=(...args)=>{const id=originalInterval(...args);intervals.add(id);return id;};const css=w.document.createElement("style");css.textContent=await load("/app.css");w.document.head.append(css);$=id=>w.document.getElementById(id);Object.defineProperty(w,"crypto",{value:crypto.webcrypto});w.TextEncoder=TextEncoder;w.fetch=async(path,options={})=>{const request={method:options.method||"GET",path,headers:options.headers||{},body:options.body?JSON.parse(options.body):undefined};requests.push(request);activeFetches++;try{const r=await rpc(request);if(request.method==="POST"&&path.endsWith("/correction-runs")&&dropCorrection){dropCorrection=false;throw Error("synthetic lost correction reply");}if(request.method==="POST"&&path.endsWith("/owner-goals")&&dropGoal){dropGoal=false;throw Error("synthetic lost own goal reply");}if(request.method==="POST"&&path.endsWith("/spec-owner-review-requests")&&request.body.command==="DECIDE"&&dropDecision){dropDecision=false;throw Error("synthetic lost decision reply");}return new Response(r.text,{status:r.status,headers:{"Content-Type":r.content_type||"application/json"}});}finally{activeFetches--;}};for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);}


(async()=>{let status="FAIL",error=null;try{
 await boot();await nav("apps");await click(appButton(info.name));await click($("internal-instances").querySelector("button"));await edit("owner-run",info.run);
 if(info.recovery_key){
  check(JSON.parse($("owner-history").textContent).latest.status==="REJECTED","original rejected declaration remains in immutable history");
  await edit("correction-key",info.recovery_key);await click("correction-recover");
 }else{
 check($("owner-status").textContent.includes("REJECTED"),"actual old rejected declaration shown");
 await click("correction-prepare");const proof=JSON.parse($("correction-proof").textContent);
 check(proof.original_goal.goal===info.goal_text,"correction keeps original Goal");
 check(proof.proposed_model_nodes>0&&proof.proposed_artifact_writes_at_most===1&&proof.real_model_allowance===0,"exact bounded model/effect proposal with zero real allowance");
 check($("correction-submit").disabled,"new Run requires explicit fresh acknowledgement");
 await confirm("correction-ack");await click("correction-submit");
 if(info.scenario==="run-lost"){
  check($("correction-submit").disabled,"unknown correction blocks duplicate Run");const n=requests.filter(r=>r.method==="POST").length;
  await click("correction-recover");check(requests.filter(r=>r.method==="POST").length===n,"unknown outcome recovers only original key GET");
 }
 }
 const receipt=JSON.parse($("correction-proof").textContent);check(receipt.run_id&&receipt.run_id!==info.run&&receipt.parent_run_id===info.run,"one distinct new Run bound to rejected parent");
 if(info.recovery_key)check(receipt.run_id===info.expected_child&&requests.every(r=>r.method==="GET"),"cold continuation recovers exact accepted child by GET without resubmitting");
 check(visible($("correction-open-run")),"accepted correction exposes direct new Run entry");
 await click("correction-open-run");
 if(!info.recovery_key){
 const queued=JSON.parse($("internal-run-detail").textContent);
 check(queued.id===receipt.run_id&&queued.status==="QUEUED","new entry opens exact queued correction progress before Worker");
 check($("owner-run").value===""&&$("owner-form").hidden,"queued correction has no successful-result judgement");
 runViews.push({stage:"before-worker",run:queued,owner_status:$("owner-status").textContent});
 assert.equal((await rpc({command:"worker",rid:receipt.run_id})).status,200);
 await click("internal-refresh");
 }
 // Polling and an explicit refresh may overlap. Await the actual same-Run
 // owner read, rather than treating an intermediate cleared selector as final.
 await wait(()=>{
  if($("owner-run").value!==receipt.run_id||!$("owner-status").textContent.includes("PENDING")||$("owner-prepare").disabled)return false;
  const detail=$("internal-run-detail").textContent,proof=$("owner-proof").textContent;
  if(!detail||!proof)return false;
  const run=JSON.parse(detail),contract=JSON.parse(proof).contract;
  return run.id===receipt.run_id&&run.status==="SUCCEEDED"&&contract?.run_id===receipt.run_id&&contract.result_version===2;
 });
 check($("owner-run").value===receipt.run_id,"same selected correction Run opens review after Worker completion");
 check($("owner-status").textContent.includes("PENDING"),"new successful result has no inherited acceptance");
 runViews.push({stage:"after-worker",run:JSON.parse($("internal-run-detail").textContent),owner_status:$("owner-status").textContent});
 const current=JSON.parse($("owner-proof").textContent).contract;
 check(current.goal.goal===info.goal_text&&current.result_version===2,"new typed version preserves Goal");
 check($("owner-natural-evidence").textContent.includes("原要求修正的理由"),"old issues and new exact result corresponding criteria are visible");
 check(current.human_correction.reference.parent_run_id===info.run&&current.human_correction.issues.length>0,"per-item old reasons remain linked without claiming repaired");
 await click("owner-prepare");const contract=JSON.parse($("owner-proof").textContent).contract;
 for(const item of contract.items){check($("owner-choice-"+item.id).value==="","new owner decision starts blank");await edit("owner-choice-"+item.id,"ACCEPT");await edit("owner-reason-"+item.id,"SIMULATED new independent judgement, not real semantics");}
 await confirm("owner-ack");await click("owner-submit");
 check($("owner-status").textContent.includes("ACCEPTED")&&$("owner-status").textContent.includes("UNKNOWN"),"fresh explicit judgement keeps semantic UNKNOWN");
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/correction-runs")).length===(info.recovery_key?0:1),info.recovery_key?"continuation creates zero correction Runs":"exactly one explicit correction Run POST");status="PASS";
 }catch(e){error=e.stack||String(e);process.stderr.write(error+"\n");process.exitCode=1;}finally{
 try{await closePage();}catch(e){error=error||String(e);status="FAIL";process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,actions,requests,run_views:runViews,final_view:finalView,static_resource_loads:assets,boots,
 classification:info.recovery_key?"ACTUAL_TESTCLIENT_HTTP_JSDOM_EXISTING_RUN_CONTINUATION_NO_NEW_WORKER":"ACTUAL_TESTCLIENT_HTTP_VISIBLE_JSDOM_ACTUAL_NEW_WORKER_SIMULATED_CHOICES",real_model:"NOT_RUN",native_browser:"NOT_RUN",real_human_semantic_acceptance:"NOT_RUN"},null,2));
 process.stdout.write(JSON.stringify({done:true})+"\n");}})();
