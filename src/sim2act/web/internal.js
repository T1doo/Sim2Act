"use strict";
// Each view and request carries its own identity/selection generation; no browser execution.
let engineering = null, engineeringGeneration = 0;
const engineeringPending = new Map();
const engineeringInstanceKeys = new Map();
function engineeringCurrent(view) {
  return engineering === view && view.token === token && view.project === $("project-select").value && view.app === activeApp && view.appGeneration === appSelectionGeneration;
}
function engineeringStatus(view,text,state="") {
  if(!engineeringCurrent(view))return;
  $("internal-status").textContent=text;$("internal-status").dataset.state=state;
}
function clearInternal() {
  engineeringGeneration++;engineering=null;
  $("internal-panel").hidden=true;$("internal-approval").hidden=true;$("internal-approval-detail").textContent="";$("internal-approval-ack").checked=false;
  $("internal-status").textContent="";
  for(const id of ["internal-releases","internal-instances","internal-runs","internal-data","internal-controls"] )$(id).replaceChildren();
  $("internal-run-form").hidden=true;$("internal-retry").hidden=true;$("internal-new-intent").hidden=true;$("internal-run-detail").textContent="";$("internal-run-status").textContent="";$("internal-instance-info").textContent="";
}
function engineeringButtons(view) {
  if(!engineeringCurrent(view))return;
  $("internal-prepare").disabled=!!view.busy;
  $("internal-refresh").disabled=!!view.busy;
  $("internal-commit").disabled=!!view.busy || !view.approval || !$("internal-approval-ack").checked;
  $("internal-run-submit").disabled=!!view.busy || !view.instance || engineeringPending.has(view.instance.id);
  $("internal-retry").hidden=!view.instance || !engineeringPending.has(view.instance.id);
  $("internal-retry").disabled=!!view.busy;
  $("internal-new-intent").hidden=$("internal-retry").hidden;$("internal-new-intent").disabled=!!view.busy;
}
async function engineeringAction(view,fn) {
  if(!view || !engineeringCurrent(view) || view.busy)return;
  const selection=view.instanceGeneration;
  view.busy=true;engineeringButtons(view);
  try {await fn();}
  catch(error){if(engineeringCurrent(view) && selection===view.instanceGeneration)engineeringStatus(view,error.message,"error");}
  finally {view.busy=false;engineeringButtons(view);}
}
async function openInternal(app,appGeneration) {
  const view={app:app.id,project:app.project_id,token,appGeneration,generation:++engineeringGeneration,draft:app,busy:false,approval:null,instance:null,run:null,instanceGeneration:0,runGeneration:0};
  engineering=view;$("apps").append($("internal-panel"));$("internal-panel").hidden=false;
  engineeringButtons(view);engineeringStatus(view,"正在读取内部版本与实例…","loading");
  try {await refreshInternal(view);}
  catch(error){if(engineeringCurrent(view)){engineeringStatus(view,error.message,"error");$("internal-releases").replaceChildren();$("internal-instances").replaceChildren();}}
}
async function refreshInternal(view=engineering) {
  if(!view || !engineeringCurrent(view))return;
  const [releases,instances]=await Promise.all([api(`/api/internal/apps/${view.app}/releases`),api(`/api/internal/apps/${view.app}/instances`)]);
  if(!engineeringCurrent(view))return;
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
  const selection=++view.instanceGeneration;view.runGeneration++;view.instance=null;view.run=null;
  $("internal-run-form").hidden=true;$("internal-controls").replaceChildren();$("internal-run-detail").textContent="";$("internal-run-status").textContent="正在读取实例…";$("internal-data").replaceChildren();$("internal-runs").replaceChildren();engineeringButtons(view);
  try {
    const instance=await api(`/api/internal/instances/${id}`);
    if(!engineeringCurrent(view) || selection!==view.instanceGeneration)return;
    if(instance.source_app_id!==view.app || instance.project_id!==view.project)throw Error("实例来源与当前选择不符");
    view.instance=instance;$("internal-instance-title").textContent=`内部实例 ${id}`;
    $("internal-instance-info").textContent=`Release ${instance.release_id} · revision ${instance.revision} · 独立结果版本 ${instance.data_version} · 正式部署关闭`;
    $("internal-column").replaceChildren(...Array.from($("app-column").options).map(o=>{const option=new Option(o.textContent,o.value);option.disabled=o.disabled;return option;}));
    $("internal-run-form").hidden=false;
    $("internal-data").replaceChildren(...instance.data.map(record=>row(`结果 v${record.version} · ${record.release_id} · ${JSON.stringify(record.data.result)}`)));
    $("internal-runs").replaceChildren(...instance.runs.map(run=>row(`${run.status} · ${run.id} · 结果版本 ${run.result_version ?? "无"}`,()=>showInternalRun(run.id,view,instance),"读取后台任务")));
    $("internal-run-status").textContent=engineeringPending.has(id) ? "上次提交回执未确认，可用原请求键恢复；不会自动重发。" : "选择数值列，提交后台只读计算；关闭页面不会取消已接受任务。";
  } catch(error){if(engineeringCurrent(view) && selection===view.instanceGeneration){$("internal-instance-info").textContent="";$("internal-run-status").textContent=error.message;engineeringStatus(view,error.message,"error");}}
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
      $("internal-run-form").hidden=true;$("internal-retry").hidden=true;$("internal-new-intent").hidden=true;$("internal-data").replaceChildren();$("internal-runs").replaceChildren();
      engineeringStatus(view,"当前权限不允许读取内容；仅显示 owner 停止控制状态，不恢复授权。","error");
    }
    if(!current())return;
    if(run.instance_id!==instance.id)throw Error("运行绑定与实例不符");
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
  } catch(error){if(current()){engineeringStatus(view,error.message,"error");$("internal-run-status").textContent+=" · 无法读取当前详情";}}
}
async function submitInternal(view,retry=false) {
  const instance=view.instance;if(!instance)return;
  let pending=engineeringPending.get(instance.id);
  if(!pending && !retry){pending={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,input:{column:$("internal-column").value},request_key:crypto.randomUUID()};engineeringPending.set(instance.id,pending);}
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
  const prepared=await api(`/api/internal/apps/${view.app}/release-approvals`,"POST",{expected_draft_fingerprint:view.draft.fingerprint,sample_input:{column:$("app-column").value}});
  const detail=await api(`/api/internal/approvals/${prepared.id}`);
  if(!engineeringCurrent(view))return;
  if(detail.fingerprint!==prepared.fingerprint)throw Error("批准指纹不一致");
  view.approval=detail;$("internal-approval").hidden=false;$("internal-approval-label").textContent=`内部批准 ${detail.id} · 到期 ${new Date(detail.expires_at*1000).toLocaleString()} · ${detail.fingerprint}`;
  $("internal-approval-detail").textContent=JSON.stringify(detail.payload,null,2);engineeringStatus(view,"请检查精确冻结快照，勾选确认后保存内部 Release。");
});
$("internal-approval-ack").onchange=()=>{if(engineering)engineeringButtons(engineering);};
$("internal-commit").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,approval=view.approval;if(!approval || !$("internal-approval-ack").checked)return;
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
 const view=engineering;if(!view || !engineeringCurrent(view) || view.busy || !view.run || !view.instance)return;
 if(!["SUCCEEDED","FAILED","CANCELLED"].includes(view.run.status))await showInternalRun(view.run.id,view,view.instance);
},2500);
