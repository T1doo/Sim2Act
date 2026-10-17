// The authenticated user declares each frozen criterion; model tools cannot call this API.
const ordinaryOwnerIntents=new Map();
let ordinaryOwnerView=null,ordinaryRubricScope=null,ordinaryOwnerMetadataOpenView=null;
function ordinaryRubricIdentity(){return activeGoalCard?JSON.stringify([token,identityConnectionGeneration,$('project-select').value,activeGoalCard.id,activeGoalCard.version,activeGoalCard.fingerprint]):null;}
function resetOrdinaryRubricAcknowledgement(){ordinaryRubricScope=null;$('ordinary-rubric-start-ack').checked=false;$('ordinary-rubric-md').checked=false;renderOrdinaryRubricStart();}
function ordinaryRubricReady(){return !!activeGoalCard&&!goalCardLoading&&!goalCardSaving&&ordinaryRubricScope===ordinaryRubricIdentity()&&$('ordinary-rubric-start-ack').checked&&activeGoalCard.snapshot.content.acceptance_checks.length>0&&activeGoalCard.snapshot.content.acceptance_checks.every(x=>x.trim())&&activeGoalCard.snapshot.content.resource_refs.length>0;}
function renderOrdinaryRubricStart(){
 const scope=ordinaryRubricIdentity(),entry=goalRunRequests.get(goalRunKey());
 if(scope!==ordinaryRubricScope){$('ordinary-rubric-start-ack').checked=false;$('ordinary-rubric-md').checked=false;ordinaryRubricScope=scope;}
 $('ordinary-rubric-preview').textContent=activeGoalCard?JSON.stringify({goal_card:activeGoalCard.id,version:activeGoalCard.version,fingerprint:activeGoalCard.fingerprint,...activeGoalCard.snapshot.content},null,2):'请先保存目标、选择材料并填写明确验收标准。';
 $('ordinary-rubric-run').textContent=$('ordinary-rubric-md').checked?'冻结标准并交付本项目一份MD':'冻结标准并执行普通任务';
 $('ordinary-rubric-run').disabled=!ordinaryRubricReady()||['sending','unknown','accepted-read-error'].includes(entry?.state);
}
$('ordinary-rubric-start-ack').onchange=renderOrdinaryRubricStart;
$('ordinary-rubric-md').onchange=()=>{$('ordinary-rubric-start-ack').checked=false;renderOrdinaryRubricStart();};
$('ordinary-rubric-run').onclick=safe(()=>executeGoalCard(false,true));
function ordinaryOwnerKey(id){return JSON.stringify([token,$('project-select').value,id]);}
function ordinaryOwnerScope(id){return JSON.stringify([ordinaryOwnerKey(id),identityConnectionGeneration,projectSelectionGeneration,runUserSelectionGeneration]);}
function clearOrdinaryOwnerReview(){ordinaryOwnerView=null;ordinaryOwnerMetadataOpenView=null;}
function ordinaryOwnerMetadataButton(id,baseCurrent){
 const scope=ordinaryOwnerScope(id),workspace=workspaceSelectionGeneration,view={id,scope,baseCurrent};ordinaryOwnerMetadataOpenView=view;
 const current=()=>ordinaryOwnerMetadataOpenView===view&&baseCurrent()&&scope===ordinaryOwnerScope(id)&&workspace===workspaceSelectionGeneration&&!$('projects').hidden;
 const button=document.createElement('button');button.id='ordinary-owner-metadata-open';button.type='button';button.textContent='只读打开此 Run 人工声明元数据 / 停止入口';
 button.onclick=safe(async()=>{if(!current()||button.disabled)return;button.disabled=true;try{await showOrdinaryOwnerMetadata(id);}finally{if(current())button.disabled=false;}});return button;
}
function resumeOrdinaryOwnerReview(){const failure=ordinaryOwnerMetadataOpenView;if(failure&&failure.scope===ordinaryOwnerScope(failure.id)&&failure.baseCurrent())$('ordinary-owner-metadata-open')?.replaceWith(ordinaryOwnerMetadataButton(failure.id,failure.baseCurrent));const old=ordinaryOwnerView;if(old&&(activeRun===old.run||(old.metadataOnly&&activeRun===null))&&old.scope===ordinaryOwnerScope(old.run)){old.node.remove();renderOrdinaryOwnerReview(old.result,old.redacted,old.metadataOnly);}}
async function showOrdinaryOwnerMetadata(id){
 renderOrdinaryOwnerReview({id,contract:{fingerprint:null,snapshot:{human_review:{version:'owner.ordinary-goal.v1'}}}},true,true);
 await $('ordinary-owner-read').onclick();
}
function renderOrdinaryOwnerReview(result,redacted=false,metadataOnly=false){
 if(!['owner.ordinary-goal.v1','owner.ordinary-goal-md.v2'].includes(result.contract?.snapshot?.human_review?.version))return;
 const id=result.id,scope=ordinaryOwnerScope(id),workspace=workspaceSelectionGeneration,intentKey=ordinaryOwnerKey(id);
 if(ordinaryOwnerView?.scope===scope&&ordinaryOwnerView.workspace===workspace){ordinaryOwnerView.result=result;$('result').append(ordinaryOwnerView.node);return;}
 const view={run:id,scope,workspace,result,read:0,busy:false,state:null,redacted,metadataOnly};ordinaryOwnerView=view;
 const current=()=>ordinaryOwnerView===view&&(activeRun===id||(metadataOnly&&activeRun===null))&&scope===ordinaryOwnerScope(id)&&workspace===workspaceSelectionGeneration&&!$('projects').hidden;
 const node=document.createElement('section');node.id='ordinary-owner-review';view.node=node;
 const heading=document.createElement('h3');heading.textContent='本次普通任务的人工逐项签收';node.append(heading);
 node.append(row('人工声明独立于自动验收 NOT_RUN、技术 PARTIAL；语义 UNKNOWN，正式发布关闭。Goal版本变化后当前签收失效，历史保留。'));
 const frozen=document.createElement('pre');frozen.id='ordinary-owner-frozen';frozen.textContent=redacted?'':JSON.stringify({run:id,contract_fingerprint:result.contract.fingerprint,source_goal:result.contract.snapshot.source_goal_card,...(result.contract.snapshot.artifact_delivery?{artifact_delivery:result.contract.snapshot.artifact_delivery}:{})},null,2);node.append(frozen);
 if(!redacted&&result.contract.snapshot.ordinary_correction){
  const feedback=result.contract.snapshot.ordinary_correction.feedback,section=document.createElement('section');section.id='ordinary-correction-source';
  section.append(row(`这是针对 ${feedback.parent_run_id} 原拒绝的新Run；原Goal与标准保留。以下是待修正问题，不表示已修复，仍须另行逐项人工声明。`));
  for(const issue of feedback.issues)section.append(row(`${issue.item_id} · 原标准：${issue.criterion} · 原拒绝理由：${issue.reason}`));node.append(section);
 }
 const status=document.createElement('p');status.id='ordinary-owner-status';status.setAttribute('role','status');
 const body=document.createElement('div');body.id='ordinary-owner-body';
 const read=document.createElement('button');read.id='ordinary-owner-read';read.type='button';read.textContent='读取此 Run 的当前签收与完整证据';
 const recover=document.createElement('button');recover.id='ordinary-owner-recover';recover.type='button';recover.textContent='只读恢复原 key 回执';
 const retry=document.createElement('button');retry.id='ordinary-owner-retry';retry.type='button';retry.textContent='明确重试原 key 原声明';
 const retryLabel=document.createElement('label'),retryAck=document.createElement('input');retryAck.type='checkbox';retryAck.id='ordinary-owner-retry-ack';retryLabel.append(retryAck,'核对原请求内容，明确仅恢复同一请求，不创建新的签收');
 const pending=()=>ordinaryOwnerIntents.get(intentKey);
 function controls(){const p=pending();if(p)p.renderCurrent=()=>{if(current())controls();};read.disabled=view.busy;recover.hidden=!p;recover.disabled=view.busy;retry.hidden=!p||p.state!=='unknown';retryLabel.hidden=retry.hidden;retry.disabled=view.busy||!retryAck.checked;}
 function clearProtected(){body.replaceChildren();frozen.textContent='';view.state=null;view.redacted=true;node.querySelector('#ordinary-correction-source')?.remove();}
 function clearResultContent(){view.redacted=true;ordinaryOutcomeView=null;frozen.textContent='';node.querySelector('#ordinary-correction-source')?.remove();$('result').replaceChildren(node);$('raw-result').textContent='';$('events').textContent='';}
 function forget(p){if(pending()===p)ordinaryOwnerIntents.delete(intentKey);}
 async function verify(state){
  if(!['owner.ordinary-goal.v1','owner.ordinary-goal-md.v2'].includes(state.version)||(!metadataOnly&&state.version!==result.contract.snapshot.human_review.version)||state.run_id!==id||state.project_id!==$('project-select').value||state.formal_publication_enabled!==false||state.automatic_goal_acceptance!=='NOT_RUN')throw Error('VERSION_CONFLICT');
  let previous='';for(const [n,row] of state.history.entries()){if(row.run_id!==id||row.principal_id!==state.principal_id||row.project_id!==state.project_id||row.sequence!==n+1||row.previous_fingerprint!==previous)throw Error('VERIFICATION_FAILED');previous=row.fingerprint;}
  if(state.sequence!==state.history.length)throw Error('VERIFICATION_FAILED');
  if(metadataOnly&&state.content_access)throw Error('授权已恢复，请从任务历史重新打开完整Run再核对证据。');
  if(state.current&&(state.current.run_id!==id||state.current.contract_fingerprint!==result.contract.fingerprint||goalRunCanonical(state.current.source_goal)!==goalRunCanonical(result.contract.snapshot.source_goal_card)))throw Error('VERSION_CONFLICT');
  for(const record of [state.record,state.recovered].filter(r=>r?.payload)){
   const metadata={...record};delete metadata.payload;delete metadata.fingerprint;
   if(await registeredHash(record.payload)!==record.fingerprint||goalRunCanonical(record.payload.metadata)!==goalRunCanonical(metadata)||await registeredHash(record.payload.request)!==record.request_fingerprint)throw Error('VERIFICATION_FAILED');
  }
 }
 function button(label,id,fn){const b=document.createElement('button');b.type='button';b.textContent=label;b.id=id;b.onclick=safe(fn);return b;}
 function render(state){
  if(!current())return;view.state=state;body.replaceChildren();status.textContent=`用户人工声明：${state.owner_acceptance} · 自动验收 NOT_RUN · 语义 UNKNOWN`;
  const history=document.createElement('pre');history.id='ordinary-owner-history';history.textContent=JSON.stringify({history:state.history,invalidation_reason:state.invalidation_reason},null,2);body.append(history);
  if(!state.content_access)clearResultContent();
  if(pending()){status.textContent+='；原请求结果尚未恢复，请先读原key。';controls();return;}
  renderOrdinaryCorrection(body,state,view,current,intentKey);
  const last=state.latest;
  function stopControls(){if(!last||!['PREPARE','DECIDE'].includes(last.kind))return;
   const reason=document.createElement('input');reason.id='ordinary-owner-stop-reason';reason.maxLength=500;reason.placeholder='取消或撤回理由';
   const ack=document.createElement('input');ack.type='checkbox';ack.id='ordinary-owner-stop-ack';const label=document.createElement('label');label.append(ack,'明确停止此精确人工声明，历史保留');
   body.append(reason,label,button(last.kind==='PREPARE'?'取消此待签收':'撤回此人工声明','ordinary-owner-stop',async()=>{if(current()&&!view.busy&&ack.checked&&reason.value.trim())await send({command:last.kind==='PREPARE'?'CANCEL':'REVOKE',target_id:last.id,target_fingerprint:last.fingerprint,reason:reason.value,expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);}));
  }
  if(!state.content_access){clearResultContent();stopControls();controls();return;}
  if(state.record?.kind==='DECIDE'){const declaration=document.createElement('pre');declaration.id='ordinary-owner-declaration';declaration.textContent=JSON.stringify(state.record.payload.choices,null,2);body.append(declaration);}
  const proof=document.createElement('pre');proof.id='ordinary-owner-proof';proof.textContent=JSON.stringify(state.current,null,2);body.append(proof);
  if(state.owner_acceptance==='PENDING'&&state.record?.kind==='PREPARE'){
   const form=document.createElement('form');form.id='ordinary-owner-form';const fields=[];
   for(const item of state.current.items){const label=document.createElement('label');label.textContent=`${item.id}：${item.text}`;const decision=document.createElement('select');decision.required=true;decision.dataset.item=item.id;decision.append(new Option('请逐项手动选择',''),new Option('接受','ACCEPT'),new Option('拒绝','REJECT'));const reason=document.createElement('textarea');reason.required=true;reason.maxLength=500;reason.dataset.reason=item.id;label.append(decision,reason);form.append(label);fields.push({item,decision,reason});}
   const label=document.createElement('label'),ack=document.createElement('input');ack.type='checkbox';ack.id='ordinary-owner-ack';label.append(ack,'我本人已核对完整 Goal、材料、此 Run 精确结果及每一项理由，明确提交人工声明；不代表自动语义验收。');
   const submit=document.createElement('button');submit.id='ordinary-owner-decide';submit.textContent='提交此 Run 的逐项人工声明';submit.disabled=true;ack.onchange=()=>{submit.disabled=!ack.checked||view.busy;};form.append(label,submit);
   form.onsubmit=safe(async()=>{if(!current()||!ack.checked||view.busy||!form.reportValidity()||fields.some(f=>!f.reason.value.trim()))return;
    await send({command:'DECIDE',review_id:state.record.id,review_fingerprint:state.record.fingerprint,choices:fields.map(f=>({item_id:f.item.id,decision:f.decision.value,reason:f.reason.value})),expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);});body.append(form);
  }else if(!state.latest||['CANCEL','REVOKE'].includes(state.latest.kind)||state.owner_acceptance==='EXPIRED'){
   body.append(button('准备此精确结果的人工签收（15分钟）','ordinary-owner-prepare',async()=>{if(current()&&!view.busy)await send({command:'PREPARE',expected_contract_fingerprint:await registeredHash(state.current),expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);}));
  }
  stopControls();
  controls();
 }
 async function load(key=null){if(!current()||view.busy)return;view.busy=true;const generation=++view.read;controls();
  try{const state=await api(`/api/runs/${id}/owner-review${key?'?request_key='+encodeURIComponent(key):''}`);await verify(state);if(!current()||generation!==view.read)return;
   if(key){const p=pending(),r=state.recovered;if(!p||p.body.request_key!==key||r?.request_key!==key||r.request_fingerprint!==await registeredHash(p.body))throw Error('VERSION_CONFLICT');if(!current()||generation!==view.read||pending()!==p)return;forget(p);}
   render(state);
  }catch(error){if(current()&&generation===view.read){clearProtected();if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('当前身份没有读取此任务的权限；已清除成果和签收内容。'));return;}status.textContent=`未确认当前签收：${error.message}。只恢复原key，不自动提交。`;}}
  finally{view.busy=false;if(current())controls();}
 }
 async function send(bodyIntent,expected=null,replay=false){
  if(!current()||view.busy||(!replay&&pending()))return;
  let p=pending();if(replay){if(!p||p.state!=='unknown'||!retryAck.checked)return;bodyIntent=p.body;}else{p={body:structuredClone(bodyIntent),principal:expected.principal_id,project:expected.project_id,state:'checking'};ordinaryOwnerIntents.set(intentKey,p);}
  view.busy=true;controls();body.querySelectorAll('button,input,select,textarea').forEach(e=>e.disabled=true);
  try{
   if(!replay){const fresh=await api(`/api/runs/${id}/owner-review`);await verify(fresh);if(!current()){forget(p);return;}if(!fresh.content_access&&expected.current){clearResultContent();render(fresh);throw Error('当前证据权限或版本已失效');}if(fresh.sequence!==expected.sequence||goalRunCanonical(fresh.current)!==goalRunCanonical(expected.current)||fresh.record?.fingerprint!==expected.record?.fingerprint)throw Error('VERSION_CONFLICT');}
   if(!current())return;p.state='sending';
   const receipt=await api(`/api/runs/${id}/owner-review-requests`,'POST',p.body);
   if(receipt.formal_publication_enabled!==false||receipt.record?.run_id!==id||receipt.record.request_fingerprint!==await registeredHash(p.body))throw Error('VERIFICATION_FAILED');
   forget(p);if(current()){view.busy=false;await load();}
  }catch(error){
   if(p.state==='checking'){forget(p);}else{
    const proof=error.submissionRejection,hash=await registeredHash(p.body);
    const rejected=proof?.namespace==='ordinary-owner-submission-rejection.v1'&&proof.principal_id===p.principal&&proof.project_id===p.project&&proof.run_id===id&&proof.request_key===p.body.request_key&&proof.request_fingerprint===hash&&proof.acceptance==='NOT_ACCEPTED'&&proof.previous_request==='ABSENT'&&proof.phase==='TRANSACTION_ROLLED_BACK';
    p.state=rejected?'rejected':'unknown';if(rejected)forget(p);
   }
   if(current()){if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('当前任务授权不可用；已清除成果与签收正文。'));return;}clearProtected();status.textContent=`人工声明未确认：${error.message}。原请求保留；不会自动重发。`;}
  }finally{view.busy=false;if(current())controls();else if(pending()===p)p.renderCurrent?.();}
 }
 read.onclick=safe(()=>load());recover.onclick=safe(()=>{const p=pending();if(p)return load(p.body.request_key);});retryAck.onchange=controls;retry.onclick=safe(()=>send(null,null,true));
 node.append(read,recover,retryLabel,retry,body,status);$('result').append(node);controls();
 const correction=ordinaryCorrectionIntents.get(intentKey);if(correction)renderOrdinaryCorrection(body,{content_access:false,principal_id:correction.principal,project_id:correction.project},view,current,intentKey);
 status.textContent=pending()?'原请求待恢复；不会自动读取或重发。':'标准已在执行前冻结。请先读取当前精确证据，再准备人工逐项签收。';
}
// Page-memory durable intents keep the original body/key across navigation and lost replies.
const ordinaryCorrectionIntents=new Map();
function renderOrdinaryCorrection(host,state,view,ownerCurrent,key){
 const pending=()=>ordinaryCorrectionIntents.get(key);
 if(!pending()&&(!state.content_access||state.owner_acceptance!=='REJECTED'||state.current?.human_correction))return;
 const section=document.createElement('section');section.id='ordinary-correction';
 const current=()=>ownerCurrent()&&section.isConnected;
 const title=document.createElement('h4');title.textContent='根据原拒绝另行创建修正任务';section.append(title);
 section.append(row('先读取精确拒绝条目和材料，再另行确认创建一个新Run。原Goal、标准、声明和成果保留；拒绝理由不授予权限。仅Mock，真实模型额度0。'));
 const status=document.createElement('p');status.id='ordinary-correction-status';status.setAttribute('role','status');
 const proof=document.createElement('div');proof.id='ordinary-correction-preview';
 let preview=null,busy=false;
 const button=(id,label,fn)=>{const node=document.createElement('button');node.type='button';node.id=id;node.textContent=label;node.onclick=safe(fn);return node;};
 const ack=document.createElement('input');ack.type='checkbox';ack.id='ordinary-correction-ack';const label=document.createElement('label');label.append(ack,'我已核对原Goal、全部标准、精确材料及拒绝理由，明确创建一个新修正Run；不覆盖旧结果。');
 const retryAck=document.createElement('input');retryAck.type='checkbox';retryAck.id='ordinary-correction-retry-ack';const retryLabel=document.createElement('label');retryLabel.append(retryAck,'仅明确重试原key、原请求；不另建第二个Run。');
 const prepare=button('ordinary-correction-read','读取新修正任务的精确预览',async()=>{
  if(!current()||busy||pending())return;busy=true;preview=null;ack.checked=false;controls();
  try{const value=await api(`/api/runs/${view.run}/correction-preview`);const {preview_fingerprint,...unsigned}=value;
   if(value.version!=='ordinary-goal-correction.v1'||value.parent_run_id!==view.run||value.project_id!==state.project_id||value.principal_id!==state.principal_id||value.real_model_allowance!==0||value.mode!=='mock'||value.automatic_goal_acceptance!=='NOT_RUN'||value.semantic_status!=='UNKNOWN'||value.formal_publication_enabled!==false||await registeredHash(unsigned)!==preview_fingerprint||value.feedback.declaration_id!==state.record?.id||value.feedback.declaration_fingerprint!==state.record?.fingerprint||goalRunCanonical(value.source_goal)!==goalRunCanonical(state.current.source_goal))throw Error('VERSION_CONFLICT');
   if(!current())return;preview=value;proof.replaceChildren();
   proof.append(row(`来源Run：${view.run} · 原声明：${value.feedback.declaration_id} · 新任务人工PENDING / 自动NOT_RUN / 语义UNKNOWN`));
   const goal=document.createElement('pre');goal.textContent=JSON.stringify({original_goal:value.source_goal,materials:value.feedback.materials,limits:value.limits,artifact_delivery:value.artifact_delivery},null,2);proof.append(goal);
   for(const issue of value.feedback.issues)proof.append(row(`${issue.item_id} · 原标准：${issue.criterion} · 拒绝理由：${issue.reason}`));
   status.textContent='请另行确认。新任务仍使用原材料与工具边界，重新鉴权；MD成功保存会产生一个新Resource及两条读取Grant。';
  }catch(error){if(current()){preview=null;proof.replaceChildren();status.textContent=`未确认修正预览：${error.message}。未创建新任务。`;if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('当前来源授权不可用；已清除成果和拒绝正文。'));}}}
  finally{busy=false;if(current())controls();}
 });
 async function verifyReceipt(value,entry){
  if(value.version!=='ordinary-goal-correction.v1'||value.status!=='ACCEPTED'||!/^run_[a-f0-9]{32}$/.test(value.run_id)||value.run_id===view.run||value.parent_run_id!==view.run||value.principal_id!==entry.principal||value.project_id!==entry.project||value.request_key!==entry.body.request_key||value.request_fingerprint!==await registeredHash(entry.body)||value.feedback_fingerprint!==await registeredHash(entry.feedback)||value.real_model_allowance!==0||value.formal_publication_enabled!==false)throw Error('VERIFICATION_FAILED');
 }
 async function send(replay=false){
  if(!current()||busy)return;let entry=pending();
  if(replay){if(!entry||entry.state!=='unknown'||!retryAck.checked)return;}
  else{if(entry||!preview||!ack.checked)return;entry={principal:state.principal_id,project:state.project_id,feedback:structuredClone(preview.feedback),source:structuredClone(preview.source_goal),body:{expected_preview_fingerprint:preview.preview_fingerprint,declaration_id:preview.feedback.declaration_id,declaration_fingerprint:preview.feedback.declaration_fingerprint,expected_sequence:preview.feedback.declaration_sequence,request_key:crypto.randomUUID(),consent:'RUN_NEW_CORRECTION_KEEP_GOAL_CRITERIA_AND_HISTORY'},state:'sending'};ordinaryCorrectionIntents.set(key,entry);}
  busy=true;entry.state='sending';ack.checked=false;retryAck.checked=false;controls();
  try{const value=await api(`/api/runs/${view.run}/correction-runs`,'POST',entry.body);await verifyReceipt(value,entry);entry.receipt=value;entry.state='accepted';if(current())status.textContent=`新修正任务已接受：${value.run_id}。请显式打开新Run，读取当前技术状态并另行核对人工声明。`;}
  catch(error){const rejected=error.submissionRejection,hash=await registeredHash(entry.body);
   const definite=rejected?.namespace==='ordinary-correction-submission-rejection.v1'&&rejected.principal_id===entry.principal&&rejected.project_id===entry.project&&rejected.parent_run_id===view.run&&rejected.request_key===entry.body.request_key&&rejected.request_fingerprint===hash&&rejected.acceptance==='NOT_ACCEPTED'&&rejected.previous_request==='ABSENT'&&rejected.phase==='TRANSACTION_ROLLED_BACK';
   entry.state=definite?'rejected':'unknown';if(definite&&pending()===entry)ordinaryCorrectionIntents.delete(key);
   if(current()){preview=null;proof.replaceChildren();status.textContent=definite?`新请求已明确拒绝：${error.message}。请重新读取当前预览。`:`接受结果UNKNOWN：${error.message}。保留原key，只显式恢复或重试原请求。`;if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('当前来源授权不可用；已清除成果和拒绝正文。'));}}
  }finally{busy=false;if(current())controls();else if(pending()===entry)entry.renderCurrent?.();}
 }
 const submit=button('ordinary-correction-submit','明确创建新修正Run',()=>send());
 const recover=button('ordinary-correction-recover','只读恢复原key的新Run回执',async()=>{
  const entry=pending();if(!current()||busy||!entry)return;busy=true;controls();
  try{const value=await api(`/api/runs/${view.run}/correction-requests/${encodeURIComponent(entry.body.request_key)}`);await verifyReceipt(value,entry);entry.receipt=value;entry.state='accepted';if(current())status.textContent=`原key已恢复：${value.run_id}。未重发创建请求，请显式打开新Run。`;}
  catch(error){if(current()){proof.replaceChildren();status.textContent=`原key未确认：${error.message}。不自动提交或另建。`;if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('当前来源授权不可用；已清除成果和拒绝正文。'));}}}
  finally{busy=false;if(current())controls();else if(pending()===entry)entry.renderCurrent?.();}
 });
 const retry=button('ordinary-correction-retry','明确重试原key原请求',()=>send(true));
 const open=button('ordinary-correction-open','打开已接受的新修正Run',async()=>{
  const entry=pending();if(!current()||busy||entry?.state!=='accepted')return;
  const identity=token,connection=identityConnectionGeneration,project=$('project-select').value,projectGeneration=projectSelectionGeneration,workspace=workspaceSelectionGeneration;
  const guard=()=>identity===token&&connection===identityConnectionGeneration&&project===$('project-select').value&&projectGeneration===projectSelectionGeneration&&workspace===workspaceSelectionGeneration&&!$('projects').hidden;
  await showRun(entry.receipt.run_id,true,guard,result=>{if(result.contract.fingerprint!==entry.receipt.contract_fingerprint||goalRunCanonical(result.contract.snapshot.ordinary_correction?.feedback)!==goalRunCanonical(entry.feedback)||goalRunCanonical(result.contract.snapshot.source_goal_card)!==goalRunCanonical(entry.source))throw Error('VERSION_CONFLICT');});
 });
 function controls(){if(!current())return;const entry=pending();if(entry)entry.renderCurrent=()=>{if(current())controls();};prepare.disabled=busy||!!entry||!state.content_access;label.hidden=submit.hidden=!!entry||!preview;submit.disabled=busy||!preview||!ack.checked;recover.hidden=!entry;recover.disabled=busy;retry.hidden=retryLabel.hidden=entry?.state!=='unknown';retry.disabled=busy||!retryAck.checked;open.hidden=entry?.state!=='accepted';open.disabled=busy;}
 ack.onchange=controls;retryAck.onchange=controls;
 section.append(prepare,proof,label,submit,recover,retryLabel,retry,open,status);host.append(section);controls();
 status.textContent=pending()?`原修正请求：${pending().state}；仅显式恢复或打开，不自动运行另一任务。`:'当前拒绝尚未创建修正Run。';
}
renderOrdinaryRubricStart();
