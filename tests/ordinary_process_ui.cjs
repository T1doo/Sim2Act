"use strict";
// Actual loopback HTTP; JSDOM gestures only, never a native-browser claim.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],assets=[],actions=[],pending=new Map();
let serial=0,dom,w,$,loseSource=false,sourceAccepted=null;
readline.createInterface({input:process.stdin}).on("line",line=>{const result=JSON.parse(line),resolve=pending.get(result.id);pending.delete(result.id);resolve(result);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const posts=()=>requests.filter(r=>r.method==="POST").length;
function visible(element){
 if(!element?.isConnected)return false;
 for(let node=element;node;node=node.parentElement){
  if(node.hidden||node.hasAttribute("inert")||node.getAttribute("aria-hidden")==="true")return false;
  const style=w.getComputedStyle(node);if(style.display==="none"||["hidden","collapse"].includes(style.visibility))return false;
  if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(element))return false;
 }
 return true;
}
async function gesture(element,perform,bindings){
 assert(visible(element),`visible action: ${element?.id}`);assert(!element.matches(":disabled"),`enabled action: ${element.id}`);
 element.focus();const work=[],restores=[];
 for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const value=original.call(this,event);work.push(Promise.resolve(value));return value;};node[key]=wrapper;restores.push(()=>{if(node[key]===wrapper)node[key]=original;});}
 actions.push({element:element.id||element.textContent,visible:true,enabled:true,event:"native DOM dispatch"});
 try{perform();await Promise.all(work);}finally{restores.forEach(restore=>restore());}
}
const click=value=>{const element=typeof value==="string"?$(value):value;return gesture(element,()=>element.click(),[[element,"onclick"],[element.form,"onsubmit"]]);};
const edit=(id,value)=>{const element=$(id);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event("input",{bubbles:true}));element.dispatchEvent(new w.Event("change",{bubbles:true}));},[[element,"oninput"],[element,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
async function http(path,options={}){
 const url=new URL(path,info.base_url);assert.equal(url.origin,info.base_url);
 fs.appendFileSync(info.http_log,JSON.stringify({phase:"REQUEST",path:url.pathname+url.search,method:options.method||"GET",body:options.body?JSON.parse(options.body):null})+"\n");
 const response=await fetch(url,options),text=await response.text();
 requests.push({path:url.pathname+url.search,method:options.method||"GET",body:options.body?JSON.parse(options.body):null,status:response.status,text});
 fs.appendFileSync(info.http_log,JSON.stringify({phase:"RESPONSE",...requests.at(-1)})+"\n");
 return {status:response.status,text,content_type:response.headers.get("content-type")};
}
async function boot(){
 const load=async path=>{const r=await http(path);assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash("sha256").update(r.text).digest("hex"),bytes:Buffer.byteLength(r.text)});return r.text;};
 const html=await load("/");dom=new JSDOM(html,{url:info.base_url+"/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();
 // Explicit polling boundary: all refreshes below are visible user actions.
 w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(path,options={})=>{
  const r=await http(path,options);
  if(loseSource&&options.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(path)){
   loseSource=false;assert.equal(r.status,202);sourceAccepted=JSON.parse(r.text);
   throw Error("controlled delivery loss AFTER actual HTTP 202 acceptance");
  }
  return new Response(r.text,{status:r.status,headers:{"Content-Type":r.content_type||"application/json"}});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");
 check($("login").hidden&&$("project-select").value===info.project,"actual HTTP login selects exact isolated project");
 await click([...$("goal-card-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes("Operating notes")));
}
async function release(){
 await click("internal-prepare");check($("internal-commit").disabled,"release needs explicit acknowledgement");
 await click("internal-approval-ack");await click("internal-commit");await click($("internal-releases").querySelector("button"));
 return w.eval("engineering.instance.id");
}
async function viewSaved(phrase){
 await click("internal-refresh");const saved=$("internal-data").querySelector(".spec-result");
 check(saved&&!saved.querySelector("blockquote"),"saved artifact requires explicit content read");
 const count=posts();await click(saved.querySelector('[data-spec-action="view"]'));
 check(posts()===count&&saved.textContent.includes(phrase),"authorized GET renders actual saved material");
 check(saved.textContent.includes("语义 UNKNOWN")&&saved.textContent.includes("Human question 15"),"semantic and all unresolved human questions remain pending");
}
function write(status,error){fs.writeFileSync(info.output,JSON.stringify({status,error,checks,requests,assets,actions,source_accepted:sourceAccepted,browser:"JSDOM_NOT_NATIVE",api:"REAL_LOOPBACK_HTTP_SEPARATE_API_WORKER",same_document:true,automatic_polling:false,model:"EXPLICIT_MOCK_TRANSPORT_ONLY",text:error?dom?.window.document.body.textContent:undefined},null,2));}
(async()=>{try{
 await boot();await edit("goal-application-family","natural_spec");await click("goal-application-start");
 check($("goal-application-confirm").disabled,"queued generation cannot be saved");
 await rpc({command:"generation"});await click("goal-application-read");
 const proof=JSON.parse($("goal-application-proof").textContent);
 check(proof.candidate.spec_recipe.steps.length===6&&proof.semantic_status==="UNKNOWN"&&proof.goal_acceptance==="NOT_RUN","actual six-step candidate retains semantic boundary");
 await click("goal-application-ack");check($("goal-application-confirm").disabled,"candidate acknowledgement alone cannot save");
 await click("goal-application-write-ack");await edit("goal-application-name","Source process app");await click("goal-application-confirm");
 const sourceInstance=await release();loseSource=true;await click("internal-run-submit");
 check(sourceAccepted&&!$("internal-retry").hidden&&$("internal-new-intent").hidden,"lost accepted response retains original-key recovery and blocks new intent");
 const sourceSubmit=requests.find(r=>r.method==="POST"&&r.path===`/api/internal/instances/${sourceInstance}/runs`);
 check(!requests.some(r=>r.path.includes("/spec-run-requests/")),"no successful keyed receipt read clears pending before restart");
 const count=posts(),beforeRestart=requests.length;
 await rpc({command:"source-restart",instance:sourceInstance,accepted:sourceAccepted,key:sourceSubmit.body.request_key});
 check(posts()===count&&requests.length===beforeRestart,"backend restart performs no page submit or hidden recovery");
 await click("internal-retry");
 const recovery=requests.slice(beforeRestart).find(r=>r.path.includes("/spec-run-requests/"));
 check(posts()===count&&recovery?.path.endsWith("/"+sourceSubmit.body.request_key)&&recovery.status===200,"same document recovers original key with GET only after actual process restart");
 const receipt=JSON.parse(recovery.text);
 check(receipt.run_id===sourceAccepted.run_id&&receipt.app_run_id===sourceAccepted.app_run_id&&receipt.status==="SUCCEEDED","recovery matches original Run and AppRun saved by separate Worker");
 await viewSaved("desk lamp");
 await nav("projects");await click([...$("goal-card-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes("Cold operating notes")));
 await edit("pa-binding-family","natural");await click("pa-binding-sources");await edit("pa-binding-source",proof.run_id);await click("pa-binding-preview");
 const preview=JSON.parse($("pa-binding-proof").textContent);
 check(preview.resource_id===info.target_resource&&preview.target_goal.card_id===info.target_card,"Cold preview freezes exact new material and complete Goal");
 await edit("pa-binding-name","Cold process app");await click("pa-binding-ack");await click("pa-binding-save");
 const bindPosts=posts();await click("pa-binding-recover");check(posts()===bindPosts,"Cold binding original-key recovery uses GET only");
 await click("pa-binding-open");const coldInstance=await release();
 check(coldInstance!==sourceInstance,"Cold has an independent instance");await click("internal-run-submit");
 await rpc({command:"cold"});await viewSaved("garden sensor");
 check(!$("internal-data").textContent.includes("desk lamp"),"Cold output contains no Source answer");
 check(requests.filter(r=>r.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(r.path)).length===2,"exactly one Source and one Cold submit");
 check(requests.filter(r=>r.method==="POST"&&r.path.endsWith("/application-runs")).length===1,"only one generation");
 check(!requests.some(r=>r.method==="POST"&&r.path.includes("application-provider-scopes")),"no LIVE scope or credential setup");
 await rpc({command:"verify-history",instance:sourceInstance,accepted:sourceAccepted});
 write("PASS");dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }catch(error){write("FAIL",error.stack);dom?.window.close();process.stderr.write(error.stack+"\n");process.exit(1);}})();
