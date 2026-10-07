"use strict";
const manifestNamespace="bounded-report-manifest.v1",manifestIntents=new Map(),manifestPromotions=new Map();
let manifestContext=null,manifestEpoch=0;
const manifestCurrent=c=>manifestContext===c&&c.epoch===manifestEpoch&&c.identity===token&&c.project===$("project-select").value&&c.generation===appSelectionGeneration&&activeApp===c.id;
const manifestIntentKey=c=>JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]);
function clearReportManifest(){manifestEpoch++;manifestContext=null;$("manifest-report-form").hidden=true;$("manifest-report-form").reset();$("manifest-report-retry").hidden=true;$("manifest-report-refresh").hidden=true;}
function manifestValid(a,pid,id){return !!a&&a.namespace===manifestNamespace&&a.project_id===pid&&a.id===id&&boundedHash(a.fingerprint)&&a.state==="PREVIEW_ONLY"&&a.formal_publication_enabled===false&&a.owner_acceptance==="PENDING"&&a.semantic_status==="UNKNOWN"&&a.overall_run_acceptance==="NOT_ACCEPTED"&&a.input_guidance?.mode==="BOUNDED_REPORT"&&a.candidate?.namespace===manifestNamespace&&a.candidate.manifest?.app_id===id&&a.candidate.report_proof?.source_run_id===a.candidate.manifest.source_run_ref&&a.candidate.report_proof?.runtime_id===a.runtime_id;}
// Compare pinned canonical data without depending on PostgreSQL JSON object key order.
function manifestSameValue(a,b){if(a===b)return true;if(Array.isArray(a))return Array.isArray(b)&&a.length===b.length&&a.every((v,i)=>manifestSameValue(v,b[i]));if(!a||!b||typeof a!=="object"||typeof b!=="object"||Array.isArray(b))return false;const keys=Object.keys(a).sort(),other=Object.keys(b).sort();return keys.length===other.length&&keys.every((k,i)=>k===other[i]&&manifestSameValue(a[k],b[k]));}
function manifestPromotionMatches(a,c){const p=a?.candidate?.report_proof,origin=c.app?.origin;return manifestValid(a,c.project,a?.id)&&/^app_[a-f0-9]{32}$/.test(a.id)&&!!origin&&p.named_app_id===c.id&&p.expected_named_fingerprint===c.app.fingerprint&&p.runtime_id===c.app.runtime_id&&["extraction_run_id","expected_plan_fingerprint","expected_check_fingerprint","target_resource_id","expected_target_hash"].every(k=>p[k]===origin[k]);}
async function openReportManifest(a,generation){
 if(!manifestValid(a,activeAppProject,activeApp))throw Error("VERSION_CONFLICT");
 const c={id:a.id,project:a.project_id,identity:token,generation,epoch:manifestEpoch,app:a,busy:false};manifestContext=c;c.pending=manifestIntents.get(manifestIntentKey(c));
 $("app-title").textContent=a.name+" · canonical Report Manifest · PREVIEW_ONLY";
 $("app-origin").textContent=`来源 Run ${a.candidate.report_proof.source_run_id} · 提取 Run ${a.candidate.report_proof.extraction_run_id} · 已保存草案 ${a.candidate.report_proof.named_app_id} · 有限 A-S 条件报告 · 共享已有项目运行授权 · 语义 UNKNOWN · 整体 NOT_ACCEPTED · 用户确认 PENDING · 未发布。默认无 provider 会停在 WAITING_RESOURCE。`;
 $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,fingerprint:a.fingerprint,runtime_id:a.runtime_id,validation:a.validation},null,2);
 $("csv-extraction-panel").hidden=true;$("manifest-report-form").hidden=false;$("manifest-report-refresh").hidden=false;manifestButtons(c);await readManifestHistory(c);return manifestCurrent(c);
}
function manifestButtons(c){if(!manifestCurrent(c))return;c.pending=manifestIntents.get(manifestIntentKey(c));const sending=c.busy||!!c.pending?.sending;for(const e of $("manifest-report-form").elements)e.disabled=sending||!!c.pending;$("manifest-report-retry").hidden=!c.pending;$("manifest-report-retry").disabled=sending;$("manifest-report-refresh").disabled=sending;}
async function readManifestHistory(c=manifestContext){
 if(!c||!manifestCurrent(c))return;
 let data;try{data=await api(`/api/projects/${c.project}/apps/${c.id}/history`);}catch(e){if(manifestCurrent(c))clearApp();throw e;}
 if(!manifestCurrent(c))return;if(!manifestValid(data,c.project,c.id)||data.fingerprint!==c.app.fingerprint||data.runtime_id!==c.app.runtime_id||!manifestSameValue(data.candidate,c.app.candidate)||!Array.isArray(data.history)||data.history.some(item=>!item||item.namespace!==manifestNamespace||!manifestRunReceipt(item.run))){clearApp();throw Error("VERSION_CONFLICT");}
 $("app-history").replaceChildren(...data.history.map(item=>{const section=document.createElement("section");section.append(row(`实际 Run ${item.run.run_id} · ${item.run.status} · 整体 NOT_ACCEPTED · 语义 UNKNOWN · 用户确认 PENDING`));const pre=document.createElement("pre");pre.textContent=JSON.stringify({input:item.input,result:item.run.result?.protocol_result?.evidence?.output||null},null,2);section.append(pre);return section;}));
}
function manifestRunReceipt(r){return !!r&&/^run_[a-f0-9]{32}$/.test(r.run_id)&&r.namespace==="conditional-run-checks.v1"&&r.phase==="cold"&&Number.isInteger(r.version)&&r.version>0&&Number.isInteger(r.fence)&&r.fence>=0&&r.owner_semantic_acceptance==="PENDING"&&r.overall_run_acceptance==="NOT_ACCEPTED"&&["QUEUED","RUNNING","WAITING_INPUT","WAITING_APPROVAL","WAITING_RESOURCE","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","RECONCILING","SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(r.status);}
function manifestReceipt(r,c){return manifestRunReceipt(r)&&r.app_id===c.id&&r.candidate_fingerprint===c.app.fingerprint&&r.compiler_namespace===manifestNamespace&&r.state==="PREVIEW_ONLY";}
async function runManifestReport(retry=false){
 const c=manifestContext;if(!c||!manifestCurrent(c)||c.busy||c.pending?.sending)return;if(c.pending&&!retry)throw Error("先恢复原回执");
 const earlierUnknown=!!c.pending,key=manifestIntentKey(c),body=retry?c.pending?.body:{expected_candidate_fingerprint:c.app.fingerprint,input:boundedFacts("manifest-report"),request_key:reportKey()};if(!body)return;
 const intent=c.pending||{body};c.pending=intent;intent.sending=true;manifestIntents.set(key,intent);c.busy=true;let accepted=false;$("app-output").textContent="正在提交新的 Scenario；接受回执尚未确认。";manifestButtons(c);
 try{const r=await api(`/api/projects/${c.project}/apps/${c.id}/previews`,"POST",body);if(!manifestReceipt(r,c))throw Error("VERSION_CONFLICT");accepted=true;manifestIntents.delete(key);c.pending=null;if(!manifestCurrent(c))return;$("app-output").textContent=`已接受新 Run ${r.run_id} · ${r.status} · PREVIEW_ONLY；刷新实际历史。整体 NOT_ACCEPTED。`;await readManifestHistory(c);}
 catch(e){const rejected=e.httpStatus===422&&!earlierUnknown&&!retry&&!accepted;if(rejected){manifestIntents.delete(key);c.pending=null;}if(manifestCurrent(c))$("app-output").textContent=rejected?"输入被拒绝，尚未接受；可修正后重新提交。":e.message+"；接受结果未确认时，用原键恢复回执。";}
 finally{intent.sending=false;c.busy=false;if(manifestContext)manifestButtons(manifestContext);}
}
async function promoteReportManifest(retry=false){
 const c=reportAppContext;if(!c||!reportCurrent(c)||!c.app||c.promoteBusy)return;
 const key=JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]);let intent=manifestPromotions.get(key);if(intent&&!retry)throw Error("先恢复原保存回执");const earlierUnknown=!!intent;if(intent?.sending)return;
 const body=retry?intent?.body:{expected_app_fingerprint:c.app.fingerprint,request_key:reportKey()};if(!body)return;intent=intent||{body};intent.sending=true;manifestPromotions.set(key,intent);c.promoteBusy=true;let accepted=false;manifestPromotionButtons(c);
 try{const made=await api(`/api/projects/${c.project}/conditional-apps/${c.id}/manifest-preview`,"POST",body);if(!manifestPromotionMatches(made,c))throw Error("VERSION_CONFLICT");if(!reportCurrent(c))return;const verified=await api(`/api/projects/${c.project}/apps/${made.id}`);if(!reportCurrent(c))return;if(!manifestPromotionMatches(verified,c)||verified.fingerprint!==made.fingerprint||!manifestSameValue(verified.candidate,made.candidate))throw Error("VERSION_CONFLICT");accepted=true;manifestPromotions.delete(key);await refreshApps();if(!reportCurrent(c))return;await showApp(made.id,c.project);}
 catch(e){const rejected=e.httpStatus===422&&!earlierUnknown&&!retry&&!accepted;if(rejected)manifestPromotions.delete(key);if(reportCurrent(c))$("report-manifest-status").textContent=rejected?"保存被拒绝，尚未接受；可修正后重新提交。":e.message+"；用原键恢复保存回执。";}
 finally{intent.sending=false;c.promoteBusy=false;manifestPromotionButtons();}
}
function manifestPromotionButtons(c=reportAppContext){if(!c||!reportCurrent(c)||!c.app)return;const intent=manifestPromotions.get(JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint])),pending=!!intent;$("report-manifest-promote").hidden=false;$("report-manifest-promote").disabled=!!c.promoteBusy||pending;$("report-manifest-promote-retry").hidden=!pending;$("report-manifest-promote-retry").disabled=!!c.promoteBusy||!!intent?.sending;}
$("manifest-report-form").onsubmit=safe(()=>runManifestReport());$("manifest-report-retry").onclick=safe(()=>runManifestReport(true));$("manifest-report-refresh").onclick=safe(()=>readManifestHistory());$("report-manifest-promote").onclick=safe(()=>promoteReportManifest());$("report-manifest-promote-retry").onclick=safe(()=>promoteReportManifest(true));
