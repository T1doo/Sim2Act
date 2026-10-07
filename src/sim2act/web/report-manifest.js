"use strict";
const manifestNamespace="bounded-report-manifest.v1",manifestIntents=new Map(),manifestPromotions=new Map();
let manifestContext=null,manifestEpoch=0;
const manifestCurrent=c=>manifestContext===c&&c.epoch===manifestEpoch&&c.identity===token&&c.project===$("project-select").value&&c.generation===appSelectionGeneration&&activeApp===c.id;
const manifestIntentKey=c=>JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]);
function clearReportManifest(){manifestEpoch++;manifestContext=null;$("manifest-report-form").hidden=true;$("manifest-report-form").reset();$("manifest-report-retry").hidden=true;$("manifest-report-refresh").hidden=true;}
function manifestValid(a,pid,id){return a.namespace===manifestNamespace&&a.project_id===pid&&a.id===id&&boundedHash(a.fingerprint)&&a.state==="PREVIEW_ONLY"&&a.formal_publication_enabled===false&&a.owner_acceptance==="PENDING"&&a.semantic_status==="UNKNOWN"&&a.overall_run_acceptance==="NOT_ACCEPTED"&&a.input_guidance?.mode==="BOUNDED_REPORT"&&a.candidate?.namespace===manifestNamespace&&a.candidate.manifest?.app_id===id;}
async function openReportManifest(a,generation){
 if(!manifestValid(a,activeAppProject,activeApp))throw Error("VERSION_CONFLICT");
 const c={id:a.id,project:a.project_id,identity:token,generation,epoch:manifestEpoch,app:a,busy:false};manifestContext=c;c.pending=manifestIntents.get(manifestIntentKey(c));
 $("app-title").textContent=a.name+" · canonical Report Manifest · PREVIEW_ONLY";
 $("app-origin").textContent="有限 A-S 条件报告 · 共享已有项目运行授权 · 语义 UNKNOWN · 整体 NOT_ACCEPTED · 用户确认 PENDING · 未发布。默认无 provider 会停在 WAITING_RESOURCE。";
 $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,fingerprint:a.fingerprint,runtime_id:a.runtime_id,validation:a.validation},null,2);
 $("csv-extraction-panel").hidden=true;$("manifest-report-form").hidden=false;$("manifest-report-refresh").hidden=false;manifestButtons(c);await readManifestHistory(c);return manifestCurrent(c);
}
function manifestButtons(c){if(!manifestCurrent(c))return;for(const e of $("manifest-report-form").elements)e.disabled=c.busy||!!c.pending;$("manifest-report-retry").hidden=!c.pending;$("manifest-report-retry").disabled=c.busy;}
async function readManifestHistory(c=manifestContext){
 if(!c||!manifestCurrent(c))return;
 let data;try{data=await api(`/api/projects/${c.project}/apps/${c.id}/history`);}catch(e){if(manifestCurrent(c))clearApp();throw e;}
 if(!manifestCurrent(c))return;if(!manifestValid(data,c.project,c.id)||data.fingerprint!==c.app.fingerprint||!Array.isArray(data.history))throw Error("VERSION_CONFLICT");
 $("app-history").replaceChildren(...data.history.map(item=>{const section=document.createElement("section");section.append(row(`实际 Run ${item.run.run_id} · ${item.run.status} · 整体 NOT_ACCEPTED · 语义 UNKNOWN · 用户确认 PENDING`));const pre=document.createElement("pre");pre.textContent=JSON.stringify({input:item.input,result:item.run.result?.protocol_result?.evidence?.output||null},null,2);section.append(pre);return section;}));
}
function manifestReceipt(r,c){return r.app_id===c.id&&r.candidate_fingerprint===c.app.fingerprint&&r.compiler_namespace===manifestNamespace&&r.state==="PREVIEW_ONLY"&&/^run_[a-f0-9]{32}$/.test(r.run_id)&&r.namespace==="conditional-run-checks.v1"&&r.phase==="cold"&&Number.isInteger(r.version)&&r.version>0&&Number.isInteger(r.fence)&&r.fence>=0&&r.owner_semantic_acceptance==="PENDING"&&r.overall_run_acceptance==="NOT_ACCEPTED"&&["QUEUED","RUNNING","WAITING_INPUT","WAITING_APPROVAL","WAITING_RESOURCE","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","RECONCILING","SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(r.status);}
async function runManifestReport(retry=false){
 const c=manifestContext;if(!c||!manifestCurrent(c)||c.busy)return;if(c.pending&&!retry)throw Error("先恢复原回执");
 const earlierUnknown=!!c.pending,key=manifestIntentKey(c),body=retry?c.pending?.body:{expected_candidate_fingerprint:c.app.fingerprint,input:boundedFacts("manifest-report"),request_key:reportKey()};if(!body)return;
 c.pending=c.pending||{body};manifestIntents.set(key,c.pending);c.busy=true;manifestButtons(c);
 try{const r=await api(`/api/projects/${c.project}/apps/${c.id}/previews`,"POST",body);if(!manifestReceipt(r,c))throw Error("VERSION_CONFLICT");manifestIntents.delete(key);c.pending=null;if(!manifestCurrent(c))return;$("app-output").textContent=`已接受新 Run ${r.run_id} · ${r.status} · PREVIEW_ONLY；刷新实际历史。整体 NOT_ACCEPTED。`;await readManifestHistory(c);}
 catch(e){if(e.httpStatus===422&&!earlierUnknown&&!retry){manifestIntents.delete(key);c.pending=null;}if(manifestCurrent(c))$("app-output").textContent=e.message+"；接受结果未确认时，用原键恢复回执。";}
 finally{c.busy=false;manifestButtons(c);}
}
async function promoteReportManifest(retry=false){
 const c=reportAppContext;if(!c||!reportCurrent(c)||!c.app||c.promoteBusy)return;
 const key=JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]);let intent=manifestPromotions.get(key);if(intent&&!retry)throw Error("先恢复原保存回执");const earlierUnknown=!!intent;
 const body=retry?intent?.body:{expected_app_fingerprint:c.app.fingerprint,request_key:reportKey()};if(!body)return;intent=intent||{body};manifestPromotions.set(key,intent);c.promoteBusy=true;manifestPromotionButtons(c);
 try{const made=await api(`/api/projects/${c.project}/conditional-apps/${c.id}/manifest-preview`,"POST",body);if(!manifestValid(made,c.project,made.id)||!/^app_[a-f0-9]{32}$/.test(made.id))throw Error("VERSION_CONFLICT");manifestPromotions.delete(key);if(!reportCurrent(c))return;await refreshApps();if(!reportCurrent(c))return;await showApp(made.id,c.project);}
 catch(e){if(e.httpStatus===422&&!earlierUnknown&&!retry)manifestPromotions.delete(key);if(reportCurrent(c))$("report-manifest-status").textContent=e.message+"；用原键恢复保存回执。";}
 finally{c.promoteBusy=false;manifestPromotionButtons(c);}
}
function manifestPromotionButtons(c=reportAppContext){if(!c||!reportCurrent(c)||!c.app)return;const pending=manifestPromotions.has(JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint]));$("report-manifest-promote").hidden=false;$("report-manifest-promote").disabled=!!c.promoteBusy||pending;$("report-manifest-promote-retry").hidden=!pending;$("report-manifest-promote-retry").disabled=!!c.promoteBusy;}
$("manifest-report-form").onsubmit=safe(()=>runManifestReport());$("manifest-report-retry").onclick=safe(()=>runManifestReport(true));$("manifest-report-refresh").onclick=safe(()=>readManifestHistory());$("report-manifest-promote").onclick=safe(()=>promoteReportManifest());$("report-manifest-promote-retry").onclick=safe(()=>promoteReportManifest(true));
