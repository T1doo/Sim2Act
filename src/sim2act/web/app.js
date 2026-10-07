"use strict";
let token = "", activeRun = null, refs = [];
let reconcileVersion = null, unresolvedAttempts = [];
let runSelectionGeneration = 0;
let runUserSelectionGeneration = 0;
let runHistoryGeneration = 0;
let identityConnectionGeneration = 0;
let activeApp = null, activeGoalCard = null;
let goalSelectionGeneration = 0, goalCardLoading = false, goalCardSaving = false;
let candidateSelectionGeneration = 0, candidateBusy = false, candidatePanelReady = false;
let appSelectionGeneration = 0, activeAppProject = null;
const candidateRequestKeys = new Map();
const extractionRequestKeys = new Map();
let extractionSource = null, extractionBusy = false;
let appCreateBusy = false;
let appReadRecovery = null, appReadBusy = false;
const appPreviewRequests = new Set();
const $ = (id) => document.getElementById(id);
async function api(path, method = "GET", body) {
  const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"}, ...(body ? {body: JSON.stringify(body)} : {})});
  const data = await response.json();
  if (!response.ok) {const error=new Error(data.error?.code || data.detail?.[0]?.msg || "请求失败");error.detail=data.error?.message;error.httpStatus=response.status;throw error;}
  return data;
}
const safe = (fn) => async (event) => { event?.preventDefault(); $("error").textContent = ""; try {await fn(event);} catch (e) {$("error").textContent = e.message;} };
function row(text, action, label) {
  const div = document.createElement("div"); div.className = "row"; div.textContent = text;
  if (action) {const b = document.createElement("button"); b.textContent = label; b.onclick = safe(action); div.append(" ", b);}
  return div;
}
async function refresh() {
  const pid = $("project-select").value; if (!pid) return;
  const identity=token,generation=++runHistoryGeneration;
  const current=()=>pid===$("project-select").value && identity===token && generation===runHistoryGeneration;
  let materials;
  try {materials = await api(`/api/projects/${pid}/resources`);}
  catch(error){if(current() && typeof invalidateConditionalSource === "function")invalidateConditionalSource("授权列表读取失败");throw error;}
  if (!current()) return;
  if(typeof reconcileConditionalSources === "function")reconcileConditionalSources(materials);
  refs = materials.map(x => x.id);
  const selectedGoals=Array.from($("goal-card-resources").selectedOptions).map(o=>o.value);
  $("goal-card-resources").replaceChildren(...materials.map(m=>{const o=new Option(m.name,m.id);o.selected=selectedGoals.includes(m.id);return o;}));
  await refreshGoalCards(pid);
  if (!current()) return;
  $("materials").replaceChildren(...materials.map(x => row(`${x.name} · ${x.format} · ${x.hash.slice(0, 12)}`, async () => {const data=await api(`/api/resources/${x.id}`);$("resource-preview").hidden=false;$("resource-preview").textContent=data.content;}, "查看")));
  const oldResource = $("app-resource").value;
  $("app-resource").replaceChildren(...materials.filter(x => x.format === "csv").map(x => {const o=document.createElement("option");o.value=x.id;o.textContent=x.name;return o;}));
  if (materials.some(x => x.id === oldResource)) $("app-resource").value = oldResource;
  await refreshApps();
  if(typeof refreshProtocol === "function")await refreshProtocol();
  if (!current()) return;
  $("run-history-status").textContent="正在读取持久任务历史…";
  let runs;
  try {runs=await api(`/api/projects/${pid}/runs`);}
  catch(error){if(!current())return;$("runs").replaceChildren();$("run-history-status").textContent="历史读取失败。请重新刷新；不会提交任务。";throw error;}
  if (!current()) return;
  $("runs").replaceChildren(...runs.map(x => {
    const accepted=Number.isFinite(x.created_at)?new Date(x.created_at*1000).toLocaleString():"时间未知";
    const mode=["MOCK","LIVE"].includes(x.mode)?x.mode:"UNKNOWN";
    return row(`${x.goal_summary || "目标摘要不可用"} · 接受 ${accepted} · 提交模式 ${mode} · ${x.status} · ${x.id.slice(0,16)}`,()=>{if(identity===token && pid===$("project-select").value)return showRun(x.id);},"查看任务");
  }));
  $("run-history-status").textContent=runs.length?`已读取 ${runs.length} 个持久任务。查看任务只读取既有状态。`:"当前项目暂无任务。";
  const grants = await api(`/api/projects/${pid}/grants`);
  if (!current()) return;
  $("grants").replaceChildren(...grants.map(g => row(`${g.tool_ref} · ${g.principal_id.startsWith("runtime_") ? "项目运行身份" : g.principal_id.startsWith("appruntime_") ? "应用预览身份" : "当前使用者"} · ${g.revoked ? "已撤回" : "有效至 " + new Date(g.expires_at * 1000).toLocaleString()}`, g.revoked ? null : async () => {await api(`/api/grants/${g.id}/revoke`, "POST", {command:"revoke",version:g.revision});activeRun=null;clearApp();$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";$("resource-preview").textContent="";await refresh();}, "撤回")));
}
function renderOrdinaryProgress(r, attempts) {
  const section=document.createElement("section");section.id="run-progress";
  const heading=document.createElement("h3");heading.textContent="执行记录（只读）";section.append(heading);
  section.append(row("目标验收：当前普通任务尚未实现（NOT_RUN）。技术状态与工具核验不代表目标已完成。"));
  const reasons={GRANT_REVOKED:"读取授权已撤回，请先核对授权。",RESOURCE_UNAVAILABLE:"所需资源当前不可用，请先核对材料。",RATE_LIMITED:"请求额度或速率受限，任务已停止等待。",OUTCOME_UNKNOWN:"已有请求或效果结果未知，请先核对既有回执，避免重复发送。"};
  if(["WAITING_RESOURCE","RECONCILING"].includes(r.status)) {
    const unknown=attempts.length>0 || r.error?.code==="OUTCOME_UNKNOWN";
    section.append(row(unknown?(attempts.length?"等待核对：已有模型尝试结果未知。请使用下方核对入口；本页面不会自动重发。":"等待核对：已有请求或工具效果结果未知。请先核对既有回执；本页面不会自动重发。"):reasons[r.error?.code] || (r.status==="RECONCILING"?"技术状态待核对，具体原因尚未记录。请先检查已记录回执。":"任务正在等待资源或授权，具体原因尚未记录。")));
  }
  const effects=Array.isArray(r.known_effects)?r.known_effects:[];
  const verified=effects.filter(e=>e && e.status==="VERIFIED").length;
  const invalid=effects.filter(e=>e && e.status==="EFFECT_KNOWN_INVALID").length;
  section.append(row(`已记录工具效果：${verified} 项已核验；${invalid} 项效果已知但核验失败。此计数不代表整体目标验收。`));
  const names={ACCEPTED:"任务已持久接受",CLAIMED:"后台已领取任务",MODEL_RESERVED:"已登记一次模型尝试（不表示已发送或成功）",TOOL_VERIFIED:"工具效果已核验",STATE:"已保存技术状态",WORKER_LOST:"后台执行失联，需核对回执",RECONCILED:"已保存任务核对结果",ATTEMPT_RECONCILED:"已保存尝试核对结果",COMMAND:"已记录人工控制指令",CONTRACT_REJECTED:"冻结任务约束被拒绝"};
  const events=(Array.isArray(r.events)?r.events:[]).filter(e=>e && typeof e.kind==="string" && Object.hasOwn(names,e.kind));
  const list=document.createElement("ol");
  for(const event of events.slice(-20)) {
    const item=document.createElement("li");
    const date=new Date(event.created_at*1000);
    const time=Number.isFinite(event.created_at) && Number.isFinite(date.getTime())?date.toLocaleString():"时间未知";
    const state=event.kind==="STATE" && ["QUEUED","RUNNING","PAUSED","CANCELLED","PARTIAL","FAILED","WAITING_RESOURCE","RECONCILING","SUCCEEDED"].includes(event.data?.status)?`（${event.data.status}）`:"";
    item.textContent=`${time} · ${names[event.kind]}${state}`;list.append(item);
  }
  if(events.length){section.append(row(`最近 ${Math.min(events.length,20)} 条已记录步骤；完整回执保留在详情中。`));section.append(list);}
  else section.append(row("尚无可展示的步骤记录；请查看持久状态或重新读取。"));
  $("result").append(section);
}
function clearRunDetail() {
  unresolvedAttempts=[];reconcileVersion=null;
  for(const name of ["result","events","raw-result","commands","reconcile-attempt"])$(name).replaceChildren();
  $("reconcile-panel").hidden=true;
  $("reconcile-response").value="";$("reconcile-evidence").value="";$("reconcile-ack").checked=false;
}
async function showRun(id, userSelection = true, selectionGuard = () => true, validateReceipt = null) {
  if(!selectionGuard())return;
  if(userSelection)runUserSelectionGeneration++;
  if(userSelection){clearRunDetail();$("result").append(row("正在读取任务…"));}
  activeRun = id;
  if(typeof protocolSelectRun === "function")protocolSelectRun(id,userSelection);
  const project=$("project-select").value,identity=token,generation=++runSelectionGeneration;
  const current=()=>activeRun===id && project===$("project-select").value && identity===token && generation===runSelectionGeneration && selectionGuard();
  let r,attempts;
  try {
    r = await api(`/api/runs/${id}`);
    if(!current())return;
    if(validateReceipt)validateReceipt(r);
    if(typeof renderSelectedProtocol === "function" && r.namespace === "protocol_jobs.v1"){await renderSelectedProtocol(r,id,current);return;}
    if(typeof clearProtocolSelection === "function")clearProtocolSelection();
    attempts = r.namespace !== "INTERNAL_APPRUN" && ["WAITING_RESOURCE","RECONCILING"].includes(r.status) ? await api(`/api/runs/${id}/unresolved-attempts`) : [];
  } catch(error) {
    if(!current())return;
    clearRunDetail();activeRun=null;
    if(typeof clearProtocolSelection === "function")clearProtocolSelection();
    const message=error.httpStatus===403?"当前身份没有读取此任务或核对回执的权限。":"任务详情或核对回执读取失败。";
    const feedback=row(`${message} 无法判断任务当前技术状态；读取失败不表示任务执行失败。已停止此详情的自动回读。`,async()=>{
      if(identity!==token || project!==$("project-select").value || generation!==runSelectionGeneration || activeRun!==null)return;
      await showRun(id);
    },"重新读取任务");
    feedback.id="run-read-failure";$("result").append(feedback);
    if(userSelection)throw error;
    return;
  }
  if(!current())return;
  const internal=r.namespace === "INTERNAL_APPRUN";
  reconcileVersion = r.version;
  unresolvedAttempts=attempts;
  $("reconcile-panel").hidden = unresolvedAttempts.length === 0;
  const selectedAttempt = $("reconcile-attempt").value;
  $("reconcile-attempt").replaceChildren(...unresolvedAttempts.map(a => {const o=document.createElement("option");o.value=a.attempt_id;o.textContent=`${a.mode || "历史请求"} · ${a.attempt_id.slice(0,16)} · ${a.request_fingerprint ? a.request_fingerprint.slice(0,12) : "历史请求未绑定，只能结束"}`;o.title=a.request_fingerprint || "没有可恢复绑定";return o;}));
  if (unresolvedAttempts.some(a => a.attempt_id === selectedAttempt)) $("reconcile-attempt").value = selectedAttempt;
  const labels = {QUEUED:"等待后台执行",RUNNING:"正在执行",PARTIAL:"部分完成",FAILED:"执行失败",WAITING_RESOURCE:"等待资源或授权",PAUSED:"已暂停",CANCELLED:"已取消"};
  $("result").replaceChildren(row(`${labels[r.status] || r.status}（${r.status}）`));
  if(internal){
    $("result").append(row(`内部工程只读任务 · 0 模型请求 · 结果版本 ${r.result_version ?? "无"} · 正式发布关闭`));
    if(r.result)$("result").append(row(`${r.result.column} 合计 ${r.result.sum}，共 ${r.result.count} 条记录。`));
  }
  if(!internal)renderOrdinaryProgress(r,attempts);
  if (r.result && !internal) {
    $("result").append(row(`${r.result.mode === "MOCK" ? "MOCK 工程样例" : "书生运行记录"}：工具回执已核验，完整目标验收尚未执行。`));
    for (const receipt of r.result.receipts || []) {
      const data = receipt.data;
      if (typeof data.content === "string") {const pre=document.createElement("pre");pre.textContent=data.content;$("result").append(pre);}
      else if (data.sum !== undefined) $("result").append(row(`${data.column} 合计 ${data.sum}，共 ${data.count} 条记录。`));
      else if (data.resource_id) $("result").append(row("已保存文本成果，可在资源工作区查看。"));
    }
  }
  if (r.error) $("result").append(row(`需要处理：${r.error.message || r.error.code}`));
  $("raw-result").textContent = JSON.stringify({...r,unresolved_attempts:unresolvedAttempts}, null, 2);
  $("events").textContent = JSON.stringify(r.events, null, 2);
  const commands = ["QUEUED","RUNNING"].includes(r.status) ? ["pause","cancel"] : ["PAUSED","WAITING_RESOURCE"].includes(r.status) ? (unresolvedAttempts.length ? ["cancel"] : ["resume","cancel"]) : [];
  $("commands").replaceChildren(...commands.map(command => {const b = document.createElement("button"); b.textContent = {pause:"暂停",cancel:"取消",resume:"继续"}[command]; b.onclick = safe(async () => {if(!current())return;await api(`/api/runs/${id}/commands`, "POST", {command,version:r.version}); if(current())await showRun(id);}); return b;}));
}
async function loadProjects() {
  const identity=token,connection=identityConnectionGeneration;
  const ps = await api("/api/projects"); if(identity!==token || connection!==identityConnectionGeneration)return; const old = $("project-select").value;
  $("project-select").replaceChildren(...ps.map(p => {const o = document.createElement("option"); o.value=p.id; o.textContent=p.name; return o;}));
  if (ps.some(p => p.id === old)) $("project-select").value = old;
  renderRunSubmission();
  await refresh();
}
function clearIdentityView() {
  if(typeof clearReportManifest === "function")clearReportManifest();
  if(typeof clearReportApps === "function")clearReportApps();
  if(typeof clearReportSave === "function")clearReportSave();
  if(typeof clearApplicationUse === "function")clearApplicationUse(true);
  runHistoryGeneration++;runSelectionGeneration++;runUserSelectionGeneration++;
  activeRun=null;refs=[];unresolvedAttempts=[];reconcileVersion=null;
  clearRunDetail();
  if(typeof clearProtocol === "function")clearProtocol();
  clearGoalCard();
  for(const id of ["runs","materials","grants","app-list","goal-card-list","result","commands","events","raw-result","resource-preview","run-history-status","run-submit-status","project-select","app-resource","goal-card-resources","capabilities"]){$(id).replaceChildren();}
  $("reconcile-panel").hidden=true;$("resource-preview").hidden=true;
  $("goal").value="";
  renderRunSubmission();
}
$("connect").onclick = safe(async () => {
  token=$("token").value;const connection=++identityConnectionGeneration;
  clearIdentityView();const identity=token;
  const current=()=>identity===token && connection===identityConnectionGeneration;
  try {
    await loadProjects();if(!current())return;
    $("token").value="";$("login").hidden=true;
    const capabilities=await api("/api/capabilities");if(current())$("capabilities").textContent=JSON.stringify(capabilities,null,2);
  } catch(error) {if(current())throw error;}
});
$("project-form").onsubmit = safe(async () => {await api("/api/projects","POST",{name:$("project-name").value}); await loadProjects();});
$("resource-form").onsubmit = safe(async () => {const pid=$("project-select").value;if(!pid)throw new Error("先选择项目");await api(`/api/projects/${pid}/resources`,"POST",{name:$("resource-name").value,format:$("format").value,content:$("content").value}); await refresh();});
$("run-form").onsubmit = safe(async () => submitOrdinaryRun());
$("run-history-refresh").onclick=safe(async()=>refresh());
$("reconcile-form").onsubmit = safe(async () => {const a=unresolvedAttempts.find(x=>x.attempt_id === $("reconcile-attempt").value);if(!a || !activeRun)throw new Error("请重新打开待核对任务");const decision=$("reconcile-decision").value;await api(`/api/runs/${activeRun}/reconcile`,"POST",{attempt_id:a.attempt_id,version:reconcileVersion,decision,expected_fingerprint:a.request_fingerprint,evidence:$("reconcile-evidence").value,acknowledge_unknown_cost:$("reconcile-ack").checked,response_json:decision === "record_response" ? $("reconcile-response").value : null});$("reconcile-response").value="";$("reconcile-evidence").value="";$("reconcile-ack").checked=false;await showRun(activeRun);});
$("project-select").onchange = safe(async () => {if(typeof clearApplicationUse === "function")clearApplicationUse(true);runUserSelectionGeneration++;runHistoryGeneration++;$("runs").replaceChildren();$("run-history-status").textContent="";activeRun=null;renderRunSubmission();if(typeof clearProtocol === "function")clearProtocol();clearApp();clearGoalCard();clearRunDetail();$("resource-preview").textContent="";await refresh();});
document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => ["projects","apps","resources"].forEach(id => $(id).hidden=id!==b.dataset.tab));
document.querySelector("#projects .grid > section:last-child").append($("reconcile-panel"));
let backgroundRefreshInFlight=false;
setInterval(async () => {
  if(backgroundRefreshInFlight)return;
  backgroundRefreshInFlight=true;
  try {
    const h=await api("/health");$("health").textContent=`${h.mode} · API ${h.api} · worker ${h.worker}`;
    if(token){await refresh();if(activeRun)await showRun(activeRun,false);}
  } catch(e) {$("health").textContent="后台不可用";}
  finally {backgroundRefreshInFlight=false;}
},2500);

function clearApp() {
  if(typeof clearDeliveryGraph === "function")clearDeliveryGraph();
  if(typeof clearReportManifest === "function")clearReportManifest();
  if(typeof clearReportApps === "function")clearReportApps();
  if(typeof clearApplicationUse === "function")clearApplicationUse();
  if(typeof clearInternal === "function")clearInternal();
  appReadRecovery=null;$("app-read-retry").hidden=true;
  $("app-create-status").textContent="";$("app-create-status").dataset.state="";
  extractionSource=null;$("extraction-form").hidden=true;$("extraction-status").textContent="";
  appSelectionGeneration++;activeAppProject=null;
  $("app-origin").textContent="";$("app-back-goal").hidden=true;$("app-frozen-goal").hidden=true;$("app-frozen-goal-text").textContent="";
  activeApp=null;$("app-title").textContent="选择草案";$("app-preview-form").hidden=true;
  $("app-output").replaceChildren();$("app-output").dataset.state="";$("app-history").replaceChildren();$("app-manifest").textContent="";
}
async function refreshApps() {
  const pid=$("project-select").value,identity=token,generation=appSelectionGeneration;
  const list=await api("/api/apps");
  if(pid!==$("project-select").value || identity!==token || generation!==appSelectionGeneration)return;
  const items=list.items.filter(x=>x.project_id === $("project-select").value);
  $("app-list").replaceChildren(...items.map(x=>row(`${x.name} · 未发布草案`,()=>showApp(x.id),"打开预览")));
  if(!items.length)$("app-list").textContent="先保存 CSV 材料，再创建一个草案。";
  if(typeof refreshApplicationUse === "function")await refreshApplicationUse(items);
  if(typeof refreshReportApps === "function")await refreshReportApps();
}
function previewText(r) {
  if(r.status === "FAILED")return `预览失败（FAILED）：${r.error?.message || r.error?.code} · 已保留这次历史`;
  return `预览成功（SUCCEEDED） · ${r.output.column} 合计 ${r.output.sum}，共 ${r.output.count} 条 · 0 模型请求 · 仅预览`;
}
function showPreviewResult(r,history=false){
  $("app-output").dataset.state=r.status === "FAILED" ? "error" : "success";
  $("app-output").replaceChildren(row(`${history ? "历史记录 · " : ""}${previewText(r)} · ${r.id.slice(0,16)}`));
}
async function showApp(id,pid=$("project-select").value,onSelectionStart=null) {
  if(pid !== $("project-select").value)return false;
  clearApp();const generation=appSelectionGeneration;
  onSelectionStart?.(generation);
  const identity=token;
  const a=await api(`/api/apps/${id}`);
  if(generation !== appSelectionGeneration || pid !== $("project-select").value || identity !== token)return false;
  if(a.project_id !== pid)throw Error("候选不属于当前项目，请重新选择");
  activeApp=id;activeAppProject=pid;
  if(typeof openDeliveryGraph === "function")openDeliveryGraph(a,generation);
  if(a.input_guidance.mode === "BOUNDED_REPORT")return openReportManifest(a,generation);
  const origin=a.candidate.generation;
  const extraction=a.candidate.extraction;
  const taskProof=a.candidate.task_proof;
  if(taskProof?.proof?.kind === "completed_registered_csv_apprun.v1"){
    $("app-origin").textContent=`来源：已成功内部 CSV AppRun ${taskProof.proof.source_run_id || a.candidate.manifest.source_run_ref} · 可信求和/独立精确数值核查 · 新 CSV 绑定 + column 运行参数 · 0 模型请求 · 目标语义条件 NOT_RUN · 未发布`;
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify(taskProof,null,2);
  } else if(taskProof){
    $("app-origin").textContent=`来源：已完成本地声明式合成任务 ${taskProof.proof.task_id} · LOCAL_DECLARATIVE_TASK · 精确求和核查通过 · 最小来源证明 v${taskProof.proof.version} · 新CSV/column参数 · 来源撤权或过期仍拒绝 · 未发布`;
    $("app-frozen-goal").hidden=false;
    $("app-frozen-goal-text").textContent=JSON.stringify(taskProof,null,2);
  }
  if(extraction){
    $("app-origin").textContent=`来源：已成功本地合成PREVIEW回执 ${extraction.preview_id} · 独立数值核查通过 · 新CSV绑定 · 仅column运行参数 · 目标条件NOT_RUN · 未发布`;
    $("app-frozen-goal").hidden=false;
    $("app-frozen-goal-text").textContent=JSON.stringify({goal:a.candidate.goal,source:extraction},null,2);
  }
  if(origin){
    $("app-origin").textContent=`来源：${a.candidate.goal.title} · 目标 v${origin.goal_version} · MOCK固定CSV能力 · 0模型请求 · 结构/依赖校验通过 · 目标条件尚未验收 · 未发布`;
    const labels={title:"名称",goal:"目标",known:"已知",assumptions:"假设",unresolved:"未决项",constraints:"硬条件",acceptance_checks:"验收检查"};
    $("app-frozen-goal").hidden=false;
    $("app-frozen-goal-text").textContent=`冻结来源 v${origin.goal_version}，目标修订不改变此快照。\n\n`+goalCardFields.map(f=>`${labels[f]}：\n${Array.isArray(a.candidate.goal[f]) ? a.candidate.goal[f].join("\n") : a.candidate.goal[f]}`).join("\n\n");
    $("app-back-goal").hidden=false;
    $("app-back-goal").onclick=safe(async()=>{
      if(pid !== $("project-select").value)return;
      clearApp();selectWorkspace("projects");await showGoalCard(origin.goal_card_id,pid);
    });
  }
  $("app-title").textContent=`${a.name} · 未发布`;
  const agent=a.input_guidance.mode === "OFFLINE_REPLAY_ONLY";
  $("app-preview-form").hidden=false;
  $("app-column-label").hidden=agent;$("app-column").required=!agent;
  $("app-agent-term-label").hidden=!agent;$("app-agent-term").value="";
  $("app-preview-submit").hidden=agent;$("csv-extraction-panel").hidden=agent;
  $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,fingerprint:a.fingerprint,runtime_id:a.runtime_id},null,2);
  if(agent){
    const manifest=a.candidate.manifest;
    $("app-origin").textContent=`${a.candidate.agent_provenance ? "来源：已验证的本地合成 AppRun "+manifest.source_run_ref : "来源：离线调用者提供的初始候选"} · OFFLINE_REPLAY_ONLY · semantic UNKNOWN · 未发布`;
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify({goal:a.candidate.goal,resource:manifest.data_bindings[0].resource_ref,revision:a.candidate.source_revision,hash:a.candidate.source_hash,permissions:manifest.permission_requirements,source:a.candidate.agent_provenance || null},null,2);
    $("app-input-hint").textContent="TXT/MD 字面检索，词长最多80字符；审批样例与运行都需对应的离线响应，界面不会生成答案。";
    $("app-history").textContent="新运行与结果版本见下方内部实例历史；不将旧结果作为当前结果。";
    if(typeof openInternal === "function")await openInternal(a,generation);
    return true;
  }
  const previous=$("app-column").value, guidance=a.input_guidance;
  $("app-column").replaceChildren(...guidance.columns.map(c=>{
    const option=new Option(c.numeric ? c.name : `${c.name}（${c.reason}）`,c.name);
    option.disabled=!c.numeric;return option;
  }));
  const selectable=guidance.columns.filter(c=>c.numeric);
  $("app-column").value=selectable.some(c=>c.name===previous) ? previous : (selectable[0]?.name || "");
  $("app-preview-submit").disabled=!selectable.length || appPreviewRequests.has(id);
  $("app-input-hint").textContent=guidance.error || (selectable.length ? `已核对 ${guidance.row_count} 条记录；请选择数值列。` : "没有可汇总的数值列，请保存修正后的材料并重建草案。");
  $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,fingerprint:a.fingerprint,runtime_id:a.runtime_id},null,2);
  $("app-history").replaceChildren(...a.history.map(r=>row(`${new Date(r.created_at*1000).toLocaleString()} · ${r.input.column || "无效输入"} · ${r.status} · ${r.id.slice(0,16)}`,()=>showPreviewResult(r,true),"回读历史")));
  if(!a.history.length)$("app-history").textContent="尚无预览。请选择 CSV 中的数值列。";
  const succeeded=a.history.filter(r=>r.status === "SUCCEEDED");
  if(!extraction && !taskProof && succeeded.length){
    extractionSource={id,project_id:pid,fingerprint:a.fingerprint,generation};
    $("extraction-preview").replaceChildren(...succeeded.map(r=>new Option(`${r.input.column} · ${r.output.sum} · ${r.id}`,r.id)));
    const sourceRid=a.candidate.manifest.data_bindings[0].resource_ref;
    $("extraction-resource").replaceChildren(...Array.from($("app-resource").options).filter(o=>o.value !== sourceRid).map(o=>new Option(o.textContent,o.value)));
    $("extraction-form").hidden=false;$("extraction-create").disabled=extractionBusy || !$("extraction-resource").value;
    $("extraction-status").textContent=$("extraction-resource").value ? "只接受成功回执；提取时重新核查来源与独立数值结果。" : "请先在同项目保存内容不同的新CSV，再打开来源草案。";
  }
  if(typeof openInternal === "function")await openInternal(a,generation);
  return true;
}
$("extraction-form").onsubmit=safe(async()=>{
  const source=extractionSource,pid=$("project-select").value;
  if(extractionBusy || !source || source.id !== activeApp || source.project_id !== pid)return;
  const previewId=$("extraction-preview").value,rid=$("extraction-resource").value;
  const name=$("extraction-name").value;
  const binding=JSON.stringify([previewId,source.fingerprint,rid,name]);
  if(!extractionRequestKeys.has(binding))extractionRequestKeys.set(binding,crypto.randomUUID());
  const current=()=>extractionSource === source && activeApp === source.id && pid === $("project-select").value && source.generation === appSelectionGeneration;
  extractionBusy=true;$("extraction-create").disabled=true;
  try{
    const candidate=await api(`/api/previews/${previewId}/extract`,"POST",{expected_source_fingerprint:source.fingerprint,resource_id:rid,name,request_key:extractionRequestKeys.get(binding)});
    if(!current())return;
    await refreshApps();if(!current())return;
    await showApp(candidate.id,pid);
  }catch(e){if(current()){$("extraction-status").textContent=`提取失败：${e.message}；选择已保留，可核对后重试。`;}}
  finally{extractionBusy=false;if(extractionSource && extractionSource.id === activeApp && extractionSource.project_id === $("project-select").value)$("extraction-create").disabled=!$("extraction-resource").value;}
});
$("app-form").onsubmit=safe(async()=>{
  if(appCreateBusy || appReadBusy)return;
  if(appReadRecovery?.kind === "created"){await retryAppRead();return;}
  const pid=$("project-select").value,rid=$("app-resource").value;
  if(!pid || !rid)throw new Error("先为当前项目保存并授权 CSV 材料");
  let generation=appSelectionGeneration,created=null;
  const goalGeneration=goalSelectionGeneration;
  const current=()=>generation === appSelectionGeneration && goalGeneration === goalSelectionGeneration && pid === $("project-select").value;
  appCreateBusy=true;$("app-create-submit").disabled=true;
  $("app-create-status").dataset.state="loading";$("app-create-status").textContent="正在保存草案；离开选择不会撤销已接受的创建。";
  try{
    created=await api(`/api/projects/${pid}/apps/csv-preview`,"POST",{name:$("app-name").value,goal:$("app-goal").value,resource_id:rid});
    if(!current())return;
    await refreshApps();if(!current())return;
    if(await showApp(created.id,pid,g=>{generation=g;}) && current() && activeApp === created.id){$("app-create-status").dataset.state="success";$("app-create-status").textContent="草案已保存，请选择数值列运行新预览。";}
  }catch(e){if(current()){
    if(created)setAppReadFailure({id:created.id,pid,kind:"created",goalGeneration},e);
    else{$("app-create-status").dataset.state="error";$("app-create-status").textContent=`创建未打开：${e.message}；可刷新草案列表核对后重试。`;}
  }}
  finally{appCreateBusy=false;$("app-create-submit").disabled=false;}
});
function setAppReadFailure(recovery,error){
  appReadRecovery=recovery;$("app-read-retry").hidden=false;
  const status=$(recovery.kind === "created" ? "app-create-status" : "app-output");
  status.dataset.state="error";
  status.textContent=`${recovery.kind === "created" ? "草案已创建" : "预览已执行"}；后续读取失败：${error.message}。重新读取只回读已保存记录，不会再次创建或执行。`;
}
async function retryAppRead(){
  const recovery=appReadRecovery;
  if(!recovery || appReadBusy || appCreateBusy || recovery.pid !== $("project-select").value || recovery.goalGeneration !== goalSelectionGeneration)return;
  let generation=appSelectionGeneration;
  const current=()=>generation === appSelectionGeneration && recovery.pid === $("project-select").value && recovery.goalGeneration === goalSelectionGeneration;
  appReadBusy=true;$("app-read-retry").disabled=true;$("app-create-submit").disabled=true;
  try{
    if(await showApp(recovery.id,recovery.pid,g=>{generation=g;}) && current()){
      if(recovery.kind === "created"){$("app-create-status").dataset.state="success";$("app-create-status").textContent="已创建草案重新读取成功；没有重复创建。";}
      else showPreviewResult(recovery.result);
    }
  }catch(e){if(current())setAppReadFailure(recovery,e);}
  finally{appReadBusy=false;$("app-read-retry").disabled=false;$("app-create-submit").disabled=appCreateBusy;}
}
$("app-read-retry").onclick=safe(retryAppRead);
$("app-preview-form").onsubmit=safe(async()=>{
  if($("app-preview-submit").hidden)return; // Agent uses the same internal approval/Run path.
  if(!activeApp || activeAppProject !== $("project-select").value)throw new Error("先打开当前项目的草案");
  const id=activeApp,pid=activeAppProject,goalGeneration=goalSelectionGeneration;
  let generation=appSelectionGeneration,result=null;
  if(appPreviewRequests.has(id))return;
  const current=()=>generation === appSelectionGeneration && pid === $("project-select").value && goalGeneration === goalSelectionGeneration;
  appPreviewRequests.add(id);$("app-preview-submit").disabled=true;
  $("app-output").dataset.state="loading";$("app-output").textContent="正在读取授权材料并运行新预览…";
  try {
    result=await api(`/api/apps/${id}/previews`,"POST",{input:{column:$("app-column").value},request_key:crypto.randomUUID()});
    if(current() && await showApp(id,pid,g=>{generation=g;})){if(current() && activeApp===id)showPreviewResult(result);}
  }catch(e){if(current()){
    if(result)setAppReadFailure({id,pid,kind:"preview",result,goalGeneration},e);
    else{$("app-output").dataset.state="error";$("app-output").textContent=`预览未打开：${e.message}；可重新打开草案核对历史。`;}
  }}
  finally{appPreviewRequests.delete(id);$("app-preview-submit").disabled=appPreviewRequests.has(activeApp) || !$("app-column").value;}
});


// Page memory only; accepted/uncertain goal execution never changes its original input.
const goalRunRequests=new Map();
const goalRunCanonical=value=>JSON.stringify(value,(key,item)=>item&&typeof item==="object"&&!Array.isArray(item)?Object.fromEntries(Object.keys(item).sort().map(k=>[k,item[k]])):item);
let goalRunDisplayed=null;
const goalRunKey=(card=activeGoalCard)=>card?JSON.stringify([token,$("project-select").value,card.id]):null;
function renderGoalRun(){
 const card=activeGoalCard,entry=goalRunRequests.get(goalRunKey());
 $("goal-card-run").disabled=!card||goalCardLoading||goalCardSaving||["sending","unknown","accepted-read-error"].includes(entry?.state);
 $("goal-card-run").textContent=card?`按已保存 v${card.version} 执行任务`:"按已保存版本执行任务";
 $("goal-card-run-recover").hidden=!["unknown","accepted-read-error"].includes(entry?.state);
 $("goal-card-run-recover").disabled=entry?.state==="sending";
 $("goal-card-run-recover").textContent=entry?.state==="accepted-read-error"?"重新读取已接受任务（不提交）":"恢复原版本执行的同一回执";
 $("goal-card-run-status").textContent=entry?.message||"执行已保存目标，不包含未保存编辑。目标验收 NOT_RUN；不会自动生成应用候选。";
}
async function readGoalRun(entry,current,selection){
 try{
  if(!current()||selection!==runUserSelectionGeneration)return;
  goalRunDisplayed=entry.runId;
  await showRun(entry.runId,true,()=>current()&&goalRunDisplayed===entry.runId,r=>{
   const source=r.contract?.snapshot?.source_goal_card;
   if(r.id!==entry.runId||!source||source.card_id!==activeGoalCard.id||source.version!==entry.body.expected_version||source.fingerprint!==entry.body.expected_fingerprint||source.snapshot?.schema_version!=="F2-goal-card.v1"||goalRunCanonical(source.snapshot)!==goalRunCanonical(entry.snapshot))throw Error("VERSION_CONFLICT");
  });
  if(!current())return;
  entry.state="accepted";entry.message=`已接受保存 v${entry.body.expected_version} 的任务；目标验收 NOT_RUN，未生成候选。请查看实际技术状态与回执。`;
 }catch(error){entry.state="accepted-read-error";entry.message="任务已接受；详情读取失败不能判断执行结果。只重新读取原 Run，不再提交。";}
 finally{if(current())renderGoalRun();}
}
async function executeGoalCard(recover=false){
 const card=activeGoalCard;if(!card||goalCardLoading||goalCardSaving)return;
 const key=goalRunKey(card),generation=goalSelectionGeneration,identity=token,project=card.project_id,selection=runUserSelectionGeneration;
 const current=()=>identity===token&&project===$("project-select").value&&generation===goalSelectionGeneration&&activeGoalCard?.id===card.id;
 let entry=goalRunRequests.get(key);
 if(entry?.state==="sending")return;
 if(!recover){
  if(["unknown","accepted-read-error"].includes(entry?.state))return;
  entry={snapshot:card.snapshot,body:{expected_version:card.version,expected_fingerprint:card.fingerprint,request_key:crypto.randomUUID()},state:"new",uncertain:false,runId:null};goalRunRequests.set(key,entry);
 }
 if(!entry)return;
 if(entry.state==="accepted-read-error"){await readGoalRun(entry,current,selection);return;}
 entry.state="sending";entry.message=`正在确认已保存 v${entry.body.expected_version} 的执行回执。`;renderGoalRun();
 try{
  const receipt=await api(`/api/projects/${project}/goal-cards/${card.id}/runs`,"POST",entry.body);
  if(!receipt||typeof receipt.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(receipt.run_id)||receipt.status!=="ACCEPTED"||receipt.goal_card_id!==card.id||receipt.goal_version!==entry.body.expected_version||receipt.goal_fingerprint!==entry.body.expected_fingerprint||receipt.goal_acceptance!=="NOT_RUN"||receipt.candidate_generated!==false)throw Error("Invalid goal execution receipt");
  entry.runId=receipt.run_id;entry.state="accepted-read-error";
 }catch(error){
  const rejected=!entry.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
  entry.state=rejected?"rejected":"unknown";if(!rejected)entry.uncertain=true;
  entry.message=rejected?`执行被拒绝：${error.message}`:"接受回执 UNKNOWN；请显式恢复原版本、原指纹与原请求键，不能另建重复任务。";
  if(current())renderGoalRun();return;
 }
 if(current()&&selection===runUserSelectionGeneration)await readGoalRun(entry,current,selection);
 if(current())renderGoalRun();
}
$("goal-card-run").onclick=safe(()=>executeGoalCard());
$("goal-card-run-recover").onclick=safe(()=>executeGoalCard(true));
const goalCardFields=["title","goal","known","assumptions","unresolved","constraints","acceptance_checks"];
function updateGoalCardSave() {
  $("goal-card-save").disabled=goalCardLoading || goalCardSaving;
  updateCandidateCreate();
  renderGoalRun();
}
function clearGoalCard() {
  if(goalRunDisplayed && activeRun===goalRunDisplayed){activeRun=null;runSelectionGeneration++;clearRunDetail();}
  goalRunDisplayed=null;
  clearApp(); // A goal selection also invalidates in-flight app readback/recovery.
  goalSelectionGeneration++;candidateSelectionGeneration++;candidatePanelReady=false;
  $("goal-candidate-form").hidden=true;$("goal-candidate-list").replaceChildren();
  $("goal-candidate-status").textContent="先打开已保存目标卡。";
  goalCardLoading=false;updateGoalCardSave();
  activeGoalCard=null;renderGoalRun();$("goal-card-form").reset();$("goal-card-status").textContent="新建草案";
  $("goal-card-history").replaceChildren();$("goal-card-history-detail").textContent="";
}
async function refreshGoalCards(pid) {
  const identity=token,generation=goalSelectionGeneration;
  const cards=await api(`/api/projects/${pid}/goal-cards`);
  if(pid !== $("project-select").value || identity!==token || generation!==goalSelectionGeneration)return;
  $("goal-card-list").replaceChildren(...cards.items.map(c=>row(`${c.title} · 草案 v${c.version}`,()=>showGoalCard(c.id,pid),"打开目标卡")));
  if(!cards.items.length)$("goal-card-list").textContent="尚无目标卡。可先整理任意目标及其检查要求。";
}
async function showGoalCard(id, pid=$("project-select").value) {
  if(pid !== $("project-select").value)return;
  clearGoalCard();
  const generation=goalSelectionGeneration,identity=token;
  goalCardLoading=true;updateGoalCardSave();$("goal-card-status").textContent="正在读取目标卡";
  const current=()=>identity===token && generation === goalSelectionGeneration && pid === $("project-select").value;
  let card;
  try {
    card=await api(`/api/goal-cards/${id}`);
    if(!current())return;
    if(card.project_id !== pid)throw Error("目标卡不属于当前项目，请重新选择");
  } catch(e) {
    if(!current())return;
    $("goal-card-status").textContent="读取失败，请重新选择或新建";
    throw e;
  } finally {
    if(current()){goalCardLoading=false;updateGoalCardSave();}
  }
  if(!Number.isInteger(card.version)||card.version<1||typeof card.fingerprint!=="string"||! /^[a-f0-9]{64}$/.test(card.fingerprint))throw Error("VERSION_CONFLICT");
  activeGoalCard={id,version:card.version,fingerprint:card.fingerprint,project_id:card.project_id,snapshot:card.history.find(v=>v.version===card.version&&v.fingerprint===card.fingerprint)?.snapshot};
  if(!activeGoalCard.snapshot){activeGoalCard=null;renderGoalRun();throw Error("VERSION_CONFLICT");}
  renderGoalRun();
  goalCardFields.forEach(f=>{$(`goal-card-${f}`).value=Array.isArray(card.content[f]) ? card.content[f].join("\n") : card.content[f];});
  Array.from($("goal-card-resources").options).forEach(o=>o.selected=card.content.resource_refs.includes(o.value));
  $("goal-card-status").textContent=`草案 v${card.version} · 目标验收 NOT_RUN · 执行使用已保存版本；保存将建立新版本`;
  $("goal-card-history-detail").textContent="";
  $("goal-card-history").replaceChildren(...card.history.map(v=>row(`v${v.version} · ${v.snapshot.content.title}`,()=>{const labels={title:"名称",goal:"目标",known:"已知",assumptions:"假设",unresolved:"未决项",constraints:"硬条件",acceptance_checks:"验收检查"};$("goal-card-history-detail").textContent=goalCardFields.map(f=>`${labels[f]}：\n${Array.isArray(v.snapshot.content[f]) ? v.snapshot.content[f].join("\n") : v.snapshot.content[f]}`).join("\n\n")+`\n\n绑定材料 ${v.snapshot.resource_snapshots.length} 份 · 只读历史版本 v${v.version}`;},"回看版本")));
  await refreshGoalCandidates(id,pid,generation);
}
$("goal-card-new").onclick=clearGoalCard;
$("goal-card-form").onsubmit=safe(async()=>{
  const pid=$("project-select").value;if(!pid)throw Error("先选择项目");
  if(goalCardLoading || goalCardSaving)return;
  const selectedCard=activeGoalCard, generation=goalSelectionGeneration;
  if(selectedCard && selectedCard.project_id !== pid)throw Error("目标卡不属于当前项目，请重新选择");
  const body={resource_refs:Array.from($("goal-card-resources").selectedOptions).map(o=>o.value)};
  goalCardFields.forEach(f=>{body[f]=["title","goal"].includes(f) ? $(`goal-card-${f}`).value : $(`goal-card-${f}`).value.split("\n").map(s=>s.trim()).filter(Boolean);});
  goalCardSaving=true;updateGoalCardSave();
  try {
    const result=selectedCard ? await api(`/api/goal-cards/${selectedCard.id}`,"PUT",{...body,expected_version:selectedCard.version}) : await api(`/api/projects/${pid}/goal-cards`,"POST",body);
    if(generation !== goalSelectionGeneration || pid !== $("project-select").value)return;
    await refreshGoalCards(pid);
    if(generation !== goalSelectionGeneration || pid !== $("project-select").value)return;
    await showGoalCard(result.id,pid);
  } finally {goalCardSaving=false;updateGoalCardSave();}
});


function selectWorkspace(id) {
  ["projects","apps","resources"].forEach(tab=>$(tab).hidden=tab !== id);
}
function updateCandidateCreate() {
  $("goal-candidate-create").disabled=candidateBusy || !candidatePanelReady || goalCardLoading || goalCardSaving;
}
async function refreshGoalCandidates(id,pid,generation) {
  const selection=candidateSelectionGeneration;
  const current=()=>generation === goalSelectionGeneration && selection === candidateSelectionGeneration && activeGoalCard?.id === id && pid === $("project-select").value;
  try {
    const options=await api(`/api/goal-cards/${id}/candidate-options`);
    if(!current())return;
    $("goal-candidate-list").replaceChildren(...options.items.map(item=>row(`${item.name} · 来源 v${item.goal_version} · MOCK未发布候选`,async()=>{
      if(pid === $("project-select").value && await showApp(item.id,pid))selectWorkspace("apps");
    },"打开候选预览")));
    if(options.goal_version !== activeGoalCard.version){$("goal-candidate-status").textContent="目标卡已更新，请重新打开后创建候选。";return;}
    $("goal-candidate-resource").replaceChildren(...options.materials.map(m=>new Option(m.name,m.id)));
    $("goal-candidate-capability").replaceChildren(...options.capabilities.map(c=>new Option(`${c.name}（MOCK固定能力）`,c.id)));
    candidatePanelReady=!!options.materials.length && !!options.capabilities.length;
    $("goal-candidate-form").hidden=!candidatePanelReady;
    $("goal-candidate-status").textContent=candidatePanelReady ? `将使用已保存目标 v${activeGoalCard.version}；未保存编辑不纳入候选。` : "本切片仅支持数值列求和，请在目标卡绑定并保存CSV材料。";
  } catch(e) {
    if(current())$("goal-candidate-status").textContent=`候选选项不可用：${e.message}。保留目标编辑，可处理授权后重新打开。`;
  } finally {updateCandidateCreate();}
}
$("goal-candidate-cancel").onclick=()=>{
  candidateSelectionGeneration++;candidatePanelReady=false;$("goal-candidate-form").hidden=true;
  $("goal-candidate-status").textContent=candidateBusy ? "已返回编辑。请求若已接受，候选仍保留在应用草案；不会自动打开。" : "已取消选择，未创建候选；可重新打开目标卡再选择。";
  updateCandidateCreate();
};
$("goal-candidate-form").onsubmit=safe(async()=>{
  if(candidateBusy || !candidatePanelReady || goalCardLoading || goalCardSaving)return;
  const card=activeGoalCard,pid=$("project-select").value;
  if(!card || card.project_id !== pid)throw Error("先打开当前项目的已保存目标卡");
  const rid=$("goal-candidate-resource").value,capability=$("goal-candidate-capability").value;
  if(!rid || capability !== "csv.sum")throw Error("请选择已绑定CSV和可信求和能力");
  const binding=JSON.stringify([card.id,card.version,rid,capability]);
  if(!candidateRequestKeys.has(binding))candidateRequestKeys.set(binding,crypto.randomUUID());
  if(candidateRequestKeys.size>50)candidateRequestKeys.delete(candidateRequestKeys.keys().next().value);
  const generation=goalSelectionGeneration,selection=candidateSelectionGeneration;
  const current=()=>generation === goalSelectionGeneration && selection === candidateSelectionGeneration && activeGoalCard?.id === card.id && pid === $("project-select").value;
  candidateBusy=true;updateCandidateCreate();$("goal-candidate-status").textContent="正在保存MOCK候选；不会调用真实模型。";
  try {
    const candidate=await api(`/api/goal-cards/${card.id}/candidates`,"POST",{expected_version:card.version,resource_id:rid,capability,request_key:candidateRequestKeys.get(binding)});
    if(!current())return;
    await refreshGoalCandidates(card.id,pid,generation);
    if(!current())return;
    await refreshApps();
    if(!current())return;
    if(await showApp(candidate.id,pid)){
      if(!current()){clearApp();return;}
      selectWorkspace("apps");$("app-output").replaceChildren(row("MOCK候选已保存。选择数值列运行预览；目标条件尚未验收，未发布。"));
    }
  } catch(e) {
    if(current())$("goal-candidate-status").textContent=`候选未打开：${e.message}。已保留编辑；可重试同一请求，或重新打开目标卡核对版本/候选列表。`;
  } finally {candidateBusy=false;updateCandidateCreate();}
});

// Page-memory only. Authentication and exact input stay out of browser storage.
const ordinarySubmissions = new Map();
function runSubmissionEntry() {
  return ordinarySubmissions.get(token)?.get($("project-select").value);
}
function renderRunSubmission() {
  const entry=runSubmissionEntry();
  const blocked=entry && ["sending","unknown"].includes(entry.state);
  $("run-submit").disabled=Boolean(blocked);
  $("goal").readOnly=Boolean(blocked);
  if(blocked)$("goal").value=entry.body.goal;
  $("run-submit-recover").hidden=entry?.state!=="unknown";
  $("run-submit-read").hidden=entry?.state!=="accepted-read-error";
  $("run-submit-status").textContent=entry?.message || "";
  $("run-submit-status").dataset.state=entry?.state==="sending"?"loading":entry?.state==="unknown" || entry?.state==="rejected"?"error":"";
}
async function readAcceptedOrdinaryRun(entry, selection) {
  const current=()=>entry.identity===token && entry.project===$("project-select").value;
  try {
    await refresh();
    if(current() && selection===runUserSelectionGeneration)await showRun(entry.runId);
    entry.state="accepted";
    entry.message=`任务已接受（${entry.runId.slice(0,16)}），可在任务历史查看。后台执行不等于目标已验收。`;
  } catch (_) {
    entry.state="accepted-read-error";
    entry.message=`任务已接受（${entry.runId.slice(0,16)}），读取暂时失败。重新读取不会提交新任务。`;
  }
  if(current())renderRunSubmission();
}
async function sendOrdinarySubmission(entry) {
  if(entry.state==="sending")return;
  const selection=runUserSelectionGeneration;
  const current=()=>entry.identity===token && entry.project===$("project-select").value;
  entry.state="sending";
  entry.message=`正在确认提交。已冻结目标与 ${entry.body.resource_refs.length} 份材料；请勿另建重复任务。`;
  if(current())renderRunSubmission();
  let receipt;
  try {
    receipt=await api(`/api/projects/${entry.project}/runs`,"POST",entry.body);
    if(typeof receipt.run_id!=="string" || !/^run_[a-f0-9]{32}$/.test(receipt.run_id))throw Error("Invalid receipt");
  } catch (error) {
    // Only a definite client rejection permits a changed new intent. Proxy/server
    // failures and malformed replies can hide a durable accepted Run.
    const rejected=!entry.wasUncertain && Number.isInteger(error.httpStatus) && error.httpStatus>=400 && error.httpStatus<500 && ![408,425,429].includes(error.httpStatus);
    entry.state=rejected?"rejected":"unknown";
    if(!rejected)entry.wasUncertain=true;
    entry.message=rejected?`提交被拒绝（${error.message}）。修正输入或授权后再提交。`:"尚未确认任务是否已接受。输入已冻结；手动恢复将使用原提交键与原输入，不会重复创建任务。";
    if(current())renderRunSubmission();
    return;
  }
  entry.runId=receipt.run_id;
  entry.state="accepted";
  entry.message=`任务已接受（${entry.runId.slice(0,16)}），可在任务历史查看。后台执行不等于目标已验收。`;
  if(current()) {
    renderRunSubmission();
    await readAcceptedOrdinaryRun(entry,selection);
  }
}
async function submitOrdinaryRun() {
  const project=$("project-select").value;
  if(!project)throw Error("先选择项目");
  const old=runSubmissionEntry();
  if(old && ["sending","unknown"].includes(old.state)){renderRunSubmission();return;}
  const body=Object.freeze({goal:$("goal").value,resource_refs:Object.freeze([...refs]),request_key:crypto.randomUUID()});
  runUserSelectionGeneration++;
  const entry={project,identity:token,body,state:"new",message:"",runId:null};
  if(!ordinarySubmissions.has(token))ordinarySubmissions.set(token,new Map());
  ordinarySubmissions.get(token).set(project,entry);
  await sendOrdinarySubmission(entry);
}
$("run-submit-recover").onclick=safe(async()=>{
  const entry=runSubmissionEntry();
  if(entry?.state==="unknown")await sendOrdinarySubmission(entry);
});
$("run-submit-read").onclick=safe(async()=>{
  const entry=runSubmissionEntry();
  if(entry?.state!=="accepted-read-error")return;
  entry.state="accepted";
  entry.message=`任务已接受（${entry.runId.slice(0,16)}），正在重新读取。`;
  renderRunSubmission();
  await readAcceptedOrdinaryRun(entry,runUserSelectionGeneration);
});
