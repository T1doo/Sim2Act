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
  $("csv-dag-branch-target").value = "";
  $("csv-dag-branch-input").value = "";
  $("csv-dag-history").replaceChildren();
  $("csv-dag-wiring").hidden = true;
  $("csv-dag-wiring-ports").replaceChildren();
  $("csv-dag-wiring-proof").textContent = "";
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
  for (const id of ["target","op","source","value"]) $("csv-dag-branch-"+id).disabled = locked;
  $("csv-dag-branch-input").disabled = locked || !c.plan?.branch_semantics;
  $("csv-dag-wiring-read").disabled = locked;
  for (const select of $("csv-dag-wiring-ports").querySelectorAll("select")) select.disabled = locked;
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
    if (action.executor.kind !== "registered_tool" || action.executor.ref !== refs[i] || action.executor.version !== "1" || action.effect !== "read" || action.idempotency !== "read_only" || !deliverySame(action.allowed_tool_refs, [])) return false;
  }
  if (d.actions[2].permission_requirements.length || d.actions[2].dependencies.length || !csvDagWiringSeal(p) || !csvDagBranchPlanSeal(p)) return false;
  return Object.values(m.outputs).every(v => v.source === "step" && v.ref === "report");
}
async function csvDagJobSeal(job, c, plan) {
  if (job.namespace !== "fixed-csv-dag.v1" || job.app_id !== c.parent.id || job.project_id !== c.parent.project || job.plan_fingerprint !== plan.plan_fingerprint || job.model_requests !== 0 || job.business_writes !== 0 || job.publishable !== false || job.formal_publication_enabled !== false || job.semantic_status !== "UNKNOWN" || job.owner_acceptance !== "PENDING" || !Array.isArray(job.steps) || job.steps.length > 3) return false;
  if (plan.branch_semantics && !csvDagBranchInputsSeal(job,plan)) return false;
  const rid = plan.definition.manifest.data_bindings[0].resource_ref, sourceHash = plan.source_hash, proved = [];
  for (let i = 0; i < job.steps.length; i++) {
    const receipt = job.steps[i], name = ["preview", "aggregate", "report"][i];
    const step = plan.definition.manifest.workflow[i], outputs = Object.fromEntries(proved.map(p => [p.step_id,p.data]));
    const inputs = plan.branch_semantics ? job.inputs : plan.input;
    const decision = plan.branch_semantics ? await csvDagBranchDecision(step,inputs,proved) : null;
    if (plan.branch_semantics && !deliverySame(receipt.branch_decision,decision)) return false;
    if (decision && !decision.passed) {
      const expected = {step_id:name,status:"SKIPPED",data:null,plan_fingerprint:plan.plan_fingerprint,source_hash:sourceHash,action_revision:plan.definition.actions[i].revision,predecessor_receipts:await Promise.all(proved.filter(p=>step.depends_on.includes(p.step_id)).map(deliveryDigest)),artifact_refs:[],actual_reads:[],branch_decision:decision};
      if (!deliverySame(receipt,expected)) return false;
      proved.push(receipt);continue;
    }
    const args = Object.fromEntries(Object.entries(step.inputs).map(([port,source]) => [port,source.source === "data" ? rid : source.source === "input" ? inputs[source.field] : outputs[source.ref]?.[source.field]]));
    const parents = await Promise.all(proved.filter(p => step.depends_on.includes(p.step_id)).map(deliveryDigest));
    if (receipt.step_id !== name || receipt.status !== "VERIFIED" || receipt.plan_fingerprint !== plan.plan_fingerprint || receipt.source_hash !== sourceHash || receipt.data.resource_id !== rid || receipt.action_revision !== plan.definition.actions[i].revision || receipt.artifact_refs.length || receipt.input_fingerprint !== await deliveryDigest(args) || receipt.output_fingerprint !== await deliveryDigest(receipt.data) || !deliverySame(receipt.predecessor_receipts, parents) || (plan.wiring && !deliverySame(receipt.input_sources,step.inputs))) return false;
    if (i === 0) {
      const hash = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(receipt.data.content));
      if (Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2,"0")).join("") !== sourceHash || receipt.data.hash !== sourceHash || receipt.data.format !== "csv") return false;
    } else if (receipt.data.column !== plan.input.column || receipt.data.source_hash !== sourceHash || !Number.isInteger(receipt.data.count) || typeof receipt.data.sum !== "string") return false;
    if (i === 2 && (!deliverySame(receipt.data, {...args,text:`列 ${args.column}；行数 ${args.count}；合计 ${args.sum}`}) || receipt.actual_reads.length)) return false;
    proved.push(receipt);
  }
  if(job.status !== "SUCCEEDED" && !(plan.branch_semantics && job.status === "PARTIAL")) return true;
  const output = proved[2]?.status === "VERIFIED" ? proved[2].data : null;
  return proved.length === 3 && job.status === (plan.branch_semantics && output === null ? "PARTIAL" : "SUCCEEDED") && deliverySame(job.result?.output,output) && deliverySame(job.result?.steps,proved) && (!plan.branch_semantics || job.result.output_status === (output ? "PRODUCED" : "SKIPPED"));
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
    if (!await csvDagJobSeal(job,c,plan) || (intent?.kind === "run" && plan.branch_semantics && !deliverySame(job.confirmation,intent.body))) throw Error("VERIFICATION_FAILED");
    if (!csvDagCurrent(c)) return;
    c.plan = plan; c.job = job;
    $("csv-dag-confirm").checked = false;
    $("csv-dag-definition").textContent = JSON.stringify(plan,null,2);
    $("csv-dag-result").textContent = JSON.stringify(job,null,2);
    $("csv-dag-status").textContent = `${job.status} · ${job.steps.length}/3 步已核执行／跳过证明${job.result?.output_status === "SKIPPED" ? " · 未产出报告" : ""} · 候选未验收 · 发布关闭`;
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
      const branchPatch = csvDagBranchPatch();
      const wiringPatch = c.wiringOptions ? Array.from($("csv-dag-wiring-ports").querySelectorAll("select"), select => ({step_id:select.dataset.step,port:select.dataset.port,source:JSON.parse(select.value)})) : null;
      c.busy = true;csvDagButtons(c);
      try {
        const anchor = await api(deliveryBase(c.parent));
        if (!csvDagCurrent(c)) {c.busy = false;return;}
        if (!await deliveryGraphSeal(anchor,c.parent)) throw Error("VERSION_CONFLICT");
        if (!csvDagCurrent(c)) {c.busy = false;return;}
        intent = {kind, body:{expected_candidate_fingerprint:c.parent.app.fingerprint,expected_graph_fingerprint:anchor.graph_fingerprint,column,request_key:crypto.randomUUID()}};
        if (branchPatch) intent.body.branch_patch = branchPatch;
        if (wiringPatch) {
          if(c.wiringOptions.graph_fingerprint !== anchor.graph_fingerprint)throw Error("VERSION_CONFLICT");
          intent.body.wiring_patch = wiringPatch;
        }
      } catch(e) {c.busy = false;csvDagButtons(c);throw e;}
    } else {
      if (!c.plan || !$("csv-dag-confirm").checked) throw Error("请确认精确计划");
      intent = {kind,plan:c.plan,body:{expected_plan_fingerprint:c.plan.plan_fingerprint,consent:"CONFIRM_EXACT_OFFLINE_CSV_DAG",request_key:crypto.randomUUID()}};
      if(c.plan.branch_semantics) {
        const value = $("csv-dag-branch-input").value;
        intent.body.branch_inputs = value === "" ? {} : {include_report:value === "true"};
      }
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
      if (!await csvDagPlanSeal(saved,c) || !deliverySame(receipt,saved) || saved.input.column !== intent.body.column || (intent.body.branch_patch && !intent.body.branch_patch.every(p=>deliverySame(saved.definition.manifest.workflow.find(s=>s.step_id===p.step_id).when,p.when))) || (intent.body.wiring_patch && !intent.body.wiring_patch.every(p => deliverySame(saved.definition.manifest.workflow.find(s => s.step_id===p.step_id).inputs[p.port],p.source)))) throw Error("VERSION_CONFLICT");
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
function csvDagPortOptions() {
  return [
    {step_id:"aggregate",port:"resource_id",semantic_type:"resource_id",sources:[{source:"step",ref:"preview",field:"resource_id"},{source:"data",ref:"source",field:"resource_id"}]},
    {step_id:"report",port:"resource_id",semantic_type:"resource_id",sources:[{source:"step",ref:"aggregate",field:"resource_id"},{source:"step",ref:"preview",field:"resource_id"}]},
    {step_id:"report",port:"source_hash",semantic_type:"source_hash",sources:[{source:"step",ref:"aggregate",field:"source_hash"},{source:"step",ref:"preview",field:"hash"}]}
  ];
}
function csvDagWiringSeal(plan) {
  const workflow = plan.definition.manifest.workflow, [preview,aggregate,report] = workflow;
  const defaults = {preview:{resource_id:{source:"data",ref:"source",field:"resource_id"}},aggregate:{resource_id:{source:"step",ref:"preview",field:"resource_id"},column:{source:"input",field:"column"}},report:Object.fromEntries(["resource_id","column","count","sum","source_hash"].map(field => [field,{source:"step",ref:"aggregate",field}]))};
  if (!deliverySame(preview.inputs,defaults.preview) || !deliverySame(preview.depends_on,[]) || !deliverySame(aggregate.depends_on,["preview"])) return false;
  if(!plan.wiring)return workflow.every(s => deliverySame(s.inputs,defaults[s.step_id])) && deliverySame(report.depends_on,["aggregate"]);
  const allowed = csvDagPortOptions();
  for(const step of workflow) {
    if(!deliverySame(Object.keys(step.inputs).sort(),Object.keys(defaults[step.step_id]).sort()))return false;
    for(const [port,source] of Object.entries(step.inputs)) {
      const choice = allowed.find(p => p.step_id===step.step_id&&p.port===port);
      if(choice ? !choice.sources.some(v => deliverySame(v,source)) : !deliverySame(source,defaults[step.step_id][port]))return false;
    }
  }
  const parents = ["preview","aggregate"].filter(ref => ref==="aggregate" || Object.values(report.inputs).some(v => v.source==="step"&&v.ref===ref));
  return deliverySame(report.depends_on,parents) && deliverySame(plan.wiring,{version:"csv.wiring.v1",inputs:Object.fromEntries(workflow.map(s => [s.step_id,s.inputs])),depends_on:Object.fromEntries(workflow.map(s => [s.step_id,s.depends_on]))});
}
async function csvDagWiringRead() {
  const c=csvDagContext;if(!c||!csvDagCurrent(c)||c.busy||csvDagIntents.has(csvDagKey(c)))return;
  c.busy=true;csvDagButtons(c);
  try {
    const data=await api(csvDagBase(c)+"/options/wiring");if(!csvDagCurrent(c))return;
    const {options_fingerprint,...body}=data;
    if(data.version!=="csv.wiring.v1"||data.app_id!==c.parent.id||data.project_id!==c.parent.project||data.candidate_fingerprint!==c.parent.app.fingerprint||data.editable_dependencies!==false||!deliverySame(data.barrier,["preview","aggregate"])||!deliverySame(data.fixed_steps,["preview","aggregate","report"])||!deliverySame(data.ports,csvDagPortOptions())||await deliveryDigest(body)!==options_fingerprint)throw Error("VERSION_CONFLICT");
    if(!csvDagCurrent(c))return;
    csvDagClearProof(c);c.wiringOptions=data;
    $("csv-dag-wiring-ports").replaceChildren();
    for(const port of data.ports) {
      const label=document.createElement("label"),select=document.createElement("select");label.textContent=`${port.step_id}.${port.port} 来源 `;select.id=`csv-dag-wire-${port.step_id}-${port.port}`;select.dataset.step=port.step_id;select.dataset.port=port.port;
      for(const source of port.sources) {const option=document.createElement("option");option.value=JSON.stringify(source);option.textContent=`${source.ref}.${source.field}`;select.append(option);}
      select.onchange=()=>{if(csvDagCurrent(c)){csvDagClearProof(c);csvDagButtons(c);}};label.append(select);$("csv-dag-wiring-ports").append(label);
    }
    $("csv-dag-wiring").hidden=false;$("csv-dag-wiring-proof").textContent=JSON.stringify(data,null,2);
  } catch(e) {if(csvDagCurrent(c)){c.wiringOptions=null;csvDagClearProof(c);$("csv-dag-wiring").hidden=true;}throw e;}
  finally{c.busy=false;csvDagButtons(c);}
}
$("csv-dag-wiring-read").onclick=safe(csvDagWiringRead);
$("csv-dag-plan").onclick = safe(() => csvDagSubmit("plan"));
$("csv-dag-run").onclick = safe(() => csvDagSubmit("run"));
$("csv-dag-retry").onclick = safe(() => csvDagSubmit(null,true));
$("csv-dag-refresh").onclick = safe(() => csvDagRead());
$("csv-dag-history-read").onclick = safe(csvDagHistory);
$("csv-dag-confirm").onchange = () => csvDagButtons();
$("csv-dag-column").onchange = () => { if(csvDagContext)csvDagClearProof(csvDagContext);csvDagButtons(); };
for(const command of ["pause","resume","cancel"])$("csv-dag-"+command).onclick = safe(() => csvDagCommand(command));

function csvDagBranchPatch() {
  const target = $("csv-dag-branch-target").value;
  if(!target)return null;
  const [ref,field] = $("csv-dag-branch-source").value.split(":"),op=$("csv-dag-branch-op").value;
  const when={op,source:ref==="input"?{source:"input",field}:{source:"step",ref,field}};
  if(op!=="exists")when.value=JSON.parse($("csv-dag-branch-value").value);
  return [{step_id:target,when}];
}
function csvDagBranchPlanSeal(plan) {
  const m=plan.definition.manifest,conditions=m.workflow.filter(s=>s.when);
  if(!plan.branch_semantics)return !conditions.length && !("include_report" in m.input_schema.properties);
  if(plan.branch_semantics!=="typed-conditions.v1" || !conditions.length || !deliverySame(m.input_schema.properties.include_report,{type:"boolean"}) || m.input_schema.required.includes("include_report"))return false;
  return conditions.every(step=>{
    const c=step.when,s=c.source;
    if(step.step_id==="preview" || !["eq","in","exists"].includes(c.op) || !["input","step"].includes(s.source) || (s.source==="input"?s.ref!=null:!step.depends_on.includes(s.ref)))return false;
    const schema=s.source==="input"?m.input_schema:plan.definition.actions[m.workflow.findIndex(v=>v.step_id===s.ref)]?.output_schema;
    const type=schema?.properties?.[s.field]?.type;
    const valid=v=>type==="boolean"?typeof v==="boolean":type==="integer"?Number.isInteger(v):type==="number"?typeof v==="number"&&Number.isFinite(v):type==="string"&&typeof v==="string";
    return c.op==="exists"?!Object.hasOwn(c,"value"):c.op==="in"?Array.isArray(c.value)&&c.value.length>0&&c.value.length<=20&&c.value.every(valid):valid(c.value);
  });
}
function csvDagBranchInputsSeal(job,plan) {
  const c=job.confirmation,inputs=job.inputs;
  if(!c || c.expected_plan_fingerprint!==plan.plan_fingerprint || c.consent!=="CONFIRM_EXACT_OFFLINE_CSV_DAG" || typeof c.request_key!=="string" || !inputs || inputs.column!==plan.input.column)return false;
  const extra=c.branch_inputs||{};
  if(Object.keys(extra).some(k=>k!=="include_report") || (Object.hasOwn(extra,"include_report")&&typeof extra.include_report!=="boolean"))return false;
  return deliverySame(inputs,{...plan.input,...extra});
}
async function csvDagBranchDecision(step,inputs,proved) {
  const parents=proved.filter(p=>step.depends_on.includes(p.step_id)),skipped=parents.filter(p=>p.status==="SKIPPED").map(p=>p.step_id);
  const condition=step.when||null;let passed=true,reason="UNCONDITIONAL",observation={evaluated:false};
  if(skipped.length){passed=false;reason="DEPENDENCY_SKIPPED";}
  else if(condition){
    const src=condition.source,values=src.source==="input"?inputs:parents.find(p=>p.step_id===src.ref)?.data;
    if(!values)throw Error("VERIFICATION_FAILED");
    const present=Object.hasOwn(values,src.field),value=values[src.field];observation={evaluated:true,present};if(present)observation.value=value;
    if(condition.op==="exists")passed=present;
    else {if(!present)throw Error("INVALID_INPUT");const choices=condition.op==="in"?condition.value:[condition.value];passed=choices.some(v=>typeof v===typeof value&&deliverySame(v,value));}
    reason=passed?"CONDITION_TRUE":"CONDITION_FALSE";
  }
  return {version:"typed-conditions.v1",condition,observation,passed,reason,skipped_predecessors:skipped,inputs_fingerprint:await deliveryDigest(inputs)};
}
$("csv-dag-branch-input").onchange=()=>{$("csv-dag-confirm").checked=false;csvDagButtons();};
