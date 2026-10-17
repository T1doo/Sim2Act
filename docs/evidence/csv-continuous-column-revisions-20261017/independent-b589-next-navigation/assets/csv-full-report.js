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
  if(expected.body&&(binding.request_key!==expected.body.request_key||binding.request_fingerprint!==await ownerHash(expected.body)||spec.resource_id!==expected.body.resource_id||spec.column!==expected.body.column))throw Error('Run与本次原请求、材料或列不匹配');
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
function openCsvFullReport(app,generation,selectionCurrent){
 if(generation!==appSelectionGeneration||!selectionCurrent())return false;
 const v={app,generation,identity:token,connection:identityConnectionGeneration,project:$('project-select').value,workspace:workspaceSelectionGeneration,epoch:csvFullReportEpoch,edit:0};csvFullReportView=v;
 $('app-title').textContent=app.name+' · 完整CSV报告流程 · 版本1';$('app-origin').textContent='每次使用已有项目授权，明确选择CSV及列，准备并另行确认完整事前合同。独立普通Run保存和下载完整MD；0模型请求，人工 PENDING，未发布。此保存流程没有内部Release或实例。';$('app-manifest').textContent=JSON.stringify(app.definition,null,2);
 const panel=document.createElement('section');panel.id='csv-full-report-use';
 const material=document.createElement('select');material.id='csv-full-report-material';material.append(new Option('请明确选择CSV材料',''),...app.materials.map(m=>new Option(`${m.name} · ${m.id}`,m.id)));
 const column=document.createElement('select');column.id='csv-full-report-column';
 const ack=document.createElement('input');ack.id='csv-full-report-use-ack';ack.type='checkbox';
 const status=document.createElement('p');status.id='csv-full-report-use-status';status.setAttribute('role','status');
 const key=csvFullReportOwner(app.id);let entry=csvFullReportUses.get(key);if(!entry){entry={state:'new'};csvFullReportUses.set(key,entry);}
 const open=csvFullReportButton('打开同一Run的完整合同、结果与MD下载','csv-full-report-open-run',async()=>{if(csvFullReportCurrent(v)&&entry.run)await csvFullReportOpenRun(entry.run,v.identity,v.connection,v.project,()=>csvFullReportCurrent(v),{app,body:entry.body});});
 const submit=csvFullReportButton('准备新完整报告合同（尚不执行）','csv-full-report-prepare',async()=>{
  if(!csvFullReportCurrent(v)||entry.state==='sending'||entry.state==='accepted'||entry.state==='rejected')return;
  const recovery=entry.state==='unknown';if(!recovery&&(!ack.checked||!material.value||!column.value||!v.ready))return;
  if(!recovery)entry.body=Object.freeze({expected_version:1,expected_definition_fingerprint:app.fingerprint,resource_id:material.value,column:column.value,request_key:crypto.randomUUID(),consent:'PREPARE_NEW_COMPLETE_MD_CONTRACT_ONLY'});
  entry.state='sending';render();
  try{
   const reply=await api(recovery?`/api/apps/${app.id}/csv-full-report-use-requests/${entry.body.request_key}`:`/api/apps/${app.id}/csv-full-report-uses`,recovery?'GET':'POST',recovery?undefined:entry.body);
   if(reply?.workflow_id!==app.id||reply.definition_version!==1||reply.definition_fingerprint!==entry.body.expected_definition_fingerprint||!/^run_[a-f0-9]{32}$/.test(reply.run_id))throw Error('逐次合同接受回执不匹配');
   if(!csvFullReportCurrent(v)){entry.state='unknown';entry.message='原视图已离开；请回原流程仅GET恢复本次key。';return;}
   if(!recovery){const original=await api(`/api/apps/${app.id}/csv-full-report-use-requests/${entry.body.request_key}`);if(original.workflow_id!==app.id||original.definition_version!==1||original.definition_fingerprint!==entry.body.expected_definition_fingerprint||original.run_id!==reply.run_id)throw Error('接受响应与原key回读不一致；请仅恢复原请求');}
   entry.run=reply.run_id;entry.state='accepted';entry.message='独立Run已保存，尚未执行。明确打开完整合同并核对，另行确认后才执行。';
  }catch(error){entry.state=!recovery&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus)?'rejected':'unknown';entry.message=entry.state==='unknown'?'结果未知；仅GET原key恢复，不再POST新合同。':error.message;if(csvFullReportDenied(error,()=>csvFullReportCurrent(v),entry))return;}finally{entry.renderCurrent?.();}
  if(csvFullReportCurrent(v))render();
 });
 const fresh=csvFullReportButton('明确另建一次使用','csv-full-report-new-use',async()=>{if(!csvFullReportCurrent(v)||['sending','unknown'].includes(entry.state))return;csvFullReportUses.delete(key);await showApp(app.id,v.project);});
 material.onchange=safe(async()=>{
  if(!csvFullReportCurrent(v)||entry.state!=='new')return;const edit=++v.edit,id=material.value;v.ready=false;ack.checked=false;column.replaceChildren();render();if(!id)return;
  try{const options=await api(`/api/resources/${id}/csv-report-columns`);if(!csvFullReportCurrent(v)||edit!==v.edit||id!==material.value)return;
   if(options.resource_id!==id||options.source_hash!==app.materials.find(m=>m.id===id)?.hash)throw Error('材料版本已改变，请重新打开流程');
   column.append(new Option('请明确选择数值列',''),...options.columns.filter(c=>c.numeric).map(c=>new Option(c.name,c.name)));v.ready=true;
  }catch(error){if(csvFullReportCurrent(v)&&edit===v.edit){if(csvFullReportDenied(error,()=>csvFullReportCurrent(v),entry))return;entry.message=error.message;v.ready=false;}}if(csvFullReportCurrent(v))render();
 });
 column.onchange=()=>{v.edit++;ack.checked=false;render();};ack.onchange=()=>{if(csvFullReportCurrent(v))render();};
 function render(){const locked=entry.state!=='new';material.disabled=locked;column.disabled=locked||!v.ready;ack.disabled=locked||!v.ready||!column.value;submit.disabled=entry.state==='sending'||entry.state==='accepted'||entry.state==='rejected'||(entry.state!=='unknown'&&(!ack.checked||!v.ready||!column.value));submit.textContent=entry.state==='unknown'?'仅GET恢复原合同回执':'准备新完整报告合同（尚不执行）';open.hidden=!entry.run;fresh.disabled=['sending','unknown'].includes(entry.state);status.textContent=entry.message||'选择材料与列后，明确准备新合同；不会自动执行。';}
 if(entry.body&&app.materials.some(m=>m.id===entry.body.resource_id)){material.value=entry.body.resource_id;column.append(new Option(entry.body.column,entry.body.column));column.value=entry.body.column;}
 panel.append(csvFullReportLabel('本次CSV材料',material),csvFullReportLabel('本次数值列',column),csvFullReportLabel('明确按此保存流程和本次输入准备独立完整MD合同；下一步核对全文后另行确认执行。',ack),submit,open,fresh,status);
 const history=document.createElement('div');history.id='csv-full-report-history';for(const item of app.history){history.append(row(`流程版本1 · 独立Run ${item.run_id}`,async()=>{if(csvFullReportCurrent(v))await csvFullReportOpenRun(item.run_id,v.identity,v.connection,v.project,()=>csvFullReportCurrent(v),{app});},'打开此Run与报告'));}
 panel.append(history);$('app-output').replaceChildren(panel);entry.renderCurrent=()=>{if(csvFullReportCurrent(v))render();};render();return true;
}
