"use strict";
// Saved instances share the existing controllers and current authorization checks.
let applicationUse=null,applicationUseGeneration=0,applicationUseListGeneration=0,applicationUseContextGeneration=0;
const applicationUseRequests=new Map();
const applicationUseDownloads=new Set();
const csvUseApp=a=>a?.candidate?.manifest?.validation_suite_ref==="receipt.readback.v1" && a.candidate.actions?.length===1 && a.candidate.actions[0].executor?.kind==="registered_tool" && a.candidate.actions[0].executor.ref==="data.aggregate_csv";
const literalUseApp=a=>a?.input_guidance?.mode==="REGISTERED_LITERAL"&&a.candidate?.manifest?.validation_suite_ref==="source.literal_evidence.v1"&&a.candidate.actions?.length===1&&a.candidate.actions[0].executor?.kind==="registered_tool"&&a.candidate.actions[0].executor.ref==="text.literal_evidence";
const closedTextUseApp=a=>a?.input_guidance?.mode==="CLOSED_TEXT_WORKFLOW"&&a.candidate?.namespace==="closed-text-four-step.v1"&&a.candidate.manifest?.validation_suite_ref==="text.four_step_readback.v1"&&a.candidate.actions?.length===4&&["resource.read","text.literal_evidence","text.literal_evidence","text.citation_report"].every((ref,index)=>{const e=a.candidate.actions[index].executor;return e?.kind==="registered_tool"&&e.ref===ref&&e.version==="1";});
const naturalUseFamily=a=>{
 const c=a?.candidate;if(a?.input_guidance?.mode!=="MODEL_SPEC_CHECKLIST"||c?.namespace!=="pa-natural-spec-app.v1")return null;
 if(c.spec_task?.kind==="pb_natural_spec_task.v1")return "NATURAL_PB";
 return !c.spec_task&&(c.goal_application||c.spec_binding?.kind==="pa_model_spec_material_binding.v1")?"NATURAL_PA":null;
};
const applicationUseCurrent=v=>!!v && applicationUse===v && v.identity===token && v.project===$("project-select").value && v.generation===applicationUseGeneration;
const applicationUseKey=v=>JSON.stringify([v.identity,v.project,v.id]);
function clearApplicationUse(clearList=false){
 applicationUseGeneration++;applicationUse=null;
 if(clearList)clearConditionalChecks(true);
 for(const id of ["use-info","use-output","use-history","use-provenance","use-column","use-acceptance"])$(id).replaceChildren();
 $("use-form").hidden=true;$("use-refresh").hidden=true;$("use-recover").hidden=true;
 if(clearList){applicationUseListGeneration++;applicationUseContextGeneration++;$("use-list").replaceChildren();}
}
async function refreshApplicationUse(apps){
 const identity=token,connection=identityConnectionGeneration,project=$("project-select").value,generation=++applicationUseListGeneration,context=applicationUseContextGeneration;
 const current=()=>identity===token&&connection===identityConnectionGeneration&&project===$("project-select").value&&generation===applicationUseListGeneration;
 const selectable=()=>identity===token&&connection===identityConnectionGeneration&&project===$("project-select").value&&context===applicationUseContextGeneration;
 const rows=[];
  if(typeof csvDagContext!=="undefined"&&csvDagContext?.savedUse&&!apps.some(summary=>summary.id===csvDagContext.parent.id))clearSavedDagUse();
 if(applicationUseCurrent(applicationUse)&&!apps.some(summary=>summary.id===applicationUse.appId))clearApplicationUseData(applicationUse);
 for(const summary of apps){
   if(summary.csv_instance_candidate===false)clearSavedDagUse(summary.id);
  // Family metadata only routes discovery; opening always reauthorizes the selection.
   if(summary.use_family==="CLOSED_TEXT_WORKFLOW"){
    const item=row(`${summary.name} · 四步文本流程 · 固定 TXT/MD（≤1536字节、32行）· 两检索词各≤80码点 + 报告开关 · 0 模型请求 · 未选报告为 PARTIAL，不新增成果。内部应用未发布，语义 UNKNOWN，人工 PENDING（暂不提交人工声明）。打开后明确选择已有实例与运行。`,async()=>{
     if(selectable())await openSavedInternalUse(summary.id,null,"CLOSED_TEXT_WORKFLOW",selectable);
    },"使用此四步文本应用");
    item.dataset.useFamily="CLOSED_TEXT_WORKFLOW";item.dataset.appId=summary.id;rows.push(item);continue;
   }
  if(summary.use_family==="LITERAL_TEXT"){
   const item=row(`${summary.name} · 文本字面检索 · 固定 TXT/MD 材料，检索词可变 · 0 模型请求 · 内部应用未发布；语义 UNKNOWN，人工签收需单独核查。打开后明确选择已有实例与运行。`,async()=>{
    if(selectable())await openSavedInternalUse(summary.id,null,"LITERAL_TEXT",selectable);
   },"使用此文本检索应用");
   item.dataset.useFamily="LITERAL_TEXT";item.dataset.appId=summary.id;rows.push(item);continue;
  }
  if(["NATURAL_PA","NATURAL_PB"].includes(summary.use_family)){
   const item=row(`${summary.name} · ${summary.use_family==="NATURAL_PA"?"P-A 目标生成":"P-B 成功任务提取"} · 定义 ${summary.definition_version} · 适用范围：逐次 TXT/MD 材料 + 已保存 Goal · 受限内部应用，未发布；真实模型默认关闭，语义 UNKNOWN，新运行人工 PENDING。Release、实例修订、结果版本和当前权限在打开后读取并选择。`,async()=>{
    if(selectable())await openSavedNaturalUse(summary.id,null,summary.use_family,selectable);
   },"使用此自然规范应用");
   item.dataset.useFamily=summary.use_family;item.dataset.appId=summary.id;rows.push(item);
   continue;
  }
  if(summary.csv_instance_candidate===false){
   if(applicationUse?.appId===summary.id&&applicationUseCurrent(applicationUse))clearApplicationUseData(applicationUse);
   continue;
  }
  let app,reply,dagInstances,dagReleases;
  try{app=await api(`/api/apps/${summary.id}`);if(!current())return;if(!csvUseApp(app))continue;
   [reply,dagInstances]=await Promise.all([api(`/api/internal/apps/${app.id}/instances`),api(`/api/internal/apps/${app.id}/dag-instances`)]);if(!current())return;
   if(dagInstances.items.length)dagReleases=await api(`/api/internal/apps/${app.id}/dag-releases`);
  }
  catch(error){if(!current())return;rows.push(row(`${summary.name} · 当前版本不可读取；请核对授权与来源。`));if(applicationUse?.appId===summary.id&&applicationUseCurrent(applicationUse))clearApplicationUseData(applicationUse);clearSavedDagUse(summary.id);continue;}
  if(!current())return;
  const sumOnly=app.candidate?.task_proof?.proof?.kind==='completed_ordinary_csv_report_sum_source.v1';
  for(const instance of reply.items){
   if(instance.project_id!==project||instance.source_app_id!==app.id)throw Error("VERSION_CONFLICT");
   const item=row(`${app.name} · CSV 单步汇总${sumOnly?' · 普通成功任务提取，仅求和、不含MD报告':''} · 未发布内部版本 · 结果版本 ${instance.data_version} · ${instance.id.slice(0,18)}`,async()=>{
    if(selectable())await openApplicationUse(app.id,instance.id);
   },"使用此本地实例");
   item.dataset.useFamily="CSV";item.dataset.appId=app.id;item.dataset.instanceId=instance.id;rows.push(item);
  }
  for(const instance of dagInstances.items){
   const release=dagReleases.items.find(v=>v.id===instance.release_id),version=release?.snapshot?.execution_source?.version,label=savedDagUseLabel(version);
   if(instance.project_id!==project||instance.source_app_id!==app.id||instance.runtime_id!==app.runtime_id)throw Error("VERSION_CONFLICT");
   if(!label){clearSavedDagUse(app.id);rows.push(row(`${app.name} · CSV DAG 实例 ${instance.id} · 当前图或版本不受此入口支持，请核查原来源。`));continue;}
   const item=row(`${app.name} · CSV DAG · ${label} · 固定授权材料与允许列 · 结果版本 ${instance.data_version} · ${instance.id} · 0 模型请求；内部未发布，语义 UNKNOWN，人工 PENDING。打开仅核查已有实例，不自动运行。`,async()=>{
    if(selectable())await openSavedDagUse(app.id,instance.id,selectable);
   },"使用此 CSV 流程实例");
   item.dataset.useFamily="CSV_DAG";item.dataset.appId=app.id;item.dataset.instanceId=instance.id;rows.push(item);
  }
 }
 if(current()){$("use-list").replaceChildren(...(rows.length?rows:[row("暂无可使用的保存实例。可点击上方“从 Goal 创建自然应用”，逐步确认候选、内部版本和实例；此处不会自动创建或授权。") ]));renderNaturalFirstGuide();}
}
function savedDagUseLabel(version){
 const labels={"internal.csv-read-sum.v1":"读取 → 求和","internal.csv-read-sum-report.v1":"读取 → 求和 → 报告","internal.csv-read-two-sums.v1":"读取 → 双求和","internal.project-csv-read-sum-report.v1":"项目固定读取 → 求和 → 报告"};
 return Object.hasOwn(labels,version)?labels[version]:null;
}
function clearSavedDagUse(appId=null){if(typeof csvDagContext!=="undefined"&&csvDagContext?.savedUse&&(!appId||csvDagContext.parent.id===appId))clearCsvDag();}
async function openSavedDagUse(appId,id,selectionCurrent=()=>true){
 const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration,project=$("project-select").value;
 let generation=null,c=null;
 const current=()=>selectionCurrent()&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration&&project===$("project-select").value&&(generation===null||generation===appSelectionGeneration);
 try{
  const opened=await showApp(appId,project,g=>{generation=g;},current,app=>{if(!csvUseApp(app))throw Error("VERSION_CONFLICT");});
  if(!opened||!current())return;
  c=csvDagContext;if(!c||!csvDagCurrent(c)||c.parent.id!==appId)throw Error("VERSION_CONFLICT");
  c.savedUse={current};
  await dagReuseHistory(c);if(!csvDagCurrent(c))return;
  const instance=c.reuse.instances.find(v=>v.id===id),release=c.reuse.releases.find(v=>v.id===instance?.release_id);
  if(!instance||!savedDagUseLabel(release?.snapshot?.execution_source?.version))throw Error("VERSION_CONFLICT");
  $("dag-reuse-instance").value=id;await dagReuseRead(c,id);
  if(!csvDagCurrent(c)||c.reuse.instance?.id!==id)return;
  $("internal-panel").hidden=true;$("app-preview-form").hidden=true;
  $("csv-dag-panel").scrollIntoView?.({block:"start"});
 }catch(error){if(current()){clearApp();throw error;}}
 finally{if(engineering?.selectionCurrent===current){if(current())engineering.selectionCurrent=null;else clearApp();}if(c?.savedUse&&c===csvDagContext&&!current())clearCsvDag();}
}
async function openSavedNaturalUse(appId,id,family,selectionCurrent=()=>true){
 return openSavedInternalUse(appId,id,family,selectionCurrent);
}
async function openSavedInternalUse(appId,id,family,selectionCurrent=()=>true){
 const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration,project=$("project-select").value;
 let generation=null,view=null;
 const current=()=>selectionCurrent()&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration&&project===$("project-select").value&&(generation===null||generation===appSelectionGeneration);
 try{
  const opened=await showApp(appId,project,g=>{generation=g;},current,app=>{
    const valid=family==="LITERAL_TEXT"?literalUseApp(app):family==="CLOSED_TEXT_WORKFLOW"?closedTextUseApp(app):naturalUseFamily(app)===family;
    if(!valid)throw Error("VERSION_CONFLICT");
  });
  if(!opened||!current())return;
  view=engineering;
  if(!view||!engineeringCurrent(view)||view.app!==appId)throw Error("VERSION_CONFLICT");
  if(id)await showInternalInstance(id,view);
  if(!current()||!engineeringCurrent(view)||(id&&view.instance?.id!==id))return;
  $("internal-title").textContent=family==="LITERAL_TEXT"?"使用已保存文本应用 · 字面检索":family==="CLOSED_TEXT_WORKFLOW"?"使用已保存文本应用 · 四步流程":`使用自然规范应用 · ${family==="NATURAL_PA"?"P-A":"P-B"}`;
  $(["LITERAL_TEXT","CLOSED_TEXT_WORKFLOW"].includes(family)?"internal-panel":"pb-use-panel")?.scrollIntoView?.({block:"start"});
 }catch(error){if(current())throw error;}
 finally{
  // The opening fence lasts through every chained read. Later explicit instance
  // selections use the original controller's own per-action navigation fences.
  if(engineering?.selectionCurrent===current){
   if(current())engineering.selectionCurrent=null;
   else clearApp();
  }
 }
}

function applicationUseButtons(v){
 if(!applicationUseCurrent(v))return;
 const pending=applicationUseRequests.get(applicationUseKey(v));
 const locked=pending&&["sending","unknown","accepted-read-error"].includes(pending.state);
 if(locked&&[...$("use-column").options].some(o=>o.value===pending.body.input.column))$("use-column").value=pending.body.input.column;
 $("use-submit").disabled=v.busy||locked||!$("use-column").value;
 $("use-column").disabled=v.busy||locked;
 $("use-recover").hidden=!pending||!["unknown","accepted-read-error"].includes(pending.state);
 $("use-recover").disabled=v.busy;
 $("use-recover").textContent=pending?.state==="unknown"?"恢复同一运行的接受回执":"重新读取已接受运行";
 $("use-refresh").disabled=v.busy;
}
async function openApplicationUse(appId,id){
 clearApp();clearApplicationUse();
 const v={id,appId,identity:token,project:$("project-select").value,generation:applicationUseGeneration,readGeneration:0,busy:false,instance:null,selected:null,historical:false};applicationUse=v;
 $("use-info").textContent="正在读取保存的版本与材料范围…";
 try{
  const app=await api(`/api/apps/${appId}`);if(!applicationUseCurrent(v))return;
  if(!csvUseApp(app)||app.project_id!==v.project)throw Error("UNSUPPORTED_CAPABILITY");
  v.app=app;
  const pending=applicationUseRequests.get(applicationUseKey(v));v.selected=pending?.runId||null;
  await readApplicationUse(v);
 }catch(error){if(applicationUseCurrent(v)){clearApplicationUseData(v);throw error;}}
}
function clearApplicationUseData(v){
 v.instance=null;
 $("use-csv-review-start")?.remove();
 for(const id of ["use-output","use-history","use-provenance","use-column","use-acceptance"])$(id).replaceChildren();
 $("use-form").hidden=true;$("use-refresh").hidden=false;
 $("use-info").textContent="当前版本或结果无法读取，请核对授权、来源和版本。读取失败不表示任务执行失败。";
 applicationUseButtons(v);
 if(v.selected&&typeof renderCsvOwnerReview==="function")renderCsvOwnerReview(v,null,null,true);
}
// Projection of authorized immutable evidence only. It cannot confirm or publish an app.
function renderApplicationAcceptance(v,release,run){
 const evidence=release.snapshot.check_evidence;
 const hash=value=>typeof value==="string"&&/^[a-f0-9]{64}$/.test(value);
 const checked=evidence?.ref==="csv.exact_integer_sum.v1"&&evidence.status==="PASS"&&
  evidence.candidate_fingerprint===v.app.fingerprint&&
  [evidence.input_fingerprint,evidence.output_fingerprint,evidence.plan_fingerprint].every(hash)&&
  release.snapshot.model_requests===0;
 const record=run&&v.instance.data.find(r=>r.instance_id===v.id&&r.run_id===run.app_run_id&&
  r.release_id===run.release_id&&r.version===run.result_version);
 const verified=run?.status==="SUCCEEDED"&&run.result&&record&&
  record.data.result.resource_id===run.result.resource_id&&record.data.result.column===run.result.column&&
  record.data.result.sum===run.result.sum&&record.data.result.count===run.result.count;
 const status=run&&["QUEUED","RUNNING","SUCCEEDED","FAILED","PARTIAL","UNKNOWN","PAUSED","CANCELLED"].includes(run.status)?run.status:"UNKNOWN";
 $("use-acceptance").replaceChildren(
  row(`固定版本样本工具检查：${checked?"PASS":"UNKNOWN"}。仅一个冻结样本的整数求和检查，不代表全部新输入或业务目标通过。`),
  row(run?`${v.historical?"所选历史":"本次"}技术执行：${status}；结果核对：${verified?`PASS · v${run.result_version}`:"尚无可核对的成功结果"}。`:"尚未选择运行；历史成功不作为本次验收。"),
  row(typeof renderCsvOwnerReview==="function"?"目标语义验收：NOT_RUN；本人适用范围声明见下方所选Run的独立读取；正式发布：关闭。内部版本批准不替代人工判断。":"目标语义验收：NOT_RUN；用户确认：PENDING；正式发布：关闭。内部版本批准不替代这些验收。"),
  row("适用范围：固定CSV材料，仅数值列参数可变；当前模型请求0。")
 );
}
function csvRunDownloadValue(instanceId,run,records){
 const result=run?.result;
 const record=records?.find(r=>r.instance_id===instanceId&&r.run_id===run.app_run_id&&r.release_id===run.release_id&&r.version===run.result_version);
 if(run?.status!=="SUCCEEDED"||run.instance_id!==instanceId||!Number.isSafeInteger(run.result_version)||run.result_version<1||
  !result||typeof result.resource_id!=="string"||typeof result.column!=="string"||typeof result.sum!=="string"||!Number.isSafeInteger(result.count)||result.count<0||
  !record||!["resource_id","column","sum","count"].every(key=>record.data?.result?.[key]===result[key]))return null;
 return {instance_id:instanceId,run_id:run.id,release_id:run.release_id,result_version:run.result_version,
  result:{resource_id:result.resource_id,column:result.column,sum:result.sum,count:result.count}};
}
function csvRunDownloadControl(v,run){
 const instance=v.instance,read=v.readGeneration,appRunId=run.app_run_id,expected=csvRunDownloadValue(v.id,run,instance.data);
 if(!expected)return;
 const node=document.createElement("div"),button=document.createElement("button"),status=document.createElement("p");
 button.type="button";button.textContent="下载此运行结果 JSON";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
 node.append(button,status);let downloading=false;
 const selected=()=>node.isConnected&&applicationUseCurrent(v)&&v.instance===instance&&v.readGeneration===read&&v.selected===expected.run_id;
 button.onclick=async()=>{
  if(downloading||v.busy||!selected())return;
  const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
  const key=JSON.stringify([connection,v.project,v.id,expected.run_id,expected.result_version]);
  if(applicationUseDownloads.has(key))return;
  const current=()=>selected()&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration;
  applicationUseDownloads.add(key);
  downloading=true;button.disabled=true;status.textContent="正在重新核对此运行的权限与结果…";
  try{
   const saved=await api(`/api/internal/instances/${encodeURIComponent(v.id)}/runs/${encodeURIComponent(expected.run_id)}`);
   if(!current())return;
   const value=csvRunDownloadValue(v.id,saved,saved.known_effects);
   if(saved.app_run_id!==appRunId||!value||JSON.stringify(value)!==JSON.stringify(expected))throw Error("VERSION_CONFLICT");
   const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+"\n"],{type:"application/json;charset=utf-8"}));
   const link=document.createElement("a");link.href=url;link.download=`sim2act-${v.id}-${expected.run_id}-v${expected.result_version}.json`;link.hidden=true;
   try{document.body.append(link);link.click();status.textContent=`已生成所选运行结果 v${value.result_version} 的 JSON 下载。`;}
   finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);}
  }catch(error){
   if(current()){
    if(error.httpStatus===403)clearApplicationUseData(v);
    else status.textContent=`结果读取未通过：${error.message}。未下载文件。`;
   }
  }finally{applicationUseDownloads.delete(key);downloading=false;button.disabled=false;}
 };
 return node;
}
async function readApplicationUse(v){
 const generation=++v.readGeneration,current=()=>applicationUseCurrent(v)&&generation===v.readGeneration;
 try{
  const instance=await api(`/api/internal/instances/${v.id}`);if(!current())return;
  if(instance.project_id!==v.project||instance.source_app_id!==v.appId||instance.id!==v.id||instance.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
  const release=await api(`/api/internal/releases/${instance.release_id}`);if(!current())return;
  const app=await api(`/api/apps/${v.appId}`);if(!current())return;
  if(!csvUseApp(app)||app.project_id!==v.project||release.project_id!==v.project||release.fingerprint!==instance.release_fingerprint||release.snapshot.draft.id!==v.appId||release.snapshot.draft.fingerprint!==app.fingerprint)throw Error("VERSION_CONFLICT");
  v.instance=instance;v.principal=instance.principal_id;v.app=app;
  const previous=$("use-column").value,pending=applicationUseRequests.get(applicationUseKey(v));
  $("use-column").replaceChildren(...app.input_guidance.columns.filter(c=>c.numeric).map(c=>new Option(c.name,c.name)));
  if([...$("use-column").options].some(o=>o.value===(pending?.state==="unknown"?pending.body.input.column:previous)))$("use-column").value=pending?.state==="unknown"?pending.body.input.column:previous;
  const material=release.snapshot.draft.candidate.manifest.data_bindings[0].resource_ref;
  $("use-info").textContent=`${app.name} · 未发布内部版本 · 固定材料 ${material} · 只读CSV求和；仅数值列可变，0模型请求，目标语义验收未执行。`;
  $("use-provenance").textContent=JSON.stringify({instance_id:v.id,release_id:instance.release_id,revision:instance.revision,release_fingerprint:instance.release_fingerprint,resource_id:material,source:app.candidate.task_proof||app.candidate.extraction||null},null,2);
  $("use-form").hidden=false;$("use-refresh").hidden=false;
  $("use-output").replaceChildren();
  const run=instance.runs.find(r=>r.id===v.selected);
  if(v.selected&&!run)throw Error("VERSION_CONFLICT: accepted run is not bound to this instance");
  if(run){
   if(run.instance_id!==v.id)throw Error("VERSION_CONFLICT");
   const label=v.historical?"已选择的历史运行":"本次运行";
   $("use-output").append(row(`${label} ${run.id} · ${run.status} · 结果版本 ${run.result_version??"尚无"}`));
   if(run.status==="SUCCEEDED"&&run.result){
    $("use-output").append(row(`${run.result.column} 合计 ${run.result.sum}，共 ${run.result.count} 条。工具结果已核验；目标语义验收未执行。`));
    const download=csvRunDownloadControl(v,run);if(download)$("use-output").append(download);
   }
   else $("use-output").append(row(run.error?.code?`本次没有可展示的新结果：${run.error.code}。` : "尚无本次新结果；下方历史成功不表示本次成功。"));
  }else $("use-output").append(row("本页尚未选择或发起运行；下方仅为持久历史，不是本次新结果。"));
  $("use-history").replaceChildren(...instance.runs.map(r=>row(`${r.id.slice(0,18)} · ${r.status} · 结果版本 ${r.result_version??"无"}`,async()=>{
   if(!applicationUseCurrent(v)||v.busy)return;v.selected=r.id;v.historical=true;await readApplicationUse(v);
  },"查看这次运行")),...instance.data.map(record=>row(`历史结果 v${record.version} · ${record.data.result.column} 合计 ${record.data.result.sum}，${record.data.result.count} 条 · ${record.release_id}`)));
  renderApplicationAcceptance(v,release,run);
  if(typeof renderCsvReviewStart==="function")renderCsvReviewStart(v,release);
  if(run&&typeof renderCsvOwnerReview==="function")renderCsvOwnerReview(v,run,release);
  applicationUseButtons(v);
 }catch(error){if(!current())return;clearApplicationUseData(v);throw error;}
}
async function submitApplicationUse(v,recover=false){
 if(!applicationUseCurrent(v)||v.busy)return;
 const key=applicationUseKey(v);let pending=applicationUseRequests.get(key);
 if(!recover){
  if(!v.instance||pending&&["sending","unknown","accepted-read-error"].includes(pending.state))return;
  const csvReview=$("use-csv-review-optin")?.checked&&typeof csvReviewStartScope==="function"&&v.csvReviewScope===csvReviewStartScope(v);
  pending={state:"new",body:{expected_revision:v.instance.revision,expected_release_fingerprint:v.instance.release_fingerprint,input:{column:$("use-column").value},request_key:crypto.randomUUID(),...(csvReview?{csv_review:"FREEZE_SUM_ONLY_WITHOUT_MD"}:{})},runId:null,uncertain:false};applicationUseRequests.set(key,pending);
 }
 if(!pending)return;
 if(!recover){$("use-acceptance").replaceChildren();v.selected=null;v.historical=false;$("use-output").replaceChildren(row("正在确认新运行的接受回执；下方历史结果不是本次新结果。"));}
 v.busy=true;applicationUseButtons(v);
 try{
  if(pending.state!=="accepted-read-error"){
   pending.state="sending";
   try{
    const reply=await api(`/api/internal/instances/${v.id}/runs`,"POST",pending.body);
    if(typeof reply.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(reply.run_id))throw Error("Invalid receipt");
    pending.runId=reply.run_id;pending.state="accepted-read-error";
   }catch(error){
    const rejected=!pending.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
    pending.state=rejected?"rejected":"unknown";if(!rejected)pending.uncertain=true;
    if(applicationUseCurrent(v)){$("use-output").replaceChildren(row(rejected?`提交被拒绝：${error.message}`:"接受回执未确认；输入已冻结。显式恢复使用原请求键，不会另建运行。"));if(error.httpStatus===403)clearApplicationUseData(v);}
    return;
   }
  }
  if(!applicationUseCurrent(v))return;
  v.selected=pending.runId;v.historical=false;
  await readApplicationUse(v);if(applicationUseCurrent(v))pending.state="accepted";
 }finally{
  v.busy=false;applicationUseButtons(v);
  const live=applicationUse;
  if(live!==v&&applicationUseCurrent(live)&&applicationUseKey(live)===key&&applicationUseRequests.get(key)===pending){
   applicationUseButtons(live);
   if(["unknown","accepted-read-error"].includes(pending.state))$("use-output").replaceChildren(row(pending.state==="unknown"?"原运行接受回执未确认；请恢复同一运行，不能另建重复任务。":"原运行已接受；请重新读取该持久运行，不会再次提交。"));
  }
 }
}
$("use-form").onsubmit=safe(()=>submitApplicationUse(applicationUse));
$("use-recover").onclick=safe(()=>submitApplicationUse(applicationUse,true));
$("use-refresh").onclick=safe(async()=>{const v=applicationUse;if(v&&applicationUseCurrent(v)&&!v.busy)await readApplicationUse(v);});

// Explicit source selection only; no cached claims survive a context change or cold page.
let conditionalContext=null,conditionalGeneration=0;
function clearConditionalChecks(clearList=false){
 conditionalGeneration++;conditionalContext=null;
 if(typeof clearConditionalRuns==="function")clearConditionalRuns();
 $("condition-form").hidden=true;$("condition-recheck").hidden=true;
 $("condition-source").replaceChildren();$("condition-results").replaceChildren();
 $("condition-status").textContent="旧证据已清除。请显式打开当前授权资料。";
 $("condition-form").reset();$("condition-submit").disabled=false;
 if(clearList)$("condition-resource").replaceChildren(new Option("请选择", ""));
}
function conditionCurrent(c){return conditionalContext===c&&c.identity===token&&c.project===$("project-select").value&&c.generation===conditionalGeneration;}
async function listConditionalSources(){
 clearConditionalChecks(true);
 const c={identity:token,project:$("project-select").value,generation:conditionalGeneration};conditionalContext=c;
 try{
  const items=await api(`/api/projects/${c.project}/resources`);if(!conditionCurrent(c))return;
  $("condition-resource").replaceChildren(new Option("请选择", ""),...items.filter(r=>["txt","md"].includes(r.format)).map(r=>new Option(`${r.name} · 内容版本 ${r.hash.slice(0,12)}`,r.id)));
  $("condition-status").textContent="仅列出当前授权文本资料；选择后再读取。仅支持 A-S 固定资料，其他内容将拒绝。";
 }catch(error){if(conditionCurrent(c)){clearConditionalChecks(true);$("condition-status").textContent=`资料列表不可读：${error.message}；旧证据失效。`;}}
}
async function openConditionalSource(){
 const rid=$("condition-resource").value;if(!rid)return;
 clearConditionalChecks();
 const c={identity:token,project:$("project-select").value,generation:conditionalGeneration,rid};conditionalContext=c;
 $("condition-status").textContent="正在核对授权与实际内容版本…";
 try{
  const source=await api(`/api/projects/${c.project}/conditional-checks/sources/${rid}`);if(!conditionCurrent(c))return;
  if(source.resource_id!==rid||source.contract.source_hash!==source.hash)throw Error("VERSION_CONFLICT");
  c.source=source;
  if(typeof showConditionalRuns==="function")showConditionalRuns(source);
  $("condition-source").replaceChildren(row(`资料 ${rid} · 内容 SHA256 ${source.hash} · 注册规则 ${source.contract.id} v${source.contract.version} · 合同 ${source.contract.fingerprint}`),...source.rules.map(r=>row(`${r.rule_id} · 第${r.line}行：${r.quote}`)));
  $("condition-form").hidden=false;
  $("condition-status").textContent="资料版本已核查。填写假设事实及人工报告；检查不确认真实事实。";
 }catch(error){if(conditionCurrent(c)){clearConditionalChecks();$("condition-status").textContent=`资料不支持、已变化或权限不足：${error.message}；旧证据失效。`;}}
}
function conditionBody(c){
 const bool=id=>$("condition-"+id).value===""?null:$("condition-"+id).value==="true";
 const number=id=>$("condition-"+id).value===""?null:Number($("condition-"+id).value);
 return {resource_id:c.rid,expected_source_hash:c.source.hash,expected_contract_fingerprint:c.source.contract.fingerprint,
  scenario:{kind:"HYPOTHETICAL_EMPLOYEE",trip_ended:bool("trip"),amount:number("amount"),receipt_present:bool("receipt"),approved:bool("approved"),elapsed_days:number("days")},
  report:{findings:c.source.rules.map(r=>({rule_id:r.rule_id,applies:$("condition-"+r.rule_id).value,citation:{line:r.line,quote:r.quote}})),decision:$("condition-decision").value,next_actions:[...$("condition-actions").selectedOptions].map(o=>o.value),deadline_days:number("deadline"),absolute_date:$("condition-date").value,receipt_restarts_deadline:bool("restart"),explanation:$("condition-explanation").value}};
}
async function runConditionalCheck(recheck=false){
 const c=conditionalContext;if(!c?.source||!conditionCurrent(c)||c.busy)return;
 const body=recheck?c.body:conditionBody(c);if(!body)return;
 const read=(c.readGeneration||0)+1;c.readGeneration=read;
 const current=()=>conditionCurrent(c)&&c.readGeneration===read;
 c.busy=true;$("condition-submit").disabled=true;$("condition-results").replaceChildren();$("condition-recheck").hidden=true;
 $("condition-status").textContent="正在重新授权读取资料并核对；此前证据不作为当前结果。";
 try{
  const result=await api(`/api/projects/${c.project}/conditional-checks`,"POST",body);if(!current())return;
  if(result.source.resource_id!==c.rid||result.source.hash!==body.expected_source_hash||result.contract_fingerprint!==body.expected_contract_fingerprint)throw Error("VERSION_CONFLICT");
  c.body=body;
  const names={SATISFIED:"满足",UNSATISFIED:"不满足",UNKNOWN:"未知",NOT_APPLICABLE:"不适用"};
  $("condition-results").replaceChildren(row(`结构化报告核对 ${result.check_status} · 注册规则决策 ${result.decision}；PASS 不表示可以提交或用户已确认。`),...result.rule_results.map(r=>row(`${r.rule_id}：${names[r.satisfaction]} · ${r.reason} 引用资料 ${result.source.resource_id} 内容版本 ${result.source.hash} 第${r.citation.line}行：${r.citation.quote}`)),...result.checks.map(r=>row(`${r.id}：${r.status}`)),row(`语义 ${result.semantic_status}；用户确认 ${result.owner_acceptance}；自由说明 ${result.explanation_status}；正式发布关闭。仅本页证据，刷新/冷会话需重新核对。`));
  $("condition-status").textContent="核对完成；真实事实与开放语言解释未验收。";$("condition-recheck").hidden=false;
 }catch(error){if(current()){
  c.body=null;c.source=null;$("condition-source").replaceChildren();$("condition-form").hidden=true;
  $("condition-status").textContent=`核对未完成，旧证据失效：${error.message}。资料变化/撤权需重新选择；请求失败不等于业务条件不满足。`;
 }}finally{c.busy=false;if(conditionCurrent(c))$("condition-submit").disabled=false;}
}
$("condition-list").onclick=safe(listConditionalSources);
$("condition-open").onclick=safe(openConditionalSource);
$("condition-resource").onchange=()=>clearConditionalChecks();
$("condition-form").onsubmit=safe(()=>runConditionalCheck());
$("condition-recheck").onclick=safe(()=>runConditionalCheck(true));
$("condition-form").oninput=()=>{if(conditionalContext){conditionalContext.readGeneration=(conditionalContext.readGeneration||0)+1;conditionalContext.body=null;}$("condition-results").replaceChildren();$("condition-recheck").hidden=true;$("condition-status").textContent="输入已变化，旧证据失效；请重新核对。";};

function invalidateConditionalSource(reason){
 if(typeof clearConditionalRuns==="function"){clearConditionalRuns();$("condition-run-status").textContent=`旧来源绑定证据失效：${reason}。请重新打开当前授权资料；已接受Run未取消，同键回执仍保留。`;}
 if(!conditionalContext?.source)return;
 clearConditionalChecks();$("condition-status").textContent=`旧证据失效：${reason}。请重新选择并核对授权资料。`;
}
function reconcileConditionalSources(items){
 if(typeof reconcileBoundedSources==="function")reconcileBoundedSources(items);
 const c=conditionalContext;if(!c?.source||!conditionCurrent(c))return;
 const item=items.find(r=>r.id===c.rid);
 if(!item||item.hash!==c.source.hash||!["txt","md"].includes(item.format))invalidateConditionalSource("资料版本变化或授权撤销");
}
