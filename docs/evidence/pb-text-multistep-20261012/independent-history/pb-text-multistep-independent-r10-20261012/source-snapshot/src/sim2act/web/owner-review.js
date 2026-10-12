"use strict";
// Human choices are explicit declarations, scoped to the immutable server preview.
let ownerView=null, ownerGeneration=0, ownerEditGeneration=0;
const ownerPending=new Map();
async function ownerHash(value){return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");}
function ownerKey(view){return JSON.stringify([view.token,view.project,view.iid]);}
function ownerCurrent(view){return ownerView===view && engineeringCurrent(view.engineering) && view.engineering.instanceGeneration===view.instanceGeneration && view.engineering.instance?.id===view.iid;}
function ownerFence(view){
  const generation=ownerGeneration,edit=ownerEditGeneration,workspace=workspaceSelectionGeneration;
  return ()=>ownerCurrent(view) && generation===ownerGeneration && edit===ownerEditGeneration && workspace===workspaceSelectionGeneration;
}
function clearOwnerReview(){
  ownerGeneration++;ownerEditGeneration++;ownerView=null;
  $("owner-panel").hidden=true;$("owner-criteria").replaceChildren();$("owner-proof").textContent="";
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
  $("owner-refresh").disabled=view.busy;$("owner-recover").disabled=view.busy || !$("owner-key").value.trim();
}
function ownerEdited(){ownerEditGeneration++;if(ownerView)ownerButtons(ownerView);}
function ownerRender(view,state){
  if(!ownerCurrent(view))return;
  const previous=view.state?.record?.id;view.state=state;
  $("owner-status").textContent=`人工声明 ${state.owner_acceptance} · 序列 ${state.sequence} · 语义 UNKNOWN · 正式发布关闭${state.invalidation_reason ? " · 当前内容不可核验："+state.invalidation_reason : ""}`;
  $("owner-history").textContent=JSON.stringify({latest:state.latest,history:state.history,recovered_receipt:state.recovered ? {id:state.recovered.id,status:state.recovered.status,request_key:state.recovered.request_key,fingerprint:state.recovered.fingerprint} : null},null,2);
  const record=state.record,contract=record?.payload?.contract || state.current || state.prepare_current;
  $("owner-proof").textContent=(state.content_access || state.prepare_current) && contract ? JSON.stringify({record_id:record?.id,record_fingerprint:record?.fingerprint,expires_at:record?.payload?.expires_at,contract,choices:record?.payload?.choices},null,2) : "当前仅可读取本人停止控制元数据；历史回执不代表当前版本仍获签收。";
  const canDecide=state.content_access && state.owner_acceptance==="PENDING" && record?.kind==="PREPARE";
  $("owner-form").hidden=!canDecide;
  if(!canDecide || record.id!==previous){
    $("owner-criteria").replaceChildren();$("owner-ack").checked=false;
    if(canDecide)for(const item of contract.items){
      const group=document.createElement("fieldset"),legend=document.createElement("legend");legend.textContent=`${item.id}：${item.text}`;group.append(legend);
      const select=document.createElement("select");select.id="owner-choice-"+item.id;select.dataset.itemId=item.id;select.required=true;
      select.append(new Option("请逐项手动判定",""),new Option("接受此项","ACCEPT"),new Option("拒绝此项","REJECT"));
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
  return ownerScope(view,value) && value.app_id===view.app && value.version==="owner.generated-text.v1" && value.formal_publication_enabled===false && value.technical_semantic_status==="UNKNOWN";
}
async function ownerValidate(view,state,key,current){
  const invalid=()=>{throw Error("签收读取身份、序列或回执绑定不一致");};
  if(!ownerContract(view,state) || !Number.isSafeInteger(state.sequence) || state.sequence<0 || state.sequence>256 || !Array.isArray(state.history) || state.history.length!==state.sequence || typeof state.content_access!=="boolean")invalid();
  const ids=new Set(),keys=new Set(),hash=/^[a-f0-9]{64}$/;
  let previous="";
  for(const [index,row] of state.history.entries()){
    if(!ownerScope(view,row) || row.sequence!==index+1 || !row.id || ids.has(row.id) || !row.request_key || keys.has(row.request_key) || !hash.test(row.fingerprint) || !hash.test(row.request_fingerprint) || row.previous_fingerprint!==previous || !({PREPARE:["PENDING"],DECIDE:["ACCEPTED","REJECTED"],CANCEL:["CANCELLED"],REVOKE:["REVOKED"]}[row.kind]||[]).includes(row.status))invalid();
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
    }else if(record===state.record)invalid();
  }
  return current();
}
async function ownerRead(view,key=null){
  const fence=ownerFence(view),generation=++view.readGeneration;
  const current=()=>fence() && generation===view.readGeneration;
  try{
    const state=await api(`/api/internal/instances/${view.iid}/owner-review${key ? "?request_key="+encodeURIComponent(key) : ""}`);
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
  if(engineeringView.workflow){$("owner-panel").hidden=false;$("owner-status").textContent="本应用人工签收 PENDING；四步技术核查不替代语义判断。本切片暂不提交此家族的人工声明。";return;}
  const instance=engineeringView.instance;if(!instance || !engineeringCurrent(engineeringView))return;
  const view={engineering:engineeringView,instanceGeneration:engineeringView.instanceGeneration,token,project:engineeringView.project,principal:instance.principal_id,app:engineeringView.app,iid:instance.id,state:null,busy:false,readGeneration:0};
  ownerView=view;$("owner-panel").hidden=false;
  $("owner-run").replaceChildren(new Option("手动选择已完成的新输入任务",""),...instance.runs.filter(run=>run.status==="SUCCEEDED").map(run=>new Option(`${run.id} · 结果 v${run.result_version}`,run.id)));
  const pending=ownerPending.get(ownerKey(view));if(pending)$("owner-key").value=pending.request_key;
  ownerButtons(view);
  const current=ownerFence(view),reading=ownerRead(view),readGeneration=view.readGeneration;
  try{await reading;}catch(error){if(current() && readGeneration===view.readGeneration)$("owner-status").textContent=`当前签收记录无法读取：${error.detail || error.message}`;}
  ownerButtons(view);
}
async function ownerAction(body){
  const view=ownerView;if(!view || !ownerCurrent(view) || view.busy || ownerPending.has(ownerKey(view)))return;
  const request={...body,request_key:crypto.randomUUID(),expected_sequence:view.state.sequence},current=ownerFence(view);
  view.readGeneration++; // A new write intent invalidates every earlier read before POST.
  ownerPending.set(ownerKey(view),request);$("owner-key").value=request.request_key;
  view.busy=true;ownerButtons(view);$("owner-status").textContent="正在保存精确人工操作；回执未知时仅以原 key 读取恢复。";
  let readGeneration=null;
  try{
    const saved=await api(`/api/internal/instances/${view.iid}/owner-review-requests`,"POST",request);
    if(!current())return;
    if(saved.formal_publication_enabled!==false || saved.record?.request_key!==request.request_key || saved.record.request_fingerprint!==await ownerHash(request))throw Error("人工回执绑定不一致");
    if(!current())return;
    const reading=ownerRead(view,request.request_key);readGeneration=view.readGeneration;
    await reading;
  }catch(error){
    if(error.httpStatus>=400 && error.httpStatus<500 && ownerPending.get(ownerKey(view))===request)ownerPending.delete(ownerKey(view));
    if(current() && (readGeneration===null || readGeneration===view.readGeneration)){
      $("owner-status").textContent=`操作未确认：${error.detail || error.message}。请手动读取原 key；不会自动重发。`;
    }
  }finally{view.busy=false;if(ownerCurrent(view))ownerButtons(view);}
}
$("owner-prepare").onclick=safe(()=>{
  const view=ownerView;if(!(view?.state?.content_access||view?.state?.prepare_current))return;
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
