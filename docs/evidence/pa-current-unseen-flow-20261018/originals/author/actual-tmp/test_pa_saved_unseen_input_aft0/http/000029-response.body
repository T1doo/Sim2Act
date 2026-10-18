"use strict";
// Immutable per-intent requests. Unknown POST outcomes recover through keyed GETs only.
const goalSpecFamily=family=>["spec_checklist","natural_spec"].includes(family);
const goalGenerationVersion=family=>family==="natural_spec"?"goal-natural-spec-application.v1":family==="spec_checklist"?"goal-spec-checklist-application.v1":"goal-text-application.v1";
async function verifyNaturalSample(sample,candidate,snapshot){
 const report=sample?.preview,value=report?.checklist,seal=candidate.model_sample_check;
 if(sample.candidate_fingerprint!==await paHash(candidate)||sample.sample_fingerprint!==seal.sample_fingerprint||!Array.isArray(sample.sample_nodes)||await paHash(sample.sample_nodes)!==seal.sample_fingerprint||sample.new_model_requests!==0||sample.project_writes!==0||sample.semantic_status!=="UNKNOWN"||sample.semantic_goal_acceptance!=="NOT_RUN"||report?.citation_status!=="PASS"||report.semantic_status!=="UNKNOWN"||report.semantic_goal_acceptance!=="NOT_RUN"||typeof value?.source_content!=="string")throw Error("VERSION_CONFLICT");
 const source=snapshot.resource_snapshots[0],text=value.source_content,chars=Array.from(text),covered=chars.map(()=>false);
 const sha=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(text))),b=>b.toString(16).padStart(2,"0")).join("");
 if(sha!==candidate.source_hash||sha!==source.hash||goalRunCanonical(value.source)!==goalRunCanonical({resource_id:source.resource_id,hash:sha,format:source.format,revision:1,coordinate_space:"unicode_scalar_index.v1"}))throw Error("VERSION_CONFLICT");
 const items=sample.sample_nodes.flatMap(node=>node.items);
 for(const item of items)for(const cite of item.citations){
  if(!Number.isSafeInteger(cite.start)||!Number.isSafeInteger(cite.end)||cite.start<0||cite.start>=cite.end||cite.end>chars.length||chars.slice(cite.start,cite.end).join("")!==cite.quote)throw Error("VERSION_CONFLICT");
  for(let index=cite.start;index<cite.end;index++)covered[index]=true;
 }
 const uncovered=[];let begin=null;
 for(let index=0;index<=chars.length;index++){
  const missing=index<chars.length&&!covered[index];if(missing&&begin===null)begin=index;
  if(!missing&&begin!==null){const quote=chars.slice(begin,index).join("");if(quote.trim())uncovered.push({start:begin,end:index,quote});begin=null;}
 }
 const expected={check_version:"natural.spec_citations.v1",source:value.source,source_content:text,
  items:items.map(item=>({...item,relation_status:item.targets.length?"MODEL_ASSERTED":["condition","exception"].includes(item.kind)?"UNASSIGNED":"NOT_APPLICABLE",decision_status:item.kind==="open_question"?"OPEN":"NOT_APPLICABLE"})),
  feedback:{check:"natural.spec_citations.v1",citation_status:"PASS",coverage_status:uncovered.length?"PARTIAL":"FULL",uncovered,semantic_status:"UNKNOWN"},
  human_unresolved:snapshot.content.unresolved,source_retention:"EXACT",semantic_goal_acceptance:"NOT_RUN",owner_acceptance:"PENDING"};
 if(goalRunCanonical(value)!==goalRunCanonical(expected)||report.text!==goalRunCanonical(expected))throw Error("VERSION_CONFLICT");
}
const goalApplications=new Map();
let goalApplicationDisplayed=null;
let goalApplicationDraftGeneration=0;
const goalProviderChoices=new Map();
const naturalGenerationReads=new Map(),naturalGenerationAvailability=new Map();
let paBindingState=null;
let goalProviderReadGeneration=0,paBindingSourceReadGeneration=0;
for(const id of [...goalCardFields.map(field=>"goal-card-"+field),"goal-card-resources"]){
  const edited=()=>{goalApplicationDraftGeneration++;renderPaBinding();};
  $(id).addEventListener("input",edited);$(id).addEventListener("change",edited);
}
const goalApplicationKey=()=>activeGoalCard ? JSON.stringify([token,$("project-select").value,activeGoalCard.id,activeGoalCard.fingerprint]) : null;
function renderGoalApplicationControls(){
  const key=goalApplicationKey(),entry=goalApplications.get(key);
  const selection=JSON.stringify([identityConnectionGeneration,goalSelectionGeneration,key]);
  if(selection!==goalApplicationDisplayed){goalApplicationDisplayed=selection;$("goal-provider-select").replaceChildren(new Option("未选择；默认真实请求预算0",""));$("goal-provider-proof").textContent="";$("goal-provider-status").textContent="未选择模型批准。";paBindingState=null;$("pa-binding-source").replaceChildren();$("pa-binding-proof").textContent="";$("pa-binding-ack").checked=false;$("goal-application-ack").checked=false;$("goal-application-write-ack").checked=false;if(entry)entry.result=null;}
  $("goal-application-panel").hidden=!activeGoalCard;
  $("goal-application-start").disabled=!key||goalCardLoading||goalCardSaving||!!entry||naturalGenerationReads.has(key);
  $("goal-application-read").disabled=!entry||!!entry.busy;
  $("goal-application-confirm").disabled=!entry?.result||!!entry.busy||!!entry.confirmBody||!$("goal-application-ack").checked;
  $("goal-application-name").disabled=!!entry?.confirmBody;
  $("goal-application-confirm-read").hidden=!entry?.confirmBody;
  $("goal-application-confirm-read").disabled=!!entry?.busy;
  $("goal-provider-refresh").disabled=!key||!!entry;
  $("goal-provider-select").disabled=!!entry||goalSpecFamily($("goal-application-family").value);
  $("goal-application-family").disabled=!!entry||(naturalFirstGuideCurrent(naturalFirstGuide)&&naturalFirstGuide.stage==="generate");
  const specFamily=goalSpecFamily(entry?.body.family)||(!entry&&goalSpecFamily($("goal-application-family").value));
  $("goal-application-write-label").hidden=!specFamily;
  if(specFamily&&!$("goal-application-write-ack").checked)$("goal-application-confirm").disabled=true;
  renderPaBinding();
  $("goal-application-proof").textContent=entry?.result ? JSON.stringify({run_id:entry.runId,version:entry.version,...entry.result,...(entry.sample ? {protected_sample_preview:entry.sample}: {})},null,2) : "";
  const availability=naturalGenerationAvailability.get(key);
  $("goal-application-status").textContent=entry?.message||(availability?.current()?availability.message:null)||"使用已保存目标；未保存编辑不纳入生成。真实模型调用关闭，语义接受 NOT_RUN。";
  renderNaturalFirstGuide();
}
function goalApplicationCurrent(entry){return goalApplicationKey()===entry.key&&entry.connection===identityConnectionGeneration&&entry.selection===goalSelectionGeneration;}
async function readGoalApplication(entry,acceptedRunId=null){
  const run=await api(entry.runId ? `/api/runs/${entry.runId}` : `/api/projects/${entry.project}/goal-cards/${entry.card}/application-runs?request_key=${encodeURIComponent(entry.body.request_key)}`);
  if(!goalApplicationCurrent(entry))return;
  if((entry.runId&&run.id!==entry.runId)||(acceptedRunId&&run.id!==acceptedRunId))throw Error("VERSION_CONFLICT");
  const source=run.contract?.snapshot?.source_goal_card;
  const selected=run.contract?.snapshot?.application_generation;
  if(!/^run_[a-f0-9]{32}$/.test(run.id)||!Number.isSafeInteger(run.version)||run.version<1||!source||source.card_id!==entry.card||source.version!==entry.body.expected_version||source.fingerprint!==entry.body.expected_fingerprint||goalRunCanonical(source.snapshot)!==goalRunCanonical(entry.snapshot)||selected?.version!==(goalGenerationVersion(entry.body.family))||selected.live_request_allowance!==0)throw Error("VERSION_CONFLICT");
  if(goalRunCanonical(selected.activation||null)!==goalRunCanonical(entry.body.activation||null))throw Error("VERSION_CONFLICT");
  if(run.status==="PARTIAL"){
    const result=run.result,candidate=result?.candidate;
    if(result?.goal_acceptance!=="NOT_RUN"||result.semantic_status!=="UNKNOWN"||result.app_created!==false||run.cancel_intent||run.error||!candidate||candidate.manifest?.app_id!==selected.app_id||(goalSpecFamily(entry.body.family) ? (candidate.namespace!==(entry.body.family==="natural_spec"?"pa-natural-spec-app.v1":"pa-spec-checklist-app.v1")||!(entry.body.family==="natural_spec"?[4,6]:[3,4]).includes(candidate.actions?.length)||candidate.spec_recipe?.steps?.length!==candidate.actions.length||(entry.body.family==="natural_spec"?Object.keys(selected.app_limits).some(k=>!Number.isSafeInteger(candidate.manifest.runtime_limits?.[k])||candidate.manifest.runtime_limits[k]>selected.app_limits[k]):goalRunCanonical(candidate.manifest.runtime_limits)!==goalRunCanonical(selected.app_limits))) : (candidate.actions?.length!==1||candidate.actions[0].action_id!==selected.action_id||candidate.actions[0].executor?.ref!=="text.literal_evidence"))||goalRunCanonical(candidate.goal)!==goalRunCanonical(entry.snapshot.content))throw Error("VERSION_CONFLICT");
    const digest=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(candidate)))),b=>b.toString(16).padStart(2,"0")).join("");
    if(!goalApplicationCurrent(entry))return;
    if(digest!==result.candidate_fingerprint)throw Error("VERSION_CONFLICT");
  }
  if(entry.body.family==="natural_spec"&&run.status==="PARTIAL"){
    const sample=await api(`/api/projects/${entry.project}/natural-spec-model-runs/${run.id}/sample-preview`);
    if(!goalApplicationCurrent(entry))return;
    await verifyNaturalSample(sample,run.result.candidate,entry.snapshot);
    if(!goalApplicationCurrent(entry))return;
    entry.sample=sample;
  }
  $("goal-application-ack").checked=false;
  entry.runId=run.id;entry.version=run.version;entry.result=run.status==="PARTIAL" ? run.result : null;
  if(entry.result)entry.expectedAppId=entry.result.candidate.manifest.app_id;
  entry.message=`${run.status} · ${run.error?.message || (entry.result ? "候选已核查；请查看完整目标、来源和精确指纹后确认。语义 UNKNOWN。" : "尚无可确认候选，当前状态只读展示。")}`;
}
function goalApplicationDraftState(){return JSON.stringify([goalCardFields.map(field=>$("goal-card-"+field).value),Array.from($("goal-card-resources").selectedOptions,option=>option.value)]);}
function goalApplicationHandoff(entry){
  const context={workspace:workspaceSelectionGeneration,app:appSelectionGeneration,edit:goalApplicationDraftGeneration,draft:goalApplicationDraftState()};
  context.current=()=>goalApplicationCurrent(entry)&&context.workspace===workspaceSelectionGeneration&&context.app===appSelectionGeneration&&context.edit===goalApplicationDraftGeneration&&context.draft===goalApplicationDraftState();
  return context;
}
async function openGoalApplication(entry,saved,context){
  if(!context.current())return;
  await refreshApps();if(!context.current())return;
  const guide=naturalFirstGuideForEntry(entry);
  const shown=await showApp(saved.id,entry.project,generation=>{context.app=generation;if(guide&&naturalFirstGuide===guide)guide.appGeneration=generation;},context.current,null,guide);
  if(!shown||!context.current()||activeApp!==saved.id||activeAppProject!==entry.project)return;
  $("app-create-status").textContent=entry.message;$("app-create-status").dataset.state="success";
  naturalFirstCandidateOpened(guide,entry,saved);
  if(engineering?.selectionCurrent===context.current)engineering.selectionCurrent=null;
  selectWorkspace("apps",guide);renderNaturalFirstGuide();if(engineering?.spec)$("internal-prepare").focus();else $("app-agent-term").focus();
}
async function goalApplicationAction(entry,operation){
  if(!entry||entry.busy||!goalApplicationCurrent(entry))return;
  entry.busy=true;renderGoalApplicationControls();
  try{await operation();}
  catch(error){if(goalApplicationCurrent(entry)){entry.result=null;$("goal-application-ack").checked=false;entry.message=`${error.message}；保留原请求键，只读恢复回执，不自动重发。`;}}
  finally{entry.busy=false;if(goalApplicationCurrent(entry))renderGoalApplicationControls();}
}
$("goal-application-start").onclick=async()=>{
  const card=activeGoalCard,key=goalApplicationKey();if(!card||goalApplications.has(key)||goalCardLoading||goalCardSaving)return;
  if($("goal-application-family").value==="natural_spec"){
    if(naturalGenerationReads.has(key))return;
    const connection=identityConnectionGeneration,selection=goalSelectionGeneration,workspace=workspaceSelectionGeneration,app=appSelectionGeneration,edit=goalApplicationDraftGeneration;
    const gate={current:()=>goalApplicationKey()===key&&activeGoalCard===card&&connection===identityConnectionGeneration&&selection===goalSelectionGeneration&&workspace===workspaceSelectionGeneration&&app===appSelectionGeneration&&edit===goalApplicationDraftGeneration&&$("goal-application-family").value==="natural_spec"};
    naturalGenerationReads.set(key,gate);renderGoalApplicationControls();
    try{
      const caps=await api("/api/capabilities");if(!gate.current())return;
      const availability=caps?.natural_spec_generation;
      const allowed=availability?.version==="natural-spec-generation-availability.v1"&&availability.availability==="OFFLINE_TEST_ONLY"&&availability.provider==="intern-s2"&&availability.live_request_allowance===0&&caps.connection?.mode==="MOCK";
      gate.message=allowed?"仅离线测试配置可用；实际发送仍须原 MockTransport 校验。真实模型预算0，下一步仅本次明确生成。":"已停止：没有可用的自然生成批准/受限离线配置。当前自然家族没有 LIVE 批准路径；未提交生成任务或模型请求。";
      naturalGenerationAvailability.set(key,gate);
      const guide=naturalFirstGuide;if(naturalFirstGuideCurrent(guide)&&guide.stage==="generate")guide.gateMessage=gate.message;
      if(!allowed)return;
    }catch(error){if(gate.current()){gate.message=`读取生成条件失败：${error.message}。未提交生成任务或模型请求。`;naturalGenerationAvailability.set(key,gate);if(naturalFirstGuideCurrent(naturalFirstGuide))naturalFirstGuide.gateMessage=gate.message;}return;}
    finally{if(naturalGenerationReads.get(key)===gate)naturalGenerationReads.delete(key);if(goalApplicationKey()===key)renderGoalApplicationControls();}
    if(!gate.current()||goalApplications.has(key))return;
  }
  const entry={key,project:$("project-select").value,card:card.id,snapshot:structuredClone(card.snapshot),connection:identityConnectionGeneration,selection:goalSelectionGeneration,body:{expected_version:card.version,expected_fingerprint:card.fingerprint,request_key:crypto.randomUUID()},busy:false,result:null,confirmBody:null,message:"正在接受冻结目标…"};
  const choice=goalProviderChoices.get(key)?.find(value=>value.activation.approval_id===$("goal-provider-select").value);
  if($("goal-provider-select").value&&!choice)return;
  if(goalSpecFamily($("goal-application-family").value)){if(choice)return;entry.body.family=$("goal-application-family").value;}
  if(choice){entry.body.activation=structuredClone(choice.activation);entry.body.request_key=choice.request_key;}
  goalApplications.set(key,entry);$("goal-application-ack").checked=false;
  return goalApplicationAction(entry,async()=>{
    const accepted=await api(`/api/projects/${entry.project}/goal-cards/${entry.card}/application-runs`,"POST",entry.body);
    if(!goalApplicationCurrent(entry))return;
    const fields=["run_id","status","goal_card_id","goal_version","goal_fingerprint","goal_acceptance","candidate_generated","generation_policy"];
    if(!accepted||Object.keys(accepted).sort().join()!==fields.sort().join()||accepted.goal_card_id!==entry.card||accepted.goal_fingerprint!==entry.body.expected_fingerprint||accepted.goal_version!==entry.body.expected_version||accepted.status!=="ACCEPTED"||accepted.goal_acceptance!=="NOT_RUN"||accepted.candidate_generated!==false||!/^run_[a-f0-9]{32}$/.test(accepted.run_id)||accepted.generation_policy?.version!==(goalGenerationVersion(entry.body.family))||accepted.generation_policy.live_request_allowance!==0||goalRunCanonical(accepted.generation_policy.activation||null)!==goalRunCanonical(entry.body.activation||null))throw Error("VERSION_CONFLICT");
    // A POST id is only a hint. The original-key GET proves the accepted request
    // before readGoalApplication promotes its verified id to future Run reads.
    await readGoalApplication(entry,accepted.run_id);
  });
};
$("goal-application-read").onclick=()=>{const entry=goalApplications.get(goalApplicationKey());if(entry&&!entry.busy){entry.connection=identityConnectionGeneration;entry.selection=goalSelectionGeneration;}return goalApplicationAction(entry,()=>readGoalApplication(entry));};
$("goal-application-ack").onchange=renderGoalApplicationControls;
$("goal-application-write-ack").onchange=renderGoalApplicationControls;
$("goal-application-family").onchange=()=>{$("goal-provider-select").value="";$("goal-provider-proof").textContent="";$("goal-application-write-ack").checked=false;renderGoalApplicationControls();};
$("goal-application-confirm").onclick=()=>{
  const entry=goalApplications.get(goalApplicationKey());if(!entry?.result||entry.confirmBody||!$("goal-application-ack").checked)return;
  if(goalSpecFamily(entry.body.family)&&!$("goal-application-write-ack").checked)return;
  const handoff=goalApplicationHandoff(entry);
  entry.confirmBody={expected_version:entry.version,candidate_fingerprint:entry.result.candidate_fingerprint,request_key:crypto.randomUUID(),name:$("goal-application-name").value,...(goalSpecFamily(entry.body.family)?{artifact_write_consent:"ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT"}:{})};
  return goalApplicationAction(entry,async()=>{
    const saved=await api(`/api/runs/${entry.runId}/confirm-application-candidate`,"POST",entry.confirmBody);
    if(!goalApplicationCurrent(entry))return;
    if(saved.id!==entry.result.candidate.manifest.app_id||saved.state!=="PREVIEW_ONLY")throw Error("VERSION_CONFLICT");
    entry.message=goalSpecFamily(entry.body.family)?`已确认 ${saved.id}，授权冻结材料读取和本项目 JSON 清单保存；语义 NOT_RUN。`:`已确认 ${saved.id}，仅授权冻结材料的读取。`;
    await openGoalApplication(entry,saved,handoff);
  });
};
$("goal-application-confirm-read").onclick=()=>{
  const entry=goalApplications.get(goalApplicationKey());if(!entry?.confirmBody)return;
  if(!entry.busy){entry.connection=identityConnectionGeneration;entry.selection=goalSelectionGeneration;}
  const handoff=goalApplicationHandoff(entry);
  return goalApplicationAction(entry,async()=>{
    const saved=await api(`/api/runs/${entry.runId}/confirmed-application-candidate?request_key=${encodeURIComponent(entry.confirmBody.request_key)}`);
    if(!goalApplicationCurrent(entry))return;
    const generation=goalApplications.get(entry.key);
    if(saved.id!==entry.expectedAppId||saved.state!=="PREVIEW_ONLY"||generation!==entry)throw Error("VERSION_CONFLICT");
    entry.message=`已只读恢复 ${saved.id}，没有重新发送确认。`;
    await openGoalApplication(entry,saved,handoff);
  });
};
const paBindingNamespace="pa-model-literal-material-binding.v1";
const specBindingNamespace="pa-spec-checklist-app.v1";
const specBindingConsent="ALLOW_ONLY_THIS_APP_TO_SAVE_VALIDATED_CHECKLIST_JSON_IN_THIS_PROJECT";
const paBindingFamily=()=>["spec","natural"].includes($("pa-binding-family").value);
const paBindingNatural=()=>$("pa-binding-family").value==="natural";
const paBindingPath=state=>state.natural?"natural-spec-model-runs":state.spec?"spec-model-runs":"pa-model-candidates";
const paBindingExpected=()=>paBindingNatural()?"pa-natural-spec-app.v1":paBindingFamily()?specBindingNamespace:paBindingNamespace;
$("pa-binding-family").onchange=()=>{paBindingSourceReadGeneration++;$("pa-binding-source").replaceChildren();paBindingState=null;$("pa-binding-proof").textContent="";$("pa-binding-ack").checked=false;renderPaBinding();};
const paBindingConsent="REUSE_ONLY_THIS_MODEL_GRAPH_WITH_THIS_EXPLICIT_TARGET_GOAL_AND_NEW_MATERIAL";
const paHash=async value=>Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",new TextEncoder().encode(goalRunCanonical(value)))),b=>b.toString(16).padStart(2,"0")).join("");
function paContext(){
 const entry={key:goalApplicationKey(),connection:identityConnectionGeneration,selection:goalSelectionGeneration};
 const handoff=goalApplicationHandoff(entry);return {entry,handoff,current:handoff.current};
}
$("goal-provider-refresh").onclick=async()=>{
 const context=paContext(),card=activeGoalCard,pid=$("project-select").value,generation=++goalProviderReadGeneration;if(!card)return;
 const current=()=>context.current()&&generation===goalProviderReadGeneration;
 $("goal-provider-select").replaceChildren(new Option("未选择；默认真实请求预算0",""));$("goal-provider-proof").textContent="";
 try{
  const value=await api(`/api/projects/${pid}/goal-cards/${card.id}/application-provider-scopes`);if(!current())return;
  if(value.project_id!==pid||value.card_id!==card.id||value.default_request_budget!==0||!Array.isArray(value.options)||value.options.length>64)throw Error("VERSION_CONFLICT");
  for(const choice of value.options){
   if(!/^gaapproval_[a-f0-9]{32}$/.test(choice.activation?.approval_id)||choice.scope?.metadata?.project_id!==pid||choice.scope.source.card_id!==card.id||choice.scope.source.version!==card.version||choice.scope.source.fingerprint!==card.fingerprint||goalRunCanonical(choice.scope.source.snapshot)!==goalRunCanonical(card.snapshot)||choice.scope.model!=="intern-s2"||!["OFFLINE_TEST","LIVE"].includes(choice.scope.mode)||choice.request_key!==choice.scope.request.generation_request_key||await paHash(choice.scope)!==choice.activation.scope_fingerprint||choice.scope_fingerprint!==choice.activation.scope_fingerprint||choice.approval_fingerprint!==choice.activation.approval_fingerprint)throw Error("VERSION_CONFLICT");
  }
  if(!current())return;goalProviderChoices.set(context.entry.key,value.options);
  for(const choice of value.options)$("goal-provider-select").add(new Option(`${choice.scope.mode} · intern-s2 · ≤${choice.scope.limits.max_requests}请求 · ${choice.activation.approval_id}`,choice.activation.approval_id));
  $("goal-provider-status").textContent=value.enabled ? "只读取得已有批准；须手动选择，未选预算0。费用封顶未建立。" : "模型适配默认关闭，真实请求预算0。";
 }catch(error){if(current()){$("goal-provider-select").replaceChildren(new Option("未选择；默认真实请求预算0",""));goalProviderChoices.delete(context.entry.key);$("goal-provider-status").textContent=error.message;}}
};
$("goal-provider-select").onchange=()=>{
 const choice=goalProviderChoices.get(goalApplicationKey())?.find(value=>value.activation.approval_id===$("goal-provider-select").value);
 $("goal-provider-proof").textContent=choice ? JSON.stringify(choice,null,2) : "";
};
function renderPaBinding(){
 const state=paBindingState,current=state?.context.current(),busy=state?.busy;
 $("pa-binding-save").disabled=!current||busy||!state?.options||!!state?.body||!$("pa-binding-ack").checked;
 $("pa-binding-recover").disabled=!state?.body||busy||!goalApplicationCurrent(state.context.entry);
 $("pa-binding-open").disabled=!current||busy||!state?.saved;
 $("pa-binding-preview").disabled=!activeGoalCard||busy||!$("pa-binding-source").value;
 $("pa-binding-name").disabled=!!state?.body;
}
$("pa-binding-ack").onchange=renderPaBinding;
$("pa-binding-source").onchange=()=>{paBindingState=null;$("pa-binding-proof").textContent="";$("pa-binding-ack").checked=false;renderPaBinding();};
$("pa-binding-sources").onclick=async()=>{
 const context=paContext(),pid=$("project-select").value,generation=++paBindingSourceReadGeneration;
 const current=()=>context.current()&&generation===paBindingSourceReadGeneration;paBindingState=null;$("pa-binding-source").replaceChildren();$("pa-binding-proof").textContent="";$("pa-binding-ack").checked=false;renderPaBinding();
 try{const value=await api(`/api/projects/${pid}/${paBindingNatural()?"natural-spec-model-candidates":paBindingFamily()?"spec-model-candidates":"pa-model-candidates"}`);if(!current())return;
  if(value.project_id!==pid||value.namespace!==paBindingExpected()||value.new_model_requests!==0||!Array.isArray(value.options)||value.options.length>64)throw Error("VERSION_CONFLICT");
  $("pa-binding-source").add(new Option("明确选择已确认的模型来源",""));
  for(const source of value.options){if(!/^run_[a-f0-9]{32}$/.test(source.run_id)||source.model!=="intern-s2"||!/^[a-f0-9]{64}$/.test(source.graph_fingerprint))throw Error("VERSION_CONFLICT");const option=new Option(source.run_id+" · "+source.step_ids.join(","),source.run_id);option.dataset.graph=source.graph_fingerprint;option.dataset.candidate=source.model_candidate_fingerprint;$("pa-binding-source").add(option);}
  $("pa-binding-status").textContent="来源仍需当前审计权限；选择后先预览新材料。";
 }catch(error){if(current()){$("pa-binding-source").replaceChildren();$("pa-binding-status").textContent=error.message;}}finally{if(current())renderPaBinding();}
};
$("pa-binding-preview").onclick=async()=>{
 const card=activeGoalCard,source=$("pa-binding-source").selectedOptions[0],context=paContext(),pid=$("project-select").value;if(!card||!source?.value)return;
 const state={context,pid,spec:paBindingFamily(),natural:paBindingNatural(),rid:source.value,card:structuredClone(card),busy:true,options:null,body:null,saved:null};paBindingState=state;$("pa-binding-ack").checked=false;renderPaBinding();
 try{const value=await api(`/api/projects/${pid}/${paBindingPath(state)}/${state.rid}/${state.spec?"binding-options":"material-binding-options"}?card_id=${card.id}`);
  if(!context.current()||paBindingState!==state)return;
  if(value.namespace!==paBindingExpected()||value.project_id!==pid||value.source_run_id!==state.rid||value.model_requests!==0||value.semantic_status!=="UNKNOWN"||value.owner_acceptance!=="PENDING"||value.formal_publication_enabled!==false||value.target_goal.card_id!==card.id||value.target_goal.version!==card.version||value.target_goal.fingerprint!==card.fingerprint||goalRunCanonical(value.target_goal.snapshot)!==goalRunCanonical(card.snapshot)||value.model_candidate_fingerprint!==source.dataset.candidate||value.graph_fingerprint!==source.dataset.graph||await paHash(value.model_graph)!==value.graph_fingerprint||await paHash(value.target_goal.snapshot)!==card.fingerprint||value.resource_id!==card.snapshot.content.resource_refs[0]||value.source_hash!==card.snapshot.resource_snapshots[0].hash)throw Error("VERSION_CONFLICT");
  if(!context.current()||paBindingState!==state)return;state.options=value;$("pa-binding-proof").textContent=JSON.stringify(value,null,2);$("pa-binding-status").textContent="已预览实际模型图和完整新目标；明确确认后保存应用；规范能力在实际运行时保存本项目一个 JSON 清单，语义完整性未验。";
 }catch(error){if(context.current()&&paBindingState===state){state.options=null;$("pa-binding-proof").textContent="";$("pa-binding-status").textContent=error.message;}}finally{state.busy=false;if(goalApplicationCurrent(context.entry)&&paBindingState===state)renderPaBinding();}
};
async function paBindingAction(state,operation){
 if(!state||state.busy||paBindingState!==state||!state.context.current())return;state.busy=true;renderPaBinding();
 try{const saved=await operation();if(paBindingState!==state||!state.context.current())return;
  const fields=["namespace","id","project_id","runtime_id","candidate_fingerprint","source_run_id","request_key","request_fingerprint","model_requests","semantic_status","owner_acceptance","formal_publication_enabled","cached"];
  if(!saved||Object.keys(saved).sort().join()!==fields.sort().join()||saved.namespace!==(state.natural?"pa-natural-spec-app.v1":state.spec?specBindingNamespace:paBindingNamespace)||saved.project_id!==state.pid||saved.source_run_id!==state.rid||saved.request_key!==state.body.request_key||saved.request_fingerprint!==await paHash(state.body)||!/^app_[a-f0-9]{32}$/.test(saved.id)||saved.model_requests!==0||saved.semantic_status!=="UNKNOWN"||saved.owner_acceptance!=="PENDING"||saved.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
  if(paBindingState!==state||!state.context.current())return;state.saved=saved;$("pa-binding-status").textContent=`已保存 ${saved.id}；另行打开核查新材料执行。`;
 }catch(error){if(paBindingState===state&&state.context.current()){state.saved=null;$("pa-binding-status").textContent=error.message+"；仅用原key GET恢复，不自动重发。";}}finally{state.busy=false;if(paBindingState===state&&goalApplicationCurrent(state.context.entry))renderPaBinding();}
}
$("pa-binding-save").onclick=()=>{
 const state=paBindingState;if(!state?.options||state.body||!$("pa-binding-ack").checked||!state.context.current())return;
 const value=state.options;state.body={card_id:state.card.id,expected_goal_version:state.card.version,expected_goal_fingerprint:state.card.fingerprint,expected_source_hash:value.source_hash,expected_model_candidate_fingerprint:value.model_candidate_fingerprint,...(state.spec?{expected_recipe_fingerprint:value.recipe_fingerprint}:{expected_graph_fingerprint:value.graph_fingerprint}),name:$("pa-binding-name").value,consent:state.spec?specBindingConsent:paBindingConsent,request_key:crypto.randomUUID()};
 return paBindingAction(state,()=>api(`/api/projects/${state.pid}/${paBindingPath(state)}/${state.rid}/${state.spec?"bindings":"material-bindings"}`,"POST",state.body));
};
$("pa-binding-recover").onclick=()=>{const state=paBindingState;if(!state?.body||state.busy||!goalApplicationCurrent(state.context.entry))return;state.context=paContext();return paBindingAction(state,()=>api(`/api/projects/${state.pid}/${paBindingPath(state)}/${state.rid}/${state.spec?"bindings/by-key":"material-binding-requests"}/${encodeURIComponent(state.body.request_key)}`));};
$("pa-binding-open").onclick=async()=>{
 const state=paBindingState;if(!state?.saved||state.busy||!state.context.current())return;
 const saved=state.saved,entry=state.context.entry;entry.project=state.pid;entry.message=`已保存 ${saved.id}；请核查本目标新材料的逐字引用。`;
 await openGoalApplication(entry,saved,state.context.handoff);
};
renderGoalApplicationControls();
