"use strict";
// Actual served forms and TestClient HTTP. Worker responses are synthetic, never LIVE.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const durable=require(path.join(process.cwd(),"tests/durable_browser.cjs"))();
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],actions=[],requests=[],assets=[],pending=new Map();
const familyCode="NATURAL_"+info.family.toUpperCase(),route=info.family+"-use";
let serial=0,dom,w,$,boots=0,activeFetches=0,resourceId=null,goalId=null,runId=null;
readline.createInterface({input:process.stdin}).on("line",line=>{const reply=JSON.parse(line),resolve=pending.get(reply.id);pending.delete(reply.id);assert(resolve,"known IPC response");resolve(reply);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(condition,label)=>{assert(condition,label);checks.push(label);};
async function wait(test,label){const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("bounded page wait: "+label);}
function visible(el){if(!el?.isConnected)return false;for(let node=el;node;node=node.parentElement){const style=w.getComputedStyle(node);if(node.hidden||node.hasAttribute("inert")||style.display==="none"||style.visibility==="hidden")return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(el))return false;}return true;}
async function gesture(el,perform,bindings){assert(visible(el),`visible ${el?.id||el?.textContent}`);assert(!el.matches(":disabled"),`enabled ${el.id}`);el.focus();const work=[],restore=[];for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const result=original.call(this,event);work.push(Promise.resolve(result));return result;};node[key]=wrapper;restore.push(()=>{if(node[key]===wrapper)node[key]=original;});}actions.push({boot:boots,id:el.id||el.textContent,visible:true,enabled:true});try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const el=typeof value==="string"?$(value):value;return gesture(el,()=>el.click(),[[el,"onclick"],[el.form,"onsubmit"]]);};
const edit=(id,value)=>{const el=$(id);return gesture(el,()=>{el.value=value;el.dispatchEvent(new w.Event("input",{bubbles:true}));el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"oninput"],[el,"onchange"]]);};
const confirm=id=>{const el=$(id);return gesture(el,()=>{el.checked=true;el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const writes=()=>requests.filter(row=>row.method!=="GET");
const usePosts=()=>requests.filter(row=>row.method==="POST"&&row.path.endsWith(`/${route}-runs`));
async function closePage(){if(!dom)return;await wait(()=>activeFetches===0&&pending.size===0,"HTTP drained");await new Promise(resolve=>setImmediate(resolve));await wait(()=>activeFetches===0&&pending.size===0,"HTTP remains drained");dom.window.close();dom=null;}
async function boot(){
 await closePage();const boot=++boots;
 const load=async assetPath=>{const reply=await rpc({method:"GET",path:assetPath});assert.equal(reply.status,200);assets.push({boot,path:assetPath,status:reply.status,sha256:crypto.createHash("sha256").update(reply.text).digest("hex")});return reply.text;};
 dom=new JSDOM(await load("/"),{url:"http://testserver/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;durable.install(w);$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,"crypto",{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(url,options={})=>{const request={boot,method:options.method||"GET",path:url,headers:options.headers||{},body:options.body?JSON.parse(options.body):undefined};requests.push(request);activeFetches++;try{const reply=await rpc(request);request.status=reply.status;try{request.response=JSON.parse(reply.text);}catch{request.response_text=reply.text;}return new Response(reply.text,{status:reply.status,headers:{"Content-Type":reply.content_type||"application/json"}});}finally{activeFetches--;}};
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project,"connected exact project");
}
async function openEntry(){
 await nav("apps");const selector=`[data-use-family="${familyCode}"][data-app-id="${info.app}"]`;
 await wait(()=>!!$("use-list").querySelector(selector),"exact saved natural family in unified directory");
 const entry=$("use-list").querySelector(selector);check(entry.textContent.includes(info.name)&&entry.textContent.includes(info.family==="pa"?"P-A":"P-B"),"directory selects exact saved application family");
 await click([...entry.querySelectorAll("button")].find(el=>el.textContent==="使用此自然规范应用"));
 const instanceRow=[...$("internal-instances").children].find(el=>el.textContent.includes(info.instance));check(!!instanceRow&&visible(instanceRow),"user explicitly selects original saved instance");
 await click(instanceRow.querySelector("button"));await wait(()=>visible($("pb-use-panel")),"existing per-use controller");
 check(w.eval("activeApp")===info.app&&w.eval("engineering.instance.id")===info.instance&&w.eval("engineering.instance.release_id")===info.release,"opened exact original app Release and instance");
}
async function sameRunOwner(){
 const row=[...$("internal-runs").children].find(el=>el.textContent.includes(runId));check(!!row,"new Run retained in exact instance history");await click(row.querySelector("button"));
 await wait(()=>$("owner-run").value===runId&&$("owner-proof").textContent.includes(runId),"same Run manual entry");
 const contract=JSON.parse($("owner-proof").textContent).contract;
 check(contract.run_id===runId&&contract.source_goal.card_id===goalId&&contract.material.resource_id===resourceId&&contract.result_version===2,"same Run manual entry binds newly saved Goal material and new result version");
 check(contract.output.checklist.source_content===info.content&&$("owner-status").textContent.includes("PENDING"),"new result readable with independent manual PENDING state");
}
(async()=>{let status="FAIL",error=null;try{
 await boot();check(writes().length===0,"cold connect reads metadata without writes");await openEntry();await rpc({command:"readonly-checkpoint",phase:"before-preparation"});
 await click("pb-use-prepare");check(visible($("natural-use-preparation"))&&visible($("resource-form")),"in-app preparation uses visible original resource form");
 check(w.document.querySelectorAll("#resource-form").length===1&&w.document.querySelectorAll("#goal-card-form").length===1,"preparation reuses exactly one shared material and Goal form");
 await edit("resource-name",`new-${info.family}-user-input.txt`);await edit("format","txt");
 if(info.family==="pa")for(const [content,label] of [["x".repeat(2049),"UTF-8 byte limit"],[Array(41).fill("x").join("\n"),"splitlines limit"],["visible\u200bhidden","Unicode control category"]]){
  await edit("content",content);const before=writes().length;await click("resource-save");check(writes().length===before,`invalid ${label} rejected before any save request`);
 }
 await edit("content",info.content);check(writes().length===0,"editing shared form creates no material Goal Grant or Run writes");await rpc({command:"readonly-checkpoint",phase:"edited-unsaved-material"});
 check(!visible($("goal-card-form")),"Goal authoring waits for an explicit saved material and next action");
 await click("resource-save");await wait(()=>visible($("natural-prep-goal-next")),"material saved and explicit next step");
 const savedMaterials=requests.filter(row=>row.method==="POST"&&row.path===`/api/projects/${info.project}/resources`);check(savedMaterials.length===1&&savedMaterials[0].status===201,"one explicit material save uses existing resource API");
 resourceId=savedMaterials[0].response.id;check(/^res_[a-f0-9]{32}$/.test(resourceId)&&resourceId!==info.original_resource&&savedMaterials[0].body.content===info.content,"new material identity comes from actual save response");
 check(writes().length===1&&usePosts().length===0&&!visible($("goal-card-form")),"material save creates no Goal or Run and does not advance without user action");await rpc({command:"saved-input-checkpoint",resource_id:resourceId});
 await click("natural-prep-goal-next");check(visible($("goal-card-form")),"explicit next action shows original shared Goal form");
 const refs=[...$("goal-card-resources").selectedOptions].map(option=>option.value);check(refs.length===1&&refs[0]===resourceId,"new Goal explicitly binds only newly saved material");
 await edit("goal-card-title",`New ${info.family.toUpperCase()} user input`);await edit("goal-card-goal","Extract duties, conditions, exceptions and pending choices into a reusable cited review checklist");
 await edit("goal-card-known","");await edit("goal-card-assumptions","");await edit("goal-card-unresolved",Array.from({length:16},(_,n)=>`Human question ${n}`).join("\n"));await edit("goal-card-constraints","Preserve the full source and uncertain relations");await edit("goal-card-acceptance_checks","Human review of completeness and meaning");
 check(writes().length===1&&usePosts().length===0,"editing Goal does not save or execute");await click("goal-card-save");await wait(()=>visible($("natural-prep-return")),"saved Goal permits explicit return");
 const savedGoals=requests.filter(row=>row.method==="POST"&&row.path===`/api/projects/${info.project}/goal-cards`);check(savedGoals.length===1&&savedGoals[0].status===201,"one explicit Goal save uses existing shared Goal API");
 goalId=savedGoals[0].response.id;check(/^goal_[a-f0-9]{32}$/.test(goalId)&&goalId!==info.original_goal&&JSON.stringify(savedGoals[0].body.resource_refs)===JSON.stringify([resourceId]),"actual new Goal response preserves exact selected material binding");
 check(writes().length===2&&usePosts().length===0,"saving material and Goal does not preview or automatically create a Run");await rpc({command:"saved-input-checkpoint",resource_id:resourceId,goal_id:goalId});
 const beforeReturn=writes().length;await click("natural-prep-return");await wait(()=>visible($("pb-use-panel"))&&$("pb-use-material").value===resourceId&&$("pb-use-goal").value===goalId,"explicit return binds new inputs");
 check(writes().length===beforeReturn,"explicit return only reauthorizes with GET reads");
 check(w.eval("activeApp")===info.app&&w.eval("engineering.instance.id")===info.instance&&w.eval("engineering.instance.release_id")===info.release,"return restores exact original app Release and instance");
 check(!visible($("natural-use-preparation"))&&!$("pb-use-proof").textContent&&!$("pb-use-ack").checked&&$("pb-use-submit").disabled,"return preserves blank preview and explicit fresh consent before execution");await rpc({command:"readonly-checkpoint",phase:"returned-without-run"});
 await click("pb-use-preview");const review=JSON.parse($("pb-use-proof").textContent);
 check(review.namespace===info.family+"-natural-per-run.v1"&&review.app_id===info.app&&review.release_id===info.release&&review.instance_id===info.instance,"existing family per-use review retains original saved application identity");
 check(review.target_goal.card_id===goalId&&review.variable_bindings.resource_id===resourceId&&review.preview.source_content===info.content,"explicit preview reads exactly newly authored material and Goal");
 check($("pb-use-submit").disabled&&review.new_model_requests===0,"preview starts no model and still requires explicit acknowledgement");await confirm("pb-use-ack");await click("pb-use-submit");
 runId=w.eval("engineering.run.id");check(!!runId&&!info.original_runs.includes(runId)&&usePosts().length===1,"one explicit confirmation creates one distinct new Run");
 await rpc({command:"worker",run_id:runId});await click("internal-refresh");await sameRunOwner();
 check($("internal-data").textContent.includes("规范成果 v1")&&$("internal-data").textContent.includes("规范成果 v2"),"new result version appends while original result remains visible");
 const result=[...$("internal-data").querySelectorAll(".spec-result")].find(el=>el.querySelector("h3")?.textContent==="规范成果 v2");await click(result.querySelector('[data-spec-action="view"]'));check(result.textContent.includes("field beacon"),"new persisted result is readable from this Run");
 const beforeCold=writes().length;await boot();await openEntry();check(writes().length===beforeCold,"cold page reopening is GET only and creates no saved-input or Run writes");check(!visible($("natural-use-preparation")),"cold page does not reopen or execute old preparation intent");await sameRunOwner();await rpc({command:"readonly-checkpoint",phase:"cold-read-only"});
 check(usePosts().length===1,"preparation return cold open and result reads never duplicate submission");status="PASS";
 }catch(e){error=e.stack||String(e);process.stderr.write(error+"\n");process.exitCode=1;}finally{
 try{await closePage();}catch(e){error=error||String(e);status="FAIL";process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,family:info.family,resource_id:resourceId,goal_id:goalId,run_id:runId,checks,actions,requests,static_resource_loads:assets,boots,
 classification:"ACTUAL_TESTCLIENT_HTTP_VISIBLE_SHARED_FORMS_ACTUAL_WORKER_MOCK_TRANSPORT",interval_scheduler:"DISABLED_MANUAL_REFRESH",real_model:"NOT_RUN",native_browser:"NOT_RUN",real_human_semantic_acceptance:"NOT_RUN"},null,2));
 process.stdout.write(JSON.stringify({done:true})+"\n");}})();
