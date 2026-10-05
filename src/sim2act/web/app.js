"use strict";
let token = "", activeRun = null, refs = [];
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
  $("raw-result").textContent = JSON.stringify(r, null, 2);
  $("events").textContent = JSON.stringify(r.events, null, 2);
  const commands = ["QUEUED","RUNNING"].includes(r.status) ? ["pause","cancel"] : ["PAUSED","WAITING_RESOURCE"].includes(r.status) ? ["resume","cancel"] : [];
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
$("project-select").onchange = safe(async () => {activeRun=null;await refresh();});
document.querySelectorAll("[data-tab]").forEach(b => b.onclick = () => ["projects","apps","resources"].forEach(id => $(id).hidden=id!==b.dataset.tab));
setInterval(async () => {try {const h=await api("/health");$("health").textContent=`${h.mode} · API ${h.api} · worker ${h.worker}`;if(token){await refresh();if(activeRun)await showRun(activeRun);}}catch(e){$("health").textContent="后台不可用";}},2500);
