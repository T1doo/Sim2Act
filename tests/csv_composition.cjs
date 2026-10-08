"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,"info.json"))),checks=[],requests=[],hashes={};
let dom,w,page,dropNextRun=false;
const check=(value,label)=>{assert(value,label);checks.push(label);};
const wait=async fn=>{const until=Date.now()+6000;while(Date.now()<until){if(fn())return;await new Promise(r=>setTimeout(r,10));}throw Error("bounded DOM wait expired");};
async function idle(){await wait(()=>page.requests===0&&page.actions.size===0);await new Promise(r=>setImmediate(r));if(page.errors.length)throw page.errors[0];}
function track(window){
  for(const name of ["onclick","onchange","onsubmit"]){const d=Object.getOwnPropertyDescriptor(window.HTMLElement.prototype,name);Object.defineProperty(window.HTMLElement.prototype,name,{...d,set(fn){d.set.call(this,typeof fn==="function"?function(...args){const r=fn.apply(this,args);if(r&&typeof r.then==="function"){const action=Promise.resolve(r);page.actions.add(action);action.then(()=>page.actions.delete(action),e=>{page.actions.delete(action);page.errors.push(e);});}return r;}:fn);}});}
  window.addEventListener("error",e=>page.errors.push(e.error||Error(e.message)));
}
(async()=>{try{
  const html=await(await fetch(info.base)).text();hashes["index.html"]=crypto.createHash("sha256").update(html).digest("hex");
  dom=new JSDOM(html,{url:info.base,runScripts:"dangerously"});w=dom.window;page={requests:0,actions:new Set(),errors:[]};track(w);
  const $=id=>w.document.getElementById(id);
  w.setInterval=()=>0;w.TextEncoder=TextEncoder;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();
  w.fetch=async(url,opts={})=>{page.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);requests.push({path:target.pathname,method:opts.method||"GET",body:opts.body&&JSON.parse(opts.body)});const r=await fetch(target,opts);if(dropNextRun&&target.pathname.endsWith("/runs")&&opts.method==="POST"){dropNextRun=false;await r.arrayBuffer();throw Error("owned fixture dropped accepted response");}return new Response(await r.arrayBuffer(),{status:r.status,headers:r.headers});}finally{page.requests--;}};
  for(const name of Array.from(w.document.querySelectorAll("script[src]")).map(s=>s.getAttribute("src").slice(1))){const code=await(await fetch(info.base+"/"+name)).text();hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const script=w.document.createElement("script");script.textContent=code;w.document.body.append(script);}
  $("token").value="synthetic-test-A";$("connect").click();await wait(()=>$("login").hidden&&$("project-select").value===info.project);await idle();await w.showApp(info.app);
  check(!$("csv-dag-panel").hidden,"existing CSV app hosts DAG controls");
  $("csv-dag-mode").value="composition";$("csv-dag-mode").dispatchEvent(new w.Event("change"));
  const rows=Array.from($("csv-dag-nodes").children),control=(row,role)=>row.querySelector(`[data-role="${role}"]`);
  check(rows.length===4&&!$("csv-dag-composition").hidden&&$("csv-dag-node-add").disabled,"editable four-node composition respects cap");
  control(rows[0],"condition").value="eq";rows[0].dispatchEvent(new w.Event("change"));
  await w.csvDagSubmit("plan");
  const plan=JSON.parse($("csv-dag-definition").textContent);
  check(plan.composition.definition.nodes.length===4&&plan.definition.actions.filter(a=>a.executor.ref==="data.aggregate_csv").length===2,"original page persisted actual typed composition");
  check(!$("csv-dag-confirm").checked&&$("csv-dag-run").disabled,"composition requires exact confirmation");
  $("csv-dag-branch-input").value=String(info.enabled);$("csv-dag-branch-input").dispatchEvent(new w.Event("change"));
  check(!$("csv-dag-confirm").checked,"changed conditional input clears confirmation");
  $("csv-dag-confirm").checked=true;dropNextRun=true;await w.csvDagSubmit("run");
  check($("csv-dag-status").textContent.includes("UNKNOWN")&&$("csv-dag-mode").disabled,"unknown acceptance freezes composition");
  await w.csvDagSubmit("run",true);
  const posts=requests.filter(r=>r.method==="POST"&&r.path.endsWith("/runs"));
  check(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),"same-key response recovery retains exact confirmation");
  const queued=JSON.parse($("csv-dag-result").textContent);
  check(queued.status==="QUEUED"&&queued.plan_fingerprint===plan.plan_fingerprint,"new four-node run queued");
  const worked=await fetch(info.base+"/__fixture__/work",{method:"POST",headers:{Authorization:"Bearer synthetic-test-A","Content-Type":"application/json"},body:JSON.stringify({run_id:queued.id})});assert(worked.ok,await worked.text());
  await w.csvDagRead();const job=JSON.parse($("csv-dag-result").textContent),jobs=[job];
  check(job.status===(info.enabled?"SUCCEEDED":"PARTIAL")&&job.steps.length===4,"real four-node worker follows conditional composition");
  check(job.result.output_by_step.node_4.sum==="15"&&(info.enabled?job.result.output_by_step.node_2.sum==="30":job.result.output_by_step.node_2===null),"actual dual branch outputs preserve independent quantity path");
  check(job.model_requests===0&&job.business_writes===0&&job.owner_acceptance==="PENDING"&&job.publishable===false,"candidate acceptance and authority preserved");
  await w.showApp(info.app);await w.csvDagRead(undefined,job.id,plan);
  check(JSON.stringify(JSON.parse($("csv-dag-result").textContent))===JSON.stringify(job),"cold original page restores all four checked receipts");
  await w.csvDagHistory();check($("csv-dag-history").textContent.includes("有限节点组合"),"original saved history accepts bounded plans");
  $("csv-dag-mode").value="composition";$("csv-dag-mode").dispatchEvent(new w.Event("change"));
  const changed=Array.from($("csv-dag-nodes").children);for(const row of changed.slice(1))row.querySelector("button").click();
  control(changed[0],"condition").value="";control(changed[0],"action").value="resource.read";changed[0].dispatchEvent(new w.Event("change"));
  await w.csvDagSubmit("plan");const one=JSON.parse($("csv-dag-definition").textContent);
  check(one.composition.definition.nodes.length===1&&one.definition.actions[0].executor.ref==="resource.read","user removes nodes and changes action to save a distinct one-node composition");
  await idle();const result={status:"PASS",checks,requests,plan,jobs,loaded_source_sha256:hashes,native:"NOT_RUN"};fs.writeFileSync(path.join(root,"results.json"),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,"failure.json"),JSON.stringify({status:"FAIL",checks,error:e.message,requests,loaded_source_sha256:hashes},null,2));console.error(e.stack);process.exitCode=1;}finally{if(dom){await idle();dom.window.close();}}})();
