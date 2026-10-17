"use strict";
let naturalUsePreparation=null;
let naturalFirstGuide=null;
const naturalPreparationGoalRequests=new Map();
let token = "", activeRun = null, refs = [];
let ordinaryRunMaterialsReady = false;
let reconcileVersion = null, unresolvedAttempts = [];
let runSelectionGeneration = 0;
let foregroundRunRead = null;
let runUserSelectionGeneration = 0;
let runHistoryGeneration = 0;
let identityConnectionGeneration = 0;
let projectListGeneration = 0, projectSelectionGeneration = 0;
let projectSelectionRefresh = Promise.resolve(), projectCreatePending = null;
let activeApp = null, activeGoalCard = null;
let goalSelectionGeneration = 0, goalCardLoading = false, goalCardSaving = false;
let candidateSelectionGeneration = 0, candidateBusy = false, candidatePanelReady = false;
let appSelectionGeneration = 0, activeAppProject = null;
let workspaceSelectionGeneration = 0;
const candidateRequestKeys = new Map();
const extractionRequestKeys = new Map();
let extractionSource = null, extractionBusy = false;
let appCreateBusy = false;
let appReadRecovery = null, appReadBusy = false;
const appPreviewRequests = new Set();
const $ = (id) => document.getElementById(id);
const textTermEditors=new WeakMap(),textTermLimit=80;
function refreshTextTerm(input,reset=false){
  const state=textTermEditors.get(input);if(!state)return;
  if(reset)state.composing=false;
  const count=Array.from(input.value).length,over=count>textTermLimit;
  state.hint.textContent=`${count}/${textTermLimit} Unicode 码点${state.composing?" · 正在组合输入，完成后再提交":over?" · 超出上限，请修改后提交":""}`;
  if(!state.composing&&over)input.setAttribute("aria-invalid","true");else input.removeAttribute("aria-invalid");
}
function bindTextTermInput(input){
  if(textTermEditors.has(input))return;
  input.dataset.termInput="";input.removeAttribute("maxlength");input.pattern=`[\\s\\S]{0,${textTermLimit}}`;
  input.title=`检索词最多 ${textTermLimit} 个 Unicode 码点；不会自动截断输入。`;
  const hint=document.createElement("small");hint.id=input.id+"-limit";hint.setAttribute("role","status");hint.setAttribute("aria-live","polite");
  input.after(hint);input.setAttribute("aria-describedby",[input.getAttribute("aria-describedby"),hint.id].filter(Boolean).join(" "));
  const state={hint,composing:false};textTermEditors.set(input,state);
  input.addEventListener("input",event=>{if(event.isComposing)state.composing=true;refreshTextTerm(input);});
  input.addEventListener("compositionstart",()=>{state.composing=true;refreshTextTerm(input);});
  input.addEventListener("compositionend",()=>{state.composing=false;refreshTextTerm(input);});
  input.addEventListener("change",()=>refreshTextTerm(input));refreshTextTerm(input);
}
function textTermReady(input,report=false){
  if(input.disabled)return true;
  refreshTextTerm(input);
  if(textTermEditors.get(input)?.composing)return false;
  if(Array.from(input.value).length<=textTermLimit)return true;
  if(report)input.reportValidity();return false;
}
function textTermsReady(container,report=false){
  return [...container.querySelectorAll("[data-term-input]")].every(input=>textTermReady(input,report));
}
document.querySelectorAll("[data-term-input]").forEach(bindTextTermInput);
async function api(path, method = "GET", body) {
  const response = await fetch(path, {method, cache: "no-store", headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"}, ...(body ? {body: JSON.stringify(body)} : {})});
  const data = await response.json();
  const clockHeader=response.headers?.get?.("X-Sim2Act-Server-Time");
  if(clockHeader && data?.natural_deadline && Number.isFinite(Number(clockHeader)))
    Object.defineProperty(data,"naturalServerTime",{value:Number(clockHeader)});
  if (!response.ok) {const error=new Error(data.error?.code || data.detail?.[0]?.msg || "请求失败");error.detail=data.error?.message;error.httpStatus=response.status;error.submissionRejection=data.error?.submission_rejection||data.submission_rejection;throw error;}
  return data;
}
const safe = (fn) => async (event) => { event?.preventDefault(); $("error").textContent = ""; try {await fn(event);} catch (e) {$("error").textContent = e.message;} };
function row(text, action, label) {
  const div = document.createElement("div"); div.className = "row"; div.textContent = text;
  if (action) {const b = document.createElement("button"); b.textContent = label; b.onclick = safe(action); div.append(" ", b);}
  return div;
}
let resourceDownloadGeneration = 0;
const resourceDownloadRequests = new Set();
function resourceDownloadContext() {
  return {identity: token, connection: identityConnectionGeneration, project: $("project-select").value, generation: resourceDownloadGeneration};
}
function resourceDownloadCurrent(context) {
  return !!context.identity && !!context.project && context.identity === token && context.connection === identityConnectionGeneration && context.project === $("project-select").value && context.generation === resourceDownloadGeneration;
}
function saveResourceDownload(data, filename = `sim2act-resource.${data.format}`) {
  const url = URL.createObjectURL(new Blob([data.content], {type: "text/plain;charset=utf-8", endings: "transparent"}));
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.hidden = true;
  try {document.body.append(anchor);anchor.click();}
  finally {anchor.remove();setTimeout(() => URL.revokeObjectURL(url), 0);}
}
async function downloadResource(resource, context, button) {
  if (!resourceDownloadCurrent(context)) return;
  const key = JSON.stringify([context.connection, context.project, context.generation, resource.id]);
  if (resourceDownloadRequests.has(key)) return;
  resourceDownloadRequests.add(key);
  button.disabled = true;
  button.textContent = "正在读取…";
  try {
    const data = await api(`/api/resources/${encodeURIComponent(resource.id)}`);
    if (!resourceDownloadCurrent(context)) return;
    if (!data || data.id !== resource.id || data.project_id !== context.project || !["txt", "md", "csv", "json"].includes(data.format) || typeof data.content !== "string")
      throw new Error("材料响应无效，未下载文件");
    saveResourceDownload(data);
  } catch (error) {if (resourceDownloadCurrent(context)) throw error;}
  finally {
    resourceDownloadRequests.delete(key);
    button.disabled = false;
    button.textContent = "下载文件";
  }
}
let resourcePreviewGeneration = 0;
function invalidateResourcePreview() {
  resourcePreviewGeneration++;
  $("resource-preview").textContent = "";
  $("resource-preview").hidden = true;
}
async function previewResource(resource, context) {
  if (!resourceDownloadCurrent(context)) return;
  invalidateResourcePreview();
  const selection = resourcePreviewGeneration;
  const current = () => resourceDownloadCurrent(context) && selection === resourcePreviewGeneration;
  try {
    const data = await api(`/api/resources/${encodeURIComponent(resource.id)}`);
    if (!current()) return;
    if (!data || data.id !== resource.id || data.project_id !== context.project || !["txt", "md", "csv", "json"].includes(data.format) || typeof data.content !== "string")
      throw new Error("材料响应无效，未显示预览");
    $("resource-preview").textContent = data.content;
    $("resource-preview").hidden = false;
  } catch (error) {
    if (!current()) return;
    invalidateResourcePreview();
    $("error").textContent = error.message;
  }
}
function resourceMaterialRow(resource) {
  const context = resourceDownloadContext();
  const div = row(`${resource.name} · ${resource.format} · ${resource.hash.slice(0, 12)}`, () => previewResource(resource, context), "查看");
  const viewButton = div.querySelector("button"), view = viewButton.onclick;
  viewButton.onclick = event => resourceDownloadCurrent(context) ? view(event) : undefined;
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = "下载文件";
  button.onclick = safe(() => downloadResource(resource, context, button));
  div.append(" ", button);
  return div;
}
$("project-select").addEventListener("change", () => {resourceDownloadGeneration++;invalidateResourcePreview();});
async function refresh() {
  const pid = $("project-select").value; if (!pid) return;
  const identity=token,generation=++runHistoryGeneration;
  const current=()=>pid===$("project-select").value && identity===token && generation===runHistoryGeneration;
  let materials;
  try {materials = await api(`/api/projects/${pid}/resources`);}
  catch(error){if(current()){updateOrdinaryRunMaterials([],false);if(typeof invalidateConditionalSource === "function")invalidateConditionalSource("授权列表读取失败");}throw error;}
  if (!current()) return;
  if(typeof renderResourceMaterial === "function")renderResourceMaterial();
  if(typeof reconcileConditionalSources === "function")reconcileConditionalSources(materials);
  updateOrdinaryRunMaterials(materials);
  const selectedGoals=Array.from($("goal-card-resources").selectedOptions).map(o=>o.value);
  $("goal-card-resources").replaceChildren(...materials.map(m=>{const o=new Option(m.name,m.id);o.selected=selectedGoals.includes(m.id);return o;}));
  await refreshGoalCards(pid);
  if (!current()) return;
  $("materials").replaceChildren(...materials.map(resourceMaterialRow));
  const oldResource = $("app-resource").value;
  $("app-resource").replaceChildren(...materials.filter(x => x.format === "csv").map(x => {const o=document.createElement("option");o.value=x.id;o.textContent=x.name;return o;}));
  if (materials.some(x => x.id === oldResource)) $("app-resource").value = oldResource;
  await refreshApps();
  if(typeof refreshProtocol === "function")await refreshProtocol();
  if (!current()) return;
  $("run-history-status").textContent="正在读取持久任务历史…";
  let runs;
  try {runs=await api(`/api/projects/${pid}/runs?metadata_only=true`);}
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
  $("grants").replaceChildren(...grants.map(g => row(`${g.tool_ref} · ${g.principal_id.startsWith("runtime_") ? "项目运行身份" : g.principal_id.startsWith("appruntime_") ? "应用预览身份" : "当前使用者"} · ${g.revoked ? "已撤回" : "有效至 " + new Date(g.expires_at * 1000).toLocaleString()}`, g.revoked ? null : async () => {await api(`/api/grants/${g.id}/revoke`, "POST", {command:"revoke",version:g.revision});activeRun=null;clearApp();$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";invalidateResourcePreview();await refresh();}, "撤回")));
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
let ordinaryOutcomeView = null;
const ordinaryArtifactRequests = new Set();
function ordinaryOutcomeScope(id) {
  return JSON.stringify([token,identityConnectionGeneration,$("project-select").value,projectSelectionGeneration,workspaceSelectionGeneration,runUserSelectionGeneration,id]);
}
function ordinaryOutcomeCurrent(view) {
  return ordinaryOutcomeView === view && activeRun === view.run && !$("projects").hidden && view.scope === ordinaryOutcomeScope(view.run);
}
function ordinaryArtifactBindings(r, project) {
  if(r.contract?.snapshot?.goal?.project_id !== project)return [];
  const effects=Array.isArray(r.known_effects)?r.known_effects:[],bindings=[];
  for(const receipt of r.result?.receipts || []) {
    const id=receipt?.data?.resource_id,hash=receipt?.data?.hash,operation=receipt?.operation_id;
    if(receipt?.status !== "VERIFIED" || receipt.receipt_ref !== operation || !/^op_[a-f0-9]{32}$/.test(operation) || !/^res_[a-f0-9]{32}$/.test(id) || !/^[a-f0-9]{64}$/.test(hash) || !Array.isArray(receipt.artifact_refs) || receipt.artifact_refs.length !== 1 || receipt.artifact_refs[0] !== id)continue;
    const matches=effects.filter(effect=>effect?.id === operation);
    if(matches.length !== 1 || matches[0].status !== "VERIFIED" || matches[0].tool_ref !== "artifact.save_text" || matches[0].resource_id !== id || matches[0].content_hash !== hash)continue;
    const key=JSON.stringify([operation,id,hash]);
    if(!bindings.some(binding=>binding.key===key))bindings.push({key,id,hash,operation});
  }
  return bindings;
}
function updateOrdinaryArtifactNodes(view) {
  if(!ordinaryOutcomeCurrent(view))return;
  for(const node of $("run-artifacts")?.querySelectorAll("[data-ordinary-artifact]") || []) {
    const key=node.dataset.ordinaryArtifact,busy=ordinaryArtifactRequests.has(view.scope+key);
    for(const button of node.querySelectorAll("button"))button.disabled=busy;
    node.querySelector("[data-artifact-status]").textContent=view.messages.get(key) || "按需重新核对此任务、成果权限和内容指纹。";
    const preview=node.querySelector("pre");preview.hidden=!view.previews.has(key);preview.textContent=view.previews.get(key) || "";
  }
}
async function readOrdinaryArtifact(view, binding, download) {
  if(!ordinaryOutcomeCurrent(view))return;
  const key=view.scope+binding.key;if(ordinaryArtifactRequests.has(key))return;
  ordinaryArtifactRequests.add(key);view.messages.set(binding.key,"正在重新核对本次任务与成果…");updateOrdinaryArtifactNodes(view);
  try {
    const run=await api(`/api/runs/${encodeURIComponent(view.run)}`);
    if(!ordinaryOutcomeCurrent(view))return;
    if(run.id !== view.run || !ordinaryArtifactBindings(run,view.project).some(item=>item.key===binding.key))throw Error("成果与本次任务的已核验回执不匹配");
    const data=await api(`/api/resources/${encodeURIComponent(binding.id)}`);
    if(!ordinaryOutcomeCurrent(view))return;
    if(data?.id !== binding.id || data.project_id !== view.project || data.format !== "md" || data.hash !== binding.hash || typeof data.content !== "string")throw Error("成果来源或内容指纹不匹配");
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(data.content))),byte=>byte.toString(16).padStart(2,"0")).join("");
    if(!ordinaryOutcomeCurrent(view))return;
    if(digest !== binding.hash)throw Error("成果内容与已保存指纹不一致");
    if(download)saveResourceDownload(data,`sim2act-${view.run}-${binding.id}.${data.format}`);
    else view.previews.set(binding.key,data.content);
    view.messages.set(binding.key,download?"已按本次任务核对并交付原文件；目标验收状态不变。":"已重新授权并核对原文；技术核验不代表目标语义验收。");
  } catch(error) {
    if(!ordinaryOutcomeCurrent(view))return;
    if(error.httpStatus === 403) {
      clearRunDetail();activeRun=null;
      $("result").append(row("当前任务或成果读取授权不可用，已清除本次成果。请核对授权后从历史重新打开任务。"));
    } else {
      view.previews.delete(binding.key);
      view.messages.set(binding.key,`${error.message}；${download?"未下载文件":"未显示成果"}，可明确重新读取。`);
    }
  } finally {ordinaryArtifactRequests.delete(key);updateOrdinaryArtifactNodes(view);}
}
function renderOrdinaryOutcome(r) {
  const scope=ordinaryOutcomeScope(r.id);
  if(!ordinaryOutcomeView || ordinaryOutcomeView.scope !== scope)ordinaryOutcomeView={scope,run:r.id,project:$("project-select").value,previews:new Map(),messages:new Map()};
  const view=ordinaryOutcomeView,section=document.createElement("section");section.id="run-outcome";
  if(typeof r.result?.answer === "string" && r.result.answer) {
    const heading=document.createElement("h3");heading.textContent="本次回答";
    const answer=document.createElement("pre");answer.id="run-answer";answer.textContent=r.result.answer;section.append(heading,answer);
  }
  const bindings=ordinaryArtifactBindings(r,view.project);
  if(bindings.length) {
    const artifacts=document.createElement("section");artifacts.id="run-artifacts";
    const heading=document.createElement("h3");heading.textContent="本次已保存成果";artifacts.append(heading);
    for(const binding of bindings) {
      const node=row(`任务 ${r.id} · 成果 ${binding.id} · 指纹 ${binding.hash}`);node.dataset.ordinaryArtifact=binding.key;
      for(const [label,download] of [["查看此成果",false],["下载此成果",true]]) {
        const button=document.createElement("button");button.type="button";button.textContent=label;button.onclick=safe(()=>readOrdinaryArtifact(view,binding,download));node.append(button);
      }
      const status=document.createElement("p");status.dataset.artifactStatus="";status.setAttribute("role","status");status.setAttribute("aria-live","polite");
      const preview=document.createElement("pre");preview.hidden=true;preview.setAttribute("aria-label","此任务保存的成果原文");node.append(status,preview);artifacts.append(node);
    }
    section.append(artifacts);
  }
  if(section.childNodes.length)$("result").append(section);
  updateOrdinaryArtifactNodes(view);
}
function clearRunDetail() {
  ordinaryOutcomeView=null;
  if(typeof invalidateNaturalGoalAcknowledgements === "function")invalidateNaturalGoalAcknowledgements();
  unresolvedAttempts=[];reconcileVersion=null;
  for(const name of ["result","events","raw-result","commands","reconcile-attempt"])$(name).replaceChildren();
  $("reconcile-panel").hidden=true;
  $("reconcile-response").value="";$("reconcile-evidence").value="";$("reconcile-ack").checked=false;
}
async function showRun(id, userSelection = true, selectionGuard = () => true, validateReceipt = null) {
  if(!selectionGuard())return;
  const project=$("project-select").value,identity=token;
  if(!userSelection && foregroundRunRead?.id===id && foregroundRunRead.project===project && foregroundRunRead.identity===identity)return;
  const read=userSelection?{id,project,identity}:null;
  if(read)foregroundRunRead=read;
  try {return await readRunDetail(id,userSelection,selectionGuard,validateReceipt);}
  finally {if(read && foregroundRunRead===read)foregroundRunRead=null;}
}
async function readRunDetail(id, userSelection, selectionGuard, validateReceipt) {
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
  const labels = {QUEUED:"等待后台执行",RUNNING:"正在执行",PARTIAL:"部分完成",FAILED:"执行失败",WAITING_RESOURCE:"等待资源或授权",WAITING_APPROVAL:"等待确认计划",PAUSED:"已暂停",CANCELLED:"已取消"};
  $("result").replaceChildren(row(`${labels[r.status] || r.status}（${r.status}）`));
  if(internal){
    $("result").append(row(`内部工程只读任务 · 0 模型请求 · 结果版本 ${r.result_version ?? "无"} · 正式发布关闭`));
    if(r.result)$("result").append(row(`${r.result.column} 合计 ${r.result.sum}，共 ${r.result.count} 条记录。`));
  }
  if(!internal)renderOrdinaryProgress(r,attempts);
  if (r.result && !internal) {
    $("result").append(row(r.result.task_acceptance?.whole_task_accepted===true?"固定合成目标整体验收 PASS；通用语义与人工签收未完成，正式发布关闭。":`${r.result.mode === "MOCK" ? "MOCK 工程样例" : "书生运行记录"}：工具回执已核验，完整目标验收尚未执行。`));
    for (const receipt of r.result.receipts || []) {
      const data = receipt.data;
      if (typeof data.content === "string") {$("result").append(row("工具读取的材料（来源回执）"));const pre=document.createElement("pre");pre.textContent=data.content;$("result").append(pre);}
      else if (data.sum !== undefined) $("result").append(row(`${data.column} 合计 ${data.sum}，共 ${data.count} 条记录。`));
    }
    renderOrdinaryOutcome(r);
  }
  if (r.error) $("result").append(row(`需要处理：${r.error.message || r.error.code}`));
  $("raw-result").textContent = JSON.stringify({...r,unresolved_attempts:unresolvedAttempts}, null, 2);
  $("events").textContent = JSON.stringify(r.events, null, 2);
  if(typeof renderNaturalGoalRun === "function")await renderNaturalGoalRun(r,id,current);
  if(typeof renderNaturalReceiptCandidate === "function")await renderNaturalReceiptCandidate(r,id,current);
  if(!current())return;
  const commands = ["QUEUED","RUNNING"].includes(r.status) ? ["pause","cancel"] : ["PAUSED","WAITING_RESOURCE"].includes(r.status) ? (unresolvedAttempts.length ? ["cancel"] : ["resume","cancel"]) : [];
  $("commands").replaceChildren(...commands.map(command => {const b = document.createElement("button"); b.textContent = {pause:"暂停",cancel:"取消",resume:"继续"}[command]; b.onclick = safe(async () => {if(!current())return;await api(`/api/runs/${id}/commands`, "POST", {command,version:r.version}); if(current())await showRun(id);}); return b;}));
}
async function loadProjects(preferred=null) {
  const identity=token,connection=identityConnectionGeneration,list=++projectListGeneration;
  const ps = await api("/api/projects"); if(identity!==token || connection!==identityConnectionGeneration || list!==projectListGeneration)return; const old = $("project-select").value;
  const adopt=preferred && preferred.selection===projectSelectionGeneration;
  if(adopt && !ps.some(p=>p.id===preferred.id))throw Error("新项目已创建，列表尚未包含其回执；请重新读取项目列表。");
  const selected=adopt?preferred.id:old;
  $("project-select").replaceChildren(...ps.map(p => {const o = document.createElement("option"); o.value=p.id; o.textContent=p.name; return o;}));
  if (ps.some(p => p.id === selected)) $("project-select").value = selected;
  if(adopt && selected!==old){
    $("project-select").dispatchEvent(new Event("change"));
    await projectSelectionRefresh;
    return;
  }
  renderRunSubmission();
  await refresh();
}
function clearIdentityView() {
  projectCreatePending=null;$("project-form").querySelector("button").disabled=false;
  clearOrdinaryRunMaterials();
  clearNaturalFirstGuide();
  if(typeof clearNaturalUsePreparation === "function")clearNaturalUsePreparation();
  if(typeof clearSpecRecoveryMemory === "function")clearSpecRecoveryMemory();
  if(typeof pnClear === "function")pnClear();
  invalidateResourcePreview();
  if(typeof clearCsvLogic === "function")clearCsvLogic();if(typeof clearTextLogic === "function")clearTextLogic();
  if(typeof clearResourceMaterial === "function")clearResourceMaterial();
  if(typeof clearReportManifest === "function")clearReportManifest();
  if(typeof clearReportApps === "function")clearReportApps();
  if(typeof clearReportSave === "function")clearReportSave();
  if(typeof clearApplicationUse === "function")clearApplicationUse(true);
  runHistoryGeneration++;runSelectionGeneration++;runUserSelectionGeneration++;
  activeRun=null;refs=[];unresolvedAttempts=[];reconcileVersion=null;
  clearRunDetail();
  if(typeof clearProtocol === "function")clearProtocol();
  clearGoalCard();
  for(const id of ["runs","materials","grants","app-list","goal-card-list","result","commands","events","raw-result","resource-preview","run-history-status","run-submit-status","project-select","app-resource","goal-card-resources","capabilities","connections"]){$(id).replaceChildren();}
  renderProjectContext();
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
    $("identity-switch").hidden=false;
    const capabilities=await api("/api/capabilities");if(current())renderResourceCatalog(capabilities);
  } catch(error) {if(current())throw error;}
});
$("identity-switch").onclick=()=>{
  token="";identityConnectionGeneration++;clearIdentityView();
  $("token").value="";$("login").hidden=false;$("identity-switch").hidden=true;$("token").focus();
};
$("project-form").onsubmit = safe(async () => {
  if(projectCreatePending)return;
  if(!token)throw Error("先连接本机 API");
  const attempt={identity:token,connection:identityConnectionGeneration,selection:projectSelectionGeneration};
  const current=()=>attempt.identity===token && attempt.connection===identityConnectionGeneration;
  projectCreatePending=attempt;$("project-form").querySelector("button").disabled=true;
  try {
    const created=await api("/api/projects","POST",{name:$("project-name").value});
    if(!current())return;
    if(typeof created?.id!=="string" || !/^proj_[a-f0-9]{32}$/.test(created.id))throw Error("创建项目回执缺失；请读取项目列表核对，勿重复创建。");
    await loadProjects({id:created.id,selection:attempt.selection});
  } catch(error) {if(current())throw error;}
  finally {if(projectCreatePending===attempt){projectCreatePending=null;$("project-form").querySelector("button").disabled=false;}}
});
$("resource-form").onsubmit = safe(async () => {const pid=$("project-select").value;if(!pid)throw new Error("先选择项目");await api(`/api/projects/${pid}/resources`,"POST",{name:$("resource-name").value,format:$("format").value,content:$("content").value}); await refresh();});
$("run-form").onsubmit = safe(async () => submitOrdinaryRun());
$("run-history-refresh").onclick=safe(async()=>refresh());
$("reconcile-form").onsubmit = safe(async () => {const a=unresolvedAttempts.find(x=>x.attempt_id === $("reconcile-attempt").value);if(!a || !activeRun)throw new Error("请重新打开待核对任务");const decision=$("reconcile-decision").value;await api(`/api/runs/${activeRun}/reconcile`,"POST",{attempt_id:a.attempt_id,version:reconcileVersion,decision,expected_fingerprint:a.request_fingerprint,evidence:$("reconcile-evidence").value,acknowledge_unknown_cost:$("reconcile-ack").checked,response_json:decision === "record_response" ? $("reconcile-response").value : null});$("reconcile-response").value="";$("reconcile-evidence").value="";$("reconcile-ack").checked=false;await showRun(activeRun);});
$("project-select").onchange = safe(async () => {projectSelectionGeneration++;clearOrdinaryRunMaterials();if(typeof clearCsvLogic === "function")clearCsvLogic();if(typeof clearTextLogic === "function")clearTextLogic();if(typeof clearResourceMaterial === "function")clearResourceMaterial();if(typeof clearApplicationUse === "function")clearApplicationUse(true);runUserSelectionGeneration++;runHistoryGeneration++;$("runs").replaceChildren();$("run-history-status").textContent="";activeRun=null;renderRunSubmission();if(typeof clearProtocol === "function")clearProtocol();clearApp();clearGoalCard();clearRunDetail();$("resource-preview").textContent="";projectSelectionRefresh=refresh();await projectSelectionRefresh;});
document.querySelectorAll("#workspace-nav [data-tab]").forEach(b => b.onclick = () => selectWorkspace(b.dataset.tab));
selectWorkspace("projects");
document.querySelector("#projects .grid > section:last-child").append($("reconcile-panel"));
function renderProjectContext() {
  const select = $("project-select"), option = select.selectedOptions[0];
  const selected = !!token && !!select.value && option?.value === select.value;
  $("project-context-status").textContent = !token
    ? "请先连接本机 API，再选择项目。材料仅在所选项目内保存和授权。"
    : selected
      ? `当前所选项目：${option.textContent}。保存材料将授权给此项目；切换项目请使用项目工作区的原选择器。`
      : "尚未选择项目。请到项目工作区选择已有项目，或填写名称创建项目。";
  $("project-context-open").textContent = !token ? "填写连接令牌" : selected ? "选择或切换项目" : "选择或创建项目";
}
$("project-context-open").onclick = () => {
  selectWorkspace("projects");
  if (!token) {$("login").hidden = false;$("token").focus();}
  else if (Array.from($("project-select").options).some(option => !!option.value)) $("project-select").focus();
  else $("project-name").focus();
};
$("project-select").addEventListener("change", renderProjectContext);
const projectContextObserver = new MutationObserver(renderProjectContext);
projectContextObserver.observe($("project-select"), {childList: true, subtree: true, characterData: true, attributes: true, attributeFilter: ["selected", "value"]});
projectContextObserver.observe($("login"), {attributes: true, attributeFilter: ["hidden"]});
renderProjectContext();

function selectResourceCategory(category) {
  const categories = ["materials", "capabilities", "connections"];
  if (!categories.includes(category)) return;
  categories.forEach(id => $("resource-" + id).hidden = id !== category);
  document.querySelectorAll("#resource-filters [data-resource-category]").forEach(button => {
    if (button.dataset.resourceCategory === category) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
}
function renderResourceCatalog(data) {
  $("capabilities").textContent = "";
  $("connections").textContent = "";
  const connection = data?.connection;
  if (!Array.isArray(data?.tools) || !data.tools.every(tool => typeof tool === "string") || data.code_execution !== "DISABLED" || !connection || typeof connection.model !== "string" || !["MOCK", "LIVE"].includes(connection.mode) || connection.status !== (connection.mode === "MOCK" ? "MOCK_ENGINEERING" : "LIVE_NOT_ACCEPTED"))
    throw new Error("能力与连接目录响应无效");
  $("capabilities").textContent = JSON.stringify({tools: data.tools, code_execution: data.code_execution}, null, 2);
  $("connections").textContent = JSON.stringify({model: connection.model, mode: connection.mode, status: connection.status}, null, 2);
}
document.querySelectorAll("#resource-filters [data-resource-category]").forEach(button => button.onclick = () => selectResourceCategory(button.dataset.resourceCategory));
selectResourceCategory("materials");

function createHealthSampler(render) {
  let generation = 0;
  return async (readHealth) => {
    const sample = ++generation;
    let available = false, message = "后台健康检查失败";
    try {
      const h = await readHealth();
      if (!h || !["MOCK", "LIVE"].includes(h.mode) || h.api !== "UP" || !["UP", "OFFLINE"].includes(h.worker))
        throw new Error("健康响应结构无效");
      message = `健康检查：${h.mode} · API ${h.api} · worker ${h.worker}`;
      available = true;
    } catch (_) { /* Only health sampling failures affect the health message. */ }
    if (sample !== generation) return false;
    render(message);
    return available;
  };
}
const sampleHealth = createHealthSampler(message => $("health").textContent = message);
let backgroundRefreshInFlight=false;
setInterval(async () => {
  if(backgroundRefreshInFlight)return;
  backgroundRefreshInFlight=true;
  try {
    if (!await sampleHealth(() => api("/health"))) return;
    if(token){await refresh();if(activeRun)await showRun(activeRun,false);}
  } catch(e) {$("error").textContent=e.message;}
  finally {backgroundRefreshInFlight=false;}
},2500);

function clearApp(preserveFirstGuide=null) {
  if(naturalFirstGuide!==preserveFirstGuide)clearNaturalFirstGuide();
  if(typeof clearNaturalUsePreparation === "function")clearNaturalUsePreparation();
  if(typeof clearAppOwnGoal === "function")clearAppOwnGoal();
  if(typeof clearCsvLogic === "function")clearCsvLogic();if(typeof clearTextLogic === "function")clearTextLogic();
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
  const list=await api("/api/apps?metadata_only=true");
  if(pid!==$("project-select").value || identity!==token || generation!==appSelectionGeneration)return;
  const items=list.items.filter(x=>x.project_id === $("project-select").value);
  const connection=identityConnectionGeneration;
  $("app-list").replaceChildren(...items.map(x=>{
    const natural=["NATURAL_PA","NATURAL_PB"].includes(x.use_family);
    const literal=x.use_family==="LITERAL_TEXT";
    const family=natural?`自然规范 ${x.use_family==="NATURAL_PA"?"P-A":"P-B"} · 定义 ${x.definition_version} · 逐次材料 + Goal`:(literal?"文本字面检索 · 固定 TXT/MD，检索词可变":x.use_family==="CLOSED_TEXT_WORKFLOW"?"四步文本流程 · 固定 TXT/MD，两检索词 + 报告开关":(x.use_family==="CSV"?"CSV 固定材料":"其他应用"));
    return row(`${x.name} · ${family} · 未发布草案；当前授权需打开核查`,()=>{
      if(identity===token&&connection===identityConnectionGeneration&&pid===$("project-select").value)return showApp(x.id,pid);
    },natural||literal?"查看应用与保存实例":"打开预览");
  }));
  if(!items.length)$("app-list").textContent="先保存 CSV 材料，再创建一个草案。";
  if(typeof refreshApplicationUse === "function")await refreshApplicationUse(items);
  if(typeof refreshReportApps === "function")await refreshReportApps();
}
function previewText(r) {
  if(r.status === "FAILED")return `预览失败（FAILED）：${r.error?.message || r.error?.code} · 已保留这次历史`;
  return `预览成功（SUCCEEDED） · ${r.output.column} 合计 ${r.output.sum}，共 ${r.output.count} 条 · 0 模型请求 · 仅预览`;
}
function showPreviewResult(r,history=false){
  if(r.output?.status === "MODEL_EXECUTION_REQUIRED"){$("app-output").dataset.state="pending";$("app-output").textContent=(history ? "历史材料预览\n" : "本次材料预览\n")+"抽取需模型执行，默认关闭；此预览没有生成答案，语义待验。\n"+JSON.stringify(r.output,null,2);return;}
  if(r.output?.citations||r.output?.checklist){$("app-output").dataset.state="success";$("app-output").textContent=(history ? "历史记录\n" : "本次预览\n")+JSON.stringify(r.output,null,2);return;}
  $("app-output").dataset.state=r.status === "FAILED" ? "error" : "success";
  $("app-output").replaceChildren(row(`${history ? "历史记录 · " : ""}${previewText(r)} · ${r.id.slice(0,16)}`));
}
async function showApp(id,pid=$("project-select").value,onSelectionStart=null,selectionCurrent=()=>true,validateSelected=null,preserveFirstGuide=null) {
  if(pid !== $("project-select").value || !selectionCurrent())return false;
  clearApp(preserveFirstGuide);const generation=appSelectionGeneration;
  onSelectionStart?.(generation);
  const identity=token;
  const a=await api(`/api/apps/${id}`);
  if(generation !== appSelectionGeneration || pid !== $("project-select").value || identity !== token || !selectionCurrent())return false;
  if(a.id !== id || a.project_id !== pid)throw Error("候选不属于当前选择，请重新选择");
  if(validateSelected)await validateSelected(a);
  if(generation !== appSelectionGeneration || pid !== $("project-select").value || identity !== token || !selectionCurrent())return false;
  activeApp=id;activeAppProject=pid;
  if(a.input_guidance.mode === "MODEL_SPEC_CHECKLIST"){
    $("app-title").textContent=a.name+(a.candidate.namespace==="pa-natural-spec-app.v1"?" · 未标注规范待验清单 · 未发布":" · 合成标记规范清单 · 未发布");
    $("app-origin").textContent=a.candidate.spec_task?`P-B 成功任务 ${a.candidate.spec_task.source_run_id} 的独立提取；来源图与人工编辑图分别冻结。新材料运行需模型、默认关闭；语义 UNKNOWN，人工 PENDING，未发布。`:"模型选择的有限步骤图；出处核查与语义完整性分开。真实模型关闭，语义 NOT_RUN。";
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify(a.candidate.goal,null,2);
    $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,recipe:a.candidate.spec_recipe,fingerprint:a.fingerprint},null,2);
    $("app-preview-form").hidden=false;$("app-preview-submit").hidden=false;$("app-preview-submit").disabled=appPreviewRequests.has(id);$("app-input-hint").textContent=a.candidate.namespace==="pa-natural-spec-app.v1"?"新材料抽取需模型执行，默认关闭；预览保留原文和完整目标，不生成答案，不保存制品。":"预览不保存业务制品；实际内部实例运行保存一个 JSON 清单。";$("app-column-label").hidden=true;$("app-column").required=false;
    $("app-agent-term-label").hidden=true;$("app-agent-term").required=false;$("app-agent-term").disabled=true;refreshTextTerm($("app-agent-term"),true);$("csv-extraction-panel").hidden=true;
    await openInternal(a,generation,selectionCurrent);return generation===appSelectionGeneration&&selectionCurrent();
  }
  if(a.input_guidance.mode === "CLOSED_TEXT_WORKFLOW")return openTextWorkflowApp(a,generation,selectionCurrent);
  if(typeof openDeliveryGraph === "function")openDeliveryGraph(a,generation,a.candidate.actions.length===1&&a.candidate.actions[0].executor.kind==="registered_tool"&&a.candidate.actions[0].executor.ref==="data.aggregate_csv"?selectionCurrent:null);
  if(a.input_guidance.mode === "BOUNDED_REPORT")return openReportManifest(a,generation);
  const origin=a.candidate.generation;
  const extraction=a.candidate.extraction;
  const taskProof=a.candidate.task_proof;
  if(taskProof?.proof?.kind === "accepted_fixed_natural_goal.v1"){
    $("app-origin").textContent="来源 Run SUCCEEDED · 固定合成目标契约 PASS · 新 CSV / column 候选适用范围仍须人工核对 · owner PENDING · 未发布，完整 P-B 未验收";
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify(taskProof,null,2);
  } else if(taskProof?.proof?.kind === "verified_natural_csv_receipt_only.v1"){
    $("app-origin").textContent=`来源 Run PARTIAL · 单项 VERIFIED 求和回执候选 · 整体任务未验收 · 新 CSV 绑定 / column 变量 · 固定 aggregate_csv@1 只读步骤 · 人工适用范围 PENDING · 未发布，完整 P-B 未验收`;
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify(taskProof,null,2);
  } else if(taskProof?.proof?.kind === "completed_registered_csv_apprun.v1"){
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
  const agent=a.input_guidance.mode === "OFFLINE_REPLAY_ONLY",literal=a.input_guidance.mode === "REGISTERED_LITERAL";
  $("app-preview-form").hidden=false;
  $("app-column-label").hidden=agent||literal;$("app-column").required=!(agent||literal);
  $("app-agent-term-label").hidden=!(agent||literal);$("app-agent-term").required=agent||literal;$("app-agent-term").disabled=!(agent||literal);$("app-agent-term").value="";refreshTextTerm($("app-agent-term"),true);
  $("app-preview-submit").hidden=agent;$("csv-extraction-panel").hidden=agent||literal;
  $("app-manifest").textContent=JSON.stringify({candidate:a.candidate,fingerprint:a.fingerprint,runtime_id:a.runtime_id},null,2);
  if(literal){
    const independent=taskProof?.proof?.kind==="authorized_data_free_text_logic.v1";
    $("app-origin").textContent=taskProof ? `来源：已成功内部文本 AppRun ${taskProof.proof.source_run_id} · 独立回执与完整字面证据核查 · 新 TXT/MD 绑定 + term 参数 · owner PENDING · 语义 UNKNOWN · 未发布，完整 P-B 未验收` : a.candidate.namespace==="pa-model-literal-material-binding.v1" ? `来源：实际模型图 ${a.candidate.pa_binding.model_candidate_fingerprint} · 明确绑定自己的新目标与新 TXT/MD · 原源仍需审计权限 · owner PENDING · 语义 UNKNOWN · 未发布` : `来源：已冻结目标与实际读取反馈 ${a.candidate.goal_application.run_id} · 字面检索 · 语义 UNKNOWN · 未发布`;
    $("app-frozen-goal").hidden=false;$("app-frozen-goal-text").textContent=JSON.stringify(taskProof ? {source_goal:a.candidate.goal,source:taskProof,new_material:a.candidate.manifest.data_bindings} : a.candidate.goal,null,2);
    if(independent){$("app-origin").textContent=`来源：项目独立文本逻辑 ${taskProof.proof.logic_id} · 新材料与新只读身份 · owner PENDING · 语义 UNKNOWN · 未发布，完整 P-B 未验收`;$("app-frozen-goal-text").textContent=JSON.stringify({logic:taskProof,new_material:a.candidate.manifest.data_bindings},null,2);}
    $("app-input-hint").textContent="TXT/MD 逐字匹配；输入非空无首尾空白、至多80字符的检索词。每次从授权材料重新计算全部匹配行，无需上传答案。";
    $("app-preview-submit").disabled=appPreviewRequests.has(id);
    $("app-history").replaceChildren(...a.history.map(r=>row(`${r.input.term || "无效输入"} · ${r.status}`,()=>showPreviewResult(r,true),"回读历史")));
    if(typeof openInternal === "function")await openInternal(a,generation,selectionCurrent);
    return generation === appSelectionGeneration && pid === $("project-select").value && identity === token && activeApp === id && selectionCurrent();
  }
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
  if(typeof openInternal === "function")await openInternal(a,generation,selectionCurrent);
  if(generation!==appSelectionGeneration||!selectionCurrent())return false;
  if(typeof deliveryContext!=="undefined"&&deliveryContext?.generation===generation&&deliveryContext.selectionCurrent===selectionCurrent)deliveryContext.selectionCurrent=null;
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
  if(!textTermsReady($("app-preview-form"),true))return;
  if(!activeApp || activeAppProject !== $("project-select").value)throw new Error("先打开当前项目的草案");
  const id=activeApp,pid=activeAppProject,goalGeneration=goalSelectionGeneration;
  let generation=appSelectionGeneration,result=null;
  if(appPreviewRequests.has(id))return;
  const current=()=>generation === appSelectionGeneration && pid === $("project-select").value && goalGeneration === goalSelectionGeneration;
  appPreviewRequests.add(id);$("app-preview-submit").disabled=true;
  $("app-output").dataset.state="loading";$("app-output").textContent="正在读取授权材料并运行新预览…";
  try {
    result=await api(`/api/apps/${id}/previews`,"POST",{input:engineering?.spec ? {} : $("app-column-label").hidden ? {term:$("app-agent-term").value} : {column:$("app-column").value},request_key:crypto.randomUUID()});
    if(current() && await showApp(id,pid,g=>{generation=g;})){if(current() && activeApp===id)showPreviewResult(result);}
  }catch(e){if(current()){
    if(result)setAppReadFailure({id,pid,kind:"preview",result,goalGeneration},e);
    else{$("app-output").dataset.state="error";$("app-output").textContent=`预览未打开：${e.message}；可重新打开草案核对历史。`;}
  }}
  finally{appPreviewRequests.delete(id);$("app-preview-submit").disabled=appPreviewRequests.has(activeApp) || (!$("app-column-label").hidden && !$("app-column").value);}
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
  entry.message=rejected?`执行被拒绝：${error.message}`:`保存 v${entry.body.expected_version} 的接受回执 UNKNOWN；请显式恢复原版本、原指纹与原请求键，不能另建重复任务。`;
  if(goalRunKey()===key)renderGoalRun();return;
 }
 if(current()&&selection===runUserSelectionGeneration)await readGoalRun(entry,current,selection);
 if(goalRunKey()===key)renderGoalRun();
}
$("goal-card-run").onclick=safe(()=>executeGoalCard());
$("goal-card-run-recover").onclick=safe(()=>executeGoalCard(true));
const goalCardFields=["title","goal","known","assumptions","unresolved","constraints","acceptance_checks"];
function updateGoalCardSave() {
  if(typeof renderNaturalGoalControls === "function")renderNaturalGoalControls();if(typeof renderGoalApplicationControls === "function")renderGoalApplicationControls();
  $("goal-card-save").disabled=goalCardLoading || goalCardSaving;
  updateCandidateCreate();
  renderGoalRun();
}
function clearGoalCard(preserveApp=false) {
  if(typeof clearTrialConsent === "function")clearTrialConsent();
  if(typeof clearNaturalGoal === "function")clearNaturalGoal();
  if(goalRunDisplayed && activeRun===goalRunDisplayed){activeRun=null;runSelectionGeneration++;clearRunDetail();}
  goalRunDisplayed=null;
  if(!preserveApp)clearApp(); // A goal selection also invalidates in-flight app readback/recovery.
  goalSelectionGeneration++;candidateSelectionGeneration++;candidatePanelReady=false;
  $("goal-candidate-form").hidden=true;$("goal-candidate-list").replaceChildren();
  $("goal-candidate-status").textContent="先打开已保存目标卡。";
  goalCardLoading=false;updateGoalCardSave();
  activeGoalCard=null;renderGoalRun();if(typeof renderNaturalGoalControls === "function")renderNaturalGoalControls();if(typeof renderGoalApplicationControls === "function")renderGoalApplicationControls();$("goal-card-form").reset();$("goal-card-status").textContent="新建草案";
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
    if(card.id !== id || card.project_id !== pid)throw Error("目标卡不属于当前选择，请重新选择");
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
  if(typeof renderNaturalGoalControls === "function")renderNaturalGoalControls();if(typeof renderGoalApplicationControls === "function")renderGoalApplicationControls();
  goalCardFields.forEach(f=>{$(`goal-card-${f}`).value=Array.isArray(card.content[f]) ? card.content[f].join("\n") : card.content[f];});
  Array.from($("goal-card-resources").options).forEach(o=>o.selected=card.content.resource_refs.includes(o.value));
  $("goal-card-status").textContent=`草案 v${card.version} · 目标验收 NOT_RUN · 执行使用已保存版本；保存将建立新版本`;
  $("goal-card-history-detail").textContent="";
  $("goal-card-history").replaceChildren(...card.history.map(v=>row(`v${v.version} · ${v.snapshot.content.title}`,()=>{const labels={title:"名称",goal:"目标",known:"已知",assumptions:"假设",unresolved:"未决项",constraints:"硬条件",acceptance_checks:"验收检查"};$("goal-card-history-detail").textContent=goalCardFields.map(f=>`${labels[f]}：\n${Array.isArray(v.snapshot.content[f]) ? v.snapshot.content[f].join("\n") : v.snapshot.content[f]}`).join("\n\n")+`\n\n绑定材料 ${v.snapshot.resource_snapshots.length} 份 · 只读历史版本 v${v.version}`;},"回看版本")));
  if(typeof refreshNaturalGoalStatus === "function")await refreshNaturalGoalStatus();
  if(!current())return;
  await refreshGoalCandidates(id,pid,generation);
}
$("goal-card-new").onclick=()=>clearGoalCard();
const saveGoalCardBody=(pid,card,body)=>card ? api(`/api/goal-cards/${card.id}`,"PUT",{...body,expected_version:card.version}) : api(`/api/projects/${pid}/goal-cards`,"POST",body);
$("goal-card-form").onsubmit=safe(async()=>{
  const pid=$("project-select").value;if(!pid)throw Error("先选择项目");
  if(goalCardLoading || goalCardSaving)return;
  const selectedCard=activeGoalCard, generation=goalSelectionGeneration;
  if(selectedCard && selectedCard.project_id !== pid)throw Error("目标卡不属于当前项目，请重新选择");
  const body={resource_refs:Array.from($("goal-card-resources").selectedOptions).map(o=>o.value)};
  goalCardFields.forEach(f=>{body[f]=["title","goal"].includes(f) ? $(`goal-card-${f}`).value : $(`goal-card-${f}`).value.split("\n").map(s=>s.trim()).filter(Boolean);});
  if(naturalUsePreparation){await saveNaturalPreparationGoal(naturalUsePreparation,body);return;}
  const identity=token,connection=identityConnectionGeneration;
  goalCardSaving=true;updateGoalCardSave();
  try {
    const result=await saveGoalCardBody(pid,selectedCard,body);
    if(identity!==token || connection!==identityConnectionGeneration || generation !== goalSelectionGeneration || pid !== $("project-select").value)return;
    await refreshGoalCards(pid);
    if(identity!==token || connection!==identityConnectionGeneration || generation !== goalSelectionGeneration || pid !== $("project-select").value)return;
    await showGoalCard(result.id,pid);
  } finally {goalCardSaving=false;updateGoalCardSave();}
});


function selectWorkspace(id,preserveFirstGuide=null) {
  if(typeof clearSavedDagUse === "function")clearSavedDagUse();
  if(naturalFirstGuide!==preserveFirstGuide)clearNaturalFirstGuide();
  if(typeof clearNaturalUsePreparation === "function")clearNaturalUsePreparation();
  if(typeof clearInternalRunReread === "function")clearInternalRunReread();
  if(typeof clearTrialConsent === "function")clearTrialConsent();
  workspaceSelectionGeneration++;
  if(preserveFirstGuide&&naturalFirstGuide===preserveFirstGuide)preserveFirstGuide.workspace=workspaceSelectionGeneration;
  ["projects","apps","resources"].forEach(tab=>$(tab).hidden=tab !== id);
  document.querySelectorAll("#workspace-nav [data-tab]").forEach(button => {
    if (button.dataset.tab === id) button.setAttribute("aria-current", "true");
    else button.removeAttribute("aria-current");
  });
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
function clearOrdinaryRunMaterials() {
  refs=[];ordinaryRunMaterialsReady=false;$("run-materials").replaceChildren();
}
function updateOrdinaryRunMaterials(materials,ready=true) {
  const select=$("run-materials"),entry=runSubmissionEntry();
  const locked=entry && ["sending","unknown"].includes(entry.state);
  const selected=locked?entry.body.resource_refs:Array.from(select.selectedOptions,o=>o.value);
  refs=materials.map(m=>m.id);ordinaryRunMaterialsReady=ready;
  select.replaceChildren(...materials.map(m=>new Option(`${m.name} · ${m.format}`,m.id)));
  for(const id of selected)if(!refs.includes(id))select.append(new Option(`当前列表不可用的原选择 · ${id}`,id));
  for(const option of select.options)option.selected=selected.includes(option.value);
  renderRunSubmission();
}
function ordinaryRunMaterialSelection() {
  const selected=Array.from($("run-materials").selectedOptions,o=>o.value);
  const unavailable=selected.filter(id=>!refs.includes(id));
  return {selected,unavailable,invalid:selected.length>8 || unavailable.length>0 || (!ordinaryRunMaterialsReady && selected.length>0)};
}
function renderOrdinaryRunMaterials(entry,locked) {
  const select=$("run-materials");
  if(locked){
    for(const id of entry.body.resource_refs)if(!Array.from(select.options).some(o=>o.value===id))select.append(new Option(`原提交材料 · ${id}`,id));
    for(const option of select.options)option.selected=entry.body.resource_refs.includes(option.value);
  }
  select.disabled=Boolean(locked);
  const state=ordinaryRunMaterialSelection();
  $("run-materials-status").textContent=locked
    ? `原提交已冻结 ${state.selected.length} 份材料；恢复沿用原集合和请求键。${state.unavailable.length?`其中 ${state.unavailable.length} 份当前列表不可用。`:""}`
    : state.selected.length>8 ? `已选择 ${state.selected.length}/8 份材料；请减少选择后提交，不会自动截断。`
      : state.unavailable.length ? `有 ${state.unavailable.length} 份原选择当前不可用；请刷新列表核对，或取消该选择后提交。`
        : `已选择 ${state.selected.length}/8 份材料。${state.selected.length?"仅所选材料随本次目标提交。":"本次未附加材料。"}${ordinaryRunMaterialsReady?"":"材料列表尚未就绪。"}`;
  return state;
}
function renderRunSubmission() {
  const entry=runSubmissionEntry();
  const blocked=entry && ["sending","unknown"].includes(entry.state);
  const materials=renderOrdinaryRunMaterials(entry,blocked);
  $("run-submit").disabled=Boolean(blocked)||materials.invalid;
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
  const materials=ordinaryRunMaterialSelection();
  if(materials.invalid){renderRunSubmission();throw Error("请明确选择当前可用的最多8份材料，或不附加材料。");}
  const body=Object.freeze({goal:$("goal").value,resource_refs:Object.freeze(materials.selected),request_key:crypto.randomUUID()});
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
$("run-materials").onchange=()=>renderRunSubmission();

"use strict";
// Browser-local import; existing resource POST remains the only explicit save/authorization.
let resourceFileGeneration=0, resourceFileReader=null, resourceFileSnapshot=null;
const resourceSaveRequests=new Map();
function resourceContext() {return {identity:token,connection:identityConnectionGeneration,project:$("project-select").value,generation:resourceFileGeneration};}
function resourceContextCurrent(c) {return c.identity===token && c.connection===identityConnectionGeneration && c.project===$("project-select").value && c.generation===resourceFileGeneration;}
function resourceSaveKey(c=resourceContext()) {return JSON.stringify([c.identity,c.project]);}
function renderResourceMaterial() {
  const pending=resourceSaveRequests.get(resourceSaveKey());
  const preparation=naturalUsePreparation,locked=!!preparation&&(preparation.step!=="material"||naturalPreparationGoalRequests.has(preparation.key));
  for(const id of ["resource-file","resource-name","format","content","resource-file-clear"])$(id).disabled=!!pending||locked;
  $("resource-save").disabled=!!resourceFileReader || !!pending || locked || !$("project-select").value;
  $("resource-save-read").hidden=!["unknown","accepted"].includes(pending?.state);
  $("resource-save-reset").hidden=$("resource-save-read").hidden;
  if(pending){
    $("resource-name").value=pending.body.name;$("format").value=pending.body.format;$("content").value=pending.body.content;
    $("resource-file-status").textContent=pending.state==="unknown" ? "保存回执未知：材料可能已保存并授权。禁止重发；先刷新材料列表核对名称与内容，不能仅凭相同内容认定是本次保存。" : pending.state==="accepted" ? `先前保存已接受：${pending.body.name} · ${pending.saved.id}。页面选择已变化，未自动继续；请刷新材料列表核对。` : "正在保存已核对材料…";
  }
}
function cancelResourceFileRead() {
  resourceFileGeneration++;
  const reader=resourceFileReader;resourceFileReader=null;
  if(reader?.readyState===FileReader.LOADING)reader.abort();
}
function clearResourceMaterial() {
  cancelResourceFileRead();resourceFileSnapshot=null;
  $("resource-file").value="";$("resource-name").value="";$("content").value="";$("format").value="csv";
  $("resource-file-status").textContent="";renderResourceMaterial();
  $("resource-file-preview").textContent="";$("resource-file-preview").hidden=true;
}
function editResourceMaterial() {
  cancelResourceFileRead();resourceFileSnapshot=null;$("resource-file").value="";
  $("resource-file-status").textContent="手工文本模式：保存当前表单内容；已解除原文件绑定。";renderResourceMaterial();
  $("resource-file-preview").textContent="";$("resource-file-preview").hidden=true;
}
function selectResourceFile() {
  if(resourceSaveRequests.has(resourceSaveKey()))return;
  cancelResourceFileRead();resourceFileSnapshot=null;
  $("resource-name").value="";$("content").value="";
  $("resource-file-preview").textContent="";$("resource-file-preview").hidden=true;
  const c=resourceContext(),generation=resourceFileGeneration,files=$("resource-file").files;
  const current=()=>resourceContextCurrent(c) && generation===resourceFileGeneration;
  const fail=message=>{if(current()){$("resource-file").value="";$("resource-file-status").textContent=message;renderResourceMaterial();}};
  if(!files?.length){clearResourceMaterial();return;}
  if(!c.project){fail("先选择项目，再选择文本文件。");return;}
  if(files.length!==1){fail("一次只能选择一个文本文件。");return;}
  const file=files[0];
  const format = /\.(txt|md|csv|json)$/i.exec(file.name)?.[1].toLowerCase();
  if(naturalPreparationCurrent(naturalUsePreparation) && (!['txt','md'].includes(format)||file.size>2048)){fail("本应用仅支持 UTF-8 TXT/MD，最多2048字节、40行；文件尚未保存。");return;}
  if(!format || file.name.length>200){fail("请选择名称不超过200字的 .txt、.md、.csv 或 .json 文件。");return;}
  if(file.size===0 || file.size>32768){fail("文本文件须为1–32768字节。");return;}
  const reader=new FileReader();resourceFileReader=reader;
  $("resource-file-status").textContent=`正在本页读取 ${format.toUpperCase()}；尚未保存或授权。`;renderResourceMaterial();
  reader.onload=()=>{
    if(!current())return;
    resourceFileReader=null;
    try {
      const bytes=new Uint8Array(reader.result);
      if(bytes.length!==file.size)throw Error("本地文件长度不一致；文件尚未保存。");
      if(["csv", "json"].includes(format) && bytes[0]===0xef && bytes[1]===0xbb && bytes[2]===0xbf)throw Error(`请选择无 BOM 的 UTF-8 ${format.toUpperCase()}；文件尚未保存。`);
      const content=new TextDecoder("utf-8",{fatal:true,ignoreBOM:true}).decode(bytes);
      if(format === "csv" && content.includes("\0"))throw Error("CSV 含不支持的空字节；文件尚未保存。");
      if(format !== "csv" && /[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(content))throw Error("文件含不支持的二进制控制字符；文件尚未保存。");
      if(format === "json") {
        try {JSON.parse(content);}
        catch (_) {throw Error("JSON 语法无效；请修正文件后重新选择，文件尚未保存。");}
      }
      if(naturalPreparationCurrent(naturalUsePreparation)){const error=naturalPreparationMaterialError({format,content});if(error)throw Error(error);}
      $("resource-name").value=file.name;$("format").value=format;$("content").value=content;
      resourceFileSnapshot={...c,content,displayContent:$("content").value,name:file.name,bytes:file.size};
      $("resource-file-preview").textContent=format === "csv" ? content : $("content").value;$("resource-file-preview").hidden=false;
      $("resource-file-status").textContent=`已在本页读取 ${file.name} · ${file.size}字节 · 目标项目：${$("project-select").selectedOptions[0].textContent}。尚未保存或授权。${format === "json" ? "JSON 语法已检查，保存仍需原校验。" : ""}请核对待保存文本，再点击原保存按钮；CSV 保留原换行，TXT/MD/JSON 按表单文本保存，编辑后转为手工文本。`;
    } catch(error){fail(error.name==="TypeError" ? "文件不是有效 UTF-8；请另存为 UTF-8 后重选。" : error.message);}
    renderResourceMaterial();
  };
  reader.onerror=()=>{if(current()){resourceFileReader=null;fail("本地文件读取失败；未保存，请重新选择。");}};
  reader.onabort=()=>{if(current()){resourceFileReader=null;fail("本地读取已取消；未保存。");}};
  reader.readAsArrayBuffer(file);
}
async function saveResourceMaterial() {
  const c=resourceContext(),key=resourceSaveKey(c);
  if(!c.project)throw Error("先选择项目");
  if(resourceFileReader || resourceSaveRequests.has(key))return;
  const file=resourceFileSnapshot;
  const original=file && resourceContextCurrent(file) && $("resource-name").value===file.name && $("format").value==="csv" && $("content").value===file.displayContent;
  const body={name:$("resource-name").value,format:$("format").value,content:original ? file.content : $("content").value};
  const preparation=naturalUsePreparation;
  if(preparation){if(!naturalPreparationCurrent(preparation)||preparation.step!=="material")return;const error=naturalPreparationMaterialError(body);if(error){$("resource-file-status").textContent=error;return;}}
  const pending={body:Object.freeze(body),state:"saving"};resourceSaveRequests.set(key,pending);renderResourceMaterial();
  let saved;
  try {saved=await api(`/api/projects/${c.project}/resources`,"POST",body);if(typeof saved?.id!=="string" || !/^res_[a-f0-9]{32}$/.test(saved.id))throw Error("保存回执缺失");}
  catch(error){
    if(error.httpStatus>=400 && error.httpStatus<500 && ![408,425,429].includes(error.httpStatus)){resourceSaveRequests.delete(key);if(c.identity===token && c.project===$("project-select").value){renderResourceMaterial();$("resource-file-status").textContent=`保存被拒绝：${error.message}`;}}
    else {pending.state="unknown";if(resourceContextCurrent(c))renderResourceMaterial();}
    return;
  }
  if(!resourceContextCurrent(c)){pending.state="accepted";pending.saved=saved;if(c.identity===token && c.project===$("project-select").value)renderResourceMaterial();return;}
  resourceSaveRequests.delete(key);
  if(preparation){
    if(!naturalPreparationCurrent(preparation))return;
    preparation.material={id:saved.id,body};preparation.step="material-saved";
    $("resource-file-status").textContent=`已保存本次材料 ${saved.id}；尚未创建 Goal 或运行。`;
    naturalPreparationRender(preparation);return;
  }
  clearResourceMaterial();$("resource-file-status").textContent=`已保存并授权当前项目：${body.name} · ${saved.id}。可在应用中选择此 CSV；创建草案仍需单独确认授权。`;
  const readContext=resourceContext();
  try {await refresh();}
  catch(error){if(resourceContextCurrent(readContext))$("resource-file-status").textContent+=` 材料列表读取失败：${error.message}；保存回执已收到，只需刷新列表核对，不要重复保存。`;}
}
$("resource-file").onchange=selectResourceFile;
$("resource-file-clear").onclick=()=>clearResourceMaterial();
for(const id of ["resource-name","format","content"])$(id).oninput=editResourceMaterial;
$("resource-form").onsubmit=safe(saveResourceMaterial);
$("resource-save-read").onclick=safe(async()=>{const c=resourceContext();await refresh();if(resourceContextCurrent(c) && resourceSaveRequests.get(resourceSaveKey(c))?.state==="unknown")$("resource-file-status").textContent+=" 已重新读取材料列表；请手动核对，读取不会确认原保存或重发。";});
$("resource-save-reset").onclick=()=>{const key=resourceSaveKey();if(!["unknown","accepted"].includes(resourceSaveRequests.get(key)?.state))return;resourceSaveRequests.delete(key);clearResourceMaterial();$("resource-file-status").textContent="已结束本页原意图核对；没有新增保存、删除材料或重新发送。新材料仍需重新选择并显式保存。";};
renderResourceMaterial();

// Move the existing save forms into the selected app. Saving never executes it.
function naturalPreparationCurrent(p) {
  if(p?.firstCreation)return naturalFirstGuideCurrent(p.firstCreation)&&p.firstCreation.stage==="inputs"&&naturalUsePreparation===p;
  return !!p && naturalUsePreparation===p && p.identity===token && p.connection===identityConnectionGeneration && p.project===$("project-select").value && p.workspace===workspaceSelectionGeneration && engineering===p.view && engineeringCurrent(p.view) && p.appGeneration===appSelectionGeneration && (p.returning ? [p.selection,p.returnSelection].includes(p.view.instanceGeneration) : (p.view.instance===p.instance && p.selection===p.view.instanceGeneration));
}
function naturalPreparationMaterialError(body) {
  const text=body.content,lines=text.split(/\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/);
  if(lines.at(-1)==="")lines.pop();
  return !['txt','md'].includes(body.format)||!text.trim()||new TextEncoder().encode(text).length>2048||lines.length>40||/\p{C}/u.test(text.replace(/[\n\r\t]/g,"")) ? "本应用仅支持非空白 UTF-8 TXT/MD，最多2048字节、40行；不支持控制或格式字符（含 BOM，换行/制表符除外）。尚未保存。" : null;
}
function naturalPreparationControls(form,disabled) {for(const node of form.querySelectorAll("input,textarea,select,button"))node.disabled=disabled;}
function clearNaturalUsePreparation(preserveGoal=false) {
  const p=naturalUsePreparation;if(!p)return;naturalUsePreparation=null;
  for(const item of p.forms){item.anchor.replaceWith(item.form);for(const [node,hidden] of item.hidden)node.hidden=hidden;for(const [node,disabled] of item.controls)node.disabled=disabled;}
  $("resource-file").accept=p.accept;
  for(const [option,disabled] of p.formats)option.disabled=disabled;
  $("goal-card-resources").disabled=false;
  p.panel.remove();$("internal-panel").hidden=p.internalHidden;$("app-preview-form").hidden=p.previewHidden;
  clearResourceMaterial();if(!preserveGoal)clearGoalCard(true);updateGoalCardSave();
}
function naturalPreparationRender(p) {
  if(!naturalPreparationCurrent(p))return;
  const pending=naturalPreparationGoalRequests.get(p.key),blocked=!!pending,pbExtraction=p.firstCreation?.mode==="PB";
  $("natural-prep-material-host").hidden=!["material","material-saved"].includes(p.step)||blocked;
  $("natural-prep-goal-host").hidden=p.step!=="goal"||blocked;
  $("natural-prep-goal-next").hidden=p.step!=="material-saved"||blocked;
  $("natural-prep-return").hidden=p.step!=="ready"||blocked;
  $("natural-prep-return").disabled=!!p.returning;
  $("natural-prep-goal-read").hidden=!(pending&&pending.state!=="saving");
  $("natural-prep-goal-reset").hidden=$("natural-prep-goal-read").hidden;
  naturalPreparationControls($("resource-form"),p.step!=="material"||blocked);renderResourceMaterial();
  if(p.step!=="material")naturalPreparationControls($("resource-form"),true);
  $("natural-prep-status").textContent=pending ? pending.state==="saving" ? "正在保存本次 Goal；不提交运行。" : `原 Goal 保存${pending.id?`已接受：${pending.id}`:"回执 UNKNOWN"}。禁止重发；仅可读取原回执或列表核对，不能凭名称或内容认领。` : p.step==="ready" ? `材料 ${p.material.id} 与 Goal ${p.goal.id} 已保存并绑定。${pbExtraction?"尚未提取应用；返回此成功成果后，另行审阅和确认提取、版本与实例。":p.firstCreation?"尚未生成应用；继续到生成后仍需分别确认候选、版本和实例。":"尚未运行；返回原实例后仍需预览与明确确认。"}` : p.step==="material-saved" ? "材料已保存；下一步填写只绑定此材料的新 Goal。尚未运行。" : pbExtraction ? "准备材料 → 保存并绑定 Goal → 返回此成功成果 → 审阅确认提取；每一步均需明确点击。" : "准备材料 → 保存并绑定 Goal → 返回原实例 → 预览确认运行；每一步均需明确点击。";
}
function beginNaturalUsePreparation(s,isCurrent) {
  if(!isCurrent()||s.busy||s.view.busy||pbUseUnknown(s.instance.id)||engineeringPending.has(s.instance.id)||goalCardSaving||resourceFileReader||resourceSaveRequests.has(resourceSaveKey()))return;
  s.edit++;s.review=null;$("pb-use-ack").checked=false;$("pb-use-proof").textContent="";s.buttons();
  beginNaturalInputPreparation({view:s.view,instance:s.instance,selection:s.view.instanceGeneration,family:naturalUseFamily(s.view.draft)});
}
function beginNaturalInputPreparation(origin) {
  clearNaturalUsePreparation();
  clearResourceMaterial();clearGoalCard(true);
  const panel=document.createElement("section");panel.id="natural-use-preparation";
  panel.innerHTML='<h3>准备本次新材料与 Goal</h3><p>仅非空白 UTF-8 TXT/MD，最多2048字节、40行；不支持控制/格式字符和 BOM（换行、制表符除外）。选择或编辑只在本页准备，点击保存才写入并沿用项目24小时授权。Goal 只绑定这一份新材料；保存不会运行或增加模型额度。</p><p id="natural-prep-status" role="status"></p><div id="natural-prep-material-host"></div><button id="natural-prep-goal-next" type="button" hidden>填写并绑定 Goal</button><div id="natural-prep-goal-host" hidden></div><button id="natural-prep-return" type="button" hidden>返回原应用与实例，预览确认运行</button><button id="natural-prep-goal-read" type="button" hidden>读取原 Goal 回执或列表（只读）</button><button id="natural-prep-goal-reset" type="button" hidden>我已核对，结束本页 Goal 保存意图</button><button id="natural-prep-cancel" type="button">结束准备，保留已保存材料与 Goal</button>';
  $("apps").append(panel);
  const p={...origin,identity:token,connection:identityConnectionGeneration,project:$("project-select").value,workspace:workspaceSelectionGeneration,appGeneration:appSelectionGeneration,step:"material",key:resourceSaveKey(),forms:[],formats:[...$("format").options].map(o=>[o,o.disabled]),accept:$("resource-file").accept,internalHidden:$("internal-panel").hidden,previewHidden:$("app-preview-form").hidden,panel};naturalUsePreparation=p;
  for(const [id,host] of [["resource-form","natural-prep-material-host"],["goal-card-form","natural-prep-goal-host"]]){
    const form=$(id),anchor=document.createComment("saved form location"),hidden=[...form.children].map(node=>[node,node.hidden]);form.before(anchor);$(host).append(form);p.forms.push({form,anchor,hidden,controls:[...form.querySelectorAll("input,textarea,select,button")].map(node=>[node,node.disabled])});
    if(id==="resource-form")for(const child of form.children)if(child.tagName==="P"&&!child.id)child.hidden=true;
    if(id==="goal-card-form")for(const child of form.children)if(!['LABEL'].includes(child.tagName)&&!['goal-card-save','goal-card-status'].includes(child.id))child.hidden=true;
  }
  $("resource-file").accept=".txt,.md,text/plain,text/markdown";$("format").value="txt";
  for(const option of $("format").options)option.disabled=!['txt','md'].includes(option.value);
  $("internal-panel").hidden=true;$("app-preview-form").hidden=true;
  $("natural-prep-cancel").onclick=()=>p.firstCreation?clearNaturalFirstGuide():clearNaturalUsePreparation();
  $("natural-prep-goal-next").onclick=()=>{
    if(!naturalPreparationCurrent(p)||p.step!=="material-saved")return;
    p.step="goal";clearGoalCard(true);
    $("goal-card-resources").replaceChildren(new Option(`${p.material.body.name} · ${p.material.id}`,p.material.id,true,true));$("goal-card-resources").disabled=true;
    naturalPreparationRender(p);
  };
  $("natural-prep-goal-read").onclick=safe(async()=>{
    if(!naturalPreparationCurrent(p))return;const pending=naturalPreparationGoalRequests.get(p.key);if(!pending||pending.state==="saving")return;
    if(pending.id&&pending===p.goalRequest)await readNaturalPreparationGoal(p,pending);
    else {const cards=await api(`/api/projects/${p.project}/goal-cards`);if(naturalPreparationCurrent(p))$("natural-prep-status").textContent=`只读核对列表：${cards.items.map(c=>`${c.title} · ${c.id}`).join("；")}。未重发或自动认领。`;}
  });
  $("natural-prep-goal-reset").onclick=()=>{const pending=naturalPreparationGoalRequests.get(p.key);if(!naturalPreparationCurrent(p)||!pending||pending.state==="saving")return;naturalPreparationGoalRequests.delete(p.key);if(p.firstCreation)clearNaturalFirstGuide();else clearNaturalUsePreparation();};
  if(p.firstCreation)$("natural-prep-return").textContent="继续到自然应用生成（不运行）";
  $("natural-prep-return").onclick=safe(()=>p.firstCreation?continueNaturalFirstGoal(p):returnNaturalPreparation(p));naturalPreparationRender(p);panel.scrollIntoView?.({block:"start"});
}
async function readNaturalPreparationGoal(p,pending) {
  const card=await api(`/api/goal-cards/${pending.id}`);if(!naturalPreparationCurrent(p)||naturalPreparationGoalRequests.get(p.key)!==pending)return;
  if(card.id!==pending.id||card.project_id!==p.project||!Number.isInteger(card.version)||card.version!==1||!/^[a-f0-9]{64}$/.test(card.fingerprint)||goalRunCanonical(card.content)!==goalRunCanonical(pending.body)||card.content.resource_refs.length!==1||card.content.resource_refs[0]!==p.material.id)throw Error("VERSION_CONFLICT");
  p.goal={id:card.id,version:card.version,fingerprint:card.fingerprint};p.savedCard=card;p.step="ready";naturalPreparationGoalRequests.delete(p.key);naturalPreparationRender(p);
}
async function saveNaturalPreparationGoal(p,body) {
  if(!naturalPreparationCurrent(p)||p.step!=="goal"||naturalPreparationGoalRequests.has(p.key))return;
  if(body.resource_refs.length!==1||body.resource_refs[0]!==p.material.id)throw Error("本次 Goal 必须且只能绑定刚保存的材料");
  const pending={body:structuredClone(body),state:"saving"};naturalPreparationGoalRequests.set(p.key,pending);p.goalRequest=pending;goalCardSaving=true;updateGoalCardSave();naturalPreparationRender(p);
  try {
    const result=await saveGoalCardBody(p.project,null,pending.body);
    if(!/^goal_[a-f0-9]{32}$/.test(result?.id))throw Error("保存回执缺失");
    pending.id=result.id;pending.state="accepted";
    if(naturalPreparationCurrent(p))await readNaturalPreparationGoal(p,pending);
  } catch(error) {
    if(!pending.id&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus))naturalPreparationGoalRequests.delete(p.key);
    else pending.state=pending.id?"accepted":"unknown";
    if(naturalPreparationCurrent(p)){$("goal-card-status").textContent=error.detail||error.message;naturalPreparationRender(p);}
  } finally {goalCardSaving=false;updateGoalCardSave();if(naturalPreparationCurrent(p))naturalPreparationRender(p);}
}
async function returnNaturalPreparation(p) {
  if(!naturalPreparationCurrent(p)||p.step!=="ready"||p.returning||pbUseUnknown(p.instance.id)||engineeringPending.has(p.instance.id))return;
  p.returnSelection=p.view.instanceGeneration+1;p.returning=true;naturalPreparationRender(p);
  try {
    const app=await api(`/api/apps/${p.view.app}`);if(!naturalPreparationCurrent(p))return;
    if(app.fingerprint!==p.view.draft.fingerprint||naturalUseFamily(app)!==p.family)throw Error("VERSION_CONFLICT");
    const card=await api(`/api/goal-cards/${p.goal.id}`);if(!naturalPreparationCurrent(p))return;
    if(card.project_id!==p.project||card.id!==p.goal.id||card.version!==p.goal.version||card.fingerprint!==p.goal.fingerprint||goalRunCanonical(card.content.resource_refs)!==goalRunCanonical([p.material.id]))throw Error("VERSION_CONFLICT");
    const selection=p.view.instanceGeneration+1;
    await showInternalInstance(p.instance.id,p.view);if(!naturalPreparationCurrent(p)||p.view.instanceGeneration!==selection)return;
    const instance=p.view.instance;
    if(!instance||instance.id!==p.instance.id||instance.release_id!==p.instance.release_id||instance.release_fingerprint!==p.instance.release_fingerprint||instance.revision!==p.instance.revision||instance.data_version!==p.instance.data_version)throw Error("VERSION_CONFLICT");
    const use=pbUseView;
    if(!use||use.view!==p.view||use.instance!==instance||!$("pb-use-material").querySelector(`option[value="${p.material.id}"]`)||!$("pb-use-goal").querySelector(`option[value="${p.goal.id}"]`))throw Error("VERSION_CONFLICT");
    const material=p.material.id,goal=p.goal.id;clearNaturalUsePreparation();
    $("pb-use-material").value=material;$("pb-use-goal").value=goal;$("pb-use-material").dispatchEvent(new Event("change"));$("pb-use-goal").dispatchEvent(new Event("change"));
    $("pb-use-status").textContent="已返回原应用与精确实例，并选中刚保存的材料和 Goal。尚未运行；请点击预览、核对后明确确认。";$("pb-use-panel").scrollIntoView?.({block:"start"});
  } catch(error) {if(naturalPreparationCurrent(p))$("natural-prep-status").textContent=`返回核对失败：${error.detail||error.message}。已保存内容保留，请重新打开原应用和实例。`;}
  finally {if(naturalUsePreparation===p){p.returning=false;$("natural-prep-return").disabled=false;}}
}

function naturalFirstGuideCurrent(g) {
  return !!g&&naturalFirstGuide===g&&g.identity===token&&g.connection===identityConnectionGeneration&&g.project===$("project-select").value&&g.workspace===workspaceSelectionGeneration&&g.appGeneration===appSelectionGeneration;
}
function clearNaturalFirstGuide() {
  const g=naturalFirstGuide;if(!g)return;naturalFirstGuide=null;
  if(naturalUsePreparation?.firstCreation===g)clearNaturalUsePreparation();
  if(g.mode==="PB"&&naturalTaskExtraction===g.extraction)clearNaturalTaskExtraction();
  $("natural-first-guide").hidden=true;$("natural-first-status").textContent="";$("natural-first-directory").hidden=true;
  // Invalidate any pending generation/confirmation handoff; accepted tasks remain saved.
  clearGoalCard(true);if(g.view&&engineering===g.view)clearInternal();if(g.mode==="PB"&&g.opening)clearApp();renderNaturalFirstGuide();
}
function renderNaturalFirstGuide() {
  const g=naturalFirstGuide;$("natural-first-start").disabled=!!g||!$("project-select").value;
  $("natural-first-guide").hidden=!g;if(!g)return;
  if(!naturalFirstGuideCurrent(g))return;
  $("natural-first-title").textContent=g.mode==="PB"?"从成功成果保存可复用的 P-B 应用":"从 Goal 创建自然应用";
  const steps=g.mode==="PB"?["核对这份成功成果的 Run、版本与来源","准备或选择自己的新材料与 Goal","审阅来源、编辑图及精确绑定，另行确认提取","核查内部快照，另行确认保存版本","明确创建独立实例，返回目录","从目录选择新材料，预览并确认受限运行"]:["准备并保存新 TXT/MD 材料","保存只绑定本次材料的 Goal","读取可用性后明确生成，查看精确候选","分别确认候选与本项目 JSON 保存授权","核查内部快照，另行确认保存版本","明确创建独立实例，返回应用目录"];
  $("natural-first-guide").querySelector("ol").replaceChildren(...steps.map(text=>{const li=document.createElement("li");li.textContent=text;return li;}));
  let message;
  if(g.stage==="inputs")message=g.mode==="PB"?`来源 Run ${g.sourceRun} · 成果 v${g.sourceVersion} 保留。分别保存自己的新材料和 Goal，再返回此成果的精确提取审阅；保存不会提取或运行。`:"第1–2步：准备新材料，分别点击材料保存、填写 Goal 和保存 Goal；本次尚未创建应用、实例或生成任务。";
  else if(g.stage==="extract")message=`来源 Run ${g.sourceRun} · Release ${g.sourceRelease} · 成果 v${g.sourceVersion}。${g.extraction.saved?"P-B 草案已核对；点击打开后另行保存内部版本和实例。":naturalTaskRequests.has(g.extraction.scope)?"保存回执未确认；仅按原 key 读取，不能再次提交。":"准备或选择自己的新材料与 Goal，再预览来源与编辑图，明确确认提取。"} 不改变原应用、版本或成果，不自动运行或发布。`;
  else if(g.stage==="generate"){
    const entry=goalApplications.get(goalApplicationKey());
    message=`第3–4步：Goal ${g.card.id} · v${g.card.version}。${g.gateMessage||"先点击生成读取当前条件；自然生成没有 LIVE 批准路径，仅支持既有离线测试适配。"} ${entry?.message||"尚未创建生成任务；核对候选后分别勾选材料读取与项目 JSON 保存授权。"}`;
  }else{
    const view=g.view;
    message=g.instance ? `第6步完成：应用 ${g.app} · Release ${g.release.id} · 实例 ${g.instance} 已保存。还没有运行此实例；返回目录后可为第二份材料单独准备 Goal、预览并确认运行。` : g.release ? `第6步：已保存精确内部版本 ${g.release.id}。点击该版本下的“创建独立实例”；不会自动创建或执行。` : view?.approval ? "第5步：核查下方精确内部快照与检查证据，另行勾选并确认保存内部 Release。" : "第5步：自然应用候选已保存。点击“核查并准备内部快照”，再明确确认保存内部版本；尚无实例。";
  }
  $("natural-first-status").textContent=message;
  $("natural-first-directory").hidden=!g.instance;
  $("natural-first-directory").disabled=!!g.busy;
}
function beginNaturalFirstGuide() {
  if(naturalFirstGuide||!$("project-select").value||goalCardSaving||resourceFileReader||resourceSaveRequests.has(resourceSaveKey()))return;
  clearApp();clearGoalCard();
  const g={identity:token,connection:identityConnectionGeneration,project:$("project-select").value,workspace:workspaceSelectionGeneration,appGeneration:appSelectionGeneration,stage:"inputs"};naturalFirstGuide=g;
  beginNaturalInputPreparation({firstCreation:g,family:"NATURAL_PA"});renderNaturalFirstGuide();
}
function continueNaturalFirstGoal(p) {
  if(!naturalPreparationCurrent(p)||p.step!=="ready")return;
  const g=p.firstCreation,card=p.savedCard,snapshot=card.history?.find(v=>v.version===card.version&&v.fingerprint===card.fingerprint)?.snapshot;
  if(!snapshot||goalRunCanonical(snapshot.content)!==goalRunCanonical(card.content))throw Error("VERSION_CONFLICT");
  if(g.mode==="PB")return returnNaturalPBTarget(p);
  clearNaturalUsePreparation(true);
  activeGoalCard={id:card.id,version:card.version,fingerprint:card.fingerprint,project_id:card.project_id,snapshot};
  g.stage="generate";g.card={...activeGoalCard};g.selection=goalSelectionGeneration;
  $("goal-application-family").value="natural_spec";$("goal-application-family").onchange();
  $("goal-application-name").value=Array.from(card.content.title).slice(0,100).join("");
  renderGoalRun();renderGoalApplicationControls();selectWorkspace("projects",g);renderNaturalFirstGuide();
  $("goal-application-panel").scrollIntoView?.({block:"start"});$("goal-application-name").focus();
}
function naturalFirstGuideForEntry(entry) {
  const g=naturalFirstGuide;
  return naturalFirstGuideCurrent(g)&&g.stage==="generate"&&g.selection===goalSelectionGeneration&&g.card.id===entry.card&&g.card.fingerprint===entry.body.expected_fingerprint&&entry.body.family==="natural_spec"?g:null;
}
function naturalFirstCandidateOpened(g,entry,saved) {
  if(!g||!naturalFirstGuideCurrent(g)||!goalApplicationCurrent(entry)||saved.id!==entry.expectedAppId||!engineeringCurrent(engineering)||engineering.app!==saved.id)return;
  g.stage="internal";g.app=saved.id;g.view=engineering;renderNaturalFirstGuide();
}
function naturalFirstReleaseSaved(view,saved) {
  const g=naturalFirstGuide;if(!naturalFirstGuideCurrent(g)||g.stage!=="internal"||g.view!==view)return;
  g.release={id:saved.id,fingerprint:saved.fingerprint};renderNaturalFirstGuide();
}
function naturalFirstInstanceCreated(view,created) {
  const g=naturalFirstGuide;if(!naturalFirstGuideCurrent(g)||g.stage!=="internal"||g.view!==view||!g.release||view.instance?.id!==created.id||view.instance.release_id!==g.release.id||view.instance.release_fingerprint!==g.release.fingerprint)return;
  g.instance=created.id;renderNaturalFirstGuide();
}
$("natural-first-start").onclick=beginNaturalFirstGuide;
$("natural-first-cancel").onclick=()=>clearNaturalFirstGuide();
$("natural-first-directory").onclick=safe(async()=>{
  const g=naturalFirstGuide;if(!naturalFirstGuideCurrent(g)||!g.instance||g.busy)return;
  g.busy=true;renderNaturalFirstGuide();
  try{await refreshApps();if(!naturalFirstGuideCurrent(g))return;clearNaturalFirstGuide();clearApp();selectWorkspace("apps");$("application-use").scrollIntoView?.({block:"start"});}
  finally{g.busy=false;if(naturalFirstGuideCurrent(g))renderNaturalFirstGuide();}
});
renderNaturalFirstGuide();

function beginNaturalPBGuide(s) {
  if(!naturalTaskCurrent(s)||!s.source)return;
  if(naturalFirstGuide?.mode==="PB"&&naturalFirstGuide.extraction===s)return;
  if(naturalFirstGuide?.view===s.view)naturalFirstGuide.view=null;
  clearNaturalFirstGuide();
  const proof=s.source.source_proof;
  naturalFirstGuide={mode:"PB",stage:"extract",extraction:s,sourceRun:s.rid,sourceVersion:proof.result_version,sourceRelease:proof.release_id,identity:token,connection:identityConnectionGeneration,project:s.view.project,workspace:workspaceSelectionGeneration,appGeneration:appSelectionGeneration};
  renderNaturalFirstGuide();
}
function beginNaturalPBTarget(s) {
  if(!naturalTaskCurrent(s)||!s.source||s.busy||naturalTaskRequests.has(s.scope)||goalCardSaving||resourceFileReader||resourceSaveRequests.has(resourceSaveKey()))return;
  beginNaturalPBGuide(s);const g=naturalFirstGuide;if(!naturalFirstGuideCurrent(g)||g.extraction!==s)return;
  naturalTaskEdited(s);g.stage="inputs";beginNaturalInputPreparation({firstCreation:g,family:"NATURAL_PB"});
  $("natural-prep-return").textContent="返回此成功成果的 P-B 提取审阅";renderNaturalFirstGuide();
}
async function returnNaturalPBTarget(p) {
  const g=p.firstCreation,s=g.extraction;if(!naturalPreparationCurrent(p)||!naturalTaskCurrent(s)||p.returning)return;
  p.returning=true;naturalPreparationRender(p);
  const current=()=>naturalPreparationCurrent(p)&&naturalTaskCurrent(s);
  try{
    const source=await api(`/api/projects/${s.view.project}/natural-spec-task-runs/${s.rid}/extraction-options`);if(!current())return;
    const proofHash=await paHash(source.source_proof);if(!current())return;
    if(source.source_run_id!==s.rid||source.source_proof_fingerprint!==s.source.source_proof_fingerprint||source.recipe_fingerprint!==s.source.recipe_fingerprint||proofHash!==source.source_proof_fingerprint||goalRunCanonical(source.source_proof)!==goalRunCanonical(s.source.source_proof))throw Error("VERSION_CONFLICT");
    const card=await api(`/api/goal-cards/${p.goal.id}`);if(!current())return;
    if(card.id!==p.goal.id||card.project_id!==p.project||card.version!==p.goal.version||card.fingerprint!==p.goal.fingerprint||goalRunCanonical(card.content.resource_refs)!==goalRunCanonical([p.material.id]))throw Error("VERSION_CONFLICT");
    const material=p.material.id,goal=p.goal.id;clearNaturalUsePreparation();g.stage="extract";
    s.target.add(new Option(`${card.content.title} · v${card.version} · ${goal}`,goal));s.target.value=goal;naturalTaskEdited(s);
    s.status.textContent=`已返回同一来源 Run ${s.rid}，选中刚保存的 Goal ${goal} 与材料 ${material}。尚未提取或运行；请另行预览和明确确认。`;renderNaturalFirstGuide();s.panel.scrollIntoView?.({block:"start"});
  }catch(error){if(current())$("natural-prep-status").textContent=`来源或新 Goal 核对失败：${error.detail||error.message}。已保存内容保留；未提取或运行。`;}
  finally{if(naturalUsePreparation===p){p.returning=false;$("natural-prep-return").disabled=false;}}
}
