"use strict";
// Full served page, actual TestClient HTTP, and actual Worker with synthetic transport.
const fs=require("node:fs"),path=require("node:path"),assert=require("node:assert/strict"),crypto=require("node:crypto"),readline=require("node:readline"),{JSDOM}=require("jsdom");
const durableBrowser=require(path.join(process.cwd(),"tests/durable_browser.cjs"))();
const info=JSON.parse(fs.readFileSync(process.argv[2])),checks=[],actions=[],requests=[],assets=[],pending=new Map();
let serial=0,dom,w,$,boots=0,activeFetches=0,dropReply=info.scenario==="lost",runId=null,revocationReceipt=null;
const familyCode=info.family==="pa"?"NATURAL_PA":"NATURAL_PB",familyLabel=info.family==="pa"?"P-A":"P-B",route=info.family+"-use";
readline.createInterface({input:process.stdin}).on("line",line=>{const value=JSON.parse(line),resolve=pending.get(value.id);pending.delete(value.id);assert(resolve,"known IPC reply");resolve(value);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+"\n");});
const check=(condition,label)=>{assert(condition,label);checks.push(label);};
async function wait(test,label){const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(resolve=>setTimeout(resolve,5));}throw Error("bounded page wait: "+label);}
function visible(el){if(!el?.isConnected)return false;for(let node=el;node;node=node.parentElement){const style=w.getComputedStyle(node);if(node.hidden||node.hasAttribute("inert")||style.display==="none"||style.visibility==="hidden")return false;if(node.tagName==="DETAILS"&&!node.open&&!node.querySelector("summary")?.contains(el))return false;}return true;}
async function gesture(el,perform,bindings){assert(visible(el),`visible ${el?.id||el?.textContent}`);assert(!el.matches(":disabled"),`enabled ${el.id}`);el.focus();const work=[],restore=[];for(const [node,key] of bindings){const original=node?.[key];if(typeof original!=="function")continue;const wrapper=function(event){const result=original.call(this,event);work.push(Promise.resolve(result));return result;};node[key]=wrapper;restore.push(()=>{if(node[key]===wrapper)node[key]=original;});}actions.push({boot:boots,id:el.id||el.textContent,visible:true,enabled:true});try{perform();await Promise.all(work);}finally{restore.forEach(fn=>fn());}}
const click=value=>{const el=typeof value==="string"?$(value):value;return gesture(el,()=>el.click(),[[el,"onclick"],[el.form,"onsubmit"]]);};
const edit=(id,value)=>{const el=$(id);return gesture(el,()=>{el.value=value;el.dispatchEvent(new w.Event("input",{bubbles:true}));el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"oninput"],[el,"onchange"]]);};
const confirm=id=>{const el=$(id);return gesture(el,()=>{el.checked=true;el.dispatchEvent(new w.Event("change",{bubbles:true}));},[[el,"onchange"]]);};
const nav=id=>click(w.document.querySelector(`#workspace-nav [data-tab=${id}]`));
const postCount=()=>requests.filter(row=>row.method==="POST").length;
const usePostCount=()=>requests.filter(row=>row.method==="POST"&&row.path.endsWith(`/${route}-runs`)).length;
async function closePage(){if(!dom)return;await wait(()=>activeFetches===0&&pending.size===0,"HTTP drained");await new Promise(resolve=>setImmediate(resolve));await wait(()=>activeFetches===0&&pending.size===0,"HTTP remains drained");dom.window.close();dom=null;}
async function boot(){
 await closePage();const boot=++boots;
 const load=async assetPath=>{const reply=await rpc({method:"GET",path:assetPath});assert.equal(reply.status,200);assets.push({boot,path:assetPath,status:reply.status,sha256:crypto.createHash("sha256").update(reply.text).digest("hex")});return reply.text;};
 dom=new JSDOM(await load("/"),{url:"http://testserver/",runScripts:"dangerously",pretendToBeVisual:true});w=dom.window;durableBrowser.install(w);$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,"crypto",{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement("style");style.textContent=await load("/app.css");w.document.head.append(style);
 w.fetch=async(url,options={})=>{const request={boot,method:options.method||"GET",path:url,headers:options.headers||{},body:options.body?JSON.parse(options.body):undefined};requests.push(request);activeFetches++;try{const reply=await rpc(request);request.status=reply.status;try{request.response=JSON.parse(reply.text);}catch{request.response_text=reply.text;}
  if(dropReply&&request.method==="POST"&&url.endsWith(`/${route}-runs`)){dropReply=false;assert.equal(reply.status,202);request.fault="ACCEPTED_REPLY_LOST_SYNTHETIC";throw Error("synthetic lost accepted natural-use reply");}
  return new Response(reply.text,{status:reply.status,headers:{"Content-Type":reply.content_type||"application/json"}});
 }finally{activeFetches--;}};
 for(const script of [...w.document.querySelectorAll("script[src]")]){const node=w.document.createElement("script");node.textContent=await load(script.getAttribute("src"));w.document.body.append(node);}
 await edit("token","synthetic-test-A");await click("connect");await wait(()=>$('login').hidden&&$('project-select').value===info.project,"connected exact project");
}
async function openEntry(){
 await nav("apps");
 const selector=`[data-use-family="${familyCode}"][data-instance-id="${info.instance}"]`;
 await wait(()=>!!$("use-list").querySelector(selector),"saved natural instance in unified directory");
 const entry=$("use-list").querySelector(selector),text=entry.textContent;
 check(text.includes(info.name)&&text.includes(familyLabel),"directory names saved app and exact natural family");
 check(text.includes(info.release)&&text.includes("pa-natural-spec-app.v1")&&text.includes("结果版本"),"directory shows exact saved Release definition and result version");
 check(text.includes("逐次")&&text.includes("TXT/MD")&&text.includes("Goal"),"directory shows per-use TXT/MD material and saved Goal scope");
 check(text.includes("受限")&&text.includes("未发布")&&text.includes("真实模型关闭"),"directory shows restricted unpublished state and closed real model boundary");
 const button=[...entry.querySelectorAll("button")].find(el=>el.textContent==="使用此自然规范应用");
 check(!!button&&visible(button),"unified directory offers visible natural-app use action");
 await click(button);await wait(()=>visible($("pb-use-panel")),"existing per-use controller visible");
 check(w.eval("activeApp")===info.app&&w.eval("engineering.instance.id")===info.instance,"directory selection opens exact saved app and instance");
}
async function selectRun(){
 const row=[...$("internal-runs").children].find(el=>el.textContent.includes(runId));
 check(!!row,"same new Run appears in persisted task history");await click(row.querySelector("button"));
 await wait(()=>$("owner-run").value===runId&&$("owner-proof").textContent.includes(runId),"same Run automatic manual-review binding");
 const contract=JSON.parse($("owner-proof").textContent).contract;
 check(w.eval("engineering.run.id")===runId&&contract.run_id===runId,"result task and manual review bind the same Run without a second selector");
 check(contract.source_goal.card_id===info.goal&&contract.material.resource_id===info.resource&&contract.result_version===info.expected_version,"manual review binds exact new Goal material and result version");
 check(contract.output.checklist.source_content===info.content,"actual saved new result contains selected third material");
 return contract;
}
(async()=>{let status="FAIL",error=null;try{
 await boot();await openEntry();check(postCount()===0,"cold connect directory and instance opening issue GET only");await rpc({command:"readonly-checkpoint"});
 check($("pb-use-material").value===""&&$("pb-use-goal").value==="","per-use material and Goal require explicit selection");
 await edit("pb-use-material",info.resource);await edit("pb-use-goal",info.goal);await click("pb-use-preview");
 const review=JSON.parse($("pb-use-proof").textContent);
 check(review.namespace===info.family+"-natural-per-run.v1","existing distinct per-use family contract retained");
 check(review.app_id===info.app&&review.release_id===info.release&&review.instance_id===info.instance,"preview preserves saved app Release and instance");
 check(review.target_goal.card_id===info.goal&&review.variable_bindings.resource_id===info.resource,"preview displays exact explicitly selected Goal and material");
 check(review.preview.source_content===info.content,"preview displays this new source");
 if(info.family==="pa"){
  check(review.instance_data_version===info.expected_version-1,"P-A preview preserves exact old result version");
  check(review.real_model_allowance===0,"P-A preview has zero real model allowance");
 }else{
  check(review.effective_candidate.manifest.runtime_limits.max_requests>0&&review.required_permissions.every(p=>["resource.read","artifact.save_text"].includes(p.tool_ref)),"P-B preview retains bounded saved limits and declared permissions");
 }
 check(review.new_model_requests===0&&review.artifact_writes===0&&review.formal_publication_enabled===false,"binding preview performs zero model requests or artifact writes and cannot publish");
 check($("pb-use-submit").disabled&&!$("pb-use-ack").checked,"explicit per-use consent is required and starts blank");
 await confirm("pb-use-ack");
 const submit=$("pb-use-submit");await gesture(submit,()=>{submit.click();submit.click();},[[submit,"onclick"]]);
 if(info.scenario==="lost"){
  check(w.eval("pbUsePending.size")===1&&$("pb-use-submit").disabled&&$("internal-run-submit").disabled,"unknown accepted outcome preserves intent and disables both duplicate submit routes");
  const before=postCount();$("pb-use-submit").click();$("internal-run-submit").click();await new Promise(resolve=>setImmediate(resolve));check(postCount()===before,"disabled duplicate clicks create no second POST");
  await click("pb-use-recover");check(postCount()===before,"unknown intent recovers only original key GET");
 }
 runId=w.eval("engineering.run.id");check(!!runId&&!info.original_runs.includes(runId)&&w.eval("pbUsePending.size")===0,"verified receipt identifies exactly one distinct new Run");
 check(usePostCount()===1,"double click and recovery produce exactly one per-use submission");
 await rpc({command:"worker",run_id:runId});await click("internal-refresh");await selectRun();
 check($("owner-status").textContent.includes("PENDING"),"new result starts independent manual acceptance PENDING");
 for(const version of [...info.old_versions,info.expected_version])check($("internal-data").textContent.includes(`规范成果 v${version}`),`historical result version ${version} remains visible`);
 const article=[...$("internal-data").querySelectorAll(".spec-result")].find(el=>el.querySelector("h3")?.textContent===`规范成果 v${info.expected_version}`);
 await click(article.querySelector('[data-spec-action="view"]'));check(article.textContent.includes("field beacon")&&!article.textContent.includes("desk lamp")&&!article.textContent.includes("garden sensor"),"explicit current-version result read displays only new source");
 await click("owner-prepare");const prepared=JSON.parse($("owner-proof").textContent).contract;
 for(const item of prepared.items){check($("owner-choice-"+item.id).value==="","new result does not inherit historical manual decisions");await edit("owner-choice-"+item.id,"ACCEPT");await edit("owner-reason-"+item.id,"SIMULATED review for synthetic entry test; not real semantic acceptance");}
 await confirm("owner-ack");await click("owner-submit");check($("owner-status").textContent.includes("ACCEPTED")&&$("owner-status").textContent.includes("UNKNOWN"),"explicit simulated manual declaration preserves semantic UNKNOWN");
 await rpc({command:"freeze-readonly-baseline"});const beforeCold=postCount();await boot();await openEntry();check(postCount()===beforeCold,"fresh cold page directory and instance read creates no new Run or POST");await rpc({command:"readonly-checkpoint"});
 for(const version of [...info.old_versions,info.expected_version])check($("internal-data").textContent.includes(`规范成果 v${version}`),`cold page retains result version ${version}`);
 await selectRun();check($("owner-status").textContent.includes("ACCEPTED")&&postCount()===beforeCold,"cold selected same Run reads persisted manual declaration without new write");
 if(info.revoke_after){
  await nav("apps");const savedEntry=$("use-list").querySelector(`[data-use-family="${familyCode}"][data-instance-id="${info.instance}"]`),staleButton=savedEntry?.querySelector("button");
  check(!!staleButton&&visible(staleButton),"authorized directory entry is available before explicit revocation");
  const revoked=await rpc({command:"revoke-original"});check(revoked.status===200,"exact original-bound read Grant explicitly revoked through authorized API");revocationReceipt=JSON.parse(revoked.text);
  const beforeOpen=requests.length,beforePosts=postCount();await click(staleButton);
  const opened=requests.slice(beforeOpen);
  check(opened.some(row=>row.method==="GET"&&row.path===`/api/apps/${info.app}`&&row.status===403),"previously visible natural entry reauthorizes with fresh app GET and receives 403 after revocation");
  check(postCount()===beforePosts&&usePostCount()===1,"revoked stale entry creates no additional Run or POST");
  check(!$("internal-data").textContent&&!$("owner-proof").textContent&&!w.eval("engineering?.instance"),"revoked open clears protected result and manual-review content");
  await rpc({command:"readonly-checkpoint"});
 }
 check(requests.filter(row=>row.path.endsWith(`/${route}-runs`)).every(row=>row.method==="POST"),"natural entry uses existing per-use submission route");
 status="PASS";
 }catch(e){error=e.stack||String(e);process.stderr.write(error+"\n");process.exitCode=1;}finally{
 try{await closePage();}catch(e){error=error||String(e);status="FAIL";process.exitCode=1;}
 fs.writeFileSync(info.output,JSON.stringify({status,error,family:info.family,scenario:info.scenario,run_id:runId,checks,actions,requests,revocation_receipt:revocationReceipt,static_resource_loads:assets,boots,
 classification:"ACTUAL_TESTCLIENT_HTTP_VISIBLE_JSDOM_UNIFIED_ENTRY_ACTUAL_WORKER_MOCK_TRANSPORT",interval_scheduler:"DISABLED_MANUAL_REFRESH",real_model:"NOT_RUN",native_browser:"NOT_RUN",real_human_semantic_acceptance:"NOT_RUN"},null,2));
 process.stdout.write(JSON.stringify({done:true})+"\n");}})();
