"use strict";
// Each view and request carries its own identity/selection generation; no browser execution.
let engineering = null, engineeringGeneration = 0;
const engineeringPending = new Map();
const specRecoveryPrefix="sim2act.spec-run-recovery.v1:";
const specRecoveryMetadata=new WeakMap();
function clearSpecRecoveryMemory(){
  for(const [id,pending] of engineeringPending)if(specRecoveryMetadata.has(pending))engineeringPending.delete(id);
  for(const [scope,pending] of naturalTaskRequests)if(naturalTaskRecoveryMetadata.has(pending))naturalTaskRequests.delete(scope);
}
function specRecoveryScope(view,instance){
  return {principal_id:instance.principal_id,project_id:view.project,app_id:view.app,instance_id:instance.id};
}
function specRecoveryKey(view,instance){return specRecoveryPrefix+JSON.stringify(Object.values(specRecoveryScope(view,instance)));}
function specRecoveryCheck(record,view,instance){
  const fields=["namespace","principal_id","project_id","app_id","instance_id","release_id","expected_revision","expected_release_fingerprint","request_key"];
  if(Object.hasOwn(record||{},"expected_owner_goal_binding_fingerprint"))fields.push("expected_owner_goal_binding_fingerprint");
  if(!record||Object.keys(record).sort().join()!==fields.sort().join()||record.namespace!=="spec-run-recovery.v1"||Object.entries(specRecoveryScope(view,instance)).some(([key,value])=>record[key]!==value)||!/^irelease_[a-f0-9]{32}$/.test(record.release_id)||!Number.isSafeInteger(record.expected_revision)||record.expected_revision<1||! /^[a-f0-9]{64}$/.test(record.expected_release_fingerprint)||! /^[a-f0-9-]{36}$/.test(record.request_key)||(record.expected_owner_goal_binding_fingerprint!==undefined&&! /^[a-f0-9]{64}$/.test(record.expected_owner_goal_binding_fingerprint)))throw Error("RECOVERY_RECORD_INVALID");
  return record;
}
function specRecoveryRead(view,instance){
  try{
    const raw=localStorage.getItem(specRecoveryKey(view,instance));
    return raw===null?null:{raw,record:specRecoveryCheck(JSON.parse(raw),view,instance)};
  }catch(error){if(error.message==="RECOVERY_RECORD_INVALID")throw error;throw Error("RECOVERY_STORAGE_UNAVAILABLE");}
}
function specRecoveryRestore(view,instance){
  if(!navigator.locks?.request)throw Error("RECOVERY_LOCK_UNAVAILABLE");
  const saved=specRecoveryRead(view,instance),pending=engineeringPending.get(instance.id),metadata=pending&&specRecoveryMetadata.get(pending);
  if(metadata&&metadata.key!==specRecoveryKey(view,instance))engineeringPending.delete(instance.id);
  if(!saved)return metadata?.key===specRecoveryKey(view,instance)?pending:null;
  if(metadata?.key===specRecoveryKey(view,instance)&&metadata.raw===saved.raw)return pending;
  const record=saved.record;
  const body={expected_revision:record.expected_revision,expected_release_fingerprint:record.expected_release_fingerprint,input:{},request_key:record.request_key,...(record.expected_owner_goal_binding_fingerprint!==undefined?{expected_owner_goal_binding_fingerprint:record.expected_owner_goal_binding_fingerprint}:{})};
  specRecoveryMetadata.set(body,{...saved,key:specRecoveryKey(view,instance)});
  engineeringPending.set(instance.id,body);return body;
}
function specRecoverySave(view,instance,pending){
  const key=specRecoveryKey(view,instance);
  if(specRecoveryRead(view,instance))throw Error("RECOVERY_RECORD_CONFLICT");
  const record=specRecoveryCheck({namespace:"spec-run-recovery.v1",...specRecoveryScope(view,instance),release_id:instance.release_id,expected_revision:pending.expected_revision,expected_release_fingerprint:pending.expected_release_fingerprint,request_key:pending.request_key,...(pending.expected_owner_goal_binding_fingerprint!==undefined?{expected_owner_goal_binding_fingerprint:pending.expected_owner_goal_binding_fingerprint}:{})},view,instance);
  const raw=JSON.stringify(record);
  try{localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)throw Error();}
  catch{throw Error("RECOVERY_STORAGE_UNAVAILABLE");}
  specRecoveryMetadata.set(pending,{key,record,raw});engineeringPending.set(instance.id,pending);
}
function specRecoveryForget(view,instance,pending){
  const metadata=specRecoveryMetadata.get(pending),saved=specRecoveryRead(view,instance);
  // Called only while holding this scope's Web Lock. Never delete a newer intent.
  if(!metadata||metadata.key!==specRecoveryKey(view,instance)||(saved&&saved.raw!==metadata.raw))throw Error("RECOVERY_RECORD_CONFLICT");
  if(saved){try{localStorage.removeItem(metadata.key);if(localStorage.getItem(metadata.key)!==null)throw Error();}catch{throw Error("RECOVERY_STORAGE_UNAVAILABLE");}}
  if(engineeringPending.get(instance.id)===pending)engineeringPending.delete(instance.id);
}
function specRecoveryRefresh(view,instance){
  view.recoveryError=null;
  try{specRecoveryRestore(view,instance);}catch(error){view.recoveryError=error.message;}
}
window.addEventListener("storage",event=>{
  const view=engineering,instance=view?.instance;
  if(!view?.spec||!instance||!engineeringCurrent(view)||!(event.key===null||event.key===specRecoveryKey(view,instance)))return;
  specRecoveryRefresh(view,instance);engineeringButtons(view);
  $("internal-run-status").textContent=view.recoveryError||"恢复记录已变化；已有原请求时仅可读取回执，不会自动提交。";
});
const engineeringInstanceKeys = new Map();
const registeredExtractionRequests = new Map();
const naturalTaskRequests = new Map();
let naturalTaskExtraction = null;
const naturalTaskRecoveryPrefix="sim2act.pb-natural-extraction-recovery.v1:";
const naturalTaskRecoveryMetadata=new WeakMap();
const naturalTaskCloseConsent="CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY";
const naturalTaskTerminalNamespace="pb-natural-spec-extraction-terminal.v1";
const naturalTaskRecoveryFields=["namespace","principal_id","project_id","source_app_id","source_instance_id","source_run_id","source_app_run_id","source_release_id","source_release_fingerprint","source_result_version","request_key","request_fingerprint","review_fingerprint","candidate_fingerprint","app_id","runtime_id","source_proof_fingerprint"].sort();
function naturalTaskRecoveryScope(s){return {principal_id:s.instance.principal_id,project_id:s.view.project,source_app_id:s.view.app,source_instance_id:s.instance.id,source_run_id:s.rid};}
function naturalTaskRecoveryKey(s){return naturalTaskRecoveryPrefix+JSON.stringify(Object.values(naturalTaskRecoveryScope(s)));}
function naturalTaskRecoveryCheck(record,s){
  const ids={project_id:/^proj_[a-f0-9]{32}$/,source_app_id:/^app_[a-f0-9]{32}$/,source_instance_id:/^iinstance_[a-f0-9]{32}$/,source_run_id:/^run_[a-f0-9]{32}$/,source_app_run_id:/^iapprun_[a-f0-9]{32}$/,source_release_id:/^irelease_[a-f0-9]{32}$/,app_id:/^app_[a-f0-9]{32}$/,runtime_id:/^appruntime_[a-f0-9]{32}$/};
  const hashes=["source_release_fingerprint","request_fingerprint","review_fingerprint","candidate_fingerprint","source_proof_fingerprint"];
  if(!record||typeof record!=="object"||Array.isArray(record)||Object.keys(record).sort().join()!==naturalTaskRecoveryFields.join()||record.namespace!=="pb-natural-extraction-recovery.v1"||Object.entries(naturalTaskRecoveryScope(s)).some(([key,value])=>record[key]!==value)||Object.entries(ids).some(([key,re])=>typeof record[key]!=="string"||!re.test(record[key]))||hashes.some(key=>typeof record[key]!=="string"||!/^[a-f0-9]{64}$/.test(record[key]))||typeof record.request_key!=="string"||!/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(record.request_key)||!Number.isSafeInteger(record.source_result_version)||record.source_result_version<1||record.app_id===record.source_app_id||record.runtime_id===s.view.draft.runtime_id)throw Error("RECOVERY_RECORD_INVALID");
  return record;
}
function naturalTaskRecoveryRead(s){
  let raw;try{raw=localStorage.getItem(naturalTaskRecoveryKey(s));}catch{throw Error("RECOVERY_STORAGE_UNAVAILABLE");}
  if(raw===null)return null;
  if(typeof raw!=="string"||raw.length>8192)throw Error("RECOVERY_RECORD_INVALID");
  let record;try{record=JSON.parse(raw);}catch{throw Error("RECOVERY_RECORD_INVALID");}
  return {raw,record:naturalTaskRecoveryCheck(record,s)};
}
function naturalTaskRecoveryRefresh(s){
  s.recoveryError=null;
  try{
    if(!navigator.locks?.request)throw Error("RECOVERY_LOCK_UNAVAILABLE");
    const saved=naturalTaskRecoveryRead(s),pending=naturalTaskRequests.get(s.scope),metadata=pending&&naturalTaskRecoveryMetadata.get(pending);
    if(!saved){if(pending&&metadata?.key!==naturalTaskRecoveryKey(s))throw Error("RECOVERY_RECORD_CONFLICT");return pending||null;}
    if(metadata?.key===naturalTaskRecoveryKey(s)&&metadata.raw===saved.raw)return pending;
    const restored={};
    naturalTaskRecoveryMetadata.set(restored,{...saved,key:naturalTaskRecoveryKey(s)});
    naturalTaskRequests.set(s.scope,restored);
    s.edit++;s.review=null;s.saved=null;s.ack.checked=false;s.proof.textContent="";
    s.status.textContent="已发现原提取意图；请明确按原 key GET 核对，不会重发或生成新 key。";
    return restored;
  }catch(error){s.recoveryError=error.message;return naturalTaskRequests.get(s.scope)||null;}
}
function naturalTaskRecoverySource(s,record){
  const proof=s.source?.source_proof;
  if(!proof||record.source_app_id!==proof.source_app_id||record.source_instance_id!==proof.instance_id||record.source_run_id!==proof.source_run_id||record.source_app_run_id!==proof.app_run_id||record.source_release_id!==proof.release_id||record.source_release_fingerprint!==proof.release_fingerprint||record.source_result_version!==proof.result_version||record.source_proof_fingerprint!==s.source.source_proof_fingerprint)throw Error("VERSION_CONFLICT");
}
function naturalTaskRecoverySave(s,pending,record){
  if(naturalTaskRecoveryRead(s))throw Error("RECOVERY_RECORD_CONFLICT");
  const key=naturalTaskRecoveryKey(s),raw=JSON.stringify(naturalTaskRecoveryCheck(record,s));
  try{localStorage.setItem(key,raw);if(localStorage.getItem(key)!==raw)throw Error();}
  catch{throw Error("RECOVERY_STORAGE_UNAVAILABLE");}
  naturalTaskRecoveryMetadata.set(pending,{key,raw,record});naturalTaskRequests.set(s.scope,pending);
}
function naturalTaskRecoveryForget(s,pending,lock){
  const metadata=naturalTaskRecoveryMetadata.get(pending),saved=naturalTaskRecoveryRead(s),key=naturalTaskRecoveryKey(s);
  // Forget only after the original accepted app or permanent closure is proved.
  if(!lock||lock.name!==key||lock.mode!=="exclusive"||!naturalTaskCurrent(s)||naturalTaskRequests.get(s.scope)!==pending||!metadata||metadata.key!==key||(saved&&saved.raw!==metadata.raw))throw Error("RECOVERY_RECORD_CONFLICT");
  if(saved){try{localStorage.removeItem(key);if(localStorage.getItem(key)!==null)throw Error();}catch{throw Error("RECOVERY_STORAGE_UNAVAILABLE");}}
  if(naturalTaskRequests.get(s.scope)===pending)naturalTaskRequests.delete(s.scope);
}
async function naturalTaskTerminalProof(s,pending,value,current){
  const metadata=naturalTaskRecoveryMetadata.get(pending),record=metadata?.record;
  const valid=()=>{
    if(!current()||naturalTaskRequests.get(s.scope)!==pending)return false;
    const saved=naturalTaskRecoveryRead(s);
    if(!metadata||naturalTaskRecoveryMetadata.get(pending)!==metadata||metadata.key!==naturalTaskRecoveryKey(s)||(saved&&saved.raw!==metadata.raw))throw Error("RECOVERY_RECORD_CONFLICT");
    naturalTaskRecoverySource(s,record);return true;
  };
  if(!valid())return false;
  const fields="namespace status acceptance principal_id project_id source_run_id request_key identity request_fingerprint close_request_fingerprint new_model_requests project_writes metadata_writes formal_publication_enabled receipt_fingerprint".split(" ").sort();
  if(!value||Object.keys(value).sort().join()!==fields.join()||value.namespace!==naturalTaskTerminalNamespace||value.status!=="CLOSED_NOT_ACCEPTED"||value.acceptance!=="NOT_ACCEPTED"||value.principal_id!==record.principal_id||value.project_id!==record.project_id||value.source_run_id!==record.source_run_id||value.request_key!==record.request_key||goalRunCanonical(value.identity)!==goalRunCanonical(record)||value.request_fingerprint!==record.request_fingerprint||value.new_model_requests!==0||value.project_writes!==0||value.metadata_writes!==2||value.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
  const closeHash=await paHash({identity:record,consent:naturalTaskCloseConsent});if(!valid())return false;
  const {receipt_fingerprint,...receipt}=value,receiptHash=await paHash(receipt);if(!valid())return false;
  if(value.close_request_fingerprint!==closeHash||receipt_fingerprint!==receiptHash)throw Error("VERSION_CONFLICT");
  return true;
}
window.addEventListener("storage",event=>{
  const s=naturalTaskExtraction;
  if(!s||!s.source||!naturalTaskCurrent(s)||!(event.key===null||event.key===naturalTaskRecoveryKey(s)))return;
  naturalTaskRecoveryRefresh(s);naturalTaskButtons(s);
  s.status.textContent=s.recoveryError||"原意图记录已变化；只可明确读取原 key，不会自动提交。";
});
let registeredExtraction = null, registeredExtractionGeneration = 0;
let registeredExtractionEditGeneration = 0;
for(const id of ["registered-extraction-target","registered-extraction-name"]){
  $(id).addEventListener("input",()=>{registeredExtractionEditGeneration++;});
  $(id).addEventListener("change",()=>{registeredExtractionEditGeneration++;});
}
function engineeringCurrent(view) {
  return engineering === view && view.token === token && view.project === $("project-select").value && view.app === activeApp && view.appGeneration === appSelectionGeneration && (!view.selectionCurrent || view.selectionCurrent());
}
function engineeringStatus(view,text,state="") {
  if(!engineeringCurrent(view))return;
  $("internal-status").textContent=text;$("internal-status").dataset.state=state;
}
function clearInternalRunReread(view=engineering) {
  if(view?.runReread && engineeringCurrent(view)){$("internal-run-detail").textContent="";$("internal-run-status").textContent="";engineeringStatus(view,"");}
  if(view)view.runReread=null;
  $("internal-run-reread")?.remove();
}
function offerInternalRunReread(view,instance,run,connection,workspace) {
  clearInternalRunReread(view);
  const target={principal:instance.principal_id,project:view.project,app:view.app,
    instance:instance.id,run:run.id,appRun:run.app_run_id,connection,workspace,
    selection:view.instanceGeneration,runSelection:view.runGeneration,busy:false};
  view.runReread=target;
  const current=()=>engineeringCurrent(view) && view.runReread===target
    && target.connection===identityConnectionGeneration && target.workspace===workspaceSelectionGeneration
    && target.selection===view.instanceGeneration && target.runSelection===view.runGeneration;
  const button=document.createElement("button");button.id="internal-run-reread";
  button.type="button";button.textContent="重新读取这个原任务";
  button.onclick=async()=>{
    if(!current()||target.busy)return;
    target.busy=true;button.disabled=true;$("internal-run-detail").textContent="";$("internal-run-status").textContent="";
    engineeringStatus(view,`正在重新鉴权并读取原任务 ${target.run}…`,"loading");
    try {
      const fresh=await api(`/api/internal/instances/${encodeURIComponent(target.instance)}`);
      if(!current())return;
      if(fresh.id!==target.instance || fresh.principal_id!==target.principal
        || fresh.project_id!==target.project || fresh.source_app_id!==target.app)throw Error("运行绑定与当前身份不符");
      const latest=await api(`/api/internal/instances/${encodeURIComponent(target.instance)}/runs/${encodeURIComponent(target.run)}`);
      if(!current())return;
      if(latest.id!==target.run || latest.instance_id!==target.instance || latest.app_run_id!==target.appRun)throw Error("运行绑定与当前身份不符");
      $("internal-run-detail").textContent=JSON.stringify(latest,null,2);
      $("internal-run-status").textContent=`原任务 ${latest.id}：${latest.status} · 取消意图 ${latest.cancel_intent ? "已保留" : "无"}`;
      engineeringStatus(view,"已重新读取这个原任务的当前状态。","success");
    } catch(error){if(current()){$("internal-run-detail").textContent="";engineeringStatus(view,error.message,"error");}}
    finally {if(current()){target.busy=false;button.disabled=false;}}
  };
  $("internal-controls").append(button);
}
function clearInternal() {
  clearInternalRunReread();
  if(typeof clearNaturalLogic==="function")clearNaturalLogic();
  clearPBUse();
  clearNaturalTaskExtraction();
  if(typeof clearOwnerReview==="function")clearOwnerReview();
  clearRegisteredExtraction();
  if(engineering)clearSwitch(engineering);
  $("internal-switch").hidden=true;$("internal-switch-history").replaceChildren();
  engineeringGeneration++;engineering=null;
  $("internal-panel").hidden=true;$("internal-approval").hidden=true;$("internal-approval-detail").textContent="";$("internal-approval-ack").checked=false;
  $("internal-status").textContent="";$("internal-agent").hidden=true;$("internal-replay-file").value="";$("internal-replay-status").textContent="";$("internal-term").value="";$("internal-term").disabled=true;refreshTextTerm($("internal-term"),true);
  for(const id of ["internal-releases","internal-instances","internal-runs","internal-data","internal-controls"] )$(id).replaceChildren();
  $("internal-run-form").hidden=true;$("internal-retry").hidden=true;$("internal-new-intent").hidden=true;$("internal-run-detail").textContent="";$("internal-run-status").textContent="";$("internal-instance-info").textContent="";
}
function switchAllowed(view,targetId) {
  const i=view.instance,p=i?.switch_policy;
  return !!targetId && p?.namespace==="internal.logic-switch-policy.v1" && p.instance_id===i.id
    && p.revision===i.revision && Array.isArray(p.blocked_release_ids) && !p.blocked_release_ids.includes(targetId);
}
function engineeringButtons(view) {
  if(!engineeringCurrent(view))return;
  const switchExpired=view.switchApproval && view.switchApproval.expires_at*1000<=Date.now();
  $("internal-switch-prepare").disabled=!!view.busy || !view.instance || !switchAllowed(view,$("internal-switch-target").value);
  $("internal-switch-target").disabled=!!view.busy;
  $("internal-switch-commit").disabled=!!view.busy || !view.instance || !view.switchApproval || !switchAllowed(view,view.switchApproval.payload?.target_release_id) || switchExpired || !$("internal-switch-ack").checked;
  if(switchExpired)$("internal-switch-status").textContent="批准已到期，请重新核查；不会自动重发确认。";
  const missingReplay=view.agent && (!view.offlineReplay || !$("app-agent-term").value.trim());
  const approvalExpired=view.approval && view.approval.expires_at*1000<=Date.now();
  $("internal-prepare").disabled=!!view.busy || missingReplay;
  $("internal-refresh").disabled=!!view.busy;
  $("internal-commit").disabled=!!view.busy || !view.approval || approvalExpired || !$("internal-approval-ack").checked;
  if(approvalExpired)engineeringStatus(view,"批准已到期，请重新核查；不会自动确认。","error");
  $("internal-run-submit").disabled=!!view.busy || !!view.recoveryError || !view.instance || engineeringPending.has(view.instance.id) || pbUseUnknown(view.instance.id) || (view.agent && (!view.offlineReplay || !$("internal-term").value.trim()));
  $("internal-retry").hidden=!view.instance || !engineeringPending.has(view.instance.id);
  $("internal-retry").disabled=!!view.busy || !!view.recoveryError;
  $("internal-retry").textContent=view.spec ? "仅用原请求键读取运行回执" : "恢复原请求回执";
  $("internal-new-intent").hidden=view.spec || $("internal-retry").hidden;$("internal-new-intent").disabled=!!view.busy;
  renderNaturalFirstGuide();
}
async function engineeringAction(view,fn) {
  if(!view || !engineeringCurrent(view) || view.busy)return;
  const selection=view.instanceGeneration,connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
  view.busy=true;engineeringButtons(view);
  try {await fn();}
  catch(error){if(engineeringCurrent(view) && selection===view.instanceGeneration && connection===identityConnectionGeneration && workspace===workspaceSelectionGeneration){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message==="RECOVERY_REQUEST_BUSY"?"另一个页面正在处理此实例。本次没有排队提交；请稍后手动刷新或读取原请求回执。":error.message,"error");}}
  finally {view.busy=false;engineeringButtons(view);}
}
async function openInternal(app,appGeneration,selectionCurrent=null) {
  const view={app:app.id,project:app.project_id,token,appGeneration,selectionCurrent,generation:++engineeringGeneration,draft:app,busy:false,approval:null,instance:null,run:null,instanceGeneration:0,runGeneration:0,releases:[],switchGeneration:0,switchApproval:null,agent:app.input_guidance.mode === "OFFLINE_REPLAY_ONLY",literal:app.input_guidance.mode === "REGISTERED_LITERAL",spec:app.input_guidance.mode === "MODEL_SPEC_CHECKLIST",offlineReplay:null,inputGeneration:0,workflow:app.input_guidance.mode === "CLOSED_TEXT_WORKFLOW"};
  engineering=view;$("apps").append($("internal-panel"));$("internal-panel").hidden=false;
  $("internal-title").textContent="内部版本与实例 · 只读运行";
  $("internal-agent").hidden=!view.agent;
  $("internal-replay-status").textContent=view.agent ? "尚未加载离线响应；审批与新运行暂不可提交。" : "";
  $("internal-prepare-hint").textContent=view.agent ? "使用上方样例字面检索词与已加载的离线响应核查当前材料。先查看精确快照，再手动确认保存内部版本；语义仍为 UNKNOWN。" : "使用当前选定数值列重新核查固定可信计算；先查看精确快照，再确认保存。仅内部版本，不是正式发布。";
  if(view.spec)$("internal-prepare-hint").textContent="先预览引用和有限模型步骤图；确认内部版本后，后台逐步核验并在一个事务中保存本项目 JSON 清单。语义完整性 NOT_RUN。";
  if(view.literal)$("internal-prepare-hint").textContent="用上方检索词独立核查完整匹配行；精确确认后保存内部版本。新实例直接输入新词，无需 Replay。语义 UNKNOWN。";
  if(view.workflow){$("internal-prepare-hint").textContent="用两次独立检索和报告分支核查完整引用，再确认精确内部快照。后台每步独立留存回执；owner PENDING、语义 UNKNOWN。";}
  engineeringButtons(view);engineeringStatus(view,"正在读取内部版本与实例…","loading");
  if(typeof openAppOwnGoal === "function")await openAppOwnGoal(view);
  try {await refreshInternal(view);}
  catch(error){if(engineeringCurrent(view)){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");$("internal-releases").replaceChildren();$("internal-instances").replaceChildren();}}
}
async function refreshInternal(view=engineering) {
  if(!view || !engineeringCurrent(view))return;
  clearInternalRunReread(view);
  const workspace=workspaceSelectionGeneration,connection=identityConnectionGeneration,generation=(view.historyGeneration||0)+1;
  view.historyGeneration=generation;
  view.historyReady=false;
  const current=()=>engineeringCurrent(view)&&workspace===workspaceSelectionGeneration&&connection===identityConnectionGeneration&&generation===view.historyGeneration;
  const latest=await api(`/api/apps/${view.app}`);
  if(!current())return;
  if(latest.project_id!==view.project || latest.fingerprint!==view.draft.fingerprint)throw Error("VERSION_CONFLICT");
  const [releases,instances]=await Promise.all([api(`/api/internal/apps/${view.app}/releases`),api(`/api/internal/apps/${view.app}/instances`)]);
  if(!current())return;
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
    if(engineeringCurrent(view) && view.instance?.id===created.id){engineeringInstanceKeys.delete(release.id);naturalFirstInstanceCreated(view,created);engineeringStatus(view,"已创建独立内部实例；结果和后台状态可重新读取。");}
  }),"创建独立实例")));
  $("internal-instances").replaceChildren(...instances.items.map(instance=>row(`${instance.id} · 版本 ${instance.revision} · 结果版本 ${instance.data_version}`,()=>showInternalInstance(instance.id,view),"打开 / 重开")));
  if(!releases.items.length)$("internal-releases").textContent="尚无内部 Release。先核查并查看精确快照。";
  if(!instances.items.length)$("internal-instances").textContent="尚无实例。内部 Release 已保存后可创建。";
  view.historyReady=true;
  engineeringStatus(view,"内部历史已读回；正式发布与部署仍关闭。");
}
async function showInternalInstance(id,view=engineering) {
  if(naturalUsePreparation && (!naturalUsePreparation.returning || !naturalUsePreparation.instance || naturalUsePreparation.instance.id!==id || naturalUsePreparation.view!==view))clearNaturalUsePreparation();
  if(typeof clearNaturalLogic==="function")clearNaturalLogic();
  clearPBUse();
  clearNaturalTaskExtraction();
  if(!view || !engineeringCurrent(view))return;
  clearInternalRunReread(view);
  if(typeof clearOwnerReview==="function")clearOwnerReview();
  clearRegisteredExtraction();
  clearSwitch(view);$("internal-switch").hidden=true;
  const selection=++view.instanceGeneration,connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
  const current=()=>engineeringCurrent(view)&&selection===view.instanceGeneration&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration;
  view.runGeneration++;view.instance=null;view.run=null;
  $("internal-run-form").hidden=true;$("internal-controls").replaceChildren();$("internal-run-detail").textContent="";$("internal-run-status").textContent="正在读取实例…";$("internal-data").replaceChildren();$("internal-runs").replaceChildren();engineeringButtons(view);
  try {
    const instance=await api(`/api/internal/instances/${id}`);
    if(!current())return;
    if(instance.source_app_id!==view.app || instance.project_id!==view.project)throw Error("实例来源与当前选择不符");
    const resultManifests=(view.agent||view.literal)?await internalResultManifests(instance,view,current):null;
    if(!current())return;
    view.instance=instance;if(view.spec)specRecoveryRefresh(view,instance);renderSwitch(view);$("internal-instance-title").textContent=`内部实例 ${id}`;
    $("internal-instance-info").textContent=`Release ${instance.release_id} · revision ${instance.revision} · 独立结果版本 ${instance.data_version} · 正式部署关闭`;
    $("internal-column-label").hidden=view.agent||view.literal||view.workflow||view.spec;$("internal-column").required=!(view.agent||view.literal||view.workflow||view.spec);$("internal-term-label").hidden=!(view.agent||view.literal);$("internal-term").required=view.agent||view.literal;$("internal-term").disabled=!(view.agent||view.literal);refreshTextTerm($("internal-term"));
    $("internal-column").replaceChildren(...Array.from($("app-column").options).map(o=>{const option=new Option(o.textContent,o.value);option.disabled=o.disabled;return option;}));
    if(typeof showTextWorkflowInputs === "function")showTextWorkflowInputs("internal",!!view.workflow);
    $("internal-run-form").hidden=false;
    $("internal-data").replaceChildren(...instance.data.map(record=>internalResult(record,view,resultManifests?.get(record.release_id))));
    $("internal-runs").replaceChildren(...instance.runs.map(run=>row(`${run.status} · ${run.id} · 结果版本 ${run.result_version ?? "无"}`,()=>showInternalRun(run.id,view,instance),"读取后台任务")));
    $("internal-run-status").textContent=engineeringPending.has(id) ? "上次提交回执未确认，可用原请求键恢复；不会自动重发。" : (view.agent ? "加载对应离线响应并填写本次检索词；后台核查真实授权材料，不调用provider。关闭页面不会取消任务。" : "选择数值列，提交后台只读计算；关闭页面不会取消已接受任务。");
    if(view.workflow)$("internal-run-status").textContent="填写两次独立检索词，明确选择报告分支。报告未选时保留 PARTIAL 与三步回执；只用原请求 key 读取未知结果。";
    if(view.literal)$("internal-run-status").textContent="输入本次检索词，后台重新读取并独立核查全部匹配行；关闭页面不会取消任务。";
    if(view.spec)$("internal-run-status").textContent=engineeringPending.has(id) ? "本次提交结果尚未确认。仅用原请求键读取回执；不会重发或开始重复运行。" : "运行已保存材料与目标，完成后可读取此版本清单或下载成果。自然规范模型默认关闭；出处核验不代表语义验收。";
    if(view.spec&&view.recoveryError)$("internal-run-status").textContent=`${view.recoveryError}：无法安全保存或读取原请求恢复信息，未提交运行。请检查浏览器存储能力后手动刷新。`;
    // One fresh response for this exact selection, discarded after rendering.
    // Both consumers keep their own scope/hash checks; no cross-refresh cache.
    let selectedRelease=null;
    if(view.draft.candidate.namespace==="pa-natural-spec-app.v1"){
      selectedRelease=await api(`/api/internal/releases/${instance.release_id}`);
      if(!current())return;
      if(selectedRelease.id!==instance.release_id||selectedRelease.fingerprint!==instance.release_fingerprint)throw Error("VERSION_CONFLICT");
    }
    await renderPBUse(view,selectedRelease);if(!current())return;
    if(typeof openNaturalLogic==="function")await openNaturalLogic(view,selectedRelease);
    if(!current())return;
    if(typeof openOwnerReview==="function")await openOwnerReview(view);
  } catch(error){if(current()){invalidateInternalContent(view);$("internal-instance-info").textContent="";$("internal-run-status").textContent=error.message;engineeringStatus(view,error.message,"error");return {permissionDenied:["PERMISSION_DENIED","GRANT_REVOKED"].includes(error.message),instanceId:id,failedSelection:selection,instanceGeneration:view.instanceGeneration,runGeneration:view.runGeneration};}}
  if(current())engineeringButtons(view);
}
async function showKnownInternalRunStop(scope){
  // Entered only from a verified accepted receipt after its own instance read
  // lost content access. Keep opaque IDs, never restore a cached instance.
  const identity=token,connection=identityConnectionGeneration,project=$("project-select").value;
  clearApp();selectWorkspace("projects");clearRunDetail();activeRun=null;
  const workspace=workspaceSelectionGeneration,selection=++runUserSelectionGeneration;runSelectionGeneration++;
  const panel=document.createElement("section"),title=document.createElement("p"),status=document.createElement("p"),read=document.createElement("button"),cancel=document.createElement("button");
  panel.id="known-internal-stop";title.textContent=`已受理修正Run ${scope.rid} · 实例 ${scope.iid}；当前内容不可读，仅保留本人停止控制。`;
  read.type=cancel.type="button";read.id="known-internal-stop-read";cancel.id="known-internal-stop-cancel";read.textContent="读取此Run的停止状态";cancel.textContent="取消此修正Run";cancel.disabled=true;
  status.id="known-internal-stop-status";status.setAttribute("role","status");panel.append(title,status,read,cancel);$("result").append(panel);
  const current=()=>panel.isConnected&&identity===token&&connection===identityConnectionGeneration&&project===$("project-select").value&&workspace===workspaceSelectionGeneration&&selection===runUserSelectionGeneration&&activeRun===null;
  const observer=new MutationObserver(()=>{
    if(current())return;
    if(panel.isConnected){read.disabled=cancel.disabled=true;status.textContent="当前任务选择或工作区已变化，此停止入口已失效；请从原回执重新打开。";}
    observer.disconnect();
  });
  observer.observe($("projects"),{attributes:true,attributeFilter:["hidden"]});observer.observe($("result"),{childList:true});
  const path=`/api/internal/instances/${encodeURIComponent(scope.iid)}/runs/${encodeURIComponent(scope.rid)}`;
  const statuses=["QUEUED","RUNNING","WAITING_APPROVAL","WAITING_RESOURCE","RECONCILING","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","SUCCEEDED","PARTIAL","FAILED","CANCELLED"];
  let busy=false,state=null;
  const buttons=()=>{if(!current())return;read.disabled=busy;cancel.disabled=busy||!state||!["QUEUED","RUNNING","PAUSED","WAITING_RESOURCE","PAUSE_REQUESTED","RECONCILING"].includes(state.status)||state.cancel_intent;};
  const readState=async()=>{
    const value=await api(path+"/control-status");if(!current())return;
    if(value.namespace!=="INTERNAL_ENGINEERING_ONLY"||value.id!==scope.rid||value.instance_id!==scope.iid||value.content_access!==false||value.formal_publication_enabled!==false||!Number.isSafeInteger(value.version)||value.version<1||typeof value.cancel_intent!=="boolean"||!statuses.includes(value.status)||Object.keys(value).some(k=>!["namespace","id","instance_id","status","version","cancel_intent","content_access","formal_publication_enabled"].includes(k)))throw Error("停止状态绑定不一致");
    state=value;status.textContent=`原Run ${value.id} · ${value.status} · 取消意图 ${value.cancel_intent?"已保留":"无"}；不读取材料或成果。`;
  };
  read.onclick=safe(async()=>{if(!current()||busy)return;busy=true;state=null;buttons();try{await readState();}catch(error){if(current())status.textContent=`停止状态未确认：${error.message}；请明确重新读取，不会重发取消。`;}finally{busy=false;buttons();}});
  cancel.onclick=safe(async()=>{
    if(!current()||busy||cancel.disabled||!state)return;
    const version=state.version;busy=true;state=null;buttons();
    try{
      const saved=await api(path+"/commands","POST",{command:"cancel",version});if(!current())return;
      if(saved.namespace!=="INTERNAL_ENGINEERING_ONLY"||saved.formal_publication_enabled!==false||!statuses.includes(saved.status))throw Error("取消回执绑定不一致");
      status.textContent=`已受理原Run ${scope.rid} 的取消：${saved.status}。`;
      try{await readState();}catch(error){if(current())status.textContent+=` 当前停止状态回读未确认：${error.message}；仅明确读取，不会重发取消。`;}
    }catch(error){if(current())status.textContent=`取消结果未确认：${error.message}；仅明确读取当前停止状态，不会自动重发。`;}
    finally{busy=false;buttons();}
  });
  await read.onclick();
}
async function showInternalRun(id,view=engineering,instance=view?.instance) {
  if(!instance || !engineeringCurrent(view) || view.instance?.id!==instance.id)return;
  clearNaturalTaskExtraction();
  clearInternalRunReread(view);
  const previousStatus=view.run?.status;
  const selection=++view.runGeneration,iSelection=view.instanceGeneration,connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
  $("internal-controls").replaceChildren();$("internal-run-detail").textContent="";view.run=null;
  const selectedCurrent=()=>engineeringCurrent(view) && selection===view.runGeneration && iSelection===view.instanceGeneration && view.instance?.id===instance.id && connection===identityConnectionGeneration;
  const current=()=>selectedCurrent() && workspace===workspaceSelectionGeneration;
  if((view.spec||view.workflow)&&typeof selectOwnerRun==="function"&&ownerView?.rid!==id)await selectOwnerRun("",view);
  if(!current())return;
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
        const actionWorkspace=workspaceSelectionGeneration;
        const actionCurrent=()=>selectedCurrent() && actionWorkspace===workspaceSelectionGeneration;
        if(!actionCurrent())return;
        let response;
        try {response=await api(`/api/internal/instances/${instance.id}/runs/${id}/commands`,"POST",{command,version:run.version});}
        catch(error){
          if(!actionCurrent())return;
          if(error.message!=="VERSION_CONFLICT")throw error;
          invalidateInternalContent(view);
          offerInternalRunReread(view,instance,run,connection,actionWorkspace);
          engineeringStatus(view,"VERSION_CONFLICT：任务状态已变化，可重新读取这个原任务。","error");
          return;
        }
        if(!actionCurrent())return;
        // The accepted stop receipt remains visible even if current grants prevent GET afterward.
        $("internal-run-status").textContent=`已接受${button.textContent}：${response.status}`;$("internal-controls").replaceChildren();view.run=null;
        try {await showInternalRun(id,view,instance);}catch(error){engineeringStatus(view,error.message,"error");}
      });return button;
    }));
    if(run.content_access!==false && previousStatus && previousStatus!==run.status && ["SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(run.status)){
      await showInternalInstance(instance.id,view);
      if(engineeringCurrent(view) && view.instance?.id===instance.id)await showInternalRun(id,view,view.instance);
      return;
    }
    if(current()&&(view.spec||view.workflow)&&typeof selectOwnerRun==="function")await selectOwnerRun(run.status==="SUCCEEDED"&&(view.workflow||run.content_access!==false)?id:"",view);
  } catch(error){if(current()){if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT"].includes(error.message))invalidateInternalContent(view);engineeringStatus(view,error.message,"error");$("internal-run-status").textContent+=" · 无法读取当前详情";}}
}
async function submitInternal(view,retry=false) {
  const instance=view.instance;if(!instance)return;
  if(pbUseUnknown(instance.id))return;
  if(view.spec)return submitPersistentSpecRun(view,instance,retry);
  let pending=engineeringPending.get(instance.id);
  if(!pending&&!retry&&!textTermsReady($("internal-run-form"),true))return;
  if(!pending && !retry){pending={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,input:view.spec ? {} : view.workflow ? textWorkflowInput("internal") : (view.agent||view.literal) ? {term:$("internal-term").value} : {column:$("internal-column").value},...(view.agent ? {offline_replay:structuredClone(view.offlineReplay)} : {}),...(appOwnGoalCurrent(appOwnGoalView)&&appOwnGoalView.state?.current ? {expected_owner_goal_binding_fingerprint:appOwnGoalView.state.current.binding_fingerprint} : {}),request_key:crypto.randomUUID()};engineeringPending.set(instance.id,pending);}
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
async function internalSubmissionRejected(error,view,instance,pending,endpoint,body){
  const proof=error.submissionRejection;
  if(!Number.isInteger(error.httpStatus)||error.httpStatus<400||error.httpStatus>=500||!proof)return false;
  const fp=await paHash(body);
  return proof.namespace==="internal-run-rejection.v1"&&proof.endpoint===endpoint&&proof.principal_id===instance.principal_id&&proof.project_id===view.project&&proof.instance_id===instance.id&&proof.request_key===(["pb-use-runs","pa-use-runs"].includes(endpoint)?body.review.request_key:body.request_key)&&proof.request_fingerprint===fp&&proof.acceptance==="NOT_ACCEPTED"&&proof.previous_request==="ABSENT"&&["TX_ROLLED_BACK","VALIDATION_NOT_STARTED"].includes(proof.phase);
}
async function submitSpecRun(view,instance,pending,retry){
  const generation=view.instanceGeneration,workspace=workspaceSelectionGeneration,connection=identityConnectionGeneration;
  const current=()=>engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===generation&&workspaceSelectionGeneration===workspace&&connection===identityConnectionGeneration&&engineeringPending.get(instance.id)===pending;
  $("internal-run-status").textContent=retry ? "正在仅用原请求键读取回执…" : "正在提交已保存规范的后台运行…";
  let accepted=null;
  if(!retry){
    try{accepted=await api(`/api/internal/instances/${instance.id}/runs`,"POST",pending);}
    catch(error){
      if(await internalSubmissionRejected(error,view,instance,pending,"runs",pending)&&engineeringPending.get(instance.id)===pending){
        if(!current())return;
        // The transient proof is not a fence. Persist owner-authorized closure,
        // then authenticate the original-key GET before clearing either cache.
        // A lost close response leaves UNKNOWN; subsequent recovery is GET only.
        await api(`/api/internal/instances/${instance.id}/spec-run-requests/${encodeURIComponent(pending.request_key)}/close`,"POST",{release_id:specRecoveryMetadata.get(pending)?.record.release_id,request:pending});
      }else{
        throw error;
      }
    }
    if(!current())return;
  }
  const receipt=await api(`/api/internal/instances/${instance.id}/spec-run-requests/${encodeURIComponent(pending.request_key)}`);
  if(!current())return;
  if(receipt.namespace==="spec-run-terminal.v1"){
    const wireHash=await paHash(pending);
    if(!current())return;
    if(accepted||receipt.status!=="CLOSED_NOT_ACCEPTED"||receipt.principal_id!==instance.principal_id||receipt.project_id!==view.project||receipt.app_id!==view.app||receipt.instance_id!==instance.id||receipt.release_id!==specRecoveryMetadata.get(pending)?.record.release_id||receipt.request_key!==pending.request_key||receipt.wire_request_fingerprint!==wireHash||goalRunCanonical(receipt.request)!==goalRunCanonical(pending)||receipt.new_model_requests!==0||receipt.project_writes!==0||receipt.run_id!==undefined||receipt.app_run_id!==undefined)throw Error("VERSION_CONFLICT");
    specRecoveryForget(view,instance,pending);
    $("internal-run-status").textContent="原请求键已由服务端永久关闭且未受理；请刷新版本后手动重新运行。关闭仅写恢复元数据。";
    engineeringButtons(view);return;
  }
  const expected={instance_id:instance.id,expected_revision:pending.expected_revision,expected_release_fp:pending.expected_release_fingerprint,input:pending.input};
  if(pending.expected_owner_goal_binding_fingerprint!==undefined)expected.owner_goal_binding_fingerprint=pending.expected_owner_goal_binding_fingerprint;
  const requestHash=await paHash(expected);
  if(!current())return;
  if(receipt.namespace!=="spec-run-request.v1"||receipt.principal_id!==instance.principal_id||receipt.project_id!==view.project||receipt.app_id!==view.app||receipt.instance_id!==instance.id||receipt.release_id!==specRecoveryMetadata.get(pending)?.record.release_id||receipt.request_key!==pending.request_key||receipt.request_fingerprint!==requestHash||goalRunCanonical(receipt.request)!==goalRunCanonical(pending)||!/^run_[a-f0-9]{32}$/.test(receipt.run_id)||!/^iapprun_[a-f0-9]{32}$/.test(receipt.app_run_id)||receipt.new_model_requests!==0||receipt.project_writes!==0||(accepted&&(accepted.run_id!==receipt.run_id||accepted.app_run_id!==receipt.app_run_id)))throw Error("VERSION_CONFLICT");
  specRecoveryForget(view,instance,pending);
  $("internal-run-status").textContent=`已核对原请求 ${pending.request_key} · ${receipt.status}；回执读取没有重新执行。`;
  await showInternalInstance(instance.id,view);
  if(engineeringCurrent(view)&&view.instance?.id===instance.id&&workspaceSelectionGeneration===workspace)await showInternalRun(receipt.run_id,view,view.instance);
}
async function submitPersistentSpecRun(view,instance,retry){
  const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration,selection=view.instanceGeneration;
  const current=()=>engineeringCurrent(view)&&view.instance===instance&&selection===view.instanceGeneration&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration;
  if(!navigator.locks?.request)throw Error("RECOVERY_LOCK_UNAVAILABLE");
  return navigator.locks.request(specRecoveryKey(view,instance),{mode:"exclusive",ifAvailable:true},async lock=>{
    if(!current())return;
    if(!lock)throw Error("RECOVERY_REQUEST_BUSY");
    let pending=specRecoveryRestore(view,instance);view.recoveryError=null;
    const recovering=!!pending;
    if(!pending&&!retry){
      pending={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,input:{},request_key:crypto.randomUUID(),...(appOwnGoalCurrent(appOwnGoalView)&&appOwnGoalView.state?.current?{expected_owner_goal_binding_fingerprint:appOwnGoalView.state.current.binding_fingerprint}:{})};
      specRecoverySave(view,instance,pending);
    }
    if(!pending)return;
    // Any durable intent, including OUTCOME_UNKNOWN, is read-only on subsequent actions.
    return submitSpecRun(view,instance,pending,retry||recovering);
  });
}
$("internal-prepare").onclick=()=>{if(!textTermsReady($("app-preview-form"),true))return;return engineeringAction(engineering,async()=>{
  const view=engineering;view.approval=null;$("internal-approval").hidden=true;$("internal-approval-ack").checked=false;
  const inputGeneration=view.inputGeneration;
  const current=()=>engineeringCurrent(view) && inputGeneration===view.inputGeneration;
  const sample=view.spec ? {} : view.workflow ? {...textWorkflowInput("app"),emit_report:true} : (view.agent||view.literal) ? {term:$("app-agent-term").value} : {column:$("app-column").value};
  const prepared=await api(`/api/internal/apps/${view.app}/release-approvals`,"POST",{expected_draft_fingerprint:view.draft.fingerprint,sample_input:sample,...(view.agent ? {offline_replay:structuredClone(view.offlineReplay)} : {})});
  if(!current())return;
  const detail=await api(`/api/internal/approvals/${prepared.id}`);
  if(!current())return;
  if(detail.fingerprint!==prepared.fingerprint)throw Error("批准指纹不一致");
  view.approval=detail;$("internal-approval").hidden=false;$("internal-approval-label").textContent=`内部批准 ${detail.id} · 到期 ${new Date(detail.expires_at*1000).toLocaleString()} · ${detail.fingerprint}`;
  $("internal-approval-detail").textContent=JSON.stringify(detail.payload,null,2);engineeringStatus(view,"请检查精确冻结快照，勾选确认后保存内部 Release。");
  renderNaturalFirstGuide();
});};
$("internal-approval-ack").onchange=()=>{if(engineering)engineeringButtons(engineering);};
$("internal-commit").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,approval=view.approval;if(!approval || approval.expires_at*1000<=Date.now() || !$("internal-approval-ack").checked)return;
  const saved=await api(`/api/internal/approvals/${approval.id}/commit`,"POST",{fingerprint:approval.fingerprint});
  if(!engineeringCurrent(view))return;
  view.approval=null;$("internal-approval").hidden=true;$("internal-approval-ack").checked=false;await refreshInternal(view);if(!engineeringCurrent(view))return;naturalFirstReleaseSaved(view,saved);engineeringStatus(view,`已保存内部 Release ${saved.id}；正式发布关闭。`);
});
$("internal-refresh").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,id=view.instance?.id,run=view.run?.id,selection=view.instanceGeneration,workspace=workspaceSelectionGeneration,connection=identityConnectionGeneration;
  const current=()=>engineeringCurrent(view)&&workspace===workspaceSelectionGeneration&&connection===identityConnectionGeneration;
  await refreshInternal(view);
  if(id&&current()&&selection===view.instanceGeneration){
    await showInternalInstance(id,view);
    if(run&&current()&&view.instance?.id===id&&view.instanceGeneration===selection+1)await showInternalRun(run,view,view.instance);
  }
});
$("internal-back").onclick=()=>{clearInternal();};
$("internal-run-form").onsubmit=event=>{event.preventDefault();const view=engineering;return engineeringAction(view,()=>submitInternal(view));};
$("internal-new-intent").onclick=()=>{const view=engineering,id=view?.instance?.id;return engineeringAction(view,async()=>{
  if(view.spec)return;
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
  $("internal-switch-target").replaceChildren(new Option("请手动选择目标版本",""),...view.releases.filter(r=>r.id!==view.instance.release_id && switchAllowed(view,r.id)).map(r=>new Option(`${r.id} · schema v${r.snapshot.data_schema_version} · ${r.fingerprint.slice(0,16)}`,r.id)));
  if(view.instance.switch_policy?.roles?.length)$("internal-switch-status").textContent="该实例提供已保存版本的来源或检查证据，不能切换版本。请使用独立业务实例。";
  else if(view.instance.switch_policy?.blocked_release_ids?.some(id=>id!==view.instance.release_id))$("internal-switch-status").textContent="已排除存在来源循环或超出有限检查范围的目标版本。";
  $("internal-switch-history").replaceChildren(...view.instance.history.map(h=>row(`revision ${h.revision} · ${h.previous_release_id || "初始版本"} → ${h.release_id} · ${h.kind || "create"}`)));
}
$("internal-switch-target").onchange=()=>{const view=engineering;if(!view)return;const value=$("internal-switch-target").value;clearSwitch(view);$("internal-switch-target").value=value;engineeringButtons(view);};
$("internal-switch-ack").onchange=()=>{if(engineering)engineeringButtons(engineering);};
$("internal-switch-cancel").onclick=()=>{const view=engineering;if(!view)return;clearSwitch(view);$("internal-switch-status").textContent="已取消本页选择；已被服务接受的切换仍可能完成，请重新读取历史确认。";engineeringButtons(view);};
$("internal-switch-prepare").onclick=()=>engineeringAction(engineering,async()=>{
  const view=engineering,instance=view.instance,target=view.releases.find(r=>r.id===$("internal-switch-target").value);
  if(!instance || !target || !switchAllowed(view,target.id))return;
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
  if(!instance || !approval || !switchAllowed(view,approval.payload?.target_release_id) || !$("internal-switch-ack").checked || approval.expires_at*1000<=Date.now())return;
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
  clearInternalRunReread(view);
  clearNaturalTaskExtraction();
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
async function internalResultManifests(instance,view,current){
  const manifests=new Map(),invalid=()=>{throw Error("成果视图与原 Release 或 Run 绑定不一致");};
  for(const id of new Set(instance.data.map(record=>record.release_id))){
    if(typeof id!=="string"||!/^irelease_[a-f0-9]{32}$/.test(id))invalid();
    const release=await api(`/api/internal/releases/${encodeURIComponent(id)}`);if(!current())return null;
    const snapshot=release.snapshot,draft=snapshot?.draft,manifest=draft?.candidate?.manifest;
    if(release.namespace!=="INTERNAL_ENGINEERING_ONLY"||release.id!==id||release.principal_id!==instance.principal_id||release.project_id!==view.project||snapshot?.namespace!=="INTERNAL_ENGINEERING_ONLY"||draft?.id!==view.app||draft.project_id!==view.project||draft.runtime_id!==instance.runtime_id||manifest?.app_id!==view.app||!Array.isArray(manifest.views)||manifest.views.length>16||(id===instance.release_id&&release.fingerprint!==instance.release_fingerprint))invalid();
    const releaseHash=await ownerHash(snapshot);if(!current())return null;
    const candidateHash=await ownerHash(draft.candidate);if(!current())return null;
    if(releaseHash!==release.fingerprint||candidateHash!==draft.fingerprint)invalid();
    manifests.set(id,manifest);
  }
  for(const record of instance.data){
    const matches=instance.runs.filter(run=>run.app_run_id===record.run_id);
    if(record.instance_id!==instance.id||matches.length!==1)invalid();
    const run=matches[0];
    if(run.instance_id!==instance.id||run.release_id!==record.release_id||run.status!=="SUCCEEDED"||run.result_version!==record.version||!ownerSame(run.result,record.data?.result))invalid();
    const typedHash=await ownerHash(record.data);if(!current())return null;
    if(typedHash!==record.fingerprint)invalid();
  }
  return manifests;
}
function manifestTableShape(schema,value){
  const scalar=(v,t)=>t==="string"?typeof v==="string"&&v.length<=65536:t==="integer"?Number.isSafeInteger(v):t==="number"?typeof v==="number"&&Number.isFinite(v):t==="boolean"&&typeof v==="boolean";
  const item=schema?.items,columns=Object.keys(item?.properties||{}),types=columns.map(key=>item.properties[key]?.type);
  return schema?.type==="array"&&Number.isSafeInteger(schema.maxItems)&&schema.maxItems<=64&&schema.maxItems>=0&&item?.type==="object"&&item.additionalProperties===false&&columns.length>0&&columns.length<=16&&Array.isArray(item.required)&&item.required.length===columns.length&&columns.every(key=>item.required.includes(key))&&types.every(type=>["string","integer","number","boolean"].includes(type))&&Array.isArray(value)&&value.length<=schema.maxItems&&JSON.stringify(value).length<=262144&&value.every(entry=>entry&&typeof entry==="object"&&!Array.isArray(entry)&&Object.keys(entry).length===columns.length&&columns.every((key,index)=>Object.hasOwn(entry,key)&&scalar(entry[key],types[index])))?{columns,types}:null;
}
function tableBarValues(schema,rows,category,series){
  const shape=manifestTableShape(schema,rows),index=shape?.columns.indexOf(series);
  if(!shape||!category||!series||!shape.columns.includes(category)||index<0||!["integer","number"].includes(shape.types[index])||!rows.length)throw Error("请选择存在的类别列和数值系列；空表或非数值不能作图。");
  const values=rows.map(row=>row[series]);
  if(values.some(value=>!Number.isFinite(value)||Math.abs(value)>Number.MAX_SAFE_INTEGER))throw Error("数值超出安全展示范围；请查看原表格。");
  const min=Math.min(0,...values),max=Math.max(0,...values),span=max-min||1;
  const zero=200+(0-min)/span*420,positions=values.map(value=>200+(value-min)/span*420);
  if(!Number.isFinite(zero)||values.some((value,index)=>!Number.isFinite(positions[index])||(value!==0&&positions[index]===zero)))throw Error("数值比例超出安全展示范围；请查看原表格。");
  return {values,min,max,span,zero,positions};
}
function renderTableBar(schema,rows,category,series,context){
  const {values,min,max,zero,positions}=tableBarValues(schema,rows,category,series),node=document.createElement("figure"),caption=document.createElement("figcaption");
  node.dataset.chartContract="table-bar.v1";
  caption.textContent=`横向条形图 · table-bar.v1 · Run ${context.run_id} · Release ${context.release_id} · 结果 v${context.result_version} · 字段 ${context.field} · 类别 ${category} · 数值系列 ${series} · 单位：未指定 · 原行顺序，零基线`;
  node.append(caption);
  const svg=document.createElementNS("http://www.w3.org/2000/svg","svg"),width=420,left=200,height=values.length*38+48;
  svg.setAttribute("viewBox",`0 0 660 ${height}`);svg.setAttribute("role","img");svg.setAttribute("aria-label",`${category} / ${series} 横向条形图，单位未指定`);svg.classList.add("table-bar-chart");
  const element=(name,attrs,text)=>{const el=document.createElementNS(svg.namespaceURI,name);for(const [key,value]of Object.entries(attrs))el.setAttribute(key,String(value));if(text!==undefined)el.textContent=text;svg.append(el);return el;};
  element("line",{x1:zero,x2:zero,y1:8,y2:height-28,class:"table-bar-axis"});
  element("text",{x:left,y:height-8},String(min));element("text",{x:left+width,y:height-8,"text-anchor":"end"},String(max));
  values.forEach((value,index)=>{
    const x=positions[index],y=12+index*38,label=String(rows[index][category]);
    const title=`第${index+1}行 · ${category}: ${label} · ${series}: ${value} · 单位未指定`;
    const bar=element("rect",{x:Math.min(x,zero),y,width:Math.abs(x-zero),height:16,class:"table-bar-value","data-row":index+1,"data-value":value,"aria-label":title});
    const full=document.createElementNS(svg.namespaceURI,"title");full.textContent=title;bar.append(full);
    element("text",{x:0,y:y+13},`${index+1}. ${Array.from(label).slice(0,24).join("")}${Array.from(label).length>24?"…":""}`);
    element("text",{x:left,y:y+31},String(value));
  });node.append(svg);return node;
}
const tableChartReads=new Set();
function tableChartControl(manifest,field,result,context){
  if(!context)return null;
  const {record,view}=context,instance=view.instance,selection=view.instanceGeneration;
  const run=instance.runs.find(r=>r.app_run_id===record.run_id&&r.result_version===record.version&&r.release_id===record.release_id);
  const schema=manifest.output_schema.properties[field],shape=manifestTableShape(schema,result[field]);
  if(!run||!shape)return null;
  const node=document.createElement("section"),label=document.createElement("p"),category=document.createElement("select"),series=document.createElement("select"),button=document.createElement("button"),status=document.createElement("p"),plot=document.createElement("div");
  node.className="table-chart-controls";label.textContent="可选图表：明确选择原列，仅改变展示；单位未指定，不推断业务含义。";
  for(const [select,title,columns]of [[category,"类别列",shape.columns],[series,"数值系列（一个原列）",shape.columns.filter((key,index)=>["integer","number"].includes(shape.types[index]))]]){
    const wrap=document.createElement("label");wrap.textContent=title;select.setAttribute("aria-label",title);select.append(new Option("请选择原列",""),...columns.map(key=>new Option(key,key)));wrap.append(select);node.append(wrap);
  }
  button.type="button";button.textContent="重新核对并显示条形图";button.dataset.chartAction="show";status.setAttribute("role","status");node.prepend(label);node.append(button,status,plot);
  let generation=0,busy=false;
  const selected=()=>node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection;
  const changed=()=>{generation++;plot.replaceChildren();status.textContent="选择已改变；请显式重新核对并显示。";};category.onchange=changed;series.onchange=changed;
  button.onclick=async()=>{
    if(!selected()||busy||view.busy)return;
    plot.replaceChildren();const cat=category.value,numeric=series.value;
    try{tableBarValues(schema,result[field],cat,numeric);}catch(error){status.textContent=error.message;return;}
    const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
    const key=JSON.stringify([connection,view.project,instance.id,run.id,record.version,field]);if(tableChartReads.has(key))return;
    const edit=++generation,runSelection=view.runGeneration,current=()=>selected()&&generation===edit&&view.runGeneration===runSelection&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration;
    tableChartReads.add(key);busy=true;button.disabled=true;status.textContent="正在重新核对此Run、原Release与表格…";
    try{
      const saved=await api(`/api/internal/instances/${encodeURIComponent(instance.id)}/runs/${encodeURIComponent(run.id)}`);if(!current())return;
      const typed=saved.known_effects?.find(r=>r.run_id===record.run_id);
      if(saved.id!==run.id||saved.app_run_id!==record.run_id||saved.instance_id!==instance.id||saved.release_id!==record.release_id||saved.result_version!==record.version||saved.status!=="SUCCEEDED"||!typed||typed.fingerprint!==record.fingerprint||!ownerSame(typed.data,record.data)||!ownerSame(saved.result,result))throw Error("VERSION_CONFLICT");
      const manifests=await internalResultManifests({...instance,data:[typed],runs:[saved]},view,current);if(!current())return;
      if(!manifests||!ownerSame(manifests.get(record.release_id),manifest))throw Error("VERSION_CONFLICT");
      plot.append(renderTableBar(schema,saved.result[field],cat,numeric,{run_id:run.id,release_id:record.release_id,result_version:record.version,field}));
      status.textContent="已重新核对此历史成果；仅展示原数值，语义与人工验收状态不变。";
    }catch(error){if(current()){plot.replaceChildren();if(error.httpStatus===403)invalidateInternalContent(view);else status.textContent=`图表读取未通过：${error.message}。`;}}
    finally{tableChartReads.delete(key);busy=false;button.disabled=false;}
  };return node;
}
function renderManifestViews(manifest,result,chartContext=null){
  const group=document.createElement("div");group.className="manifest-views";
  const scalar=(value,type)=>type==="string"?typeof value==="string"&&value.length<=65536:type==="integer"?Number.isSafeInteger(value):type==="number"?typeof value==="number"&&Number.isFinite(value):type==="boolean"&&typeof value==="boolean";
  for(const definition of manifest.views){
    const section=document.createElement("section"),heading=document.createElement("h4"),message=document.createElement("p");
    section.dataset.viewComponent=definition.component_ref;section.dataset.outputField=definition.output_field;
    heading.textContent=definition.output_field;section.append(heading);group.append(section);
    const schema=manifest.output_schema?.properties?.[definition.output_field],value=result[definition.output_field];
    if(definition.component_ref==="text"&&schema?.type==="string"&&scalar(value,"string")){
      message.className="manifest-text";message.textContent=value;section.append(message);continue;
    }
    if(definition.component_ref==="table"||definition.component_ref==="chart"){
      const shape=manifestTableShape(schema,value),columns=shape?.columns;
      if(shape){
        const scroll=document.createElement("div"),table=document.createElement("table"),caption=document.createElement("caption"),head=document.createElement("thead"),body=document.createElement("tbody"),headers=document.createElement("tr");
        scroll.className="manifest-table-scroll";caption.textContent=`${definition.output_field} · ${value.length} 条`;table.append(caption,head,body);head.append(headers);
        for(const key of columns){const th=document.createElement("th");th.scope="col";th.textContent=key;headers.append(th);}
        for(const entry of value){const tr=document.createElement("tr");for(const key of columns){const td=document.createElement("td");td.textContent=String(entry[key]);tr.append(td);}body.append(tr);}
        scroll.append(table);section.append(scroll);
        if(!value.length){message.textContent="暂无记录；无字面命中不代表语义不存在。";section.append(message);}
        const controls=tableChartControl(manifest,definition.output_field,result,chartContext);
        if(controls)section.append(controls);
        else if(definition.component_ref==="chart"){message.textContent="图表需要已核对的同Run与原Release；请从历史成果入口打开。";section.append(message);}continue;
      }
    }
    message.textContent="此字段形状暂不支持所选视图；可查看原始结果。";section.append(message);
  }
  if(!manifest.views.length)group.textContent="清单未声明视图；可查看原始结果。";
  return group;
}
function internalResult(record,view,manifest) {
  if(view.spec)return specResult(record,view);
  if(view.workflow)return textWorkflowResult(record,view);
  if(!view.agent&&!view.literal)return row(`结果 v${record.version} · ${record.release_id} · ${JSON.stringify(record.data.result)}`);
  const value=record.data.result,node=document.createElement("article");node.className="agent-result";
  const title=document.createElement("p");title.textContent=`历史结果 v${record.version} · ${record.release_id} · ${view.literal ? "确定性文本工具" : "离线 Replay"} · 字面检查 PASS · 语义 ${value.semantic_status}`;
  const scope=document.createElement("p");scope.textContent=`检索词：${value.term} · 材料 ${value.resource_id} · revision ${value.revision} · hash ${value.source_hash}`;
  node.dataset.resultVersion=record.version;node.dataset.releaseId=record.release_id;
  const raw=document.createElement("details"),label=document.createElement("summary"),json=document.createElement("pre");label.textContent="查看原始结果";json.textContent=JSON.stringify(value,null,2);raw.append(label,json);
  node.append(title,scope,renderManifestViews(manifest,value,{record,view}),raw);
  if(view.literal)literalResultDownload(node,record,view);
  return node;
}
function textWorkflowReportValue(value){
  const keys=["resource_id","source_hash","term_a","term_b","citations_a","citations_b","text","semantic_status"];
  const term=x=>typeof x==="string"&&x===x.trim()&&Array.from(x).length>0&&Array.from(x).length<=80&&!/[\r\n]/.test(x);
  const citations=x=>Array.isArray(x)&&x.length<=8&&x.every(c=>c&&Object.keys(c).sort().join()===['end_line','quote','start_line'].join()&&Number.isSafeInteger(c.start_line)&&c.start_line>0&&Number.isSafeInteger(c.end_line)&&c.end_line>=c.start_line&&c.end_line<=32&&typeof c.quote==="string"&&Array.from(c.quote).length<=1536);
  if(!value||Object.keys(value).sort().join()!==keys.sort().join()||typeof value.resource_id!=="string"||!value.resource_id||!/^[a-f0-9]{64}$/.test(value.source_hash)||!term(value.term_a)||!term(value.term_b)||!citations(value.citations_a)||!citations(value.citations_b)||value.semantic_status!=="UNKNOWN"||typeof value.text!=="string"||Array.from(value.text).length>6000)return null;
  const chunks=[];
  for(const side of ["a","b"]){chunks.push(`${side.toUpperCase()}: ${value['term_'+side]}`);for(const cite of value['citations_'+side])chunks.push(`L${cite.start_line}: ${cite.quote}`);if(!value['citations_'+side].length)chunks.push("No literal matches");}
  return value.text===chunks.join("\n")?value:null;
}
async function textWorkflowOwnerContract(view,contract,current){
  const invalid=()=>{throw Error("四步报告与所选 Run、材料或成果版本不一致");},instance=view.engineering.instance;
  const run=view.engineering.run,record=instance.data.find(r=>r.run_id===run?.app_run_id&&r.version===run?.result_version);
  if(!run||run.id!==view.rid||!record||run.status!=="SUCCEEDED"||contract.app_run_id!==run.app_run_id||contract.release_id!==run.release_id||contract.release_id!==instance.release_id||contract.release_fingerprint!==instance.release_fingerprint||contract.instance_revision!==instance.revision||contract.result_version!==run.result_version||contract.result_version!==instance.data_version||contract.data_version!==instance.data_version||contract.typed_fingerprint!==record.fingerprint||record.release_id!==run.release_id||record.instance_id!==instance.id||!textWorkflowReportValue(contract.output)||!ownerSame(contract.output,run.result)||!ownerSame(contract.output,record.data.result)||!ownerSame(contract.goal,contract.source_goal?.snapshot?.content)||!ownerSame(contract.input,{term_a:contract.output.term_a,term_b:contract.output.term_b,emit_report:true})||contract.material?.resource_id!==contract.output.resource_id||contract.material.hash!==contract.output.source_hash||typeof contract.material.content!=="string"||!["txt","md"].includes(contract.material.format)||new TextEncoder().encode(contract.material.content).length>1536||!Array.isArray(contract.actual_operations)||contract.actual_operations.length!==4||!Array.isArray(run.steps)||run.steps.length!==4)invalid();
  const outputHash=await ownerHash(contract.output);if(!current())return false;
  if(outputHash!==contract.output_fingerprint)invalid();
  const typedHash=await ownerHash(record.data);if(!current())return false;
  if(typedHash!==contract.typed_fingerprint)invalid();
  const bytesHash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(contract.material.content))),b=>b.toString(16).padStart(2,"0")).join("");if(!current())return false;
  if(bytesHash!==contract.material.hash)invalid();
  for(const [n,id] of ["read","lookup_a","lookup_b","report"].entries()){
    const receipt=contract.actual_operations[n],step=run.steps[n];
    if(receipt.step_id!==id||receipt.status!=="VERIFIED"||step.step_id!==id||step.status!=="VERIFIED")invalid();
    const hash=await ownerHash(receipt);if(!current())return false;if(hash!==step.fingerprint)invalid();
  }
  if(!ownerSame(contract.actual_operations[0].data,contract.material)||!ownerSame(contract.actual_operations[3].data,contract.output))invalid();
  for(const [n,side] of [[1,"a"],[2,"b"]]){
    const lookup=contract.actual_operations[n].data;
    if(lookup.resource_id!==contract.output.resource_id||lookup.source_hash!==contract.output.source_hash||lookup.term!==contract.output['term_'+side]||!ownerSame(lookup.citations,contract.output['citations_'+side])||lookup.semantic_status!=="UNKNOWN")invalid();
  }
  return current();
}
function renderTextWorkflowReport(parent,contract){
  const value=textWorkflowReportValue(contract.output);if(!value)return;
  const title=document.createElement("h4"),scope=document.createElement("p"),goal=document.createElement("p");
  title.textContent=`四步文本报告 · Run ${contract.run_id} · 结果 v${contract.result_version}`;
  scope.textContent=`材料 ${value.resource_id} · SHA-256 ${value.source_hash} · Release ${contract.release_id} · 语义 UNKNOWN；人工判断属于此 Run。`;
  goal.textContent=`冻结目标：${contract.goal.goal}`;parent.append(title,goal,scope);
  for(const side of ["a","b"]){
    const section=document.createElement("section"),heading=document.createElement("h5"),list=document.createElement("ul");
    heading.textContent=`检索 ${side.toUpperCase()}：${value['term_'+side]}`;section.append(heading,list);
    for(const cite of value['citations_'+side]){const item=document.createElement("li"),line=document.createElement("p"),quote=document.createElement("blockquote");line.textContent=`第 ${cite.start_line}—${cite.end_line} 行`;quote.textContent=cite.quote;item.append(line,quote);list.append(item);}
    if(!value['citations_'+side].length){const none=document.createElement("p");none.textContent="无字面命中；不代表语义不存在。";section.append(none);}
    parent.append(section);
  }
  const reportTitle=document.createElement("h5"),text=document.createElement("pre");reportTitle.textContent="完整报告文本";text.textContent=value.text;parent.append(reportTitle,text);
}
function textWorkflowResult(record,view){
  const instance=view.instance,selection=view.instanceGeneration,run=instance.runs.find(r=>r.app_run_id===record.run_id&&r.result_version===record.version&&r.release_id===record.release_id);
  const node=document.createElement("article"),title=document.createElement("h3"),status=document.createElement("p"),open=document.createElement("button");
  node.className="text-workflow-result";node.dataset.resultVersion=record.version;title.textContent=`四步文本成果 · 结果 v${record.version}`;
  status.textContent="打开后重新核对当前权限和同一 Run 的完整报告；历史人工声明不代表当前接受。语义 UNKNOWN。";
  open.type="button";open.textContent="打开此 Run 报告与人工验收";open.dataset.textWorkflowAction="review";
  const current=()=>node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection;
  open.onclick=()=>{if(current()&&!view.busy&&run)return showInternalRun(run.id,view,instance);};open.disabled=!run;
  node.append(title,status,open);return node;
}
const literalResultDownloads=new Set();
function literalResultValue(instanceId,run,record){
  if(!run||!record||run.status!=="SUCCEEDED"||run.instance_id!==instanceId||record.instance_id!==instanceId||
    record.run_id!==run.app_run_id||record.release_id!==run.release_id||record.version!==run.result_version||
    !Number.isSafeInteger(run.result_version)||run.result_version<1)return null;
  const project=value=>{
    if(!value||typeof value.resource_id!=="string"||!Number.isSafeInteger(value.revision)||value.revision<1||
      typeof value.source_hash!=="string"||!/^[a-f0-9]{64}$/.test(value.source_hash)||typeof value.term!=="string"||!value.term||value.term!==value.term.trim()||Array.from(value.term).length>80||
      value.semantic_status!=="UNKNOWN"||!Array.isArray(value.citations)||value.citations.length>16||
      !value.citations.every(c=>c&&Number.isSafeInteger(c.start_line)&&c.start_line>0&&Number.isSafeInteger(c.end_line)&&c.end_line>=c.start_line&&typeof c.quote==="string"))return null;
    return {resource_id:value.resource_id,revision:value.revision,source_hash:value.source_hash,term:value.term,
      citations:value.citations.map(c=>({start_line:c.start_line,end_line:c.end_line,quote:c.quote})),semantic_status:"UNKNOWN"};
  };
  const result=project(run.result),typed=project(record.data?.result);
  if(!result||!typed||JSON.stringify(result)!==JSON.stringify(typed))return null;
  return {instance_id:instanceId,run_id:run.id,release_id:run.release_id,result_version:run.result_version,result};
}
function literalResultDownload(node,record,view){
  const instance=view.instance,selection=view.instanceGeneration;
  const run=instance.runs.find(r=>r.app_run_id===record.run_id&&r.release_id===record.release_id&&r.result_version===record.version);
  const expected=literalResultValue(instance.id,run,record);if(!expected)return;
  const button=document.createElement("button"),status=document.createElement("p");
  button.type="button";button.textContent="下载此检索结果 JSON";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
  node.dataset.literalRun=run.id;node.dataset.resultVersion=record.version;node.append(button,status);
  const selected=()=>node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection;
  button.onclick=async()=>{
    if(!selected()||view.busy)return;
    const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration,runSelection=view.runGeneration;
    const key=JSON.stringify([connection,view.project,instance.id,run.id,record.version]);
    if(literalResultDownloads.has(key))return;
    const current=()=>selected()&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration&&runSelection===view.runGeneration;
    literalResultDownloads.add(key);button.disabled=true;status.textContent="正在重新核对此运行与成果版本…";
    try{
      const saved=await api(`/api/internal/instances/${encodeURIComponent(instance.id)}/runs/${encodeURIComponent(run.id)}`);
      if(!current())return;
      const typed=saved.known_effects?.find(r=>r.run_id===record.run_id);
      const value=literalResultValue(instance.id,saved,typed);
      if(saved.app_run_id!==record.run_id||!value||JSON.stringify(value)!==JSON.stringify(expected))throw Error("VERSION_CONFLICT");
      const url=URL.createObjectURL(new Blob([JSON.stringify(value,null,2)+"\n"],{type:"application/json;charset=utf-8"}));
      const link=document.createElement("a");link.href=url;link.download=`literal-${instance.id}-${run.id}-v${record.version}.json`;link.hidden=true;
      try{node.append(link);link.click();status.textContent=`已生成此运行成果 v${record.version} 的 JSON 下载；语义 UNKNOWN。`;}
      finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),0);}
    }catch(error){if(current()){if(error.httpStatus===403)invalidateInternalContent(view);else status.textContent=`成果核对未通过：${error.message}。未下载文件。`;}}
    finally{literalResultDownloads.delete(key);button.disabled=false;}
  };
}
function specResult(record,view){
  const instance=view.instance,selection=view.instanceGeneration,value=record.data.result;
  const run=instance.runs.find(item=>item.app_run_id===record.run_id&&item.result_version===record.version);
  const node=document.createElement("article"),title=document.createElement("h3"),status=document.createElement("p"),body=document.createElement("div");
  node.className="spec-result";title.textContent=`规范成果 v${record.version}`;
  status.setAttribute("role","status");status.textContent="已保存；读取前将重新核对当前权限、来源和此版本内容。语义 UNKNOWN，人工验收 PENDING。";
  node.append(title,status);let reading=0;
  const buttons=[];
  for(const [format,label] of [["view","读取此版本清单"],["json","下载 JSON"],["md","下载 Markdown"]]){
    const button=document.createElement("button");button.type="button";button.textContent=label;button.dataset.specAction=format;buttons.push(button);node.append(button);
    button.onclick=async()=>{
      const generation=++reading,workspace=workspaceSelectionGeneration;
      const current=()=>node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection&&workspaceSelectionGeneration===workspace&&generation===reading;
      if(!current()||!run)return;
      buttons.forEach(b=>b.disabled=true);body.replaceChildren();status.textContent="正在读取并核对此版本已保存成果…";
      try{
        const saved=await api(`/api/internal/app-run-jobs/${run.id}/spec-artifact`);
        if(!current())return;
        const outputHash=await paHash(value);
        if(!current())return;
        const bytesHash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(saved.resource?.content))),b=>b.toString(16).padStart(2,"0")).join("");
        if(!current())return;
        if(saved.namespace!=="spec-saved-artifact.v1"||saved.principal_id!==instance.principal_id||saved.project_id!==view.project||saved.app_id!==view.app||saved.instance_id!==instance.id||saved.run_id!==run.id||saved.app_run_id!==record.run_id||saved.release_id!==record.release_id||saved.result_version!==record.version||saved.output_fingerprint!==outputHash||saved.resource?.resource_id!==value.resource_id||saved.resource.format!=="json"||saved.resource.hash!==value.hash||bytesHash!==value.hash||saved.resource.content!==goalRunCanonical(value.checklist)||saved.markdown_view!==run.markdown_view||typeof saved.markdown_view!=="string"||saved.citation_status!=="PASS"||saved.semantic_status!=="UNKNOWN"||saved.semantic_goal_acceptance!=="NOT_RUN"||saved.owner_acceptance!=="PENDING"||saved.formal_publication_enabled!==false||saved.new_model_requests!==0||saved.project_writes!==0)throw Error("VERSION_CONFLICT");
        renderSpecChecklist(body,value.checklist);
        status.textContent=`已核对成果 v${record.version} · 出处 PASS · 语义 UNKNOWN · 人工验收 PENDING。完整原文、条件、例外与未决项保留。`;
        if(format!=="view"){
          const url=URL.createObjectURL(new Blob([format==="json"?saved.resource.content:saved.markdown_view],{type:format==="json"?"application/json;charset=utf-8":"text/markdown;charset=utf-8"}));
          const link=document.createElement("a");link.href=url;link.download=`spec-${instance.id}-v${record.version}.${format}`;node.append(link);link.click();link.remove();URL.revokeObjectURL(url);
        }
      }catch(error){if(current()){body.replaceChildren();status.textContent=`成果读取未通过：${error.detail||error.message}。未显示或下载此响应。`;}}
      finally{if(node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection&&generation===reading)buttons.forEach(b=>b.disabled=false);}
    };
  }
  if(run&&view.draft.candidate.namespace==="pa-natural-spec-app.v1"&&view.draft.candidate.manifest.origin==="goal"&&!view.draft.candidate.spec_task){
    const extract=document.createElement("button");extract.type="button";extract.textContent="从此成功任务提取应用（P-B）";extract.dataset.specAction="extract";
    extract.onclick=()=>{if(node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection)return openNaturalTaskExtraction(view,run.id,node);};node.append(extract);
  }
  if(run){
    const review=document.createElement("button");review.type="button";review.textContent="查看此运行与人工验收";review.dataset.specAction="review";
    review.onclick=()=>{if(node.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection)return showInternalRun(run.id,view,instance);};
    node.append(review);
  }
  node.append(body);return node;
}

function clearNaturalTaskExtraction(){const s=naturalTaskExtraction;if(s)s.panel.remove();naturalTaskExtraction=null;if(s&&naturalFirstGuide?.mode==="PB"&&naturalFirstGuide.extraction===s&&!naturalFirstGuide.opening&&naturalFirstGuide.stage!=="internal")clearNaturalFirstGuide();}
function naturalTaskCurrent(s){return naturalTaskExtraction===s&&s.panel.isConnected&&engineeringCurrent(s.view)&&s.instance===s.view.instance&&s.selection===s.view.instanceGeneration&&s.runSelection===s.view.runGeneration&&s.connection===identityConnectionGeneration&&s.workspace===workspaceSelectionGeneration;}
function naturalTaskButtons(s){
  if(!naturalTaskCurrent(s))return;
  const pending=naturalTaskRequests.get(s.scope);
  const blocked=!!s.recoveryError;
  s.prepare.disabled=s.busy||blocked||!!pending||!s.source||!!s.saved;
  s.preview.disabled=s.busy||blocked||!!pending||!!s.saved||!s.source||!s.target.value;
  s.commit.disabled=s.busy||blocked||!!pending||!!s.saved||!s.source||!s.review||!s.ack.checked;
  s.recover.hidden=!pending;s.recover.disabled=s.busy||blocked||!pending||!s.source;s.open.disabled=s.busy||blocked||!!pending||!s.saved;
  s.closeIntent.hidden=!pending;s.closeIntent.disabled=s.busy||blocked||!pending||!s.source;
  s.key.value=(pending&&naturalTaskRecoveryMetadata.get(pending)?.record.request_key)||s.review?.request.request_key||s.saved?.request_key||"";
  s.ack.disabled=blocked||!!pending;
  for(const input of s.inputs)input.disabled=blocked||!!pending;
  renderNaturalFirstGuide();
}
function naturalTaskEdited(s){if(!naturalTaskCurrent(s))return;s.edit++;s.review=null;s.saved=null;s.ack.checked=false;s.proof.textContent="逻辑或绑定已编辑，请重新审阅；不会沿用旧确认。";naturalTaskButtons(s);}
function naturalTaskRecipe(s){
  const recipe=structuredClone(s.source.recipe),names=new Map();
  s.rows.forEach((row,index)=>names.set(recipe.steps[index].step_id,row.id.value));
  recipe.steps.forEach((step,index)=>{step.step_id=s.rows[index].id.value;step.operator=s.rows[index].operator.value;step.depends_on=step.depends_on.map(id=>names.get(id));for(const input of Object.values(step.inputs))if(input.source==="step")input.ref=names.get(input.ref);});
  const models=recipe.steps.filter(step=>step.operator.startsWith("model."));
  if(models.length===2){const second=models[1],first=models[0];delete second.inputs.prior_items;delete second.inputs.prior_feedback;second.depends_on=[recipe.steps[0].step_id];if(s.prior.checked){second.inputs.prior_items={source:"step",ref:first.step_id,field:"items"};second.inputs.prior_feedback={source:"step",ref:first.step_id,field:"feedback"};second.depends_on.push(first.step_id);}}
  return recipe;
}
async function openNaturalTaskExtraction(view,rid,parent){
  clearNaturalTaskExtraction();
  const panel=document.createElement("section"),s={view,rid,panel,instance:view.instance,selection:view.instanceGeneration,runSelection:view.runGeneration,connection:identityConnectionGeneration,workspace:workspaceSelectionGeneration,busy:true,recoveryError:null,source:null,review:null,saved:null,edit:0,rows:[],inputs:[]};
  s.scope=naturalTaskRecoveryKey(s);naturalTaskExtraction=s;parent.append(panel);
  const element=(tag,id,text)=>{const node=document.createElement(tag);if(id)node.id=id;if(text)node.textContent=text;panel.append(node);return node;};
  element("h4",null,"成功任务 → 可审阅的 P-B 应用候选");
  element("p",null,"从此运行实际步骤图开始。可编辑稳定节点名称、模型关注范围及是否读取前一节点反馈；所有输入端口由当前图重新绑定。只允许既有有限图与来源预算。新材料仍需模型执行，默认关闭；出处 PASS 不代表通用语义通过。");
  s.status=element("p","pb-spec-status","正在核对完整成功任务来源…");s.status.setAttribute("role","status");
  s.editor=element("div","pb-spec-steps");
  const targetLabel=element("label",null,"自己的新目标与材料 ");s.target=document.createElement("select");s.target.id="pb-spec-target";targetLabel.append(s.target);s.inputs.push(s.target);
  s.prepare=element("button","pb-spec-prepare","准备自己的新材料与 Goal");s.prepare.type="button";s.prepare.onclick=()=>beginNaturalPBTarget(s);
  const nameLabel=element("label",null,"新应用名称 ");s.name=document.createElement("input");s.name.id="pb-spec-name";s.name.maxLength=100;s.name.value="成功规范任务复用应用";nameLabel.append(s.name);s.inputs.push(s.name);
  const priorLabel=element("label",null," ");s.prior=document.createElement("input");s.prior.type="checkbox";s.prior.id="pb-spec-prior";priorLabel.prepend(s.prior);priorLabel.append(document.createTextNode("第二模型节点读取第一节点的实际结果和反馈"));s.inputs.push(s.prior);
  s.preview=element("button","pb-spec-preview","审阅编辑图与精确新绑定");s.preview.type="button";
  s.proof=element("pre","pb-spec-proof");
  const ackLabel=element("label",null," ");s.ack=document.createElement("input");s.ack.type="checkbox";s.ack.id="pb-spec-ack";ackLabel.prepend(s.ack);ackLabel.append(document.createTextNode("核对来源、编辑图、新目标与材料、原预算；只授权这个新应用读取此材料并保存本项目 JSON 清单。语义 UNKNOWN，人工 PENDING。"));
  s.commit=element("button","pb-spec-commit","确认此精确审阅并提取应用");s.commit.type="button";
  const keyLabel=element("label",null,"原提取请求键（只读，可选中复制） ");s.key=document.createElement("input");s.key.id="pb-spec-request-key";s.key.readOnly=true;keyLabel.append(s.key);
  element("p",null,"提交前只保存此浏览器的来源标识和原意图指纹，不保存凭据或材料正文。重载后重新打开这个成功成果，可明确按原 key 读取回执；未知时保持锁定，不重发或改用新 key。");
  s.recover=element("button","pb-spec-recover","仅按原 key GET 恢复提取回执");s.recover.type="button";
  element("p",null,"原请求若始终未受理，可明确关闭这个原 key；服务端只在确认未受理后封存并拒绝迟到提交。已受理应用不能取消。关闭回执不会清除票据，仍须另点原 key GET 核对后，再自行重新审阅。权限拒绝或未知状态不能证明关闭。");
  s.closeIntent=element("button","pb-spec-close-intent","确认仅关闭尚未受理的原 key，并拒绝迟到提交");s.closeIntent.type="button";
  s.open=element("button","pb-spec-open","打开已核对应用，另行确认内部版本");s.open.type="button";
  const close=element("button","pb-spec-close","关闭审阅（不取消已发送请求）");close.type="button";close.onclick=()=>{if(naturalTaskCurrent(s))clearNaturalTaskExtraction();};
  s.target.onchange=()=>naturalTaskEdited(s);s.name.oninput=()=>naturalTaskEdited(s);s.prior.onchange=()=>naturalTaskEdited(s);s.ack.onchange=()=>naturalTaskButtons(s);
  naturalTaskButtons(s);
  const path=`/api/projects/${view.project}/natural-spec-task-runs/${rid}`,expectedRun=s.instance.runs.find(run=>run.id===rid);
  try{
    const source=await api(path+"/extraction-options");if(!naturalTaskCurrent(s))return;
    const proofHash=await paHash(source.source_proof);if(!naturalTaskCurrent(s))return;
    const recipeHash=await paHash(source.recipe);if(!naturalTaskCurrent(s))return;
    if(source.namespace!=="pb-natural-spec-extraction.v1"||source.project_id!==view.project||source.principal_id!==s.instance.principal_id||source.source_run_id!==rid||source.source_proof?.source_run_id!==rid||source.source_proof.principal_id!==source.principal_id||source.source_proof.project_id!==view.project||source.source_proof_fingerprint!==proofHash||source.recipe_fingerprint!==recipeHash||source.new_model_requests!==0||source.project_writes!==0||source.semantic_status!=="UNKNOWN"||source.owner_acceptance!=="PENDING"||source.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
    if(!expectedRun||expectedRun.status!=="SUCCEEDED"||source.source_proof.source_app_id!==view.app||source.source_proof.instance_id!==s.instance.id||source.source_proof.app_run_id!==expectedRun.app_run_id||source.source_proof.release_id!==expectedRun.release_id||source.source_proof.result_version!==expectedRun.result_version)throw Error("VERSION_CONFLICT");
    s.source=source;
    naturalTaskRecoveryRefresh(s);
    for(const [index,step] of source.recipe.steps.entries()){
      const line=document.createElement("label");line.textContent=`步骤 ${index+1} · 稳定 ID `;
      const id=document.createElement("input");id.value=step.step_id;id.dataset.pbStep=String(index);id.maxLength=40;id.setAttribute("aria-label",`步骤 ${index+1} 稳定 ID`);id.oninput=()=>naturalTaskEdited(s);line.append(id);
      const operator=document.createElement("select");operator.setAttribute("aria-label",`步骤 ${index+1} 算子`);
      const options=step.operator.startsWith("model.")?["model.spec.all","model.spec.requirements","model.spec.qualifiers"]:[step.operator];for(const ref of options)operator.add(new Option(ref,ref));operator.value=step.operator;operator.onchange=()=>naturalTaskEdited(s);line.append(operator);
      const ports=document.createElement("span");ports.textContent=` · 输入：${Object.entries(step.inputs).map(([name,port])=>`${name} ← ${port.source}:${port.ref||""}.${port.field}`).join("；")}`;line.append(ports);s.editor.append(line);s.rows.push({id,operator});s.inputs.push(id,operator);
    }
    const models=source.recipe.steps.filter(step=>step.operator.startsWith("model."));priorLabel.hidden=models.length!==2;s.prior.checked=models.length===2&&!!models[1].inputs.prior_items;
    const goals=await api(`/api/projects/${view.project}/goal-cards`);if(!naturalTaskCurrent(s))return;
    s.target.add(new Option("请选择明确不同的已保存目标和材料",""));for(const goal of goals.items)if(goal.id!==view.draft.candidate.manifest.goal_ref)s.target.add(new Option(`${goal.title} · v${goal.version} · ${goal.id}`,goal.id));
    s.status.textContent=s.recoveryError?`${s.recoveryError}：原意图记录无法安全核对，已禁止新提取；不会清除未知记录。`:naturalTaskRequests.has(s.scope)?"已发现这个成功来源的原提取意图；请明确按原 key GET 核对回执。不会自动读取、重发或生成新 key。":"已核对成功来源；默认图来自实际回执。编辑图和新材料尚未运行。";
    beginNaturalPBGuide(s);
  }catch(error){if(naturalTaskCurrent(s)){s.source=null;s.status.textContent=`来源未通过：${error.detail||error.message}`;if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT","RESOURCE_UNAVAILABLE"].includes(error.message)){const pending=naturalTaskRequests.get(s.scope);if(pending&&naturalTaskRecoveryMetadata.has(pending)){delete pending.body;delete pending.review;}invalidateInternalContent(view);engineeringStatus(view,"当前成功来源核对未通过；原提取意图不会清除，请重新核查授权与来源。","error");}}}
  finally{s.busy=false;naturalTaskButtons(s);}
  s.preview.onclick=async()=>{
    if(!naturalTaskCurrent(s)||s.busy)return;
    naturalTaskRecoveryRefresh(s);naturalTaskButtons(s);
    if(s.recoveryError||naturalTaskRequests.has(s.scope))return;
    const edit=s.edit;s.busy=true;s.review=null;s.ack.checked=false;naturalTaskButtons(s);
    const current=()=>naturalTaskCurrent(s)&&edit===s.edit&&!s.recoveryError&&!naturalTaskRequests.has(s.scope);
    try{
      const goal=await api(`/api/goal-cards/${s.target.value}`);if(!current())return;
      const saved=goal.history?.[0];if(goal.project_id!==view.project||goal.id!==s.target.value||!saved||saved.version!==goal.version||saved.fingerprint!==goal.fingerprint||saved.snapshot?.resource_snapshots?.length!==1)throw Error("VERSION_CONFLICT");
      const goalHash=await paHash(saved.snapshot);if(!current())return;if(goalHash!==goal.fingerprint)throw Error("VERSION_CONFLICT");
      naturalTaskRecoveryRefresh(s);if(!current())return;
      const request={source_run_id:rid,expected_source_proof_fingerprint:s.source.source_proof_fingerprint,expected_source_recipe_fingerprint:s.source.recipe_fingerprint,card_id:goal.id,expected_goal_version:goal.version,expected_goal_fingerprint:goal.fingerprint,expected_source_hash:saved.snapshot.resource_snapshots[0].hash,recipe:naturalTaskRecipe(s),name:s.name.value,request_key:crypto.randomUUID()};
      const result=await api(path+"/extraction-reviews","POST",request);if(!current())return;
      const {review_fingerprint,...review}=result,hash=await paHash(review);if(!current())return;
      if(result.namespace!=="pb-natural-spec-extraction.v1"||result.principal_id!==s.instance.principal_id||result.project_id!==view.project||result.source_run_id!==rid||hash!==review_fingerprint||goalRunCanonical(result.request)!==goalRunCanonical(request)||result.request_fingerprint!==await paHash(request)||result.source_proof_fingerprint!==request.expected_source_proof_fingerprint||result.original_recipe_fingerprint!==request.expected_source_recipe_fingerprint||goalRunCanonical(result.edited_recipe)!==goalRunCanonical(request.recipe)||goalRunCanonical(result.target_goal.snapshot)!==goalRunCanonical(saved.snapshot)||result.target_goal.card_id!==goal.id||result.target_goal.version!==goal.version||result.target_goal.fingerprint!==goal.fingerprint||result.candidate.manifest.origin!=="task_run"||result.candidate.manifest.source_run_ref!==rid||result.candidate.manifest.data_bindings[0].resource_ref!==saved.snapshot.resource_snapshots[0].resource_id||result.candidate_fingerprint!==await paHash(result.candidate)||result.new_model_requests!==0||result.project_writes!==0||result.semantic_status!=="UNKNOWN"||result.owner_acceptance!=="PENDING"||result.edited_recipe_execution!=="NOT_RUN"||result.sample_scope!=="SUCCESSFUL_SOURCE_ONLY"||result.preview.status!=="MODEL_EXECUTION_REQUIRED")throw Error("VERSION_CONFLICT");
      if(!current())return;s.review=result;s.proof.textContent=JSON.stringify({source:result.source_proof,original_recipe:result.original_recipe,edited_recipe:result.edited_recipe,variable_bindings:result.variable_bindings,target_goal:result.target_goal,limits:result.candidate.manifest.runtime_limits,human_unresolved:result.preview.human_unresolved,edited_recipe_execution:result.edited_recipe_execution,sample_scope:result.sample_scope,review_fingerprint},null,2);s.status.textContent="精确审阅已读回。编辑图未运行，来源的一次成功不证明通用语义；请明确确认这份绑定。";
    }catch(error){if(current())s.status.textContent=`审阅未通过：${error.detail||error.message}`;}
    finally{s.busy=false;naturalTaskButtons(s);}
  };
  const recover=async(pending,lock,operationCurrent)=>{
    const current=()=>operationCurrent()&&!s.recoveryError&&naturalTaskRequests.get(s.scope)===pending;
    const metadata=naturalTaskRecoveryMetadata.get(pending),record=metadata?.record;
    const saved=naturalTaskRecoveryRead(s);
    if(!metadata||metadata.key!==naturalTaskRecoveryKey(s)||(saved&&saved.raw!==metadata.raw))throw Error("RECOVERY_RECORD_CONFLICT");
    naturalTaskRecoverySource(s,record);
    const value=await api(path+"/extractions/by-key/"+encodeURIComponent(record.request_key));if(!current())return;
    if(value.namespace===naturalTaskTerminalNamespace){
      if(!await naturalTaskTerminalProof(s,pending,value,current))return;
      naturalTaskRecoveryForget(s,pending,lock);delete pending.body;delete pending.review;
      s.review=null;s.saved=null;s.ack.checked=false;
      s.proof.textContent=JSON.stringify({closed_request_key:record.request_key,status:value.status,receipt_fingerprint:value.receipt_fingerprint},null,2);
      s.status.textContent="已按原 key 核对永久未受理关闭凭据，清除了此原意图票据。迟到提交将被拒绝；如仍需提取，请自行重新审阅并另行确认。";
      return;
    }
    const returnedRequestHash=await paHash(value.request);if(!current())return;
    const {review_fingerprint,...review}=value.reviewed||{},reviewHash=await paHash(review);if(!current())return;
    const candidateHash=await paHash(value.reviewed?.candidate);if(!current())return;
    const sourceHash=await paHash(value.reviewed?.source_proof);if(!current())return;
    if(returnedRequestHash!==record.request_fingerprint||value.request_fingerprint!==record.request_fingerprint||review_fingerprint!==record.review_fingerprint||reviewHash!==record.review_fingerprint||candidateHash!==record.candidate_fingerprint||value.candidate_fingerprint!==record.candidate_fingerprint||value.reviewed.candidate_fingerprint!==record.candidate_fingerprint||value.id!==record.app_id||value.app_id!==record.app_id||value.runtime_id!==record.runtime_id||value.reviewed.app_id!==record.app_id||value.reviewed.runtime_id!==record.runtime_id||value.request_key!==record.request_key||value.request?.review?.request_key!==record.request_key||value.request.expected_review_fingerprint!==record.review_fingerprint||value.request.consent!=="EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"||value.request.artifact_write_consent!=="ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT"||sourceHash!==record.source_proof_fingerprint||value.source_proof_fingerprint!==record.source_proof_fingerprint||value.reviewed.source_proof_fingerprint!==record.source_proof_fingerprint||value.reviewed.source_proof.app_run_id!==record.source_app_run_id||value.reviewed.source_proof.release_id!==record.source_release_id||value.reviewed.source_proof.release_fingerprint!==record.source_release_fingerprint||value.reviewed.source_proof.result_version!==record.source_result_version||goalRunCanonical(value.reviewed.request)!==goalRunCanonical(value.request.review))throw Error("VERSION_CONFLICT");
    // Only the independently frozen local hashes permit cold RAM reconstruction.
    if(!pending.body&&!pending.review){pending.body=structuredClone(value.request);pending.review=structuredClone(value.reviewed);}
    const requestHash=await paHash(pending.body);if(!current())return;
    if(value.namespace!=="pb-natural-spec-extraction.v1"||value.kind!=="pb_natural_spec_task.v1"||value.principal_id!==s.instance.principal_id||value.project_id!==view.project||value.source_run_id!==rid||value.request_key!==pending.body.review.request_key||value.request_fingerprint!==requestHash||goalRunCanonical(value.request)!==goalRunCanonical(pending.body)||review_fingerprint!==pending.body.expected_review_fingerprint||reviewHash!==review_fingerprint||goalRunCanonical(value.reviewed)!==goalRunCanonical(pending.review)||value.id!==pending.review.app_id||value.app_id!==value.id||value.runtime_id!==pending.review.runtime_id||value.candidate_fingerprint!==pending.review.candidate_fingerprint||value.new_model_requests!==0||value.project_writes!==0||value.owner_acceptance!=="PENDING"||value.semantic_status!=="UNKNOWN"||value.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
    const app=await api(`/api/apps/${value.id}`);if(!current())return;
    const appHash=await paHash(app.candidate);if(!current())return;
    if(app.id!==record.app_id||app.project_id!==view.project||app.runtime_id!==value.runtime_id||app.fingerprint!==value.candidate_fingerprint||appHash!==record.candidate_fingerprint||goalRunCanonical(app.candidate)!==goalRunCanonical(pending.review.candidate)||app.name!==pending.body.review.name||app.candidate.spec_task?.kind!=="pb_natural_spec_task.v1"||app.candidate.spec_task.source_run_id!==rid||app.candidate.manifest.origin!=="task_run"||app.candidate.manifest.source_run_ref!==rid)throw Error("VERSION_CONFLICT");
    naturalTaskRecoveryForget(s,pending,lock);
    s.review=structuredClone(value.reviewed);s.saved=value;s.ack.checked=false;
    s.target.value=pending.body.review.card_id;s.name.value=pending.body.review.name;
    s.rows.forEach((row,index)=>{row.id.value=value.reviewed.edited_recipe.steps[index].step_id;row.operator.value=value.reviewed.edited_recipe.steps[index].operator;});
    const models=value.reviewed.edited_recipe.steps.filter(step=>step.operator.startsWith("model."));s.prior.checked=models.length===2&&!!models[1].inputs.prior_items;
    s.proof.textContent=JSON.stringify({recovered_request_key:record.request_key,source:value.reviewed.source_proof,edited_recipe:value.reviewed.edited_recipe,target_goal:value.reviewed.target_goal,review_fingerprint:record.review_fingerprint,candidate_fingerprint:record.candidate_fingerprint,semantic_status:"UNKNOWN",owner_acceptance:"PENDING"},null,2);
    s.status.textContent="已核对原意图指纹、独立 P-B 草案和原 key 回执；打开后另行核查内部版本。新材料结果尚未运行。";
  };
  const action=async(submit,closeIntent=false)=>{
    if(!naturalTaskCurrent(s)||s.busy)return;
    const edit=s.edit,current=()=>naturalTaskCurrent(s)&&edit===s.edit;
    s.busy=true;naturalTaskButtons(s);
    try{
      if(!navigator.locks?.request)throw Error("RECOVERY_LOCK_UNAVAILABLE");
      await navigator.locks.request(naturalTaskRecoveryKey(s),{mode:"exclusive",ifAvailable:true},async lock=>{
        if(!current())return;if(!lock)throw Error("RECOVERY_REQUEST_BUSY");
        let pending=naturalTaskRecoveryRefresh(s);naturalTaskButtons(s);
        if(s.recoveryError)throw Error(s.recoveryError);
        if(!current())return;
        if(closeIntent){
          if(!pending||!s.source)return;
          const metadata=naturalTaskRecoveryMetadata.get(pending),saved=naturalTaskRecoveryRead(s);
          if(!metadata||metadata.key!==naturalTaskRecoveryKey(s)||(saved&&saved.raw!==metadata.raw))throw Error("RECOVERY_RECORD_CONFLICT");
          naturalTaskRecoverySource(s,metadata.record);
          const value=await api(path+"/extractions/by-key/"+encodeURIComponent(metadata.record.request_key)+"/close","POST",{identity:structuredClone(metadata.record),consent:naturalTaskCloseConsent});if(!current())return;
          if(!await naturalTaskTerminalProof(s,pending,value,current))return;
          s.status.textContent="服务端已封存此未受理原 key，迟到提交将被拒绝；原票据仍保留。请另点原 key GET，核对永久关闭凭据后才能重新审阅。";
          return;
        }
        if(submit){
          if(pending||s.saved||!s.source||!s.review||!s.ack.checked)return;
          const reviewed=s.review,body={review:structuredClone(reviewed.request),expected_review_fingerprint:reviewed.review_fingerprint,consent:reviewed.consent,artifact_write_consent:reviewed.artifact_write_consent};
          const {review_fingerprint,...reviewBody}=reviewed,reviewHash=await paHash(reviewBody);if(!current()||s.review!==reviewed)return;
          const candidateHash=await paHash(reviewed.candidate);if(!current()||s.review!==reviewed)return;
          const requestHash=await paHash(body);if(!current()||s.review!==reviewed)return;
          if(reviewHash!==review_fingerprint||candidateHash!==reviewed.candidate_fingerprint||body.consent!=="EXTRACT_THIS_SUCCESSFUL_NATURAL_SPEC_RUN_WITH_THIS_REVIEW_AND_TARGET"||body.artifact_write_consent!=="ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT")throw Error("VERSION_CONFLICT");
          const proof=reviewed.source_proof,record=naturalTaskRecoveryCheck({namespace:"pb-natural-extraction-recovery.v1",...naturalTaskRecoveryScope(s),source_app_run_id:proof.app_run_id,source_release_id:proof.release_id,source_release_fingerprint:proof.release_fingerprint,source_result_version:proof.result_version,request_key:body.review.request_key,request_fingerprint:requestHash,review_fingerprint,candidate_fingerprint:candidateHash,app_id:reviewed.app_id,runtime_id:reviewed.runtime_id,source_proof_fingerprint:reviewed.source_proof_fingerprint},s);
          naturalTaskRecoverySource(s,record);
          pending={body,review:structuredClone(reviewed)};
          naturalTaskRecoverySave(s,pending,record);naturalTaskButtons(s);
          await api(path+"/extractions","POST",pending.body);if(!current()||naturalTaskRequests.get(s.scope)!==pending)return;
        }
        if(pending)await recover(pending,lock,current);
      });
    }catch(error){
      if(current()){
        if(["RECOVERY_STORAGE_UNAVAILABLE","RECOVERY_RECORD_INVALID","RECOVERY_RECORD_CONFLICT","RECOVERY_LOCK_UNAVAILABLE"].includes(error.message))s.recoveryError=error.message;
        s.status.textContent=`回执未确认：${error.detail||error.message}。保留原意图，仅用原 key GET 恢复；不会重发。`;
        if(["PERMISSION_DENIED","GRANT_REVOKED","VERSION_CONFLICT","RESOURCE_UNAVAILABLE"].includes(error.message)){const pending=naturalTaskRequests.get(s.scope);if(pending&&naturalTaskRecoveryMetadata.has(pending)){delete pending.body;delete pending.review;}invalidateInternalContent(view);engineeringStatus(view,"当前提取内容核对未通过；原意图仍保留，请重新打开成功来源后只读核查。","error");}
      }
    }
    finally{s.busy=false;naturalTaskButtons(s);}
  };
  s.commit.onclick=()=>action(true);s.recover.onclick=()=>action(false);s.closeIntent.onclick=()=>action(false,true);
  s.open.onclick=async()=>{
    if(!naturalTaskCurrent(s)||s.busy||!s.saved)return;
    const saved=s.saved,identity=token,connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration;
    const guide=naturalFirstGuideCurrent(naturalFirstGuide)&&naturalFirstGuide.mode==="PB"&&naturalFirstGuide.extraction===s?naturalFirstGuide:null;
    let generation=appSelectionGeneration;const current=()=>token===identity&&identityConnectionGeneration===connection&&workspaceSelectionGeneration===workspace&&$("project-select").value===view.project&&generation===appSelectionGeneration&&(!guide||naturalFirstGuide===guide);
    const failed=message=>{if(!current())return;if(guide)clearNaturalFirstGuide();else clearApp();$("app-create-status").dataset.state="error";$("app-create-status").textContent=`已保存的 P-B 应用保留；打开核对未完成：${message}。请从应用目录重新选择并核对当前权限。`;};
    s.busy=true;naturalTaskButtons(s);if(guide)guide.opening=true;
    try{
      const shown=await showApp(saved.id,view.project,g=>{generation=g;if(guide&&naturalFirstGuide===guide)guide.appGeneration=g;},current,app=>{if(app.fingerprint!==saved.candidate_fingerprint||goalRunCanonical(app.candidate)!==goalRunCanonical(saved.reviewed.candidate)||app.candidate.spec_task?.source_run_id!==rid)throw Error("VERSION_CONFLICT");},guide);
      if(!current())return;
      if(!shown||!engineeringCurrent(engineering)||engineering.app!==saved.id||engineering.historyReady!==true){failed("内部历史未完整读回");return;}
      if(engineering.selectionCurrent===current)engineering.selectionCurrent=null;
      if(guide){guide.stage="internal";guide.app=saved.id;guide.view=engineering;guide.opening=false;renderNaturalFirstGuide();}
      $("internal-prepare").focus();
    }catch(error){failed(error.detail||error.message);}
    finally{s.busy=false;if(guide)guide.opening=false;naturalTaskButtons(s);}
  };
}
function renderSpecChecklist(node,value){
  const paragraph=(parent,tag,text)=>{const element=document.createElement(tag);element.textContent=text;parent.append(element);return element;};
  if(value.check_version!=="natural.spec_citations.v1"){
    paragraph(node,"pre",JSON.stringify(value,null,2));return;
  }
  paragraph(node,"p",`来源 ${value.source.resource_id} · SHA256 ${value.source.hash}`);
  const labels={requirement:"要求",condition:"条件",exception:"例外",open_question:"未决问题",unclassified:"未分类"};
  for(const item of value.items){
    const fact=document.createElement("section");fact.dataset.specKind=item.kind;node.append(fact);
    paragraph(fact,"h4",`${labels[item.kind]} · ${item.item_id}`);paragraph(fact,"p",item.summary);
    paragraph(fact,"p",item.targets.length?`模型声明关联：${item.targets.join("、")}；待人工判断关系准确性。`:item.relation_status==="UNASSIGNED"?"关联尚未确定，保留待判断。":item.decision_status==="OPEN"?"此问题仍待决定。":"");
    for(const cite of item.citations){paragraph(fact,"p",`原文字符 ${cite.start}—${cite.end}（Unicode 码点，右端不含）`);paragraph(fact,"blockquote",cite.quote);}
  }
  paragraph(node,"h4","人工未决项");const pending=document.createElement("ul");node.append(pending);for(const text of value.human_unresolved)paragraph(pending,"li",text);
  paragraph(node,"h4","未被引用覆盖的原文");for(const gap of value.feedback.uncovered)paragraph(node,"blockquote",gap.quote);
  if(!value.feedback.uncovered.length)paragraph(node,"p","未发现未被引用覆盖的非空白片段；含义与完整性仍待人工判断。");
  const full=document.createElement("details");node.append(full);paragraph(full,"summary","完整原文（原样保留）");paragraph(full,"pre",value.source_content);
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

// Per-Run inputs use the same saved app, Release and instance; old default runs remain explicit.
let pbUseView=null,pbUseRenderGeneration=0;
const pbUsePending=new Map();
function pbUseUnknown(iid){return (typeof naturalLogicUnknown==="function"&&naturalLogicUnknown(iid))||[...pbUsePending.values()].some(p=>p.instance_id===iid);}
function clearPBUse(){pbUseRenderGeneration++;if(pbUseView){pbUseView.edit++;pbUseView.panel.remove();pbUseView=null;}}
async function renderPBUse(view,freshRelease=null){
  clearPBUse();if(!engineeringCurrent(view)||!view.instance)return;
  const baseCandidate=view.draft.candidate;let candidate=baseCandidate;const isPB=baseCandidate.spec_task?.kind==="pb_natural_spec_task.v1",isPA=baseCandidate.namespace==="pa-natural-spec-app.v1"&&!baseCandidate.spec_task&&(baseCandidate.goal_application||baseCandidate.spec_binding?.kind==="pa_model_spec_material_binding.v1");
  if(!isPB&&!isPA)return;
  const opening={instance:view.instance,selection:view.instanceGeneration,workspace:workspaceSelectionGeneration,connection:identityConnectionGeneration,render:pbUseRenderGeneration};
  const openingCurrent=()=>engineeringCurrent(view)&&view.instance===opening.instance&&view.instanceGeneration===opening.selection&&workspaceSelectionGeneration===opening.workspace&&identityConnectionGeneration===opening.connection&&pbUseRenderGeneration===opening.render;
  const selected=freshRelease||await api(`/api/internal/releases/${opening.instance.release_id}`);if(!openingCurrent())return;
  const selectedFP=await paHash(selected.snapshot);if(!openingCurrent())return;
  if(selectedFP!==selected.fingerprint)throw Error("VERSION_CONFLICT");
  const logicOrigin=selected.snapshot?.natural_logic_source;
  if(selected.id!==view.instance.release_id||selected.fingerprint!==view.instance.release_fingerprint)throw Error("VERSION_CONFLICT");
  if(logicOrigin){candidate=(await naturalLogicBaseline(view,selected)).base_candidate;if(!openingCurrent())return;}
  const mode=isPB?{route:"pb-use",namespace:"pb-natural-per-run.v1",consent:"RUN_THIS_SAVED_PB_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"}:{route:"pa-use",namespace:"pa-natural-per-run.v1",consent:"RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT"};
  const instance=view.instance,scope=goalRunCanonical([token,view.project,view.app,instance.id,instance.release_id,mode.route]);
  const panel=document.createElement("section");panel.id="pb-use-panel";
  panel.innerHTML='<h3>使用同一保存逻辑处理新材料</h3><p>每个运行单独选择材料和自己的 Goal，核对精确预览后确认。原应用、版本和历史保持；自然规范模型默认关闭，语义 UNKNOWN，人工 PENDING。</p><button type="button" id="pb-use-prepare">准备本次新材料与 Goal</button><label>本次材料<select id="pb-use-material"></select></label><label>本次 Goal<select id="pb-use-goal"></select></label><button type="button" id="pb-use-preview">预览本次绑定</button><pre id="pb-use-proof"></pre><label><input type="checkbox" id="pb-use-ack">确认上述材料、Goal、逻辑、预算与仅本次材料读取授权</label><button type="button" id="pb-use-submit">确认并运行</button><button type="button" id="pb-use-recover">仅读原 key 回执</button><p id="pb-use-status" role="status"></p>';
  $("internal-panel").append(panel);
  const s={view,instance,scope,panel,edit:0,review:null,busy:false,workspace:workspaceSelectionGeneration,connection:identityConnectionGeneration,selection:view.instanceGeneration};pbUseView=s;
  const current=()=>pbUseView===s&&panel.isConnected&&engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===s.selection&&s.workspace===workspaceSelectionGeneration&&s.connection===identityConnectionGeneration;
  const material=panel.querySelector('#pb-use-material'),goal=panel.querySelector('#pb-use-goal'),preview=panel.querySelector('#pb-use-preview'),ack=panel.querySelector('#pb-use-ack'),submit=panel.querySelector('#pb-use-submit'),recover=panel.querySelector('#pb-use-recover'),status=panel.querySelector('#pb-use-status'),proof=panel.querySelector('#pb-use-proof');
  const buttons=()=>{if(!current())return;const pending=pbUsePending.get(scope),other=engineeringPending.has(instance.id)||(!pending&&pbUseUnknown(instance.id));material.disabled=goal.disabled=!!pending||other||s.busy;preview.disabled=!!pending||other||s.busy||!material.value||!goal.value;ack.disabled=!!pending||other||s.busy||!s.review;submit.disabled=!!pending||other||s.busy||!s.review||!ack.checked;recover.disabled=!pending||s.busy;panel.querySelector('#pb-use-prepare').disabled=!!pending||other||s.busy||view.busy;};
  s.buttons=buttons;
  const prepare=panel.querySelector('#pb-use-prepare');
  prepare.onclick=()=>beginNaturalUsePreparation(s,current);
  const edit=()=>{s.edit++;s.review=null;ack.checked=false;proof.textContent="";buttons();};material.onchange=goal.onchange=edit;ack.onchange=buttons;buttons();
  try{const [materials,cards]=await Promise.all([api(`/api/projects/${view.project}/resources`),api(`/api/projects/${view.project}/goal-cards`)]);if(!current())return;
    material.replaceChildren(new Option("明确选择本次 TXT/MD",""),...materials.filter(x=>['txt','md'].includes(x.format)).map(x=>new Option(`${x.name} · ${x.id}`,x.id)));
    goal.replaceChildren(new Option("明确选择本次 Goal",""),...cards.items.map(x=>new Option(`${x.title} · v${x.version} · ${x.id}`,x.id)));
    status.textContent=pbUsePending.has(scope)?"保留本次未知请求，仅原 key GET 恢复；不能重发或另建意图。":"请选择材料与匹配的已保存 Goal；预览不运行模型、不写资源。";
  }catch(error){if(current())status.textContent=error.message;}buttons();
  preview.onclick=async()=>{
    if(!current()||s.busy||pbUseUnknown(instance.id)||engineeringPending.has(instance.id))return;s.review=null;ack.checked=false;proof.textContent="";s.busy=true;buttons();const generation=s.edit,cid=goal.value,rid=material.value,valid=()=>current()&&generation===s.edit&&goal.value===cid&&material.value===rid;
    try{const card=await api(`/api/goal-cards/${cid}`);if(!valid())return;const snapshot=card.history?.[0]?.snapshot,refs=snapshot?.resource_snapshots;
      if(!refs||refs.length!==1||refs[0].resource_id!==rid)throw Error("所选 Goal 必须明确引用本次材料");
      const request={expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,expected_app_fingerprint:view.draft.fingerprint,expected_recipe_fingerprint:await paHash(candidate.spec_recipe),resource_id:rid,card_id:cid,expected_goal_version:card.version,expected_goal_fingerprint:card.fingerprint,expected_source_hash:refs[0].hash,request_key:crypto.randomUUID()};
      if(!valid())return;
      const result=await api(`/api/internal/instances/${instance.id}/${mode.route}-reviews`,"POST",request);if(!valid())return;
      const {review_fingerprint,...body}=result,fp=await paHash(body);if(!valid())return;
      const goalSnapshotFP=await paHash(result.target_goal?.snapshot);if(!valid())return;
      const effectiveFP=await paHash(result.effective_candidate);if(!valid())return;
      if(effectiveFP!==result.effective_fingerprint)throw Error("VERSION_CONFLICT");
      if(result.target_goal?.version!==card.version||result.target_goal.fingerprint!==card.fingerprint||goalSnapshotFP!==card.fingerprint||goalRunCanonical(result.target_goal.snapshot)!==goalRunCanonical(snapshot)||goalRunCanonical(result.effective_candidate?.goal)!==goalRunCanonical(snapshot.content)||result.effective_candidate?.manifest?.goal_ref!==cid)throw Error("VERSION_CONFLICT");
      if(result.namespace!==mode.namespace||result.app_id!==view.app||result.instance_id!==instance.id||result.release_id!==instance.release_id||result.release_fingerprint!==instance.release_fingerprint||result.runtime_id!==instance.runtime_id||result.principal_id!==instance.principal_id||result.project_id!==view.project||goalRunCanonical(result.request)!==goalRunCanonical(request)||fp!==review_fingerprint||result.saved_app_fingerprint!==view.draft.fingerprint||result.recipe_fingerprint!==request.expected_recipe_fingerprint||result.variable_bindings.resource_id!==rid||result.variable_bindings.source_hash!==request.expected_source_hash||result.target_goal.card_id!==cid||goalRunCanonical(result.effective_candidate.spec_recipe)!==goalRunCanonical(candidate.spec_recipe)||result.consent!==mode.consent||result.new_model_requests!==0||result.semantic_status!=="UNKNOWN"||result.owner_acceptance!=="PENDING"||result.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
      if(logicOrigin){const savedFP=await paHash(candidate);if(!valid())return;if(goalRunCanonical(result.saved_logic_source?.origin)!==goalRunCanonical(logicOrigin)||result.saved_logic_source?.effective_fingerprint!==savedFP||result.saved_logic_source?.recipe_fingerprint!==request.expected_recipe_fingerprint||goalRunCanonical(result.effective_candidate.logic_revision)!==goalRunCanonical(candidate.logic_revision)||result.effective_candidate.manifest.revision!==candidate.manifest.revision||result.effective_candidate.actions[2].revision!==candidate.actions[2].revision||["goal_application","spec_binding","spec_task"].some(k=>k in result.effective_candidate))throw Error("VERSION_CONFLICT");}
      s.review=result;proof.textContent=JSON.stringify(result,null,2);status.textContent="精确预览已核对：同一 app/Release/实例、保存逻辑、此次材料/Goal与权限预算。尚未运行模型。";
    }catch(error){if(valid())status.textContent=error.detail||error.message;}finally{s.busy=false;buttons();}
  };
  const receipt=async pending=>{
    const valid=()=>current()&&pbUsePending.get(scope)===pending;
    const value=await api(`/api/internal/instances/${instance.id}/${mode.route}-requests/${encodeURIComponent(pending.body.review.request_key)}`);if(!valid())return;
    const fp=await paHash(pending.body);if(!valid())return;
    if(value.namespace!==mode.namespace||value.principal_id!==instance.principal_id||value.project_id!==view.project||value.app_id!==view.app||value.instance_id!==instance.id||value.release_id!==instance.release_id||value.request_key!==pending.body.review.request_key||value.request_fingerprint!==fp||goalRunCanonical(value.request)!==goalRunCanonical(pending.body)||goalRunCanonical(value.reviewed)!==goalRunCanonical(pending.review)||value.review_fingerprint!==pending.body.expected_review_fingerprint||value.effective_fingerprint!==pending.review.effective_fingerprint||!/^run_[a-f0-9]{32}$/.test(value.run_id)||!/^iapprun_[a-f0-9]{32}$/.test(value.app_run_id)||value.new_model_requests!==0||value.semantic_status!=="UNKNOWN"||value.owner_acceptance!=="PENDING"||value.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
    pbUsePending.delete(scope);status.textContent=`已核对原 key ${value.request_key} 的独立运行 ${value.run_id}；不会重新提交。`;s.review=null;ack.checked=false;
    await showInternalInstance(instance.id,view);if(engineeringCurrent(view)&&view.instance?.id===instance.id&&workspaceSelectionGeneration===s.workspace)await showInternalRun(value.run_id,view,view.instance);
  };
  const action=async commit=>{if(!current()||s.busy)return;let pending=pbUsePending.get(scope);if(commit){if(pending||pbUseUnknown(instance.id)||engineeringPending.has(instance.id)||!s.review||!ack.checked)return;
    if(isPB){
      const reviewed=s.review,edit=s.edit;s.busy=true;buttons();
      try{const caps=await api("/api/capabilities");if(!current()||s.review!==reviewed||s.edit!==edit)return;
        const available=caps.natural_spec_generation;
        if(available?.version!=="natural-spec-generation-availability.v1"||available.availability!=="OFFLINE_TEST_ONLY"||available.provider!=="intern-s2"||available.live_request_allowance!==0||caps.connection?.mode!=="MOCK"||caps.connection?.model!=="intern-s2"){status.textContent="已停止：当前没有可用的受限自然执行配置；真实模型额度0，未提交本次 Run。";return;}
      }catch(error){if(current())status.textContent=`执行配置读取失败：${error.message}；未提交本次 Run。`;return;}
      finally{s.busy=false;buttons();}
      if(!current()||s.review!==reviewed||s.edit!==edit)return;
      if(pbUseUnknown(instance.id)||engineeringPending.has(instance.id)||view.busy){status.textContent="此实例已有正在处理或回执未确认的操作；未提交本次 Run。请先核对原操作。";return;}
    }
    pending={instance_id:instance.id,body:{review:structuredClone(s.review.request),expected_review_fingerprint:s.review.review_fingerprint,consent:s.review.consent},review:structuredClone(s.review)};pbUsePending.set(scope,pending);$("internal-run-submit").disabled=true;}if(!pending)return;s.busy=true;buttons();try{if(commit){try{await api(`/api/internal/instances/${instance.id}/${mode.route}-runs`,"POST",pending.body);}catch(error){
      if(await internalSubmissionRejected(error,view,instance,pending,mode.route+"-runs",pending.body)&&pbUsePending.get(scope)===pending){pbUsePending.delete(scope);s.review=null;if(current()){edit();status.textContent="明确未受理；可修正材料/Goal并重新预览确认。原成功结果保留，不会自动提交。";engineeringButtons(view);}if(pbUseView?.scope===scope&&pbUseView!==s)pbUseView.buttons();if(engineering&&engineeringCurrent(engineering)&&engineering.instance?.id===instance.id)engineeringButtons(engineering);return;}throw error;
    }if(!current()||pbUsePending.get(scope)!==pending)return;}await receipt(pending);}catch(error){if(current())status.textContent=`回执未确认：${error.detail||error.message}。仅原 key GET 恢复；不重发。`;}finally{s.busy=false;buttons();}};
  submit.onclick=()=>action(true);recover.onclick=()=>action(false);
}

"use strict";
// The original selection and key stay frozen across unknown responses. No POST retry.
let naturalLogicView=null;
const naturalLogicPending=new Map();
const naturalLogicKey=v=>JSON.stringify([v.token,v.project,v.app,v.instance.id]);
const naturalLogicUnknown=iid=>[...naturalLogicPending.values()].some(p=>p.instance===iid&&p.token===token);
const naturalLogicPath=v=>`/api/internal/instances/${v.instance.id}/logic-patches`;
const naturalLogicCurrent=s=>naturalLogicView===s&&engineeringCurrent(s.view)&&s.view.instance===s.instance&&s.workspace===workspaceSelectionGeneration&&s.connection===identityConnectionGeneration;
function clearNaturalLogic(){naturalLogicView=null;$("natural-logic-panel").hidden=true;$("natural-logic-proof").textContent="";for(const id of ["natural-logic-check-ack","natural-logic-version-ack"])$(id).checked=false;}
function naturalLogicButtons(){const s=naturalLogicView;if(!s||!naturalLogicCurrent(s))return;const blocked=s.view.busy||naturalLogicPending.has(naturalLogicKey(s.view));$("natural-logic-key").readOnly=blocked||!!s.preview;$("natural-logic-preview").disabled=blocked;$("natural-logic-mode").disabled=blocked;$("natural-logic-check").disabled=blocked||!s.preview||!!s.run||!$("natural-logic-check-ack").checked;$("natural-logic-version").disabled=blocked||!s.proof||!!s.approval||!$("natural-logic-version-ack").checked;$("natural-logic-commit").disabled=blocked||!s.approval||s.approval.expires_at*1000<=Date.now()||!$("natural-logic-version-ack").checked;$("natural-logic-recover").disabled=s.view.busy;$("natural-logic-control-read").disabled=s.view.busy||!($("natural-logic-key").value.trim());$("natural-logic-cancel").disabled=s.view.busy||!s.control||["SUCCEEDED","FAILED","CANCELLED"].includes(s.control.status);engineeringButtons(s.view);}
async function naturalLogicBaseline(view,release,anchor=null){
 const baseline=await api(`/api/internal/instances/${view.instance.id}/logic-patches/context`);
 const ctx=baseline?.context,depth=ctx?.parent_logic?.depth;
 if(![1,2].includes(depth)||baseline.namespace!=="natural-local-logic.v1.context"||ctx.instance_id!==view.instance.id||ctx.release_id!==release.id||ctx.release_fingerprint!==release.fingerprint||ctx.draft_fingerprint!==view.draft.fingerprint||ctx.principal_id!==view.instance.principal_id||ctx.project_id!==view.project||ctx.app_id!==view.app||ctx.runtime_id!==view.draft.runtime_id||ctx.instance_revision!==view.instance.revision||ctx.data_version!==view.instance.data_version||!deliverySame(ctx.parent_logic.origin,release.snapshot.natural_logic_source))throw Error("VERSION_CONFLICT");
 let expected=structuredClone(release.snapshot.draft.candidate);
 for(let i=0;i<depth;i++){const recipe=structuredClone(expected.spec_recipe),q=recipe.steps[2],prior=recipe.steps[1],consume=!("prior_items" in q.inputs);for(const [name,field]of[["prior_items","items"],["prior_feedback","feedback"]]){if(consume)q.inputs[name]={source:"step",ref:prior.step_id,field};else delete q.inputs[name];}q.depends_on=[recipe.steps[0].step_id,...(consume?[prior.step_id]:[])];expected=naturalLogicExpectedCandidate(expected,recipe,consume);}
 if(!deliverySame(expected,baseline.base_candidate)||ctx.parent_logic.effective_fingerprint!==await deliveryDigest(expected)||baseline.remaining_adjustments!==2-depth)throw Error("VERSION_CONFLICT");
 anchor=anchor||await api(`/api/projects/${view.project}/apps/${view.app}/delivery-graph`);
 if(!await deliveryGraphSeal(anchor,{app:view.draft,id:view.app,project:view.project})||ctx.parent_logic.anchor_graph_fingerprint!==anchor.graph_fingerprint)throw Error("VERSION_CONFLICT");
 const effective=baseline.graph,c={app:{...view.draft,candidate:expected,fingerprint:await deliveryDigest(expected)},id:view.app,project:view.project};
 if(!await deliveryGraphSeal(effective,c)||ctx.graph_fingerprint!==effective.graph_fingerprint||ctx.graph_revision!==anchor.graph_revision||!deliverySame(effective.source_versions,anchor.source_versions)||effective.graph.nodes.length!==anchor.graph.nodes.length)throw Error("VERSION_CONFLICT");
 for(const node of effective.graph.nodes){const old=anchor.graph.nodes.find(n=>n.key===node.key);if(!old||old.id!==node.id||old.locked!==node.locked)throw Error("VERSION_CONFLICT");const definition=structuredClone(old.definition);let revision=old.revision;if(node.kind==="MANIFEST"){Object.assign(definition,structuredClone(expected.manifest));for(const step of definition.workflow)for(const b of Object.values(step.inputs))if(!("ref"in b))b.ref=null;revision=expected.manifest.revision;}else if(node.key==="action:"+expected.spec_recipe.steps[2].step_id){definition.action=structuredClone(expected.actions[2]);Object.assign(definition.step,structuredClone(expected.manifest.workflow[2]));for(const b of Object.values(definition.step.inputs))if(!("ref"in b))b.ref=null;revision=expected.actions[2].revision;}else if(["ARTIFACT","VIEW"].includes(node.kind))revision=expected.manifest.revision;const {content_fingerprint,...body}=node,expectedBody={...old,definition,revision};delete expectedBody.content_fingerprint;if(!deliverySame(body,expectedBody))throw Error("VERSION_CONFLICT");}
 const prior=expected.actions[1].action_id,q=expected.actions[2].action_id;const edges=anchor.graph.edges.filter(e=>!(e.type==="DATA"&&e.upstream===prior&&e.downstream===q));if("prior_items"in expected.spec_recipe.steps[2].inputs)edges.push({upstream:prior,downstream:q,type:"DATA",provenance:"DECLARED"});
 if(!deliverySame([...effective.graph.edges].map(deliveryCanonical).sort(),edges.map(deliveryCanonical).sort())||!deliverySame(effective.graph.unknown_dependencies,anchor.graph.unknown_dependencies))throw Error("VERSION_CONFLICT");
 const sealed=new Map(),g=effective.graph;
 while(sealed.size<g.nodes.length){const ready=g.nodes.filter(n=>!sealed.has(n.id)&&g.edges.filter(e=>e.downstream===n.id).every(e=>sealed.has(e.upstream)));if(!ready.length)throw Error("VERSION_CONFLICT");for(const node of ready){const incoming=[];for(const edge of g.edges.filter(e=>e.downstream===node.id)){const upstream=sealed.get(edge.upstream),value={...edge,revision:upstream.revision,content_fingerprint:upstream.content_fingerprint};incoming.push({value,hash:await deliveryDigest(value)});}incoming.sort((x,y)=>x.hash<y.hash?-1:x.hash>y.hash?1:0);const {content_fingerprint,...body}=node;if(await deliveryDigest({...body,upstream_versions:incoming.map(x=>x.value)})!==content_fingerprint)throw Error("VERSION_CONFLICT");sealed.set(node.id,node);}}
 return baseline;
}
async function openNaturalLogic(view,freshRelease=null){
 clearNaturalLogic();
 if(!engineeringCurrent(view)||!view.instance||view.draft.candidate.namespace!=="pa-natural-spec-app.v1")return;
 const instance=view.instance,selection=view.instanceGeneration,workspace=workspaceSelectionGeneration,connection=identityConnectionGeneration;
 const current=()=>engineeringCurrent(view)&&view.instance===instance&&view.instanceGeneration===selection&&workspaceSelectionGeneration===workspace&&identityConnectionGeneration===connection;
 const release=freshRelease||await api(`/api/internal/releases/${instance.release_id}`);
 if(!current())return;
 const releaseHash=await paHash(release.snapshot);
 if(!current())return;
 if(release.id!==instance.release_id||release.fingerprint!==instance.release_fingerprint||releaseHash!==release.fingerprint)throw Error("VERSION_CONFLICT");
 let baseline=null;
 if(release.snapshot.natural_logic_source){
  baseline=await naturalLogicBaseline(view,release);
  if(!current())return;
  if(baseline.remaining_adjustments===0)return;
 }
 const steps=(baseline?.base_candidate||view.draft.candidate).spec_recipe.steps;
 if(steps.length!==6||steps[1].operator!=="model.spec.requirements"||steps[2].operator!=="model.spec.qualifiers"||!current())return;
 const s={view,instance,release,baseline,workspace,connection,selection};naturalLogicView=s;
 $("natural-logic-panel").hidden=false;$("natural-logic-mode").value=String(!("prior_items" in steps[2].inputs));
 $("natural-logic-status").textContent="只调整第二模型的前序结果/反馈依赖；节点ID、原目标、验收标准、来源和限额保留。重验隔离实例，语义仍UNKNOWN。";
 const pending=naturalLogicPending.get(naturalLogicKey(view));if(pending)$("natural-logic-key").value=pending.key;
 naturalLogicButtons();
}

async function naturalLogicReadGraph(s){
 const c={app:s.view.draft,id:s.view.app,project:s.view.project};
 const graph=await api(`/api/projects/${s.view.project}/apps/${s.view.app}/delivery-graph`);
 if(!naturalLogicCurrent(s)||!await deliveryGraphSeal(graph,c)||!naturalLogicCurrent(s))throw Error("VERSION_CONFLICT");
 if(s.release.snapshot.natural_logic_source){const baseline=await naturalLogicBaseline(s.view,s.release,graph);if(!naturalLogicCurrent(s))throw Error("VERSION_CONFLICT");s.baseline=baseline;s.graph=baseline.graph;}else{s.graph=graph;}return s.graph;
}
async function naturalLogicImpact(s,value,key){
 const graph=s.graph.graph,p=value.impact,changed=s.release.snapshot.draft.candidate.actions[2].action_id;
 const node=graph.nodes.find(n=>n.id===changed),all=graph.nodes.map(n=>n.id).sort();
 if(!node||graph.nodes.some(n=>n.locked)||!graph.unknown_dependencies.length||graph.unknown_dependencies.some(u=>u.scope!=="APP"))return false;
 const request={project_id:s.view.project,app_id:s.view.app,request_key:key,changes:[{node_id:node.id,expected_revision:node.revision,expected_content_fingerprint:node.content_fingerprint}]};
 const expected={schema_version:"delivery-change-plan.v1",graph_fingerprint:graph.graph_fingerprint,context_fingerprint:graph.context_fingerprint,request_key:key,request_fingerprint:await deliveryDigest(request),changed_nodes:[changed],definite_impact:[changed],uncertain_impact:all.filter(id=>id!==changed),revalidation_nodes:all,revalidation_scope:"APP",project_id:s.view.project,app_id:s.view.app,revalidation_checks:graph.nodes.filter(n=>n.kind==="CHECK").map(n=>n.id).sort(),invalidated_packages:graph.nodes.filter(n=>["MANIFEST","RELEASE"].includes(n.kind)).map(n=>n.id).sort(),retained_objects:[],global_invariants:["current_authority","current_versions","strict_preflight","dependency_completeness","manual_locks"],patch_executed:false,business_write_performed:false,publishable:false};
 expected.plan_fingerprint=await deliveryDigest(expected);return deliverySame(p,expected);
}
function naturalLogicExpectedCandidate(base,recipe,consume){
 const candidate=structuredClone(base);for(const key of ["goal_application","spec_binding","spec_task"])delete candidate[key];
 const revision=base.manifest.revision+1;if(![2,3].includes(revision))throw Error("VERSION_CONFLICT");
 candidate.spec_recipe=recipe;candidate.logic_revision={version:"natural-local-logic.v1",step_id:recipe.steps[2].step_id};if(revision===3)candidate.logic_revision.revision=3;
 candidate.manifest.revision=revision;candidate.manifest.origin="goal";candidate.manifest.source_run_ref=null;candidate.manifest.action_bindings[2].revision=revision;
 candidate.manifest.workflow[2].inputs=structuredClone(recipe.steps[2].inputs);candidate.manifest.workflow[2].depends_on=[...recipe.steps[2].depends_on];
 const action=candidate.actions[2];action.revision=revision;
 for(const name of ["prior_items","prior_feedback"]){if(consume)action.input_schema.properties[name]=structuredClone(base.actions[1].output_schema.properties[name==="prior_items"?"items":"feedback"]);else delete action.input_schema.properties[name];}
 action.input_schema.required=Object.keys(action.input_schema.properties);return candidate;
}
async function naturalLogicValidatePreview(s,value,key){
  const ctx=value?.context,candidate=value?.effective_candidate;
  await naturalLogicReadGraph(s);const base=s.baseline?.base_candidate||s.release.snapshot.draft.candidate;
  if(s.baseline&&!deliverySame(ctx.parent_logic,s.baseline.context.parent_logic))throw Error("VERSION_CONFLICT");
  const goal=await api(`/api/goal-cards/${base.manifest.goal_ref}`);if(!naturalLogicCurrent(s))return;
  if(!ctx||goal.id!==base.manifest.goal_ref||ctx.goal.version!==goal.version||ctx.goal.fingerprint!==goal.fingerprint||!deliverySame(ctx.goal.snapshot.content,goal.content)||ctx.graph_fingerprint!==s.graph.graph_fingerprint||ctx.graph_revision!==s.graph.graph_revision||!await naturalLogicImpact(s,value,key))throw Error("VERSION_CONFLICT");
  const copy=structuredClone(value),fp=copy.preview_fingerprint;delete copy.preview_fingerprint;
  if(!ctx||value.namespace!=="natural-local-logic.v1"||value.request_key!==key||fp!==await deliveryDigest(copy)||value.semantic_status!=="UNKNOWN"||value.formal_publication_enabled!==false||value.owner_acceptance!=="PENDING"||ctx.principal_id!==s.instance.principal_id||ctx.instance_id!==s.instance.id||ctx.app_id!==s.view.app||ctx.project_id!==s.view.project||ctx.runtime_id!==s.view.draft.runtime_id||ctx.release_id!==s.release.id||ctx.release_fingerprint!==s.release.fingerprint||ctx.draft_fingerprint!==s.view.draft.fingerprint||ctx.instance_revision!==s.instance.revision||ctx.data_version!==s.instance.data_version||ctx.goal.card_id!==base.manifest.goal_ref||!deliverySame(ctx.goal.snapshot.content,base.goal)||ctx.source.resource_id!==base.manifest.data_bindings[0].resource_ref||ctx.source.hash!==base.source_hash||value.effective_fingerprint!==await deliveryDigest(candidate))throw Error("VERSION_CONFLICT");
  const recipe=structuredClone(base.spec_recipe),q=recipe.steps[2],prior=recipe.steps[1],consume=!("prior_items" in q.inputs);
  for(const [name,field] of [["prior_items","items"],["prior_feedback","feedback"]]){if(consume)q.inputs[name]={source:"step",ref:prior.step_id,field};else delete q.inputs[name];}
  q.depends_on=[recipe.steps[0].step_id,...(consume?[prior.step_id]:[])];
  if(!deliverySame(candidate,naturalLogicExpectedCandidate(base,recipe,consume))||!deliverySame(candidate.spec_recipe,recipe)||!deliverySame(candidate.goal,base.goal)||candidate.source_hash!==base.source_hash||!deliverySame(candidate.manifest.runtime_limits,base.manifest.runtime_limits)||!deliverySame(candidate.manifest.permission_requirements,base.manifest.permission_requirements)||candidate.manifest.revision!==base.manifest.revision+1||candidate.actions.length!==6||candidate.actions[2].revision!==base.manifest.revision+1||value.modified_step_id!==q.step_id||value.original_recipe_fingerprint!==await deliveryDigest(base.spec_recipe)||value.new_recipe_fingerprint!==await deliveryDigest(recipe)||value.impact.graph_fingerprint!==ctx.graph_fingerprint||value.impact.revalidation_scope!=="APP"||!deliverySame(value.impact.changed_nodes,[base.actions[2].action_id]))throw Error("VERSION_CONFLICT");
  for(let i=0;i<6;i++){if(candidate.actions[i].action_id!==base.actions[i].action_id||candidate.manifest.workflow[i].step_id!==base.manifest.workflow[i].step_id||(i!==2&&!deliverySame(candidate.actions[i],base.actions[i])))throw Error("VERSION_CONFLICT");}
  const preserved=await Promise.all(base.actions.map(async(a,i)=>i===2?null:{step_id:base.spec_recipe.steps[i].step_id,action_id:a.action_id,definition_fingerprint:await deliveryDigest(a)}));
  if(!deliverySame(value.preserved_action_definitions,preserved.filter(Boolean)))throw Error("VERSION_CONFLICT");
  if(!naturalLogicCurrent(s))return;s.preview=value;s.key=key;$("natural-logic-key").value=key;$("natural-logic-mode").value=String(consume);
}
async function naturalLogicRender(s,value,stage,key){
  if(!naturalLogicCurrent(s))return;
  if(stage==="previews")await naturalLogicValidatePreview(s,value,key);
  if(stage==="checks"&&value.status==="PASS"){
    const copy=structuredClone(value),fp=copy.check_fingerprint;delete copy.check_fingerprint;
    const control=await api(naturalLogicPath(s.view)+"/check-controls/"+encodeURIComponent(key));if(!naturalLogicCurrent(s))return;
    if(control.namespace!=="natural-local-logic.v1.control"||control.principal_id!==s.instance.principal_id||control.instance_id!==s.instance.id||control.request_key!==key||control.status!=="SUCCEEDED"||control.cancel_intent||control.run_id!==value.run_id||control.check_instance_id!==value.check_instance_id||control.check_fingerprint!==fp||control.actual_proof_fingerprint!==value.actual_proof_fingerprint||fp!==await deliveryDigest(copy)||value.namespace!=="natural-local-logic.v1"||value.preview_fingerprint!==s.preview?.preview_fingerprint||value.effective_fingerprint!==s.preview.effective_fingerprint||value.semantic_status!=="UNKNOWN"||value.owner_acceptance!=="PENDING"||value.citation_status!=="PASS"||(s.run&&s.run!==value.run_id))throw Error("VERSION_CONFLICT");if(!naturalLogicCurrent(s))return;s.proof=value;s.run=value.run_id;s.checkInstance=value.check_instance_id;
  }else if(stage==="checks"&&value.run_id){if(!/^run_[a-f0-9]{32}$/.test(value.run_id)||!/^iapprun_[a-f0-9]{32}$/.test(value.app_run_id)||!/^iinstance_[a-f0-9]{32}$/.test(value.check_instance_id)||value.check_instance_id===s.instance.id||(s.run&&s.run!==value.run_id))throw Error("VERSION_CONFLICT");s.run=value.run_id;s.checkInstance=value.check_instance_id;}
  if(stage==="version-approvals"){
    const origin=value.snapshot?.natural_logic_source;
    if(value.namespace!=="INTERNAL_ENGINEERING_ONLY"||value.formal_publication_enabled!==false||value.snapshot_fingerprint!==await deliveryDigest(value.snapshot)||!deliverySame(value.snapshot.draft,s.release.snapshot.draft)||!deliverySame(value.snapshot.data_schema,s.release.snapshot.data_schema)||origin?.namespace!=="natural-local-logic.v1"||origin.instance_id!==s.instance.id||origin.preview_key!==key||origin.preview_fingerprint!==s.preview.preview_fingerprint||origin.check_fingerprint!==s.proof.check_fingerprint||!deliverySame(value.snapshot.check_evidence,{...s.proof,original_draft_fingerprint:s.view.draft.fingerprint})||!(value.expires_at*1000>Date.now()||s.readCommitted))throw Error("VERSION_CONFLICT");
    const detail=await api(`/api/internal/approvals/${value.id}`);
    if(!naturalLogicCurrent(s))return;
    if(detail.id!==value.id||detail.fingerprint!==value.fingerprint||detail.principal_id!==s.preview.context.principal_id||detail.project_id!==s.view.project||!deliverySame(detail.payload.snapshot,value.snapshot)||await deliveryDigest(detail.payload)!==value.fingerprint)throw Error("VERSION_CONFLICT");s.approval=value;$("natural-logic-version-ack").checked=false;
  }
  if(stage==="commit"){
    if(value.approval_id!==s.approval?.id||value.fingerprint!==s.approval.snapshot_fingerprint||!deliverySame(value.snapshot,s.approval.snapshot))throw Error("VERSION_CONFLICT");
    $("natural-logic-status").textContent=`新内部版本 ${value.id} 已确认；原实例和旧版本保留。可从内部历史明确选择新版本。`;s.approval=null;$("natural-logic-version-ack").checked=false;
  }
  if(!naturalLogicCurrent(s))return;$("natural-logic-proof").textContent=JSON.stringify(stage==="version-approvals"?{...value,approved_logic_preview:s.preview,actual_check:s.proof}:value,null,2);naturalLogicButtons();
}
async function naturalLogicRecover(s,p){
  if(p.stage!=="previews"&&!s.preview){const preview=await api(naturalLogicPath(s.view)+"/previews/"+encodeURIComponent(p.key));await naturalLogicValidatePreview(s,preview,p.key);}
  if(["version-approvals","commit"].includes(p.stage)&&!s.proof){const proof=await api(naturalLogicPath(s.view)+"/checks/"+encodeURIComponent(p.key));await naturalLogicRender(s,proof,"checks",p.key);}
  let value;
  if(p.stage==="commit"){
    const a=await api(naturalLogicPath(s.view)+"/version-approvals/"+encodeURIComponent(p.key));s.readCommitted=true;try{await naturalLogicRender(s,a,"version-approvals",p.key);}finally{s.readCommitted=false;}
    const history=await api(`/api/internal/apps/${s.view.app}/releases`);value=history.items.find(r=>r.approval_id===a.id);if(!value)throw Error("OUTCOME_UNKNOWN");
  }else value=await api(naturalLogicPath(s.view)+"/"+p.stage+"/"+encodeURIComponent(p.key));
  if(!naturalLogicCurrent(s))return;await naturalLogicRender(s,value,p.stage,p.key);if(naturalLogicPending.get(naturalLogicKey(s.view))===p)naturalLogicPending.delete(naturalLogicKey(s.view));naturalLogicButtons();
}
async function naturalLogicWrite(stage,body,url){const s=naturalLogicView;if(!s||!naturalLogicCurrent(s)||s.view.busy||naturalLogicPending.has(naturalLogicKey(s.view)))return;const p={token:s.view.token,instance:s.instance.id,key:body.request_key||s.key,stage,body:structuredClone(body),url:url||naturalLogicPath(s.view)+"/"+stage};naturalLogicPending.set(naturalLogicKey(s.view),p);s.view.busy=true;naturalLogicButtons();try{const value=await api(url||naturalLogicPath(s.view)+"/"+stage,"POST",body);if(!naturalLogicCurrent(s))return;await naturalLogicRender(s,value,stage,p.key);await naturalLogicRecover(s,p);}catch(e){const proof=e.submissionRejection;if([400,403,409,422].includes(e.httpStatus)&&["INVALID_INPUT","VERSION_CONFLICT","GRANT_REVOKED","PERMISSION_DENIED","RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY","LOCK_CONFLICT"].includes(e.message)&&proof?.namespace==="natural-local-logic.v1.rejection"&&proof.instance_id===s.instance.id&&proof.principal_id===s.instance.principal_id&&proof.stage===stage&&proof.request_key===p.key&&proof.request_fingerprint===await deliveryDigest(p.body)&&proof.acceptance==="NOT_ACCEPTED"&&proof.previous_request==="ABSENT"&&proof.phase==="TX_ROLLED_BACK"&&naturalLogicPending.get(naturalLogicKey(s.view))===p)naturalLogicPending.delete(naturalLogicKey(s.view));if(naturalLogicCurrent(s))$("natural-logic-status").textContent=`${e.detail||e.message}；保留原key，仅GET读取，不自动重发。`;}finally{s.view.busy=false;naturalLogicButtons();}}
$("natural-logic-preview").onclick=safe(async()=>{const s=naturalLogicView;if(!s||s.view.busy||naturalLogicUnknown(s.instance.id))return;const key=crypto.randomUUID();$("natural-logic-key").value=key;s.preview=null;s.proof=null;s.approval=null;$("natural-logic-check-ack").checked=false;$("natural-logic-version-ack").checked=false;s.view.busy=true;naturalLogicButtons();try{const graph=await naturalLogicReadGraph(s);if(!naturalLogicCurrent(s))return;s.view.busy=false;await naturalLogicWrite("previews",{request_key:key,expected_revision:s.instance.revision,expected_release_fingerprint:s.release.fingerprint,expected_graph_fingerprint:graph.graph_fingerprint,consume_prior_feedback:$("natural-logic-mode").value==="true"});}finally{s.view.busy=false;naturalLogicButtons();}});
$("natural-logic-check").onclick=safe(()=>{const s=naturalLogicView;if(s?.preview&&$("natural-logic-check-ack").checked)return naturalLogicWrite("checks",{request_key:s.key,expected_preview_fingerprint:s.preview.preview_fingerprint,consent:"RUN_EXACT_LOCAL_LOGIC_CHECK_KEEP_ORIGINAL"});});
$("natural-logic-version").onclick=safe(()=>{const s=naturalLogicView;if(s?.proof&&$("natural-logic-version-ack").checked)return naturalLogicWrite("version-approvals",{request_key:s.key,expected_check_fingerprint:s.proof.check_fingerprint,consent:"CREATE_EXACT_CHECKED_INTERNAL_LOGIC_VERSION"});});
$("natural-logic-commit").onclick=safe(()=>{const s=naturalLogicView;if(s?.approval&&$("natural-logic-version-ack").checked)return naturalLogicWrite("commit",{fingerprint:s.approval.fingerprint},`/api/internal/approvals/${s.approval.id}/commit`);});
$("natural-logic-recover").onclick=safe(async()=>{const s=naturalLogicView;if(!s||s.view.busy)return;const p=naturalLogicPending.get(naturalLogicKey(s.view))||{key:$("natural-logic-key").value.trim(),stage:$("natural-logic-stage").value};s.view.busy=true;naturalLogicButtons();try{await naturalLogicRecover(s,p);}finally{s.view.busy=false;naturalLogicButtons();}});
for(const id of ["natural-logic-check-ack","natural-logic-version-ack"])$(id).onchange=naturalLogicButtons;
$("natural-logic-mode").onchange=()=>{const s=naturalLogicView;if(s){s.preview=null;s.proof=null;s.approval=null;}$("natural-logic-check-ack").checked=false;$("natural-logic-version-ack").checked=false;naturalLogicButtons();};

$("natural-logic-control-read").onclick=safe(async()=>{
 const s=naturalLogicView;if(!s||!naturalLogicCurrent(s)||s.view.busy)return;
 const key=naturalLogicPending.get(naturalLogicKey(s.view))?.key||s.key||$("natural-logic-key").value.trim();s.view.busy=true;naturalLogicButtons();
 try{const value=await api(naturalLogicPath(s.view)+"/check-controls/"+encodeURIComponent(key));if(!naturalLogicCurrent(s))return;
 if(value.namespace!=="natural-local-logic.v1.control"||value.instance_id!==s.instance.id||value.principal_id!==s.instance.principal_id||value.request_key!==key||!/^run_[a-f0-9]{32}$/.test(value.run_id)||!/^iinstance_[a-f0-9]{32}$/.test(value.check_instance_id)||value.check_instance_id===s.instance.id||!Number.isInteger(value.version))throw Error("VERSION_CONFLICT");
 s.control=value;s.run=value.run_id;s.checkInstance=value.check_instance_id;$("natural-logic-status").textContent=`重验 ${value.run_id} · ${value.status} · 仅本人停止控制元数据，未读取成果正文。`;
 }finally{s.view.busy=false;naturalLogicButtons();}
});
$("natural-logic-cancel").onclick=safe(async()=>{
 const s=naturalLogicView,c=s?.control;if(!s||!c||!naturalLogicCurrent(s)||s.view.busy)return;s.view.busy=true;naturalLogicButtons();
 try{const value=await api(`/api/internal/instances/${c.check_instance_id}/runs/${c.run_id}/commands`,"POST",{command:"cancel",version:c.version});if(!naturalLogicCurrent(s))return;s.control=null;$("natural-logic-status").textContent=`取消请求已接受：${value.status}。请再次读取停止状态；不会提交新的版本。`;
 }finally{s.view.busy=false;naturalLogicButtons();}
});
