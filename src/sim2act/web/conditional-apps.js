"use strict";
// Fixed server wrappers only; Scenario is the only user execution input.
let reportAppContext=null,reportAppEpoch=0,reportSaveContext=null,reportSaveEpoch=0,reportListGeneration=0;
const reportIntents=new Map();
const reportKey=()=>"report-"+crypto.randomUUID();
const reportScope=()=>({identity:token,project:$("project-select").value});
const reportScopeCurrent=c=>c.identity===token&&c.project===$("project-select").value;
const reportCurrent=c=>reportAppContext===c&&c.epoch===reportAppEpoch&&reportScopeCurrent(c);
function clearReportApps(clearList=true){
 $("report-manifest-promote").hidden=true;$("report-manifest-promote-retry").hidden=true;$("report-manifest-status").textContent="";
 reportAppEpoch++;reportListGeneration++;reportAppContext=null;if(clearList)$("report-app-list").replaceChildren();$("report-app-form").hidden=true;$("report-app-name").textContent="选择保存的条件报告草案";$("report-app-output").replaceChildren();$("report-app-history").replaceChildren();$("report-app-origin").textContent="";$("report-app-retry").hidden=true;$("report-app-form").reset();
}
function clearReportSave(){reportSaveEpoch++;reportSaveContext=null;$("report-save-form").hidden=true;$("report-save-name").value="假设差旅条件报告";$("report-save-status").textContent="";$("report-save-retry").hidden=true;}
async function refreshReportApps(){
 const scope=reportScope();if(!scope.project)return;
 if(reportAppContext&&!reportScopeCurrent(reportAppContext))clearReportApps();
 const generation=++reportListGeneration,current=()=>reportScopeCurrent(scope)&&generation===reportListGeneration;
 let items;try{items=await api(`/api/projects/${scope.project}/conditional-apps`);}catch(e){if(current())clearReportApps();throw e;}if(!current())return;
 $("report-app-list").replaceChildren(...items.items.map(a=>row(`${a.name} · PREVIEW_ONLY · 用户确认 PENDING`,()=>openReportApp(a.id),"打开条件报告草案")));
 if(!items.items.length)$("report-app-list").textContent="暂无保存的条件报告草案；先完成来源绑定检查和有限候选提取。";
}
async function prepareReportSave(bounded,plan,resources){
 clearReportSave();const c={...reportScope(),epoch:reportSaveEpoch,bounded,plan,busy:false};reportSaveContext=c;
 $("report-save-resource").replaceChildren(new Option("选择已有授权规则资料", ""),...resources.filter(r=>["txt","md"].includes(r.format)&&r.hash===bounded.source.hash).map(r=>new Option(r.name+" · "+r.id,r.id)));
 $("report-save-form").hidden=false;
}
const reportSaveCurrent=c=>reportSaveContext===c&&c.epoch===reportSaveEpoch&&reportScopeCurrent(c)&&boundedCurrent(c.bounded);
async function saveReportDraft(retry=false){
 const c=reportSaveContext;if(!c||!reportSaveCurrent(c)||c.busy)return;
 const resource=$("report-save-resource").value,name=$("report-save-name").value;if(!retry&&(!resource||!name))return;
 const body=retry?c.pending?.body:{extraction_run_id:c.bounded.extractRun.run_id,expected_plan_fingerprint:c.plan.plan_fingerprint,expected_check_fingerprint:c.plan.source_check_fingerprint,target_resource_id:resource,expected_target_hash:c.bounded.source.hash,name,request_key:reportKey()};if(!body)return;
 if(c.pending&&!retry)throw Error("先恢复同一保存回执");c.pending={body};c.busy=true;$("report-save-submit").disabled=true;
 try{const made=await api(`/api/projects/${c.project}/conditional-apps`,"POST",body);if(made.namespace!=="bounded-conditional-app.v1"||made.project_id!==c.project||!/^app_[a-f0-9]{32}$/.test(made.id)||!boundedHash(made.fingerprint)||made.state!=="PREVIEW_ONLY"||made.formal_publication_enabled!==false||made.owner_acceptance!=="PENDING")throw Error("VERSION_CONFLICT");c.pending=null;if(!reportSaveCurrent(c))return;$("report-save-status").textContent=`已保存 ${made.name} · ${made.id}；PREVIEW_ONLY，未签收、未发布。`;await refreshReportApps();}
 catch(e){if(reportSaveCurrent(c)){$("report-save-status").textContent=e.message+"；未确认接受结果，请用原键恢复回执。";$("report-save-retry").hidden=false;}}
 finally{c.busy=false;if(reportSaveCurrent(c))$("report-save-submit").disabled=!!c.pending;}
}
async function openReportApp(id){
 clearReportApps(false);const c={...reportScope(),epoch:reportAppEpoch,id,busy:false};reportAppContext=c;
 let a;try{a=await api(`/api/projects/${c.project}/conditional-apps/${id}`);}catch(e){if(reportCurrent(c))clearReportApps();throw e;}if(!reportCurrent(c))return;
 if(a.namespace!=="bounded-conditional-app.v1"||a.id!==id||a.project_id!==c.project)throw Error("VERSION_CONFLICT");c.app=a;
 c.pending=reportIntents.get(JSON.stringify([c.identity,c.project,c.id,a.fingerprint]));
 $("report-app-name").textContent=a.name;$("report-app-origin").textContent=JSON.stringify({state:a.state,authorization_domain:a.authorization_domain,runtime_id:a.runtime_id,origin:a.origin,semantic:a.semantic_status,owner:a.owner_acceptance},null,2);$("report-app-form").hidden=false;
 reportAppButtons(c);if(typeof manifestPromotionButtons === "function")manifestPromotionButtons(c);await readReportHistory(c);
}
function reportAppButtons(c){if(!reportCurrent(c))return;for(const e of $("report-app-form").elements)e.disabled=c.busy||!!c.pending;$("report-app-retry").hidden=!c.pending;$("report-app-retry").disabled=c.busy;}
async function readReportHistory(c=reportAppContext){
 if(!c||!reportCurrent(c)||!c.app)return;let data;try{data=await api(`/api/projects/${c.project}/conditional-apps/${c.id}/history`);}catch(e){if(reportCurrent(c))clearReportApps();throw e;}if(!reportCurrent(c))return;
 if(data.app.fingerprint!==c.app.fingerprint)throw Error("VERSION_CONFLICT");
 $("report-app-history").replaceChildren(...data.items.map(item=>{const container=document.createElement("section");container.append(row(`实际 Run ${item.run.run_id} · ${item.run.status} · 整体 NOT_ACCEPTED · 语义 UNKNOWN · 用户确认 PENDING`));const pre=document.createElement("pre");pre.textContent=JSON.stringify({scenario:item.scenario,actual_result:item.run.result?.protocol_result?.evidence?.output||null},null,2);container.append(pre);return container;}));
}
async function runReportApp(retry=false){
 const c=reportAppContext;if(!c||!reportCurrent(c)||!c.app||c.busy)return;
 if(c.pending&&!retry)throw Error("先恢复原回执");
 const key=JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]);
 const earlierUnknown=!!c.pending;
 const body=retry?c.pending?.body:{expected_app_fingerprint:c.app.fingerprint,scenario:boundedFacts("report-app"),request_key:reportKey()};if(!body)return;
 const intent=c.pending||{body};c.pending=intent;reportIntents.set(key,intent);c.busy=true;reportAppButtons(c);
 try{const made=await api(`/api/projects/${c.project}/conditional-apps/${c.id}/runs`,"POST",body);if(made.app_id!==c.id||made.app_fingerprint!==c.app.fingerprint||!/^run_[a-f0-9]{32}$/.test(made.run_id)||made.namespace!=="conditional-run-checks.v1"||made.phase!=="cold"||!Number.isInteger(made.version)||made.version<1||!Number.isInteger(made.fence)||made.fence<0||made.owner_semantic_acceptance!=="PENDING"||made.overall_run_acceptance!=="NOT_ACCEPTED"||!["QUEUED","RUNNING","WAITING_INPUT","WAITING_APPROVAL","WAITING_RESOURCE","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","RECONCILING","SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(made.status))throw Error("VERSION_CONFLICT");reportIntents.delete(key);c.pending=null;if(!reportCurrent(c))return;$("report-app-output").textContent=`已接受新 Run ${made.run_id} · ${made.status}；刷新只读历史。未启用 provider，整体未验收。`;await readReportHistory(c);}
 catch(e){if(e.httpStatus===422&&!earlierUnknown&&!retry){reportIntents.delete(key);c.pending=null;}if(reportCurrent(c))$("report-app-output").textContent=e.message+"；用原键恢复接受回执，不另建任务。";}
 finally{c.busy=false;reportAppButtons(c);}
}
$("report-save-form").onsubmit=safe(()=>saveReportDraft());$("report-save-retry").onclick=safe(()=>saveReportDraft(true));$("report-app-list-refresh").onclick=safe(refreshReportApps);$("report-app-form").onsubmit=safe(()=>runReportApp());$("report-app-retry").onclick=safe(()=>runReportApp(true));$("report-app-refresh").onclick=safe(()=>readReportHistory());
