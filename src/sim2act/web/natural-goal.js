"use strict";
// Page-memory intent keys survive view changes; no credentials or data are persisted.
const naturalGoalRequests = new Map(), naturalGoalConfirmations = new Map(), naturalGoalAcknowledgements = new Set(), naturalGoalCancellations = new Map();
let naturalGoalGeneration = 0, naturalGoalDisplayed = null;
let naturalActivationSelection=null,naturalActivationRows=[],naturalActivationGeneration=0,naturalActivationBlocked=false,naturalActivationContext=null;
const naturalGoalKey = (card=activeGoalCard) => card ? JSON.stringify([token,$("project-select").value,card.id,naturalActivationSelection?.row.id || null]) : null;
const naturalGoalFp = value => typeof value === "string" && /^[a-f0-9]{64}$/.test(value);
function invalidateNaturalGoalAcknowledgements(){naturalGoalAcknowledgements.clear();}
function clearNaturalGoal() {
  naturalGoalGeneration++;
  naturalActivationGeneration++;
  if(naturalActivationContext && (naturalActivationContext.identity!==token || naturalActivationContext.project!==$("project-select").value))clearNaturalActivation();
  naturalGoalAcknowledgements.clear();
  $("natural-fixed-acceptance").checked=false;
  if(naturalGoalDisplayed && activeRun===naturalGoalDisplayed){activeRun=null;runSelectionGeneration++;clearRunDetail();}
  naturalGoalDisplayed=null;
  $("natural-goal-config").textContent="先保存并打开目标，再读取当前项目的规划配置。";
  renderNaturalGoalControls();
}
function renderNaturalGoalControls(){
  const card=activeGoalCard,entry=naturalGoalRequests.get(naturalGoalKey());
  const selected=naturalActivationSelection?.row;
  $("natural-fixed-acceptance").disabled=selected?.scope.mode!=="OFFLINE_TEST" || Boolean(entry && entry.state!=="rejected");
  if(entry)$("natural-fixed-acceptance").checked=entry.acceptFixed===true;
  const bound=selected?.scope.goals.find(g=>g.card_id===card?.id && g.expected_version===card.version && g.expected_fingerprint===card.fingerprint);
  const unavailable=selected && (!selected.submission_available || !selected.approved_not_expired || !bound || selected.charged_requests>=2 || selected.charged_kinds.includes(bound.kind) || Date.now()>=selected.approval.expires_at*1000);
  $("natural-goal-generate").disabled=naturalActivationBlocked||unavailable||!card||goalCardLoading||goalCardSaving||Boolean(entry && !["rejected"].includes(entry.state));
  $("natural-goal-generate").textContent=card?`生成已保存 v${card.version} 的计划`:"生成已保存目标的计划";
  $("natural-goal-recover").hidden=entry?.state!=="unknown";
  $("natural-goal-read").hidden=!entry?.runId;
  $("natural-goal-read").disabled=entry?.state==="sending";
  $("natural-goal-new").hidden=!entry||!["accepted","rejected"].includes(entry.state);
  $("natural-goal-status").textContent=entry?.message||"先保存目标。生成计划不会确认执行；结构校验也不代表目标语义验收。";
}
async function refreshNaturalGoalStatus(){
  const project=$("project-select").value,identity=token,generation=naturalGoalGeneration;
  if(!project)return;
  const current=()=>project===$("project-select").value&&identity===token&&generation===naturalGoalGeneration;
  $("natural-goal-config").textContent="正在读取项目规划配置…";
  try {
    const status=await api(`/api/projects/${project}/natural-planning-status`);
    if(!current())return;
    if(!["disabled","intern-s2"].includes(status.provider)||status.live_request_allowance!==0||status.available!==false||status.reason!==(status.provider==="disabled"?"PROVIDER_DISABLED":"LIVE_ALLOWANCE_ZERO"))throw Error("未知规划配置，不能判断可用性");
    $("natural-goal-config").textContent=(naturalActivationSelection?"默认普通规划授权为0；选中会话的有限范围与状态见上方，生成请求必须绑定该会话。 ":"")+ (status.provider==="disabled"?"自然语言规划默认关闭：缺少显式模型配置与调用授权。可保存目标或提交持久规划请求；当前会等待资源，不会产生计划。":"已选择 Intern-S2，但真实调用授权为 0：当前不能调用真实模型。离线工程适配器不代表真实模型可用。");
  } catch(error){if(current())$("natural-goal-config").textContent=`规划配置读取失败：${error.message}。不能判断模型可用性。`;}
}
async function readNaturalGoal(entry,current){
  if(!current())return;
  try {
    naturalGoalDisplayed=entry.runId;
    await showRun(entry.runId,true,()=>current()&&naturalGoalDisplayed===entry.runId,r=>{
      const source=r.contract?.snapshot?.source_goal_card;
      const binding=r.contract?.snapshot?.natural_planning?.activation;
      if(entry.activation && goalRunCanonical(binding)!==goalRunCanonical(entry.activation))throw Error("VERSION_CONFLICT");
      if(!entry.activation && binding)throw Error("VERSION_CONFLICT");
      if(goalRunCanonical(r.contract?.snapshot?.natural_planning?.goal_acceptance||null)!==goalRunCanonical(entry.fixedSpec||null))throw Error("验收契约绑定不匹配");
      if(r.id!==entry.runId||!source||source.card_id!==entry.cardId||source.version!==entry.body.expected_version||source.fingerprint!==entry.body.expected_fingerprint||goalRunCanonical(source.snapshot)!==goalRunCanonical(entry.snapshot)||r.contract?.snapshot?.natural_planning?.require_confirmation!==true)throw Error("VERSION_CONFLICT");
    });
    if(!current())return;
    if(activeRun!==entry.runId)throw Error("任务详情不可用");
    entry.state="accepted";entry.message=`已接受保存 v${entry.body.expected_version} 的规划请求。请查看实际状态；计划、工具回执和语义验收分开记录。`;
  } catch(error){entry.state="read-error";entry.message="规划请求已接受，但详情读取失败或版本不匹配。只能重读原任务，不能另建请求。";}
  finally {if(current())renderNaturalGoalControls();}
}
async function generateNaturalGoal(recover=false){
  const card=activeGoalCard;if(!card||goalCardLoading||goalCardSaving)return;
  const key=naturalGoalKey(card),identity=token,project=card.project_id,generation=naturalGoalGeneration,selection=runUserSelectionGeneration;
  const current=()=>identity===token&&project===$("project-select").value&&generation===naturalGoalGeneration&&activeGoalCard?.id===card.id;
  let entry=naturalGoalRequests.get(key);
  if(entry?.state==="sending")return;
  if(!recover){
    if(entry && entry.state!=="rejected")return;
    const selected=naturalActivationSelection?.row;
    if(naturalActivationBlocked)return;
    if(selected && (!selected.submission_available || !selected.approved_not_expired || selected.charged_requests>=2 || !selected.scope.goals.some(g=>g.card_id===card.id && g.expected_version===card.version && g.expected_fingerprint===card.fingerprint && !selected.charged_kinds.includes(g.kind))))return;
    const acceptFixed=selected?.scope.mode==="OFFLINE_TEST" && $("natural-fixed-acceptance").checked;
    const fixedGoal=selected?.scope.goals.find(g=>g.card_id===card.id);
    const fixedSpec=acceptFixed?{version:"fixed-csv-goal-acceptance.v1",kind:fixedGoal.kind,resource_id:fixedGoal.resource_id,source_hash:fixedGoal.resource_hash,goal_fingerprint:fixedGoal.expected_fingerprint,check:fixedGoal.kind==="read_preview"?"csv.complete_preview.v1":"csv.exact_integer_sum.v1"}:null;
    entry={acceptFixed,fixedSpec,endpoint:selected?`/api/natural-activations/${selected.id}/goal-cards/${card.id}/${acceptFixed?"fixed-goal-runs":"planned-runs"}`:`/api/projects/${project}/goal-cards/${card.id}/planned-runs`,activation:selected?{activation_id:selected.id,scope_fingerprint:selected.scope_fingerprint,approval_fingerprint:selected.approval_fingerprint}:null,cardId:card.id,snapshot:card.snapshot,body:{expected_version:card.version,expected_fingerprint:card.fingerprint,request_key:crypto.randomUUID()},state:"new",uncertain:false,runId:null};naturalGoalRequests.set(key,entry);
  }
  if(!entry)return;
  if(entry.runId){await readNaturalGoal(entry,current);return;}
  entry.state="sending";entry.message="正在接受规划请求；不会自动确认执行。";renderNaturalGoalControls();
  try {
    const receipt=await api(entry.endpoint,"POST",entry.body);
    if(typeof receipt?.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(receipt.run_id)||receipt.status!=="ACCEPTED"||receipt.goal_card_id!==entry.cardId||receipt.goal_version!==entry.body.expected_version||receipt.goal_fingerprint!==entry.body.expected_fingerprint||receipt.goal_acceptance!=="NOT_RUN"||receipt.candidate_generated!==false||receipt.planning_policy?.require_confirmation!==true)throw Error("未知规划接受回执");
    if(entry.activation && goalRunCanonical(receipt.planning_policy.activation)!==goalRunCanonical(entry.activation))throw Error("会话绑定回执不匹配");
    if(goalRunCanonical(receipt.planning_policy.goal_acceptance||null)!==goalRunCanonical(entry.fixedSpec||null))throw Error("整体验收合同回执不匹配");
    entry.runId=receipt.run_id;entry.state="read-error";
  } catch(error){
    const rejected=!entry.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
    entry.state=rejected?"rejected":"unknown";if(!rejected)entry.uncertain=true;
    entry.message=rejected?`规划请求被拒绝：${error.message}`:"规划接受结果 UNKNOWN。请显式恢复原版本、原指纹和原请求键，不另建重复任务。";
    if(current())renderNaturalGoalControls();return;
  }
  if(current()&&selection===runUserSelectionGeneration)await readNaturalGoal(entry,current);
  if(current())renderNaturalGoalControls();
}
function naturalGoalPlanShape(r,n){
  const plan=n?.plan,source=r.contract?.snapshot?.source_goal_card;
  if(!Number.isSafeInteger(r.version)||r.version<1||n?.validation!=="VALIDATED"||n.confirmation_required!==(r.contract?.snapshot?.natural_planning?.require_confirmation===true)||Object.keys(n).some(k=>!["plan","fingerprint","validation","confirmation_required","confirmed"].includes(k)))throw Error("计划校验或确认元数据不可信");
  if(!plan||plan.version!=="natural-goal-plan.v1"||!naturalGoalFp(n.fingerprint)||typeof n.confirmed!=="boolean"||typeof n.confirmation_required!=="boolean"||!source||plan.source_goal_fingerprint!==source.fingerprint||Object.keys(plan).some(k=>!["version","source_goal_fingerprint","interpretation","steps"].includes(k)))throw Error("未知或不匹配的计划 schema");
  const meaning=plan.interpretation;
  if(!meaning||typeof meaning.objective!=="string"||!meaning.objective||Object.keys(meaning).some(k=>!["objective","assumptions","unresolved"].includes(k))||![meaning.assumptions,meaning.unresolved].every(v=>Array.isArray(v)&&v.length<=16&&v.every(x=>typeof x==="string"))||!Array.isArray(plan.steps)||!plan.steps.length||plan.steps.length>4)throw Error("未知计划结构");
  const seen=new Set();
  for(const step of plan.steps){
    if(!step||Object.keys(step).some(k=>!["id","tool_ref","resource_id","column","depends_on"].includes(k))||typeof step.id!=="string"||!/^[a-z][a-z0-9_]{0,15}$/.test(step.id)||seen.has(step.id)||!["resource.read","data.aggregate_csv"].includes(step.tool_ref)||!source.snapshot?.content?.resource_refs?.includes(step.resource_id)||!Array.isArray(step.depends_on)||step.depends_on.length>4||new Set(step.depends_on).size!==step.depends_on.length||!step.depends_on.every(x=>seen.has(x))||(step.tool_ref==="data.aggregate_csv"?(typeof step.column!=="string"||!step.column):step.column!=null))throw Error("未知或越界计划步骤");
    seen.add(step.id);
  }
  if(n.confirmation_required && r.contract.snapshot.natural_planning?.require_confirmation!==true)throw Error("确认策略不匹配");
  if(r.status==="WAITING_APPROVAL"&&(!n.confirmation_required||n.confirmed||r.contract.snapshot.natural_planning?.require_confirmation!==true))throw Error("确认状态与计划策略矛盾");
  return plan;
}
async function renderNaturalGoalRun(r,id,current){
  if(!r.contract?.snapshot?.natural_planning)return;
  const section=document.createElement("section");section.id="natural-goal-plan";$("result").append(section);
  section.append(row("自然语言计划与确认"));
  let deadline=null;
  if(r.natural_deadline){
    const d=r.natural_deadline,seals=r.events.filter(e=>e.kind==="NL_RUN_DEADLINE_FROZEN");
    if(![d.accepted_at,d.expires_at,d.run_seconds].every(Number.isFinite) || d.run_seconds!==r.contract.snapshot.limits.run_seconds || Math.abs(d.expires_at-d.accepted_at-d.run_seconds)>.001 || seals.length!==1 || seals[0].data.created_at!==d.accepted_at || seals[0].data.deadline!==d.expires_at || seals[0].data.contract_fingerprint!==r.contract.fingerprint){section.append(row("冻结确认期限不匹配，确认关闭。"));return;}
    deadline=Date.now()+(d.expires_at-(Number.isFinite(r.naturalServerTime)?r.naturalServerTime:Date.now()/1000))*1000;
    section.append(row(`任务接受：${new Date(d.accepted_at*1000).toISOString()}；确认和执行截止：${new Date(d.expires_at*1000).toISOString()}（原接受起 ${d.run_seconds} 秒，不随刷新续期）。`));
    if(deadline<=Date.now())section.append(row("任务确认期限已过；会话批准不能延长此任务。历史仍可读取。"));
  }
  if(r.contract.snapshot.natural_planning.activation)section.append(row(`已绑定会话 ${r.contract.snapshot.natural_planning.activation.activation_id}；会话授权不是本计划的执行确认。`));
  if(!r.natural_plan){
    section.append(row(r.status==="WAITING_RESOURCE"?"当前等待规划配置、授权或可信回执；没有可确认的计划。":"尚无已校验计划；失败或未知结果不会被显示为规划成功。"));return;
  }
  let plan;
  try {
    plan=naturalGoalPlanShape(r,r.natural_plan);
    const bytes=new TextEncoder().encode(goalRunCanonical(plan));
    const hash=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",bytes)),b=>b.toString(16).padStart(2,"0")).join("");
    if(!current())return;
    if(hash!==r.natural_plan.fingerprint)throw Error("计划内容与指纹不匹配");
  }
  catch(error){if(current()){invalidateNaturalGoalAcknowledgements();section.append(row(`${error.message}。确认已关闭，请核对持久任务。`));}return;}
  const accepted=r.result?.task_acceptance;
  if(r.contract.snapshot.natural_planning.goal_acceptance)section.append(row(`本次冻结固定目标契约 fixed-csv-goal-acceptance.v1：${accepted?.status||"等待全部检查"}；单步 ${accepted?.single_step_status||"未完成"}；限定整体 ${accepted?.whole_task_accepted===true?"PASS":"未通过"}；人工 PENDING，正式发布关闭。`));
  section.append(row(`已通过结构与来源校验；通用目标语义 NOT_RUN，人工签收 PENDING。保存来源 v${r.contract.snapshot.source_goal_card.version}。`));
  section.append(row(`计划目标：${plan.interpretation.objective}`));
  section.append(row(`假设：${plan.interpretation.assumptions.join("；")||"无"}`),row(`未决项：${plan.interpretation.unresolved.join("；")||"无"}`));
  const steps=document.createElement("ol");
  for(const step of plan.steps){const li=document.createElement("li");li.textContent=`${step.id}：${step.tool_ref} · ${step.resource_id}${step.column?` · 列 ${step.column}`:""} · 依赖 ${step.depends_on.join(",")||"无"}`;steps.append(li);}section.append(steps);
  section.append(row(r.result?.transport==="OFFLINE_MOCKTRANSPORT"||r.contract.snapshot.mode==="MOCK"?"离线 MOCK 工程记录，不代表真实模型验收。":"规划记录不是目标语义验收。"));
  let sessionReady=true;
  const activation=r.contract.snapshot.natural_planning.activation;
  if(activation){
    try {
      const list=await api(`/api/projects/${$("project-select").value}/natural-activations`);
      if(!current())return;
      const session=list.items?.find(x=>x.id===activation.activation_id);
      if(!session || session.scope_fingerprint!==activation.scope_fingerprint || session.approval_fingerprint!==activation.approval_fingerprint)throw Error("会话指纹不匹配");
      sessionReady=session.submission_available===true && session.approved_not_expired===true;
      section.append(row(`会话到期：${new Date(session.approval.expires_at*1000).toISOString()} · 已占请求 ${session.charged_requests}/2；${sessionReady?"会话有效，仍须另行确认本计划":"会话不可执行："+(session.blocked_reason||session.status)}。`));
    } catch(error){sessionReady=false;section.append(row(`会话回读失败：${error.message}；执行确认关闭。`));}
  }
  const n=r.natural_plan,key=JSON.stringify([token,$("project-select").value,id,n.fingerprint]),entry=naturalGoalConfirmations.get(key),cancelEntry=naturalGoalCancellations.get(key);
  if(n.confirmed){if(entry)entry.state="accepted";section.append(row("该计划已有显式确认记录；实际执行状态与回执见本任务。"));return;}
  if(!n.confirmation_required){section.append(row("历史工程任务未要求新确认门；本页不追认确认。"));return;}
  if(r.status!=="WAITING_APPROVAL"){section.append(row("当前状态不可确认执行。"));return;}
  section.append(row("等待显式确认：确认前工具操作为 0。确认会使用该任务冻结的材料、版本与参数；撤权或材料变化仍会阻止执行。"));
  const label=document.createElement("label"),ack=document.createElement("input");ack.type="checkbox";ack.id="natural-goal-ack";const ackKey=JSON.stringify([key,r.version]);ack.checked=naturalGoalAcknowledgements.has(ackKey);label.append(ack," 我已阅读以上计划，确认执行这些只读步骤");section.append(label);
  const confirm=document.createElement("button");confirm.id="natural-goal-confirm";confirm.textContent="确认此计划并执行";confirm.disabled=!sessionReady||!deadline||Date.now()>=deadline||!ack.checked||Boolean(entry&&entry.state!=="rejected")||Boolean(cancelEntry);
  ack.onchange=()=>{if(ack.checked)naturalGoalAcknowledgements.add(ackKey);else naturalGoalAcknowledgements.delete(ackKey);confirm.disabled=!sessionReady||!deadline||Date.now()>=deadline||!ack.checked||Boolean(entry&&entry.state!=="rejected")||Boolean(cancelEntry);};
  ack.disabled=!sessionReady||Boolean(cancelEntry)||!deadline||Date.now()>=deadline;
  confirm.onclick=safe(()=>sessionReady?confirmNaturalGoal(r,n,key,current,false,deadline):undefined);section.append(confirm);
  if(entry?.state==="unknown"||entry?.state==="sending"){
    section.append(row("确认接受结果 UNKNOWN 或仍在提交。不要新建确认；只能核对任务或恢复原确认键。"));
    const read=document.createElement("button");read.id="natural-goal-confirm-read-recover";read.textContent="核对确认状态（只读）";read.onclick=safe(()=>current()?showRun(id):undefined);section.append(read);
    const retry=document.createElement("button");retry.id="natural-goal-confirm-retry";retry.textContent="显式恢复原确认回执";retry.disabled=entry.state==="sending";retry.onclick=safe(()=>confirmNaturalGoal(r,n,key,current,true));section.append(retry);
  }
  if(entry?.message)section.append(row(entry.message));
  const cancel=document.createElement("button");cancel.id="natural-goal-cancel";cancel.textContent=cancelEntry?.state==="unknown"?"显式恢复原取消请求":"取消此任务";cancel.disabled=entry?.state==="sending"||cancelEntry?.state==="sending";
  if(cancelEntry)section.append(row("已有取消意图，确认已关闭。取消接受不明时只能读取或显式恢复原版本取消。"));
  cancel.onclick=safe(async()=>{
    if(!current())return;
    let attempt=naturalGoalCancellations.get(key);if(attempt?.state==="sending")return;
    if(!attempt){attempt={body:{command:"cancel",version:r.version},state:"new"};naturalGoalCancellations.set(key,attempt);}
    attempt.state="sending";cancel.disabled=true;confirm.disabled=true;ack.disabled=true;
    try {await api(`/api/runs/${id}/commands`,"POST",attempt.body);attempt.state="accepted";}
    catch(error){attempt.state="unknown";}
    if(current())await showRun(id);
  });section.append(cancel);
}
async function confirmNaturalGoal(r,n,key,current,recover,deadline=null){
  if(!recover && (!deadline || Date.now()>=deadline))return;
  if(!current()||naturalGoalCancellations.has(key))return;
  let entry=naturalGoalConfirmations.get(key);
  if(entry?.state==="sending")return;
  if(!recover){
    if(entry&&entry.state!=="rejected")return;
    if(!$("natural-goal-ack")?.checked)return;
    entry={body:{expected_version:r.version,expected_plan_fingerprint:n.fingerprint,request_key:crypto.randomUUID()},state:"new"};naturalGoalConfirmations.set(key,entry);
  }
  if(!entry)return;
  entry.state="sending";
  for(const id of ["natural-goal-confirm","natural-goal-ack","natural-goal-cancel","natural-goal-confirm-retry"]){if($(id))$(id).disabled=true;}
  try {
    const receipt=await api(`/api/runs/${r.id}/confirm-natural-plan`,"POST",entry.body);
    if(receipt?.run_id!==r.id||receipt.plan_fingerprint!==n.fingerprint||receipt.confirmed!==true||!Number.isSafeInteger(receipt.version)||receipt.version<entry.body.expected_version+1||receipt.goal_acceptance!=="NOT_RUN"||receipt.candidate_generated!==false||!["QUEUED","RUNNING","PARTIAL","FAILED","WAITING_RESOURCE","PAUSED","CANCELLED","CANCEL_REQUESTED","RECONCILING"].includes(receipt.status))throw Error("未知确认回执");
    entry.state="accepted";entry.message="确认已接受。请读取实际执行记录。";
  } catch(error){
    const rejected=!entry.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
    entry.state=rejected?"rejected":"unknown";if(!rejected)entry.uncertain=true;
    entry.message=rejected?`确认被拒绝：${error.message}。请重读当前计划和版本。`:`确认接受结果 UNKNOWN：${error.message}。保留原确认键，仅显式恢复。`;
  }
  if(current())await showRun(r.id);
}
$("natural-goal-generate").onclick=safe(()=>generateNaturalGoal());
$("natural-goal-recover").onclick=safe(()=>generateNaturalGoal(true));
$("natural-goal-read").onclick=safe(()=>generateNaturalGoal(true));
$("natural-goal-back").onclick=()=>{clearNaturalGoal();renderNaturalGoalControls();};
$("natural-goal-new").onclick=()=>{
  const key=naturalGoalKey(),entry=naturalGoalRequests.get(key);
  if(entry&&["accepted","rejected"].includes(entry.state)){naturalGoalRequests.delete(key);clearNaturalGoal();renderNaturalGoalControls();}
};
renderNaturalGoalControls();

function clearNaturalActivation(){
  naturalActivationGeneration++;naturalActivationSelection=null;naturalActivationRows=[];naturalActivationBlocked=false;naturalActivationContext=null;
  $("natural-activation-select").replaceChildren(new Option("未选择；沿用默认关闭的普通规划",""));
  $("natural-activation-goals").replaceChildren();$("natural-activation-status").textContent="尚未读取当前项目会话。";
}
function renderNaturalActivation(){
  const selected=naturalActivationSelection?.row;
  $("natural-activation-goals").replaceChildren();
  if(!selected){$("natural-activation-status").textContent="未选择会话。读取和选择不创建或批准会话；真实调用默认0。";renderNaturalGoalControls();return;}
  const expires=selected.approval?.expires_at;
  $("natural-activation-status").textContent=`${selected.scope.mode=== "OFFLINE_TEST"?"离线测试会话，不代表真实模型":"LIVE范围记录，不代表当前已启用发送"} · ${selected.status} · 请求已占 ${selected.charged_requests}/2 · token已预留 ${selected.reserved_tokens}/22000（不是金额上限） · ${selected.scope.version==="natural-activation.v2"?"RPM1":"旧scope未冻结RPM，不能新执行"} · ${expires?"批准到期 "+new Date(expires*1000).toISOString():"未批准"} · ${selected.submission_available&&selected.approved_not_expired&&selected.charged_requests<2&&selected.reserved_tokens<22000?"可提交冻结目标，发送仍由Worker复核":"不可提交："+(selected.blocked_reason||(selected.charged_requests>=2?"预算已用尽":"批准已过期"))} · scope ${selected.scope_fingerprint}`;
  for(const goal of selected.scope.goals){
    const node=row(`${goal.kind==="read_preview"?"合成CSV预览":"合成quantity_z求和，独立oracle19"} · 目标 v${goal.expected_version} · 材料hash ${goal.resource_hash}`,async()=>{
      const state=naturalActivationSelection;if(!state||state.row.id!==selected.id || state.identity!==token || state.project!==$("project-select").value)return;
      await showGoalCard(goal.card_id);
      if(naturalActivationSelection!==state)return;
      if(activeGoalCard?.version!==goal.expected_version||activeGoalCard?.fingerprint!==goal.expected_fingerprint){naturalActivationBlocked=true;$("natural-activation-status").textContent="会话冻结目标版本已变化，请重新核对；不会改用普通规划。";}
      renderNaturalGoalControls();
    },"打开会话冻结目标");
    $("natural-activation-goals").append(node);
  }
  renderNaturalGoalControls();
}
async function refreshNaturalActivations(){
  const identity=token,project=$("project-select").value,generation=++naturalActivationGeneration;
  const current=()=>identity===token&&project===$("project-select").value&&generation===naturalActivationGeneration;
  if(!project)return;
  naturalActivationContext={identity,project};
  $("natural-activation-status").textContent="正在只读核对已有会话…";
  try {
    const body=await api(`/api/projects/${project}/natural-activations`);
    if(!current())return;
    if(body.project_id!==project||body.general_live_request_allowance!==0||!Array.isArray(body.items))throw Error("会话列表范围不可信");
    for(const item of body.items){
      if(!/^nlactivation_[a-f0-9]{32}$/.test(item.id)||item.project_id!==project||!naturalGoalFp(item.scope_fingerprint)||!item.scope||!["OFFLINE_TEST","LIVE"].includes(item.scope.mode)||!Array.isArray(item.scope.goals)||!item.scope.goals.length||item.scope.goals.length>2||item.scope.goals.some(g=>!["read_preview","sum_quantity_z"].includes(g.kind)||!/^goal_[a-f0-9]{32}$/.test(g.card_id)||!naturalGoalFp(g.expected_fingerprint))||item.scope.caps.requests!==2||item.scope.caps.tokens!==22000||!Number.isSafeInteger(item.charged_requests)||item.charged_requests<0||item.charged_requests>2||!Number.isSafeInteger(item.reserved_tokens)||!Array.isArray(item.charged_kinds)||typeof item.submission_available!=="boolean"||typeof item.approved_not_expired!=="boolean"||(item.status==="APPROVED"&&(!naturalGoalFp(item.approval_fingerprint)||!Number.isFinite(item.approval?.expires_at))))throw Error("会话范围或额度不可信");
    }
    const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");
    const closed=(value,keys)=>value && typeof value==="object" && !Array.isArray(value) && Object.keys(value).sort().join(",")===[...keys].sort().join(",");
    for(const item of body.items){
      const scope=item.scope,v2=scope.version==="natural-activation.v2";
      if(!["natural-activation.v1","natural-activation.v2"].includes(scope.version) || !closed(scope,["version","principal_id","project_id","runtime_id","mode","provider","caps","goals"]) || scope.project_id!==project || !closed(scope.caps,v2?["requests","tokens","output_tokens","ttl_seconds","rpm"]:["requests","tokens","output_tokens","ttl_seconds"]) || scope.caps.output_tokens!==512 || scope.caps.ttl_seconds!==7200 || (v2?scope.caps.rpm!==1:item.submission_available!==false) || !closed(scope.provider,["model","endpoint","quota_subject"]) || scope.provider.model!=="intern-s2" || scope.provider.endpoint!=="https://chat.intern-ai.org.cn/api/v1/chat/completions" || typeof scope.provider.quota_subject!=="string" || !scope.provider.quota_subject || new Set(scope.goals.map(g=>g.kind)).size!==scope.goals.length || new Set(scope.goals.map(g=>g.card_id)).size!==scope.goals.length || item.reserved_tokens<0 || item.reserved_tokens>22000 || item.charged_kinds.length!==item.charged_requests || item.charged_kinds.some(k=>!scope.goals.some(g=>g.kind===k)))throw Error("未知或越界的冻结会话scope");
      for(const goal of scope.goals){
        if(!closed(goal,["kind","card_id","expected_version","expected_fingerprint","snapshot","resource_id","resource_hash"]) || !Number.isSafeInteger(goal.expected_version) || goal.expected_version<1 || !/^res_[a-f0-9]{32}$/.test(goal.resource_id) || goal.resource_hash!=="5c21ed898ea8068472098586cc8daea6ab2f64030af6fc1f24937976ba34d66e" || await digest(goal.snapshot)!==goal.expected_fingerprint)throw Error("冻结目标来源或版本不可信");
      }
      if(await digest(scope)!==item.scope_fingerprint || (item.approval!==null && await digest(item.approval)!==item.approval_fingerprint))throw Error("冻结会话内容与指纹不匹配");
    }
    if(!current())return;
    const prior=naturalActivationSelection;
    naturalActivationRows=body.items;
    $("natural-activation-select").replaceChildren(new Option("未选择；沿用默认关闭的普通规划",""),...body.items.map(r=>new Option(`${r.scope.mode} · ${r.status} · ${r.id}`,r.id)));
    if(prior){const row=body.items.find(r=>r.id===prior.row.id && r.scope_fingerprint===prior.row.scope_fingerprint && r.approval_fingerprint===prior.row.approval_fingerprint);if(!row)throw Error("原会话绑定已变化");naturalActivationSelection={identity,project,row};$("natural-activation-select").value=row.id;}
    naturalActivationBlocked=false;renderNaturalActivation();
  } catch(error){if(current()){naturalActivationRows=[];naturalActivationBlocked=true;$("natural-activation-select").replaceChildren(new Option("读取失败；请重新核对",""));$("natural-activation-goals").replaceChildren();$("natural-activation-status").textContent=`会话读取失败：${error.message}。不会自动改用普通规划。`;renderNaturalGoalControls();}}
}
$("natural-activation-refresh").onclick=safe(refreshNaturalActivations);
$("natural-activation-select").onchange=()=>{
  const row=naturalActivationRows.find(r=>r.id===$("natural-activation-select").value);
  naturalGoalGeneration++;naturalActivationGeneration++;naturalGoalAcknowledgements.clear();
  naturalGoalDisplayed=null;activeRun=null;runSelectionGeneration++;clearRunDetail();
  naturalActivationSelection=row?{identity:token,project:$("project-select").value,row}:null;
  naturalActivationBlocked=false;renderNaturalActivation();
};

// Receipt-only candidate: this does not turn a PARTIAL Run into a successful task.
const naturalReceiptIntents=new Map(), naturalReceiptChoices=new Map();
async function renderNaturalReceiptCandidate(r,id,current){
  if(!current() || !["PARTIAL","SUCCEEDED"].includes(r.status) || !r.contract?.snapshot?.natural_planning?.activation)return;
  const section=document.createElement("section");section.id="natural-receipt-candidate";
  $("result").append(section);
  const whole=r.status==="SUCCEEDED" && r.result?.task_acceptance?.whole_task_accepted===true;
  section.append(row(whole?"固定合成目标契约 PASS；来源 Run SUCCEEDED。人工适用范围 PENDING，候选未验收，完整 P-B 未验收。":"单项可信回执可形成待验收候选；来源 Run PARTIAL，整体目标 NOT_RUN，完整 P-B 未验收。"));
  const key=JSON.stringify([token,$("project-select").value,id]);
  let options;
  try {options=await api(`/api/runs/${id}/receipt-candidate-options`);}
  catch(error){if(current())section.append(row(`不能提取此回执：${error.message}`));return;}
  if(!current())return;
  section.append(row("变量：创建时绑定已有授权新 CSV；运行时 column。稳定逻辑：aggregate_csv@1 只读求和；适用范围须人工核对，不代表模型泛化。"));
  const select=document.createElement("select");select.id="natural-receipt-target";
  for(const target of options.targets){const choice=document.createElement("option");choice.value=target.id;choice.textContent=target.name;select.append(choice);}
  const name=document.createElement("input");name.id="natural-receipt-name";name.maxLength=200;
  const saved=naturalReceiptChoices.get(key);if(saved && options.targets.some(t=>t.id===saved.target))select.value=saved.target;
  name.value=saved?.name||"可信求和回执候选（未验收）";
  const remember=()=>naturalReceiptChoices.set(key,{target:select.value,name:name.value});select.onchange=remember;name.oninput=remember;
  section.append(select,name);
  const intent=naturalReceiptIntents.get(key),button=document.createElement("button");button.id="natural-receipt-extract";
  button.textContent=intent?.state==="unknown"?"显式恢复原候选请求":intent?.state==="accepted"?"打开已保存候选":"保存单项回执候选（未验收）";
  button.disabled=intent?.state==="sending";select.disabled=Boolean(intent);name.disabled=Boolean(intent);
  if(intent?.state==="accepted")section.append(row("候选已保存；源 Run 状态及验收不改变。"));
  if(intent?.state==="unknown")section.append(row("接受结果 UNKNOWN；只恢复原指纹、目标和请求键，不自动重发。"));
  button.onclick=safe(async()=>{
    if(!current())return;
    let entry=naturalReceiptIntents.get(key);
    if(entry?.state==="sending")return;
    if(entry?.state==="accepted"){
      if(await showApp(entry.id))selectWorkspace("apps");return;
    }
    if(!entry){
      const target=options.targets.find(t=>t.id===select.value);
      if(!target || !name.value.trim())return;
      entry={state:"new",body:{expected_proof_fingerprint:options.source_proof_fingerprint,
        target_app_id:target.id,expected_target_draft_fingerprint:target.fingerprint,
        name:name.value.trim(),request_key:crypto.randomUUID()}};
      naturalReceiptIntents.set(key,entry);
    }
    entry.state="sending";button.disabled=true;select.disabled=true;name.disabled=true;
    try {
      const made=await api(`/api/runs/${id}/receipt-candidates`,"POST",entry.body);
      const fields=["state","publishable","formal_publication_enabled","whole_task_accepted","source_run_status","semantic_goal_acceptance","owner_acceptance","generator","model_requests","id","candidate_fingerprint","cached","source_proof_fingerprint"];
      if(!made || Object.keys(made).sort().join()!==fields.sort().join() ||
          made.state!=="CANDIDATE_ONLY" || made.whole_task_accepted!==whole || made.source_run_status!==r.status ||
          made.publishable!==false || made.formal_publication_enabled!==false || made.semantic_goal_acceptance!=="NOT_RUN" ||
          made.owner_acceptance!=="PENDING" || made.model_requests!==0 || typeof made.cached!=="boolean" ||
          made.generator!=="TRUSTED_OFFLINE_RECEIPT_CANDIDATE.v1" || !/^app_[a-f0-9]{32}$/.test(made.id) ||
          !naturalGoalFp(made.candidate_fingerprint) || made.source_proof_fingerprint!==entry.body.expected_proof_fingerprint)throw Error("候选回执范围不匹配");
      if(!current()){entry.state="unknown";return;}
      const draft=await api(`/api/apps/${made.id}`);
      if(!current()){entry.state="unknown";return;}
      const digest=async value=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");
      const lineage=draft.candidate?.task_proof;
      if(draft.id!==made.id || draft.project_id!==$("project-select").value || draft.fingerprint!==made.candidate_fingerprint ||
          await digest(draft.candidate)!==made.candidate_fingerprint || draft.candidate.manifest.source_run_ref!==id ||
          lineage?.generator!==made.generator || lineage.proof_fingerprint!==entry.body.expected_proof_fingerprint ||
          await digest(lineage.proof)!==entry.body.expected_proof_fingerprint ||
          lineage.target.app_id!==entry.body.target_app_id || lineage.target.fingerprint!==entry.body.expected_target_draft_fingerprint ||
          lineage.proof.source_run_status!==r.status || lineage.proof.whole_task_accepted!==whole ||
          lineage.proof.semantic_goal_acceptance!=="NOT_RUN" || lineage.proof.owner_acceptance!=="PENDING")throw Error("保存候选与冻结回执来源不匹配");
      if(!current()){entry.state="unknown";return;}
      entry.id=made.id;entry.state="accepted";
    } catch(error){entry.state="unknown";}
    if(current())await showRun(id);
  });section.append(button);
}

// P-A exact trial preparation and consent.
"use strict";
// Only original keys and transient page state; never model/Run submission.
const trialEntries = new Map();
let trialGeneration = 0, trialCards = [];
const trialContext = () => ({identity: token, connection: identityConnectionGeneration, project: $("project-select").value, generation: trialGeneration});
const trialCurrent = c => c.identity === token && c.connection === identityConnectionGeneration && c.project === $("project-select").value && c.generation === trialGeneration;
const trialIndex = c => JSON.stringify([c.identity, c.project]);
function updateTrialAddress(project, key, expectedKey = null) {
  const url = new URL(location.href), params = new URLSearchParams(url.hash.slice(1));
  if (key) { params.set("trial-project", project); params.set("trial-key", key); }
  else {
    if (params.get("trial-project") !== project || params.get("trial-key") !== expectedKey) return;
    params.delete("trial-project"); params.delete("trial-key");
  }
  url.hash = params.toString();
  history.replaceState(history.state, "", url);
}
function trialHistoryChanged() {
  const ctx = trialContext(), entry = trialEntry(), params = new URLSearchParams(location.hash.slice(1));
  const key = params.get("trial-project") === ctx.project ? params.get("trial-key") : null;
  const valid = /^[A-Za-z0-9_-]{1,100}$/.test(key || "");
  const preserve = entry && (!valid || (["sending", "unknown", "unapproved"].includes(entry.state) && entry.key !== key));
  clearTrialConsent();
  if (!ctx.identity || !ctx.project) return;
  if (preserve) {
    updateTrialAddress(ctx.project, entry.key);
    entry.message = "历史地址不能替换未恢复的原键；只读取当前原键恢复。";
  } else if (valid) {
    trialEntries.set(trialIndex(ctx), {key, base: `/api/projects/${ctx.project}/natural-trials/${key}`, operation: 0, state: "unknown", receipt: null, message: "历史地址仅恢复原键意图；先只读取原键，不自动提交。"});
  }
  $("trial-original-key").value = trialEntry()?.key || "";
  renderTrialConsent();
}
function clearTrialConsent() {
  trialGeneration++; trialCards = [];
  for (const entry of trialEntries.values()) { entry.operation = (entry.operation || 0) + 1; entry.receipt = null; if (["known", "sending", "unapproved", "closed"].includes(entry.state)) entry.state = "unknown"; }
  $("trial-ack").checked = false; $("trial-withdraw-ack").checked = false; $("trial-end-ack").checked = false;
  $("trial-scope").textContent = ""; $("trial-source").replaceChildren(); $("trial-cold").replaceChildren();
  $("trial-status").textContent = "读取两张已保存的完整目标卡，准备七槽同意范围。LIVE 仍关闭。";
  $("trial-original-key").value = trialEntry()?.key || "";
  renderTrialConsent();
}
function trialEntry() { return trialEntries.get(trialIndex(trialContext())); }
const trialReviewDeadline = c => c?.namespace === "natural-live-trial.v2" ? c.review_expires_at : c?.expires_at;
function trialValid(r, key) {
  const c = r?.contract;
  if (r?.status !== "PREPARED_LIVE_BLOCKED" || r.path !== "P-A" || r.live_allowed !== false || r.new_runs !== 0 || r.new_slots !== 0 || r.actual_model_requests !== 0 || !/^[a-f0-9]{64}$/.test(r.review_token) || c?.trial_key !== key || c.project_id !== $("project-select").value || !Array.isArray(c.bindings) || c.bindings.length !== 2 || !Number.isFinite(c.expires_at) || typeof r.approved !== "boolean" || typeof r.revoked !== "boolean" || typeof r.expired !== "boolean") throw Error("未知准备回执");
  if (c.namespace === "natural-live-trial.v2" && (!Number.isFinite(c.prepared_at) || c.review_expires_at !== c.prepared_at + 300 || c.execution_expires_at !== c.prepared_at + 3600 || c.expires_at !== c.execution_expires_at || c.stage_handoff_seconds !== 900 || typeof r.review_expired !== "boolean")) throw Error("未知期限合同");
  return r;
}
function renderTrialConsent() {
  const entry = trialEntry(), r = entry?.receipt, busy = entry?.state === "sending", unknown = ["unknown", "unapproved"].includes(entry?.state);
  const expired = r?.expired || r?.review_expired || (r?.contract && Date.now() >= trialReviewDeadline(r.contract) * 1000);
  $("trial-source").disabled = $("trial-cold").disabled = Boolean(entry);
  $("trial-prepare").disabled = !token || !$("project-select").value || Boolean(entry) || trialCards.length < 2;
  $("trial-consent").disabled = !r?.contract || !$("trial-ack").checked || r.approved || r.revoked || expired || busy || unknown;
  $("trial-withdraw").disabled = !r?.approved || r.revoked || !$("trial-withdraw-ack").checked || busy || unknown;
  $("trial-recover").disabled = busy || !token || !$("project-select").value;
  $("trial-new").disabled = !entry || !(["closed", "rejected"].includes(entry.state) || (entry.state === "known" && r?.approved && r.revoked));
  $("trial-end").disabled = !(entry?.state === "unapproved" || (entry?.state === "known" && r && !r.approved)) || !$("trial-end-ack").checked;
  $("trial-refresh").disabled = busy || unknown;
  if (entry) $("trial-status").textContent = entry.message;
}
function showTrialScope(r) {
  const c = r.contract;
  if (!c) { $("trial-scope").textContent = `仅恢复同意元数据。批准：${r.approved}；撤回：${r.revoked}；过期：${r.expired}。材料不可读取时不展示旧私有范围；仍可明确撤回。LIVE 关闭。`; return; }
  const fields = {title: "名称", goal: "目标", known: "已知", assumptions: "假设", unresolved: "未决项", constraints: "硬条件", acceptance_checks: "验收检查", resource_refs: "绑定材料"};
  const materials = c.bindings.map((b, i) => `${i === 0 ? "生成及 Source" : "未见输入 Cold"}：目标 ${b.card_id} v${b.goal_version}\n材料 ${b.resource_id}（TXT）\n${b.content}\n\n${Object.entries(fields).map(([field, label]) => `${label}：${Array.isArray(b.goal_snapshot.content[field]) ? b.goal_snapshot.content[field].join("\n") : b.goal_snapshot.content[field]}`).join("\n")}`).join("\n\n");
  const cap = c.caps;
  const deadlines = c.namespace === "natural-live-trial.v2" ? `V2 审阅截止 ${new Date(c.review_expires_at * 1000).toISOString()}；执行截止 ${new Date(c.execution_expires_at * 1000).toISOString()}。均从准备时冻结，恢复、批准、重放不续期。总时窗60分钟含5分钟审阅；每个后继阶段须在前序 Run 受理后15分钟内明确批准（含前序最多300秒、排队及人工交接）。每 Run 的300秒含额度等待、模型延迟和工具工作；人工迟到或剩余时间不足即拒绝。不是七槽完成保证。` : "V1 原单一期限保持，不迁移或续期。";
  $("trial-scope").textContent = `P-A 精确准备与同意范围\n${deadlines}\n项目 ${c.project_id}\n身份 ${c.principal_id}\n运行身份 ${c.runtime_id}\n模型 ${c.model}\n端点 ${c.endpoint}\n流式 ${c.stream}\n额度主体 ${c.quota_subject}（尚未配置、未验证免费资格）\n期限 ${new Date(c.expires_at * 1000).toISOString()}（不会因恢复延长）\n生成 ${cap.generate_requests} / Source ${cap.source_requests} / Cold ${cap.cold_requests}，共 ${cap.max_requests} 槽\n每请求输出 ≤${cap.max_output_tokens} tokens；总输出 ≤${cap.total_output_tokens}\n每请求 wire ≤${cap.max_wire_bytes} bytes；响应 ASCII ≤${cap.max_response_ascii_bytes} bytes\n每 Run 预留 ≤${cap.per_run_reserved}；总预留 ≤${cap.total_reserved}\n每 Run ≤${cap.run_seconds} 秒；lease ${cap.lease_seconds} 秒；每分钟 ${cap.requests_per_minute} 请求；付费上限 ${cap.paid_cap}\n阶段键 ${Object.entries(c.stage_keys).map(([k,v]) => `${k}: ${v}`).join("；")}\n批准：${r.approved}；撤回：${r.revoked}；过期：${r.expired}\n\n${materials}\n\n此入口新增 Run / 槽 / 外发均为 0。LIVE 与正式发布保持关闭；不是实际运行或完整 P-A/P-B 验收。`;
}
async function refreshTrialCards() {
  clearTrialConsent();
  const ctx = trialContext(); if (!ctx.identity || !ctx.project) return;
  const result = await api(`/api/projects/${ctx.project}/goal-cards`);
  if (!trialCurrent(ctx)) return;
  trialCards = result.items;
  for (const [id, offset] of [["trial-source", 0], ["trial-cold", 1]]) {
    $(id).replaceChildren(...trialCards.map(c => new Option(`${c.title} · v${c.version}`, c.id)));
    if (trialCards[offset]) $(id).value = trialCards[offset].id;
  }
  $("trial-scope").textContent = ""; $("trial-ack").checked = false; $("trial-withdraw-ack").checked = false; $("trial-end-ack").checked = false;
  const stored = trialEntry();
  if (stored) { $("trial-original-key").value = stored.key; stored.message = "已保留原键。重新读取范围和同意状态后再操作。"; stored.receipt = null; }
  else {
    const params = new URLSearchParams(location.hash.slice(1));
    const key = params.get("trial-key");
    if (params.get("trial-project") === ctx.project && /^[A-Za-z0-9_-]{1,100}$/.test(key || "")) {
      $("trial-original-key").value = key;
      trialEntries.set(trialIndex(ctx), {key, base: `/api/projects/${ctx.project}/natural-trials/${key}`, operation: 0, state: "unknown", receipt: null, message: "冷页保留原准备键；先只读取原键恢复，不能另建准备。"});
    }
  }
  renderTrialConsent();
}
function trialMetadata(r) {
  if (!["PREPARATION_CLOSED_NO_APPROVAL", "PREPARED_NOT_APPROVED", "CONSENT_METADATA_ONLY_LIVE_BLOCKED"].includes(r?.status) || r.live_allowed !== false || r.new_runs !== 0 || r.new_slots !== 0 || r.actual_model_requests !== 0) throw Error("未知状态回执");
  if (r.status === "PREPARED_NOT_APPROVED") { if (r.approved !== false) throw Error("未知未批准状态"); }
  else if (!/^[a-f0-9]{64}$/.test(r.review_token) || (r.status === "PREPARATION_CLOSED_NO_APPROVAL" ? r.approved !== false || !Number.isFinite(r.closed_at) : r.approved !== true || typeof r.revoked !== "boolean" || typeof r.expired !== "boolean")) throw Error("未知终结或批准回执");
  return r;
}
async function trialRead(ctx, entry, operation) {
  let receipt;
  try { const value = await api(`${entry.base}/preparation`); receipt = value.status === "PREPARATION_CLOSED_NO_APPROVAL" ? trialMetadata(value) : trialValid(value, entry.key); }
  catch (error) {
    if (!trialCurrent(ctx) || entry.operation !== operation) return;
    if (![400,403,409].includes(error.httpStatus)) throw error;
    const metadata = await api(`${entry.base}/consent-status`);
    receipt = trialMetadata(metadata);
  }
  if (!trialCurrent(ctx) || entry.operation !== operation) return;
  entry.receipt = receipt; entry.state = receipt.status === "PREPARATION_CLOSED_NO_APPROVAL" ? "closed" : receipt.status === "PREPARED_NOT_APPROVED" ? "unapproved" : "known";
  entry.message = entry.state === "closed" ? "旧准备已永久结束，无批准；可明确开始另一份准备。LIVE 关闭。" : entry.state === "unapproved" ? "原准备当前未批准；须明确永久结束并读取终结回执后，才能开始另一份准备。" : receipt.revoked ? "已恢复原键：批准已撤回，LIVE 关闭。" : receipt.approved ? "已恢复原键：精确批准已持久保存，LIVE 关闭。" : "准备已冻结，请阅读完整范围后明确确认。LIVE 关闭。";
  if (trialCurrent(ctx)) { $("trial-ack").checked = false; $("trial-withdraw-ack").checked = false; $("trial-end-ack").checked = false; showTrialScope(receipt); }
}
async function prepareTrial() {
  const ctx = trialContext(); if (!ctx.identity || !ctx.project || trialEntry()) return;
  const choices = [$("trial-source").value, $("trial-cold").value].map(id => trialCards.find(c => c.id === id));
  if (choices.some(c => !c) || choices[0].id === choices[1].id) throw Error("请选择两张不同的完整目标卡");
  const key = crypto.randomUUID(), entry = {key, base: `/api/projects/${ctx.project}/natural-trials/${key}`, state: "sending", operation: 1, message: "正在准备；不会新增 Run 或发送模型请求。"};
  const operation = entry.operation;
  trialEntries.set(trialIndex(ctx), entry); $("trial-original-key").value = key;
  updateTrialAddress(ctx.project, key);
  renderTrialConsent();
  try {
    const receipt = await api(`${entry.base}/preparation`, "POST", {bindings: choices.map(c => ({card_id: c.id, expected_version: c.version}))});
    if (entry.operation !== operation) return;
    // Validate while current; late replies cannot acknowledge or enable another view.
    if (!trialCurrent(ctx)) { entry.state = "unknown"; entry.message = "页面已切换；只读取原键恢复。"; return; }
    entry.receipt = trialValid(receipt, key); entry.state = "known"; entry.message = "准备已冻结，请阅读完整范围后明确确认。LIVE 关闭。";
    showTrialScope(entry.receipt);
  } catch (error) { if (entry.operation !== operation) return; const rejected = error.message !== "OUTCOME_UNKNOWN" && Number.isInteger(error.httpStatus) && error.httpStatus >= 400 && error.httpStatus < 500 && ![408,425,429].includes(error.httpStatus); entry.state = rejected ? "rejected" : "unknown"; entry.receipt = null; entry.message = rejected ? `准备明确被拒绝：${error.message}。可修正目标或授权后明确开始另一份准备。` : `准备结果未确认：${error.message}。只读取原键恢复，不自动另建。`; }
  finally { if (trialCurrent(ctx)) renderTrialConsent(); }
}
async function recoverTrial() {
  const ctx = trialContext(), key = $("trial-original-key").value.trim();
  if (!ctx.identity || !ctx.project || !/^[A-Za-z0-9_-]{1,100}$/.test(key)) throw Error("请输入原准备键");
  let entry = trialEntry();
  if (entry?.state === "sending") return;
  if (["unknown", "unapproved"].includes(entry?.state) && entry.key !== key) throw Error("未知结果必须先读取原键");
  if (!entry || entry.key !== key) entry = {key, base: `/api/projects/${ctx.project}/natural-trials/${key}`};
  const operation = entry.operation = (entry.operation || 0) + 1;
  updateTrialAddress(ctx.project, key);
  trialEntries.set(trialIndex(ctx), entry); entry.state = "sending"; entry.message = "只读取原键…"; entry.receipt = null;
  $("trial-ack").checked = false; $("trial-withdraw-ack").checked = false; $("trial-end-ack").checked = false; $("trial-scope").textContent = ""; renderTrialConsent();
  try { await trialRead(ctx, entry, operation); }
  catch (error) { if (entry.operation !== operation) return; entry.state = "unknown"; entry.message = `原键读取未确认：${error.message}。不提交新请求。`; }
  finally { if (trialCurrent(ctx)) renderTrialConsent(); }
}
async function mutateTrial(withdraw = false) {
  const ctx = trialContext(), entry = trialEntry(), r = entry?.receipt;
  if (!r || entry.state !== "known" || (withdraw ? !$("trial-withdraw-ack").checked || !r.approved || r.revoked : !$("trial-ack").checked || !r.contract || r.approved || r.revoked || r.expired || r.review_expired || Date.now() >= trialReviewDeadline(r.contract) * 1000)) return;
  const operation = entry.operation = (entry.operation || 0) + 1;
  entry.state = "sending"; entry.message = withdraw ? "正在撤回原批准…" : "正在保存此精确范围的批准；LIVE 关闭…"; renderTrialConsent();
  try {
    const response = await api(`${entry.base}/${withdraw ? "withdrawal" : "consent"}`, "POST", {review_token: r.review_token, [withdraw ? "confirm_withdrawal" : "confirm_exact_scope"]: true});
    if (entry.operation !== operation) return;
    if (response.live_allowed !== false || response.actual_model_requests !== 0 || response.status !== (withdraw ? "REVOKED" : "EXACT_APPROVAL_RECORDED_LIVE_BLOCKED") || (!withdraw && response.contract_fingerprint !== r.review_token)) throw Error("未知同意回执");
    if (!trialCurrent(ctx)) { entry.receipt = null; entry.state = "unknown"; entry.message = "页面已切换；只读取原键恢复。"; return; }
    await trialRead(ctx, entry, operation);
  } catch (error) { if (entry.operation !== operation) return; entry.receipt = null; entry.state = "unknown"; entry.message = `结果未确认：${error.message}。只能读取原键，不重发批准或撤回。`; if (trialCurrent(ctx)) $("trial-scope").textContent = ""; }
  finally { if (trialCurrent(ctx)) { $("trial-ack").checked = false; $("trial-withdraw-ack").checked = false; $("trial-end-ack").checked = false; renderTrialConsent(); } }
}
async function endTrialPreparation() {
  const ctx = trialContext(), entry = trialEntry();
  if (!(entry?.state === "unapproved" || (entry?.state === "known" && entry.receipt && !entry.receipt.approved)) || !$("trial-end-ack").checked) return;
  const operation = entry.operation = (entry.operation || 0) + 1;
  entry.state = "sending"; entry.receipt = null; entry.message = "正在永久结束旧准备…"; renderTrialConsent();
  try {
    const value = trialMetadata(await api(`${entry.base}/end-preparation`, "POST", {confirm_end: true}));
    if (value.status !== "PREPARATION_CLOSED_NO_APPROVAL") throw Error("未知结束回执");
    if (!trialCurrent(ctx) || entry.operation !== operation) return;
    await trialRead(ctx, entry, operation);
  } catch (error) { if (entry.operation !== operation) return; entry.state = "unknown"; entry.message = `结束结果未确认：${error.message}。只读取原键恢复，不重发。`; }
  finally { if (trialCurrent(ctx)) { $("trial-end-ack").checked = false; renderTrialConsent(); } }
}
$("trial-end").onclick = safe(endTrialPreparation);
$("trial-end-ack").onchange = renderTrialConsent;
$("trial-refresh").onclick = safe(refreshTrialCards);
$("trial-prepare").onclick = safe(prepareTrial);
$("trial-recover").onclick = safe(recoverTrial);
$("trial-consent").onclick = safe(() => mutateTrial());
$("trial-withdraw").onclick = safe(() => mutateTrial(true));
$("trial-ack").onchange = renderTrialConsent;
$("trial-withdraw-ack").onchange = renderTrialConsent;
$("trial-source").onchange = $("trial-cold").onchange = () => { $("trial-ack").checked = false; renderTrialConsent(); };
$("trial-new").onclick = safe(() => {
  const ctx = trialContext(), entry = trialEntry();
  if (!entry || !(["closed", "rejected"].includes(entry.state) || (entry.state === "known" && entry.receipt?.approved && entry.receipt.revoked))) return;
  entry.operation = (entry.operation || 0) + 1;
  updateTrialAddress(ctx.project, null, entry.key);
  trialEntries.delete(trialIndex(ctx));
  clearTrialConsent();
});
window.addEventListener("popstate", trialHistoryChanged);
window.addEventListener("hashchange", trialHistoryChanged);
setInterval(renderTrialConsent, 1000);
