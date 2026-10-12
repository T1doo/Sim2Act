"use strict";
// Production request settlement, controlled promises. HTTP/Worker/native NOT_RUN.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),{JSDOM}=require("jsdom");
const [scenario,sourcePath,outputPath]=process.argv.slice(2);
assert(["late-r1-after-r2","normal-r1"].includes(scenario));
const source=fs.readFileSync(sourcePath,"utf8"),web=path.dirname(sourcePath);
const dom=new JSDOM(fs.readFileSync(path.join(web,"index.html"),"utf8"),{runScripts:"outside-only",url:"http://controlled.invalid/"}),w=dom.window;
w.$=id=>w.document.getElementById(id);Object.defineProperty(w,"crypto",{value:crypto.webcrypto});
w.$("project-select").append(new w.Option("project","project"));w.$("project-select").value="project";
w.token="controlled-principal";w.activeApp="app";w.appSelectionGeneration=1;w.calls=[];w.reads=[];
const current=source.match(/function engineeringCurrent\(view\) \{[\s\S]*?\n\}/)[0];
const submit=source.match(/async function submitInternal\(view,retry=false\) \{[\s\S]*?\n\}/)[0];
w.eval(`let engineering=null;const engineeringPending=new Map();let appOwnGoalView=null;
function appOwnGoalCurrent(){return false;}
function textWorkflowInput(){return {term_a:"A",term_b:"B",emit_report:true};}
function api(url,method="GET",body){return new Promise((resolve,reject)=>calls.push({url,method,body,resolve,reject}));}
async function showInternalInstance(id,view){reads.push({kind:"instance",id});}
async function showInternalRun(id,view,instance){reads.push({kind:"run",id});}
${current}\n${submit}
globalThis.probe={open(){engineering={token,project:"project",app:activeApp,appGeneration:appSelectionGeneration,instanceGeneration:1,workflow:true,instance:{id:"instance",revision:1,release_fingerprint:"a".repeat(64)}};return engineering;},submit:submitInternal,pending:()=>engineeringPending.get("instance")};`);
(async()=>{let status="FAIL",error=null,checks={},r1key,r2key;
try{
 const oldView=w.probe.open(),oldReply=w.probe.submit(oldView);assert.equal(w.calls.length,1);r1key=w.calls[0].body.request_key;assert(r1key);
 if(scenario==="normal-r1"){
  w.calls[0].resolve({run_id:"run-r1"});await oldReply;
  checks={own_pending_cleared:w.probe.pending()===undefined,normal_readback:w.reads.length===2&&w.reads[1].id==="run-r1",one_post:w.calls.length===1&&w.calls[0].method==="POST"};
 }else{
  w.appSelectionGeneration++;const newView=w.probe.open(),recovery=w.probe.submit(newView,true);
  assert.equal(w.calls.length,2);assert.equal(w.calls[1].method,"GET");assert(w.calls[1].url.endsWith("/"+r1key));w.calls[1].resolve({id:"run-r1"});await recovery;assert.equal(w.probe.pending(),undefined);
  const newReply=w.probe.submit(newView),pendingR2=w.probe.pending();r2key=pendingR2.request_key;assert.notEqual(r2key,r1key);assert.equal(w.calls.length,3);assert.equal(w.calls[2].method,"POST");
  const beforeReads=w.reads.length,beforeStatus=w.$("internal-run-status").textContent;
  w.calls[0].resolve({run_id:"run-r1"});await oldReply;
  checks={r2_pending_identity_kept:w.probe.pending()===pendingR2,r2_original_key_kept:w.probe.pending()?.request_key===r2key,stale_view_no_readback:w.reads.length===beforeReads,stale_view_no_status:w.$("internal-run-status").textContent===beforeStatus,original_key_get_only:w.calls[1].method==="GET"&&w.calls[1].url.endsWith("/"+r1key),exact_two_posts:w.calls.filter(r=>r.method==="POST").length===2};
  w.calls[2].resolve({run_id:"run-r2"});await newReply;checks.r2_clears_own_pending=w.probe.pending()===undefined;checks.r2_normal_readback=w.reads.at(-1).id==="run-r2";
 }
 status=Object.values(checks).every(Boolean)?"PASS":"FAIL";
}catch(e){error=e.stack;console.error(error);}
const proof={status,scenario,checks,error,r1key,r2key,requests:w.calls.map(({url,method,body})=>({url,method,body})),reads:w.reads,source_sha256:crypto.createHash("sha256").update(source).digest("hex"),classification:"CONTROLLED_LOCAL_PRODUCTION_FUNCTION_JSDOM",http:"NOT_RUN",worker:"NOT_RUN",native_browser:"NOT_RUN",real_model:"NOT_RUN",real_human_semantics:"NOT_RUN"};
fs.writeFileSync(outputPath,JSON.stringify(proof,null,2)+"\n");dom.window.close();console.log(JSON.stringify({scenario,status,checks}));assert.equal(status,"PASS","only the exact pending request may settle its recovery key");
})().catch(e=>{console.error(e.stack);dom.window.close();process.exitCode=1;});
