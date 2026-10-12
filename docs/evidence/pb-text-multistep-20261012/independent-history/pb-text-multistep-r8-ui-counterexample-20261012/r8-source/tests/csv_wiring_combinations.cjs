"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const root=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(root,"info.json"))),checks=[],requests=[],hashes={};
let dom,w,page;
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
  w.fetch=async(url,opts={})=>{page.requests++;try{const target=new URL(url,info.base);assert.equal(target.origin,info.base);requests.push({path:target.pathname,method:opts.method||"GET",body:opts.body&&JSON.parse(opts.body)});const r=await fetch(target,opts);return new Response(await r.arrayBuffer(),{status:r.status,headers:r.headers});}finally{page.requests--;}};
  for(const name of Array.from(w.document.querySelectorAll("script[src]")).map(s=>s.getAttribute("src").slice(1))){const code=await(await fetch(info.base+"/"+name)).text();hashes[name]=crypto.createHash("sha256").update(code).digest("hex");const script=w.document.createElement("script");script.textContent=code;w.document.body.append(script);}
  $("token").value="synthetic-test-A";$("connect").click();await wait(()=>$("login").hidden&&$("project-select").value===info.project);await idle();await w.showApp(info.app);
  check(!$("csv-dag-panel").hidden,"existing CSV app hosts DAG controls");
  await w.csvDagWiringRead();check($("csv-dag-wiring-ports").querySelectorAll("select").length===3,"exactly three serverallowed semantic ports");
  const options=JSON.parse($("csv-dag-wiring-proof").textContent),selected=options.ports.map((p,i)=>({step_id:p.step_id,port:p.port,source:p.sources[info.choices[i]]}));
  for(const p of selected)$("csv-dag-wire-"+p.step_id+"-"+p.port).value=JSON.stringify(p.source);
  $("csv-dag-column").value="quantity";await w.csvDagSubmit("plan");
  const plan=JSON.parse($("csv-dag-definition").textContent);check(selected.every(p=>JSON.stringify(plan.definition.manifest.workflow.find(s=>s.step_id===p.step_id).inputs[p.port])===JSON.stringify(p.source)),"all selected source ports sealed in actual saved plan");
  check(JSON.stringify(plan.definition.manifest.workflow[1].depends_on)===JSON.stringify(["preview"]),"every combination retains preview barrier");
  check(!$("csv-dag-confirm").checked&&$("csv-dag-run").disabled,"new plan requires explicit exact confirmation");
  $("csv-dag-confirm").checked=true;await w.csvDagSubmit("run");const queued=JSON.parse($("csv-dag-result").textContent);
  const worked=await fetch(info.base+"/__fixture__/work",{method:"POST",headers:{Authorization:"Bearer synthetic-test-A","Content-Type":"application/json"},body:JSON.stringify({run_id:queued.id})});assert(worked.ok,await worked.text());
  await w.csvDagRead();const job=JSON.parse($("csv-dag-result").textContent);
  check(job.status==="SUCCEEDED"&&job.steps.length===3&&job.result.output.sum===info.expected.quantity,"actual worker receipts pass independent CSV total");
  check(job.result.output.count===2&&job.result.output.text==="列 quantity；行数 2；合计 15","actual fixed report schema and text readback");
  const parents=await Promise.all(job.steps.slice(0,2).filter(s=>plan.definition.manifest.workflow[2].depends_on.includes(s.step_id)).map(s=>w.deliveryDigest(s)));
  check(parents.length===(info.choices[1]||info.choices[2]?2:1)&&JSON.stringify(job.steps[2].predecessor_receipts)===JSON.stringify(parents),"report seals exact selected one or two actual predecessors");
  check(job.steps.every((s,i)=>JSON.stringify(s.input_sources)===JSON.stringify(plan.definition.manifest.workflow[i].inputs)),"each actual receipt records every selected input source");
  check(job.model_requests===0&&job.business_writes===0&&job.owner_acceptance==="PENDING"&&job.semantic_status==="UNKNOWN"&&job.publishable===false,"model business semantic and publication gates remain honest");
  await idle();const result={status:"PASS",choices:info.choices,checks,requests,plan,job,expected:info.expected,loaded_source_sha256:hashes,native:"NOT_RUN"};fs.writeFileSync(path.join(root,"results.json"),JSON.stringify(result,null,2));console.log(JSON.stringify({status:result.status,choices:info.choices,checks:checks.length}));
}catch(e){fs.writeFileSync(path.join(root,"failure.json"),JSON.stringify({status:"FAIL",checks,error:e.message,requests,loaded_source_sha256:hashes},null,2));console.error(e.stack);process.exitCode=1;}finally{if(dom){await idle();dom.window.close();}}})();
