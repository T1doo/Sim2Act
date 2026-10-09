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
 let data;try{data=await api(`/api/projects/${c.project}/apps/${c.id}/history`);}catch(e){if(manifestCurrent(c)){clearApp();e.manifestReadCleared=c;}throw e;}
 if(!manifestCurrent(c))return;if(!manifestValid(data,c.project,c.id)||data.fingerprint!==c.app.fingerprint||data.runtime_id!==c.app.runtime_id||!manifestSameValue(data.candidate,c.app.candidate)||!Array.isArray(data.history)||data.history.some(item=>!item||item.namespace!==manifestNamespace||!manifestRunReceipt(item.run))){clearApp();throw Error("VERSION_CONFLICT");}
 await readPresentationHistory(c,data.history);if(!manifestCurrent(c))return;
 $("app-history").replaceChildren(...data.history.map(item=>{const section=document.createElement("section");section.append(row(`实际 Run ${item.run.run_id} · ${item.run.status} · 整体 NOT_ACCEPTED · 语义 UNKNOWN · 用户确认 PENDING`));const pre=document.createElement("pre");pre.textContent=JSON.stringify({input:item.input,result:item.run.result?.protocol_result?.evidence?.output||null},null,2);section.append(pre,presentationControls(c,item));return section;}));
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

// Independent archived-result presentation drafts. Canonical views and PROJECT
// impact jobs remain unchanged; a text readback is never overall acceptance.
const presentationIntents=new Map();
const presentationBase=c=>`/api/projects/${c.project}/apps/${c.id}/delivery-graph/report-presentations`;
const presentationKey=(c,r)=>JSON.stringify([c.identity,c.project,c.id,c.app.fingerprint,r.run_id,r.version,r.fence,r.result_fingerprint]);
function presentationFlags(v,c){return !!v&&v.project_id===c.project&&v.app_id===c.id&&v.kind==="ARCHIVED_RESULT_PRESENTATION_ONLY"&&v.actual_material_verification==="PENDING"&&v.semantic_status==="UNKNOWN"&&v.owner_acceptance==="PENDING"&&v.overall_run_acceptance==="NOT_ACCEPTED"&&v.formal_publication_enabled===false&&v.canonical_patch_executed===false&&v.business_writes===0&&v.model_requests===0;}
function presentationPatch(v,c,r){return presentationFlags(v,c)&&v.namespace==="report-presentation.v1"&&boundedHash(v.patch_fingerprint)&&v.candidate_fingerprint===c.app.fingerprint&&boundedHash(v.baseline_graph_fingerprint)&&v.definition?.slot_key==="view:text:decision"&&/^node_[a-f0-9]{32}$/.test(v.definition.slot_id)&&manifestSameValue(v.definition.baseline_view,{component_ref:"text",output_field:"decision"})&&manifestSameValue(v.definition.view,{component_ref:"text",output_field:"explanation"})&&manifestSameValue(v.result_binding,{run_id:r.run_id,version:r.version,fence:r.fence,result_fingerprint:r.result_fingerprint})&&v.impact_plan?.receipt?.revalidation_scope==="PROJECT"&&["PENDING","BLOCKED_PARTIAL"].includes(v.project_revalidation_status);}
function presentationCheck(v,c,r,p){return presentationFlags(v,c)&&v.namespace==="report-presentation-readback.v1"&&boundedHash(v.check_fingerprint)&&v.patch_fingerprint===p.patch_fingerprint&&v.slot_id===p.definition.slot_id&&v.display_readback_status==="PASS"&&v.project_revalidation_status===p.project_revalidation_status&&manifestSameValue(v.result_binding,p.result_binding)&&manifestSameValue(v.view,p.definition.view)&&typeof v.text==="string"&&v.text===r.result?.protocol_result?.evidence?.output?.explanation&&v.baseline_text===r.result?.protocol_result?.evidence?.output?.decision;}
function presentationText(text,label,slot){const section=document.createElement("section");section.className="report-text-presentation";section.dataset.slot=slot;section.append(row(label));const content=document.createElement("p");content.className="report-view-text";content.textContent=text;section.append(content);return section;}
function repaintPresentationButtons(){for(const box of document.querySelectorAll(".report-presentation-controls"))box.repaint?.();}
async function reconcilePresentationIntent(c,intent,box){
 intent.busy=false;repaintPresentationButtons();
 const current=manifestContext;
 // A new selection must read its own current authority/result/history. Never
 // render an old closure's output or resume its next write after navigation.
 if(!current||(current===c&&box.isConnected)||!manifestCurrent(current)||current.identity!==c.identity||current.project!==c.project||current.id!==c.id||current.app.fingerprint!==c.app.fingerprint)return;
 try{await readManifestHistory(current);}catch(e){const cleared=e.manifestReadCleared===current&&manifestContext===null&&activeApp===null&&appSelectionGeneration===current.generation+1;if(current.identity!==token||current.project!==$("project-select").value||(!manifestCurrent(current)&&!cleared))return;$("error").textContent=e.message+"；当前展示回读失败，请重新打开或刷新；不使用旧回执内容。";}
}
function presentationControls(c,item){
 const r=item.run,box=document.createElement("section");box.className="report-presentation-controls";
 const original=r.result?.protocol_result?.evidence?.output;if(typeof original?.decision==="string")box.append(presentationText(original.decision,"原版本 · text / decision","view:text:decision"));
 if(r.status!=="WAITING_APPROVAL"||typeof original?.explanation!=="string"||!boundedHash(r.result_fingerprint))return box;
 const button=document.createElement("button"),confirm=document.createElement("button"),status=document.createElement("p"),versions=document.createElement("section");button.type=confirm.type="button";button.className="report-presentation-propose";confirm.className="report-presentation-confirm";box.append(button,confirm,status,versions);
 const key=presentationKey(c,r);let intent=presentationIntents.get(key);
 const paint=()=>{intent=presentationIntents.get(key);button.textContent=intent&&!intent.patch?"用原键恢复展示草案":"保存 text: decision → explanation 展示草案";button.disabled=!!intent?.busy||!!intent?.patch;confirm.hidden=!intent?.patch;confirm.disabled=!!intent?.busy||!!intent?.checked;confirm.textContent=intent?.checkUnknown?"用原键恢复精确版本文本检查":`确认展示版本 ${intent?.patch?.patch_fingerprint?.slice(0,12)||""} 并检查文本`;};box.repaint=()=>{if(manifestCurrent(c)&&box.isConnected)paint();};paint();
 button.onclick=safe(async()=>{
  if(!manifestCurrent(c)||intent?.busy||intent?.patch)return;
  intent=intent||{deriveKey:reportKey(),planKey:reportKey(),definitionKey:reportKey(),checkKey:reportKey()};presentationIntents.set(key,intent);intent.busy=true;paint();status.textContent="正在保存独立展示草案；PROJECT 扩验保持未完成。";
  try{
   const graphURL=`/api/projects/${c.project}/apps/${c.id}/delivery-graph`;
   if(!intent.graph){const g=await api(graphURL+"/derive","POST",{expected_candidate_fingerprint:c.app.fingerprint,request_key:intent.deriveKey});if(!manifestCurrent(c))return;if(g.project_id!==c.project||g.app_id!==c.id||g.candidate_fingerprint!==c.app.fingerprint||!boundedHash(g.graph_fingerprint)||!Array.isArray(g.graph?.nodes))throw Error("VERSION_CONFLICT");intent.graph=g;}
   if(!intent.plan){
    const slot=intent.graph.graph.nodes.find(n=>n.kind==="VIEW"&&n.key==="view:text:decision");if(!slot)throw Error("VERSION_CONFLICT");
    // A later rejection cannot establish that an earlier lost reply was never
    // accepted. Freeze that uncertainty before every same-key plan request.
    const previousUnknown=!!intent.planUnknown;intent.planUnknown=true;intent.planRejected=false;
    let p;try{p=await api(graphURL+"/plans","POST",{expected_graph_fingerprint:intent.graph.graph_fingerprint,request_key:intent.planKey,changes:[{node_id:slot.id,expected_revision:slot.revision,expected_content_fingerprint:slot.content_fingerprint}]});}
    catch(e){if(!previousUnknown&&e.httpStatus===400&&e.message==="LOCK_CONFLICT"){intent.planUnknown=false;intent.planRejected=true;}throw e;}
    if(!manifestCurrent(c))return;if(p.project_id!==c.project||p.app_id!==c.id||p.receipt?.revalidation_scope!=="PROJECT"||!boundedHash(p.native_outer_fingerprint)||p.receipt.patch_executed!==false)throw Error("VERSION_CONFLICT");intent.plan=p;intent.planUnknown=false;
   }
   intent.body=intent.body||{expected_candidate_fingerprint:c.app.fingerprint,expected_graph_fingerprint:intent.graph.graph_fingerprint,plan_key:intent.planKey,expected_plan_fingerprint:intent.plan.native_outer_fingerprint,run_id:r.run_id,expected_run_version:r.version,expected_run_fence:r.fence,expected_result_fingerprint:r.result_fingerprint,view:{component_ref:"text",output_field:"explanation"},request_key:intent.definitionKey};
   const p=await api(presentationBase(c),"POST",intent.body);if(!presentationPatch(p,c,r)||p.request_key!==intent.definitionKey||p.baseline_graph_fingerprint!==intent.graph.graph_fingerprint||p.impact_plan.native_outer_fingerprint!==intent.plan.native_outer_fingerprint)throw Error("VERSION_CONFLICT");intent.patch=p;if(manifestCurrent(c))status.textContent=`已保存展示草案 ${p.patch_fingerprint}；PROJECT ${p.project_revalidation_status}；实际材料 PENDING，未验收、未发布。`;
  }catch(e){const locked=e.httpStatus===400&&e.message==="LOCK_CONFLICT"&&intent.planRejected===true&&intent.planUnknown===false&&!intent.plan&&!intent.body;if(locked&&presentationIntents.get(key)===intent)presentationIntents.delete(key);if(manifestCurrent(c))status.textContent=locked?"LOCK_CONFLICT；保留锁定内容，解锁后须新精确规划。":e.message+"；保留原键恢复。";}finally{await reconcilePresentationIntent(c,intent,box);}
 });
 confirm.onclick=safe(async()=>{
  if(!manifestCurrent(c)||!intent?.patch||intent.busy||intent.checked)return;intent.busy=true;intent.checkUnknown=true;paint();
  try{const v=await api(presentationBase(c)+`/${encodeURIComponent(intent.definitionKey)}/checks`,"POST",{expected_patch_fingerprint:intent.patch.patch_fingerprint,request_key:intent.checkKey});if(!presentationCheck(v,c,r,intent.patch)||v.request_key!==intent.checkKey)throw Error("VERSION_CONFLICT");intent.checked=v;if(manifestCurrent(c)){versions.replaceChildren(presentationText(v.text,`新展示版本 · text / explanation · 文本回读 PASS · PROJECT ${v.project_revalidation_status} · 实际材料 PENDING · NOT_ACCEPTED`,v.slot_id));status.textContent="仅历史结果展示预览；原计算结果和 canonical 图保留。";}}
  catch(e){if(manifestCurrent(c))status.textContent=e.message+"；用原键恢复精确版本文本检查。";}finally{await reconcilePresentationIntent(c,intent,box);}
 });
 if(intent?.checked&&presentationPatch(intent.patch,c,r)&&presentationCheck(intent.checked,c,r,intent.patch))versions.append(presentationText(intent.checked.text,`新展示版本 · text / explanation · 文本回读 PASS · PROJECT ${intent.checked.project_revalidation_status} · 实际材料 PENDING · NOT_ACCEPTED`,intent.checked.slot_id));
 return box;
}
async function readPresentationHistory(c,items){
 if(!items.some(item=>item.run.result))return;
 let data;try{data=await api(presentationBase(c));}catch(e){if(e.httpStatus===409&&e.detail?.includes("has not been derived"))return;if(manifestCurrent(c)){clearApp();e.manifestReadCleared=c;}throw e;}
 if(!manifestCurrent(c))return;if(!presentationFlags(data,c)||data.namespace!=="report-presentation-history.v1"||!Array.isArray(data.items)){clearApp();throw Error("VERSION_CONFLICT");}
 for(const item of data.items){const p=item.patch,r=items.find(x=>x.run.run_id===p?.result_binding?.run_id)?.run;if(!r||!presentationPatch(p,c,r)||!Array.isArray(item.checks)||item.checks.some(v=>!presentationCheck(v,c,r,p))){clearApp();throw Error("VERSION_CONFLICT");}const key=presentationKey(c,r),old=presentationIntents.get(key);if(!old?.busy)presentationIntents.set(key,{...old,definitionKey:p.request_key,patch:p,checkKey:item.checks.at(-1)?.request_key||old?.checkKey||reportKey(),checked:item.checks.at(-1)});}
}
