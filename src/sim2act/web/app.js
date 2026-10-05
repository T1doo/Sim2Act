"use strict";
let token = "", activeRun = null, refs = [];
let reconcileVersion = null, unresolvedAttempts = [];
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
  const materials = await api(`/api/projects/${pid}/resources`); refs = materials.map(x => x.id);
  $("materials").replaceChildren(...materials.map(x => row(`${x.name} · ${x.format} · ${x.hash.slice(0, 12)}`, async () => {const data=await api(`/api/resources/${x.id}`);$("resource-preview").hidden=false;$("resource-preview").textContent=data.content;}, "查看")));
  const runs = await api(`/api/projects/${pid}/runs`);
  $("runs").replaceChildren(...runs.map(x => row(`${x.status} · ${x.id.slice(0, 16)}`, () => showRun(x.id), "查看任务")));
  const grants = await api(`/api/projects/${pid}/grants`);
  $("grants").replaceChildren(...grants.map(g => row(`${g.tool_ref} · ${g.principal_id.startsWith("runtime_") ? "项目运行身份" : "当前使用者"} · ${g.revoked ? "已撤回" : "有效至 " + new Date(g.expires_at * 1000).toLocaleString()}`, g.revoked ? null : async () => {await api(`/api/grants/${g.id}/revoke`, "POST", {command:"revoke",version:g.revision});activeRun=null;$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";$("resource-preview").textContent="";await refresh();}, "撤回")));
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
$("project-select").onchange = safe(async () => {activeRun=null;unresolvedAttempts=[];$("reconcile-panel").hidden=true;$("result").replaceChildren();$("events").textContent="";$("raw-result").textContent="";$("resource-preview").textContent="";await refresh();});
document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => ["projects","apps","resources"].forEach(id => $(id).hidden=id!==b.dataset.tab));
document.querySelector("#projects .grid > section:last-child").append($("reconcile-panel"));
setInterval(async () => {try {const h=await api("/health");$("health").textContent=`${h.mode} · API ${h.api} · worker ${h.worker}`;if(token){await refresh();if(activeRun)await showRun(activeRun);}}catch(e){$("health").textContent="后台不可用";}},2500);
