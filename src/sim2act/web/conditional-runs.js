"use strict";
// Actual server Run evidence only. No client Report, provider, grant, or candidate construction.
let boundedRunContext=null,boundedRunGeneration=0;
const boundedRunRequests=new Map();
const boundedRequestKey=()=>"bounded-"+Array.from(crypto.getRandomValues(new Uint32Array(4)),n=>n.toString(16)).join("-");
const boundedHash=v=>typeof v==="string"&&/^[a-f0-9]{64}$/.test(v);
function clearConditionalRuns(){
 if(typeof clearReportSave === "function")clearReportSave();
 boundedRunGeneration++;boundedRunContext=null;
 for(const id of ["source-form","refresh","retry","check","extract","plan","cold-form","cold-check"])$("condition-run-"+id).hidden=true;
 for(const id of ["output","check-output","extract-output","plan-text","cold-output","cold-check-output"])$("condition-run-"+id).replaceChildren();
 $("condition-run-status").textContent="旧来源绑定证据已清除；请显式打开当前授权资料。";
 $("condition-run-source-form").reset();$("condition-run-cold-form").reset();
}
function boundedCurrent(c){return boundedRunContext===c&&c.identity===token&&c.project===$("project-select").value&&c.generation===boundedRunGeneration;}
function showConditionalRuns(source){
 clearConditionalRuns();boundedRunContext={identity:token,project:$("project-select").value,generation:boundedRunGeneration,source,busy:false,revision:0};
 const pending=[...boundedRunRequests.values()].find(p=>p.state==="unknown"&&p.identity===token&&p.project===$("project-select").value);if(pending)boundedRunContext.pending=pending;
 $("condition-run-source-form").hidden=false;$("condition-run-status").textContent="已核查授权资料；只提交显式假设，不提交人工报告。";boundedButtons();
}
function boundedFacts(prefix){
 const bool=k=>$(prefix+"-"+k).value===""?null:$(prefix+"-"+k).value==="true";
 const num=k=>$(prefix+"-"+k).value===""?null:Number($(prefix+"-"+k).value);
 return {kind:"HYPOTHETICAL_EMPLOYEE",trip_ended:bool("trip"),amount:num("amount"),receipt_present:bool("receipt"),approved:bool("approved"),elapsed_days:num("days")};
}
function boundedButtons(){
 const c=boundedRunContext;if(!c||!boundedCurrent(c))return;
 const unresolved=c.pending?.state==="unknown",locked=c.busy||unresolved;
 for(const id of ["start","check","extract","cold-start","cold-check","refresh"])$("condition-run-"+id).disabled=locked;
 $("condition-run-retry").hidden=!unresolved;$("condition-run-retry").disabled=c.busy;
 $("condition-run-check").hidden=c.sourceRun?.status!=="WAITING_APPROVAL"||!boundedHash(c.sourceRun?.result_fingerprint);
 $("condition-run-extract").hidden=c.check?.value?.candidate_eligible!==true||c.check.value.result_fingerprint!==c.sourceRun?.result_fingerprint||!!c.extractRun;
 $("condition-run-cold-check").hidden=c.coldRun?.status!=="WAITING_APPROVAL"||!boundedHash(c.coldRun?.result_fingerprint);
 for(const form of ["source","cold"])for(const el of $("condition-run-"+form+"-form").elements)el.disabled=locked;
}
function boundedRenderRun(value,id){
 const output=value.result?.protocol_result?.evidence?.output;
 $(id).replaceChildren(row(`Run ${value.run_id} · ${value.phase} · 技术状态 ${value.status} · v${value.version}/fence${value.fence}`),row(`整体 ${value.overall_run_acceptance}；语义 ${value.semantic_status}；用户确认 PENDING；有限技术回执≠整体成功。`));
 if(value.result?.protocol_result?.evidence?.inputs?.scenario_json)$(id).append(row("实际冻结假设："+value.result.protocol_result.evidence.inputs.scenario_json));
 if(output){const pre=document.createElement("pre");pre.textContent=JSON.stringify(output,null,2);$(id).append(pre);}
 if(value.status==="WAITING_RESOURCE")$(id).append(row("当前无可用的已批准 provider/资源；未完成报告，不可检查或提取。请联系本机控制器，不会自动启用模型。"));
}
function boundedRenderCheck(value,id){
 const v=value.value;
 $(id).replaceChildren(row(`绑定检查 ${value.check_id} · ${value.fingerprint} · Run ${v.run_id} · v${v.version}/fence${v.fence}`),row(`有限报告检查 ${v.checks.check_status} · 决策 ${v.checks.decision} · 可提取有限候选 ${v.candidate_eligible===true?"是":"否"}。整体 NOT_ACCEPTED；语义 UNKNOWN；说明文字 NOT_CHECKED；假设事实未核查。`),...v.checks.rule_results.map(r=>row(`${r.rule_id}：${r.satisfaction} · ${r.reason}`)));
}
function boundedPath(c){return `/api/projects/${c.project}/conditional-runs`;}
async function boundedRead(c){
 c.check=null;$("condition-run-check-output").replaceChildren();$("condition-run-cold-check-output").replaceChildren();
 for(const [key,id]of [["sourceRun","output"],["extractRun","extract-output"],["coldRun","cold-output"]]){
  if(!c[key])continue;const rid=c[key].run_id;const value=await api(boundedPath(c)+"/"+rid);if(!boundedCurrent(c))return;
  if(value.namespace!=="conditional-run-checks.v1"||value.run_id!==rid||value.overall_run_acceptance!=="NOT_ACCEPTED")throw Error("VERSION_CONFLICT");
  c[key]=value;if(id)boundedRenderRun(value,"condition-run-"+id);
 }
 const plan=c.extractRun?.status==="SUCCEEDED"&&c.extractRun.result?.compiled_plan;
 $("condition-run-plan").hidden=!plan;$("condition-run-cold-form").hidden=!plan;
 if(plan){
  $("condition-run-plan-text").textContent=JSON.stringify(plan,null,2);
  const resources=await api(`/api/projects/${c.project}/resources`);if(!boundedCurrent(c))return;
  const old=$("condition-run-cold-resource").value;
  $("condition-run-cold-resource").replaceChildren(new Option("请选择当前授权规则资料", ""),...resources.filter(r=>["txt","md"].includes(r.format)&&r.hash===c.source.hash).map(r=>new Option(`${r.name} · ${r.id} · ${r.hash.slice(0,12)}`,r.id)));
  if([...$("condition-run-cold-resource").options].some(o=>o.value===old))$("condition-run-cold-resource").value=old;
  if(typeof prepareReportSave === "function" && (reportSaveContext?.bounded!==c||reportSaveContext?.plan?.plan_fingerprint!==plan.plan_fingerprint))await prepareReportSave(c,plan,resources);
 }
}
async function boundedAction(fn){
 const c=boundedRunContext;if(!c||!boundedCurrent(c)||c.busy)return;
 c.busy=true;boundedButtons();
 try{await fn(c);if(boundedCurrent(c))$("condition-run-status").textContent="已重新核查当前持久来源；每一步仍需显式操作，整体未验收。";}
 catch(error){if(boundedCurrent(c)){
  c.check=null;for(const id of ["output","check-output","extract-output","cold-output","cold-check-output","plan-text"])$("condition-run-"+id).replaceChildren();
  $("condition-run-plan").hidden=true;$("condition-run-cold-form").hidden=true;
  $("condition-run-status").textContent=c.pending?.state==="unknown"?"提交回执未知；只能显式恢复同一键，不能另建重复任务。":`来源或请求不可核验：${error.message}；旧检查与候选失效，不表示业务规则不满足。`;
 }}finally{if(boundedCurrent(c)){c.busy=false;boundedButtons();}}
}
async function boundedSubmit(c,phase,body,retry=false){
 const intent=JSON.stringify([c.identity,c.project,phase,body]);
 let pending=retry?c.pending:boundedRunRequests.get(intent);
 if(!pending){pending={phase,identity:c.identity,project:c.project,body:{...body,request_key:boundedRequestKey()},state:"new"};boundedRunRequests.set(intent,pending);}
 c.pending=pending;const earlierUnknown=pending.state==="unknown"||pending.uncertain===true;pending.state="unknown";
 let reply;
 try{
  reply=await api(boundedPath(c)+"/"+pending.phase,"POST",pending.body);
  if(reply.namespace!=="conditional-run-checks.v1"||reply.phase!==pending.phase||typeof reply.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(reply.run_id)||!Number.isInteger(reply.version)||!Number.isInteger(reply.fence))throw Error("VERSION_CONFLICT");
 }catch(error){
  if(!earlierUnknown&&error.httpStatus>=400&&error.httpStatus<500){pending.state="rejected";}else{pending.uncertain=true;}
  throw error;
 }
 pending.state="accepted";pending.runId=reply.run_id;pending.uncertain=false;boundedButtons();if(!boundedCurrent(c))return;
 c[pending.phase+"Run"]=reply;
 $("condition-run-refresh").hidden=false;await boundedRead(c);
}
async function startBoundedSource(){return boundedAction(async c=>{
 const contract=await api(boundedPath(c)+"/contract");if(!boundedCurrent(c))return;
 await boundedSubmit(c,"source",{resource_id:c.source.resource_id,expected_source_hash:c.source.hash,expected_contract_fingerprint:contract.check_contract_fingerprint,goal:contract.goal,scenario:boundedFacts("condition-run-source")});
});}
async function checkBoundedRun(c,phase){
 await boundedRead(c);if(!boundedCurrent(c))return;
 const run=c[phase+"Run"];if(run?.status!=="WAITING_APPROVAL"||!boundedHash(run.result_fingerprint))throw Error("VERIFICATION_FAILED");
 const key=JSON.stringify([c.identity,c.project,run.run_id,run.result_fingerprint,run.version,run.fence,"check"]);
 let pending=boundedRunRequests.get(key);if(!pending){pending={body:{expected_result_fingerprint:run.result_fingerprint,expected_version:run.version,expected_fence:run.fence,request_key:boundedRequestKey()}};boundedRunRequests.set(key,pending);}
 const reply=await api(boundedPath(c)+"/"+run.run_id+"/checks","POST",pending.body);
 pending.state="accepted";boundedButtons();if(!boundedCurrent(c))return;
 if(reply.value?.run_id!==run.run_id||reply.value.result_fingerprint!==run.result_fingerprint||reply.value.version!==run.version||reply.value.fence!==run.fence)throw Error("VERSION_CONFLICT");
 if(phase==="source")c.check=reply;boundedRenderCheck(reply,"condition-run-"+(phase==="source"?"check-output":"cold-check-output"));
}
async function extractBoundedCandidate(){return boundedAction(async c=>{
 // No cached client eligible claim authorizes extraction: fresh actual Run/check first.
 await checkBoundedRun(c,"source");if(!boundedCurrent(c))return;
 if(c.check.value.candidate_eligible!==true)throw Error("VERIFICATION_FAILED");
 await boundedSubmit(c,"extract",{source_run_id:c.sourceRun.run_id,expected_source_fingerprint:c.sourceRun.result_fingerprint,expected_check_fingerprint:c.check.fingerprint});
});}
async function startBoundedCold(){return boundedAction(async c=>{
 await boundedRead(c);if(!boundedCurrent(c))return;
 const plan=c.extractRun?.result?.compiled_plan;if(c.extractRun?.status!=="SUCCEEDED"||!boundedHash(plan?.plan_fingerprint))throw Error("VERIFICATION_FAILED");
 await boundedSubmit(c,"cold",{extraction_run_id:c.extractRun.run_id,expected_plan_fingerprint:plan.plan_fingerprint,resource_id:$("condition-run-cold-resource").value,scenario:boundedFacts("condition-run-cold")});
});}
$("condition-run-source-form").onsubmit=safe(startBoundedSource);
$("condition-run-refresh").onclick=safe(()=>boundedAction(boundedRead));
$("condition-run-retry").onclick=safe(()=>boundedAction(c=>boundedSubmit(c,c.pending.phase,{},true)));
$("condition-run-check").onclick=safe(()=>boundedAction(c=>checkBoundedRun(c,"source")));
$("condition-run-extract").onclick=safe(extractBoundedCandidate);
$("condition-run-cold-form").onsubmit=safe(startBoundedCold);
$("condition-run-cold-check").onclick=safe(()=>boundedAction(c=>checkBoundedRun(c,"cold")));
$("condition-run-source-form").oninput=()=>{
 const c=boundedRunContext;if(!c)return;
 const fields=[...$("condition-run-source-form").elements].filter(e=>e.id).map(e=>[e.id,e.value]);
 const source=c.source;showConditionalRuns(source);for(const [id,value]of fields)$(id).value=value;$("condition-run-status").textContent="源假设已变化，旧来源绑定已失效；只可显式提交新假设。";
};
$("condition-run-cold-form").oninput=()=>{
 const c=boundedRunContext;if(!c)return;
 boundedRunContext={...c,generation:++boundedRunGeneration,busy:false,coldRun:null};$("condition-run-cold-output").replaceChildren();$("condition-run-cold-check-output").replaceChildren();boundedButtons();
};

function reconcileBoundedSources(items){
 const c=boundedRunContext;if(!c||!boundedCurrent(c))return;
 const item=items.find(r=>r.id===c.source.resource_id);
 if(!item||item.hash!==c.source.hash||!["txt","md"].includes(item.format)){clearConditionalRuns();$("condition-run-status").textContent="来源授权或版本已变化，旧绑定检查与候选失效；请重新打开当前资料。";}
}
