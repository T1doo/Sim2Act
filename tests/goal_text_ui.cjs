"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],hashes={},pending=new Map(),userActions=[],staticResourceLoads=[];
let serial=0,bootCount=0,dom,w,$,fault="",hold=null,expectedApp=null;
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
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const css=await load("/app.css");hashes["app.css"]=crypto.createHash("sha256").update(css).digest("hex");const style=w.document.createElement("style");style.textContent=css;w.document.head.append(style);
 w.fetch=async(url,options={})=>{
  const request={path:url,method:options.method||"GET",body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const result=await rpc(request);
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
 else await click($("goal-card-list").querySelector("button"));
}
function assertHandoff(label){
 check(visible($("apps"))&&!visible($("projects"))&&w.document.querySelector('#workspace-nav [data-tab=apps]').getAttribute("aria-current")==="true",`${label}: apps workspace actually visible`);
 check(w.eval("activeApp")===expectedApp&&JSON.parse($("app-manifest").textContent).candidate.manifest.app_id===expectedApp,`${label}: exact generated app and manifest selected`);
 check(visible($("app-agent-term"))&&visible($("app-preview-submit"))&&visible($("internal-prepare")),`${label}: preview and instance entry controls visible`);
 check(w.document.activeElement===$("app-agent-term"),`${label}: visible term receives focus`);
 check($("app-create-status").textContent.includes(expectedApp),`${label}: visible confirmation status identifies exact app`);
}
(async()=>{try{
 await boot();check(visible($("goal-application-start"))&&!$("goal-application-start").disabled,"saved non-CSV goal has visible generation entry");await edit("goal-card-goal","UNSAVED MUST NOT BECOME GOAL");
 if(info.scenario==="lost-generation")fault="generation";
 if(info.scenario.startsWith("poison-"))fault=info.scenario;
 if(info.scenario==="late-generation"){
  fault="late-generation";const action=click("goal-application-start");await wait(()=>hold);const release=hold;hold=null;
  await edit("project-select",info.other);check(!w.eval("activeGoalCard"),"changed project clears old selected goal");const count=requests.length;release();await action;
  check(requests.length===count,"late accepted generation performs no changed-selection followup");check(!$("goal-application-proof").textContent,"late response cannot paint protected source");
  await edit("project-select",info.project);await click($("goal-card-list").querySelector("button"));await edit("goal-card-goal","UNSAVED MUST NOT BECOME GOAL");
 }else await click("goal-application-start");
 const generation=requests.find(request=>request.method==="POST"&&request.path.endsWith("/application-runs"));
 check(Object.keys(generation.body).sort().join(",")==="expected_fingerprint,expected_version,request_key","generation carries exact saved-version intent");
 check($("goal-application-confirm").disabled,"queued or unknown generation has no confirmation");
 let count=posts();await click("goal-application-read");check(posts()===count,"generation recovery uses GET only");
 if(info.scenario.startsWith("poison-")){
  check(!requests.some(request=>request.path.includes("/api/runs/run_"+"b".repeat(32))||request.path.includes("[object Object]")),"unverified POST id never selects a Run read route");
  check(requests.some(request=>request.method==="GET"&&request.path.includes("/application-runs?request_key="+generation.body.request_key)),"poisoned acceptance recovered with original request key");
 }
 await rpc({command:"worker"});await click("goal-application-read");
 const proof=JSON.parse($("goal-application-proof").textContent);expectedApp=proof.candidate.manifest.app_id;
 check(proof.semantic_status==="UNKNOWN"&&proof.goal_acceptance==="NOT_RUN","candidate-ready keeps semantic and goal gaps visible");
 check(proof.candidate.goal.goal!=="UNSAVED MUST NOT BECOME GOAL","full saved goal excludes unsaved editing");
 check(proof.candidate.actions[0].executor.ref==="text.literal_evidence","provider graph uses registered non-CSV executor");
 check(proof.candidate.goal.constraints.length===2&&proof.candidate.goal.unresolved.length===1,"hard constraints and unresolved items preserved");
 check($("goal-application-confirm").disabled,"exact candidate awaits explicit confirmation");await click("goal-application-ack");check(!$("goal-application-confirm").disabled,"visible ack enables exact candidate");await edit("goal-application-name","Visible literal app");
 let draft=$("goal-card-goal").value;
 if(info.scenario==="lost-confirm")fault="confirmation";
 if((info.scenario.startsWith("late-confirm-")&&info.scenario!=="late-confirm-read-edit-undo")||["late-app-read","late-internal-read"].includes(info.scenario)){
  fault=info.scenario.startsWith("late-confirm-")?"late-confirm":info.scenario;
  const action=click("goal-application-confirm");await wait(()=>hold);const release=hold;hold=null;
  if(info.scenario==="late-confirm-edit"){draft="NEW UNSAVED DRAFT WHILE CONFIRMING";await edit("goal-card-goal",draft);}
  else if(info.scenario==="late-confirm-edit-undo")await editGoalAndUndo();
  else if(info.scenario==="late-confirm-app"){await nav("apps");await click(appButton("Other app"));check(w.eval("activeApp")===info.other_app,"user chose another visible app while confirmation pending");}
  else if(info.scenario==="late-confirm-goal"){await click("goal-card-new");draft="NEW UNRELATED GOAL DRAFT";await edit("goal-card-goal",draft);}
  else{await nav("resources");await nav("projects");}
  const focus=w.document.activeElement;release();await action;
  check(w.document.activeElement===focus,"stale handoff does not steal current focus");check($("goal-card-goal").value===draft,"stale handoff preserves current unsaved goal draft");
  if(info.scenario==="late-confirm-app"){check(visible($("apps"))&&w.eval("activeApp")===info.other_app,"stale confirmation cannot replace newer selected app");await nav("projects");}
  else check(visible($("projects"))&&!visible($("apps")),"stale handoff does not navigate after newer user intent");
  if(info.scenario==="late-confirm-goal"){check(!w.eval("activeGoalCard"),"stale confirmation cannot reselect prior goal");await click($("goal-card-list").querySelector("button"));draft=$("goal-card-goal").value;}
 }else{
  await click("goal-application-confirm");
  if(info.scenario!=="lost-confirm")assertHandoff("confirmation");
 }
 if(visible($("apps")))await nav("projects");
 check($("goal-card-goal").value===draft,"handoff leaves unsaved goal editor intact");
 if(info.scenario==="late-confirm-read-edit-undo"){
  count=posts();fault="late-confirm-read";const action=click("goal-application-confirm-read");await wait(()=>hold);const release=hold;hold=null;
  await editGoalAndUndo();const focus=w.document.activeElement;release();await action;
  check(posts()===count,"stale confirmation recovery still uses original key GET only");
  check(w.document.activeElement===focus,"edit undo during keyed recovery prevents stale focus takeover");
  check(visible($("projects"))&&!visible($("apps")),"edit undo during keyed recovery prevents stale navigation");
  check($("goal-card-goal").value===draft,"stale keyed recovery preserves original unsaved draft after undo");
 }
 count=posts();await click("goal-application-confirm-read");check(posts()===count,"confirmation recovery uses original key GET only");assertHandoff("read recovery");
 check($("app-column-label").hidden&&!$("app-agent-term-label").hidden,"text app uses term rather than CSV column");check($("internal-agent").hidden,"text app needs no Replay upload");
 await edit("app-agent-term","Alpha");await click("app-preview-submit");check($("app-output").textContent.includes("Alpha obligation retained"),"visible native preview submit computes source sample");
 await edit("app-agent-term","Alpha");await click("internal-prepare");check(visible($("internal-approval"))&&$("internal-commit").disabled,"visible exact approval requires consent");
 await click("internal-approval-ack");await click("internal-commit");const create=$("internal-releases").querySelector("button");check(visible(create),"verified internal version has visible create button");await click(create);
 const app=w.eval("activeApp"),instance=w.eval("engineering.instance.id");check(!!instance,"visible action creates empty instance");
 count=posts();await boot(app);const instanceButton=[...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(instance));await click(instanceButton);check(posts()===count,"cold page uses visible read controls without automatic POST");
 await edit("internal-term","Beta");await click("internal-run-submit");await rpc({command:"worker"});await click("internal-refresh");
 check(visible($("internal-data"))&&$("internal-data").textContent.includes("Beta due tomorrow")&&$("internal-data").textContent.includes("<em>Beta literal</em>"),"cold unseen term yields visible actual whole-line results");
 check(!$("internal-data").querySelector("em"),"source quote renders literal text");check(!$("internal-data").textContent.includes("Alpha obligation"),"new result differs from preview sample");
 const dataBefore=$("internal-data").textContent;await edit("internal-term","");count=posts();await click("internal-run-submit");check(posts()===count,"native required input blocks blank submit before any POST");
 await edit("internal-term"," Beta");await click("internal-run-submit");await rpc({command:"worker"});await click("internal-refresh");
 check($("internal-runs").textContent.includes("FAILED"),"browser-valid but contract-invalid input leaves actual FAILED history");check($("internal-data").textContent===dataBefore,"failed input appends no partial result");
 check(requests.filter(request=>request.method==="POST"&&request.path.endsWith("/application-runs")).length===1,"one generation POST across all receipt recovery");
 check(requests.filter(request=>request.method==="POST"&&request.path.endsWith("/confirm-application-candidate")).length===1,"one precise confirmation POST");
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,user_actions:userActions,static_resource_loads:staticResourceLoads,loaded_source_sha256:hashes,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",scenario:info.scenario,app,instance},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }catch(error){fs.writeFileSync(info.output,JSON.stringify({status:"FAIL",checks,requests,user_actions:userActions,static_resource_loads:staticResourceLoads,text:dom?.window.document.body.textContent},null,2));dom?.window.close();process.stderr.write(error.stack+"\n");process.exit(1);}})();
