"use strict";
// Each view and request carries its own identity/selection generation; no browser execution.
let engineering = null, engineeringGeneration = 0;
const engineeringPending = new Map();
const engineeringInstanceKeys = new Map();
const registeredExtractionRequests = new Map();
let registeredExtraction = null, registeredExtractionGeneration = 0;
function engineeringCurrent(view) {
  return engineering === view && view.token === token && view.project === $("project-select").value && view.app === activeApp && view.appGeneration === appSelectionGeneration;
}
function engineeringStatus(view,text,state="") {
  if(!engineeringCurrent(view))return;
  $("internal-status").textContent=text;$("internal-status").dataset.state=state;
}
function clearInternal() {
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
  const view={app:app.id,project:app.project_id,token,appGeneration,generation:++engineeringGeneration,draft:app,busy:false,approval:null,instance:null,run:null,instanceGeneration:0,runGeneration:0,releases:[],switchGeneration:0,switchApproval:null,agent:app.input_guidance.mode === "OFFLINE_REPLAY_ONLY",offlineReplay:null,inputGeneration:0};
  engineering=view;$("apps").append($("internal-panel"));$("internal-panel").hidden=false;
  $("internal-agent").hidden=!view.agent;
  $("internal-replay-status").textContent=view.agent ? "尚未加载离线响应；审批与新运行暂不可提交。" : "";
  $("internal-prepare-hint").textContent=view.agent ? "使用上方样例字面检索词与已加载的离线响应核查当前材料。先查看精确快照，再手动确认保存内部版本；语义仍为 UNKNOWN。" : "使用当前选定数值列重新核查固定可信计算；先查看精确快照，再确认保存。仅内部版本，不是正式发布。";
  engineeringButtons(view);engineeringStatus(view,"正在读取内部版本与实例…","loading");
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
    $("internal-column-label").hidden=view.agent;$("internal-column").required=!view.agent;$("internal-term-label").hidden=!view.agent;$("internal-term").required=view.agent;
    $("internal-column").replaceChildren(...Array.from($("app-column").options).map(o=>{const option=new Option(o.textContent,o.value);option.disabled=o.disabled;return option;}));
    $("internal-run-form").hidden=false;
    $("internal-data").replaceChildren(...instance.data.map(record=>internalResult(record,view)));
    $("internal-runs").replaceChildren(...instance.runs.map(run=>row(`${run.status} · ${run.id} · 结果版本 ${run.result_version ?? "无"}`,()=>showInternalRun(run.id,view,instance),"读取后台任务")));
    $("internal-run-status").textContent=engineeringPending.has(id) ? "上次提交回执未确认，可用原请求键恢复；不会自动重发。" : (view.agent ? "加载对应离线响应并填写本次检索词；后台核查真实授权材料，不调用provider。关闭页面不会取消任务。" : "选择数值列，提交后台只读计算；关闭页面不会取消已接受任务。");
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
    if(run.content_access!==false && previousStatus && previousStatus!==run.status && ["SUCCEEDED","FAILED","CANCELLED"].includes(run.status)){
      await showInternalInstance(instance.id,view);
      if(engineeringCurrent(view) && view.instance?.id===instance.id)await showInternalRun(id,view,view.instance);
    }
  } catch(error){if(current()){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");$("internal-run-status").textContent+=" · 无法读取当前详情";}}
}
async function submitInternal(view,retry=false) {
  const instance=view.instance;if(!instance)return;
  let pending=engineeringPending.get(instance.id);
  if(!pending && !retry){pending={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,input:view.agent ? {term:$("internal-term").value} : {column:$("internal-column").value},...(view.agent ? {offline_replay:structuredClone(view.offlineReplay)} : {}),request_key:crypto.randomUUID()};engineeringPending.set(instance.id,pending);}
  if(!pending)return;
  const generation=view.instanceGeneration;
  $("internal-run-status").textContent="正在提交持久任务…";
  const accepted=await api(`/api/internal/instances/${instance.id}/runs`,"POST",pending);
  engineeringPending.delete(instance.id);
  if(!engineeringCurrent(view) || generation!==view.instanceGeneration)return;
  $("internal-run-status").textContent=`已接受 ${accepted.run_id}，关闭页面不取消。`;
  await showInternalInstance(instance.id,view);
  if(engineeringCurrent(view) && view.instance?.id===instance.id)await showInternalRun(accepted.run_id,view,view.instance);
}
$("internal-prepare").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering;view.approval=null;$("internal-approval").hidden=true;$("internal-approval-ack").checked=false;
  const inputGeneration=view.inputGeneration;
  const current=()=>engineeringCurrent(view) && inputGeneration===view.inputGeneration;
  const sample=view.agent ? {term:$("app-agent-term").value} : {column:$("app-column").value};
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
 if(!["SUCCEEDED","FAILED","CANCELLED"].includes(view.run.status))await showInternalRun(view.run.id,view,view.instance);
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
  if(!view.agent)return row(`结果 v${record.version} · ${record.release_id} · ${JSON.stringify(record.data.result)}`);
  const value=record.data.result,node=document.createElement("article");node.className="agent-result";
  const title=document.createElement("p");title.textContent=`历史结果 v${record.version} · ${record.release_id} · 离线 Replay · 字面检查 PASS · 语义 ${value.semantic_status}`;
  const scope=document.createElement("p");scope.textContent=`检索词：${value.term} · 材料 ${value.resource_id} · revision ${value.revision} · hash ${value.source_hash}`;
  const quotes=document.createElement("ul");
  for(const cite of value.citations){const line=document.createElement("li"),label=document.createElement("span"),quote=document.createElement("blockquote");label.textContent=`第 ${cite.start_line}—${cite.end_line} 行`;quote.textContent=cite.quote;line.append(label,quote);quotes.append(line);}
  if(!value.citations.length)quotes.textContent="无字面命中；不代表语义不存在。";
  node.append(title,scope,quotes);return node;
}
function changeAgentInput() {
  const view=engineering;if(!view || !engineeringCurrent(view) || !view.agent)return;
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
  registeredExtractionGeneration++;registeredExtraction=null;
  $("registered-extraction").hidden=true;$("registered-extraction-form").hidden=true;
  $("registered-extraction-proof").textContent="";$("registered-extraction-target-info").textContent="";
  $("registered-extraction-target").replaceChildren();$("registered-extraction-status").textContent="";
  $("registered-extraction-name").value="从成功任务保存的汇总";
  $("registered-extraction-retry").hidden=true;
  for(const id of ["registered-extraction-target","registered-extraction-name","registered-extraction-retry","registered-extraction-submit"])$(id).disabled=false;
}
function registeredCurrent(state) {
  return registeredExtraction===state && engineeringCurrent(state.view) && state.token===token && state.project===$("project-select").value && state.view.instance?.id===state.iid && state.view.run?.id===state.rid && state.view.run.version===state.version;
}
function renderRegisteredExtraction(view,instance,run) {
  if(view.agent || run.status!=="SUCCEEDED" || run.content_access===false || run.cancel_intent){clearRegisteredExtraction();return;}
  if(registeredExtraction?.view===view && registeredExtraction.iid===instance.id && registeredExtraction.rid===run.id && registeredExtraction.version===run.version)return;
  clearRegisteredExtraction();registeredExtraction={view,token,project:view.project,iid:instance.id,rid:run.id,version:run.version,generation:registeredExtractionGeneration,options:null,busy:false};
  $("registered-extraction").hidden=false;$("registered-extraction-open").disabled=false;
}
function registeredBody(state) {
  const target=state.options?.targets.find(t=>t.id===$("registered-extraction-target").value);
  if(!target)return null;
  return {expected_proof_fingerprint:state.options.source_proof_fingerprint || state.options.proof_fingerprint,target_app_id:target.id,expected_target_draft_fingerprint:target.fingerprint,name:$("registered-extraction-name").value};
}
function registeredKey(state,body) {return JSON.stringify([state.token,state.project,state.iid,state.rid,state.version,body]);}
function registeredSelectionChanged() {
  const state=registeredExtraction;if(!state || !registeredCurrent(state))return;
  const body=registeredBody(state),target=state.options?.targets.find(t=>t.id===body?.target_app_id);
  $("registered-extraction-target-info").textContent=target ? `材料 ${target.resource_id} · hash ${target.source_hash || target.hash} · 沿用授权域 ${target.runtime_id}；共享授权撤回同时影响此草案。` : "";
  $("registered-extraction-retry").hidden=!body || !registeredExtractionRequests.has(registeredKey(state,body));
  $("registered-extraction-submit").disabled=state.busy || !body || !body.name.trim();
}
$("registered-extraction-target").onchange=registeredSelectionChanged;
$("registered-extraction-name").oninput=registeredSelectionChanged;
$("registered-extraction-open").onclick=safe(async()=>{
  const state=registeredExtraction;if(!state || !registeredCurrent(state) || state.busy)return;
  state.busy=true;$("registered-extraction-open").disabled=true;$("registered-extraction-status").textContent="正在核查真实成功任务与已有授权…";
  try {
    const options=await api(`/api/internal/instances/${state.iid}/runs/${state.rid}/extraction-options`);
    if(!registeredCurrent(state))return;
    state.options=options;$("registered-extraction-proof").textContent=JSON.stringify({proof:options.proof,proof_fingerprint:options.source_proof_fingerprint || options.proof_fingerprint},null,2);
    $("registered-extraction-target").replaceChildren(new Option("请选择已有授权的新 CSV 应用",""),...options.targets.map(t=>new Option(t.name,t.id)));
    $("registered-extraction-form").hidden=false;$("registered-extraction-status").textContent="来源已核查。选择不同 CSV 的既有授权域；不会自动创建权限。";
  }catch(error){if(registeredCurrent(state)){if(["GRANT_REVOKED","PERMISSION_DENIED","VERSION_CONFLICT"].includes(error.message)){clearRegisteredExtraction();engineeringStatus(state.view,error.message,"error");}else $("registered-extraction-status").textContent=error.detail || error.message;}}
  finally {state.busy=false;if(registeredCurrent(state)){$("registered-extraction-open").disabled=false;registeredSelectionChanged();}}
});
async function submitRegisteredExtraction(retry=false) {
  const state=registeredExtraction;if(!state || !registeredCurrent(state) || state.busy)return;
  const body=registeredBody(state);if(!body || !body.name.trim())return;
  const key=registeredKey(state,body);let pending=registeredExtractionRequests.get(key);
  if(!pending && !retry){pending={...body,request_key:crypto.randomUUID()};registeredExtractionRequests.set(key,pending);}
  if(!pending)return;
  const current=()=>registeredCurrent(state) && registeredKey(state,registeredBody(state))===key;
  state.busy=true;$("registered-extraction-submit").disabled=true;$("registered-extraction-retry").disabled=true;$("registered-extraction-target").disabled=true;$("registered-extraction-name").disabled=true;
  $("registered-extraction-status").textContent="正在由服务端生成可复用草案…";
  let made=null,readGeneration=null;const readGoalGeneration=goalSelectionGeneration;
  try {
    made=await api(`/api/internal/instances/${state.iid}/runs/${state.rid}/extract`,"POST",pending);
    if(!current())return;
    $("registered-extraction-status").textContent=`已生成 ${made.id}；正在回读草案。`;
    await refreshApps();if(!current())return;
    if(await showApp(made.id,state.project,g=>{readGeneration=g;})){selectWorkspace("apps");registeredExtractionRequests.delete(key);}
  }catch(error){if(made && readGeneration===appSelectionGeneration && state.token===token && state.project===$("project-select").value && readGoalGeneration===goalSelectionGeneration){selectWorkspace("apps");setAppReadFailure({id:made.id,pid:state.project,kind:"created",goalGeneration:readGoalGeneration},error);registeredExtractionRequests.delete(key);}else if(current()){if(["GRANT_REVOKED","PERMISSION_DENIED","VERSION_CONFLICT"].includes(error.message)){clearRegisteredExtraction();engineeringStatus(state.view,error.message,"error");}else {$("registered-extraction-status").textContent=`生成回执或草案回读未确认：${error.detail || error.message}。可用原请求键手动恢复；不会自动重发。`;$("registered-extraction-retry").hidden=false;}}}
  finally {state.busy=false;if(registeredCurrent(state)){$("registered-extraction-target").disabled=false;$("registered-extraction-name").disabled=false;$("registered-extraction-retry").disabled=false;registeredSelectionChanged();}}
}
$("registered-extraction-form").onsubmit=event=>{event.preventDefault();return safe(()=>submitRegisteredExtraction())();};
$("registered-extraction-retry").onclick=safe(()=>submitRegisteredExtraction(true));
