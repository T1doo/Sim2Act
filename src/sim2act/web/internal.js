"use strict";
// Each view and request carries its own identity/selection generation; no browser execution.
let engineering = null, engineeringGeneration = 0;
const engineeringPending = new Map();
const engineeringInstanceKeys = new Map();
const registeredExtractionRequests = new Map();
let registeredExtraction = null, registeredExtractionGeneration = 0;
let registeredExtractionEditGeneration = 0;
for(const id of ["registered-extraction-target","registered-extraction-name"]){
  $(id).addEventListener("input",()=>{registeredExtractionEditGeneration++;});
  $(id).addEventListener("change",()=>{registeredExtractionEditGeneration++;});
}
function engineeringCurrent(view) {
  return engineering === view && view.token === token && view.project === $("project-select").value && view.app === activeApp && view.appGeneration === appSelectionGeneration;
}
function engineeringStatus(view,text,state="") {
  if(!engineeringCurrent(view))return;
  $("internal-status").textContent=text;$("internal-status").dataset.state=state;
}
function clearInternal() {
  if(typeof clearOwnerReview==="function")clearOwnerReview();
  clearRegisteredExtraction();
  if(engineering)clearSwitch(engineering);
  $("internal-switch").hidden=true;$("internal-switch-history").replaceChildren();
  engineeringGeneration++;engineering=null;
  $("internal-panel").hidden=true;$("internal-approval").hidden=true;$("internal-approval-detail").textContent="";$("internal-approval-ack").checked=false;
  $("internal-status").textContent="";$("internal-agent").hidden=true;$("internal-replay-file").value="";$("internal-replay-status").textContent="";$("internal-term").value="";
  for(const id of ["internal-releases","internal-instances","internal-runs","internal-data","internal-controls"] )$(id).replaceChildren();
  $("internal-run-form").hidden=true;$("internal-retry").hidden=true;$("internal-new-intent").hidden=true;$("internal-run-detail").textContent="";$("internal-run-status").textContent="";$("internal-instance-info").textContent="";
}
function engineeringButtons(view) {
  if(!engineeringCurrent(view))return;
  const switchExpired=view.switchApproval && view.switchApproval.expires_at*1000<=Date.now();
  $("internal-switch-prepare").disabled=!!view.busy || !view.instance || !$("internal-switch-target").value;
  $("internal-switch-target").disabled=!!view.busy;
  $("internal-switch-commit").disabled=!!view.busy || !view.instance || !view.switchApproval || switchExpired || !$("internal-switch-ack").checked;
  if(switchExpired)$("internal-switch-status").textContent="批准已到期，请重新核查；不会自动重发确认。";
  const missingReplay=view.agent && (!view.offlineReplay || !$("app-agent-term").value.trim());
  const approvalExpired=view.approval && view.approval.expires_at*1000<=Date.now();
  $("internal-prepare").disabled=!!view.busy || missingReplay;
  $("internal-refresh").disabled=!!view.busy;
  $("internal-commit").disabled=!!view.busy || !view.approval || approvalExpired || !$("internal-approval-ack").checked;
  if(approvalExpired)engineeringStatus(view,"批准已到期，请重新核查；不会自动确认。","error");
  $("internal-run-submit").disabled=!!view.busy || !view.instance || engineeringPending.has(view.instance.id) || (view.agent && (!view.offlineReplay || !$("internal-term").value.trim()));
  $("internal-retry").hidden=!view.instance || !engineeringPending.has(view.instance.id);
  $("internal-retry").disabled=!!view.busy;
  $("internal-new-intent").hidden=$("internal-retry").hidden;$("internal-new-intent").disabled=!!view.busy;
}
async function engineeringAction(view,fn) {
  if(!view || !engineeringCurrent(view) || view.busy)return;
  const selection=view.instanceGeneration;
  view.busy=true;engineeringButtons(view);
  try {await fn();}
  catch(error){if(engineeringCurrent(view) && selection===view.instanceGeneration){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");}}
  finally {view.busy=false;engineeringButtons(view);}
}
async function openInternal(app,appGeneration) {
  const view={app:app.id,project:app.project_id,token,appGeneration,generation:++engineeringGeneration,draft:app,busy:false,approval:null,instance:null,run:null,instanceGeneration:0,runGeneration:0,releases:[],switchGeneration:0,switchApproval:null,agent:app.input_guidance.mode === "OFFLINE_REPLAY_ONLY",literal:app.input_guidance.mode === "REGISTERED_LITERAL",offlineReplay:null,inputGeneration:0,workflow:app.input_guidance.mode === "CLOSED_TEXT_WORKFLOW"};
  engineering=view;$("apps").append($("internal-panel"));$("internal-panel").hidden=false;
  $("internal-agent").hidden=!view.agent;
  $("internal-replay-status").textContent=view.agent ? "尚未加载离线响应；审批与新运行暂不可提交。" : "";
  $("internal-prepare-hint").textContent=view.agent ? "使用上方样例字面检索词与已加载的离线响应核查当前材料。先查看精确快照，再手动确认保存内部版本；语义仍为 UNKNOWN。" : "使用当前选定数值列重新核查固定可信计算；先查看精确快照，再确认保存。仅内部版本，不是正式发布。";
  if(view.literal)$("internal-prepare-hint").textContent="用上方检索词独立核查完整匹配行；精确确认后保存内部版本。新实例直接输入新词，无需 Replay。语义 UNKNOWN。";
  if(view.workflow){$("internal-prepare-hint").textContent="用两次独立检索和报告分支核查完整引用，再确认精确内部快照。后台每步独立留存回执；owner PENDING、语义 UNKNOWN。";}
  engineeringButtons(view);engineeringStatus(view,"正在读取内部版本与实例…","loading");
  if(typeof openAppOwnGoal === "function")await openAppOwnGoal(view);
  try {await refreshInternal(view);}
  catch(error){if(engineeringCurrent(view)){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");$("internal-releases").replaceChildren();$("internal-instances").replaceChildren();}}
}
async function refreshInternal(view=engineering) {
  if(!view || !engineeringCurrent(view))return;
  const latest=await api(`/api/apps/${view.app}`);
  if(!engineeringCurrent(view))return;
  if(latest.project_id!==view.project || latest.fingerprint!==view.draft.fingerprint)throw Error("VERSION_CONFLICT");
  const [releases,instances]=await Promise.all([api(`/api/internal/apps/${view.app}/releases`),api(`/api/internal/apps/${view.app}/instances`)]);
  if(!engineeringCurrent(view))return;
  view.releases=releases.items;
  $("internal-releases").replaceChildren(...releases.items.map(release=>row(`内部 Release ${release.id} · 指纹 ${release.fingerprint.slice(0,16)} · 正式发布关闭`,()=>engineeringAction(view,async()=>{
    const selection=view.instanceGeneration;
    let key=engineeringInstanceKeys.get(release.id);if(!key){key=crypto.randomUUID();engineeringInstanceKeys.set(release.id,key);}
    engineeringStatus(view,"正在创建独立内部实例…","loading");
    const created=await api(`/api/internal/releases/${release.id}/instances`,"POST",{expected_release_fingerprint:release.fingerprint,request_key:key});
    // Keep key if receipt delivery/readback fails; repeating the intent cannot duplicate instance.
    if(!engineeringCurrent(view) || selection!==view.instanceGeneration)return;
    await refreshInternal(view);
    if(!engineeringCurrent(view) || selection!==view.instanceGeneration)return;
    await showInternalInstance(created.id,view);
    if(engineeringCurrent(view) && view.instance?.id===created.id){engineeringInstanceKeys.delete(release.id);engineeringStatus(view,"已创建独立内部实例；结果和后台状态可重新读取。");}
  }),"创建独立实例")));
  $("internal-instances").replaceChildren(...instances.items.map(instance=>row(`${instance.id} · 版本 ${instance.revision} · 结果版本 ${instance.data_version}`,()=>showInternalInstance(instance.id,view),"打开 / 重开")));
  if(!releases.items.length)$("internal-releases").textContent="尚无内部 Release。先核查并查看精确快照。";
  if(!instances.items.length)$("internal-instances").textContent="尚无实例。内部 Release 已保存后可创建。";
  engineeringStatus(view,"内部历史已读回；正式发布与部署仍关闭。");
}
async function showInternalInstance(id,view=engineering) {
  if(!view || !engineeringCurrent(view))return;
  if(typeof clearOwnerReview==="function")clearOwnerReview();
  clearRegisteredExtraction();
  clearSwitch(view);$("internal-switch").hidden=true;
  const selection=++view.instanceGeneration;view.runGeneration++;view.instance=null;view.run=null;
  $("internal-run-form").hidden=true;$("internal-controls").replaceChildren();$("internal-run-detail").textContent="";$("internal-run-status").textContent="正在读取实例…";$("internal-data").replaceChildren();$("internal-runs").replaceChildren();engineeringButtons(view);
  try {
    const instance=await api(`/api/internal/instances/${id}`);
    if(!engineeringCurrent(view) || selection!==view.instanceGeneration)return;
    if(instance.source_app_id!==view.app || instance.project_id!==view.project)throw Error("实例来源与当前选择不符");
    view.instance=instance;renderSwitch(view);$("internal-instance-title").textContent=`内部实例 ${id}`;
    $("internal-instance-info").textContent=`Release ${instance.release_id} · revision ${instance.revision} · 独立结果版本 ${instance.data_version} · 正式部署关闭`;
    $("internal-column-label").hidden=view.agent||view.literal||view.workflow;$("internal-column").required=!(view.agent||view.literal||view.workflow);$("internal-term-label").hidden=!(view.agent||view.literal);$("internal-term").required=view.agent||view.literal;
    $("internal-column").replaceChildren(...Array.from($("app-column").options).map(o=>{const option=new Option(o.textContent,o.value);option.disabled=o.disabled;return option;}));
    if(typeof showTextWorkflowInputs === "function")showTextWorkflowInputs("internal",!!view.workflow);
    $("internal-run-form").hidden=false;
    $("internal-data").replaceChildren(...instance.data.map(record=>internalResult(record,view)));
    $("internal-runs").replaceChildren(...instance.runs.map(run=>row(`${run.status} · ${run.id} · 结果版本 ${run.result_version ?? "无"}`,()=>showInternalRun(run.id,view,instance),"读取后台任务")));
    $("internal-run-status").textContent=engineeringPending.has(id) ? "上次提交回执未确认，可用原请求键恢复；不会自动重发。" : (view.agent ? "加载对应离线响应并填写本次检索词；后台核查真实授权材料，不调用provider。关闭页面不会取消任务。" : "选择数值列，提交后台只读计算；关闭页面不会取消已接受任务。");
    if(view.workflow)$("internal-run-status").textContent="填写两次独立检索词，明确选择报告分支。报告未选时保留 PARTIAL 与三步回执；只用原请求 key 读取未知结果。";
    if(view.literal)$("internal-run-status").textContent="输入本次检索词，后台重新读取并独立核查全部匹配行；关闭页面不会取消任务。";
    if(typeof openOwnerReview==="function")await openOwnerReview(view);
  } catch(error){if(engineeringCurrent(view) && selection===view.instanceGeneration){invalidateInternalContent(view);$("internal-instance-info").textContent="";$("internal-run-status").textContent=error.message;engineeringStatus(view,error.message,"error");}}
  engineeringButtons(view);
}
async function showInternalRun(id,view=engineering,instance=view?.instance) {
  if(!instance || !engineeringCurrent(view) || view.instance?.id!==instance.id)return;
  const previousStatus=view.run?.status;
  const selection=++view.runGeneration,iSelection=view.instanceGeneration;
  $("internal-controls").replaceChildren();$("internal-run-detail").textContent="";view.run=null;
  const current=()=>engineeringCurrent(view) && selection===view.runGeneration && iSelection===view.instanceGeneration && view.instance?.id===instance.id;
  try {
    let run;
    try {run=await api(`/api/internal/instances/${instance.id}/runs/${id}`);}
    catch(error){
      if(!current())return;
      if(!["GRANT_REVOKED","PERMISSION_DENIED"].includes(error.message))throw error;
      run=await api(`/api/internal/instances/${instance.id}/runs/${id}/control-status`);
      if(!current())return;
      clearSwitch(view);$("internal-switch").hidden=true;
      $("internal-run-form").hidden=true;$("internal-retry").hidden=true;$("internal-new-intent").hidden=true;$("internal-data").replaceChildren();$("internal-runs").replaceChildren();
      engineeringStatus(view,"当前权限不允许读取内容；仅显示 owner 停止控制状态，不恢复授权。","error");
    }
    if(!current())return;
    if(run.instance_id!==instance.id)throw Error("运行绑定与实例不符");
    renderRegisteredExtraction(view,instance,run);
    view.run=run;$("internal-run-status").textContent=`${run.status} · 取消意图 ${run.cancel_intent ? "已保留" : "无"} · ${run.result ? JSON.stringify(run.result) : run.error?.code || "等待后台状态"}`;
    $("internal-run-detail").textContent=JSON.stringify(run,null,2);
    const commands=["QUEUED","RUNNING"].includes(run.status)?["pause","cancel"]:["PAUSED","WAITING_RESOURCE"].includes(run.status)&&!run.cancel_intent?(run.content_access===false?["cancel"]:["resume","cancel"]):["PAUSE_REQUESTED","RECONCILING"].includes(run.status)?["cancel"]:[];
    $("internal-controls").replaceChildren(...commands.map(command=>{
      const button=document.createElement("button");button.textContent={pause:"暂停",cancel:"取消后台任务",resume:"继续"}[command];
      button.onclick=()=>engineeringAction(view,async()=>{
        if(!current())return;
        const response=await api(`/api/internal/instances/${instance.id}/runs/${id}/commands`,"POST",{command,version:run.version});
        if(!current())return;
        // The accepted stop receipt remains visible even if current grants prevent GET afterward.
        $("internal-run-status").textContent=`已接受${button.textContent}：${response.status}`;$("internal-controls").replaceChildren();view.run=null;
        try {await showInternalRun(id,view,instance);}catch(error){engineeringStatus(view,error.message,"error");}
      });return button;
    }));
    if(run.content_access!==false && previousStatus && previousStatus!==run.status && ["SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(run.status)){
      await showInternalInstance(instance.id,view);
      if(engineeringCurrent(view) && view.instance?.id===instance.id)await showInternalRun(id,view,view.instance);
    }
  } catch(error){if(current()){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");$("internal-run-status").textContent+=" · 无法读取当前详情";}}
}
async function submitInternal(view,retry=false) {
  const instance=view.instance;if(!instance)return;
  let pending=engineeringPending.get(instance.id);
  if(!pending && !retry){pending={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,input:view.workflow ? textWorkflowInput("internal") : (view.agent||view.literal) ? {term:$("internal-term").value} : {column:$("internal-column").value},...(view.agent ? {offline_replay:structuredClone(view.offlineReplay)} : {}),...(appOwnGoalCurrent(appOwnGoalView)&&appOwnGoalView.state?.current ? {expected_owner_goal_binding_fingerprint:appOwnGoalView.state.current.binding_fingerprint} : {}),request_key:crypto.randomUUID()};engineeringPending.set(instance.id,pending);}
  if(!pending)return;
  const requestKey=pending.request_key;
  const generation=view.instanceGeneration;
  $("internal-run-status").textContent="正在提交持久任务…";
  const accepted=view.workflow && retry ? await api(`/api/internal/instances/${instance.id}/text-workflow-run-requests/${encodeURIComponent(pending.request_key)}`) : await api(`/api/internal/instances/${instance.id}/runs`,"POST",pending);
  if(view.workflow && retry){accepted.run_id=accepted.id;}
  if(engineeringPending.get(instance.id)===pending && pending.request_key===requestKey)engineeringPending.delete(instance.id);
  if(!engineeringCurrent(view) || generation!==view.instanceGeneration)return;
  $("internal-run-status").textContent=`已接受 ${accepted.run_id}，关闭页面不取消。`;
  await showInternalInstance(instance.id,view);
  if(engineeringCurrent(view) && view.instance?.id===instance.id)await showInternalRun(accepted.run_id,view,view.instance);
}
$("internal-prepare").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering;view.approval=null;$("internal-approval").hidden=true;$("internal-approval-ack").checked=false;
  const inputGeneration=view.inputGeneration;
  const current=()=>engineeringCurrent(view) && inputGeneration===view.inputGeneration;
  const sample=view.workflow ? {...textWorkflowInput("app"),emit_report:true} : (view.agent||view.literal) ? {term:$("app-agent-term").value} : {column:$("app-column").value};
  const prepared=await api(`/api/internal/apps/${view.app}/release-approvals`,"POST",{expected_draft_fingerprint:view.draft.fingerprint,sample_input:sample,...(view.agent ? {offline_replay:structuredClone(view.offlineReplay)} : {})});
  if(!current())return;
  const detail=await api(`/api/internal/approvals/${prepared.id}`);
  if(!current())return;
  if(detail.fingerprint!==prepared.fingerprint)throw Error("批准指纹不一致");
  view.approval=detail;$("internal-approval").hidden=false;$("internal-approval-label").textContent=`内部批准 ${detail.id} · 到期 ${new Date(detail.expires_at*1000).toLocaleString()} · ${detail.fingerprint}`;
  $("internal-approval-detail").textContent=JSON.stringify(detail.payload,null,2);engineeringStatus(view,"请检查精确冻结快照，勾选确认后保存内部 Release。");
});
$("internal-approval-ack").onchange=()=>{if(engineering)engineeringButtons(engineering);};
$("internal-commit").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,approval=view.approval;if(!approval || approval.expires_at*1000<=Date.now() || !$("internal-approval-ack").checked)return;
  const saved=await api(`/api/internal/approvals/${approval.id}/commit`,"POST",{fingerprint:approval.fingerprint});
  if(!engineeringCurrent(view))return;
  view.approval=null;$("internal-approval").hidden=true;$("internal-approval-ack").checked=false;await refreshInternal(view);engineeringStatus(view,`已保存内部 Release ${saved.id}；正式发布关闭。`);
});
$("internal-refresh").onclick=()=>engineeringAction(engineering,async()=>{const view=engineering,id=view.instance?.id,selection=view.instanceGeneration;await refreshInternal(view);if(id && engineeringCurrent(view) && selection===view.instanceGeneration)await showInternalInstance(id,view);});
$("internal-back").onclick=()=>{clearInternal();};
$("internal-run-form").onsubmit=event=>{event.preventDefault();const view=engineering;return engineeringAction(view,()=>submitInternal(view));};
$("internal-new-intent").onclick=()=>{const view=engineering,id=view?.instance?.id;return engineeringAction(view,async()=>{
  if(!id)return;await showInternalInstance(id,view);
  if(!engineeringCurrent(view) || view.instance?.id!==id)return;
  engineeringPending.delete(id);$("internal-run-status").textContent="已读回当前历史并结束本页旧请求重试；不取消任何已接受后台任务。下一次提交是新运行。";
});};
$("internal-retry").onclick=()=>{const view=engineering;return engineeringAction(view,()=>submitInternal(view,true));};
setInterval(async()=>{
 const view=engineering;if(!view || !engineeringCurrent(view))return;engineeringButtons(view);if(view.busy || !view.run || !view.instance)return;
 if(!["SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(view.run.status))await showInternalRun(view.run.id,view,view.instance);
},2500);

function clearSwitch(view) {
  view.switchGeneration++;view.switchApproval=null;
  $("internal-switch-approval").hidden=true;$("internal-switch-ack").checked=false;
  $("internal-switch-detail").textContent="";$("internal-switch-summary").textContent="";
  $("internal-switch-status").textContent="";$("internal-switch-target").value="";
}
function renderSwitch(view) {
  $("internal-switch").hidden=false;
  $("internal-switch-target").replaceChildren(new Option("请手动选择目标版本",""),...view.releases.filter(r=>r.id!==view.instance.release_id).map(r=>new Option(`${r.id} · schema v${r.snapshot.data_schema_version} · ${r.fingerprint.slice(0,16)}`,r.id)));
  $("internal-switch-history").replaceChildren(...view.instance.history.map(h=>row(`revision ${h.revision} · ${h.previous_release_id || "初始版本"} → ${h.release_id} · ${h.kind || "create"}`)));
}
$("internal-switch-target").onchange=()=>{const view=engineering;if(!view)return;const value=$("internal-switch-target").value;clearSwitch(view);$("internal-switch-target").value=value;engineeringButtons(view);};
$("internal-switch-ack").onchange=()=>{if(engineering)engineeringButtons(engineering);};
$("internal-switch-cancel").onclick=()=>{const view=engineering;if(!view)return;clearSwitch(view);$("internal-switch-status").textContent="已取消本页选择；已被服务接受的切换仍可能完成，请重新读取历史确认。";engineeringButtons(view);};
$("internal-switch-prepare").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,instance=view.instance,target=view.releases.find(r=>r.id===$("internal-switch-target").value);
  if(!instance || !target)return;
  clearSwitch(view);$("internal-switch-target").value=target.id;
  const generation=view.switchGeneration,selection=view.instanceGeneration;
  const current=()=>engineeringCurrent(view) && selection===view.instanceGeneration && generation===view.switchGeneration && view.instance?.id===instance.id;
  $("internal-switch-status").textContent="正在检查兼容性、当前权限和保留数据…";
  try {
    const prepared=await api(`/api/internal/instances/${instance.id}/switch-approvals`,"POST",{target_release_id:target.id,expected_target_fingerprint:target.fingerprint,expected_revision:instance.revision});
    if(!current())return;
    const detail=await api(`/api/internal/instances/${instance.id}/switch-approvals/${prepared.id}`);
    if(!current())return;
    if(detail.fingerprint!==prepared.fingerprint || detail.payload.instance_id!==instance.id || detail.payload.target_release_id!==target.id || detail.payload.target_fingerprint!==target.fingerprint)throw Error("切换批准绑定不一致");
    view.switchApproval=detail;$("internal-switch-approval").hidden=false;
    $("internal-switch-summary").textContent=`${detail.payload.from_release_id} → ${detail.payload.target_release_id} · revision ${detail.payload.revision} → ${detail.payload.revision+1} · schema ${detail.from_schema_version} → ${detail.target_schema_version} · 保留 ${detail.retained_records} 条结果，结果版本 ${detail.payload.data_version} 不变 · 不新增授权 · 到期 ${new Date(detail.expires_at*1000).toLocaleString()}`;
    $("internal-switch-detail").textContent=JSON.stringify(detail,null,2);$("internal-switch-status").textContent="兼容性检查通过。请核对目标版本并手动确认。";
  } catch(error){if(current())$("internal-switch-status").textContent=`核查拒绝：${error.detail || error.message}`;}
});
$("internal-switch-commit").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,instance=view.instance,approval=view.switchApproval;
  if(!instance || !approval || !$("internal-switch-ack").checked || approval.expires_at*1000<=Date.now())return;
  const generation=view.switchGeneration,selection=view.instanceGeneration;
  const current=()=>engineeringCurrent(view) && selection===view.instanceGeneration && generation===view.switchGeneration && view.instance?.id===instance.id;
  // A consumed approval is never retried. Lost response must be resolved by history readback.
  view.switchApproval=null;$("internal-switch-ack").checked=false;$("internal-switch-approval").hidden=true;engineeringButtons(view);
  try {
    const saved=await api(`/api/internal/instances/${instance.id}/switch-approvals/${approval.id}/commit`,"POST",{fingerprint:approval.fingerprint});
    if(!current())return;
    await showInternalInstance(instance.id,view);
    if(engineeringCurrent(view) && view.instance?.id===instance.id)$("internal-switch-status").textContent=`已切换至 ${saved.release_id}，revision ${saved.revision}；数据与历史保留。`;
  } catch(error){if(current())$("internal-switch-status").textContent=`确认结果待核对：${error.detail || error.message}。请重新读取历史；不自动重发批准。`;}
});
setInterval(()=>{if(engineering?.switchApproval)engineeringButtons(engineering);},500);


function clearReleaseApproval(view) {
  view.inputGeneration++;view.approval=null;
  $("internal-approval").hidden=true;$("internal-approval-ack").checked=false;
  $("internal-approval-detail").textContent="";$("internal-approval-label").textContent="";
}
function invalidateInternalContent(view) {
  if(typeof clearOwnerReview==="function")clearOwnerReview();
  clearRegisteredExtraction();
  clearReleaseApproval(view);clearSwitch(view);
  view.instanceGeneration++;view.runGeneration++;view.instance=null;view.run=null;view.offlineReplay=null;
  $("internal-replay-file").value="";$("internal-replay-status").textContent="当前内容不可访问，请重新打开候选核查授权与来源。";
  for(const id of ["internal-data","internal-runs","internal-releases","internal-instances","internal-controls"])$(id).replaceChildren();
  $("internal-run-detail").textContent="";$("internal-instance-info").textContent="";
  $("internal-run-form").hidden=true;$("internal-switch").hidden=true;
  $("app-frozen-goal-text").textContent="";$("app-frozen-goal").hidden=true;$("app-manifest").textContent="";
}
function internalResult(record,view) {
  if(!view.agent&&!view.literal)return row(`结果 v${record.version} · ${record.release_id} · ${JSON.stringify(record.data.result)}`);
  const value=record.data.result,node=document.createElement("article");node.className="agent-result";
  const title=document.createElement("p");title.textContent=`历史结果 v${record.version} · ${record.release_id} · ${view.literal ? "确定性文本工具" : "离线 Replay"} · 字面检查 PASS · 语义 ${value.semantic_status}`;
  const scope=document.createElement("p");scope.textContent=`检索词：${value.term} · 材料 ${value.resource_id} · revision ${value.revision} · hash ${value.source_hash}`;
  const quotes=document.createElement("ul");
  for(const cite of value.citations){const line=document.createElement("li"),label=document.createElement("span"),quote=document.createElement("blockquote");label.textContent=`第 ${cite.start_line}—${cite.end_line} 行`;quote.textContent=cite.quote;line.append(label,quote);quotes.append(line);}
  if(!value.citations.length)quotes.textContent="无字面命中；不代表语义不存在。";
  node.append(title,scope,quotes);return node;
}
function changeAgentInput() {
  const view=engineering;if(!view || !engineeringCurrent(view) || !(view.agent||view.literal))return;
  if(view.literal){clearReleaseApproval(view);engineeringButtons(view);return;}
  clearReleaseApproval(view);view.offlineReplay=null;$("internal-replay-file").value="";
  $("internal-replay-status").textContent="检索词已变化，请重新加载对应离线响应；未确认批准已清除。";
  engineeringButtons(view);
}
$("app-agent-term").oninput=changeAgentInput;
$("internal-term").oninput=changeAgentInput;
$("internal-replay-file").onchange=async()=>{
  const view=engineering;if(!view || !engineeringCurrent(view) || !view.agent)return;
  clearReleaseApproval(view);view.offlineReplay=null;
  const generation=view.inputGeneration,file=$("internal-replay-file").files[0];
  const current=()=>engineeringCurrent(view) && generation===view.inputGeneration;
  engineeringButtons(view);$("internal-replay-status").textContent="正在读取离线文件…";
  try {
    if(!file)throw Error("尚未选择离线响应文件");
    if(file.size>32000)throw Error("离线文件超过32000字节");
    const data=JSON.parse(await file.text());
    if(!current())return;
    if(!Array.isArray(data) || data.length!==2 || data.some(r=>!r || Array.isArray(r) || typeof r!=="object" || Object.keys(r).some(k=>!["choices","model","id","object","created","usage"].includes(k)) || !Array.isArray(r.choices) || r.choices.length!==1) || new TextEncoder().encode(JSON.stringify(data)).length>32000)throw Error("需要恰好两条有限的wire响应；不接受gold或provider选项");
    view.offlineReplay=structuredClone(data);
    $("internal-replay-status").textContent="已加载两条离线响应；尚未验证。服务端会实际读取当前授权材料并核查引用，0网络模型请求。";
  }catch(error){if(current())$("internal-replay-status").textContent=`离线文件未加载：${error.message}`;}
  finally{if(current())engineeringButtons(view);}
};


function clearRegisteredExtraction() {
  if(typeof clearTextLogic === "function")clearTextLogic();
  registeredExtractionGeneration++;registeredExtraction=null;
  $("registered-extraction").hidden=true;$("registered-extraction-form").hidden=true;
  $("registered-extraction-proof").textContent="";$("registered-extraction-target-info").textContent="";
  $("registered-extraction-target").replaceChildren();$("registered-extraction-status").textContent="";
  $("registered-extraction-name").value="从成功任务保存的汇总";
  $("registered-extraction-retry").hidden=true;
  $("registered-extraction-new").hidden=true;$("registered-extraction-request-info").textContent="";
  for(const id of ["registered-extraction-target","registered-extraction-name","registered-extraction-retry","registered-extraction-submit","registered-extraction-new"])$(id).disabled=false;
}
function registeredCurrent(state) {
  return registeredExtraction===state && engineeringCurrent(state.view) && state.token===token && state.project===$("project-select").value && state.view.instance?.id===state.iid && state.view.run?.id===state.rid && state.view.run.version===state.version;
}
function renderRegisteredExtraction(view,instance,run) {
  if(view.workflow || view.agent || run.status!=="SUCCEEDED" || run.content_access===false || run.cancel_intent){clearRegisteredExtraction();return;}
  if(registeredExtraction?.view===view && registeredExtraction.iid===instance.id && registeredExtraction.rid===run.id && registeredExtraction.version===run.version)return;
  clearRegisteredExtraction();registeredExtraction={view,token,project:view.project,iid:instance.id,rid:run.id,version:run.version,generation:registeredExtractionGeneration,options:null,busy:false};
  $("registered-extraction").hidden=false;$("registered-extraction-open").disabled=false;
  if(typeof renderTextLogicSource === "function")renderTextLogicSource(registeredExtraction);
}
function registeredBody(state) {
  const target=state.options?.targets.find(t=>t.id===$("registered-extraction-target").value);
  if(!target)return null;
  return {expected_proof_fingerprint:state.options.source_proof_fingerprint || state.options.proof_fingerprint,target_app_id:target.id,expected_target_draft_fingerprint:target.fingerprint,name:$("registered-extraction-name").value};
}
function registeredKey(state,body) {return JSON.stringify([state.token,state.project,state.iid,state.rid,state.version,body]);}
function registeredTextContext(state){
  const context={workspace:workspaceSelectionGeneration,app:appSelectionGeneration,goal:goalSelectionGeneration,connection:identityConnectionGeneration,edit:registeredExtractionEditGeneration,instance:state.view.instanceGeneration,run:state.view.runGeneration,handoff:false};
  context.current=()=>state.token===token&&state.project===$("project-select").value&&context.connection===identityConnectionGeneration&&context.workspace===workspaceSelectionGeneration&&context.app===appSelectionGeneration&&context.goal===goalSelectionGeneration&&context.edit===registeredExtractionEditGeneration&&(context.handoff||(registeredCurrent(state)&&context.instance===state.view.instanceGeneration&&context.run===state.view.runGeneration));
  return context;
}
async function registeredHash(value){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");}
function registeredJournalMeta(state,row){
  if(!row||row.namespace!=="registered-text-request-identity.v1"||row.principal_id!==state.view.instance.principal_id||row.project_id!==state.project||row.source_app_id!==state.view.app||row.instance_id!==state.iid||row.source_run_id!==state.rid||typeof row.request_key!=="string"||!row.request_key.length||row.request_key.length>100||!Number.isSafeInteger(row.sequence)||row.sequence<1||row.sequence>64||!['PREPARED','COMMITTED','CLOSED'].includes(row.state)||!['request_fingerprint','expected_proof_fingerprint','expected_target_draft_fingerprint'].every(k=>/^[a-f0-9]{64}$/.test(row[k]))||!/^app_[a-f0-9]{32}$/.test(row.target_app_id)||(row.state==='COMMITTED'&&(!/^app_[a-f0-9]{32}$/.test(row.app_id)||!/^[a-f0-9]{64}$/.test(row.candidate_fingerprint)))||(row.state!=='COMMITTED'&&(row.app_id!==null||row.candidate_fingerprint!==null)))throw Error('VERSION_CONFLICT');
  return row;
}
async function registeredJournalRequest(state,meta,record,current){
  registeredJournalMeta(state,record);
  if(goalRunCanonical(Object.fromEntries(Object.entries(record).filter(([k])=>!['request','latest_key','formal_publication_enabled'].includes(k))))!==goalRunCanonical(Object.fromEntries(Object.entries(meta).filter(([k])=>k!=='formal_publication_enabled'))))throw Error('VERSION_CONFLICT');
  const request=record.request,{request_key,...body}=request||{};
  const digest=await registeredHash(body);
  if(!current())return null;
  const target=state.options.targets.find(t=>t.id===record.target_app_id);
  if(!target||record.latest_key!==record.request_key||request_key!==record.request_key||digest!==record.request_fingerprint||body.instance_id!==state.iid||body.source_run_id!==state.rid||body.expected_proof_fingerprint!==state.options.source_proof_fingerprint||body.expected_proof_fingerprint!==record.expected_proof_fingerprint||body.target_app_id!==record.target_app_id||body.expected_target_draft_fingerprint!==target.fingerprint||body.expected_target_draft_fingerprint!==record.expected_target_draft_fingerprint||typeof body.name!=='string'||!body.name.trim()||goalRunCanonical(Object.keys(body).sort())!==goalRunCanonical(['instance_id','source_run_id','expected_proof_fingerprint','target_app_id','expected_target_draft_fingerprint','name'].sort()))throw Error('VERSION_CONFLICT');
  const {instance_id,source_run_id,...pending}=request;
  return pending;
}
function registeredJournalControls(state){
  const latest=state.latest,pending=state.pending;
  const blocked=!!pending||!!latest&&latest.state!=='CLOSED'&&!state.newReady;
  $("registered-extraction-request-info").textContent=latest?`原请求 ${latest.request_key} · 序列 ${latest.sequence} · ${latest.state} · 指纹 ${latest.request_fingerprint}。先只读核对；未知结果不自动重发。`:"尚无持久请求。保存前会先记录此精确请求身份。";
  $("registered-extraction-retry").hidden=!blocked;
  $("registered-extraction-submit").disabled=state.busy||!state.discovered||blocked||!registeredBody(state)?.name.trim();
  $("registered-extraction-new").hidden=!latest||latest.state==='CLOSED'||state.newReady;
  $("registered-extraction-new").disabled=state.busy;
  $("registered-extraction-new").textContent=latest?.state==='PREPARED'?"明确结束未受理的原请求":"核对原请求后开始另一次明确提取";
}
async function registeredTextReceipt(state,pending,saved,current){
  const {request_key,...body}=pending;
  const digest=await registeredHash({instance_id:state.iid,source_run_id:state.rid,...body});
  return registeredTextReceiptMatches(state,pending,saved,digest,current);
}
function registeredTextReceiptMatches(state,pending,saved,digest,current){
  const target=state.options.targets.find(t=>t.id===pending.target_app_id),request_key=pending.request_key;
  if(!current())return false;
  if(!saved||!/^app_[a-f0-9]{32}$/.test(saved.id)||!/^[a-f0-9]{64}$/.test(saved.candidate_fingerprint)||[state.view.app,target.id].includes(saved.id)||saved.instance_id!==state.iid||saved.source_run_id!==state.rid||saved.project_id!==state.project||saved.principal_id!==state.view.instance.principal_id||saved.request_key!==request_key||saved.request_fingerprint!==digest||saved.source_proof_fingerprint!==pending.expected_proof_fingerprint||saved.target_resource_hash!==target.source_hash||saved.authorization_domain!==target.runtime_id||saved.generator!=="TRUSTED_REGISTERED_TEXT_FROM_APPRUN.v1"||saved.state!=="PREVIEW_ONLY"||saved.publishable!==false||saved.formal_publication_enabled!==false||saved.model_requests!==0||saved.semantic_goal_acceptance!=="NOT_RUN"||saved.technical_semantic_status!=="UNKNOWN"||saved.owner_acceptance!=="PENDING"||typeof saved.cached!=="boolean")throw Error("VERSION_CONFLICT");
  return true;
}
async function registeredTextCandidate(state,pending,saved,candidate,current){
  const target=state.options.targets.find(t=>t.id===pending.target_app_id),value=candidate.candidate,marker=value?.task_proof;
  const expectedTarget={app_id:target.id,fingerprint:target.fingerprint,resource_id:target.resource_id,source_hash:target.source_hash,runtime_id:target.runtime_id};
  const digest=await registeredHash(value);
  if(!current())return;
  if(candidate.id!==saved.id||candidate.project_id!==state.project||candidate.runtime_id!==target.runtime_id||candidate.name!==pending.name||candidate.fingerprint!==saved.candidate_fingerprint||digest!==saved.candidate_fingerprint||value?.manifest?.app_id!==saved.id||value.manifest.origin!=="task_run"||value.manifest.source_run_ref!==state.rid||value.goal_application||value.source_hash!==target.source_hash||value.manifest.data_bindings?.length!==1||value.manifest.data_bindings[0].resource_ref!==target.resource_id||marker?.generator!==saved.generator||marker.proof_fingerprint!==pending.expected_proof_fingerprint||goalRunCanonical(marker.proof)!==goalRunCanonical(state.options.proof)||goalRunCanonical(marker.target)!==goalRunCanonical(expectedTarget)||goalRunCanonical(marker.extraction_request)!==goalRunCanonical({instance_id:state.iid,source_run_id:state.rid,...pending}))throw Error("VERSION_CONFLICT");
  const {request_key,...body}=pending;
  const requestDigest=await registeredHash({instance_id:state.iid,source_run_id:state.rid,...body});
  if(!current())return;
  const fresh=await api(`/api/internal/instances/${state.iid}/runs/${state.rid}/extraction-receipts?request_key=${encodeURIComponent(pending.request_key)}&require_latest=true`);
  if(!registeredTextReceiptMatches(state,pending,fresh,requestDigest,current))return;
  if(fresh.latest_verified!==true||fresh.latest_request_key!==pending.request_key||fresh.journal_sequence!==saved.journal_sequence||fresh.id!==saved.id||fresh.candidate_fingerprint!==saved.candidate_fingerprint)throw Error('VERSION_CONFLICT');
}
function registeredSelectionChanged() {
  const state=registeredExtraction;if(!state || !registeredCurrent(state))return;
  const body=registeredBody(state),target=state.options?.targets.find(t=>t.id===body?.target_app_id);
  $("registered-extraction-target-info").textContent=target ? `材料 ${target.resource_id} · hash ${target.source_hash || target.hash} · 沿用授权域 ${target.runtime_id}；共享授权撤回同时影响此草案。` : "";
  $("registered-extraction-retry").hidden=!body || !registeredExtractionRequests.has(registeredKey(state,body));
  $("registered-extraction-submit").disabled=state.busy || !body || !body.name.trim() || (state.view.literal&&registeredExtractionRequests.has(registeredKey(state,body)));
  if(state.view.literal)registeredJournalControls(state);
}
$("registered-extraction-target").onchange=registeredSelectionChanged;
$("registered-extraction-name").oninput=registeredSelectionChanged;
$("registered-extraction-open").onclick=safe(async()=>{
  const state=registeredExtraction;if(!state || !registeredCurrent(state) || state.busy)return;
  const context=state.view.literal?registeredTextContext(state):null,current=()=>context?context.current():registeredCurrent(state);
  state.busy=true;$("registered-extraction-open").disabled=true;$("registered-extraction-status").textContent="正在核查真实成功任务与已有授权…";
  try {
    const options=await api(`/api/internal/instances/${state.iid}/runs/${state.rid}/extraction-options`);
    if(!current())return;
    if(state.view.literal){
      const proof=options.proof,digest=await registeredHash(proof);
      if(!current())return;
      if(proof?.kind!=="completed_registered_text_apprun.v1"||proof.instance_id!==state.iid||proof.source_run_id!==state.rid||proof.project_id!==state.project||proof.principal_id!==state.view.instance.principal_id||proof.run_version!==state.version||options.source_proof_fingerprint!==digest||options.proof_fingerprint!==digest||options.owner_acceptance!=="PENDING"||options.technical_semantic_status!=="UNKNOWN"||options.model_requests!==0||options.formal_publication_enabled!==false||!Array.isArray(options.targets)||!options.targets.length)throw Error("VERSION_CONFLICT");
    }
    state.options=options;$("registered-extraction-proof").textContent=JSON.stringify({proof:options.proof,proof_fingerprint:options.source_proof_fingerprint || options.proof_fingerprint},null,2);
    $("registered-extraction-target").replaceChildren(new Option(state.view.literal?"请选择已有授权的新 TXT/MD 应用":"请选择已有授权的新 CSV 应用",""),...options.targets.map(t=>new Option(t.name,t.id)));
    $("registered-extraction-form").hidden=false;$("registered-extraction-status").textContent=state.view.literal?"来源已核查。选择不同 TXT/MD 的既有授权域；term 为运行变量，owner PENDING，语义 UNKNOWN。":"来源已核查。选择不同 CSV 的既有授权域；不会自动创建权限。";
    if(state.view.literal){
      const index=await api(`/api/internal/instances/${state.iid}/runs/${state.rid}/extraction-requests`);
      if(!current())return;
      if(index.namespace!=="registered-text-request-identity.v1"||!Array.isArray(index.items)||index.items.length>64||goalRunCanonical(index.latest)!==goalRunCanonical(index.items.at(-1)||null))throw Error('VERSION_CONFLICT');
      index.items.forEach((row,i)=>{registeredJournalMeta(state,row);if(row.sequence!==i+1||row.previous_key!==(i?index.items[i-1].request_key:null))throw Error('VERSION_CONFLICT');});
      state.latest=index.latest;state.newReady=false;state.discovered=true;
      if(!state.latest){for(const [key,value] of registeredExtractionRequests){const scope=JSON.parse(key);if(scope[0]===state.token&&scope[1]===state.project&&scope[2]===state.iid&&scope[3]===state.rid&&scope[4]===state.version){state.pending=value;break;}}}
      if(state.latest&&state.latest.state!=='CLOSED')$("registered-extraction-status").textContent="找到持久原请求身份。请只读核对原 key；未确定结果前不能重复保存。term 为变量，owner PENDING，语义 UNKNOWN。";
    }
  }catch(error){if(current()){if(["GRANT_REVOKED","PERMISSION_DENIED","VERSION_CONFLICT"].includes(error.message)){clearRegisteredExtraction();engineeringStatus(state.view,error.message,"error");}else $("registered-extraction-status").textContent=error.detail || error.message;}}
  finally {state.busy=false;if(registeredCurrent(state)){$("registered-extraction-open").disabled=false;registeredSelectionChanged();}}
});
async function submitRegisteredExtraction(retry=false) {
  const state=registeredExtraction;if(!state || !registeredCurrent(state) || state.busy)return;
  const body=registeredBody(state);if((!body || !body.name.trim())&&!(state.view.literal&&retry))return;
  let key=body?registeredKey(state,body):null,pending=state.view.literal?(state.newReady?null:state.pending||registeredExtractionRequests.get(key)):registeredExtractionRequests.get(key);
  if(state.view.literal&&!retry&&(!state.discovered||$("registered-extraction-submit").disabled))return;
  if(!pending && !retry){pending={...body,request_key:crypto.randomUUID()};registeredExtractionRequests.set(key,pending);}
  if(!pending&&!(state.view.literal&&retry&&state.latest))return;
  if(state.view.literal&&pending)state.pending=pending;
  const context=state.view.literal?registeredTextContext(state):null;
  const current=()=>context?context.current():registeredCurrent(state) && registeredKey(state,registeredBody(state))===key;
  state.busy=true;$("registered-extraction-submit").disabled=true;$("registered-extraction-retry").disabled=true;$("registered-extraction-target").disabled=true;$("registered-extraction-name").disabled=true;
  $("registered-extraction-status").textContent="正在由服务端生成可复用草案…";
  let made=null,readGeneration=null;const readGoalGeneration=goalSelectionGeneration;
  try {
    const base=`/api/internal/instances/${state.iid}/runs/${state.rid}`;
    if(state.view.literal){
      let hint=null;
      if(!retry){
        const prepared=await api(base+'/extraction-requests','POST',{...pending,expected_latest_key:state.latest?.request_key||null,expected_latest_candidate_fingerprint:state.newReady&&state.latest?.state==='COMMITTED'?state.latest.candidate_fingerprint:null});
        if(!current())return;registeredJournalMeta(state,prepared);
        const {request_key,...fields}=pending,digest=await registeredHash({instance_id:state.iid,source_run_id:state.rid,...fields});
        if(!current())return;
        if(prepared.request_key!==request_key||prepared.request_fingerprint!==digest||prepared.state!=='PREPARED')throw Error('VERSION_CONFLICT');
        state.latest=prepared;state.newReady=false;
        hint=await api(base+"/extract","POST",pending);if(!await registeredTextReceipt(state,pending,hint,current))return;
      }
      const originalKey=pending?.request_key||state.latest.request_key;
      const record=await api(base+`/extraction-requests?request_key=${encodeURIComponent(originalKey)}`);
      if(!current())return;
      registeredJournalMeta(state,record);
      if(record.request_key!==originalKey||(state.latest&&state.latest.request_key===originalKey&&record.request_fingerprint!==state.latest.request_fingerprint))throw Error('VERSION_CONFLICT');
      if(pending){const {request_key,...known}=pending,knownHash=await registeredHash({instance_id:state.iid,source_run_id:state.rid,...known});if(!current())return;if(record.request_fingerprint!==knownHash)throw Error('VERSION_CONFLICT');}
      const meta=Object.fromEntries(Object.entries(record).filter(([k])=>!['request','latest_key'].includes(k)));
      pending=await registeredJournalRequest(state,meta,record,current);if(!pending)return;
      key=registeredKey(state,registeredBody(state)||pending);state.pending=pending;registeredExtractionRequests.set(key,pending);state.latest=meta;
      if(record.state!=='COMMITTED'){
        $("registered-extraction-status").textContent=record.state==='CLOSED'?"原请求已明确关闭，不得重发；下一次明确保存使用新身份。":"原请求已准备但提交结果尚未确定。保留原 key，只读核对或明确结束未受理请求；不会自动重发。";
        if(record.state==='CLOSED'){state.pending=null;registeredExtractionRequests.delete(key);}return;
      }
      const saved=await api(base+`/extraction-receipts?request_key=${encodeURIComponent(pending.request_key)}&require_latest=true`);
      if(!await registeredTextReceipt(state,pending,saved,current))return;
      if(saved.latest_verified!==true||saved.latest_request_key!==originalKey||saved.journal_sequence!==record.sequence||(hint&&saved.id!==hint.id)||saved.id!==record.app_id||saved.candidate_fingerprint!==record.candidate_fingerprint)throw Error("VERSION_CONFLICT");
      made=saved;
    }else made=await api(base+"/extract","POST",pending);
    if(!current())return;
    $("registered-extraction-status").textContent=`已生成 ${made.id}；正在回读草案。`;
    await refreshApps();if(!current())return;
    if(await showApp(made.id,state.project,g=>{readGeneration=g;if(context){context.app=g;context.handoff=true;}},context?current:()=>true,context?a=>registeredTextCandidate(state,pending,made,a,current):null)&&(!context||current())){
      selectWorkspace("apps");registeredExtractionRequests.delete(key);
      if(state.view.literal){state.pending=null;for(const [entry,value] of registeredExtractionRequests)if(value.request_key===pending.request_key)registeredExtractionRequests.delete(entry);}
      if(state.view.literal){$("app-create-status").textContent=`已只读核对独立应用 ${made.id} · owner PENDING · 语义 UNKNOWN · 未发布`;$("app-agent-term").focus();}
    }
  }catch(error){if(made && readGeneration===appSelectionGeneration && state.token===token && state.project===$("project-select").value && readGoalGeneration===goalSelectionGeneration&&(!context||current())){selectWorkspace("apps");if(context){$("app-create-status").dataset.state="error";$("app-create-status").textContent=`独立应用未通过回执与候选核对：${error.detail || error.message}。请重开来源任务，用原请求键恢复；不会自动重发。`;}else{setAppReadFailure({id:made.id,pid:state.project,kind:"created",goalGeneration:readGoalGeneration},error);registeredExtractionRequests.delete(key);}}else if(current()){if(["GRANT_REVOKED","PERMISSION_DENIED"].includes(error.message)||(!state.view.literal&&error.message==="VERSION_CONFLICT")){clearRegisteredExtraction();engineeringStatus(state.view,error.message,"error");}else {$("registered-extraction-status").textContent=`生成回执或草案回读未确认：${error.detail || error.message}。可用原请求键手动恢复；不会自动重发。`;$("registered-extraction-retry").hidden=false;}}}
  finally {state.busy=false;if(registeredCurrent(state)){$("registered-extraction-target").disabled=false;$("registered-extraction-name").disabled=false;$("registered-extraction-retry").disabled=false;registeredSelectionChanged();}}
}
$("registered-extraction-form").onsubmit=event=>{event.preventDefault();return safe(()=>submitRegisteredExtraction())();};
$("registered-extraction-retry").onclick=safe(()=>submitRegisteredExtraction(true));
$("registered-extraction-new").onclick=safe(async()=>{
  const state=registeredExtraction;if(!state?.view.literal||!registeredCurrent(state)||state.busy||!state.latest)return;
  const context=registeredTextContext(state),current=()=>context.current(),latest=state.latest;
  state.busy=true;registeredSelectionChanged();
  try{
    const base=`/api/internal/instances/${state.iid}/runs/${state.rid}`;
    if(latest.state==='PREPARED'){
      const closed=await api(base+'/extraction-request-close','POST',{request_key:latest.request_key,expected_request_fingerprint:latest.request_fingerprint,expected_latest_key:latest.request_key});
      if(!current())return;registeredJournalMeta(state,closed);
      if(closed.request_key!==latest.request_key||closed.request_fingerprint!==latest.request_fingerprint)throw Error('VERSION_CONFLICT');
      state.latest=closed;state.pending=null;
      for(const [key,value] of registeredExtractionRequests)if(value.request_key===latest.request_key)registeredExtractionRequests.delete(key);
      if(closed.state!=='CLOSED'){$("registered-extraction-status").textContent="原请求已经提交。请先用原 key 只读核对，不得将它关闭或重复安装。";return;}
    }else{
      const record=await api(base+`/extraction-requests?request_key=${encodeURIComponent(latest.request_key)}`);
      if(!current())return;const pending=await registeredJournalRequest(state,latest,record,current);if(!pending)return;
      const saved=await api(base+`/extraction-receipts?request_key=${encodeURIComponent(latest.request_key)}&require_latest=true`);
      if(!await registeredTextReceipt(state,pending,saved,current))return;
      if(saved.latest_verified!==true||saved.latest_request_key!==latest.request_key||saved.journal_sequence!==latest.sequence||saved.id!==latest.app_id||saved.candidate_fingerprint!==latest.candidate_fingerprint)throw Error('VERSION_CONFLICT');
      const candidate=await api(`/api/apps/${saved.id}`);if(!current())return;
      await registeredTextCandidate(state,pending,saved,candidate,current);if(!current())return;
      state.pending=null;
    }
    for(const [entry,value] of registeredExtractionRequests)if(value.request_key===latest.request_key)registeredExtractionRequests.delete(entry);
    state.newReady=true;$("registered-extraction-status").textContent="已核对前序请求。下一次手动保存是新的明确请求，使用新 key；term 为变量，owner PENDING，语义 UNKNOWN；原历史保留。";
  }catch(error){if(current())$("registered-extraction-status").textContent=`无法确定原请求状态：${error.detail||error.message}。保留原 key，阻止重复保存。`;}
  finally{state.busy=false;if(registeredCurrent(state))registeredSelectionChanged();}
});

let registeredRecoveryGeneration=0;
function clearRegisteredRecoveries(){registeredRecoveryGeneration++;$("registered-recovery-list").replaceChildren();$("registered-recovery-status").textContent="";}
$("project-select").addEventListener('change',clearRegisteredRecoveries);
$("connect").addEventListener('click',clearRegisteredRecoveries);
function registeredRecoveryContext(){
  const ctx={token,project:$("project-select").value,connection:identityConnectionGeneration,workspace:workspaceSelectionGeneration,app:appSelectionGeneration,goal:goalSelectionGeneration,generation:registeredRecoveryGeneration};
  ctx.current=()=>ctx.token===token&&ctx.project===$("project-select").value&&ctx.connection===identityConnectionGeneration&&ctx.workspace===workspaceSelectionGeneration&&ctx.app===appSelectionGeneration&&ctx.goal===goalSelectionGeneration&&ctx.generation===registeredRecoveryGeneration;
  return ctx;
}
$("registered-recovery-refresh").onclick=safe(async()=>{
  const ctx=registeredRecoveryContext();registeredRecoveryGeneration++;ctx.generation=registeredRecoveryGeneration;
  $("registered-recovery-list").replaceChildren();$("registered-recovery-status").textContent="正在只读发现本项目的原请求身份…";
  try{
    const index=await api(`/api/projects/${ctx.project}/registered-text-requests`);if(!ctx.current())return;
    if(index.namespace!=='registered-text-request-identity.v1'||index.project_id!==ctx.project||typeof index.principal_id!=='string'||!Array.isArray(index.items)||index.items.length>64)throw Error('VERSION_CONFLICT');
    const elements=index.items.map(item=>{
      const fake={view:{app:item.source_app_id,instance:{principal_id:index.principal_id}},project:ctx.project,iid:item.instance_id,rid:item.source_run_id};registeredJournalMeta(fake,item);
      const entry=document.createElement('div'),label=document.createElement('p'),open=document.createElement('button'),close=document.createElement('button');
      label.textContent=`原请求 ${item.request_key} · ${item.state} · 序列 ${item.sequence} · 来源 ${item.source_app_id}/${item.instance_id}/${item.source_run_id}`;
      open.type=close.type='button';open.textContent="重新核查来源并打开原 key 恢复入口";close.textContent="明确结束未受理的原请求";close.disabled=item.state!=='PREPARED';
      open.onclick=safe(async()=>{
        const reading=registeredRecoveryContext();
        if(reading.project!==ctx.project||reading.token!==ctx.token||reading.connection!==ctx.connection||reading.generation!==ctx.generation)return;
        try{
          const scoped=await api(`/api/internal/instances/${item.instance_id}/runs/${item.source_run_id}/extraction-requests`);
          if(!reading.current())return;
          if(scoped.namespace!=='registered-text-request-identity.v1'||!scoped.latest)throw Error('VERSION_CONFLICT');
          for(const field of ['principal_id','project_id','source_app_id','instance_id','source_run_id','request_key','sequence','previous_key','request_fingerprint','target_app_id','expected_proof_fingerprint','expected_target_draft_fingerprint'])if(scoped.latest[field]!==item[field])throw Error('VERSION_CONFLICT');
          if(!await showApp(item.source_app_id,ctx.project,g=>reading.app=g,reading.current))return;
          if(!reading.current())return;const view=engineering;
          await showInternalInstance(item.instance_id,view);if(!reading.current()||!view.instance)return;
          await showInternalRun(item.source_run_id,view,view.instance);if(!reading.current())return;
          $("registered-recovery-status").textContent="来源重新读取。打开任务提取入口后，用原 key 只读核对；不会自动重发。";
        }catch(error){if(reading.current())$("registered-recovery-status").textContent=`当前权限或来源不允许恢复：${error.detail||error.message}。原身份保留，不会重发；未受理请求仍可明确结束。`;}
      });
      close.onclick=safe(async()=>{
        const closing=registeredRecoveryContext();if(closing.project!==ctx.project||closing.token!==ctx.token||closing.connection!==ctx.connection||closing.generation!==ctx.generation)return;
        close.disabled=true;
        try{
          const result=await api(`/api/internal/instances/${item.instance_id}/runs/${item.source_run_id}/extraction-request-close`,'POST',{request_key:item.request_key,expected_request_fingerprint:item.request_fingerprint,expected_latest_key:item.request_key});
          if(!closing.current())return;registeredJournalMeta(fake,result);
          if(result.request_key!==item.request_key||result.request_fingerprint!==item.request_fingerprint)throw Error('VERSION_CONFLICT');
          label.textContent=`原请求 ${result.request_key} · ${result.state} · 序列 ${result.sequence}`;
          $("registered-recovery-status").textContent=result.state==='CLOSED'?"原请求已明确关闭。迟到的原提取将拒绝；历史身份保留。":"原请求已提交，不能关闭。请在当前授权允许时按原 key 只读核对。";
        }catch(error){if(closing.current()){$("registered-recovery-status").textContent=`无法结束原请求：${error.detail||error.message}。原 key 保留。`;close.disabled=false;}}
      });entry.append(label,open,close);return entry;
    });
    $("registered-recovery-list").replaceChildren(...elements);$("registered-recovery-status").textContent=elements.length?"仅显示受保护请求身份元数据。正文仍须当前权限；恢复不重发。":"本项目尚无本协议的持久请求。";
  }catch(error){if(ctx.current())$("registered-recovery-status").textContent=`无法发现原请求：${error.detail||error.message}。先核对，不自动提交。`;}
});
