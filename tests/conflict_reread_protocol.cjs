"use strict";
// Controlled synthetic HTTP fault protocol; real HTTP/Worker proof is separate.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const web=path.join(__dirname,"../src/sim2act/web"),checks=[],windows=[],cases=[],commandCases=[];
const ids={principal:"owner-A",project:"project-A",app:"app-A",instance:"instance-A",run:"run-A",appRun:"apprun-A"};
const browser=require("./durable_browser.cjs")(undefined,{storageEvents:false});
function check(value,label){assert(value,label);checks.push(label);}
function page(options={}){
 const dom=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{url:"http://protocol.test",runScripts:"dangerously"}),w=dom.window;windows.push(w);browser.install(w);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w.crypto,"subtle",{value:crypto.webcrypto.subtle});w.crypto.randomUUID=()=>crypto.randomUUID();w.setInterval=()=>0;
 let release,entered;const waiting=new Promise(resolve=>entered=resolve),calls=[];
 const instance={id:ids.instance,principal_id:ids.principal,project_id:ids.project,source_app_id:ids.app};
 const run={id:ids.run,instance_id:ids.instance,app_run_id:ids.appRun,status:"CANCELLED",version:4,cancel_intent:true};
 if(options.badInstance)Object.assign(instance,options.badInstance);
 if(options.badRun)Object.assign(run,options.badRun);
 w.fetch=async(url,config)=>{
  calls.push({url,method:config.method,authorization:config.headers.Authorization});
  assert.equal(config.method,"GET","reread cannot mutate");
  const stage=url.endsWith("/"+ids.instance)?"instance":url.endsWith("/runs/"+ids.run)?"run":"other";
  if(stage===options.hold){entered();await new Promise(resolve=>release=resolve);}
  if(stage===options.deny||stage==="other")return new Response(JSON.stringify({error:{code:"PERMISSION_DENIED"}}),{status:403});
  return new Response(JSON.stringify(stage==="instance"?instance:run),{status:200});
 };
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=fs.readFileSync(path.join(web,script.getAttribute("src").slice(1)),"utf8");w.document.body.append(node);}
 w.fixture=ids;
 w.eval(`token="synthetic-test-A";activeApp=fixture.app;document.getElementById("project-select").replaceChildren(new Option("Own",fixture.project));engineering={token,project:fixture.project,app:fixture.app,appGeneration:appSelectionGeneration,instanceGeneration:0,runGeneration:0,spec:true,draft:{},instance:{id:fixture.instance,principal_id:fixture.principal}};invalidateInternalContent(engineering);offerInternalRunReread(engineering,{id:fixture.instance,principal_id:fixture.principal},{id:fixture.run,app_run_id:fixture.appRun},identityConnectionGeneration,workspaceSelectionGeneration);document.getElementById("internal-panel").hidden=false;selectWorkspace("apps");offerInternalRunReread(engineering,{id:fixture.instance,principal_id:fixture.principal},{id:fixture.run,app_run_id:fixture.appRun},identityConnectionGeneration,workspaceSelectionGeneration);`);
 const $=id=>w.document.getElementById(id),button=$("internal-run-reread");
 const evidence={options,calls};cases.push(evidence);
 return {w,$,button,calls,waiting,release:()=>release(),evidence};
}
(async()=>{try{
 const good=page();await good.button.onclick();
 check(good.calls.length===2&&good.calls.every(c=>c.method==="GET"&&c.authorization==="Bearer synthetic-test-A"),"explicit reread uses only two authenticated GETs");
 check(JSON.parse(good.$("internal-run-detail").textContent).id===ids.run&&good.$("internal-run-status").textContent.includes("CANCELLED"),"latest original task terminal displays without command");
 good.evidence.transitions=["successful exact-task read, then instance authorization denied"];
 good.evidence.options.deny="instance";await good.button.onclick();
 check(good.$("internal-run-detail").textContent===""&&good.$("internal-run-status").textContent===""&&good.$("internal-status").textContent==="PERMISSION_DENIED","a later authorization denial clears previously displayed terminal status");
 const double=page({hold:"instance"}),reading=double.button.onclick();await double.waiting;await double.button.onclick();
 check(double.calls.length===1&&double.button.disabled,"double click cannot queue another reread");double.release();await reading;
 check(double.calls.length===2&&!double.button.disabled,"one explicit reread completes and permits later manual GET");
 for(const deny of ["instance","run"]){const p=page({deny});await p.button.onclick();check(p.$("internal-run-detail").textContent===""&&p.$("internal-status").dataset.state==="error"&&p.$("internal-status").textContent==="PERMISSION_DENIED","fresh "+deny+" authorization denial clears content");check(p.calls.length===(deny==="instance"?1:2),"authorization denial has no fallback or mutation: "+deny);}
 for(const field of ["id","principal_id","project_id","source_app_id"]){const p=page({badInstance:{[field]:"foreign"}});await p.button.onclick();check(p.calls.length===1&&p.$("internal-run-detail").textContent===""&&p.$("internal-status").dataset.state==="error","mismatched instance "+field+" blocks Run GET");}
 for(const field of ["id","instance_id","app_run_id"]){const p=page({badRun:{[field]:"foreign"}});await p.button.onclick();check(p.calls.length===2&&p.$("internal-run-detail").textContent===""&&p.$("internal-status").dataset.state==="error","mismatched Run "+field+" never renders");}
 for(const hold of ["instance","run"]){
  for(const change of ["identity","reconnect","workspace","instance"]){
   const p=page({hold}),action=p.button.onclick();await p.waiting;
   if(change==="identity")p.$("identity-switch").click();
   if(change==="reconnect")p.w.eval('identityConnectionGeneration++;'); // Same-token ABA fault, old view deliberately preserved.
   if(change==="workspace"){p.w.document.querySelector('#workspace-nav [data-tab="resources"]').click();p.w.document.querySelector('#workspace-nav [data-tab="apps"]').click();}
   if(change==="instance")await p.w.eval('showInternalInstance("instance-B")'); // Actual selection path, synthetic GET403.
   const before={detail:p.$("internal-run-detail").textContent,status:p.$("internal-status").textContent,runStatus:p.$("internal-run-status").textContent,calls:p.calls.length};
   p.release();await action;await p.button.onclick();
   check(p.$("internal-run-detail").textContent===before.detail&&p.$("internal-status").textContent===before.status&&p.$("internal-run-status").textContent===before.runStatus&&p.calls.length===before.calls,"late "+hold+" response and captured old callback ignored after "+change);
  }
 }
 check(cases.every(c=>c.calls.every(r=>r.method==="GET")),"all synthetic recovery fault cases remain GET-only");
 for(const pending of [false,true]){
  const p=page(),calls=[];let release,entered;const waiting=new Promise(resolve=>entered=resolve);
  const evidence={explicit_command_test:true,pending,calls};commandCases.push(evidence);
  p.w.fetch=async(url,config)=>{calls.push({url,method:config.method});if(config.method==="POST"){if(pending){entered();await new Promise(resolve=>release=resolve);}return new Response(JSON.stringify({error:{code:"VERSION_CONFLICT"}}),{status:409});}return new Response(JSON.stringify({id:ids.run,instance_id:ids.instance,app_run_id:ids.appRun,status:"PAUSED",version:3,cancel_intent:false}),{status:200});};
  await p.w.eval('engineering.instance={id:fixture.instance,principal_id:fixture.principal};showInternalRun(fixture.run)');
  const resume=[...p.$("internal-controls").querySelectorAll("button")].find(b=>b.textContent==="继续");
  let action;if(pending){action=resume.onclick();await waiting;}
  p.w.document.querySelector('#workspace-nav [data-tab="resources"]').click();p.w.document.querySelector('#workspace-nav [data-tab="apps"]').click();
  if(!pending){await resume.onclick();check(calls.filter(c=>c.method==="POST").length===1&&!!p.$("internal-run-reread"),"new explicit click after workspace return sends command and offers reread on 409");}
  else{const before=p.$("internal-status").textContent;release();await action;check(!p.$("internal-run-reread")&&p.$("internal-status").textContent===before,"old command 409 received after workspace return cannot offer stale reread");}
 }
 fs.writeFileSync(process.argv[2],JSON.stringify({status:"PASS",platform:"SYNTHETIC_HTTP_JSDOM_PROTOCOL_NOT_REAL_SERVER",checks,cases,command_cases:commandCases},null,2));
 }catch(error){fs.writeFileSync(process.argv[2],JSON.stringify({status:"FAIL",error:error.stack,checks,cases,command_cases:commandCases},null,2));throw error;}finally{windows.forEach(w=>w.close());}})().catch(error=>{console.error(error);process.exitCode=1;});
