"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,"info.json"))),checks=[],requests=[],assets=[];
let dom,w,page,drop=false,dropRead=false;
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async fn=>{const until=Date.now()+10000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error("bounded DOM wait expired");};
async function idle(){await wait(()=>page.requests===0&&page.actions.size===0);await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];}
function track(window){for(const name of ["onclick","onchange","onsubmit"]){const d=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==="function"?function(...args){const r=fn.apply(this,args);if(r&&typeof r.then==="function"){const action=Promise.resolve(r);page.actions.add(action);action.then(()=>page.actions.delete(action),e=>{page.actions.delete(action);page.errors.push(e);});}return r;}:fn);}});}window.addEventListener("error",e=>page.errors.push(e.error||Error(e.message)));}
async function boot(){const hashes={},html=await(await fetch(info.base)).text();hashes["index.html"]=crypto.createHash("sha256").update(html).digest("hex");dom=new JSDOM(html,{url:info.base,runScripts:"dangerously"});w=dom.window;page={requests:0,actions:new Set(),errors:[]};track(w);w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();
w.fetch=async(url,opts={})=>{page.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);requests.push({path:target.pathname,method:opts.method||"GET",body:opts.body&&JSON.parse(opts.body),page:assets.length+1});const r=await fetch(target,opts);if(drop&&target.pathname.includes("/switch-approvals/")&&target.pathname.endsWith("/commit")&&opts.method==="POST"){drop=false;await r.arrayBuffer();throw Error("owned fixture dropped accepted response");}if(dropRead&&target.pathname===`/api/internal/instances/${info.instance}`&&(opts.method||"GET")==="GET"){dropRead=false;await r.arrayBuffer();throw Error("owned fixture dropped GET after acceptance");}return new Response(await r.arrayBuffer(),{status:r.status,headers:r.headers});}finally{page.requests--;}};
for(const name of Array.from(w.document.querySelectorAll("script[src]")).map(s=>s.getAttribute("src").slice(1))){const code=await(await fetch(info.base+"/"+name)).text();hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const script=w.document.createElement("script");script.textContent=code;w.document.body.append(script);}const $=id=>w.document.getElementById(id);$("token").value="synthetic-test-A";$("connect").click();await wait(()=>$("login").hidden&&$("project-select").value===info.project);await idle();await w.showApp(info.app);assets.push({loaded_source_sha256:hashes});return $;}
async function work(rid){const response=await fetch(info.base+"/__fixture__/work",{method:"POST",headers:{Authorization:"Bearer synthetic-test-A","Content-Type":"application/json"},body:JSON.stringify({run_id:rid})});assert(response.ok,await response.text());}
(async()=>{try {
let $=await boot();$("dag-reuse-history").click();await idle();
$("dag-reuse-instance").value=info.instance;$("dag-reuse-read").click();await idle();
const detail=()=>JSON.parse($("dag-reuse-proof").textContent).instance;
check(detail().revision===1&&detail().data_version===1,"cold original instance and typed result restored");
check($("dag-reuse-switch-commit").disabled,"no switch without exact approval and confirmation");
check(Array.from($("dag-reuse-switch-target").options).some(o=>o.value===info.target),"compatible target offered in actual page");
const pick=value=>{$("dag-reuse-switch-target").value=value;$("dag-reuse-switch-target").dispatchEvent(new w.Event("change"));};
pick(info.target);const beforePrepare=requests.length;$("dag-reuse-switch-prepare").click();await idle();
check(requests.slice(beforePrepare).filter(v=>v.method==="POST").length===1,"preparation does not commit or run");
check($("dag-reuse-switch-proof").textContent.includes(info.old)&&$("dag-reuse-switch-proof").textContent.includes(info.target),"exact source and target visible before confirmation");
check($("dag-reuse-switch-commit").disabled&&detail().revision===1,"preparation preserves pointer and requires manual confirmation");
// Target selection must invalidate an already displayed approval.
pick("");check($("dag-reuse-switch-commit").disabled&&!$("dag-reuse-switch-proof").textContent,"changing target invalidates approval and checkbox");
pick(info.target);$("dag-reuse-switch-prepare").click();await idle();
$("dag-reuse-switch-confirm").checked=true;$("dag-reuse-switch-confirm").dispatchEvent(new w.Event("change"));
check(!$("dag-reuse-switch-commit").disabled,"exact approval can be explicitly confirmed");
if(info.lost==="post")drop=true;else dropRead=true;
const beforeCommit=requests.length;$("dag-reuse-switch-commit").click();await idle();
check($("dag-reuse-status").textContent.includes("UNKNOWN")&&!$("dag-reuse-recover").hidden,"lost accepted response preserves uncertain switch intent");
check($("dag-reuse-switch-target").disabled&&$("dag-reuse-run").disabled,"uncertain acceptance prevents changing target or running new work");
$("dag-reuse-recover").click();await idle();
check(requests.slice(beforeCommit).filter(v=>v.method==="POST").length===1,"recovery reads history without second commit POST");
check(detail().revision===2&&detail().release_id===info.target&&detail().data_version===1,"accepted upgrade preserves result version");
check(detail().data[0].data.result.sum==="30"&&detail().data[0].release_id===info.old,"old result retains original immutable release");
check($("dag-reuse-run").disabled&&!$("dag-reuse-run-confirm").checked,"switch does not implicitly approve a new input");
const coldStart=requests.length;dom.window.close();$=await boot();$("dag-reuse-history").click();await idle();$("dag-reuse-instance").value=info.instance;$("dag-reuse-read").click();await idle();
check(requests.slice(coldStart).every(v=>v.method==="GET"),"new cold page verifies mixed-version history with zero POST");
check(detail().revision===2&&detail().data[0].data.result.sum==="30","cold old result and upgrade remain visible");
$("dag-reuse-column").value="quantity";$("dag-reuse-column").dispatchEvent(new w.Event("change"));$("dag-reuse-run-confirm").checked=true;$("dag-reuse-run-confirm").dispatchEvent(new w.Event("change"));$("dag-reuse-run").click();await idle();
const accepted=detail().runs.find(v=>v.status==="QUEUED");check(!!accepted,"new input uses actual queued durable run");
check($("dag-reuse-switch-prepare").disabled,"active queued run prevents preparing version change");
await work(accepted.run_id);$("dag-reuse-read").click();await idle();
check(detail().data_version===2&&detail().data.map(v=>v.data.result.sum).join(",")==="30,15","new worker input computes fresh15 without replacing old30");
check(detail().runs.every(v=>v.proof.steps.length===info.nodes&&v.proof.model_requests===0),"actual complete workflow receipts retained with zero model requests");
pick(info.old);$("dag-reuse-switch-prepare").click();await idle();$("dag-reuse-switch-confirm").checked=true;$("dag-reuse-switch-confirm").dispatchEvent(new w.Event("change"));$("dag-reuse-switch-commit").click();await idle();
check(detail().revision===3&&detail().release_id===info.old&&detail().data_version===2,"explicit rollback changes pointer without destructive data migration");
check(detail().history.length===3&&detail().data.map(v=>v.release_id).join(",")===[info.old,info.target].join(","),"rollback history and per-result release lineage preserved");
fs.writeFileSync(path.join(root,"results.json"),JSON.stringify({status:"PASS",pages:2,checks,requests,assets,instance:detail()},null,2));console.log(JSON.stringify({status:"PASS",pages:2,checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,"FAILURE.json"),JSON.stringify({message:String(e),checks,requests,assets,html:dom?.serialize()},null,2));console.error(e);process.exitCode=1;}finally{dom?.window.close();}})();
