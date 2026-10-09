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
  $("csv-dag-column").value="quantity";
  $("csv-dag-branch-target").value=info.target;$("csv-dag-branch-op").value=info.op;
  $("csv-dag-branch-source").value=info.source;$("csv-dag-branch-value").value=info.value;
  let host;
  if(info.mode==="composition"){
    $("csv-dag-mode").value="composition";$("csv-dag-mode").dispatchEvent(new w.Event("change"));
    host=$("csv-dag-nodes").children[1];
    host.querySelector('[data-role="condition"]').value="eq";
    host.querySelector('[data-role="condition-source"]').value="input:include_report";
    host.querySelector('[data-role="condition-value"]').value="true";
  }else host=$("csv-dag-branch");
  const mode=host.querySelector('[data-role="combine"]');mode.value=info.group;mode.dispatchEvent(new w.Event("change"));
  const second=host.querySelector('[data-role="conditions"]').children[0];
  second.querySelector('[data-role="group-source"]').value=info.mode==="composition"?"node_1:count":"aggregate:count";
  second.querySelector('[data-role="group-value"]').value=String(info.count);
  second.querySelector('[data-role="group-value"]').dispatchEvent(new w.Event("change",{bubbles:true}));
  await w.csvDagSubmit("plan");
  let plan=JSON.parse($("csv-dag-definition").textContent);
  check(plan.branch_semantics==="typed-conditions.v2"&&plan.definition.manifest.workflow.find(s=>s.step_id===info.target).when.op===info.group,"actual page saved exact typed condition");
  check(!$("csv-dag-confirm").checked&&$("csv-dag-run").disabled,"condition plan requires explicit confirmation");
  const value=second.querySelector('[data-role="group-value"]');$("csv-dag-confirm").checked=true;
  value.dispatchEvent(new w.Event("change",{bubbles:true}));
  check(!$("csv-dag-confirm").checked&&$("csv-dag-definition").textContent==="","editing a group leaf clears saved proof and exact confirmation");
  await w.csvDagSubmit("plan");plan=JSON.parse($("csv-dag-definition").textContent);
  check(host.querySelector('[data-role="combine"]').value===info.group,"group draft survives explicit replan");
  const jobs=[];
  for(let i=0;i<info.inputs.length;i++){
    $("csv-dag-branch-input").value=info.inputs[i];$("csv-dag-branch-input").dispatchEvent(new w.Event("change"));
    check(!$("csv-dag-confirm").checked&&$("csv-dag-run").disabled,"changed input clears confirmation");
    $("csv-dag-confirm").checked=true;dropNextRun=i===0;await w.csvDagSubmit("run");
    if(i===0){
      check($("csv-dag-status").textContent.includes("UNKNOWN")&&$("csv-dag-branch-input").disabled,"lost acceptance freezes branch input and original key");
      await w.csvDagSubmit("run",true);
      const posts=requests.filter(r=>r.method==="POST"&&r.path.endsWith("/runs"));
      check(posts.length===2&&JSON.stringify(posts[0].body)===JSON.stringify(posts[1].body),"unknown acceptance restores exact same input key and confirmation");
    }
    const queued=JSON.parse($("csv-dag-result").textContent);
    check(queued.status==="QUEUED"&&queued.plan_fingerprint===plan.plan_fingerprint,"same frozen plan accepts distinct explicit input");
    const worked=await fetch(info.base+"/__fixture__/work",{method:"POST",headers:{Authorization:"Bearer synthetic-test-A","Content-Type":"application/json"},body:JSON.stringify({run_id:queued.id})});assert(worked.ok,await worked.text());
    await w.csvDagRead();const job=JSON.parse($("csv-dag-result").textContent);jobs.push(job);
    const targeted=job.steps.find(s=>s.step_id===info.target);
    check(job.status===(info.statuses[i]==="SKIPPED"?"PARTIAL":"SUCCEEDED")&&targeted.status===info.statuses[i],"real worker takes expected conditional path");
    check(targeted.branch_decision.reason===(info.statuses[i]==="SKIPPED"?"CONDITION_FALSE":"CONDITION_TRUE"),"persisted decision explains the actual path");
    const skipped=targeted.status==="SKIPPED";
    check(skipped?(info.mode==="composition"?job.result.output_by_step.node_2===null&&job.result.output_by_step.node_4.sum==="15":job.result.output===null&&job.result.output_status==="SKIPPED"&&$("csv-dag-status").textContent.includes("未产出报告")):(info.mode==="composition"?job.result.output_by_step.node_2.sum==="30"&&job.result.output_by_step.node_4.sum==="15":job.result.output.sum==="15"&&job.result.output_status==="PRODUCED"),"skipped report never fabricates result or acceptance");
    check(job.model_requests===0&&job.business_writes===0&&job.owner_acceptance==="PENDING"&&job.semantic_status==="UNKNOWN"&&job.publishable===false,"existing authority and acceptance gates retained");
    await w.showApp(info.app);await w.csvDagRead(undefined,job.id,plan);
    check(JSON.stringify(JSON.parse($("csv-dag-result").textContent))===JSON.stringify(job),"cold page reads same persisted branch without rerun");
  }
  check(new Set(jobs.map(j=>j.id)).size===info.inputs.length,"distinct inputs create distinct runs while sharing plan");
  await idle();const result={status:"PASS",checks,requests,plan,jobs,loaded_source_sha256:hashes,native:"NOT_RUN"};fs.writeFileSync(path.join(root,"results.json"),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,"failure.json"),JSON.stringify({status:"FAIL",checks,error:e.message,requests,loaded_source_sha256:hashes},null,2));console.error(e.stack);process.exitCode=1;}finally{if(dom){await idle();dom.window.close();}}})();
