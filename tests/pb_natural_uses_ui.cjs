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
  if(fault==="lost"&&request.method==="POST"&&path.endsWith("/pb-use-runs")){fault="";assert.equal(result.status,202);throw Error("actual accepted P-B response lost");}
  if((fault==="review-late-navigation"&&path.endsWith("/pb-use-reviews"))||(fault==="commit-late-navigation"&&request.method==="POST"&&path.endsWith("/pb-use-runs"))){fault="";assert.equal(result.status,path.endsWith("/pb-use-runs")?202:200);await new Promise(resolve=>hold=resolve);}
  if(fault==="receipt-poison"&&request.method==="GET"&&path.includes("/pb-use-requests/")){fault="";const value=JSON.parse(result.text);value.request_key="wrong-key";return new Response(JSON.stringify(value),{status:result.status});}
  return new Response(result.text,{status:result.status,headers:{"Content-Type":result.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);await nav("apps");
}
async function main(){
 await boot();await click([...$("app-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.name)));
 await click([...$("internal-instances").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.instance)));
 check(visible($("pb-use-panel")),"same saved P-B app exposes explicit per-use form");
 await edit("pb-use-material",info.target_resource);await edit("pb-use-goal",info.target);
 if(info.scenario==="review-late-navigation"){
  fault=info.scenario;const request=click("pb-use-preview");await wait(()=>!!hold);
  check($("pb-use-goal").disabled&&$("pb-use-material").disabled,"pending preview freezes material and Goal inputs");
  await nav("resources");hold();hold=null;await request;await nav("apps");
  await click([...$("internal-instances").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.instance)));
  check(w.eval("pbUseView.review===null")&&$("pb-use-proof").textContent==="","late preview cannot bind newly selected view");check($("pb-use-submit").disabled,"late preview cannot enable commit");
  await edit("pb-use-material",info.target_resource);await edit("pb-use-goal",info.target);
 }
 await click("pb-use-preview");check(w.eval("pbUseView.review!==null"),"typed material and Goal preview verified");
 check($("pb-use-proof").textContent.includes(info.target_resource),"full review displays exact material");check($("pb-use-submit").disabled,"explicit consent required");await click("pb-use-ack");
 if(info.scenario==="commit-late-navigation"){
  fault=info.scenario;const request=click("pb-use-submit");await wait(()=>!!hold);const count=requests.filter(r=>r.path.includes("/pb-use-requests/")).length;await nav("resources");hold();hold=null;await request;
  check(requests.filter(r=>r.path.includes("/pb-use-requests/")).length===count,"late response cannot follow into another page");
  await nav("apps");await click([...$("internal-instances").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.instance)));
  check($("pb-use-preview").disabled&&$("internal-run-submit").disabled,"unknown use fences both new and default run controls");await click("pb-use-recover");
 }else{
  if(["lost","receipt-poison"].includes(info.scenario))fault=info.scenario;await click("pb-use-submit");
  if(["lost","receipt-poison"].includes(info.scenario)){check(w.eval("pbUsePending.size")===1,"unknown receipt retains exact pending intent");check($("pb-use-preview").disabled&&$("internal-run-submit").disabled,"unknown intent disables duplicate default and explicit submit");await click("pb-use-recover");}
 }
 check(countPost("/pb-use-runs")===1,"recovery never repeats POST");check(w.eval("pbUsePending.size")===0,"verified original receipt clears pending");
 const run=w.eval("engineering.run.id");check(w.eval("activeApp")===info.app&&w.eval("engineering.instance.id")===info.instance,"same app and instance retained");
 await rpc({command:"cold-worker",run_id:run,instance_id:info.instance});
 await boot();await click([...$("app-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.name)));await click([...$("internal-instances").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.instance)));
 check($("internal-data").textContent.includes("规范成果 v1"),"cold page loads saved typed result");await click(w.document.querySelector('[data-spec-action="view"]'));
 check($("internal-data").textContent.includes("field beacon")&&!$("internal-data").textContent.includes("garden sensor")&&!$("internal-data").textContent.includes("desk lamp"),"third material result excludes earlier answers");
 check($("internal-data").textContent.includes("语义 UNKNOWN")&&$("internal-data").textContent.includes("人工验收 PENDING"),"semantic and human boundary preserved");
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,user_actions:actions,loaded_source_sha256:loaded,scenario:info.scenario,browser:"JSDOM_NOT_NATIVE",api:"IPC_IN_PROCESS_HTTP",real_model_requests:0},null,2));process.stdout.write(JSON.stringify({done:true})+"\n");dom.window.close();process.exit(0);
}
main().catch(error=>{process.stderr.write(error.stack+"\n");process.exit(1);});
