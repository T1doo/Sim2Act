"use strict";
// Normal visible flow only: actual TestClient HTTP and cold Worker via IPC.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],actions=[],requests=[],assets=[],pending=new Map();
let serial=0,dom,w,$,boots=0,activeFetches=0,intervals=new Set(),dropGoal=false,dropDecision=false,dropCorrection=info.scenario==="lost",generated=null;
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
async function closePage(){if(!dom)return;for(const id of intervals)w.clearInterval(id);intervals.clear();await wait(()=>activeFetches===0&&pending.size===0);await new Promise(resolve=>setTimeout(resolve,0));await wait(()=>activeFetches===0&&pending.size===0);dom.window.close();dom=null;}
async function boot(){await closePage();const boot=++boots;const load=async path=>{const r=await rpc({method:"GET",path});assert.equal(r.status,200);assets.push({boot,path,status:r.status,sha256:crypto.createHash("sha256").update(r.text).digest("hex")});return r.text;};dom=new JSDOM(await load("/"),{url:"http://testserver/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;const originalInterval=w.setInterval.bind(w);w.setInterval=(...args)=>{const id=originalInterval(...args);intervals.add(id);return id;};const css=w.document.createElement("style");css.textContent=await load("/app.css");w.document.head.append(css);$=id=>w.document.getElementById(id);Object.defineProperty(w,"crypto",{value:crypto.webcrypto});w.TextEncoder=TextEncoder;w.fetch=async(path,options={})=>{const request={method:options.method||"GET",path,headers:options.headers||{},body:options.body?JSON.parse(options.body):undefined};requests.push(request);activeFetches++;try{const r=await rpc(request);if(request.method==="POST"&&path.endsWith("/pa-use-runs")&&dropCorrection){dropCorrection=false;throw Error("synthetic lost PA per-use reply");}if(request.method==="POST"&&path.endsWith("/owner-goals")&&dropGoal){dropGoal=false;throw Error("synthetic lost own goal reply");}if(request.method==="POST"&&path.endsWith("/spec-owner-review-requests")&&request.body.command==="DECIDE"&&dropDecision){dropDecision=false;throw Error("synthetic lost decision reply");}return new Response(r.text,{status:r.status,headers:{"Content-Type":r.content_type||"application/json"}});}finally{activeFetches--;}};for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);}

(async()=>{let status="FAIL",error=null;try{
 await boot();await nav("apps");await click(appButton(info.name));await click($("internal-instances").querySelector("button"));
 check(visible($("pb-use-panel")),"saved P-A instance exposes explicit new material/Goal input");
 await edit("pb-use-material",info.resource);await edit("pb-use-goal",info.goal);
 await click("pb-use-preview");const review=JSON.parse($("pb-use-proof").textContent);
 check(review.namespace==="pa-natural-per-run.v1","separate P-A per-use namespace");
 check(review.app_id===info.app&&review.release_id===info.release&&review.instance_id===info.instance,"same saved app/Release/instance");
 check(review.target_goal.card_id===info.goal&&review.variable_bindings.resource_id===info.resource,"this exact new Goal and material");
 check(review.preview.source_content===info.content&&review.instance_data_version===2,"unseen third source displayed with original result version");
 check(review.effective_candidate.manifest.origin==="goal"&&!review.effective_candidate.spec_task,"P-A generation provenance retained");
 check(review.proposed_model_nodes>0&&review.proposed_artifact_writes_at_most===1&&review.real_model_allowance===0,"explicit bounded proposal and no real model allowance");
 check($("pb-use-submit").disabled,"fresh explicit confirmation required");
 await confirm("pb-use-ack");await click("pb-use-submit");
 if(info.scenario==="lost"){
  check(w.eval("pbUsePending.size")===1&&$("internal-run-submit").disabled&&$("pb-use-submit").disabled,"unknown outcome retains original intent and blocks duplicates");
  const posts=requests.filter(x=>x.method==="POST").length;await click("pb-use-recover");
  check(requests.filter(x=>x.method==="POST").length===posts,"original-key recovery is GET only");
 }
 const run=w.eval("engineering.run.id");check(run&&run!==info.original&&w.eval("pbUsePending.size")===0,"one distinct accepted new Run with verified receipt");
 check(requests.filter(x=>x.method==="POST"&&x.path.endsWith("/pa-use-runs")).length===1,"exactly one explicit P-A per-use POST");
 assert.equal((await rpc({command:"worker",rid:run})).status,200);
 await click("internal-refresh");await edit("owner-run",run);
 check($("owner-status").textContent.includes("PENDING"),"new result has fresh PENDING owner state");
 const contract=JSON.parse($("owner-proof").textContent).contract;
 check(contract.source_goal.card_id===info.goal&&contract.material.resource_id===info.resource&&contract.result_version===3,"fresh owner contract binds third Goal/source/exact version3");
 check(contract.output.checklist.source_content===info.content,"new actual saved result derives from third source");
 check($("internal-data").textContent.includes("规范成果 v1")&&$("internal-data").textContent.includes("规范成果 v2")&&$("internal-data").textContent.includes("规范成果 v3"),"all three historical result versions remain visible");
 await click("owner-prepare");const reviewed=JSON.parse($("owner-proof").textContent).contract;
 for(const item of reviewed.items){check($("owner-choice-"+item.id).value==="","fresh owner choices start blank");await edit("owner-choice-"+item.id,"ACCEPT");await edit("owner-reason-"+item.id,"SIMULATED independent third-input judgement, not real semantics");}
 await confirm("owner-ack");await click("owner-submit");
 check($("owner-status").textContent.includes("ACCEPTED")&&$("owner-status").textContent.includes("UNKNOWN"),"independent new human declaration does not change semantic UNKNOWN");status="PASS";
 }catch(e){error=e.stack||String(e);process.stderr.write(error+"\n");process.exitCode=1;}finally{
 try{await closePage();}catch(e){error=error||String(e);status="FAIL";process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,actions,requests,static_resource_loads:assets,boots,
 classification:"ACTUAL_TESTCLIENT_HTTP_VISIBLE_JSDOM_ACTUAL_NEW_WORKER_SIMULATED_CHOICES",real_model:"NOT_RUN",native_browser:"NOT_RUN",real_human_semantic_acceptance:"NOT_RUN"},null,2));
 process.stdout.write(JSON.stringify({done:true})+"\n");}})();
