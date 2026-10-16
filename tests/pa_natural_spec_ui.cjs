"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],hashes={},pending=new Map(),userActions=[],staticResourceLoads=[];
let serial=0,bootCount=0,dom,w,$,fault="",hold=null,expectedApp=null,heldOwnerState=null,readOrderEvidence=null;
const downloads=[],downloadWork=[];
const durableBrowser=require("./durable_browser.cjs")();
readline.createInterface({input:process.stdin}).on("line",line=>{const result=JSON.parse(line),resolve=pending.get(result.id);pending.delete(result.id);resolve(result);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async fn=>{const end=Date.now()+15000;while(Date.now()<end){if(fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("offline bounded wait");};
function visible(element){
 if(!element?.isConnected)return false;
 for(let node=element;node;node=node.parentElement){
  if(node.hidden||node.hasAttribute("inert")||node.getAttribute("aria-hidden")==="true")return false;
  const style=w.getComputedStyle(node);if(style.display==="none"||["hidden","collapse"].includes(style.visibility))return false;
  if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(element))return false;
 }
 return true;
}
function usable(element){assert(visible(element),`User action must be visible: ${element?.id||element?.textContent}`);assert(!element.matches(":disabled"),`User action must be enabled: ${element.id}`);}
async function gesture(element,perform,bindings){
 usable(element);element.focus();const work=[],restores=[];
 for(const [node,property] of bindings){const original=node?.[property];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[property]=wrapper;restores.push(()=>{if(node[property]===wrapper)node[property]=original;});}
 userActions.push({element:element.id||element.textContent,workspace:w.document.querySelector("#workspace-nav [aria-current=true]")?.dataset.tab,visible:true,enabled:true,event:"native DOM dispatch"});
 try{perform();await Promise.all(work);}finally{restores.forEach(restore=>restore());}
}
const click=value=>{const element=typeof value==="string"?$(value):value;return gesture(element,()=>element.click(),[[element,"onclick"],[element.form,"onsubmit"]]);};
const edit=(id,value)=>{const element=$(id);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event("input",{bubbles:true}));element.dispatchEvent(new w.Event("change",{bubbles:true}));},[[element,"oninput"],[element,"onchange"]]);};
async function editGoalAndUndo(){
 const element=$("goal-card-goal"),original=element.value,suffix=" EDIT WHILE RECEIPT PENDING",selection=w.eval("[workspaceSelectionGeneration,appSelectionGeneration,goalSelectionGeneration,activeGoalCard.id]");
 const events=[];const record=event=>events.push({input_type:event.inputType,value:element.value});element.addEventListener("input",record);
 try{
  await gesture(element,()=>{element.setSelectionRange(original.length,original.length);element.setRangeText(suffix,original.length,original.length,"end");element.dispatchEvent(new w.InputEvent("input",{bubbles:true,inputType:"insertText",data:suffix}));},[[element,"oninput"]]);
  check(element.value===original+suffix,"actual textarea input changes draft A to B");
  await gesture(element,()=>{element.setRangeText("",original.length,original.length+suffix.length,"end");element.dispatchEvent(new w.InputEvent("input",{bubbles:true,inputType:"historyUndo",data:null}));},[[element,"oninput"]]);
  check(element.value===original&&events.length===2&&events[0].input_type==="insertText"&&events[1].input_type==="historyUndo","textarea historyUndo restores B to original A through input event");
  check(JSON.stringify(w.eval("[workspaceSelectionGeneration,appSelectionGeneration,goalSelectionGeneration,activeGoalCard.id]"))===JSON.stringify(selection),"draft edit undo leaves workspace app and goal selection generations unchanged");
  userActions.push({element:element.id,event:"JSDOM InputEvent insertText then historyUndo",visible:visible(element),enabled:!element.matches(":disabled"),input_events:events});
 }finally{element.removeEventListener("input",record);}
}
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const posts=()=>requests.filter(request=>request.method==="POST").length;
const appButton=name=>[...$("app-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(name));
async function boot(app){
 if(dom)dom.window.close();const pageBoot=++bootCount;
 const load=async asset=>{const response=await rpc({path:asset,method:"GET"});staticResourceLoads.push({boot:pageBoot,path:asset,status:response.status,content_type:response.content_type,bytes:Buffer.byteLength(response.text,"utf8"),sha256:crypto.createHash("sha256").update(response.text).digest("hex")});assert.equal(response.status,200,`Actual HTTP asset ${asset} must be available`);return response.text;};
 const html=await load("/");
 hashes["index.html"]=crypto.createHash("sha256").update(html).digest("hex");
 dom=new JSDOM(html,{url:"http://offline.test/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 durableBrowser.install(w);
 const blobs=new Map();w.URL.createObjectURL=blob=>{const key=`blob:offline-${blobs.size}`;blobs.set(key,blob);return key;};w.URL.revokeObjectURL=key=>blobs.delete(key);
 w.document.addEventListener("click",event=>{const link=event.target.closest("a[download]");if(!link)return;event.preventDefault();const blob=blobs.get(link.href),name=link.download;assert(blob);downloadWork.push(new Promise((resolve,reject)=>{const reader=new w.FileReader();reader.onload=()=>{downloads.push({name,content:reader.result,type:blob.type});resolve();};reader.onerror=reject;reader.readAsText(blob);}));},true);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const css=await load("/app.css");hashes["app.css"]=crypto.createHash("sha256").update(css).digest("hex");const style=w.document.createElement("style");style.textContent=css;w.document.head.append(style);
 w.fetch=async(url,options={})=>{
  const request={path:url,method:options.method||"GET",body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const result=await rpc(request);
  if(fault==="run-lost"&&request.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(url)){fault="";assert.equal(result.status,202);throw Error("actual accepted spec Run response lost");}
  if(fault==="run-late"&&request.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(url)){fault="";assert.equal(result.status,202);await new Promise(resolve=>hold=resolve);}
  if(fault==="run-receipt-poison"&&request.method==="GET"&&url.includes("/spec-run-requests/")){fault="";const value=JSON.parse(result.text);value.request_key="not-the-original-key";return new Response(JSON.stringify(value),{status:result.status,headers:{"Content-Type":"application/json"}});}
  if(fault==="artifact-poison"&&request.method==="GET"&&url.endsWith("/spec-artifact")){fault="";const value=JSON.parse(result.text);value.markdown_view="Unbound changed Markdown";return new Response(JSON.stringify(value),{status:result.status,headers:{"Content-Type":"application/json"}});}
  if(fault==="artifact-late"&&request.method==="GET"&&url.endsWith("/spec-artifact")){fault="";await new Promise(resolve=>hold=resolve);}
  if(fault==="binding-lost"&&request.method==="POST"&&url.endsWith("/bindings")){fault="";assert.equal(result.status,201);throw Error("injected accepted typed binding response lost");}
  if(fault==="binding-late"&&request.method==="POST"&&url.endsWith("/bindings")){fault="";assert.equal(result.status,201);await new Promise(resolve=>hold=resolve);}
  if(fault==="scope-late"&&request.method==="GET"&&url.endsWith("/application-provider-scopes")){fault="";await new Promise(resolve=>hold=resolve);}
  const ownerCommand=request.method==="POST"&&url.endsWith("/owner-review-requests")?request.body.command:null;
  if(fault==="owner-initial-read-order"&&request.method==="GET"&&url.endsWith("/owner-review")){fault="";heldOwnerState=JSON.parse(result.text);await new Promise(resolve=>hold=resolve);if(info.scenario==="owner-read-order-error")throw Error("controlled delayed initial HTTP response loss");}
  if(fault.startsWith("owner-poison-")&&request.method==="GET"&&url.includes("/owner-review")){
   const actual=JSON.parse(result.text),mode=fault;fault="";let value=structuredClone(actual);
   if(mode==="owner-poison-lower")value=structuredClone(heldOwnerState);
   if(["instance_id","project_id","principal_id","app_id"].some(k=>mode==="owner-poison-"+k)){const k=mode.slice("owner-poison-".length);value[k]="wrong-scope";}
   if(mode==="owner-poison-latest")value.latest.id="wrong-latest";
   if(mode==="owner-poison-history"){value.history[0].request_fingerprint="f".repeat(64);}
   if(mode==="owner-poison-status")value.owner_acceptance="ACCEPTED";
   if(mode==="owner-poison-key")value.recovered.request_key="different-original-key";
   readOrderEvidence.response_faults.push({mode,actual_http_response:actual,controlled_response:value});
   return new Response(JSON.stringify(value),{status:result.status,headers:{"Content-Type":"application/json"}});
  }
  if((fault==="owner-lost-prepare"&&ownerCommand==="PREPARE")||(fault==="owner-lost-decision"&&ownerCommand==="DECIDE")){fault="";assert.equal(result.status,201);throw Error("injected actual accepted owner response loss");}
  if((fault==="owner-late-prepare"&&ownerCommand==="PREPARE")||(fault==="owner-late-decision"&&ownerCommand==="DECIDE")||(fault==="owner-late-read"&&request.method==="GET"&&url.endsWith("/owner-review"))){fault="";await new Promise(resolve=>hold=resolve);}
  if(fault==="generation"&&request.method==="POST"&&url.endsWith("/application-runs")){fault="";assert.equal(result.status,202);throw Error("injected accepted generation lost");}
  if(fault==="confirmation"&&request.method==="POST"&&url.endsWith("/confirm-application-candidate")){fault="";assert.equal(result.status,200);throw Error("injected accepted confirmation lost");}
  if(fault.startsWith("poison-")&&request.method==="POST"&&url.endsWith("/application-runs")){
   const accepted=JSON.parse(result.text),mode=fault;fault="";
   if(mode==="poison-accepted-id")accepted.run_id="run_"+"b".repeat(32);
   if(mode==="poison-accepted-shape")accepted.run_id={unexpected:"id"};
   if(mode==="poison-accepted-fields"){accepted.goal_acceptance="ACCEPTED";accepted.candidate_generated=true;accepted.extra="unexpected";}
   return new Response(JSON.stringify(accepted),{status:200,headers:{"Content-Type":"application/json"}});
  }
  if(["sample-tampered","sample-nodes-tampered"].includes(info.scenario)&&request.method==="GET"&&url.endsWith("/sample-preview")){
   const value=JSON.parse(result.text);if(info.scenario==="sample-tampered")value.preview.checklist.items[0].summary="Unbound displayed assertion";else value.sample_nodes[0].items[0].summary="Unsealed received assertion";
   return new Response(JSON.stringify(value),{status:200,headers:{"Content-Type":"application/json"}});
  }
  const paused=(fault==="late-generation"&&request.method==="POST"&&url.endsWith("/application-runs"))||(fault==="late-confirm"&&request.method==="POST"&&url.endsWith("/confirm-application-candidate"))||(fault==="late-confirm-read"&&request.method==="GET"&&url.includes("/confirmed-application-candidate?request_key="))||(fault==="late-app-read"&&request.method==="GET"&&url===`/api/apps/${expectedApp}`)||(fault==="late-internal-read"&&request.method==="GET"&&url===`/api/internal/apps/${expectedApp}/instances`);
  if(paused){fault="";await new Promise(resolve=>hold=resolve);}
  return new Response(result.text,{status:result.status,headers:{"Content-Type":result.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const name=script.getAttribute("src").slice(1),code=await load("/"+name);hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const node=w.document.createElement("script");node.textContent=code;w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);
 if(app){await nav("apps");await click(appButton("Visible spec app"));check(w.eval("activeApp")===app,"cold page opens exact app through visible list");}
 else await click([...$("goal-card-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes("Operating notes")));
}

(async()=>{try{
 await boot();await edit("goal-application-family","natural_spec");
 check($("goal-provider-select").disabled&&$("goal-provider-select").value==="","spec cannot select a LIVE approval");
 check(visible($("goal-application-write-ack")),"project JSON consent is visible");
 await click("goal-application-start");check($("goal-application-confirm").disabled,"queued candidate cannot be confirmed");
 await rpc({command:"provider-worker"});await click("goal-application-read");
 if(info.scenario.startsWith("sample-")){
  check($("goal-application-confirm").disabled,"unsealed sample cannot enable confirmation");
  check($("goal-application-proof").textContent==="","unsealed sample facts are not painted");
  check($("goal-application-status").textContent.includes("VERSION_CONFLICT"),"sample contract mismatch is explicit");
  check(!requests.some(r=>r.method==="POST"&&r.path.endsWith("/confirm-application-candidate")),"no confirmation mutation for poisoned sample");
  fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,user_actions:userActions,static_resource_loads:staticResourceLoads,loaded_source_sha256:hashes,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",scenario:info.scenario,model_requests:"SYNTHETIC_ONLY"},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }
 const proof=JSON.parse($("goal-application-proof").textContent);expectedApp=proof.candidate.manifest.app_id;
 check(proof.candidate.namespace==="pa-natural-spec-app.v1"&&proof.candidate.spec_recipe.steps.length===6,"actual selected six-node model recipe displayed with pending semantic acceptance");
 check(proof.protected_sample_preview?.preview?.checklist?.items.some(i=>i.kind==="condition")&&proof.protected_sample_preview.preview.checklist.items.some(i=>i.kind==="exception")&&proof.protected_sample_preview.preview.checklist.items.some(i=>i.kind==="open_question"),"protected actual sample includes conditions exceptions and pending questions");
 check(proof.goal_acceptance==="NOT_RUN"&&proof.semantic_status==="UNKNOWN","citations do not certify semantic completeness");
 await click("goal-application-ack");check($("goal-application-confirm").disabled,"candidate ack alone grants no project save");
 await click("goal-application-write-ack");check(!$("goal-application-confirm").disabled,"explicit JSON consent enables exact confirmation");
 await edit("goal-application-name","Initial model spec app");await click("goal-application-confirm");
 check(visible($("apps"))&&w.eval("activeApp")===expectedApp&&visible($("internal-prepare")),"confirmation opens exact usable app");
 check(!visible($("app-agent-term"))&&!visible($("app-column")),"spec app needs no manually entered answer or unrelated input");
 await nav("projects");await click([...$("goal-card-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes("Cold operating notes")));
 await edit("pa-binding-family","natural");await click("pa-binding-sources");await edit("pa-binding-source",proof.run_id);await click("pa-binding-preview");
 const preview=JSON.parse($("pa-binding-proof").textContent);
 check(preview.resource_id===info.target_resource&&preview.target_goal.card_id===info.target_card,"new-material preview identifies exact current target");
 check(preview.model_graph.steps[0].step_id==="read_pick"&&$("pa-binding-save").disabled,"model steps preserved and binding remains unconfirmed");
 await edit("pa-binding-name","Visible spec app");await click("pa-binding-ack");
 if(info.scenario==="binding-lost")fault="binding-lost";
 if(info.scenario==="binding-late"){
  fault="binding-late";const action=click("pa-binding-save");await wait(()=>hold);const release=hold;hold=null;
  await editGoalAndUndo();const focus=w.document.activeElement,count=requests.length;release();await action;
  check($("pa-binding-open").disabled&&w.document.activeElement===focus&&requests.length===count,"late binding after editor undo cannot paint or navigate");
 }else await click("pa-binding-save");
 let count=posts();await click("pa-binding-recover");check(posts()===count,"accepted or lost binding recovers with original-key GET only");
 expectedApp=w.eval("paBindingState.saved.id");await click("pa-binding-open");
 check(w.eval("activeApp")===expectedApp&&visible($("internal-prepare")),"explicit open selects the exact bound app");
 await click("app-preview-submit");check($("app-output").textContent.includes("garden sensor")&&$("app-output").textContent.includes("UNSAVED_PREVIEW"),"new-source preview explicitly requires model execution and preserves source without saving");
 await click("internal-prepare");check($("internal-commit").disabled,"internal snapshot requires separate acknowledgement");
 await click("internal-approval-ack");await click("internal-commit");await click($("internal-releases").querySelector("button"));
 const instance=w.eval("engineering.instance.id"),app=w.eval("activeApp");count=posts();await boot(app);
 await click([...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(instance)));
 check(posts()===count,"cold page resumes exact instance with reads only");
 check($("owner-status").textContent.includes("请选择具体成功结果")&&$("owner-prepare").disabled&&$("owner-submit").disabled&&!requests.some(r=>r.path.endsWith("/owner-review")||r.path.endsWith("/spec-owner-review")),"spec requires explicit successful-result selection before any human acceptance or owner API read");
 if(["run-lost","run-late","run-receipt-poison"].includes(info.scenario))fault=info.scenario;
 if(info.scenario==="run-late"){
  const action=click("internal-run-submit");await wait(()=>hold);const release=hold;hold=null;await nav("projects");const reads=requests.length;release();await action;
  check(requests.length===reads,"late accepted Run cannot follow up or paint after workspace switch");await nav("apps");
 }else await click("internal-run-submit");
 if(["run-lost","run-late","run-receipt-poison"].includes(info.scenario)){
  if(info.scenario==="run-receipt-poison"){
   check($("internal-status").textContent.includes("VERSION_CONFLICT"),"wrong original-key receipt is rejected");
   await click(appButton("Visible spec app"));await click([...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(instance)));
  }
  check(!$("internal-retry").hidden&&$("internal-new-intent").hidden,"unknown spec submit retains original-key read and prevents duplicate intent");
  count=posts();await click("internal-retry");check(posts()===count,"spec Run recovery performs GET only");
 }
 await rpc({command:"cold-worker"});await click("internal-refresh");
 const savedVersion=()=>$("internal-data").querySelector(".spec-result");
 check(savedVersion()&&!savedVersion().querySelector("blockquote"),"saved version offers explicit authorized content read");
 if(info.scenario==="artifact-poison"){
  fault=info.scenario;await click(savedVersion().querySelector('[data-spec-action="md"]'));
  check(savedVersion().textContent.includes("VERSION_CONFLICT")&&!savedVersion().querySelector("blockquote")&&!downloads.length,"unbound Markdown is neither rendered nor downloaded");
 }
 if(info.scenario==="artifact-late"){
  fault=info.scenario;const action=click(savedVersion().querySelector('[data-spec-action="json"]'));await wait(()=>hold);const release=hold;hold=null;
  await nav("projects");const reads=requests.length;release();await action;
  check(!downloads.length&&requests.length===reads&&!savedVersion().querySelector("blockquote"),"late artifact cannot paint or download after workspace switch");
  await nav("apps");check(!savedVersion().querySelector('[data-spec-action="view"]').disabled,"returning to same result can explicitly read again after a discarded late response");
 }
 count=posts();await click(savedVersion().querySelector('[data-spec-action="view"]'));
 check(posts()===count,"reading saved result creates no business write or model request");
 check($("internal-data").textContent.includes("garden sensor samples")&&$("internal-data").textContent.includes("winter interval"),"cold actual worker saves newly computed constraints");
 check(savedVersion().querySelectorAll('[data-spec-kind="condition"]').length===1&&savedVersion().querySelectorAll('[data-spec-kind="exception"]').length===1&&savedVersion().querySelectorAll('[data-spec-kind="open_question"]').length===1,"readable checklist separates condition exception and unresolved decision");
 check(savedVersion().textContent.includes("Human question 15")&&savedVersion().textContent.includes("语义 UNKNOWN"),"all human unresolved items and semantic boundary remain visible");
 const artifactReads=requests.filter(r=>r.path.endsWith("/spec-artifact")).length;
 await click(savedVersion().querySelector('[data-spec-action="json"]'));await click(savedVersion().querySelector('[data-spec-action="md"]'));await Promise.all(downloadWork);
 check(downloads.length===2&&downloads.every(file=>file.content.includes("garden sensor")&&!file.content.includes("desk lamp")),"JSON and Markdown download bytes contain only current cold material");
 check(JSON.parse(downloads.find(file=>file.name.endsWith(".json")).content).owner_acceptance==="PENDING","downloaded saved JSON keeps pending semantic acceptance");
 check(requests.filter(r=>r.path.endsWith("/spec-artifact")).length===artifactReads+2&&posts()===count,"each download rechecks actual authorized artifact through GET only");
 check(requests.filter(r=>r.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(r.path)).length===1,"exactly one runtime submission despite unknown or delayed response");
 check(!$("internal-data").textContent.includes("desk lamp"),"old source answers are absent from new output");
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/application-runs")).length===1,"one generation submission");
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/bindings")).length===1,"one binding submission despite recovery");
 check(!requests.some(r=>r.method==="POST"&&r.path.includes("application-provider-scopes")),"no model scope or credential setup");
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,downloads,user_actions:userActions,static_resource_loads:staticResourceLoads,loaded_source_sha256:hashes,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",scenario:info.scenario,model_requests:"SYNTHETIC_ONLY"},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:"FAIL",checks,requests,user_actions:userActions,text:dom?.window.document.body.textContent},null,2));dom?.window.close();process.stderr.write(error.stack+"\n");process.exit(1);}})();
