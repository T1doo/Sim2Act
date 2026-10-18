"use strict";
// Human choices are explicit declarations, scoped to the immutable server preview.
let ownerView=null, ownerGeneration=0, ownerEditGeneration=0;
const ownerPending=new Map();
const ownerPerRun=view=>view?.perRun??!!view?.spec;
async function ownerHash(value){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");}
function ownerKey(view){return JSON.stringify([view.token,view.project,view.iid,...(ownerPerRun(view) ? [view.connection,view.rid] : [])]);}
function ownerEndpoint(view){return `/api/internal/instances/${view.iid}/${ownerPerRun(view) ? "runs/"+encodeURIComponent(view.rid)+(view.workflow?"/text-owner-review":"/spec-owner-review") : "owner-review"}`;}
function ownerCurrent(view){return ownerView===view && (!ownerPerRun(view) || view.connection===identityConnectionGeneration) && engineeringCurrent(view.engineering) && view.engineering.instanceGeneration===view.instanceGeneration && view.engineering.instance?.id===view.iid;}
function ownerFence(view){
  const generation=ownerGeneration,edit=ownerEditGeneration,workspace=workspaceSelectionGeneration;
  return ()=>ownerCurrent(view) && generation===ownerGeneration && edit===ownerEditGeneration && workspace===workspaceSelectionGeneration;
}
function clearOwnerReview(){
  clearCorrectionView();ownerGeneration++;ownerEditGeneration++;ownerView=null;
  $("owner-panel").hidden=true;$("owner-criteria").replaceChildren();$("owner-proof").textContent="";$("owner-natural-evidence").replaceChildren();
  $("owner-status").textContent="";$("owner-history").textContent="";$("owner-form").hidden=true;
  $("owner-ack").checked=false;$("owner-stop-reason").value="";$("owner-key").value="";
}
function ownerButtons(view){
  if(!ownerCurrent(view))return;
  const pending=ownerPending.get(ownerKey(view)),latest=view.state?.latest;
  $("owner-prepare").disabled=view.busy || !!pending || !(view.state?.content_access||view.state?.prepare_current) || !$("owner-run").value;
  $("owner-submit").disabled=view.busy || !!pending || !$("owner-ack").checked || view.state?.owner_acceptance!=="PENDING" || !view.state?.record;
  $("owner-cancel").disabled=view.busy || !!pending || latest?.kind!=="PREPARE" || !$("owner-stop-reason").value.trim();
  $("owner-revoke").disabled=view.busy || !!pending || latest?.kind!=="DECIDE" || !$("owner-stop-reason").value.trim();
  $("owner-refresh").disabled=view.busy || (ownerPerRun(view) && !view.rid);$("owner-recover").disabled=view.busy || (ownerPerRun(view) && !view.rid) || !$("owner-key").value.trim();
  correctionButtons(view);
}
function ownerEdited(){ownerEditGeneration++;if(ownerView)ownerButtons(ownerView);}
function ownerRender(view,state){
  if(!ownerCurrent(view))return;
  const previous=view.state?.record?.id;view.state=state;
  $("owner-status").textContent=`人工声明 ${state.owner_acceptance} · 序列 ${state.sequence} · 语义 UNKNOWN · 正式发布关闭${state.invalidation_reason ? " · 当前内容不可核验："+state.invalidation_reason : ""}`;
  $("owner-history").textContent=JSON.stringify({latest:state.latest,history:state.history,recovered_receipt:state.recovered ? {id:state.recovered.id,status:state.recovered.status,request_key:state.recovered.request_key,fingerprint:state.recovered.fingerprint} : null},null,2);
  const record=state.record,contract=record?.payload?.contract || state.current || state.prepare_current;
  $("owner-proof").textContent=(state.content_access || state.prepare_current) && contract ? JSON.stringify({record_id:record?.id,record_fingerprint:record?.fingerprint,expires_at:record?.payload?.expires_at,contract,choices:record?.payload?.choices},null,2) : "当前仅可读取本人停止控制元数据；历史回执不代表当前版本仍获签收。";
  $("owner-natural-evidence").replaceChildren();
  $("owner-proof").closest("details").open=!view.workflow;
  if(view.workflow && state.content_access && contract?.output)renderTextWorkflowReport($("owner-natural-evidence"),contract);
  if(view.spec && state.content_access && contract?.output?.checklist){
    renderSpecChecklist($("owner-natural-evidence"),contract.output.checklist);
    if(contract.human_correction){
      const title=document.createElement("h4");title.textContent=`原结果 v${contract.human_correction.reference.base_data_version} 的修正问题 → 本结果 v${contract.result_version}，仍须逐项人工判断`;
      $("owner-natural-evidence").append(title);
      for(const issue of contract.human_correction.issues){const text=document.createElement("p");text.textContent=`${issue.item_id} · 原标准：${issue.criterion} · 原要求修正的理由：${issue.reason} · 本结果的同一标准待重新判定（不声明已修复）`;$("owner-natural-evidence").append(text);}
    }
  }
  const canDecide=state.content_access && state.owner_acceptance==="PENDING" && record?.kind==="PREPARE";
  $("owner-form").hidden=!canDecide;
  if(!canDecide || record.id!==previous){
    $("owner-criteria").replaceChildren();$("owner-ack").checked=false;
    if(canDecide)for(const item of contract.items){
      const group=document.createElement("fieldset"),legend=document.createElement("legend");legend.textContent=`${item.id}：${item.text}`;group.append(legend);
      const select=document.createElement("select");select.id="owner-choice-"+item.id;select.dataset.itemId=item.id;select.required=true;
      select.append(new Option("请逐项手动判定",""),new Option("接受此项","ACCEPT"),new Option(view.spec ? "要求修正此项" : "拒绝此项","REJECT"));
      const reason=document.createElement("textarea");reason.id="owner-reason-"+item.id;reason.required=true;reason.maxLength=500;reason.setAttribute("aria-label",item.id+" 判定依据");
      select.oninput=ownerEdited;select.onchange=ownerEdited;reason.oninput=ownerEdited;reason.onchange=ownerEdited;group.append(select,reason);$("owner-criteria").append(group);
    }
  }
  ownerButtons(view);
}
function ownerSame(a,b){return goalRunCanonical(a)===goalRunCanonical(b);}
function ownerScope(view,value){
  return value?.principal_id===view.principal && value.project_id===view.project && value.instance_id===view.iid;
}
function ownerContract(view,value){
  return ownerScope(view,value) && value.app_id===view.app && value.version===(view.csv ? "owner.csv-sum.v1" : view.workflow ? "owner.text-four-step.v1" : view.spec ? "owner.natural-spec.v1" : "owner.generated-text.v1") && (!ownerPerRun(view) || value.run_id===view.rid) && value.formal_publication_enabled===false && value.technical_semantic_status==="UNKNOWN";
}
async function ownerValidate(view,state,key,current){
  const invalid=()=>{throw Error("签收读取身份、序列或回执绑定不一致");};
  if(!ownerContract(view,state) || !Number.isSafeInteger(state.sequence) || state.sequence<0 || state.sequence>256 || !Array.isArray(state.history) || state.history.length!==state.sequence || typeof state.content_access!=="boolean")invalid();
  const ids=new Set(),keys=new Set(),hash=/^[a-f0-9]{64}$/;
  let previous="";
  for(const [index,row] of state.history.entries()){
    if(!ownerScope(view,row) || (ownerPerRun(view) && row.run_id!==view.rid) || row.sequence!==index+1 || !row.id || ids.has(row.id) || !row.request_key || keys.has(row.request_key) || !hash.test(row.fingerprint) || !hash.test(row.request_fingerprint) || row.previous_fingerprint!==previous || !({PREPARE:["PENDING"],DECIDE:["ACCEPTED","REJECTED"],CANCEL:["CANCELLED"],REVOKE:["REVOKED"]}[row.kind]||[]).includes(row.status))invalid();
    ids.add(row.id);keys.add(row.request_key);previous=row.fingerprint;
  }
  if(!ownerSame(state.latest,state.history.at(-1)||null))invalid();
  if(view.state && (state.sequence<view.state.sequence || !ownerSame(state.history.slice(0,view.state.sequence),view.state.history)))invalid();
  if(state.content_access ? !ownerContract(view,state.current) : !!(state.current || state.record))invalid();
  if(state.prepare_current && (!ownerContract(view,state.prepare_current)||state.prepare_current.declaration_scope!=="EXACT_OWN_GOAL_RELEASE_INSTANCE_WORKER_EVIDENCE"||!state.prepare_current.own_goal_binding_fingerprint||state.prepare_current.source_goal?.origin!=="THIS_APPLICATION_OWNER_AUTHORED"))invalid();
  const last=state.latest,status=state.owner_acceptance;
  const expected=last ? last.status : "PENDING";
  if(!state.content_access && last && !["CANCEL","REVOKE"].includes(last.kind) && status!=="STALE")invalid();
  if(status!==expected && !(status==="STALE" && last && !state.content_access && !["CANCEL","REVOKE"].includes(last.kind)) && !(status==="EXPIRED" && last?.kind==="PREPARE" && state.content_access))invalid();
  const active=state.content_access && last && ["PREPARE","DECIDE"].includes(last.kind);
  if(!!state.record!==!!active)invalid();
  for(const [record,row] of [[state.record,active ? last : null],[state.recovered,key ? state.history.find(row=>row.request_key===key) : null]]){
    if(!record && !row)continue;
    if(!record || !row)invalid();
    const {payload,...metadata}=record;
    if(!ownerSame(metadata,row))invalid();
    if(payload){
      const {fingerprint,...unsigned}=row;
      if(!state.content_access || !ownerSame(payload.metadata,unsigned) || payload.request?.command!==row.kind || payload.request.request_key!==row.request_key || payload.request.expected_sequence!==row.sequence-1 || (payload.contract && !ownerContract(view,payload.contract)))invalid();
      const requestHash=await ownerHash(payload.request);
      if(!current())return false;
      if(requestHash!==row.request_fingerprint)invalid();
      if(ownerPerRun(view)){const payloadHash=await ownerHash(payload);if(!current())return false;
        if(payloadHash!==row.fingerprint || (record===state.record && !ownerSame(payload.contract,state.current)))invalid();}
    }else if(record===state.record)invalid();
  }
  if(view.workflow && state.content_access && !await textWorkflowOwnerContract(view,state.current,current))return false;
  return current();
}
async function ownerRead(view,key=null){
  const fence=ownerFence(view),generation=++view.readGeneration;
  const current=()=>fence() && generation===view.readGeneration;
  try{
    const state=await api(`${ownerEndpoint(view)}${key ? "?request_key="+encodeURIComponent(key) : ""}`);
    if(!current() || !await ownerValidate(view,state,key,current) || !current())return false;
    const pending=ownerPending.get(ownerKey(view));
    if(key && pending?.request_key===key){
      const requestHash=await ownerHash(pending);
      if(!current())return false;
      if(state.recovered.request_fingerprint!==requestHash)throw Error("原请求回执绑定不一致");
      ownerPending.delete(ownerKey(view));
    }
    ownerRender(view,state);return true;
  }catch(error){if(!current())return false;throw error;}
}
async function openOwnerReview(engineeringView){
  clearOwnerReview();
  const instance=engineeringView.instance;if(!instance || !engineeringCurrent(engineeringView))return;
  const view={engineering:engineeringView,instanceGeneration:engineeringView.instanceGeneration,token,project:engineeringView.project,principal:instance.principal_id,app:engineeringView.app,iid:instance.id,connection:identityConnectionGeneration,spec:!!engineeringView.spec,workflow:!!engineeringView.workflow,perRun:!!(engineeringView.spec||engineeringView.workflow),rid:null,state:null,busy:false,readGeneration:0};
  ownerView=view;$("owner-panel").hidden=false;
  $("correction-key").value=correctionPending.get(ownerKey(view))?.key||"";
  $("owner-run").replaceChildren(new Option("手动选择已完成的新输入任务",""),...instance.runs.filter(run=>run.status==="SUCCEEDED").map(run=>new Option(`${run.id} · 结果 v${run.result_version}`,run.id)));
  const pending=ownerPending.get(ownerKey(view));if(pending)$("owner-key").value=pending.request_key;
  ownerButtons(view);
  if(ownerPerRun(view)){$("owner-status").textContent=view.workflow?"请选择具体成功 Run，阅读两次检索的完整引用与报告，再逐项人工判断。PARTIAL 不产生可验收报告，新结果不继承历史声明。":"请选择具体成功结果，阅读原文、条件、例外和未决项后，明确接受或要求修正。新结果不继承历史声明。";return;}
  const current=ownerFence(view),reading=ownerRead(view),readGeneration=view.readGeneration;
  try{await reading;}catch(error){if(current() && readGeneration===view.readGeneration)$("owner-status").textContent=`当前签收记录无法读取：${error.detail || error.message}`;}
  ownerButtons(view);
}
async function ownerAction(body){
  const view=ownerView;if(!view || !ownerCurrent(view) || view.busy || ownerPending.has(ownerKey(view)))return;
  if(!view.state || (ownerPerRun(view) && !view.rid))return;
  if(ownerPerRun(view) && body.command==="DECIDE" && body.choices.some(x=>!["ACCEPT","REJECT"].includes(x.decision)||!x.reason.trim()))throw Error("请逐项明确判定并填写依据");
  const request={...body,request_key:crypto.randomUUID(),expected_sequence:view.state.sequence},current=ownerFence(view),scopeKey=ownerKey(view),scope={principal:view.principal,project:view.project,iid:view.iid,rid:view.rid},endpoint=ownerEndpoint(view);
  view.readGeneration++; // A new write intent invalidates every earlier read before POST.
  ownerPending.set(scopeKey,request);$("owner-key").value=request.request_key;
  view.busy=true;ownerButtons(view);$("owner-status").textContent="正在保存精确人工操作；回执未知时仅以原 key 读取恢复。";
  let readGeneration=null;
  try{
    const saved=await api(endpoint+"-requests","POST",request);
    if(!current())return;
    if(saved.formal_publication_enabled!==false || saved.record?.request_key!==request.request_key || saved.record.request_fingerprint!==await ownerHash(request))throw Error("人工回执绑定不一致");
    if(!current())return;
    const reading=ownerRead(view,request.request_key);readGeneration=view.readGeneration;
    await reading;
  }catch(error){
    if(ownerPerRun(view) && readGeneration===null && error.httpStatus>=400 && error.httpStatus<500 && ["INVALID_INPUT","VERSION_CONFLICT","GRANT_REVOKED","PERMISSION_DENIED","RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY"].includes(error.message)){
      const proof=error.submissionRejection;
      const hash=await ownerHash(request);
      if(proof?.namespace===(view.workflow?"text-workflow-owner-submission-rejection.v1":"natural-owner-submission-rejection.v1") && proof.principal_id===scope.principal && proof.project_id===scope.project && proof.instance_id===scope.iid && proof.run_id===scope.rid && proof.request_key===request.request_key && proof.request_fingerprint===hash && proof.acceptance==="NOT_ACCEPTED" && proof.previous_request==="ABSENT" && proof.phase==="TRANSACTION_ROLLED_BACK" && ownerPending.get(scopeKey)===request)ownerPending.delete(scopeKey);
    }
    if(!ownerPerRun(view) && error.httpStatus>=400 && error.httpStatus<500 && ownerPending.get(ownerKey(view))===request)ownerPending.delete(ownerKey(view));
    if(current() && (readGeneration===null || readGeneration===view.readGeneration)){
      $("owner-status").textContent=`操作未确认：${error.detail || error.message}。请手动读取原 key；不会自动重发。`;
    }
  }finally{view.busy=false;if(ownerCurrent(view))ownerButtons(view);else if(ownerPerRun(ownerView) && ownerCurrent(ownerView) && ownerKey(ownerView)===scopeKey)ownerButtons(ownerView);}
}
$("owner-prepare").onclick=safe(async()=>{
  const view=ownerView;if(!(view?.state?.content_access||view?.state?.prepare_current))return;
  if(ownerPerRun(view)){const fence=ownerFence(view),snapshot=view.state.current,rid=view.rid;
    const hash=await ownerHash(snapshot);if(!fence()||view.rid!==rid||view.state.current!==snapshot)return;
    return ownerAction({command:"PREPARE",expected_contract_fingerprint:hash});}
  return ownerAction({command:"PREPARE",expected_revision:(view.state.current||view.state.prepare_current).instance_revision,expected_release_fingerprint:(view.state.current||view.state.prepare_current).release_fingerprint,run_ids:[$("owner-run").value]});
});
$("owner-form").onsubmit=event=>{event.preventDefault();return safe(()=>{
  const view=ownerView,review=view?.state?.record;if(!review || !$("owner-ack").checked)return;
  const choices=review.payload.contract.items.map(item=>({item_id:item.id,decision:$("owner-choice-"+item.id).value,reason:$("owner-reason-"+item.id).value}));
  return ownerAction({command:"DECIDE",review_id:review.id,review_fingerprint:review.fingerprint,choices});
})();};
for(const [id,command] of [["owner-cancel","CANCEL"],["owner-revoke","REVOKE"]])$(id).onclick=safe(()=>{
  const last=ownerView?.state?.latest;if(!last)return;
  return ownerAction({command,target_id:last.id,target_fingerprint:last.fingerprint,reason:$("owner-stop-reason").value});
});
for(const id of ["owner-run","owner-ack","owner-stop-reason","owner-key"]){$(id).oninput=ownerEdited;$(id).onchange=ownerEdited;}
async function selectOwnerRun(id,engineeringView=engineering){
  const view=ownerView;if(!ownerPerRun(view) || !ownerCurrent(view)||view.engineering!==engineeringView)return;
  if(id&&![...$("owner-run").options].some(option=>option.value===id))throw Error("运行不属于当前人工验收范围");
  if(view.rid===id&&(!view.workflow||!id))return;
  ownerEdited();$("owner-run").value=id;
  clearCorrectionView();ownerGeneration++;view.readGeneration++;view.rid=id;view.state=null;
  $("owner-form").hidden=true;$("owner-criteria").replaceChildren();$("owner-proof").textContent="";
  $("owner-history").textContent="";$("owner-natural-evidence").replaceChildren();$("owner-ack").checked=false;
  $("owner-status").textContent=id?`正在重新鉴权并读取 ${id} 的人工状态…`:"当前未选择可验收的成功运行；历史人工声明不代表本次运行。";
  $("owner-key").value=ownerPending.get(ownerKey(view))?.request_key||"";
  $("correction-key").value=correctionPending.get(ownerKey(view))?.key||"";
  ownerButtons(view);if(!view.rid)return;
  const current=ownerFence(view),reading=ownerRead(view),generation=view.readGeneration;
  try{await reading;}catch(error){if(current()&&generation===view.readGeneration)$("owner-status").textContent=`读取未确认：${error.detail||error.message}`;}
}
$("owner-run").onchange=safe(()=>{
  const view=ownerView,id=$("owner-run").value;
  if(view?.workflow&&id&&ownerCurrent(view)&&view.engineering.run?.id!==id)return showInternalRun(id,view.engineering,view.engineering.instance);
  return selectOwnerRun(id);
});
for(const [id,recover] of [["owner-refresh",false],["owner-recover",true]])$(id).onclick=safe(async()=>{
  const view=ownerView;if(!view || !ownerCurrent(view) || view.busy)return;
  const current=ownerFence(view);view.busy=true;ownerButtons(view);
  const reading=ownerRead(view,recover ? $("owner-key").value.trim() : null),readGeneration=view.readGeneration;
  try{await reading;}catch(error){if(current() && readGeneration===view.readGeneration)$("owner-status").textContent=`读取未确认：${error.detail || error.message}；保留原 key 与人工草稿。`;}
  finally{view.busy=false;if(ownerCurrent(view))ownerButtons(view);}
});

// Application-owned GoalCard authoring; unknown acceptance recovers by original GET.
let appOwnGoalView=null,appOwnGoalGeneration=0,appOwnGoalEdit=0;
const appOwnGoalPending=new Map(),appOwnGoalFields=["title","goal","known","assumptions","unresolved","constraints","acceptance_checks","applicability"];
const appOwnGoalKey=v=>JSON.stringify([v.token,v.project,v.app]);
const appOwnGoalCurrent=v=>!!v&&v===appOwnGoalView&&v.token===token&&v.project===$("project-select").value&&engineeringCurrent(v.engineering)&&v.generation===appOwnGoalGeneration;
function appOwnGoalFence(v){const edit=appOwnGoalEdit,workspace=workspaceSelectionGeneration;return ()=>appOwnGoalCurrent(v)&&edit===appOwnGoalEdit&&workspace===workspaceSelectionGeneration;}
function clearAppOwnGoal(){appOwnGoalGeneration++;appOwnGoalEdit++;appOwnGoalView=null;$("app-own-goal-panel").hidden=true;$("app-own-goal-proof").textContent="";$("app-own-goal-status").textContent="";$("app-own-goal-ack").checked=false;$("app-own-goal-key").value="";for(const f of appOwnGoalFields)$("app-own-goal-"+f).value="";}
function appOwnGoalButtons(v){if(!appOwnGoalCurrent(v))return;const pending=appOwnGoalPending.has(appOwnGoalKey(v));$("app-own-goal-save").disabled=v.busy||pending||!v.state||!$("app-own-goal-ack").checked;$("app-own-goal-read").disabled=v.busy;$("app-own-goal-recover").disabled=v.busy||!$("app-own-goal-key").value.trim();}
async function appOwnGoalValidate(v,value,key,current){
  const bad=()=>{throw Error("自有目标读取身份、版本或回执不一致");},hash=/^[a-f0-9]{64}$/;
  if(value.namespace!=="app-owned-text-goal.v1"||value.anchor?.app_id!==v.app||value.anchor.project_id!==v.project||value.anchor.candidate_fingerprint!==v.engineering.draft.fingerprint||value.anchor.runtime_id!==v.engineering.draft.runtime_id||value.anchor.resource_id!==v.engineering.draft.candidate.manifest.data_bindings[0].resource_ref||value.formal_publication_enabled!==false||value.technical_semantic_status!=="UNKNOWN"||!Number.isSafeInteger(value.sequence)||value.sequence<0||value.sequence>64||!Array.isArray(value.history)||value.sequence!==value.history.length)bad();
  if(v.engineering.instance&&value.anchor.owner_id!==v.engineering.instance.principal_id)bad();
  const keys=new Set();let cid=null;
  for(const [n,row] of value.history.entries()){
    if(row.sequence!==n+1||!row.request_key||keys.has(row.request_key)||!row.card_id||(cid&&cid!==row.card_id)||!Number.isSafeInteger(row.goal_version)||row.goal_version<1||!hash.test(row.goal_fingerprint)||!hash.test(row.binding_fingerprint))bad();keys.add(row.request_key);cid=row.card_id;
  }
  if(v.state&&(value.sequence<v.state.sequence||!ownerSame(value.history.slice(0,v.state.sequence),v.state.history)))bad();
  const last=value.history.at(-1);
  if(last ? value.binding_fingerprint!==last.binding_fingerprint||value.head?.card_id!==last.card_id||!Number.isSafeInteger(value.head.version)||value.head.version<last.goal_version||!hash.test(value.head.fingerprint) : value.binding_fingerprint!==null||value.head!==null)bad();
  if(!["MISSING","CURRENT","STALE"].includes(value.status)||((value.status==="CURRENT")!==!!value.current)||(value.status==="MISSING")!==(value.sequence===0))bad();
  for(const [receipt,row] of [[value.current,value.current?last:null],[value.recovered,key?value.history.find(r=>r.request_key===key):null]]){
    if(!receipt&&!row)continue;if(!receipt||!row||!ownerSame(receipt.anchor,value.anchor)||receipt.namespace!==value.namespace||!hash.test(receipt.request_fingerprint)||!ownerSame(Object.fromEntries(Object.keys(row).map(k=>[k,receipt[k]])),row)||!Array.isArray(receipt.applicability)||!receipt.applicability.length||!ownerSame(receipt.snapshot?.content?.resource_refs,[value.anchor.resource_id]))bad();
    const {binding_fingerprint,...unsigned}=receipt;
    if(await ownerHash(unsigned)!==binding_fingerprint||await ownerHash(receipt.snapshot)!==receipt.goal_fingerprint)bad();if(!current())return false;
    if(receipt===value.current&&(receipt.goal_version!==value.head.version||receipt.goal_fingerprint!==value.head.fingerprint||receipt.snapshot.content.title!==value.head.title))bad();
  }
  return current();
}
async function appOwnGoalRead(v,key=null){
  const fence=appOwnGoalFence(v),reading=++v.readGeneration,current=()=>fence()&&reading===v.readGeneration;
  try{
    const value=await api(`/api/internal/apps/${v.app}/owner-goals${key?"?request_key="+encodeURIComponent(key):""}`);
    if(!current()||!await appOwnGoalValidate(v,value,key,current)||!current())return false;
    if(key){const pending=appOwnGoalPending.get(appOwnGoalKey(v));if(pending?.request_key===key){if(value.recovered.request_fingerprint!==await ownerHash(pending))throw Error("原key目标回执不一致");if(!current())return false;appOwnGoalPending.delete(appOwnGoalKey(v));}}
    v.state=value;$("app-own-goal-proof").textContent=JSON.stringify(value,null,2);$("app-own-goal-status").textContent=`自有目标 ${value.status} · 版本 ${value.head?.version||0} · 签收须新版本下的正常Worker证据；人工声明，语义 UNKNOWN、发布关闭。`;$("app-own-goal-ack").checked=false;appOwnGoalButtons(v);return true;
  }catch(error){if(!current())return false;throw error;}
}
async function openAppOwnGoal(engineeringView){
  clearAppOwnGoal();if(engineeringView.draft.candidate.task_proof?.proof?.kind!=="authorized_data_free_text_logic.v1")return;
  const v={engineering:engineeringView,token,project:engineeringView.project,app:engineeringView.app,generation:appOwnGoalGeneration,busy:false,state:null,readGeneration:0};appOwnGoalView=v;$("app-own-goal-panel").hidden=false;
  const pending=appOwnGoalPending.get(appOwnGoalKey(v));if(pending)$("app-own-goal-key").value=pending.request_key;
  const current=appOwnGoalFence(v),reading=appOwnGoalRead(v),readGeneration=v.readGeneration;
  try{await reading;}catch(e){if(current()&&readGeneration===v.readGeneration)$("app-own-goal-status").textContent=e.message;}
  appOwnGoalButtons(v);
}
function appOwnGoalBody(v){const fields=Object.fromEntries(appOwnGoalFields.map(f=>[f,["title","goal"].includes(f)?$("app-own-goal-"+f).value:$("app-own-goal-"+f).value.split(/\r?\n/).filter(s=>s.trim())]));const {applicability,...goal}=fields;goal.resource_refs=[v.engineering.draft.candidate.manifest.data_bindings[0].resource_ref];return {expected_candidate_fingerprint:v.engineering.draft.fingerprint,expected_goal_version:v.state.head?.version||0,expected_goal_fingerprint:v.state.head?.fingerprint||null,expected_binding_fingerprint:v.state.binding_fingerprint,goal,applicability,consent:"AUTHOR_THIS_APPLICATION_OWN_GOAL_AND_SCOPE",request_key:crypto.randomUUID().replaceAll("-","")};}
$("app-own-goal-form").onsubmit=event=>{event.preventDefault();return safe(async()=>{
  const v=appOwnGoalView;if(!appOwnGoalCurrent(v)||v.busy||appOwnGoalPending.has(appOwnGoalKey(v))||!v.state||!$("app-own-goal-ack").checked)return;
  const body=appOwnGoalBody(v),current=appOwnGoalFence(v);appOwnGoalPending.set(appOwnGoalKey(v),body);$("app-own-goal-key").value=body.request_key;v.readGeneration++;v.busy=true;appOwnGoalButtons(v);
  let readGeneration=null;
  try{
    await api(`/api/internal/apps/${v.app}/owner-goals`,"POST",body);if(!current())return;
    const reading=appOwnGoalRead(v,body.request_key);readGeneration=v.readGeneration;
    const readBack=await reading;
    if(readBack&&current()&&readGeneration===v.readGeneration&&v.engineering.instance)await openOwnerReview(v.engineering);
  }catch(e){
    if(current()&&(readGeneration===null||readGeneration===v.readGeneration)){
      // A failed GET cannot establish that the preceding save had no effect.
      if(readGeneration===null&&e.httpStatus>=400&&e.httpStatus<500&&appOwnGoalPending.get(appOwnGoalKey(v))===body){appOwnGoalPending.delete(appOwnGoalKey(v));v.state=null;}
      $("app-own-goal-status").textContent=`操作未确认 ${e.message}；只读原key，不自动重发。`;
    }
  }finally{v.busy=false;if(appOwnGoalCurrent(v))appOwnGoalButtons(v);}
})();// no automatic retry
};
for(const f of appOwnGoalFields)for(const event of ["input","change"])$("app-own-goal-"+f).addEventListener(event,()=>{appOwnGoalEdit++;ownerEdited();$("app-own-goal-ack").checked=false;$("owner-ack").checked=false;appOwnGoalButtons(appOwnGoalView);});
for(const id of ["app-own-goal-ack","app-own-goal-key"])$(id).onchange=$(id).oninput=()=>appOwnGoalButtons(appOwnGoalView);
for(const [id,recover] of [["app-own-goal-read",false],["app-own-goal-recover",true]])$(id).onclick=safe(async()=>{
  const v=appOwnGoalView;if(!appOwnGoalCurrent(v)||v.busy)return;v.busy=true;appOwnGoalButtons(v);
  const current=appOwnGoalFence(v),reading=appOwnGoalRead(v,recover?$("app-own-goal-key").value.trim():null),readGeneration=v.readGeneration;
  try{await reading;}catch(e){if(current()&&readGeneration===v.readGeneration)$("app-own-goal-status").textContent=e.message;}
  finally{v.busy=false;if(appOwnGoalCurrent(v))appOwnGoalButtons(v);}
});

// A correction is a separate explicit bounded Run; old declarations are immutable.
const correctionPending=new Map();
function clearCorrectionView(){
  $("correction-panel").hidden=true;
  for(const id of ["correction-proof","correction-status","correction-key"])$(id)[id==="correction-key"?"value":"textContent"]="";
  $("correction-ack").checked=false;$("correction-approval").hidden=true;
  if(ownerView)ownerView.correctionReview=null;
}
function correctionButtons(view){
  if(!ownerCurrent(view))return;
  const pending=correctionPending.get(ownerKey(view));
  $("correction-panel").hidden=!view.spec;
  $("correction-prepare").disabled=view.busy||!!pending||view.state?.owner_acceptance!=="REJECTED"||!view.state?.content_access||!!view.state?.current?.human_correction;
  $("correction-submit").disabled=view.busy||!!pending||!view.correctionReview||!$("correction-ack").checked;
  $("correction-recover").disabled=view.busy||!view.rid||!$("correction-key").value.trim();
  $("correction-reset").disabled=view.busy||!!pending;
}
function correctionPath(v){return `/api/internal/instances/${v.iid}/runs/${encodeURIComponent(v.rid)}`;}
async function correctionValidate(v,value,current){
  const {review_fingerprint,...unsigned}=value;
  if(value.namespace!=="natural-spec-correction.v1"||value.principal_id!==v.principal||value.project_id!==v.project||value.instance_id!==v.iid||value.parent_run_id!==v.rid||value.formal_publication_enabled!==false||value.semantic_status!=="UNKNOWN"||value.owner_acceptance!=="PENDING"||value.real_model_allowance!==0||value.proposed_artifact_writes_at_most!==1||value.consent!=="RUN_NEW_BOUNDED_CORRECTION_KEEP_ORIGINAL_GOAL_AND_CRITERIA"||!value.declaration?.payload?.choices?.some(x=>x.decision==="REJECT"))throw Error("修正预览的身份、原拒绝或限额不一致");
  const hash=await ownerHash(unsigned);if(!current())return false;
  if(hash!==review_fingerprint)throw Error("修正预览指纹不一致");
  const payloadHash=await ownerHash(value.declaration.payload);if(!current())return false;
  if(payloadHash!==value.declaration.fingerprint)throw Error("原声明正文指纹不一致");
  const {payload,fingerprint,...metadata}=value.declaration;
  if(!ownerSame(payload.metadata,metadata))throw Error("原声明元数据不一致");
  const candidateHash=await ownerHash(value.effective_candidate);if(!current())return false;
  if(candidateHash!==value.context.effective_plan_fingerprint)throw Error("原实际流程指纹不一致");
  if(value.context.run_id!==v.rid||value.context.instance_id!==v.iid||value.declaration.kind!=="DECIDE"||value.declaration.status!=="REJECTED"||!ownerSame(value.context.items,value.declaration.payload.contract.items)||!ownerSame(value.context.goal,value.declaration.payload.contract.goal))throw Error("修正不能降低原Goal或验收标准");
  return true;
}
function correctionRender(v,value){
  if(!ownerCurrent(v))return;
  v.correctionReview=value;$("correction-approval").hidden=false;$("correction-ack").checked=false;
  $("correction-key").value=value.request_key;
  $("correction-proof").textContent=JSON.stringify({original_goal:value.context.goal,original_criteria:value.context.items,
    rejected_declaration:value.declaration,original_result_version:value.context.result_version,
    material:value.context.material,effective_recipe:value.effective_candidate.spec_recipe,
    effective_plan_fingerprint:value.context.effective_plan_fingerprint,
    proposed_limits:value.proposed_limits,proposed_model_nodes:value.proposed_model_nodes,
    proposed_artifact_writes_at_most:value.proposed_artifact_writes_at_most,real_model_allowance:value.real_model_allowance,
    expires_at:value.expires_at,review_fingerprint:value.review_fingerprint},null,2);
  $("correction-status").textContent="原Goal与全部验收标准保持不变。请核对逐项理由、本次限额与模型节点；确认后仅创建一条新Run，新结果需另行人工判定。真实模型额度0，正式发布关闭。";
  correctionButtons(v);
}
async function correctionRecover(v,key,stage){
  const fence=ownerFence(v),serial=++v.readGeneration,current=()=>fence()&&serial===v.readGeneration;
  const value=await api(correctionPath(v)+(stage==="REVIEW"?"/correction-reviews/":"/correction-requests/")+encodeURIComponent(key));
  if(!current())return false;
  const review=stage==="REVIEW"?value:value.review;
  if(!await correctionValidate(v,review,current)||!current())return false;
  const pending=correctionPending.get(ownerKey(v));
  if(stage==="REVIEW"&&pending?.key===key){
    const contextHash=await ownerHash(review.context);if(!current())return false;
    if(contextHash!==pending.body.expected_context_fingerprint||review.declaration.id!==pending.body.declaration_id||review.declaration.fingerprint!==pending.body.declaration_fingerprint||review.declaration.sequence!==pending.body.expected_owner_sequence)throw Error("原key预览与原请求锚不一致");
  }
  if(review.request_key!==key||(pending&&pending.key===key&&(pending.stage!==stage||pending.body.expected_review_fingerprint&&pending.body.expected_review_fingerprint!==review.review_fingerprint)))throw Error("原key修正回执不一致");
  if(stage==="RUN"&&(value.run_id===v.rid||value.principal_id!==v.principal||value.instance_id!==v.iid||value.parent_run_id!==v.rid||value.request_key!==key||value.formal_publication_enabled!==false||value.semantic_status!=="UNKNOWN"||value.owner_acceptance!=="PENDING"))throw Error("新Run回执绑定不一致");
  if(pending?.key===key)correctionPending.delete(ownerKey(v));
  correctionRender(v,review);
  if(stage==="RUN"){
    v.correctionReview=null;$("correction-approval").hidden=true;
    $("correction-status").textContent=`旧问题来自结果 v${review.context.result_version} · 新Run ${value.run_id} · ${value.status}${value.result_version?" · 新结果 v"+value.result_version:""}。旧成果与声明保留；刷新运行历史选择新结果，再独立人工判定。`;
    $("correction-proof").textContent=JSON.stringify(value,null,2);
  }
  correctionButtons(v);return true;
}
$("correction-prepare").onclick=safe(async()=>{
  const v=ownerView;if(!v?.spec||!ownerCurrent(v)||v.busy||correctionPending.has(ownerKey(v))||v.state?.owner_acceptance!=="REJECTED"||!v.state.content_access||v.state.current.human_correction)return;
  const fence=ownerFence(v),context=v.state.current,decl=v.state.latest,scopeKey=ownerKey(v),endpoint=correctionPath(v),serial=++v.readGeneration;
  const hash=await ownerHash(context);if(!fence()||serial!==v.readGeneration||v.state.current!==context)return;
  const body={request_key:crypto.randomUUID(),expected_owner_sequence:v.state.sequence,declaration_id:decl.id,declaration_fingerprint:decl.fingerprint,expected_context_fingerprint:hash};
  correctionPending.set(scopeKey,{key:body.request_key,stage:"REVIEW",body});$("correction-key").value=body.request_key;v.busy=true;correctionButtons(v);
  try{const value=await api(endpoint+"/correction-reviews","POST",body);
    if(!fence()||serial!==v.readGeneration||!await correctionValidate(v,value,fence)||!fence())return;
    if(value.request_key!==body.request_key||value.declaration.id!==decl.id||value.declaration.fingerprint!==decl.fingerprint||await ownerHash(value.context)!==hash)throw Error("原拒绝预览回执不一致");
    if(!fence())return;correctionPending.delete(scopeKey);correctionRender(v,value);
  }catch(e){if(fence())$("correction-status").textContent=`预览回执未确认：${e.detail||e.message}。保留原key，仅GET恢复。`;}
  finally{v.busy=false;if(ownerCurrent(v))correctionButtons(v);}
});
$("correction-submit").onclick=safe(async()=>{
  const v=ownerView;if(!v?.spec||!ownerCurrent(v)||v.busy||!v.correctionReview||!$("correction-ack").checked||correctionPending.has(ownerKey(v)))return;
  const review=v.correctionReview,scopeKey=ownerKey(v),endpoint=correctionPath(v),rid=v.rid,fence=ownerFence(v);
  const body={request_key:review.request_key,expected_review_fingerprint:review.review_fingerprint,consent:review.consent};
  const pending={key:body.request_key,stage:"RUN",body};correctionPending.set(scopeKey,pending);v.busy=true;v.readGeneration++;correctionButtons(v);
  let reading=false;
  try{const receipt=await api(endpoint+"/correction-runs","POST",body);
    if(!fence())return;if(receipt.run_id===rid||!receipt.run_id)throw Error("新Run回执不一致");
    reading=true;await correctionRecover(v,body.request_key,"RUN");
  }catch(e){
    const proof=e.submissionRejection;
    if(!reading&&e.httpStatus>=400&&e.httpStatus<500&&["INVALID_INPUT","VERSION_CONFLICT","GRANT_REVOKED","PERMISSION_DENIED","RESOURCE_UNAVAILABLE","UNSUPPORTED_CAPABILITY"].includes(e.message)&&proof?.namespace==="internal-run-rejection.v1"&&proof.endpoint==="correction-runs"&&proof.parent_run_id===rid&&proof.principal_id===v.principal&&proof.project_id===v.project&&proof.instance_id===v.iid&&proof.request_key===body.request_key&&proof.acceptance==="NOT_ACCEPTED"&&proof.previous_request==="ABSENT"&&proof.phase==="CORRECTION_TX_ROLLED_BACK"&&proof.request_fingerprint===await ownerHash(body)&&correctionPending.get(scopeKey)===pending)correctionPending.delete(scopeKey);
    if(fence())$("correction-status").textContent=`修正提交未确认：${e.detail||e.message}。未知结果只以原key读取，不自动重发。`;
  }finally{v.busy=false;if(ownerCurrent(v))correctionButtons(v);else if(ownerView&&ownerCurrent(ownerView)&&ownerKey(ownerView)===scopeKey)correctionButtons(ownerView);}
});
$("correction-recover").onclick=safe(async()=>{
  const v=ownerView;if(!v?.spec||!ownerCurrent(v)||v.busy)return;
  const key=$("correction-key").value.trim(),pending=correctionPending.get(ownerKey(v));
  const stage=pending?.key===key?pending.stage:($("correction-recovery-stage").value||"RUN");
  const fence=ownerFence(v);v.busy=true;correctionButtons(v);
  try{await correctionRecover(v,key,stage);}catch(e){if(fence())$("correction-status").textContent=`读取未确认：${e.detail||e.message}；保留原key。`;}
  finally{v.busy=false;if(ownerCurrent(v))correctionButtons(v);}
});
$("correction-reset").onclick=safe(()=>{const v=ownerView;if(!v||v.busy||correctionPending.has(ownerKey(v)))return;clearCorrectionView();correctionButtons(v);});
for(const id of ["correction-ack","correction-key","correction-recovery-stage"]){$(id).oninput=()=>{ownerEdited();if(ownerView)correctionButtons(ownerView);};$(id).onchange=$(id).oninput;}
