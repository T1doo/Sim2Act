"use strict";
// Actual loopback HTTP, with an origin-partitioned persistent Storage/Web Locks
// adapter. This is not evidence of native WebView2 disk behavior.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const info=JSON.parse(fs.readFileSync(process.argv[2],"utf8")),requests=[],errors=[];
const storage=fs.existsSync(info.profile)?JSON.parse(fs.readFileSync(info.profile,"utf8")):{};
const origin=new URL(info.base).origin,web=path.join(__dirname,"../src/sim2act/web");
const browser=require("./durable_browser.cjs")(undefined,{storageEvents:false});
let dom,w,$,inflight=0,lost=null;
const wait=async(fn,label)=>{const end=Date.now()+10000;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error("Timeout "+label);};
const persist=()=>{storage[origin]=browser.values(origin);fs.writeFileSync(info.profile,JSON.stringify(storage));};
(async()=>{try{
 const html=await(await fetch(info.base)).text();
 dom=new JSDOM(html,{url:info.base,runScripts:"dangerously"});w=dom.window;$=id=>w.document.getElementById(id);browser.install(w);
 for(const [key,value] of storage[origin]||[])w.localStorage.setItem(key,value);
 for(const name of ["setItem","removeItem"]){const original=w.localStorage[name];w.localStorage[name]=(...args)=>{original(...args);persist();};}
 w.crypto.randomUUID=crypto.randomUUID;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.TextEncoder=TextEncoder;w.TextDecoder=TextDecoder;w.structuredClone=structuredClone;w.setInterval=()=>0;
 w.addEventListener("error",e=>errors.push(e.message));
 w.fetch=async(url,opts={})=>{
  const target=new URL(url,info.base);assert.equal(target.origin,origin);const req={method:opts.method||"GET",path:target.pathname,...(opts.body?{body:JSON.parse(opts.body)}:{})};requests.push(req);inflight++;
  try{
   const response=await fetch(target,opts),raw=await response.text();req.status=response.status;
   if(info.mode==="submit-lost"&&req.method==="POST"&&/\/instances\/[^/]+\/runs$/.test(req.path)){
    assert.equal(response.status,202);lost=JSON.parse(raw);throw TypeError("Synthetic lost accepted response");
   }
   if(info.mode==="recover-corrupt"&&req.method==="GET"&&req.path.includes("/spec-run-requests/")){
    assert.equal(response.status,200);return new Response(JSON.stringify({...JSON.parse(raw),release_id:"irelease_"+"0".repeat(32)}),{status:200});
   }
   return new Response(raw,{status:response.status,headers:response.headers});
  }finally{inflight--;}
 };
 for(const element of [...w.document.querySelectorAll("script[src]")]){
  const name=element.getAttribute("src").slice(1),raw=await(await fetch(info.base+"/"+name)).text();
  assert.equal(crypto.createHash("sha256").update(raw).digest("hex"),crypto.createHash("sha256").update(fs.readFileSync(path.join(web,name))).digest("hex"));
  const script=w.document.createElement("script");script.textContent=raw;w.document.body.append(script);
 }
 $("token").value=info.token;$("connect").click();await wait(()=>$("login").hidden&&inflight===0,"authenticated project reads");
 $("project-select").value=info.project;$("project-select").dispatchEvent(new w.Event("change"));await wait(()=>inflight===0,"project selection");
 const appRow=[...$("app-list").querySelectorAll(".row")].find(n=>n.textContent.includes("Model chosen checklist"));assert(appRow);appRow.querySelector("button").click();
 await wait(()=>w.eval("engineering?.historyReady")&&inflight===0,"spec source and history read");
 const instanceRow=[...$("internal-instances").querySelectorAll(".row")].find(n=>n.textContent.includes(info.instance));assert(instanceRow);instanceRow.querySelector("button").click();
 await wait(()=>w.eval("engineering?.instance?.id")===info.instance&&inflight===0,"exact instance selected");
 const originalProfile=JSON.stringify(storage);
 if(info.mode==="submit-lost"){
  $("internal-run-form").dispatchEvent(new w.Event("submit",{cancelable:true}));
  await wait(()=>lost&&!w.eval("engineering.busy")&&inflight===0,"lost receipt retained");
  const pending=w.eval("engineeringPending.get(engineering.instance.id)");assert(pending);assert.equal(requests.filter(r=>r.method==="POST").length,1);assert($("internal-run-submit").disabled);
  assert(!JSON.stringify(storage).includes(info.token));
  assert(!Object.hasOwn(JSON.parse(browser.values(origin)[0][1]),"input"));
  info.accepted=lost;info.request=JSON.parse(JSON.stringify(pending));
 }else{
  const pending=w.eval("engineeringPending.get(engineering.instance.id)");assert(pending);assert.equal(pending.request_key,info.request.request_key);assert($("internal-run-submit").disabled);
  $("internal-retry").click();await wait(()=>!w.eval("engineering.busy")&&inflight===0,"explicit original-key GET recovery");
  assert.equal(requests.filter(r=>r.method==="POST").length,0);
  if(info.mode==="recover-corrupt"){
   assert.equal(JSON.stringify(storage),originalProfile);assert(w.eval(`engineeringPending.has(${JSON.stringify(info.instance)})`));
  }else{
   assert.equal(w.eval("engineering.run.id"),info.accepted.run_id);assert.equal(w.eval("engineering.run.app_run_id"),info.accepted.app_run_id);
   assert.equal(w.eval("engineeringPending.has(engineering.instance.id)"),false);assert.equal(browser.values(origin).length,0);
  }
 }
 assert.deepEqual(errors,[]);persist();
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",mode:info.mode,origin,requests,accepted:info.accepted,request:info.request,profile_sha256:crypto.createHash("sha256").update(fs.readFileSync(info.profile)).digest("hex"),native_webview:"NOT_RUN"},null,2));
 console.log(JSON.stringify({status:"PASS",mode:info.mode,origin,posts:requests.filter(r=>r.method==="POST").length}));
}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:"FAIL",error:error.stack,requests},null,2));console.error(error.stack);process.exitCode=1;}finally{dom?.window.close();}})();
