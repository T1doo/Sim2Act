"use strict";
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto");
const {JSDOM}=require("jsdom"),out=process.argv[2],info=JSON.parse(fs.readFileSync(path.join(out,"info.json")));
const origin=new URL(info.base).origin,loaded={},checks=[],timers=[],requests=[];
let dom,hold=null,pending=[],gates=[],closing=false;
const check=(value,name)=>{assert(value,name);checks.push({name,status:"PASS"});};
const wait=async(fn)=>{const end=Date.now()+10000;while(!fn()){assert(Date.now()<end,"owned response gate reached");await new Promise(r=>setTimeout(r,5));}};
(async()=>{
 try {
  dom=new JSDOM(await(await fetch(info.base)).text(),{url:info.base,runScripts:"dangerously"});
  const w=dom.window;
  w.setInterval=fn=>{timers.push(fn);return timers.length;};w.clearInterval=()=>{};
  w.crypto.randomUUID=()=>crypto.randomUUID();Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.TextEncoder=require("node:util").TextEncoder;
  w.fetch=async(url,options={})=>{
   const target=new URL(url,info.base);assert.equal(target.origin,origin);requests.push({path:target.pathname,method:options.method||"GET"});
   const result=await fetch(target,options);
   if(hold&&target.pathname===`/api/runs/${info.run_id}`){const gate=hold;hold=null;gate.used=true;await new Promise(resolve=>{gate.release=resolve;if(closing)resolve();});if(gate.reject)throw Error("controlled foreground transport failure");}
   return result;
  };
  for(const name of [...w.document.querySelectorAll("script[src]")].map(s=>new URL(s.src).pathname.slice(1))){
   const code=await(await fetch(info.base+"/"+name)).text();loaded[name]=crypto.createHash("sha256").update(code).digest("hex");const script=w.document.createElement("script");script.textContent=code;w.document.body.append(script);
  }
  w.document.getElementById("token").value="synthetic-test-A";
  await w.document.getElementById("connect").onclick({preventDefault(){}});
  w.document.getElementById("project-select").value=info.project;
  const read=user=>w.eval(`showRun(${JSON.stringify(info.run_id)},${user})`);
  await read(true);check(!!w.document.getElementById("natural-goal-ack"),"initial actual saved plan offers unchecked acknowledgement");
  const poll=timers[0];assert.equal(typeof poll,"function");
  const first={used:false};gates.push(first);hold=first;
  const manual=read(true);pending.push(manual);await wait(()=>first.used);
  const count=requests.filter(r=>r.path===`/api/runs/${info.run_id}`).length;
  const background={used:false};gates.push(background);hold=background;
  let pollDone=false;const polling=poll().finally(()=>{pollDone=true;});pending.push(polling);
  await wait(()=>background.used||pollDone);
  first.release();await manual;
  check(!!w.document.getElementById("natural-goal-ack")&&!w.document.getElementById("natural-goal-ack").checked,"completed explicit read renders full valid plan with fresh unchecked acknowledgement");
  check(requests.filter(r=>r.path===`/api/runs/${info.run_id}`).length===count,"actual background timer cannot send a superseding Run read during explicit read");
  hold=null;if(background.release)background.release();await polling;
  await poll();check(requests.filter(r=>r.path===`/api/runs/${info.run_id}`).length===count+1,"background polling resumes after explicit read finishes");
  const failed={used:false,reject:true};gates.push(failed);hold=failed;
  const failing=read(true).catch(e=>e);pending.push(failing);await wait(()=>failed.used);await poll();failed.release();
  check((await failing).message==="controlled foreground transport failure","explicit read error is retained");
  check(!!w.document.getElementById("run-read-failure")&&!w.document.getElementById("natural-goal-ack"),"failed explicit read clears plan and leaves actual recovery feedback");
  await read(true);check(!!w.document.getElementById("natural-goal-ack"),"foreground recovery is available after failure");
  const recovered=requests.filter(r=>r.path===`/api/runs/${info.run_id}`).length;
  await poll();check(requests.filter(r=>r.path===`/api/runs/${info.run_id}`).length===recovered+1,"failure does not strand subsequent background polling");
  check(requests.every(r=>r.method==="GET"),"all page actions are read-only and do not confirm or execute");
  fs.writeFileSync(path.join(out,"results.json"),JSON.stringify({status:"PASS",checks,posts:0,browser:"JSDOM_NOT_NATIVE",api:"ACTUAL_LOOPBACK_HTTP",loaded_source_sha256:loaded,requests},null,2));
 }catch(error){fs.writeFileSync(path.join(out,"failure.json"),JSON.stringify({status:"FAIL",checks,error:error.message,loaded_source_sha256:loaded,requests},null,2));console.error(error.stack);process.exitCode=1;}
 finally{closing=true;for(const gate of gates)if(gate.release)gate.release();for(const p of pending)await p.catch(()=>{});if(dom)dom.window.close();}
})();
