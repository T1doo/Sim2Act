"use strict";
// Immutable saved recipe -> independently confirmed original ordinary CSV Run.
const csvFullReportExtractions=new Map(),csvFullReportUses=new Map();
let csvFullReportView=null,csvFullReportEpoch=0,csvFullReportSource=null,csvFullReportExtractionView=null;
const csvFullReportOwner=id=>JSON.stringify([token,$('project-select').value,id]);
function clearCsvFullReport(){csvFullReportEpoch++;csvFullReportView=null;$('csv-full-report-use')?.remove();}
function clearCsvFullReportExtraction(){csvFullReportSource=null;csvFullReportExtractionView=null;for(const entry of csvFullReportExtractions.values()){delete entry.options;entry.ack=false;}}
function csvFullReportDenied(error,current,entry,source=false){
 if(!current()||![403,409].includes(error.httpStatus))return false;
 if(source){delete entry.options;entry.ack=false;clearRunDetail();activeRun=null;$('result').append(row('来源、合同或当前权限不可用，已清除完整报告证明；保留原请求key，仅在重新核查授权后恢复。'));}
 else{clearApp();clearRunDetail();activeRun=null;$('app-output').append(row('流程、材料或当前权限不可用，已清除定义和输入正文；原请求key保留。请重新打开目录核查。'));}
 return true;
}

function csvFullReportButton(label,id,action){const b=document.createElement('button');b.type='button';b.id=id;b.textContent=label;b.onclick=safe(action);return b;}
function csvFullReportLabel(label,input){const node=document.createElement('label');node.append(document.createTextNode(label),input);return node;}
function csvFullReportCurrent(v){return csvFullReportView===v&&v.identity===token&&v.connection===identityConnectionGeneration&&v.project===$('project-select').value&&v.workspace===workspaceSelectionGeneration&&v.generation===appSelectionGeneration&&v.epoch===csvFullReportEpoch&&!$('apps').hidden&&activeApp===v.app.id;}
async function csvFullReportOpenRun(run,identity,connection,project,selected=()=>true,expected=null){
 const selection=appSelectionGeneration,projectGeneration=projectSelectionGeneration;
 let handoffWorkspace=null;
 const failureCurrent=()=>current()&&(handoffWorkspace===null?selected():handoffWorkspace===workspaceSelectionGeneration&&!$('projects').hidden);
 const current=()=>identity===token&&connection===identityConnectionGeneration&&project===$('project-select').value&&selection===appSelectionGeneration&&projectGeneration===projectSelectionGeneration;
 try{
 const r=await api(`/api/runs/${run}`);if(!current()||!selected()||r.id!==run)return;
 if(expected){
  const bindings=(r.events||[]).filter(e=>e.kind==='CSV_FULL_REPORT_USE').map(e=>e.data),binding=bindings[0],spec=r.contract?.snapshot?.ordinary_csv_report;
  if(bindings.length!==1||binding.workflow_id!==expected.app.id||binding.definition_version!==1||binding.definition_fingerprint!==expected.app.fingerprint||binding.run_id!==run||binding.project_id!==project||binding.contract_fingerprint!==r.contract?.fingerprint||binding.resource_id!==spec?.resource_id)throw Error('Run与所选完整报告流程的冻结版本不匹配');
  if(expected.body&&!expected.instanceReceipt&&(binding.request_key!==expected.body.request_key||binding.request_fingerprint!==await ownerHash(expected.body)||spec.resource_id!==expected.body.resource_id||spec.column!==expected.body.column))throw Error('Run与本次原请求、材料或列不匹配');
  if(expected.instanceReceipt){
   const receipt=expected.instanceReceipt,links=(r.events||[]).filter(e=>e.kind==='CSV_FULL_REPORT_INSTANCE_USE').map(e=>e.data),link=links[0];
   const fields=['namespace','workflow_id','definition_fingerprint','run_id','app_run_id','instance_id','release_id','revision','release_fingerprint','request_key','request_fingerprint','contract_fingerprint','resource_id','principal_id','project_id','runtime_id','data_version'];
   if(links.length!==1||fields.some(key=>receipt[key]===undefined||link[key]!==receipt[key])||link.workflow_id!==expected.app.id||link.definition_fingerprint!==expected.app.fingerprint||link.run_id!==run||link.project_id!==project||link.contract_fingerprint!==r.contract?.fingerprint||link.resource_id!==spec?.resource_id)throw Error('Run与实例原键、Release或冻结版本不匹配');
   if(expected.body&&(link.request_key!==expected.body.request_key||link.request_fingerprint!==await ownerHash(expected.body)||spec.resource_id!==expected.body.resource_id||spec.column!==expected.body.column))throw Error('实例Run与本次材料、列或原请求不匹配');
  }
  if(!current()||!selected())return;
 }

 selectWorkspace('projects');handoffWorkspace=workspaceSelectionGeneration;await showRun(run,true,failureCurrent);
 }catch(error){if(csvFullReportDenied(error,failureCurrent,{}))return;throw error;}
}
function renderCsvFullReportExtraction(r,id,current){
 if(!csvReportPassed(r)||(r.events||[]).some(e=>e.kind==='CSV_FULL_REPORT_USE'))return;
 csvFullReportSource={r,id,owner:csvFullReportOwner(id)};
 const identity=token,connection=identityConnectionGeneration,project=$('project-select').value,workspace=workspaceSelectionGeneration,owner=csvFullReportOwner(id);
 const signature=JSON.stringify([owner,connection,projectSelectionGeneration,runUserSelectionGeneration,workspace,r.version,r.contract.fingerprint]);
 if(csvFullReportExtractionView?.signature===signature){csvFullReportExtractionView.baseCurrent=current;$('result').append(csvFullReportExtractionView.node);csvFullReportExtractionView.render();return;}
 const panel=document.createElement('section');panel.id='csv-full-report-extraction';
 const sourceView={signature,node:panel,baseCurrent:current};csvFullReportExtractionView=sourceView;
 const here=()=>csvFullReportExtractionView===sourceView&&sourceView.baseCurrent()&&identity===token&&connection===identityConnectionGeneration&&project===$('project-select').value&&workspace===workspaceSelectionGeneration&&!$('projects').hidden;

 panel.append(row('将本次已完成的读取 → 精确求和 → 保存完整MD流程另存为可复用流程。保留原合同验收范围；每次新CSV生成独立合同，人工仍 PENDING，未发布。'));
 let entry=csvFullReportExtractions.get(owner);if(!entry){entry={state:'new',name:'完整CSV报告流程',ack:false};csvFullReportExtractions.set(owner,entry);}
 const status=document.createElement('p');status.id='csv-full-report-save-status';status.setAttribute('role','status');
 const proof=document.createElement('pre');proof.id='csv-full-report-save-proof';
 const name=document.createElement('input');name.id='csv-full-report-name';name.maxLength=100;name.value=entry.name;
 const ack=document.createElement('input');ack.type='checkbox';ack.id='csv-full-report-save-ack';ack.checked=entry.ack&&entry.workspace===workspace;entry.ack=ack.checked;entry.workspace=workspace;
 const read=csvFullReportButton('核查完整报告流程','csv-full-report-options',async()=>{
  if(!here()||entry.state==='sending')return;entry.ack=false;ack.checked=false;
  try{const options=await api(`/api/runs/${id}/csv-full-report-workflow-options`);if(!here())return;
   entry.options=options;entry.message='请核对来源及完整三工具流程，再明确勾选保存。';render();
  }catch(error){if(csvFullReportDenied(error,here,entry,true))return;throw error;}

 });
 const save=csvFullReportButton('保存完整报告流程','csv-full-report-save',async()=>{
  if(!here()||entry.state==='sending'||entry.state==='accepted')return;
  const recovery=entry.state==='unknown';if(!recovery&&(!entry.options||!entry.ack||!entry.name.trim()))return;
  if(!recovery)entry.body=Object.freeze({name:entry.name,expected_definition_fingerprint:entry.options.fingerprint,request_key:crypto.randomUUID(),consent:'SAVE_READ_SUM_COMPLETE_MD_WORKFLOW'});
  entry.state='sending';render();
  try{
   const reply=await api(recovery?`/api/runs/${id}/csv-full-report-workflow-requests/${entry.body.request_key}`:`/api/runs/${id}/csv-full-report-workflows`,recovery?'GET':'POST',recovery?undefined:entry.body);
   if(!/^app_[a-f0-9]{32}$/.test(reply?.id)||reply.use_family!=='CSV_FULL_REPORT'||reply.fingerprint!==entry.body.expected_definition_fingerprint)throw Error('流程接受回执不匹配');
   entry.app=reply.id;entry.state='accepted';entry.message='完整流程已保存；从应用目录明确选择后使用。';
  }catch(error){entry.state=!recovery&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus)?'rejected':'unknown';entry.message=entry.state==='unknown'?'结果未知；仅GET原key恢复，勿重复保存。':error.message;if(csvFullReportDenied(error,here,entry,true))return;}finally{entry.renderCurrent?.();}
  if(here())render();
 });
 const open=csvFullReportButton('打开应用目录','csv-full-report-directory',async()=>{if(!here()||!entry.app)return;selectWorkspace('apps');await refreshApps();});
 name.oninput=()=>{if(here()&&entry.state!=='sending'&&entry.state!=='unknown'){entry.name=name.value;entry.ack=false;ack.checked=false;render();}};
 ack.onchange=()=>{if(here()){entry.ack=ack.checked;render();}};
 function render(){const locked=['sending','unknown','accepted','rejected'].includes(entry.state);name.disabled=locked;ack.disabled=locked||!entry.options;read.disabled=locked;save.disabled=entry.state==='sending'||entry.state==='accepted'||entry.state==='rejected'||(entry.state!=='unknown'&&(!entry.ack||!entry.options||!entry.name.trim()));save.textContent=entry.state==='unknown'?'仅GET恢复原保存回执':'保存完整报告流程';open.hidden=!entry.app;status.textContent=entry.message||'尚未核查或保存';proof.textContent=entry.options?JSON.stringify(entry.options,null,2):'';}
 entry.renderCurrent=()=>{if(here())render();};sourceView.render=render;render();panel.append(read,csvFullReportLabel('流程名称',name),proof,csvFullReportLabel('已核对完整三工具流程、来源和版本；明确另存为未发布的可复用流程。',ack),save,open,status);$('result').append(panel);
}
function resumeCsvFullReportExtraction(){const source=csvFullReportSource;if(!source||activeRun!==source.id||source.owner!==csvFullReportOwner(source.id))return;const id=source.id;$('csv-full-report-extraction')?.remove();renderCsvFullReportExtraction(source.r,id,()=>activeRun===id);}
// Draft: the saved full-MD recipe retains its original ordinary Run controller.
// This view only selects a separately saved internal Release/instance.
const csvFullReportDeliveryIntents=new Map();
const csvFullReportDeliveryKey=(v,stage,target='')=>JSON.stringify([v.identity,v.project,v.app.id,stage,target]);
function csvFullReportDelivery(v,panel,onSelect){
 const app=v.app,base=`/api/apps/${app.id}/csv-full-report-delivery`;
 const section=document.createElement('section');section.id='csv-full-report-delivery';
 const heading=document.createElement('h3');heading.textContent='受限内部 Release 与实例';section.append(heading);
 section.append(row('分别核查批准、保存内部版本、创建或选择实例。此处不执行报告、不增加授权；正式发布关闭。未选择实例时仍使用原保存流程。'));
 const state={read:0,selection:0,busy:false,releases:[],instances:[],ready:false,reviewed:null};
 v.delivery=state;
 const here=()=>csvFullReportCurrent(v)&&section.isConnected&&v.delivery===state;
 const status=document.createElement('p');status.id='csv-full-report-delivery-status';status.setAttribute('role','status');
 const proof=document.createElement('pre');proof.id='csv-full-report-delivery-proof';
 const releaseSelect=document.createElement('select');releaseSelect.id='csv-full-report-release-select';
 const instanceSelect=document.createElement('select');instanceSelect.id='csv-full-report-instance-select';
 const approvalAck=document.createElement('input');approvalAck.type='checkbox';approvalAck.id='csv-full-report-release-ack';
 const createAck=document.createElement('input');createAck.type='checkbox';createAck.id='csv-full-report-instance-ack';
 const switchTarget=document.createElement('select');switchTarget.id='csv-full-report-switch-target';
 const switchPrepareAck=document.createElement('input');switchPrepareAck.type='checkbox';switchPrepareAck.id='csv-full-report-switch-prepare-ack';
 const switchAck=document.createElement('input');switchAck.type='checkbox';switchAck.id='csv-full-report-switch-ack';
 let switchReviewed=null;
 const releaseKey=csvFullReportDeliveryKey(v,'release');
 let releaseIntent=csvFullReportDeliveryIntents.get(releaseKey);
 const same=(a,b)=>goalRunCanonical(a)===goalRunCanonical(b);
 const fail=error=>{if(!here())return;if(csvFullReportDenied(error,here,{}))return;status.textContent=error.detail||error.message;};
 function checkDelivery(reply){
  if(reply?.namespace!=='csv-full-report-instances.v1'||reply.formal_publication_enabled!==false||reply.workflow_id!==app.id||reply.definition_fingerprint!==app.fingerprint||!Array.isArray(reply.releases)||!Array.isArray(reply.instances))throw Error('完整报告内部版本目录不匹配');
  if(new Set(reply.releases.map(x=>x.id)).size!==reply.releases.length||new Set(reply.instances.map(x=>x.id)).size!==reply.instances.length)throw Error('重复内部版本或实例');
  for(const r of reply.releases)if(!/^irelease_[a-f0-9]{32}$/.test(r.id)||!/^[a-f0-9]{64}$/.test(r.fingerprint)||r.project_id!==v.project||r.snapshot?.namespace!=='csv-full-report-instances.v1'||r.snapshot?.draft?.id!==app.id||r.snapshot?.draft?.fingerprint!==app.fingerprint||r.snapshot?.formal_publication_enabled!==false)throw Error('内部Release回执不匹配');
  for(const i of reply.instances){const r=reply.releases.find(x=>x.id===i.release_id);if(!/^iinstance_[a-f0-9]{32}$/.test(i.id)||i.project_id!==v.project||i.source_app_id!==app.id||i.runtime_id!==app.definition.runtime_id||!r||i.release_fingerprint!==r.fingerprint||!Number.isSafeInteger(i.revision)||i.revision<1||!Number.isSafeInteger(i.data_version)||!Array.isArray(i.history)||!Array.isArray(i.runs))throw Error('内部实例与版本不匹配');}
  return reply;
 }
 async function readDelivery(){
  const read=++state.read,selection=state.selection;
  const reply=checkDelivery(await api(base));if(!here()||read!==state.read||selection!==state.selection)return null;
  state.releases=reply.releases;state.instances=reply.instances;state.ready=true;
  const selectedRelease=releaseSelect.value,selectedInstance=instanceSelect.value;
  releaseSelect.replaceChildren(new Option('请明确选择用于创建实例的Release',''),...state.releases.map(r=>new Option(`${r.id} · ${r.fingerprint.slice(0,16)}`,r.id)));
  instanceSelect.replaceChildren(new Option('原流程模式（不选择实例）',''),...state.instances.map(i=>new Option(`${i.id} · 修订 ${i.revision} · 结果版本 ${i.data_version}`,i.id)));
  if(state.releases.some(r=>r.id===selectedRelease))releaseSelect.value=selectedRelease;
  if(state.instances.some(i=>i.id===selectedInstance)){instanceSelect.value=selectedInstance;onSelect(state.instances.find(i=>i.id===selectedInstance),false);}
  else if(selectedInstance){onSelect(null,true);throw Error('原所选实例已不可核验');}
  approvalAck.checked=createAck.checked=switchPrepareAck.checked=switchAck.checked=false;state.reviewed=null;switchReviewed=null;refreshSwitchTargets();return reply;
 }
 const read=csvFullReportButton('读取已保存内部版本与实例','csv-full-report-delivery-read',async()=>{
  if(!here()||state.busy)return;state.busy=true;approvalAck.checked=createAck.checked=false;state.reviewed=null;render();
  try{await readDelivery();if(here()){proof.textContent=JSON.stringify({releases:state.releases,instances:state.instances},null,2);status.textContent='只读目录已核查；请选择或分别准备下一步。';}}
  catch(error){fail(error);}finally{state.busy=false;if(here())render();}
 });
 function original(value){const {release,...approval}=value.approval?value.approval:value;return {approval:value.approval||approval,release:value.release||null};}
 function checkApproval(value){
  const {approval,release}=original(value);
  if(!/^iapproval_[a-f0-9]{32}$/.test(approval?.id)||!/^[a-f0-9]{64}$/.test(approval.fingerprint)||!approval.payload||approval.project_id!==v.project||approval.payload?.snapshot?.namespace!=='csv-full-report-instances.v1'||approval.payload?.snapshot?.draft?.id!==app.id||approval.payload?.snapshot?.draft?.fingerprint!==app.fingerprint||!Number.isFinite(approval.expires_at))throw Error('完整Release批准回执不匹配');
  if(release&&(release.approval_id!==approval.id||!/^irelease_[a-f0-9]{32}$/.test(release.id)))throw Error('保存的Release不属于原批准');
  return {approval,release};
 }
 const prepare=csvFullReportButton('准备内部Release批准','csv-full-report-release-prepare',async()=>{
  if(!here()||state.busy||releaseIntent?.state==='sending')return;
  if(!releaseIntent){releaseIntent={state:'new',body:Object.freeze({expected_definition_fingerprint:app.fingerprint,request_key:crypto.randomUUID(),consent:'FREEZE_COMPLETE_MD_RECIPE_AND_CHECK'})};csvFullReportDeliveryIntents.set(releaseKey,releaseIntent);}
  const intent=releaseIntent,recovery=intent.state!=='new';intent.state='sending';state.busy=true;state.reviewed=null;approvalAck.checked=false;render();
  try{
   let hint=null;if(!recovery){hint=await api(base+'/release-approvals','POST',intent.body);if(!here()){intent.state='unknown';return;}}
   const receipt=checkApproval(await api(base+'/release-requests/'+encodeURIComponent(intent.body.request_key)));if(!here()){intent.state='unknown';return;}
   if(hint&&!same(receipt.approval,hint))throw Error('原批准与接受响应不匹配');
   intent.approval=receipt.approval;intent.release=receipt.release;if(receipt.release)intent.commitState='accepted';intent.state='accepted';state.reviewed=intent;
   proof.textContent=JSON.stringify(receipt,null,2);status.textContent=receipt.release?'原Release已保存；尚未创建或采用实例。':'请阅读完整冻结批准，重新勾选后单独保存内部Release。';
  }catch(error){intent.state='unknown';fail(error);}finally{state.busy=false;intent.renderCurrent?.();if(here())render();}
 });
 const commit=csvFullReportButton('明确保存此内部Release','csv-full-report-release-commit',async()=>{
  const intent=releaseIntent;if(!here()||state.busy||!intent?.approval||intent.commitState==='sending')return;
  const recovery=!!intent.commitState;
  if(!recovery&&(state.reviewed!==intent||!approvalAck.checked||intent.approval.expires_at*1000<=Date.now()))return;
  intent.commitState='sending';state.busy=true;approvalAck.checked=false;render();
  try{
   if(!recovery){await api(`/api/internal/approvals/${intent.approval.id}/commit`,'POST',{fingerprint:intent.approval.fingerprint});if(!here()){intent.commitState='unknown';return;}}
   const receipt=checkApproval(await api(base+'/release-requests/'+encodeURIComponent(intent.body.request_key)));if(!here()){intent.commitState='unknown';return;}
   if(!same(receipt.approval.payload,intent.approval.payload)||receipt.approval.id!==intent.approval.id||receipt.approval.fingerprint!==intent.approval.fingerprint||!receipt.release)throw Error('原批准的已保存Release尚未读回；仅能GET恢复');
   intent.release=receipt.release;intent.commitState='accepted';state.reviewed=null;proof.textContent=JSON.stringify(receipt,null,2);await readDelivery();
   if(here())status.textContent='原批准的内部Release已保存；请选择Release并明确创建实例。';
  }catch(error){intent.commitState='unknown';fail(error);}finally{state.busy=false;intent.renderCurrent?.();if(here())render();}
 });
 const another=csvFullReportButton('准备另一个相同配方内部版本','csv-full-report-release-new',async()=>{
  if(!here()||state.busy||releaseIntent?.commitState!=='accepted')return;
  const previous=releaseIntent;
  // This explicit action starts the next approval key without discarding the
  // completed original approval/commit handle.
  releaseIntent={state:'new',body:Object.freeze({expected_definition_fingerprint:app.fingerprint,request_key:crypto.randomUUID(),consent:'FREEZE_COMPLETE_MD_RECIPE_AND_CHECK'}),history:[...(previous.history||[]),{body:previous.body,approval:previous.approval,release:previous.release,commitState:previous.commitState}]};
  csvFullReportDeliveryIntents.set(releaseKey,releaseIntent);state.reviewed=null;approvalAck.checked=false;proof.textContent='新请求键已准备；请单独点击准备批准。定义仍为同一 immutable v1 配方，不迁移目标或执行逻辑。';render();
 });
 const create=csvFullReportButton('明确创建此Release的实例','csv-full-report-instance-create',async()=>{
  const release=state.releases.find(r=>r.id===releaseSelect.value);if(!here()||state.busy||!release)return;
  const key=csvFullReportDeliveryKey(v,'create',release.id);let intent=csvFullReportDeliveryIntents.get(key);
  if(intent?.state==='sending'||intent?.state==='accepted')return;
  if(!intent){if(!createAck.checked)return;intent={state:'new',body:Object.freeze({expected_release_fingerprint:release.fingerprint,request_key:crypto.randomUUID()})};csvFullReportDeliveryIntents.set(key,intent);}
  const recovery=intent.state!=='new',selection=state.selection;intent.state='sending';state.busy=true;createAck.checked=false;render();
  const current=()=>here()&&selection===state.selection&&releaseSelect.value===release.id;
  try{
   let hint=null;if(!recovery){hint=await api(`/api/internal/releases/${release.id}/instances`,'POST',intent.body);if(!current()){intent.state='unknown';return;}}
   const saved=await api(base+`/instance-requests/${release.id}/${encodeURIComponent(intent.body.request_key)}`);if(!current()){intent.state='unknown';return;}
   if(!/^iinstance_[a-f0-9]{32}$/.test(saved.id)||saved.release_id!==release.id||saved.project_id!==v.project||saved.source_app_id!==app.id||saved.runtime_id!==app.definition.runtime_id||saved.release_fingerprint!==release.fingerprint||hint&&hint.id!==saved.id)throw Error('实例创建原键回执不匹配');
   intent.instance=saved.id;intent.state='accepted';proof.textContent=JSON.stringify(saved,null,2);await readDelivery();
   if(here())status.textContent=`已保存实例 ${saved.id}；请在已有实例中明确选择，尚未准备新合同。`;
  }catch(error){intent.state='unknown';fail(error);}finally{state.busy=false;intent.renderCurrent?.();if(here())render();}
 });
 releaseSelect.onchange=()=>{state.selection++;createAck.checked=false;render();};
 instanceSelect.onchange=safe(async()=>{
  if(!here()||state.busy)return;const id=instanceSelect.value,selection=++state.selection;approvalAck.checked=createAck.checked=switchPrepareAck.checked=switchAck.checked=false;state.reviewed=null;switchReviewed=null;onSelect(null,!!id);refreshSwitchTargets();
  if(!id){proof.textContent='原流程模式：本次使用不绑定内部实例。';render();return;}
  state.busy=true;render();
  try{
   const reply=await readDelivery();if(!here()||selection!==state.selection||instanceSelect.value!==id||!reply)return;
   const instance=state.instances.find(i=>i.id===id);if(!instance)throw Error('所选实例不在当前授权目录');
   proof.textContent=JSON.stringify(instance,null,2);onSelect(instance,false);status.textContent='已核查所选实例及当前Release；逐次CSV仍需另行准备并确认新完整合同。';
  }catch(error){if(here()&&selection===state.selection){onSelect(null,true);fail(error);}}finally{state.busy=false;if(here())render();}
 });
 function switchIntent(){const id=instanceSelect.value;return id&&csvFullReportDeliveryIntents.get(csvFullReportDeliveryKey(v,'switch',id));}
 function refreshSwitchTargets(){
  const instance=state.instances.find(i=>i.id===instanceSelect.value),previous=switchTarget.value,intent=switchIntent();
  switchTarget.replaceChildren(new Option('请明确选择同配方的目标Release',''),...state.releases.filter(r=>r.id!==instance?.release_id).map(r=>new Option(`${r.id} · ${r.fingerprint.slice(0,16)}`,r.id)));
  const desired=intent&&!intent.cancelled&&intent.commitState!=='accepted'?intent.body.target_release_id:previous;
  if(state.releases.some(r=>r.id===desired&&r.id!==instance?.release_id))switchTarget.value=desired;
 }
 function checkSwitch(value,intent){
  const {committed,...row}=value.approval?value.approval:value,approval=value.approval||row,p=approval.payload,b=intent.body;
  if(!/^iapproval_[a-f0-9]{32}$/.test(approval.id)||!/^[a-f0-9]{64}$/.test(approval.fingerprint)||!Number.isFinite(approval.expires_at)||!p||p.instance_id!==intent.instance.id||p.from_release_id!==intent.instance.release_id||p.target_release_id!==b.target_release_id||p.target_fingerprint!==b.expected_target_fingerprint||p.revision!==b.expected_revision||p.data_version!==intent.instance.data_version)throw Error('原实例采用批准不匹配');
  const done=value.committed||null;
  if(done&&(done.instance_id!==intent.instance.id||done.release_id!==b.target_release_id||done.revision!==b.expected_revision+1||done.data_version!==intent.instance.data_version||typeof done.namespace!=='string'))throw Error('原实例采用回执不匹配');
  return {approval,committed:done};
 }
 const switchPrepare=csvFullReportButton('准备采用所选内部版本','csv-full-report-switch-prepare',async()=>{
  const instance=state.instances.find(i=>i.id===instanceSelect.value),target=state.releases.find(r=>r.id===switchTarget.value);
  if(!here()||state.busy||!instance||!target||target.id===instance.release_id)return;
  const key=csvFullReportDeliveryKey(v,'switch',instance.id);let intent=csvFullReportDeliveryIntents.get(key);
  if(!intent||intent.cancelled||intent.commitState==='accepted'){
   if(!switchPrepareAck.checked)return;
   const previous=intent;intent={state:'new',instance:{id:instance.id,release_id:instance.release_id,data_version:instance.data_version},body:Object.freeze({target_release_id:target.id,expected_target_fingerprint:target.fingerprint,expected_revision:instance.revision,request_key:crypto.randomUUID()}),history:previous?[...(previous.history||[]),{body:previous.body,approval:previous.approval,committed:previous.committed}]:[]};csvFullReportDeliveryIntents.set(key,intent);
  }
  if(intent.state==='sending')return;
  const recovery=intent.state!=='new',selection=state.selection,current=()=>here()&&selection===state.selection&&instanceSelect.value===instance.id&&switchTarget.value===intent.body.target_release_id;
  state.busy=true;intent.state='sending';switchPrepareAck.checked=switchAck.checked=false;switchReviewed=null;onSelect(null,true);render();
  try{
   let hint=null;if(!recovery){hint=await api(`/api/internal/instances/${instance.id}/csv-full-report-switch-approvals`,'POST',intent.body);if(!current()){intent.state='unknown';return;}}
   const receipt=checkSwitch(await api(`/api/internal/instances/${instance.id}/csv-full-report-switch-requests/${encodeURIComponent(intent.body.request_key)}`),intent);if(!current()){intent.state='unknown';return;}
   if(hint&&!same(checkSwitch(hint,intent),receipt))throw Error('采用批准与原键回读不一致');
   intent.approval=receipt.approval;intent.committed=receipt.committed;intent.state='accepted';switchReviewed=intent;proof.textContent=JSON.stringify(receipt,null,2);status.textContent='请核对原实例、保留结果和目标Release，重新勾选后单独采用。';
  }catch(error){intent.state='unknown';fail(error);}finally{state.busy=false;intent.renderCurrent?.();if(here())render();}
 });
 const switchCommit=csvFullReportButton('明确采用此内部版本','csv-full-report-switch-commit',async()=>{
  const intent=switchIntent();if(!here()||state.busy||!intent?.approval||intent.cancelled||['sending','accepted'].includes(intent.commitState))return;
  const recovery=!!intent.commitState;
  if(!recovery&&(switchReviewed!==intent||!switchAck.checked||intent.approval.expires_at*1000<=Date.now()))return;
  const selection=state.selection,id=intent.instance.id,current=()=>here()&&selection===state.selection&&instanceSelect.value===id;
  state.busy=true;intent.commitState='sending';switchAck.checked=false;onSelect(null,true);render();
  try{
   let hint=null;if(!recovery){hint=await api(`/api/internal/instances/${id}/csv-full-report-switch-requests/${encodeURIComponent(intent.body.request_key)}/commit`,'POST',{fingerprint:intent.approval.fingerprint});if(!current()){intent.commitState='unknown';return;}}
   const receipt=checkSwitch(await api(`/api/internal/instances/${id}/csv-full-report-switch-requests/${encodeURIComponent(intent.body.request_key)}`),intent);if(!current()){intent.commitState='unknown';return;}
   if(!receipt.committed||receipt.approval.id!==intent.approval.id||receipt.approval.fingerprint!==intent.approval.fingerprint||!same(receipt.approval.payload,intent.approval.payload)||hint&&!same(checkSwitch(hint,intent),receipt))throw Error('采用结果尚未精确读回；仅可GET恢复原键');
   // Never retain an old per-use selection through a successful CAS. Read the
   // current directory and history, then require an explicit instance selection.
   instanceSelect.value='';switchTarget.value='';onSelect(null,true);switchReviewed=null;
   await readDelivery();if(!here()){intent.commitState='unknown';return;}
   const saved=state.instances.find(i=>i.id===id),b=intent.body;
   if(!saved||saved.release_id!==b.target_release_id||saved.release_fingerprint!==b.expected_target_fingerprint||saved.revision!==b.expected_revision+1||saved.data_version!==intent.instance.data_version||!saved.history.some(h=>h.kind==='switch'&&h.approval_id===intent.approval.id&&h.previous_release_id===intent.instance.release_id&&h.release_id===b.target_release_id&&h.revision===b.expected_revision+1))throw Error('当前实例与原采用历史不匹配');
   intent.committed=receipt.committed;intent.commitState='accepted';proof.textContent=JSON.stringify({receipt,current_instance:saved},null,2);onSelect(null,false);status.textContent='已采用同一配方内部版本，原结果与历史保留。请重新明确选择实例；尚未准备新合同。';
  }catch(error){intent.commitState='unknown';fail(error);}finally{state.busy=false;intent.renderCurrent?.();if(here())render();}
 });
 const switchCancel=csvFullReportButton('取消本页采用选择','csv-full-report-switch-cancel',async()=>{
  if(!here()||state.busy)return;const cancelled=switchIntent();if(cancelled?.state==='accepted'&&!cancelled.commitState)cancelled.cancelled=true;state.selection++;instanceSelect.value='';switchTarget.value='';switchPrepareAck.checked=switchAck.checked=false;switchReviewed=null;onSelect(null,false);proof.textContent='已清除本页选择和确认；原采用请求键保留，已接受的请求不会因此取消。';render();
 });
 switchTarget.onchange=()=>{state.selection++;switchPrepareAck.checked=switchAck.checked=false;switchReviewed=null;render();};
 approvalAck.onchange=createAck.onchange=switchPrepareAck.onchange=switchAck.onchange=()=>{if(here())render();};
 function render(){
  if(!here())return;
  const release=state.releases.find(r=>r.id===releaseSelect.value),created=release&&csvFullReportDeliveryIntents.get(csvFullReportDeliveryKey(v,'create',release.id));
  if(releaseIntent){const intent=releaseIntent;intent.renderCurrent=()=>{if(here()&&csvFullReportDeliveryIntents.get(releaseKey)===intent)render();};}
  if(created){const intent=created,id=release.id;intent.renderCurrent=()=>{if(here()&&releaseSelect.value===id)render();};}
  read.disabled=state.busy;prepare.disabled=state.busy||releaseIntent?.state==='sending';prepare.textContent=releaseIntent&&releaseIntent.state!=='new'?'仅GET核对原Release批准／回执':'准备内部Release批准';
  approvalAck.disabled=state.busy||state.reviewed!==releaseIntent||!releaseIntent?.approval||!!releaseIntent?.commitState||releaseIntent.approval.expires_at*1000<=Date.now();
  commit.disabled=state.busy||!releaseIntent?.approval||['sending','accepted'].includes(releaseIntent.commitState)||(!releaseIntent.commitState&&(!approvalAck.checked||state.reviewed!==releaseIntent||releaseIntent.approval.expires_at*1000<=Date.now()));commit.textContent=releaseIntent?.commitState==='unknown'?'仅GET恢复原Release保存回执':'明确保存此内部Release';
  releaseSelect.disabled=state.busy||!state.ready;createAck.disabled=state.busy||!release||!!created;create.disabled=state.busy||!release||created?.state==='accepted'||created?.state==='sending'||(!created&&!createAck.checked);create.textContent=created?.state==='unknown'?'仅GET恢复原实例创建回执':'明确创建此Release的实例';
  instanceSelect.disabled=state.busy||!state.ready;
  another.disabled=state.busy||releaseIntent?.commitState!=='accepted';
  const instance=state.instances.find(i=>i.id===instanceSelect.value),switching=switchIntent(),originalSwitch=switching&&!switching.cancelled&&switching.commitState!=='accepted';
  if(switching){const intent=switching,id=instanceSelect.value;intent.renderCurrent=()=>{if(here()&&instanceSelect.value===id)render();};}
  switchTarget.disabled=state.busy||!instance||!!originalSwitch;
  switchPrepareAck.disabled=state.busy||!instance||!switchTarget.value||!!originalSwitch;
  switchPrepare.disabled=state.busy||switching?.state==='sending'||!instance||!switchTarget.value||(!originalSwitch&&!switchPrepareAck.checked);switchPrepare.textContent=originalSwitch?'仅GET核查原采用批准':'准备采用所选内部版本';
  switchAck.disabled=state.busy||!!switching?.cancelled||switchReviewed!==switching||!switching?.approval||!!switching.commitState||switching.approval.expires_at*1000<=Date.now();
  switchCommit.disabled=state.busy||!!switching?.cancelled||!switching?.approval||['sending','accepted'].includes(switching.commitState)||(!switching.commitState&&(!switchAck.checked||switchReviewed!==switching||switching.approval.expires_at*1000<=Date.now()));switchCommit.textContent=switching?.commitState==='unknown'?'仅GET恢复原采用结果':'明确采用此内部版本';switchCancel.disabled=state.busy;
 }
 section.append(read,prepare,proof,csvFullReportLabel('已阅读本页刚回读的完整批准；明确保存受限内部Release。',approvalAck),commit,another,csvFullReportLabel('用于创建实例的Release',releaseSelect),csvFullReportLabel('按所选Release明确创建一个独立实例，不自动运行或采用其他版本。',createAck),create,csvFullReportLabel('选择已有实例或原流程模式',instanceSelect),csvFullReportLabel('采用同配方的另一个内部Release',switchTarget),csvFullReportLabel('已核对当前实例与所选同配方版本，明确准备采用批准。',switchPrepareAck),switchPrepare,csvFullReportLabel('已核对刚回读的完整采用批准；明确采用并保留原结果。',switchAck),switchCommit,switchCancel,status);
 panel.append(section);return {render,instanceSelect};
}

function openCsvFullReport(app,generation,selectionCurrent){
 if(generation!==appSelectionGeneration||!selectionCurrent())return false;
 const v={app,generation,identity:token,connection:identityConnectionGeneration,project:$('project-select').value,workspace:workspaceSelectionGeneration,epoch:csvFullReportEpoch,edit:0,instance:null,instanceGeneration:0,deliveryPending:false};csvFullReportView=v;
 $('app-title').textContent=app.name+' · 完整CSV报告流程 · 定义版本1';$('app-origin').textContent='可分别保存受限内部Release、创建和选择实例；未选择实例时保留原流程用法。每次明确选择CSV及列，准备并另行确认完整事前合同。独立普通Run保存和下载完整MD；0模型请求，人工 PENDING，正式发布关闭。';$('app-manifest').textContent=JSON.stringify(app.definition,null,2);
 const panel=document.createElement('section');panel.id='csv-full-report-use';
 const material=document.createElement('select');material.id='csv-full-report-material';material.append(new Option('请明确选择CSV材料',''),...app.materials.map(m=>new Option(`${m.name} · ${m.id}`,m.id)));
 const column=document.createElement('select');column.id='csv-full-report-column';
 const ack=document.createElement('input');ack.id='csv-full-report-use-ack';ack.type='checkbox';
 const status=document.createElement('p');status.id='csv-full-report-use-status';status.setAttribute('role','status');
 const selected=document.createElement('pre');selected.id='csv-full-report-use-binding';
 let key,entry;
 const here=()=>csvFullReportCurrent(v)&&panel.isConnected;
 function chooseInstance(instance,pending=false){
  v.instanceGeneration++;v.edit++;v.instance=instance;v.deliveryPending=pending;v.ready=false;ack.checked=false;material.value='';column.replaceChildren();
  key=instance?JSON.stringify([v.identity,v.project,app.id,'instance',instance.id]):csvFullReportOwner(app.id);
  entry=csvFullReportUses.get(key);if(!entry){entry={state:'new'};csvFullReportUses.set(key,entry);}
  if(entry.body&&app.materials.some(m=>m.id===entry.body.resource_id)){material.value=entry.body.resource_id;column.append(new Option(entry.body.column,entry.body.column));column.value=entry.body.column;}
  const selectedEntry=entry,selectedKey=key;entry.renderCurrent=()=>{if(here()&&entry===selectedEntry&&csvFullReportUses.get(selectedKey)===selectedEntry)render();};render();
 }
 function expectedRun(intent){return {app,body:intent.body,...(intent.instance?{instanceReceipt:intent.receipt}: {})};}
 const open=csvFullReportButton('打开同一Run的完整合同、结果与MD下载','csv-full-report-open-run',async()=>{
  const intent=entry,selection=v.instanceGeneration;if(!here()||v.deliveryPending||!intent.run)return;
  await csvFullReportOpenRun(intent.run,v.identity,v.connection,v.project,()=>here()&&selection===v.instanceGeneration&&entry===intent,expectedRun(intent));
 });
 const submit=csvFullReportButton('准备新完整报告合同（尚不执行）','csv-full-report-prepare',async()=>{
  if(!here()||v.deliveryPending||['sending','accepted','rejected'].includes(entry.state))return;
  const intent=entry,instance=v.instance,selection=v.instanceGeneration,recovery=intent.state==='unknown';
  const current=()=>here()&&selection===v.instanceGeneration&&entry===intent;
  if(!recovery&&(!ack.checked||!material.value||!column.value||!v.ready))return;
  if(!recovery){
   intent.body=Object.freeze(instance?{expected_revision:instance.revision,expected_release_fingerprint:instance.release_fingerprint,resource_id:material.value,column:column.value,request_key:crypto.randomUUID(),consent:'PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY'}:{expected_version:1,expected_definition_fingerprint:app.fingerprint,resource_id:material.value,column:column.value,request_key:crypto.randomUUID(),consent:'PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY'});
   intent.instance=instance?{id:instance.id,release_id:instance.release_id,revision:instance.revision,release_fingerprint:instance.release_fingerprint,data_version:instance.data_version}:null;
  }
  const path=intent.instance?`/api/internal/instances/${intent.instance.id}/csv-full-report-uses`:`/api/apps/${app.id}/csv-full-report-uses`;
  const receiptPath=intent.instance?`/api/internal/instances/${intent.instance.id}/csv-full-report-requests/${encodeURIComponent(intent.body.request_key)}`:`/api/apps/${app.id}/csv-full-report-use-requests/${encodeURIComponent(intent.body.request_key)}`;
  async function verify(reply){
   if(reply?.workflow_id!==app.id||reply.definition_fingerprint!==app.fingerprint||!/^run_[a-f0-9]{32}$/.test(reply.run_id))throw Error('逐次合同接受回执不匹配');
   if(intent.instance){
    if(reply.namespace!=='csv-full-report-instances.v1'||reply.project_id!==v.project||reply.runtime_id!==app.definition.runtime_id||reply.instance_id!==intent.instance.id||reply.release_id!==intent.instance.release_id||reply.revision!==intent.body.expected_revision||reply.release_fingerprint!==intent.body.expected_release_fingerprint||reply.request_key!==intent.body.request_key||reply.request_fingerprint!==await ownerHash(intent.body)||reply.resource_id!==intent.body.resource_id||!/^iapprun_[a-f0-9]{32}$/.test(reply.app_run_id))throw Error('实例逐次合同原键或版本不匹配');
   }else if(reply.definition_version!==1)throw Error('流程定义版本不匹配');
   return reply;
  }
  intent.state='sending';ack.checked=false;render();
  try{
   let hint=null;
   if(!recovery){hint=await verify(await api(path,'POST',intent.body));if(!current()){intent.state='unknown';intent.message='原视图或所选实例已离开；回原流程仅GET恢复本次key。';return;}}
   const original=await verify(await api(receiptPath));if(!current()){intent.state='unknown';return;}
   if(hint&&(hint.run_id!==original.run_id||intent.instance&&hint.app_run_id!==original.app_run_id))throw Error('接受响应与原key回读不一致；请仅恢复原请求');
   intent.run=original.run_id;intent.receipt=original;intent.state='accepted';intent.message='独立ordinary Run已保存，尚未执行。明确打开完整合同并核对，另行确认后才执行。';
  }catch(error){intent.state=!recovery&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus)?'rejected':'unknown';intent.message=intent.state==='unknown'?'结果未知；仅GET原key恢复，不再POST新合同。':error.message;if(csvFullReportDenied(error,current,intent))return;}finally{intent.renderCurrent?.();}
  if(current())render();
 });
 const fresh=csvFullReportButton('明确另建一次使用','csv-full-report-new-use',async()=>{
  if(!here()||['sending','unknown'].includes(entry.state))return;
  // Keep the completed handle in this scope's local audit trail.
  const previous=entry;entry={state:'new',history:[...(previous.history||[]),{body:previous.body,receipt:previous.receipt,run:previous.run,state:previous.state}]};csvFullReportUses.set(key,entry);chooseInstance(v.instance,v.deliveryPending);
 });
 material.onchange=safe(async()=>{
  if(!here()||v.deliveryPending||entry.state!=='new')return;const edit=++v.edit,id=material.value,selection=v.instanceGeneration;v.ready=false;ack.checked=false;column.replaceChildren();render();if(!id)return;
  const current=()=>here()&&selection===v.instanceGeneration&&edit===v.edit&&id===material.value;
  try{const options=await api(`/api/resources/${id}/csv-report-columns`);if(!current())return;
   if(options.resource_id!==id||options.source_hash!==app.materials.find(m=>m.id===id)?.hash)throw Error('材料版本已改变，请重新打开流程');
   column.append(new Option('请明确选择数值列',''),...options.columns.filter(c=>c.numeric).map(c=>new Option(c.name,c.name)));v.ready=true;
  }catch(error){if(current()){if(csvFullReportDenied(error,current,entry))return;entry.message=error.message;v.ready=false;}}if(current())render();
 });
 column.onchange=()=>{v.edit++;ack.checked=false;render();};ack.onchange=()=>{if(here())render();};
 const history=document.createElement('div');history.id='csv-full-report-history';
 function render(){
  if(!here()||!entry)return;const locked=entry.state!=='new'||v.deliveryPending;
  material.disabled=locked;column.disabled=locked||!v.ready;ack.disabled=locked||!v.ready||!column.value;submit.disabled=v.deliveryPending||['sending','accepted','rejected'].includes(entry.state)||(entry.state!=='unknown'&&(!ack.checked||!v.ready||!column.value));submit.textContent=entry.state==='unknown'?'仅GET恢复原合同回执':'准备新完整报告合同（尚不执行）';open.hidden=v.deliveryPending||!entry.run;fresh.disabled=v.deliveryPending||['sending','unknown'].includes(entry.state);status.textContent=entry.message||(v.deliveryPending?'正在核查所选实例；尚未选择本次材料。':'选择材料与列后，明确准备新合同；不会自动执行。');
  selected.textContent=JSON.stringify({mode:v.instance?'INTERNAL_INSTANCE':'SAVED_WORKFLOW_ONLY',instance:v.instance?{id:v.instance.id,release_id:v.instance.release_id,revision:v.instance.revision,data_version:v.instance.data_version,release_fingerprint:v.instance.release_fingerprint}:null,frozen_request:entry.body||null,accepted_receipt:entry.receipt||null},null,2);
  history.replaceChildren();
  for(const item of (v.deliveryPending?[]:v.instance?v.instance.runs:app.history)){
   const instance=v.instance,selection=v.instanceGeneration;
   history.append(row(`${instance?'实例 '+instance.id+' · Release '+item.release_id+' · ':''}独立Run ${item.run_id} · ${item.status||'已保存'}`,async()=>{
    const current=()=>here()&&selection===v.instanceGeneration&&v.instance===instance;if(!current())return;
    let receipt=null;
    if(instance){try{receipt=await api(`/api/internal/instances/${instance.id}/csv-full-report-requests/${encodeURIComponent(item.request_key)}`);if(!current())return;
      if(receipt.namespace!=='csv-full-report-instances.v1'||receipt.project_id!==v.project||receipt.runtime_id!==app.definition.runtime_id||receipt.request_key!==item.request_key||receipt.instance_id!==instance.id||receipt.run_id!==item.run_id||receipt.app_run_id!==item.app_run_id||receipt.release_id!==item.release_id||receipt.revision!==item.revision||receipt.release_fingerprint!==item.release_fingerprint||receipt.workflow_id!==app.id||receipt.definition_fingerprint!==app.fingerprint)throw Error('历史Run与所选实例/版本不匹配');
     }catch(error){if(csvFullReportDenied(error,current,{}))return;throw error;}}
    if(current())await csvFullReportOpenRun(item.run_id,v.identity,v.connection,v.project,current,{app,...(receipt?{instanceReceipt:receipt}:{})});
   },'打开此Run与报告'));
  }
 }
 // Keep the lifecycle controls in this existing view so navigation uses its
 // established identity/workspace/app epoch fence; no second app canvas.
 const delivery=csvFullReportDelivery(v,panel,chooseInstance);
 panel.append(selected,csvFullReportLabel('本次CSV材料',material),csvFullReportLabel('本次数值列',column),csvFullReportLabel('明确按此保存流程和本次输入准备独立完整MD合同；下一步核对全文后另行确认执行。',ack),submit,open,fresh,status,history);
 $('app-output').replaceChildren(panel);chooseInstance(null);delivery.render();return true;
}
