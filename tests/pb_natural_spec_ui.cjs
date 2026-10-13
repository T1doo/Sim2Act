"use strict";
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],loaded={},actions=[],loads=[],pending=new Map();
let serial=0,dom,w,$,fault="",hold=null;
readline.createInterface({input:process.stdin}).on("line",line=>{const value=JSON.parse(line);pending.get(value.id)(value);pending.delete(value.id);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(condition,label)=>{assert(condition,label);checks.push(label);};
const wait=async fn=>{const end=Date.now()+15000;while(Date.now()<end){if(fn())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("offline bounded wait");};
function visible(element){for(let node=element;node;node=node.parentElement){if(node.hidden||node.hasAttribute("inert"))return false;const style=w.getComputedStyle(node);if(style.display==="none"||style.visibility==="hidden")return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(element))return false;}return !!element?.isConnected;}
async function gesture(element,perform,properties){
 assert(visible(element),`visible gesture: ${element?.id||element?.textContent}`);assert(!element.matches(":disabled"),`enabled gesture: ${element?.id}`);element.focus();const work=[],restore=[];
 for(const [node,key] of properties){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[key]=wrapper;restore.push(()=>{if(node[key]===wrapper)node[key]=original;});}
 actions.push({element:element.id||element.textContent,event:"native DOM dispatch",visible:true,enabled:true});
 try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const click=value=>{const element=typeof value==="string"?$(value):value;return gesture(element,()=>element.click(),[[element,"onclick"],[element.form,"onsubmit"]]);};
const edit=(element,value)=>{if(typeof element==="string")element=$(element);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event("input",{bubbles:true}));element.dispatchEvent(new w.Event("change",{bubbles:true}));},[[element,"oninput"],[element,"onchange"]]);};
const nav=tab=>click(w.document.querySelector(`#workspace-nav [data-tab=${tab}]`));
const countPost=suffix=>requests.filter(request=>request.method==="POST"&&request.path.endsWith(suffix)).length;
async function boot(){
 if(dom)dom.window.close();const load=async path=>{const response=await rpc({path,method:"GET"});assert.equal(response.status,200);const name=path==="/"?"index.html":path.slice(1),sha=crypto.createHash("sha256").update(response.text).digest("hex");loaded[name]=sha;loads.push({path,status:response.status,sha256:sha,bytes:Buffer.byteLength(response.text)});return response.text;};
 dom=new JSDOM(await load("/"),{url:"http://offline.test/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={path,method:options.method||"GET",body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const result=await rpc(request);
  if(fault==="lost"&&request.method==="POST"&&path.endsWith("/extractions")){fault="";assert.equal(result.status,201);throw Error("actual accepted P-B response lost");}
  if((fault==="review-late-edit"&&path.endsWith("/extraction-reviews"))||(fault==="commit-late-navigation"&&request.method==="POST"&&path.endsWith("/extractions"))){fault="";assert.equal(result.status,path.endsWith("/extractions")?201:200);await new Promise(resolve=>hold=resolve);}
  if(fault==="receipt-poison"&&request.method==="GET"&&path.includes("/extractions/by-key/")){fault="";const value=JSON.parse(result.text);value.request_key="wrong-key";return new Response(JSON.stringify(value),{status:result.status});}
  return new Response(result.text,{status:result.status,headers:{"Content-Type":result.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);await nav("apps");
}
async function main(){
 await boot();await click([...$("app-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(info.source_name)));
 await click([...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(info.instance)));
 check(w.eval("engineering.instance.id")===info.instance,"selected actual successful source instance");
 const sourceButton=()=>w.document.querySelector('[data-spec-action="extract"]');check(visible(sourceButton()),"independent P-B entry is visible on saved successful result");await click(sourceButton());
 check($("pb-spec-status").textContent.includes("已核对成功来源"),"actual success provenance loaded before editing");
 await edit("pb-spec-target",info.target);const modelId=w.document.querySelector('[data-pb-step="1"]');await edit(modelId,"user_edited_inference");await edit("pb-spec-name","User reviewed P-B checklist");
 if(info.scenario==="review-late-edit"){
  fault=info.scenario;const request=click("pb-spec-preview");await wait(()=>!!hold);const name=$("pb-spec-name").value;await edit("pb-spec-name",name+" changed");await edit("pb-spec-name",name);hold();hold=null;await request;
  check(w.eval("naturalTaskExtraction.review===null"),"edit then undo rejects late review through monotonic edit generation");check($("pb-spec-commit").disabled,"late review cannot enable confirmation");
 }
 await click("pb-spec-preview");check($("pb-spec-proof").textContent.includes("user_edited_inference"),"review contains actual edited stable recipe");
 check($("pb-spec-proof").textContent.includes(info.target_resource)&&$("pb-spec-proof").textContent.includes(info.target),"review binds exact new material and own Goal");
 check($("pb-spec-proof").textContent.includes("Human question 15")&&$("pb-spec-proof").textContent.includes("NOT_RUN"),"full human unresolved items and unexecuted edited graph retained");check($("pb-spec-commit").disabled,"separate exact confirmation is required");
 await click("pb-spec-ack");
 if(info.scenario==="commit-late-navigation"){
  fault=info.scenario;const request=click("pb-spec-commit");await wait(()=>!!hold);const reads=requests.filter(r=>r.path.includes("/extractions/by-key/")).length;await nav("commands");hold();hold=null;await request;
  check(requests.filter(r=>r.path.includes("/extractions/by-key/")).length===reads,"late commit cannot follow response into new workspace");check(w.eval("naturalTaskRequests.size")===1,"late navigation preserves exact pending intent");
  await nav("apps");await click(sourceButton());check($("pb-spec-preview").disabled,"reopened unknown intent cannot create a replacement request");await click("pb-spec-recover");
 }else{
  if(["lost","receipt-poison"].includes(info.scenario))fault=info.scenario;await click("pb-spec-commit");
  if(["lost","receipt-poison"].includes(info.scenario)){check(w.eval("naturalTaskRequests.size")===1&&$("pb-spec-open").disabled,"lost or poisoned receipt cannot clear pending or open app");check($("pb-spec-preview").disabled&&$("pb-spec-commit").disabled,"unknown outcome prohibits another write intent");await click("pb-spec-recover");}
 }
 const saved=w.eval("naturalTaskExtraction.saved");check(saved?.kind==="pb_natural_spec_task.v1"&&saved.source_run_id===info.run,"independent source marker and original-key receipt verified");
 check(countPost("/extractions")===1,"exactly one extraction POST across recovery and navigation");check(w.eval("naturalTaskRequests.size")===0,"only verified original intent clears pending");
 await click("pb-spec-open");check(w.eval("activeApp")===saved.id&&$("app-origin").textContent.includes("P-B"),"exact task-origin app opened through visible action");
 check($("app-manifest").textContent.includes("user_edited_inference"),"selected app keeps user-edited recipe rather than source output");
 await click("internal-prepare");await click("internal-approval-ack");await click("internal-commit");await click($("internal-releases").querySelector("button"));
 await click("internal-run-submit");const instanceId=w.eval("engineering.instance.id");await rpc({command:"cold-worker"});
 await boot();await click([...$("app-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes("User reviewed P-B checklist")));
 await click([...$("internal-instances").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(instanceId)));
 check($("internal-data").textContent.includes("规范成果 v1"),"cold page reads new actual typed result version");await click(w.document.querySelector('[data-spec-action="view"]'));
 check($("internal-data").textContent.includes("garden sensor")&&!$("internal-data").textContent.includes("desk lamp"),"fresh authorized result contains new material without old answers");
 check($("internal-data").textContent.includes("语义 UNKNOWN")&&$("internal-data").textContent.includes("人工验收 PENDING"),"cold result preserves semantic and human boundary");
 check(requests.every(r=>!r.path.includes("application-provider-scopes")||r.method==="GET"),"no model approval or credential configuration writes");
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,user_actions:actions,static_resource_loads:loads,loaded_source_sha256:loaded,scenario:info.scenario,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",real_model_requests:0},null,2));
 process.stdout.write(JSON.stringify({done:true})+"\n");dom.window.close();process.exit(0);
}
main().catch(error=>{process.stderr.write(error.stack+"\n");process.exit(1);});
