"use strict";
// Full page assets + authenticated real loopback HTTP. Storage/Locks are a test adapter.
const fs=require("node:fs"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),zlib=require("node:zlib"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],requests=[],assets=[],actions=[],pending=new Map();
const browser=require("./durable_browser.cjs")(info.storage_path,{storageEvents:false});
let serial=0,dom,w,$,documents=0,lose=true,accepted,originalRequest;
readline.createInterface({input:process.stdin}).on("line",line=>{const value=JSON.parse(line),resolve=pending.get(value.id);pending.delete(value.id);resolve(value);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(value,label)=>{assert(value,label);checks.push(label);};
const submissions=()=>requests.filter(r=>r.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(r.path));
function visible(element){
 if(!element?.isConnected)return false;
 for(let node=element;node;node=node.parentElement){if(node.hidden||node.hasAttribute("inert"))return false;const style=w.getComputedStyle(node);if(style.display==="none"||["hidden","collapse"].includes(style.visibility))return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(element))return false;}
 return true;
}
async function gesture(element,perform,bindings){
 assert(visible(element),"visible action "+element?.id);assert(!element.matches(":disabled"));element.focus();const work=[],restores=[];
 for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const result=original.call(this,event);work.push(Promise.resolve(result));return result;};node[key]=wrapper;restores.push(()=>{if(node[key]===wrapper)node[key]=original;});}
 actions.push({element:element.id||element.textContent,visible:true,enabled:true,event:"DOM click/input dispatch in JSDOM"});
 try{perform();await Promise.all(work);}finally{restores.forEach(restore=>restore());}
}
const click=element=>{element=typeof element==="string"?$(element):element;return gesture(element,()=>element.click(),[[element,"onclick"],[element.form,"onsubmit"]]);};
const edit=(id,value)=>{const element=$(id);return gesture(element,()=>{element.value=value;element.dispatchEvent(new w.Event("input",{bubbles:true}));element.dispatchEvent(new w.Event("change",{bubbles:true}));},[[element,"oninput"],[element,"onchange"]]);};
async function http(path,options={}){
 const url=new URL(path,info.base_url);assert.equal(url.origin,info.base_url);
 const response=await fetch(url,options),text=await response.text();
 const value={document:documents,path:url.pathname+url.search,method:options.method||"GET",body:options.body?JSON.parse(options.body):null,status:response.status,text,authenticated:options.headers?.Authorization==="Bearer synthetic-test-A"};
 requests.push(value);fs.appendFileSync(info.http_log,zlib.gzipSync(JSON.stringify(value)+"\n"));
 return {status:response.status,text,content_type:response.headers.get("content-type")};
}
async function boot(){
 const previous=w;if(dom)dom.window.close();documents++;
 const load=async path=>{const r=await http(path);assert.equal(r.status,200);assets.push({document:documents,path,sha256:crypto.createHash("sha256").update(r.text).digest("hex")});return r.text;};
 const html=await load("/");dom=new JSDOM(html,{url:info.base_url+"/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);browser.install(w);
 check(!previous||previous!==w,"fresh document object "+documents);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(path,options={})=>{const r=await http(path,options);if(lose&&options.method==="POST"&&/\/internal\/instances\/[^/]+\/runs$/.test(path)){lose=false;assert.equal(r.status,202);accepted=JSON.parse(r.text);originalRequest=JSON.parse(options.body);throw Error("controlled loss AFTER actual accepted response");}return new Response(r.text,{status:r.status,headers:{"Content-Type":r.content_type||"application/json"}});};
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");check($("login").hidden&&$("project-select").value===info.project,"authenticated own project in document "+documents);
 await click(w.document.querySelector('#workspace-nav [data-tab="apps"]'));
 await click([...$("app-list").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.app_name)));
 await click([...$("internal-instances").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(info.instance)));
}
function write(status,error){fs.writeFileSync(info.output,zlib.gzipSync(JSON.stringify({status,error,checks,requests,assets,actions,accepted,original_request:originalRequest,documents,lock_events:browser.events,browser:"JSDOM_NOT_NATIVE",api:"ACTUAL_LOOPBACK_SEPARATE_API_WORKER",storage_locks:"TEST_ADAPTER",automatic_polling:false,model:"EXPLICIT_MOCK_ONLY",text:error?w?.document.body.textContent:undefined},null,2)));}
(async()=>{try{
 await boot();await click("internal-run-submit");
 check(accepted&&submissions().length===1&&!$("internal-retry").hidden,"accepted response loss preserves exact durable key without duplicate execution submit");
 check(!requests.some(r=>r.path.includes("/spec-run-requests/")),"no successful keyed receipt consumed the recovery intent before pause");
 const values=browser.values(info.base_url);check(values.length===1&&!JSON.stringify(values).includes("synthetic-test-A")&&!JSON.stringify(values).includes("desk lamp"),"only minimal durable metadata persists, no token or source body");
 await rpc({command:"pause-and-replace-worker",accepted,request:originalRequest});
 const before=requests.length;await boot();
 check($("internal-run-submit").disabled&&!$("internal-retry").hidden,"new DOM restores old key and disables duplicate submit");
 await click("internal-retry");
 const keyed=requests.slice(before).filter(r=>r.path.endsWith("/spec-run-requests/"+originalRequest.request_key));assert.equal(keyed.length,1);const receipt=JSON.parse(keyed[0].text);
 check(keyed[0].method==="GET"&&keyed[0].authenticated&&keyed[0].status===200,"new DOM performs authenticated original-key GET");
 check(receipt.request_key===originalRequest.request_key&&receipt.run_id===accepted.run_id&&receipt.app_run_id===accepted.app_run_id&&receipt.status==="PAUSED","new DOM recovers identical request key, Run and AppRun at PAUSED");
 check(submissions().length===1&&browser.values(info.base_url).length===0,"exact receipt clears original intent without another run POST");
 const resume=[...$("internal-controls").querySelectorAll("button")].find(b=>b.textContent==="继续");
 check(resume&&visible(resume)&&!resume.disabled,"PAUSED original run exposes explicit enabled resume action");
 check(!requests.some(r=>r.path.endsWith("/commands")&&r.body?.command==="resume"),"no resume command before explicit action");
 await rpc({command:"verify-paused-before-resume",accepted,request:originalRequest});
 await click(resume);const commands=requests.filter(r=>r.path.endsWith("/commands")&&r.body?.command==="resume");
 check(commands.length===1&&commands[0].path.includes(accepted.run_id)&&commands[0].status===200,"explicit visible resume targets original run with current version");
 await rpc({command:"finish-same-run",accepted,request:originalRequest});
 await click("internal-refresh");await click([...$("internal-runs").querySelectorAll("button")].find(b=>b.closest(".row").textContent.includes(accepted.run_id)));
 const detail=JSON.parse($("internal-run-detail").textContent);check(detail.id===accepted.run_id&&detail.status==="SUCCEEDED","same recovered run succeeds after explicit resume");
 const saved=$("internal-data").querySelector(".spec-result");check(saved,"one saved result renders");await click(saved.querySelector('[data-spec-action="view"]'));
 check(saved.textContent.includes("desk lamp")&&saved.textContent.includes("语义 UNKNOWN"),"authenticated saved artifact retains original material and semantic boundary");
 check(submissions().length===1,"only one original execution submission throughout both documents");
 await rpc({command:"verify-no-duplicate",accepted,request:originalRequest});
 write("PASS");dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
 }catch(error){write("FAIL",error.stack);dom?.window.close();process.stderr.write(error.stack+"\n");process.exit(1);}})();
