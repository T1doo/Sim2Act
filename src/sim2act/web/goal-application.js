"use strict";
// Immutable per-intent requests. Unknown POST outcomes recover through keyed GETs only.
const goalApplications=new Map();
let goalApplicationDisplayed=null;
const goalApplicationKey=()=>activeGoalCard ? JSON.stringify([token,$("project-select").value,activeGoalCard.id,activeGoalCard.fingerprint]) : null;
function renderGoalApplicationControls(){
  const key=goalApplicationKey(),entry=goalApplications.get(key);
  const selection=JSON.stringify([identityConnectionGeneration,goalSelectionGeneration,key]);
  if(selection!==goalApplicationDisplayed){goalApplicationDisplayed=selection;$("goal-application-ack").checked=false;if(entry)entry.result=null;}
  $("goal-application-panel").hidden=!activeGoalCard;
  $("goal-application-start").disabled=!key||goalCardLoading||goalCardSaving||!!entry;
  $("goal-application-read").disabled=!entry||!!entry.busy;
  $("goal-application-confirm").disabled=!entry?.result||!!entry.busy||!!entry.confirmBody||!$("goal-application-ack").checked;
  $("goal-application-name").disabled=!!entry?.confirmBody;
  $("goal-application-confirm-read").hidden=!entry?.confirmBody;
  $("goal-application-confirm-read").disabled=!!entry?.busy;
  $("goal-application-proof").textContent=entry?.result ? JSON.stringify({run_id:entry.runId,version:entry.version,...entry.result},null,2) : "";
  $("goal-application-status").textContent=entry?.message||"使用已保存目标；未保存编辑不纳入生成。真实模型调用关闭，语义接受 NOT_RUN。";
}
function goalApplicationCurrent(entry){return goalApplicationKey()===entry.key&&entry.connection===identityConnectionGeneration&&entry.selection===goalSelectionGeneration;}
async function readGoalApplication(entry){
  const run=await api(entry.runId ? `/api/runs/${entry.runId}` : `/api/projects/${entry.project}/goal-cards/${entry.card}/application-runs?request_key=${encodeURIComponent(entry.body.request_key)}`);
  if(!goalApplicationCurrent(entry))return;
  if(entry.runId&&run.id!==entry.runId)throw Error("VERSION_CONFLICT");
  const source=run.contract?.snapshot?.source_goal_card;
  const selected=run.contract?.snapshot?.application_generation;
  if(!/^run_[a-f0-9]{32}$/.test(run.id)||!Number.isSafeInteger(run.version)||run.version<1||!source||source.card_id!==entry.card||source.version!==entry.body.expected_version||source.fingerprint!==entry.body.expected_fingerprint||goalRunCanonical(source.snapshot)!==goalRunCanonical(entry.snapshot)||selected?.version!=="goal-text-application.v1"||selected.live_request_allowance!==0)throw Error("VERSION_CONFLICT");
  if(run.status==="PARTIAL"){
    const result=run.result,candidate=result?.candidate;
    if(result?.goal_acceptance!=="NOT_RUN"||result.semantic_status!=="UNKNOWN"||result.app_created!==false||run.cancel_intent||run.error||!candidate||candidate.manifest?.app_id!==selected.app_id||candidate.actions?.length!==1||candidate.actions[0].action_id!==selected.action_id||candidate.actions[0].executor?.ref!=="text.literal_evidence"||goalRunCanonical(candidate.goal)!==goalRunCanonical(entry.snapshot.content))throw Error("VERSION_CONFLICT");
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(candidate)))),b=>b.toString(16).padStart(2,"0")).join("");
    if(!goalApplicationCurrent(entry))return;
    if(digest!==result.candidate_fingerprint)throw Error("VERSION_CONFLICT");
  }
  $("goal-application-ack").checked=false;
  entry.runId=run.id;entry.version=run.version;entry.result=run.status==="PARTIAL" ? run.result : null;
  if(entry.result)entry.expectedAppId=entry.result.candidate.manifest.app_id;
  entry.message=`${run.status} · ${run.error?.message || (entry.result ? "候选已核查；请查看完整目标、来源和精确指纹后确认。语义 UNKNOWN。" : "尚无可确认候选，当前状态只读展示。")}`;
}
async function goalApplicationAction(entry,operation){
  if(!entry||entry.busy||!goalApplicationCurrent(entry))return;
  entry.busy=true;renderGoalApplicationControls();
  try{await operation();}
  catch(error){if(goalApplicationCurrent(entry)){entry.result=null;$("goal-application-ack").checked=false;entry.message=`${error.message}；保留原请求键，只读恢复回执，不自动重发。`;}}
  finally{entry.busy=false;if(goalApplicationCurrent(entry))renderGoalApplicationControls();}
}
$("goal-application-start").onclick=()=>{
  const card=activeGoalCard,key=goalApplicationKey();if(!card||goalApplications.has(key)||goalCardLoading||goalCardSaving)return;
  const entry={key,project:$("project-select").value,card:card.id,snapshot:structuredClone(card.snapshot),connection:identityConnectionGeneration,selection:goalSelectionGeneration,body:{expected_version:card.version,expected_fingerprint:card.fingerprint,request_key:crypto.randomUUID()},busy:false,result:null,confirmBody:null,message:"正在接受冻结目标…"};
  goalApplications.set(key,entry);$("goal-application-ack").checked=false;
  return goalApplicationAction(entry,async()=>{
    const accepted=await api(`/api/projects/${entry.project}/goal-cards/${entry.card}/application-runs`,"POST",entry.body);
    if(!goalApplicationCurrent(entry))return;
    if(accepted.goal_card_id!==entry.card||accepted.goal_fingerprint!==entry.body.expected_fingerprint||accepted.goal_version!==entry.body.expected_version||!accepted.run_id)throw Error("VERSION_CONFLICT");
    entry.runId=accepted.run_id;await readGoalApplication(entry);
  });
};
$("goal-application-read").onclick=()=>{const entry=goalApplications.get(goalApplicationKey());if(entry&&!entry.busy){entry.connection=identityConnectionGeneration;entry.selection=goalSelectionGeneration;}return goalApplicationAction(entry,()=>readGoalApplication(entry));};
$("goal-application-ack").onchange=renderGoalApplicationControls;
$("goal-application-confirm").onclick=()=>{
  const entry=goalApplications.get(goalApplicationKey());if(!entry?.result||entry.confirmBody||!$("goal-application-ack").checked)return;
  entry.confirmBody={expected_version:entry.version,candidate_fingerprint:entry.result.candidate_fingerprint,request_key:crypto.randomUUID(),name:$("goal-application-name").value};
  return goalApplicationAction(entry,async()=>{
    const saved=await api(`/api/runs/${entry.runId}/confirm-application-candidate`,"POST",entry.confirmBody);
    if(!goalApplicationCurrent(entry))return;
    if(saved.id!==entry.result.candidate.manifest.app_id||saved.state!=="PREVIEW_ONLY")throw Error("VERSION_CONFLICT");
    entry.message=`已确认 ${saved.id}，仅授权冻结材料的读取。`;await refreshApps();
    if(goalApplicationCurrent(entry))await showApp(saved.id,entry.project);
  });
};
$("goal-application-confirm-read").onclick=()=>{
  const entry=goalApplications.get(goalApplicationKey());if(!entry?.confirmBody)return;
  if(!entry.busy){entry.connection=identityConnectionGeneration;entry.selection=goalSelectionGeneration;}
  return goalApplicationAction(entry,async()=>{
    const saved=await api(`/api/runs/${entry.runId}/confirmed-application-candidate?request_key=${encodeURIComponent(entry.confirmBody.request_key)}`);
    if(!goalApplicationCurrent(entry))return;
    const generation=goalApplications.get(entry.key);
    if(saved.id!==entry.expectedAppId||saved.state!=="PREVIEW_ONLY"||generation!==entry)throw Error("VERSION_CONFLICT");
    entry.message=`已只读恢复 ${saved.id}，没有重新发送确认。`;await refreshApps();
    if(goalApplicationCurrent(entry))await showApp(saved.id,entry.project);
  });
};
renderGoalApplicationControls();
