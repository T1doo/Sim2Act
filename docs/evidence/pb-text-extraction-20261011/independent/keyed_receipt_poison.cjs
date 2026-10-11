"use strict";
// Actual in-process HTTP via IPC + cold normal Worker. JSDOM is not a native browser.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],actions=[],assets=[],hashes={},pending=new Map();
let serial=0,boots=0,dom,w,$,fault="",held=null,expectedApp=null;
readline.createInterface({input:process.stdin}).on("line",line=>{const value=JSON.parse(line),resolve=pending.get(value.id);pending.delete(value.id);resolve(value);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async test=>{const end=Date.now()+15000;while(Date.now()<end){if(test())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("bounded page wait");};
function visible(element){if(!element?.isConnected)return false;for(let node=element;node;node=node.parentElement){const style=w.getComputedStyle(node);if(node.hidden||node.hasAttribute("inert")||node.getAttribute("aria-hidden")==="true"||style.display==="none"||["hidden","collapse"].includes(style.visibility))return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(element))return false;}return true;}
async function gesture(element,perform,bindings){assert(visible(element),`visible action ${element?.id||element?.textContent}`);assert(!element.matches(":disabled"),`enabled action ${element.id}`);element.focus();const work=[],restore=[];for(const [node,property] of bindings){const original=node?.[property];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[property]=wrapper;restore.push(()=>{if(node[property]===wrapper)node[property]=original;});}actions.push({element:element.id||element.textContent,visible:true,enabled:true,event:"DOM dispatch"});try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const element=typeof value==="string"?$(value):value;return gesture(element,()=>element.click(),[[element,"onclick"],[element.form,"onsubmit"]]);};
const edit=(id,value)=>{const element=$(id);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event("input",{bubbles:true}));element.dispatchEvent(new w.Event("change",{bubbles:true}));},[[element,"oninput"],[element,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const appButton=name=>[...$("app-list").querySelectorAll("button")].find(button=>button.closest(".row").textContent.includes(name));
const extractionPosts=()=>requests.filter(r=>r.method==="POST"&&r.path.endsWith("/extract"));
async function boot(name){
 if(dom)dom.window.close();const boot=++boots;
 const load=async path=>{const result=await rpc({path,method:"GET"});assert.equal(result.status,200);const sha=crypto.createHash("sha256").update(result.text).digest("hex");assets.push({boot,path,status:result.status,content_type:result.content_type,bytes:Buffer.byteLength(result.text),sha256:sha});hashes[path.slice(1)||"index.html"]=sha;return result.text;};
 dom=new JSDOM(await load("/"),{url:"http://offline.test/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=crypto.randomUUID;w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(path,options={})=>{
  const request={path,method:options.method||"GET",body:options.body&&JSON.parse(options.body),headers:options.headers};requests.push(request);const result=await rpc(request);
  if(request.method==="POST"&&path.endsWith("/extract")&&result.status===201){expectedApp=JSON.parse(result.text).id;}
  if(fault==="lost"&&request.method==="POST"&&path.endsWith("/extract")){fault="";assert.equal(result.status,201);throw Error("controlled lost accepted extraction response");}
  if(fault==="poison"&&request.method==="POST"&&path.endsWith("/extract")){fault="";const value=JSON.parse(result.text);value.id=info.target;return new Response(JSON.stringify(value),{status:result.status});}
  if(path.includes("/extraction-receipts?")&&info.poison_kind){const value=JSON.parse(result.text);if(info.poison_kind==="wrong-existing-app")value.id=info.poison_app;else value.candidate_fingerprint="0".repeat(64);return new Response(JSON.stringify(value),{status:result.status,headers:{"Content-Type":"application/json"}});}
  const pause=(fault==="options"&&path.endsWith("/extraction-options"))||(fault==="post"&&request.method==="POST"&&path.endsWith("/extract"))||(fault==="app"&&request.method==="GET"&&path===`/api/apps/${expectedApp}`&&w.eval("activeApp")===null);
  if(pause){fault="";await new Promise(resolve=>held=resolve);}
  return new Response(result.text,{status:result.status,headers:{"Content-Type":result.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const path=script.getAttribute("src"),node=w.document.createElement("script");node.textContent=await load(path);w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);await nav("apps");await click(appButton(name));
}
async function openSource(){await click(appButton("source"));await click($("internal-instances").querySelector("button"));await click($("internal-runs").querySelector("button"));check(visible($("registered-extraction-open")),"actual succeeded source exposes visible extraction entry");await click("registered-extraction-open");check($("registered-extraction-proof").textContent.includes("completed_registered_text_apprun.v1"),"exact verified text source proof rendered");await edit("registered-extraction-target",info.target);await edit("registered-extraction-name","Extracted visible text");}
async function inputUndo(id){const element=$(id),original=element.value;await gesture(element,()=>{element.value=original+" edit";element.dispatchEvent(new w.InputEvent("input",{bubbles:true,inputType:"insertText",data:" edit"}));},[[element,"oninput"]]);await gesture(element,()=>{element.value=original;element.dispatchEvent(new w.InputEvent("input",{bubbles:true,inputType:"historyUndo"}));},[[element,"oninput"]]);check(element.value===original,"real InputEvent edit and historyUndo restore name A B A");}
async function recoverFromSource(){await openSource();const before=extractionPosts().length;check(visible($("registered-extraction-retry")),"original pending configuration exposes read-only recovery");await click("registered-extraction-retry");check(extractionPosts().length===before,"original key recovery performs no POST");}
(async()=>{let status="FAIL",error=null;try{
 await boot("source");await openSource();check($("registered-extraction-target-info").textContent.includes(info.resource),"selected new authorized material identity visible");
 check($("registered-extraction-status").textContent.includes("term")&&$("registered-extraction-status").textContent.includes("PENDING"),"variable and unaccepted scope visible before confirmation");
 if(info.scenario==="late-options-edit-undo"){
  fault="options";const reading=click("registered-extraction-open");await wait(()=>held);const release=held;held=null;await inputUndo("registered-extraction-name");const focus=w.document.activeElement;release();await reading;
  check(w.document.activeElement===focus&&!$("registered-extraction-status").textContent.includes("来源已核查"),"late options after edit undo cannot install status or change focus");await click("registered-extraction-open");await edit("registered-extraction-target",info.target);
 }
 if(info.scenario==="lost"||info.scenario==="poison")fault=info.scenario;
 if(info.scenario==="late-post-nav"||info.scenario==="late-app-nav"){
  fault=info.scenario==="late-post-nav"?"post":"app";const saving=click("registered-extraction-submit");await wait(()=>held);const release=held;held=null;await nav("projects");await nav("apps");const focus=w.document.activeElement,count=requests.length;release();await saving;
  check(requests.length===count&&w.document.activeElement===focus&&w.eval("activeApp")!==expectedApp,"late accepted or app read after workspace A B A cannot hand off or focus");await recoverFromSource();
 }else{
  await click("registered-extraction-submit");
  if(info.scenario==="lost"||info.scenario==="poison"){
   check(visible($("registered-extraction-retry"))&&$("registered-extraction-status").textContent.includes("不会自动重发"),"unknown or invalid accepted response retains exact key recovery");check($("registered-extraction-submit").disabled,"unknown outcome cannot resend normal POST");const count=extractionPosts().length;await click("registered-extraction-retry");check(extractionPosts().length===count,"explicit recovery uses GET only");
  }
 }
 if(info.poison_kind){check(w.eval("activeApp")!==info.poison_app&&w.eval("activeApp")!==expectedApp,"invalid original-key receipt cannot install a candidate before exact candidate/proof binding is checked");check(visible($("registered-extraction-retry")),"invalid keyed receipt retains GET-only recovery");status="PASS";return;}
 check(extractionPosts().length===1,"exactly one extraction POST in whole flow");check(w.eval("activeApp")===expectedApp&&expectedApp!==info.source&&expectedApp!==info.target,"keyed receipt opens exact independent app");
 check(visible($("app-agent-term"))&&w.document.activeElement===$("app-agent-term"),"new app visible term receives focus");check($("app-origin").textContent.includes("owner PENDING")&&$("app-origin").textContent.includes("UNKNOWN")&&$("app-origin").textContent.includes("完整 P-B 未验收"),"source and remaining semantic PB limits visible");
 const manifest=JSON.parse($("app-manifest").textContent).candidate;check(manifest.manifest.data_bindings[0].resource_ref===info.resource&&!manifest.goal_application&&manifest.manifest.source_run_ref===info.run,"new binding and independent task origin are exact");
 await boot("Extracted visible text");check(w.eval("activeApp")===expectedApp,"cold independent page opens saved application without original page state");
 await edit("app-agent-term","Alpha");await click("internal-prepare");await click("internal-approval-ack");await click("internal-commit");await click($("internal-releases").querySelector("button"));
 check($("owner-status").textContent.includes("PENDING"),"new instance has no inherited owner declaration");
 await edit("internal-term","Gamma");await click("internal-run-submit");const newRun=w.eval("engineering.run.id");check(newRun!==info.run,"new unseen input creates independent persistent Run");const worked=await rpc({command:"worker"});assert.equal(worked.status,200);await click("internal-refresh");await click($("internal-runs").querySelector("button"));
 const actual=w.eval("engineering.run");check(actual.status==="SUCCEEDED"&&actual.result_version===1,"cold normal Worker produces actual typed success version1");
 check(actual.result.resource_id===info.resource&&actual.result.term==="Gamma"&&actual.result.citations.length===2&&actual.result.citations[0].quote==="Gamma new obligation"&&actual.result.citations[1].quote==="Gamma final note","result uses new material and new variable instead of old task output");
 check($("internal-data").textContent.includes("Gamma new obligation")&&$("owner-status").textContent.includes("PENDING"),"new result visible alongside unaccepted owner state");status="PASS";
 }catch(exc){error=exc.stack||String(exc);process.stderr.write(error+"\n");process.exitCode=1;}
 finally{fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,classification:"ACTUAL_IPC_HTTP_JSDOM_CONTROLLED_KEYED_RECEIPT_SUBSTITUTION",active_app:w?.eval("activeApp"),poison_app:info.poison_app,poison_kind:info.poison_kind,checks,actions,requests,boots,static_resource_loads:assets,loaded_source_sha256:hashes,generated:expectedApp,real_model:"NOT_RUN",human_semantic:"NOT_RUN",formal_publication:false},null,2));if(dom)dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");}
})();
