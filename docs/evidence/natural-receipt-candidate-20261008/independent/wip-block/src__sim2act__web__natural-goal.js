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
  if(naturalGoalDisplayed && activeRun===naturalGoalDisplayed){activeRun=null;runSelectionGeneration++;clearRunDetail();}
  naturalGoalDisplayed=null;
  $("natural-goal-config").textContent="先保存并打开目标，再读取当前项目的规划配置。";
  renderNaturalGoalControls();
}
function renderNaturalGoalControls(){
  const card=activeGoalCard,entry=naturalGoalRequests.get(naturalGoalKey());
  const selected=naturalActivationSelection?.row;
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
    entry={endpoint:selected?`/api/natural-activations/${selected.id}/goal-cards/${card.id}/planned-runs`:`/api/projects/${project}/goal-cards/${card.id}/planned-runs`,activation:selected?{activation_id:selected.id,scope_fingerprint:selected.scope_fingerprint,approval_fingerprint:selected.approval_fingerprint}:null,cardId:card.id,snapshot:card.snapshot,body:{expected_version:card.version,expected_fingerprint:card.fingerprint,request_key:crypto.randomUUID()},state:"new",uncertain:false,runId:null};naturalGoalRequests.set(key,entry);
  }
  if(!entry)return;
  if(entry.runId){await readNaturalGoal(entry,current);return;}
  entry.state="sending";entry.message="正在接受规划请求；不会自动确认执行。";renderNaturalGoalControls();
  try {
    const receipt=await api(entry.endpoint,"POST",entry.body);
    if(typeof receipt?.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(receipt.run_id)||receipt.status!=="ACCEPTED"||receipt.goal_card_id!==entry.cardId||receipt.goal_version!==entry.body.expected_version||receipt.goal_fingerprint!==entry.body.expected_fingerprint||receipt.goal_acceptance!=="NOT_RUN"||receipt.candidate_generated!==false||receipt.planning_policy?.require_confirmation!==true)throw Error("未知规划接受回执");
    if(entry.activation && goalRunCanonical(receipt.planning_policy.activation)!==goalRunCanonical(entry.activation))throw Error("会话绑定回执不匹配");
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
  section.append(row(`已通过结构与来源校验；目标语义 NOT_RUN，人工签收 PENDING。保存来源 v${r.contract.snapshot.source_goal_card.version}。`));
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
  if(!current() || r.status!=="PARTIAL" || !r.contract?.snapshot?.natural_planning?.activation)return;
  const section=document.createElement("section");section.id="natural-receipt-candidate";
  $("result").append(section);
  section.append(row("单项可信回执可形成待验收候选；来源 Run PARTIAL，整体目标 NOT_RUN，完整 P-B 未验收。"));
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
      if(made.state!=="CANDIDATE_ONLY" || made.whole_task_accepted!==false || made.source_run_status!=="PARTIAL")throw Error("候选回执范围不匹配");
      entry.id=made.id;entry.state="accepted";
    } catch(error){entry.state="unknown";}
    if(current())await showRun(id);
  });section.append(button);
}
