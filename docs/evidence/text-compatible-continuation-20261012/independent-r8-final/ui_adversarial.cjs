"use strict";
// Normal visible flow only: actual TestClient HTTP and cold Worker via IPC.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],actions=[],requests=[],assets=[],pending=new Map();
let serial=0,dom,w,$,boots=0,activeFetches=0,intervals=new Set(),dropAuth=info.scenario==="authorization-lost",dropBind=info.scenario==="commit-lost",generated=null,attack=false;
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
async function boot(){await closePage();const boot=++boots;const load=async path=>{const r=await rpc({method:"GET",path});assert.equal(r.status,200);assets.push({boot,path,status:r.status,sha256:crypto.createHash("sha256").update(r.text).digest("hex")});return r.text;};dom=new JSDOM(await load("/"),{url:"http://testserver/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;w.Date.now=()=>info.fixture_time*1000;const originalInterval=w.setInterval.bind(w);w.setInterval=(...args)=>{const id=originalInterval(...args);intervals.add(id);return id;};const css=w.document.createElement("style");css.textContent=await load("/app.css");w.document.head.append(css);$=id=>w.document.getElementById(id);Object.defineProperty(w,"crypto",{value:crypto.webcrypto});w.TextEncoder=TextEncoder;w.fetch=async(path,options={})=>{const request={method:options.method||"GET",path,headers:options.headers||{},body:options.body?JSON.parse(options.body):undefined};requests.push(request);activeFetches++;try{let r=await rpc(request);
if(info.custom==="late-connect"&&request.method==="POST"&&path.endsWith("software-continuation-preflights")){w.__held=true;await new Promise(resolve=>{w.__release=resolve;});}
if(attack&&request.method==="GET"&&path.includes("software-continuations?request_key=")){
 const value=JSON.parse(r.text);
 if(info.custom==="wrong-key")value.request_key="another-accepted-original-key";
 if(info.custom==="wrong-release")value.preflight.source_release_fingerprint="0".repeat(64);
 {
  const p=value.preflight,request={expected_revision:p.revision,expected_release_fingerprint:p.source_release_fingerprint,expected_candidate_fingerprint:p.candidate_fingerprint,expected_source_implementation:p.source_implementation,input:p.input,request_key:value.request_key};
  value.approval_fingerprint=await w.eval("registeredHash")({continuation:p,request,approval_id:value.approval_id,principal_id:p.principal_id,project_id:p.project_id,kind:"text_software_prepare",expires_at:value.expires_at});
 }
 r={...r,text:JSON.stringify(value)};
}
if(request.method==="POST"&&path.endsWith("/text-logic-authorizations")&&dropAuth){dropAuth=false;throw Error("synthetic lost authorization reply");}if(request.method==="POST"&&path.endsWith("/software-continuations")&&dropBind){dropBind=false;throw Error("synthetic lost binding reply");}return new Response(r.text,{status:r.status,headers:{"Content-Type":r.content_type||"application/json"}});}finally{activeFetches--;}};for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project);}
(async()=>{let status="FAIL",error=null;try{
 await boot();await click("text-continuation-list");await edit("text-continuation-selected",info.instance);
 if(info.custom==="late-connect"){
  const pendingPreview=click("text-continuation-preview");await wait(()=>w.__held);
  // Explicit local boundary fault injection: login is hidden after connection.
  // This is not claimed as a visible/native identity-switch gesture.
  w.eval("token='independent-foreign-token';identityConnectionGeneration++;clearIdentityView();");
  const before=requests.filter(r=>r.path.includes("software-continuations?request_key=")).length;
  w.__release();await pendingPreview;
  check(requests.filter(r=>r.path.includes("software-continuations?request_key=")).length===before,"late original POST does not send old GET under fresh identity or connection");
  check(requests.filter(r=>r.method==="POST").length===1,"identity change does not repeat accepted POST");
  check(!$("text-continuation-proof").textContent,"late original response does not paint new identity scope");
 }else{
  await click("text-continuation-preview");const key=$("text-continuation-key").value;
  check(!$("text-continuation-ack").checked,"fresh preview never auto approves");
  await edit("text-continuation-key",key);attack=true;
  const before=requests.filter(r=>r.method==="POST").length;await click("text-continuation-recover");
  check($("text-continuation-commit").disabled,"forged recovery never enables confirmation");
  check(!w.eval("textContinuation.preflight"),"forged recovery never sets an accepted preflight");
  check($("text-continuation-status").textContent.includes("UNKNOWN"),"bad200 is exposed and original intent remains read only");
  check(requests.filter(r=>r.method==="POST").length===before,"bad200 recovery creates no mutation");
 }
 status="PASS";
 }catch(e){error=e.stack||String(e);process.stderr.write(error+"\n");process.exitCode=1;}
 finally{try{await closePage();}catch(e){error=error||e.stack;status="FAIL";process.exitCode=1;}fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.custom,checks,actions,requests,static_resource_loads:assets,boots,classification:"ACTUAL_TESTCLIENT_SHIPPED_JSDOM_INDEPENDENT_ADVERSARIAL",fault_injections:info.custom==="late-connect"?["controlled identity/connection boundary; no hidden-control gesture"]:["200 payload altered and valid SHA recomputed"],native_browser:"NOT_RUN",real_model:"NOT_RUN"},null,2));process.stdout.write(JSON.stringify({done:true})+"\n");}
})();
