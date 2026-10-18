"use strict";
const projectVersionIntents=new Map();
async function projectVersionSourceSeal(s,source,execution,current){
 const e=s.execution_source,app={...s.draft},parent={app,id:app.id,project:app.project_id};
 if(!deliverySame(e,execution))return false;
 const plan=await api(`/api/projects/${app.project_id}/apps/${app.id}/csv-dag/${encodeURIComponent(e.plan_key)}`);if(!current())return false;
 const proof=await api(`/api/csv-dag/runs/${e.run_id}`);if(!current())return false;
 if(!await csvDagPlanSeal(plan,{parent})||!await csvDagJobSeal(proof,{parent},plan)||dagReuseShape(plan)?.version!==dagReuseFixedVersion||!deliverySame(source.proof,proof))return false;
 const expected={version:dagReuseFixedVersion,run_id:source.run_id,run_version:proof.version,fence:source.fence,accepted_fingerprint:execution.accepted_fingerprint,plan_key:source.plan_key,plan_fingerprint:plan.plan_fingerprint,source_hash:plan.source_hash,graph_fingerprint:plan.graph_fingerprint,authorization_fingerprint:plan.authorization_fingerprint,receipt_fingerprints:await Promise.all(proof.steps.map(deliveryDigest)),columns:s.column_overlay.column_binding.schema.enum,limits:plan.definition.manifest.runtime_limits,aggregate_step:"aggregate",report_step:"report",default_column:s.column_overlay.column_binding.value};
 return deliveryHash(e.accepted_fingerprint)&&proof.status==="SUCCEEDED"&&source.cancel_intent===false&&plan.input.column===expected.default_column&&deliverySame(e,expected);
}
async function dagReuseFixedSeal(rel,c){
 const s=rel.snapshot,o=s.project_column_origin;if(!o||!/^[-A-Za-z0-9_]{1,64}$/.test(o.patch_key)||o.namespace!=="finite-project-column-versions.v1"||o.project_id!==c.parent.project||o.source_app_id!==c.parent.id||o.principal_id!==rel.principal_id)return false;
 const current=()=>csvDagCurrent(c),evidence=await api(`/api/internal/releases/${rel.id}/project-column-origin`);if(!current())return false;
 if(evidence.namespace!=="finite-project-column-versions.v1"||evidence.release_id!==rel.id||evidence.release_fingerprint!==rel.fingerprint||!deliverySame(evidence.origin,o))return false;
 const affected=evidence.affected,source=evidence.source;
 if(affected?.app_id!==c.parent.id||source?.app_id!==c.parent.id||source.phase!=="patched"||!deliverySame(s.column_overlay,affected.patch.definition)||!deliverySame(s.column_overlay_graph,affected.patch.graph)||!deliverySame(s.draft.candidate,affected.patch.definition.candidate))return false;
 const approval=await api(`/api/internal/approvals/${rel.approval_id}`);if(!current())return false;
 if(approval.id!==rel.approval_id||approval.principal_id!==rel.principal_id||approval.project_id!==rel.project_id||approval.kind!=="release"||approval.consumed!==true||approval.fingerprint!==await deliveryDigest(approval.payload)||!deliverySame(approval.payload.snapshot,s)||!deliverySame(approval.payload.project_column_group,{namespace:"finite-project-column-versions.v1",project_id:o.project_id,app_id:o.app_id,request_key:o.patch_key,receipt_fingerprint:o.receipt_fingerprint}))return false;
 return await projectVersionSourceSeal(s,source,evidence.execution_source,current);
}
function projectVersionsClear(){document.getElementById("project-version-controls")?.remove();}
function projectVersionsOpen(c,receipt,patch){
 projectVersionsClear();
 if(receipt?.state!=="CHECKED_PROJECT_CANDIDATE"||!patch)return;
 const principal=patch.principal_id;
 const box=document.createElement("fieldset");box.id="project-version-controls";
 const legend=document.createElement("legend");legend.textContent="将已保存的列修改生成可运行内部版本";
 const info=document.createElement("p");info.textContent=`新实例默认列 ${receipt.column||receipt.affected[0].patch.definition.column_binding.value}；可用原材料的数值列作为新输入。整组保存独立实例，原版本及数据保留；正式发布关闭。`;
 const ack=document.createElement("input");ack.type="checkbox";ack.id="project-version-confirm";
 const label=document.createElement("label");label.append("已核对下方精确 overlay、全部新版本、来源和到期预算",ack);
 const button=(id,text)=>{const b=document.createElement("button");b.type="button";b.id="project-version-"+id;b.textContent=text;return b;};
 const prepare=button("preview","查看整组可运行版本预览"),commit=button("commit","确认并生成整组内部版本及实例"),read=button("read","用原修改键只读恢复版本"),cancel=button("cancel","放弃这组版本批准"),status=document.createElement("p"),proof=document.createElement("pre"),items=document.createElement("div");status.id="project-version-status";
 box.append(legend,info,prepare,label,commit,read,cancel,status,items,proof);$("delivery-panel").append(box);
 const current=()=>deliveryCurrent(c)&&box.isConnected,key=receipt.patch_key,context=JSON.stringify([projectColumnKey(c),key]),base=projectColumnBase(c)+"/"+encodeURIComponent(key)+"/internal-versions";
 let preview=null,value=null,busy=false;
 const paint=()=>{if(!current())return;const unknown=projectVersionIntents.has(context);prepare.disabled=busy||unknown||!!preview;commit.disabled=busy||unknown||!preview||!ack.checked||value?.state!=="INTERNAL_VERSIONS_PREVIEW"||preview.expires_at*1000<=Date.now();cancel.disabled=busy||unknown||!preview||value?.state!=="INTERNAL_VERSIONS_PREVIEW";read.disabled=busy;ack.disabled=busy||unknown;};
 const flags=v=>v?.namespace==="finite-project-column-versions.v1"&&v.project_id===c.project&&v.app_id===c.id&&v.principal_id===principal&&v.request_key===key&&v.receipt_fingerprint===receipt.receipt_fingerprint&&v.publishable===false&&v.formal_publication_enabled===false&&v.canonical_patch_executed===false&&v.business_writes===0&&v.model_requests===0&&v.semantic_status==="UNKNOWN"&&v.owner_acceptance==="PENDING";
 const verifyPreview=async p=>{
  const {preview_fingerprint,cached,...body}=p;
  if(!flags(p)||p.state!=="INTERNAL_VERSIONS_PREVIEW"||p.patch_fingerprint!==receipt.patch_fingerprint||!deliverySame(p.affected,receipt.affected)||!deliverySame(p.preserved,receipt.preserved)||!deliverySame(p.budget,receipt.budget)||!Array.isArray(p.entries)||!deliverySame(p.entries.map(v=>v.app_id).sort(),receipt.affected.map(v=>v.app_id).sort())||new Set(p.entries.map(v=>v.app_id)).size!==p.entries.length||!Number.isFinite(p.issued_at)||!Number.isFinite(p.expires_at)||p.expires_at<=p.issued_at||p.expires_at>p.issued_at+p.budget.per_run.run_seconds||await deliveryDigest(body)!==preview_fingerprint)return false;
  const issued=Math.min(...p.entries.map(e=>e.approval.expires_at))-300;
  if(p.issued_at!==issued||p.expires_at!==Math.min(issued+p.budget.per_run.run_seconds,...p.entries.map(e=>e.approval.expires_at)))return false;
  for(const e of p.entries){const approved=await api(`/api/internal/approvals/${e.approval.id}`);if(!current())return false;
   if(approved.id!==e.approval.id||approved.principal_id!==principal||approved.project_id!==c.project||approved.kind!=="release"||approved.fingerprint!==e.approval.fingerprint||approved.expires_at!==e.approval.expires_at||approved.fingerprint!==await deliveryDigest(approved.payload)||!deliverySame(approved.payload.snapshot,e.snapshot)||!deliverySame(approved.payload.project_column_group,{namespace:"finite-project-column-versions.v1",project_id:c.project,app_id:c.id,request_key:key,receipt_fingerprint:receipt.receipt_fingerprint}))return false;
   const affected=receipt.affected.find(v=>v.app_id===e.app_id),source=receipt.jobs.find(v=>v.app_id===e.app_id&&v.phase==="patched"),s=e.snapshot,x=s?.execution_source;
   if(!x||x.version!==dagReuseFixedVersion||x.run_id!==source.run_id||x.source_hash!==affected.patch.source_hash||x.default_column!==affected.patch.definition.column_binding.value||!Array.isArray(x.columns)||!deliverySame(x.columns,affected.patch.definition.column_binding.schema.enum)||!deliverySame(x.limits,p.budget.per_run)||!deliverySame(s.column_overlay,affected.patch.definition)||!deliverySame(s.column_overlay_graph,affected.patch.graph)||s.namespace!=="INTERNAL_ENGINEERING_ONLY"||s.publishable!==false||s.formal_publication_enabled!==false||s.model_requests!==0||s.semantic_status!=="UNKNOWN"||s.owner_acceptance!=="PENDING"||s.draft.id!==e.app_id||s.draft.project_id!==c.project||s.draft.fingerprint!==affected.patch.candidate_fingerprint||!deliverySame(s.draft.candidate,affected.patch.definition.candidate)||!deliverySame(s.project_column_origin,{namespace:"finite-project-column-versions.v1",project_id:c.project,principal_id:principal,app_id:c.id,patch_key:key,receipt_fingerprint:receipt.receipt_fingerprint,source_app_id:e.app_id})||e.snapshot_fingerprint!==await deliveryDigest(s)||!/^iapproval_[a-f0-9]{32}$/.test(e.approval?.id)||!deliveryHash(e.approval?.fingerprint)||!Number.isFinite(e.approval?.expires_at)||e.approval.expires_at<p.expires_at)return false;
   const evidence=await api(`/api/internal/approvals/${e.approval.id}/project-column-origin`);if(!current())return false;
   if(evidence.namespace!=="finite-project-column-versions.v1"||evidence.approval_id!==e.approval.id||evidence.approval_fingerprint!==e.approval.fingerprint||!deliverySame(evidence.origin,s.project_column_origin)||!await projectVersionSourceSeal(s,source,evidence.execution_source,current))return false;
  }return true;
 };
 const render=()=>{if(!current())return;proof.textContent=JSON.stringify({preview,receipt:value},null,2);items.replaceChildren();if(preview)items.append(row(`整组 ${preview.entries.length} 个版本；批准到期 ${new Date(preview.expires_at*1000).toISOString()}；原键 ${key}`));
  if(value?.state==="EXECUTABLE_INTERNAL_VERSIONS")for(const e of value.entries){const b=button("open-"+e.app_id,`打开 ${e.app_id} 的修改后实例`);b.onclick=safe(async()=>{
    if(!current())return;const identity=c.identity,project=c.project;let generation;await showApp(e.app_id,project,g=>generation=g);
    const next=csvDagContext;if(!next||!csvDagCurrent(next)||next.parent.generation!==generation||next.parent.identity!==identity||next.parent.project!==project||next.parent.id!==e.app_id)return;
    await readDeliveryGraph();if(!csvDagCurrent(next))return;await dagReuseHistory(next);if(!csvDagCurrent(next))return;
    $("dag-reuse-instance").value=e.instance_id;await dagReuseRead(next,e.instance_id);
   });items.append(row(`${e.release_id} · ${e.instance_id} · 内部可运行，发布关闭`),b);}
  status.textContent=value?.state||"请先查看整组版本预览";
 };
 const recover=async intent=>{if(intent&&intent.key!==key)throw Error("VERSION_CONFLICT");const p=await api(base+"/definition");if(!current())return false;if(!await verifyPreview(p)||intent?.body.expected_preview_fingerprint&&intent.body.expected_preview_fingerprint!==p.preview_fingerprint||intent?.body.expected_receipt_fingerprint&&intent.body.expected_receipt_fingerprint!==p.receipt_fingerprint)throw Error("VERSION_CONFLICT");if(!current())return false;const v=await api(base);if(!current())return false;
  if(v.state==="EXECUTABLE_INTERNAL_VERSIONS"){
   const {group_fingerprint,cached,...body}=v;if(!flags(v)||v.preview_fingerprint!==p.preview_fingerprint||await deliveryDigest(body)!==group_fingerprint||!Array.isArray(v.entries)||!deliverySame(v.entries.map(e=>e.app_id).sort(),p.entries.map(e=>e.app_id).sort())||new Set(v.entries.map(e=>e.instance_id)).size!==v.entries.length)throw Error("VERSION_CONFLICT");
   for(const e of v.entries){const expected=p.entries.find(x=>x.app_id===e.app_id),rel=await api(`/api/internal/releases/${e.release_id}`);if(!current())return false;const i=await api(`/api/internal/instances/${e.instance_id}`);if(!current())return false;if(e.release_fingerprint!==expected.snapshot_fingerprint||rel.fingerprint!==e.release_fingerprint||rel.approval_id!==expected.approval.id||!deliverySame(rel.snapshot,expected.snapshot)||i.id!==e.instance_id||i.project_id!==c.project||i.source_app_id!==e.app_id||i.runtime_id!==rel.snapshot.draft.runtime_id||i.history?.[0]?.release_id!==rel.id)throw Error("VERSION_CONFLICT");}
  }else if(v.state==="CANCELLED"){if(!deliverySame(v,{namespace:"finite-project-column-versions.v1",request_key:key,preview_fingerprint:p.preview_fingerprint,state:"CANCELLED"}))throw Error("VERSION_CONFLICT");}
  else if(!deliverySame({...v,cached:undefined},{...p,cached:undefined}))throw Error("VERSION_CONFLICT");
  if(intent?.phase==="commit"&&v.state!=="EXECUTABLE_INTERNAL_VERSIONS"||intent?.phase==="cancel"&&v.state!=="CANCELLED")throw Error("OUTCOME_UNKNOWN");if(!current())return false;preview=p;value=v;ack.checked=false;render();return true;
 };
 const failure=e=>{if(current()){preview=null;value=null;ack.checked=false;items.replaceChildren();proof.textContent="";status.textContent=e.message+"；保留原修改键，仅只读恢复。";}};
 const submit=async phase=>{if(!current()||busy||projectVersionIntents.has(context)||phase==="commit"&&(!preview||!ack.checked))return;const body=phase==="preview"?{expected_receipt_fingerprint:receipt.receipt_fingerprint,request_key:key}:{expected_preview_fingerprint:preview.preview_fingerprint,consent:phase==="commit"?"CONFIRM_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS":"CANCEL_EXACT_PROJECT_COLUMN_INTERNAL_VERSIONS",request_key:key};const intent={phase,key,body:JSON.parse(JSON.stringify(body))};projectVersionIntents.set(context,intent);busy=true;let awaitingPost=true;paint();try{await api(base+(phase==="preview"?"":"/"+phase),"POST",body);awaitingPost=false;if(!current())return;if(await recover(intent))projectVersionIntents.delete(context);}catch(e){if(awaitingPost&&[400,403,409,422].includes(e.httpStatus)&&projectVersionIntents.get(context)===intent)projectVersionIntents.delete(context);failure(e);}finally{busy=false;paint();}};
 prepare.onclick=safe(()=>submit("preview"));commit.onclick=safe(()=>submit("commit"));cancel.onclick=safe(()=>submit("cancel"));read.onclick=safe(async()=>{if(!current()||busy)return;busy=true;paint();try{if(await recover(projectVersionIntents.get(context)))projectVersionIntents.delete(context);}catch(e){failure(e);}finally{busy=false;paint();}});ack.onchange=paint;render();paint();
}
