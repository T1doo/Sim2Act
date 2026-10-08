"use strict";
const csvDagIntents = new Map();
let csvDagContext = null;
const csvDagCurrent = c => c === csvDagContext && deliveryCurrent(c.parent);
const csvDagKey = c => deliveryKey(c.parent);
const csvDagBase = c => `/api/projects/${c.parent.project}/apps/${c.parent.id}/csv-dag`;
function clearCsvDag() {
  csvDagContext = null;
  $("csv-dag-panel").hidden = true;
  $("csv-dag-definition").textContent = "";
  $("csv-dag-result").textContent = "";
  $("csv-dag-status").textContent = "";
  $("csv-dag-confirm").checked = false;
  $("csv-dag-history").replaceChildren();
}
function openCsvDag(parent) {
  clearCsvDag();
  const actions = parent.app.candidate.actions;
  if (actions.length !== 1 || actions[0].executor.ref !== "data.aggregate_csv" || actions[0].executor.kind !== "registered_tool") return;
  const c = {parent, plan: null, job: null, busy: false};
  csvDagContext = c;
  $("csv-dag-panel").hidden = false;
  $("csv-dag-column").replaceChildren(...(parent.app.input_guidance?.columns || []).filter(v => v.numeric).map(v => {
    const o = document.createElement("option"); o.value = v.name; o.textContent = v.name; return o;
  }));
  csvDagButtons(c);
}
function csvDagClearProof(c) {
  c.plan = null; c.job = null;
  $("csv-dag-definition").textContent = ""; $("csv-dag-result").textContent = ""; $("csv-dag-confirm").checked = false;
  $("csv-dag-history").replaceChildren();
}
function csvDagButtons(c = csvDagContext) {
  if (!c || !csvDagCurrent(c)) return;
  const intent = csvDagIntents.get(csvDagKey(c)), locked = c.busy || !!intent;
  $("csv-dag-plan").disabled = locked || !$("csv-dag-column").value;
  $("csv-dag-run").disabled = locked || !c.plan || !$("csv-dag-confirm").checked;
  $("csv-dag-retry").hidden = !intent;
  $("csv-dag-retry").disabled = c.busy;
  $("csv-dag-refresh").disabled = c.busy || (!c.job && !intent?.runId);
  $("csv-dag-history-read").disabled = c.busy || !!intent;
  $("csv-dag-column").disabled = locked;
  $("csv-dag-confirm").disabled = locked || !c.plan;
  for (const command of ["pause", "resume", "cancel"]) {
    const states = command === "pause" ? ["QUEUED", "RUNNING"] : command === "resume" ? ["PAUSED", "WAITING_RESOURCE"] : ["QUEUED", "RUNNING", "PAUSED", "PAUSE_REQUESTED", "WAITING_RESOURCE", "RECONCILING"];
    $("csv-dag-" + command).disabled = locked || !c.job || !states.includes(c.job.status);
  }
}
async function csvDagPlanSeal(p, c) {
  const a = c.parent.app, d = p?.definition;
  if (p?.namespace !== "fixed-csv-dag.v1" || p.project_id !== c.parent.project || p.app_id !== c.parent.id || p.runtime_id !== a.runtime_id || p.candidate_fingerprint !== a.fingerprint || p.source_hash !== a.candidate.source_hash || p.model_generated !== false || p.model_requests !== 0 || p.business_writes !== 0 || p.publishable !== false || p.formal_publication_enabled !== false || p.semantic_status !== "UNKNOWN" || p.owner_acceptance !== "PENDING" || !d || !Array.isArray(d.actions) || d.actions.length !== 3) return false;
  const {plan_fingerprint, cached, ...body} = p;
  if (await deliveryDigest(body) !== plan_fingerprint) return false;
  const m = d.manifest, steps = ["preview", "aggregate", "report"], refs = ["resource.read", "data.aggregate_csv", "intern.csv_report.v1"];
  if (m.app_id !== a.id || m.revision !== a.candidate.manifest.revision + 1 || !deliverySame(m.data_bindings, a.candidate.manifest.data_bindings) || !deliverySame(m.permission_requirements, a.candidate.manifest.permission_requirements) || !deliverySame(p.preflight.topological_order, steps) || !deliverySame(m.workflow.map(s => s.step_id), steps)) return false;
  for (let i = 0; i < 3; i++) {
    const action = d.actions[i], step = m.workflow[i];
    if (action.executor.kind !== "registered_tool" || action.executor.ref !== refs[i] || action.executor.version !== "1" || action.effect !== "read" || action.idempotency !== "read_only" || !deliverySame(action.allowed_tool_refs, []) || !deliverySame(step.depends_on, i ? [steps[i - 1]] : [])) return false;
  }
  if (d.actions[2].permission_requirements.length || d.actions[2].dependencies.length || !deliverySame(m.workflow[1].inputs.resource_id, {source:"step",ref:"preview",field:"resource_id"})) return false;
  return Object.values(m.outputs).every(v => v.source === "step" && v.ref === "report");
}
async function csvDagJobSeal(job, c, plan) {
  if (job.namespace !== "fixed-csv-dag.v1" || job.app_id !== c.parent.id || job.project_id !== c.parent.project || job.plan_fingerprint !== plan.plan_fingerprint || job.model_requests !== 0 || job.business_writes !== 0 || job.publishable !== false || job.formal_publication_enabled !== false || job.semantic_status !== "UNKNOWN" || job.owner_acceptance !== "PENDING" || !Array.isArray(job.steps) || job.steps.length > 3) return false;
  const rid = plan.definition.manifest.data_bindings[0].resource_ref, sourceHash = plan.source_hash, proved = [];
  for (let i = 0; i < job.steps.length; i++) {
    const receipt = job.steps[i], name = ["preview", "aggregate", "report"][i];
    const args = i === 0 ? {resource_id:rid} : i === 1 ? {resource_id:rid,column:plan.input.column} : job.steps[1].data;
    if (receipt.step_id !== name || receipt.status !== "VERIFIED" || receipt.plan_fingerprint !== plan.plan_fingerprint || receipt.source_hash !== sourceHash || receipt.data.resource_id !== rid || receipt.action_revision !== plan.definition.actions[i].revision || receipt.artifact_refs.length || receipt.input_fingerprint !== await deliveryDigest(args) || receipt.output_fingerprint !== await deliveryDigest(receipt.data) || !deliverySame(receipt.predecessor_receipts, i ? [await deliveryDigest(proved[i-1])] : [])) return false;
    if (i === 0) {
      const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(receipt.data.content));
      if (Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2,"0")).join("") !== sourceHash || receipt.data.hash !== sourceHash || receipt.data.format !== "csv") return false;
    } else if (receipt.data.column !== plan.input.column || receipt.data.source_hash !== sourceHash || !Number.isInteger(receipt.data.count) || typeof receipt.data.sum !== "string") return false;
    if (i === 2 && (!deliverySame(receipt.data, {...args,text:`列 ${args.column}；行数 ${args.count}；合计 ${args.sum}`}) || receipt.actual_reads.length)) return false;
    proved.push(receipt);
  }
  return job.status !== "SUCCEEDED" || (proved.length === 3 && deliverySame(job.result?.output, proved[2].data));
}
async function csvDagRead(c = csvDagContext, runId, plan = c?.plan) {
  if (!c || !csvDagCurrent(c)) return;
  const intent = csvDagIntents.get(csvDagKey(c));
  runId = runId || c.job?.id || intent?.runId;
  plan = plan || intent?.plan;
  if (!runId || !plan) throw Error("尚无已接受运行");
  try {
    const current = await api(csvDagBase(c) + "/" + encodeURIComponent(plan.request_key));
    if (!csvDagCurrent(c)) return;
    if (!await csvDagPlanSeal(current,c) || !deliverySame(current,plan)) throw Error("VERSION_CONFLICT");
    const job = await api(`/api/csv-dag/runs/${runId}`);
    if (!csvDagCurrent(c)) return;
    if (!await csvDagJobSeal(job,c,plan)) throw Error("VERIFICATION_FAILED");
    if (!csvDagCurrent(c)) return;
    c.plan = plan; c.job = job;
    $("csv-dag-confirm").checked = false;
    $("csv-dag-definition").textContent = JSON.stringify(plan,null,2);
    $("csv-dag-result").textContent = JSON.stringify(job,null,2);
    $("csv-dag-status").textContent = `${job.status} · ${job.steps.length}/3 步已核回执 · 候选未验收 · 发布关闭`;
    csvDagButtons(c); return job;
  } catch (e) {
    if (csvDagCurrent(c)) {
      csvDagClearProof(c);
      const metadata = await api(`/api/csv-dag/runs/${runId}/status`);
      if (csvDagCurrent(c) && metadata.id === runId && metadata.proof_status === "NOT_VALIDATED" && metadata.result === null && deliverySame(metadata.steps, [])) {
        c.job = metadata;
        $("csv-dag-status").textContent = `${metadata.status} · 来源／权限／版本证明失效；仅保留停止控制信息`;
        csvDagButtons(c);
      }
    }
    throw e;
  }
}
async function csvDagSubmit(kind, retry = false) {
  const c = csvDagContext; if (!c || !csvDagCurrent(c) || c.busy) return;
  const key = csvDagKey(c);
  let intent = csvDagIntents.get(key), returned = false;
  if (!retry) {
    if (intent) throw Error("先恢复原接受回执");
    if (kind === "plan") {
      const column = $("csv-dag-column").value;
      c.busy = true;csvDagButtons(c);
      try {
        const anchor = await api(deliveryBase(c.parent));
        if (!csvDagCurrent(c)) {c.busy = false;return;}
        if (!await deliveryGraphSeal(anchor,c.parent)) throw Error("VERSION_CONFLICT");
        if (!csvDagCurrent(c)) {c.busy = false;return;}
        intent = {kind, body:{expected_candidate_fingerprint:c.parent.app.fingerprint,expected_graph_fingerprint:anchor.graph_fingerprint,column,request_key:crypto.randomUUID()}};
      } catch(e) {c.busy = false;csvDagButtons(c);throw e;}
    } else {
      if (!c.plan || !$("csv-dag-confirm").checked) throw Error("请确认精确计划");
      intent = {kind,plan:c.plan,body:{expected_plan_fingerprint:c.plan.plan_fingerprint,consent:"CONFIRM_EXACT_OFFLINE_CSV_DAG",request_key:crypto.randomUUID()}};
    }
    csvDagIntents.set(key,intent);
  }
  if (!intent) return;
  c.busy = true; csvDagButtons(c);
  try {
    const path = intent.kind === "plan" ? csvDagBase(c) : csvDagBase(c) + "/" + encodeURIComponent(intent.plan.request_key) + "/runs";
    const made = await api(path,"POST",intent.body); returned = true;
    if (!csvDagCurrent(c)) return;
    if (intent.kind === "plan") {
      const saved = await api(csvDagBase(c) + "/" + encodeURIComponent(intent.body.request_key));
      if (!csvDagCurrent(c)) return;
      const {cached,...receipt} = made;
      if (!await csvDagPlanSeal(saved,c) || !deliverySame(receipt,saved) || saved.input.column !== intent.body.column) throw Error("VERSION_CONFLICT");
      if (!csvDagCurrent(c)) return;
      c.plan = saved; c.job = null;
      $("csv-dag-definition").textContent = JSON.stringify(saved,null,2); $("csv-dag-result").textContent = ""; $("csv-dag-confirm").checked = false;
      $("csv-dag-status").textContent = "固定草案已读回 · 尚未运行 · 请核对精确版本";
    } else {
      if (made.plan_fingerprint !== intent.plan.plan_fingerprint || made.plan_key !== intent.plan.request_key) throw Error("VERSION_CONFLICT");
      intent.runId = made.run_id;
      await csvDagRead(c,made.run_id,intent.plan);
      if (!csvDagCurrent(c)) return;
    }
    csvDagIntents.delete(key);
  } catch (e) {
    const rejected = !retry && !returned && [400,403,409,422].includes(e.httpStatus);
    if (rejected) csvDagIntents.delete(key);
    if (csvDagCurrent(c)) {csvDagClearProof(c);$("csv-dag-status").textContent = e.message + (rejected ? " · 请求被拒绝" : " · 接受结果 UNKNOWN，保留原键恢复");}
  } finally {c.busy = false;csvDagButtons();}
}
async function csvDagCommand(command) {
  const c = csvDagContext; if (!c?.job || !csvDagCurrent(c)) return;
  const id = c.job.id, plan = c.plan;
  let commandError;
  try {await api(`/api/runs/${id}/commands`,"POST",{command,version:c.job.version});}
  catch(e) {commandError=e;}
  if (csvDagCurrent(c)) {
    if (plan) await csvDagRead(c,id,plan);
    else {c.job = await api(`/api/csv-dag/runs/${id}/status`);if(csvDagCurrent(c))csvDagButtons(c);}
  }
  if(commandError)throw commandError;
}
async function csvDagHistory() {
  const c = csvDagContext; if (!c || !csvDagCurrent(c)) return;
  try {
    const data = await api(csvDagBase(c));
    if (!csvDagCurrent(c)) return;
    if (data.namespace !== "fixed-csv-dag.v1" || data.app_id !== c.parent.id || data.project_id !== c.parent.project || !Array.isArray(data.items) || !Array.isArray(data.invalidated)) throw Error("VERSION_CONFLICT");
    for (const item of data.items) if (!await csvDagPlanSeal(item.plan,c) || !Array.isArray(item.runs)) throw Error("VERSION_CONFLICT");
    if (!csvDagCurrent(c)) return;
    csvDagClearProof(c);
    for (const item of data.items) {
      $("csv-dag-history").append(row(`${item.plan.input.column} · ${item.plan.plan_fingerprint} · 候选未验收`, async () => {
        if (!csvDagCurrent(c)) return;
        const plan = await api(csvDagBase(c) + "/" + encodeURIComponent(item.plan.request_key));
        if (!csvDagCurrent(c)) return;
        if (!await csvDagPlanSeal(plan,c) || !deliverySame(plan,item.plan)) throw Error("VERSION_CONFLICT");
        if (!csvDagCurrent(c)) return;
        c.plan = plan;c.job = null;$("csv-dag-confirm").checked = false;$("csv-dag-definition").textContent = JSON.stringify(plan,null,2);$("csv-dag-result").textContent = "";csvDagButtons(c);
      }, "读回精确计划"));
      for (const job of item.runs) $("csv-dag-history").append(row(`${job.id} · ${job.status} · 回执尚未重新核对`, () => csvDagRead(c,job.id,item.plan), "核对运行回执"));
    }
    for (const stale of data.invalidated) $("csv-dag-history").append(row(`${stale.request_key} · INVALIDATED`));
    csvDagButtons(c);
  } catch(e) {if(csvDagCurrent(c))csvDagClearProof(c);throw e;}
}
$("csv-dag-plan").onclick = safe(() => csvDagSubmit("plan"));
$("csv-dag-run").onclick = safe(() => csvDagSubmit("run"));
$("csv-dag-retry").onclick = safe(() => csvDagSubmit(null,true));
$("csv-dag-refresh").onclick = safe(() => csvDagRead());
$("csv-dag-history-read").onclick = safe(csvDagHistory);
$("csv-dag-confirm").onchange = () => csvDagButtons();
$("csv-dag-column").onchange = () => { if(csvDagContext)csvDagClearProof(csvDagContext);csvDagButtons(); };
for(const command of ["pause","resume","cancel"])$("csv-dag-"+command).onclick = safe(() => csvDagCommand(command));
