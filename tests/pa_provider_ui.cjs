"use strict";
const durableBrowser=require("./durable_browser.cjs")();
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],hashes={},pending=new Map(),userActions=[],staticResourceLoads=[];
let serial=0,bootCount=0,dom,w,$,fault="",hold=null,expectedApp=null,heldOwnerState=null,readOrderEvidence=null;
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
 dom=new JSDOM(html,{url:"http://offline.test/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;durableBrowser.install(w);$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const css=await load("/app.css");hashes["app.css"]=crypto.createHash("sha256").update(css).digest("hex");const style=w.document.createElement("style");style.textContent=css;w.document.head.append(style);
 w.fetch=async(url,options={})=>{
  const request={path:url,method:options.method||"GET",body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const result=await rpc(request);
  if(fault==="binding-lost"&&request.method==="POST"&&url.endsWith("/material-bindings")){fault="";assert.equal(result.status,201);throw Error("injected accepted typed binding response lost");}
  if(fault==="binding-late"&&request.method==="POST"&&url.endsWith("/material-bindings")){fault="";assert.equal(result.status,201);await new Promise(resolve=>hold=resolve);}
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
  const paused=(fault==="late-generation"&&request.method==="POST"&&url.endsWith("/application-runs"))||(fault==="late-confirm"&&request.method==="POST"&&url.endsWith("/confirm-application-candidate"))||(fault==="late-confirm-read"&&request.method==="GET"&&url.includes("/confirmed-application-candidate?request_key="))||(fault==="late-app-read"&&request.method==="GET"&&url===`/api/apps/${expectedApp}`)||(fault==="late-internal-read"&&request.method==="GET"&&url===`/api/internal/apps/${expectedApp}/instances`);
  if(paused){fault="";await new Promise(resolve=>hold=resolve);}
  return new Response(result.text,{status:result.status,headers:{"Content-Type":result.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const name=script.getAttribute("src").slice(1),code=await load("/"+name);hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const node=w.document.createElement("script");node.textContent=code;w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);
 if(app){await nav("apps");await click(appButton("Visible literal app"));check(w.eval("activeApp")===app,"cold page opens exact app through visible list");}
 else await click([...$("goal-card-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes("Literal references")));
}
function assertHandoff(label){
 check(visible($("apps"))&&!visible($("projects"))&&w.document.querySelector('#workspace-nav [data-tab=apps]').getAttribute("aria-current")==="true",`${label}: apps workspace actually visible`);
 check(w.eval("activeApp")===expectedApp&&JSON.parse($("app-manifest").textContent).candidate.manifest.app_id===expectedApp,`${label}: exact generated app and manifest selected`);
 check(visible($("app-agent-term"))&&visible($("app-preview-submit"))&&visible($("internal-prepare")),`${label}: preview and instance entry controls visible`);
 check(w.document.activeElement===$("app-agent-term"),`${label}: visible term receives focus`);
 check($("app-create-status").textContent.includes(expectedApp),`${label}: visible confirmation status identifies exact app`);
}
(async()=>{try{
 await boot();check(visible($("goal-provider-refresh")),"explicit approved-provider entry visible on saved natural goal");
 check($("goal-provider-select").value==="","no provider approval automatically selected");
 if(info.scenario==="scope-late"){
  fault="scope-late";const action=click("goal-provider-refresh");await wait(()=>hold);const release=hold;hold=null;
  await editGoalAndUndo();release();await action;
  check($("goal-provider-select").options.length===1&&!$("goal-provider-proof").textContent,"late scope read after editor ABA cannot install private approval");
 }
 const initialPosts=posts();await click("goal-provider-refresh");
 check(posts()===initialPosts&&$("goal-provider-select").options.length===2,"existing scope read uses GET and creates no approval or Run");
 check($("goal-provider-select").value==="","read scope remains unselected");
 await edit("goal-provider-select",info.approval_id);
 check($("goal-provider-proof").textContent.includes(info.approval_id)&&$("goal-provider-proof").textContent.includes("OFFLINE_TEST"),"explicit synthetic scope proof identifies exact bounded source");
 await click("goal-application-start");
 const generation=requests.find(r=>r.method==="POST"&&r.path.endsWith("/application-runs"));
 check(generation.body.activation.approval_id===info.approval_id&&generation.body.request_key==="exact-generation","submitted run binds selected approval and its original key");
 check($("goal-application-confirm").disabled,"queued application is not confirmable");
 await rpc({command:"provider-worker"});await click("goal-application-read");
 const proof=JSON.parse($("goal-application-proof").textContent);expectedApp=proof.candidate.manifest.app_id;
 check(proof.candidate.manifest.workflow[0].step_id==="provider_chosen_literal_report","model-chosen actual graph survives page candidate proof");
 check(proof.semantic_status==="UNKNOWN"&&proof.goal_acceptance==="NOT_RUN","protocol generation does not claim human semantic acceptance");
 await click("goal-application-ack");await click("goal-application-confirm");assertHandoff("model candidate confirmation");
 await nav("projects");await click([...$("goal-card-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes("Explicit UI new-material goal")));
 check(w.eval("activeGoalCard.id")===info.target_card,"user visibly opens separately saved target goal");
 await click("pa-binding-sources");check($("pa-binding-source").options.length===2&&$("pa-binding-source").value==="","cold source index requires explicit model source choice");
 await edit("pa-binding-source",proof.run_id);await click("pa-binding-preview");
 const preview=JSON.parse($("pa-binding-proof").textContent);
 check(preview.resource_id===info.target_resource&&preview.target_goal.card_id===info.target_card&&preview.model_graph.manifest.workflow[0].step_id==="provider_chosen_literal_report","typed preview shows exact new material and preserves actual model steps");
 check($("pa-binding-save").disabled,"preview does not automatically confirm binding");
 await edit("pa-binding-name","Visible literal app");await click("pa-binding-ack");
 if(info.scenario==="binding-lost")fault="binding-lost";
 if(info.scenario==="binding-late"){
  fault="binding-late";const action=click("pa-binding-save");await wait(()=>hold);const release=hold;hold=null;
  await editGoalAndUndo();const focus=w.document.activeElement,count=requests.length;release();await action;
  check($("pa-binding-open").disabled&&w.document.activeElement===focus&&requests.length===count,"late accepted binding after editor ABA cannot install result, focus, navigation or followup");
 }else await click("pa-binding-save");
 {const count=posts();await click("pa-binding-recover");check(posts()===count,"lost or successful typed save recovers only original key GET");
  expectedApp=w.eval("paBindingState.saved.id");await click("pa-binding-open");assertHandoff("explicit new material open");
  const manifest=JSON.parse($("app-manifest").textContent).candidate;
  check(manifest.namespace===preview.namespace&&manifest.manifest.data_bindings[0].resource_ref===info.target_resource,"opened app has exact typed namespace and target resource");
  await edit("app-agent-term","Gamma");await click("internal-prepare");check(visible($("internal-approval"))&&$("internal-commit").disabled,"new material precheck requires separate internal version confirmation");
  await click("internal-approval-ack");await click("internal-commit");await click($("internal-releases").querySelector("button"));
  const instance=w.eval("engineering.instance.id"),app=w.eval("activeApp");check(!!instance,"visible gestures create new material empty instance");
  const before=posts();await boot(app);await click([...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(instance)));check(posts()===before,"cold page recovers app and instance using GET only");
  await edit("internal-term","Gamma");await click("internal-run-submit");await rpc({command:"cold-worker"});await click("internal-refresh");
  check($("internal-data").textContent.includes("Gamma fresh material")&&$("internal-data").textContent.includes("Gamma not an old report"),"cold real Worker returns actual new-material whole-line citations");
  check(!$("internal-data").textContent.includes("Beta due tomorrow"),"new material computation never returns old source result");
 }
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/application-runs")).length===1,"one exact generation submission");
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/material-bindings")).length===1,"one binding submission despite unknown outcome recovery");
 check(!requests.some(r=>r.method==="POST"&&r.path.includes("application-provider-scopes")),"page never prepares approves or configures a model scope");
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,user_actions:userActions,static_resource_loads:staticResourceLoads,loaded_source_sha256:hashes,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",scenario:info.scenario,model_requests:"SYNTHETIC_ONLY"},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:"FAIL",checks,requests,user_actions:userActions,text:dom?.window.document.body.textContent},null,2));dom?.window.close();process.stderr.write(error.stack+"\n");process.exit(1);}})();
