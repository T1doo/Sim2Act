"use strict";
let token = "", activeRun = null, refs = [];
let reconcileVersion = null, unresolvedAttempts = [];
let activeApp = null, activeGoalCard = null;
let goalSelectionGeneration = 0, goalCardLoading = false, goalCardSaving = false;
let candidateSelectionGeneration = 0, candidateBusy = false, candidatePanelReady = false;
let appSelectionGeneration = 0, activeAppProject = null;
const candidateRequestKeys = new Map();
const extractionRequestKeys = new Map();
let extractionSource = null, extractionBusy = false;
let appCreateBusy = false;
const appPreviewRequests = new Set();
const $ = (id) => document.getElementById(id);
async function api(path, method = "GET", body) {
  const response = await fetch(path, {method, headers: {Authorization: `Bearer ${token}`, "Content-Type": "application/json"}, ...(body ? {body: JSON.stringify(body)} : {})});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error?.code || data.detail?.[0]?.msg || "请求失败");
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
  const materials = await api(`/api/projects/${pid}/resources`);
  if (pid !== $("project-select").value) return;
  refs = materials.map(x => x.id);
  const selectedGoals=Array.from($("goal-card-resources").selectedOptions).map(o=>o.value);
  $("goal-card-resources").replaceChildren(...materials.map(m=>{const o=new Option(m.name,m.id);o.selected=selectedGoals.includes(m.id);return o;}));
  await refreshGoalCards(pid);
  if (pid !== $("project-select").value) return;
  $("materials").replaceChildren(...materials.map(x => row(`${x.name} · ${x.format} · ${x.hash.slice(0, 12)}`, async () => {const data=await api(`/api/resources/${x.id}`);$("resource-preview").hidden=false;$("resource-preview").textContent=data.content;}, "查看")));
  const oldResource = $("app-resource").value;
  $("app-resource").replaceChildren(...materials.filter(x => x.format === "csv").map(x => {const o=document.createElement("option");o.value=x.id;o.textContent=x.name;return o;}));
  if (materials.some(x => x.id === oldResource)) $("app-resource").value = oldResource;
  await refreshApps();
  if (pid !== $("project-select").value) return;
  const runs = await api(`/api/projects/${pid}/runs`);
  if (pid !== $("project-select").value) return;
  $("runs").replaceChildren(...runs.map(x => row(`${x.status} · ${x.id.slice(0, 16)}`, () => showRun(x.id), "查看任务")));
  const grants = await api(`/api/projects/${pid}/grants`);
  if (pid !== $("project-select").value) return;
  $("grants").replaceChildren(...grants.map(g => row(`${g.tool_ref} · ${g.principal_id.startsWith("runtime_") ? "项目运行身份" : g.principal_id.startsWith("appruntime_") ? "应用预览身份" : "当前使用者"} · ${g.revoked ? "已撤回" : "有效至 " + new Date(g.expires_at * 1000).toLocaleString()}`, g.revoked ? null : async () => {await api(`/api/grants/${g.id}/revoke`, "POST", {command:"revoke",version:g.revision});activeRun=null;clearApp();$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";$("resource-preview").textContent="";await refresh();}, "撤回")));
}
async function showRun(id) {
  activeRun = id;
  const r = await api(`/api/runs/${id}`);
  reconcileVersion = r.version;
  unresolvedAttempts = ["WAITING_RESOURCE","RECONCILING"].includes(r.status) ? await api(`/api/runs/${id}/unresolved-attempts`) : [];
  $("reconcile-panel").hidden = unresolvedAttempts.length === 0;
  const selectedAttempt = $("reconcile-attempt").value;
  $("reconcile-attempt").replaceChildren(...unresolvedAttempts.map(a => {const o=document.createElement("option");o.value=a.attempt_id;o.textContent=`${a.mode || "历史请求"} · ${a.attempt_id.slice(0,16)} · ${a.request_fingerprint ? a.request_fingerprint.slice(0,12) : "历史请求未绑定，只能结束"}`;o.title=a.request_fingerprint || "没有可恢复绑定";return o;}));
  if (unresolvedAttempts.some(a => a.attempt_id === selectedAttempt)) $("reconcile-attempt").value = selectedAttempt;
  const labels = {QUEUED:"等待后台执行",RUNNING:"正在执行",PARTIAL:"部分完成",FAILED:"执行失败",WAITING_RESOURCE:"等待资源或授权",PAUSED:"已暂停",CANCELLED:"已取消"};
  $("result").replaceChildren(row(`${labels[r.status] || r.status}（${r.status}）`));
  if (r.result) {
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
  $("commands").replaceChildren(...commands.map(command => {const b = document.createElement("button"); b.textContent = {pause:"暂停",cancel:"取消",resume:"继续"}[command]; b.onclick = safe(async () => {await api(`/api/runs/${id}/commands`, "POST", {command,version:r.version}); await showRun(id);}); return b;}));
}
async function loadProjects() {
  const ps = await api("/api/projects"); const old = $("project-select").value;
  $("project-select").replaceChildren(...ps.map(p => {const o = document.createElement("option"); o.value=p.id; o.textContent=p.name; return o;}));
  if (ps.some(p => p.id === old)) $("project-select").value = old;
  await refresh();
}
$("connect").onclick = safe(async () => {token=$("token").value; await loadProjects(); $("token").value=""; $("login").hidden=true; $("capabilities").textContent=JSON.stringify(await api("/api/capabilities"),null,2);});
$("project-form").onsubmit = safe(async () => {await api("/api/projects","POST",{name:$("project-name").value}); await loadProjects();});
$("resource-form").onsubmit = safe(async () => {const pid=$("project-select").value;if(!pid)throw new Error("先选择项目");await api(`/api/projects/${pid}/resources`,"POST",{name:$("resource-name").value,format:$("format").value,content:$("content").value}); await refresh();});
$("run-form").onsubmit = safe(async () => {const pid=$("project-select").value;if(!pid)throw new Error("先选择项目");const r=await api(`/api/projects/${pid}/runs`,"POST",{goal:$("goal").value,resource_refs:refs,request_key:crypto.randomUUID()});await refresh();await showRun(r.run_id);});
$("reconcile-form").onsubmit = safe(async () => {const a=unresolvedAttempts.find(x=>x.attempt_id === $("reconcile-attempt").value);if(!a || !activeRun)throw new Error("请重新打开待核对任务");const decision=$("reconcile-decision").value;await api(`/api/runs/${activeRun}/reconcile`,"POST",{attempt_id:a.attempt_id,version:reconcileVersion,decision,expected_fingerprint:a.request_fingerprint,evidence:$("reconcile-evidence").value,acknowledge_unknown_cost:$("reconcile-ack").checked,response_json:decision === "record_response" ? $("reconcile-response").value : null});$("reconcile-response").value="";$("reconcile-evidence").value="";$("reconcile-ack").checked=false;await showRun(activeRun);});
$("project-select").onchange = safe(async () => {activeRun=null;clearApp();clearGoalCard();unresolvedAttempts=[];$("reconcile-panel").hidden=true;$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";$("resource-preview").textContent="";await refresh();});
document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => ["projects","apps","resources"].forEach(id => $(id).hidden=id!==b.dataset.tab));
document.querySelector("#projects .grid > section:last-child").append($("reconcile-panel"));
setInterval(async () => {try {const h=await api("/health");$("health").textContent=`${h.mode} · API ${h.api} · worker ${h.worker}`;if(token){await refresh();if(activeRun)await showRun(activeRun);}}catch(e){$("health").textContent="后台不可用";}},2500);

function clearApp() {
  $("app-create-status").textContent="";$("app-create-status").dataset.state="";
  extractionSource=null;$("extraction-form").hidden=true;$("extraction-status").textContent="";
  appSelectionGeneration++;activeAppProject=null;
  $("app-origin").textContent="";$("app-back-goal").hidden=true;$("app-frozen-goal").hidden=true;$("app-frozen-goal-text").textContent="";
  activeApp=null;$("app-title").textContent="选择草案";$("app-preview-form").hidden=true;
  $("app-output").replaceChildren();$("app-output").dataset.state="";$("app-history").replaceChildren();$("app-manifest").textContent="";
}
async function refreshApps() {
  const list=await api("/api/apps");
  const items=list.items.filter(x=>x.project_id === $("project-select").value);
  $("app-list").replaceChildren(...items.map(x=>row(`${x.name} · 未发布草案`,()=>showApp(x.id),"打开预览")));
  if(!items.length)$("app-list").textContent="先保存 CSV 材料，再创建一个草案。";
}
function previewText(r) {
  if(r.status === "FAILED")return `预览失败（FAILED）：${r.error?.message || r.error?.code} · 已保留这次历史`;
  return `预览成功（SUCCEEDED） · ${r.output.column} 合计 ${r.output.sum}，共 ${r.output.count} 条 · 0 模型请求 · 仅预览`;
}
function showPreviewResult(r,history=false){
  $("app-output").dataset.state=r.status === "FAILED" ? "error" : "success";
  $("app-output").replaceChildren(row(`${history ? "历史记录 · " : ""}${previewText(r)} · ${r.id.slice(0,16)}`));
}
async function showApp(id,pid=$("project-select").value) {
  if(pid !== $("project-select").value)return false;
  clearApp();const generation=appSelectionGeneration;
  const a=await api(`/api/apps/${id}`);
  if(generation !== appSelectionGeneration || pid !== $("project-select").value)return false;
  if(a.project_id !== pid)throw Error("候选不属于当前项目，请重新选择");
  activeApp=id;activeAppProject=pid;
  const origin=a.candidate.generation;
  const extraction=a.candidate.extraction;
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
  $("app-preview-form").hidden=false;
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
  if(!extraction && succeeded.length){
    extractionSource={id,project_id:pid,fingerprint:a.fingerprint,generation};
    $("extraction-preview").replaceChildren(...succeeded.map(r=>new Option(`${r.input.column} · ${r.output.sum} · ${r.id}`,r.id)));
    const sourceRid=a.candidate.manifest.data_bindings[0].resource_ref;
    $("extraction-resource").replaceChildren(...Array.from($("app-resource").options).filter(o=>o.value !== sourceRid).map(o=>new Option(o.textContent,o.value)));
    $("extraction-form").hidden=false;$("extraction-create").disabled=extractionBusy || !$("extraction-resource").value;
    $("extraction-status").textContent=$("extraction-resource").value ? "只接受成功回执；提取时重新核查来源与独立数值结果。" : "请先在同项目保存内容不同的新CSV，再打开来源草案。";
  }
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
  if(appCreateBusy)return;
  const pid=$("project-select").value,rid=$("app-resource").value;
  if(!pid || !rid)throw new Error("先为当前项目保存并授权 CSV 材料");
  const generation=appSelectionGeneration,current=()=>generation === appSelectionGeneration && pid === $("project-select").value;
  appCreateBusy=true;$("app-create-submit").disabled=true;
  $("app-create-status").dataset.state="loading";$("app-create-status").textContent="正在保存草案；离开选择不会撤销已接受的创建。";
  try{
    const a=await api(`/api/projects/${pid}/apps/csv-preview`,"POST",{name:$("app-name").value,goal:$("app-goal").value,resource_id:rid});
    if(!current())return;
    await refreshApps();if(!current())return;
    if(await showApp(a.id,pid) && activeApp === a.id){$("app-create-status").dataset.state="success";$("app-create-status").textContent="草案已保存，请选择数值列运行新预览。";}
  }catch(e){if(current()){$("app-create-status").dataset.state="error";$("app-create-status").textContent=`创建未打开：${e.message}；可刷新草案列表核对后重试。`;}}
  finally{appCreateBusy=false;$("app-create-submit").disabled=false;}
});
$("app-preview-form").onsubmit=safe(async()=>{
  if(!activeApp || activeAppProject !== $("project-select").value)throw new Error("先打开当前项目的草案");
  const id=activeApp,pid=activeAppProject,generation=appSelectionGeneration;
  if(appPreviewRequests.has(id))return;
  const current=()=>activeApp === id && generation === appSelectionGeneration && pid === $("project-select").value;
  appPreviewRequests.add(id);$("app-preview-submit").disabled=true;
  $("app-output").dataset.state="loading";$("app-output").textContent="正在读取授权材料并运行新预览…";
  try {
    const r=await api(`/api/apps/${id}/previews`,"POST",{input:{column:$("app-column").value},request_key:crypto.randomUUID()});
    if(current() && await showApp(id,pid)){if(activeApp===id)showPreviewResult(r);}
  }catch(e){if(current()){$("app-output").dataset.state="error";$("app-output").textContent=`预览未打开：${e.message}；可重新打开草案核对历史。`;}}
  finally{appPreviewRequests.delete(id);$("app-preview-submit").disabled=appPreviewRequests.has(activeApp) || !$("app-column").value;}
});


const goalCardFields=["title","goal","known","assumptions","unresolved","constraints","acceptance_checks"];
function updateGoalCardSave() {
  $("goal-card-save").disabled=goalCardLoading || goalCardSaving;
  updateCandidateCreate();
}
function clearGoalCard() {
  goalSelectionGeneration++;candidateSelectionGeneration++;candidatePanelReady=false;
  $("goal-candidate-form").hidden=true;$("goal-candidate-list").replaceChildren();
  $("goal-candidate-status").textContent="先打开已保存目标卡。";
  goalCardLoading=false;updateGoalCardSave();
  activeGoalCard=null;$("goal-card-form").reset();$("goal-card-status").textContent="新建草案";
  $("goal-card-history").replaceChildren();$("goal-card-history-detail").textContent="";
}
async function refreshGoalCards(pid) {
  const cards=await api(`/api/projects/${pid}/goal-cards`);
  if(pid !== $("project-select").value)return;
  $("goal-card-list").replaceChildren(...cards.items.map(c=>row(`${c.title} · 草案 v${c.version}`,()=>showGoalCard(c.id,pid),"打开目标卡")));
  if(!cards.items.length)$("goal-card-list").textContent="尚无目标卡。可先整理任意目标及其检查要求。";
}
async function showGoalCard(id, pid=$("project-select").value) {
  if(pid !== $("project-select").value)return;
  clearGoalCard();
  const generation=goalSelectionGeneration;
  goalCardLoading=true;updateGoalCardSave();$("goal-card-status").textContent="正在读取目标卡";
  const current=()=>generation === goalSelectionGeneration && pid === $("project-select").value;
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
  activeGoalCard={id,version:card.version,project_id:card.project_id};
  goalCardFields.forEach(f=>{$(`goal-card-${f}`).value=Array.isArray(card.content[f]) ? card.content[f].join("\n") : card.content[f];});
  Array.from($("goal-card-resources").options).forEach(o=>o.selected=card.content.resource_refs.includes(o.value));
  $("goal-card-status").textContent=`草案 v${card.version} · 未验收/不可执行 · 保存将建立新版本`;
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
