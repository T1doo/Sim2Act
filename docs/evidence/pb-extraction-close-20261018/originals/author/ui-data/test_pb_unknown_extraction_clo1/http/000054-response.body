// Explicit finite task; arbitrary ordinary Goal drafts remain independent.
const csvReportIntents=new Map(),csvReportConfirmations=new Map();
let csvReportMaterials=[],csvReportGeneration=0,csvReportOptionsReady=false,csvReportContractView=null;
function csvReportIdentity(){return JSON.stringify([token,identityConnectionGeneration,$('project-select').value,projectSelectionGeneration]);}
function csvReportOwner(){return JSON.stringify([token,$('project-select').value]);}
function csvReportCurrent(scope){return scope===csvReportIdentity()&&!$('projects').hidden;}
function clearCsvReport(){csvReportGeneration++;csvReportOptionsReady=false;csvReportMaterials=[];$('csv-report-source').replaceChildren();$('csv-report-column').replaceChildren();renderCsvReportForm();}
function updateCsvReportMaterials(materials,ready){
 const old=$('csv-report-source').value,previous=csvReportMaterials.find(m=>m.id===old),next=ready?materials.filter(m=>m.format==='csv'):[];
 const current=next.find(m=>m.id===old),same=!!previous&&!!current&&previous.hash===current.hash;
 csvReportMaterials=next;
 $('csv-report-source').replaceChildren(new Option('请明确选择CSV材料',''),...next.map(m=>new Option(`${m.name} · ${m.id}`,m.id)));
 if(current)$('csv-report-source').value=old;
 if(!same){csvReportGeneration++;csvReportOptionsReady=false;$('csv-report-column').replaceChildren();}
 renderCsvReportForm();
}
function renderCsvReportForm(){
 const entry=csvReportIntents.get(csvReportOwner()),locked=entry&&['sending','unknown'].includes(entry.state);
 if(locked){for(const [id,value] of [['csv-report-source',entry.body.resource_id],['csv-report-column',entry.body.column]]){if(![...$(id).options].some(o=>o.value===value))$(id).append(new Option(value,value));$(id).value=value;}}
 $('csv-report-source').disabled=!!locked;$('csv-report-column').disabled=!!locked;
 $('csv-report-prepare').disabled=!!locked||entry?.state==='accepted'||!csvReportOptionsReady||!$('csv-report-column').value;
 $('csv-report-recover').hidden=entry?.state!=='unknown';$('csv-report-recover').disabled=entry?.state==='sending';
 $('csv-report-open').hidden=!entry?.run;
 $('csv-report-new').hidden=!entry||entry.state==='sending';
 $('csv-report-status').textContent=entry?.message||'先选择材料与列，冻结合同后仍需另行明确确认执行。';
}
async function readCsvReportColumns(){
 const scope=csvReportIdentity(),workspace=workspaceSelectionGeneration,generation=++csvReportGeneration,rid=$('csv-report-source').value;
 csvReportOptionsReady=false;$('csv-report-column').replaceChildren();renderCsvReportForm();if(!rid)return;
 try{
  // Authoritative original resource read. Server preparation checks every numeric bound.
  const data=await api(`/api/resources/${rid}`);
  if(!csvReportCurrent(scope)||workspace!==workspaceSelectionGeneration||generation!==csvReportGeneration||$('csv-report-source').value!==rid)return;
  if(data.id!==rid||data.format!=='csv'||!csvReportMaterials.some(m=>m.id===rid&&m.hash===data.hash))throw Error('来源版本已变更，请刷新材料列表。');
  // Server guidance reuses the registered CSV parser; the browser does not parse cells.
  const options=await api(`/api/resources/${rid}/csv-report-columns`);
  if(!csvReportCurrent(scope)||workspace!==workspaceSelectionGeneration||generation!==csvReportGeneration||$('csv-report-source').value!==rid)return;
  if(options.source_hash!==data.hash)throw Error('材料版本已改变，请重新读取。');
  $('csv-report-column').replaceChildren(new Option('请明确选择数值列',''),...options.columns.filter(c=>c.numeric).map(c=>new Option(c.name,c.name)));
  csvReportOptionsReady=true;$('csv-report-status').textContent=options.error||'列已读取；选列后准备完整合同。';
 }catch(error){if(csvReportCurrent(scope)&&workspace===workspaceSelectionGeneration&&generation===csvReportGeneration){csvReportOptionsReady=false;$('csv-report-status').textContent=error.message;}}
 finally{if(csvReportCurrent(scope)&&workspace===workspaceSelectionGeneration&&generation===csvReportGeneration){const message=$('csv-report-status').textContent;renderCsvReportForm();$('csv-report-status').textContent=message;}}
}
async function submitCsvReport(recover=false){
 const owner=csvReportOwner(),scope=csvReportIdentity();let entry=csvReportIntents.get(owner);
 if(recover){if(entry?.state!=='unknown')return;}
 else{
  if(entry&&['sending','unknown','accepted'].includes(entry.state)||!csvReportOptionsReady||!$('csv-report-column').value)return;
  entry={body:{resource_id:$('csv-report-source').value,column:$('csv-report-column').value,request_key:crypto.randomUUID()}};csvReportIntents.set(owner,entry);
 }
 if(!recover)runUserSelectionGeneration++;
 const userSelection=runUserSelectionGeneration,workspace=workspaceSelectionGeneration;
 const current=()=>csvReportCurrent(scope)&&workspace===workspaceSelectionGeneration&&userSelection===runUserSelectionGeneration&&csvReportIntents.get(owner)===entry;
 entry.state='sending';entry.message='正在持久保存事前合同，尚未确认执行…';renderCsvReportForm();
 try{
  const receipt=await api(`/api/projects/${$('project-select').value}/csv-report-runs`,'POST',entry.body);
  if(!/^run_[a-f0-9]{32}$/.test(receipt?.run_id))throw Error('合同接受回执无效；请恢复同一请求。');
  entry.run=receipt.run_id;entry.state='accepted';entry.message=`事前合同已保存：${entry.run}。请在成果画布核对并明确确认。`;
  if(current())await showRun(entry.run,false,current);
 }catch(error){entry.state=!entry.wasUncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus)?'rejected':'unknown';if(entry.state==='unknown')entry.wasUncertain=true;entry.message=entry.state==='unknown'?'结果未知；仅恢复同一请求，勿另建重复任务。':error.message;}
 finally{if(csvReportCurrent(scope)&&csvReportIntents.get(owner)===entry)renderCsvReportForm();}
}
function csvReportPassed(r){
 const spec=r.contract?.snapshot?.ordinary_csv_report,report=r.result?.task_acceptance;
 return spec?.version==='ordinary-csv-report.v1'&&spec.checker==='csv-report-independent.v1'&&/^[a-f0-9]{64}$/.test(r.contract?.fingerprint)&&/^[a-f0-9]{64}$/.test(report?.contract_fingerprint)&&r.status==='SUCCEEDED'&&r.result?.goal_acceptance==='PASS_CSV_REPORT_CONTRACT'&&r.result.model_requests===0&&
  report?.version===spec.version&&report.checker===spec.checker&&report.contract_fingerprint===r.contract.fingerprint&&report.status==='PASS'&&report.whole_task_accepted===true&&
  report.scope==='EXPLICIT_CSV_REPORT_CONTRACT_ONLY'&&report.general_semantic_acceptance==='NOT_RUN'&&report.owner_acceptance==='PENDING'&&report.formal_publication_enabled===false;
}
function csvReportContractOwner(id){return JSON.stringify([csvReportIdentity(),runUserSelectionGeneration,id]);}
function clearCsvReportContract(){csvReportContractView=null;}
function resumeCsvReportContract(){
 const previous=csvReportContractView;
 if(!previous||activeRun!==previous.run||previous.owner!==csvReportContractOwner(previous.run))return;
 const owner=previous.owner,id=previous.run;
 $('csv-report-contract')?.remove();
 renderCsvReportContract(previous.result,id,()=>activeRun===id&&owner===csvReportContractOwner(id));
}
function renderCsvReportContract(r,id,current){
 const spec=r.contract?.snapshot?.ordinary_csv_report;if(!spec){clearCsvReportContract();return;}
 const scope=csvReportIdentity(),workspace=workspaceSelectionGeneration,owner=csvReportContractOwner(id),viewScope=owner+':'+workspace;
 const sameView=csvReportContractView?.scope===viewScope;
 const view=sameView?csvReportContractView:{scope:viewScope,owner,run:id,ackGeneration:0};csvReportContractView=view;view.result=r;
 const ownerCurrent=()=>csvReportContractView===view&&activeRun===id&&csvReportCurrent(scope)&&workspace===workspaceSelectionGeneration&&owner===csvReportContractOwner(id);
 const stillCurrent=()=>current()&&ownerCurrent();
 const section=document.createElement('section');section.id='csv-report-contract';
 const heading=document.createElement('h3');heading.textContent='本次完整事前合同（只读）';section.append(heading);
 const proof=document.createElement('pre');proof.id='csv-report-proof';proof.textContent=JSON.stringify({run:id,run_version:r.version,contract_fingerprint:r.contract.fingerprint,
  deadline:r.ordinary_csv?.deadline,rules:r.ordinary_csv?.rules,...spec},null,2);section.append(proof);
 section.append(row(r.ordinary_csv?.confirmed?'此精确合同已确认；通用语义 NOT_RUN，人工 PENDING。':'以下为冻结报告预览，尚未保存成果。确认前不会执行工具或调用模型。'));
 const preview=document.createElement('pre');preview.id='csv-report-preview';preview.textContent=spec.report_text;section.append(preview);
 if(r.status==='WAITING_APPROVAL'&&!r.ordinary_csv?.confirmed){
  const key=JSON.stringify([token,$('project-select').value,id]);let entry=csvReportConfirmations.get(key);
  if(!entry){entry={body:{version:r.version,contract_fingerprint:r.contract.fingerprint,request_key:crypto.randomUUID()},state:'ready',ack:false};csvReportConfirmations.set(key,entry);}
  if(!sameView&&entry.state==='ready'){entry.ack=false;entry.message='请核对当前完整合同并重新明确勾选。';}
  const label=document.createElement('label'),ack=document.createElement('input');ack.type='checkbox';ack.id='csv-report-ack';ack.checked=sameView&&entry.ack;
  label.append(ack,document.createTextNode('已核对来源版本/hash、列与数值规则、记录数、完整MD及保存回读要求，明确执行此合同。'));
  const button=document.createElement('button');button.id='csv-report-confirm';button.type='button';
  const status=document.createElement('p');status.id='csv-report-confirm-status';status.setAttribute('role','status');
  const render=()=>{ack.disabled=entry.state==='sending'||entry.state==='unknown';button.disabled=!entry.ack||entry.state==='sending'||entry.state==='accepted'||entry.state==='rejected';button.textContent=entry.state==='unknown'?'恢复同一确认的回执':'确认此合同并提交后台执行';status.textContent=entry.message||'尚未确认执行';};
  entry.renderCurrent=()=>{if(stillCurrent())render();};
  ack.onchange=safe(async()=>{
   if(!stillCurrent()||ack.disabled)return;
   const generation=++view.ackGeneration;entry.ack=false;render();if(!ack.checked)return;
   entry.message='正在重新核验原Run的完整合同…';render();
   try{
    const fresh=await api(`/api/runs/${id}`);
    if(!stillCurrent()||generation!==view.ackGeneration||!ack.checked)return;
    if(fresh?.id!==id||fresh.status!=='WAITING_APPROVAL'||fresh.version!==entry.body.version||fresh.ordinary_csv?.confirmed!==false||fresh.contract?.fingerprint!==entry.body.contract_fingerprint||JSON.stringify(fresh.contract?.snapshot)!==JSON.stringify(r.contract.snapshot))throw Error('合同状态已改变；请重新读取完整合同后核对。');
    entry.ack=true;entry.message='完整合同回读一致；可明确提交本次确认。';
   }catch(error){
    if(!stillCurrent()||generation!==view.ackGeneration)return;
    ack.checked=false;entry.ack=false;entry.message=error.message;
    if(error.httpStatus===403){clearRunDetail();activeRun=null;$('result').append(row('原Run读取授权不可用，已清除合同；未发送确认。'));return;}
   }finally{if(stillCurrent()&&generation===view.ackGeneration)render();}
  });
  button.onclick=safe(async()=>{
   if(!stillCurrent()||!entry.ack||['sending','accepted','rejected'].includes(entry.state))return;
   entry.state='sending';entry.message='正在提交本次明确确认…';render();
   try{
    const receipt=await api(`/api/runs/${id}/confirm-csv-report`,'POST',entry.body);
    if(receipt?.run_id!==id||receipt.confirmed_contract!==entry.body.contract_fingerprint||receipt.confirmed_version!==entry.body.version)throw Error('确认回执不匹配，请恢复原请求。');
    entry.state='accepted';entry.message='合同已确认；只运行原有工具，0模型请求。';if(ownerCurrent())await showRun(id,false,ownerCurrent);
   }catch(error){entry.state=!entry.wasUncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus)?'rejected':'unknown';if(entry.state==='unknown')entry.wasUncertain=true;entry.message=entry.state==='unknown'?'确认结果未知；仅用原key恢复，不自动重发。':error.message;}
   finally{if(ownerCurrent())entry.renderCurrent?.();}
  });
  const read=document.createElement('button');read.type='button';read.id='csv-report-confirm-read';read.textContent='重新读取原Run完整合同（只读）';
  read.onclick=safe(async()=>{if(stillCurrent())await showRun(id,false,ownerCurrent);});
  render();section.append(label,button,read,status);
 }
 $('result').append(section);
}
$('csv-report-source').onchange=safe(readCsvReportColumns);
$('csv-report-column').onchange=renderCsvReportForm;
$('csv-report-form').onsubmit=safe(async event=>{event.preventDefault();await submitCsvReport();});
$('csv-report-recover').onclick=safe(()=>submitCsvReport(true));
$('csv-report-open').onclick=safe(async()=>{const entry=csvReportIntents.get(csvReportOwner());if(entry?.run)await showRun(entry.run,true);});
$('csv-report-new').onclick=()=>{const entry=csvReportIntents.get(csvReportOwner());if(entry?.state==='sending')return;if(entry?.state==='unknown'){$('csv-report-status').textContent='请先恢复未知原请求，不能另建重复任务。';return;}csvReportIntents.delete(csvReportOwner());renderCsvReportForm();};

// Explicit subtask extraction. A source report PASS never becomes this app's MD promise.
const csvSumIntents=new Map();let csvSumView=null;
function csvSumOwner(id){return JSON.stringify([token,$('project-select').value,id]);}
function clearCsvSumExtraction(){csvSumView=null;}
function resumeCsvSumExtraction(){
 const old=csvSumView;if(!old||activeRun!==old.id||old.owner!==csvSumOwner(old.id))return;
 const owner=old.owner,id=old.id,workspace=workspaceSelectionGeneration;
 old.node.remove();csvSumView=null;
 safe(()=>showRun(id,false,()=>activeRun===id&&owner===csvSumOwner(id)&&workspace===workspaceSelectionGeneration))();
}
function renderCsvSumExtraction(r,id,baseCurrent){
 if(!csvReportPassed(r))return;
 const owner=csvSumOwner(id),connection=identityConnectionGeneration,project=projectSelectionGeneration,
  selection=runUserSelectionGeneration,workspace=workspaceSelectionGeneration;
 const signature=JSON.stringify([owner,connection,project,selection,workspace,r.version,r.contract.fingerprint]);
 if(csvSumView?.signature===signature){csvSumView.baseCurrent=baseCurrent;$('result').append(csvSumView.node);csvSumView.render();return;}
 const node=document.createElement('section');node.id='csv-sum-extraction';
 const view={id,owner,node,busy:false,options:null,signature,baseCurrent};csvSumView=view;
 const current=()=>csvSumView===view&&node.isConnected&&view.baseCurrent()&&owner===csvSumOwner(id)&&connection===identityConnectionGeneration&&project===projectSelectionGeneration&&selection===runUserSelectionGeneration&&workspace===workspaceSelectionGeneration&&!$('projects').hidden;
 const element=(tag,id,text)=>{const el=document.createElement(tag);el.id=id;if(text)el.textContent=text;return el;};
 node.append(element('h3','csv-sum-heading','将本次成功任务的求和步骤保存为应用'),element('p','csv-sum-scope','原完整CSV报告合同 PASS；本次仅提取只读求和，输出来源、列、记录数、合计及hash。不包含原MD生成或保存，也不继承原报告验收。新应用仍待新输入验证、人工适用范围 PENDING，语义 UNKNOWN，内部未发布。'));
 const status=element('p','csv-sum-status');status.setAttribute('role','status');
 const proof=element('pre','csv-sum-proof');
 const choose=element('select','csv-sum-target');choose.setAttribute('aria-label','另一份已有授权CSV草案');choose.append(new Option('先读取可用来源和目标',''));
 const name=element('input','csv-sum-name');name.value='从普通成功任务提取的求和';name.maxLength=200;name.setAttribute('aria-label','求和应用名称');
 const ack=element('input','csv-sum-ack');ack.type='checkbox';
 const label=element('label','csv-sum-consent');label.append(ack,'我已核对来源及另一份已有授权CSV，明确只提取求和步骤，不包含原完整MD报告；随后独立验证新输入。');
 const key=element('input','csv-sum-key');key.maxLength=100;key.setAttribute('aria-label','原提取请求key');key.value=csvSumIntents.get(owner)?.body?.request_key||'';
 const retryAck=element('input','csv-sum-retry-ack');retryAck.type='checkbox';const retryLabel=element('label','csv-sum-retry-label');retryLabel.append(retryAck,'仅明确重试保留的原key与原正文；不另建请求。');
 const make=(id,text,fn)=>{const el=element('button',id,text);el.type='button';el.onclick=safe(fn);return el;};
 const pending=()=>csvSumIntents.get(owner);
 function render(){const p=pending();read.disabled=view.busy||Boolean(p);choose.disabled=view.busy||Boolean(p);name.disabled=choose.disabled;ack.disabled=choose.disabled;submit.disabled=view.busy||Boolean(p)||!view.options||!choose.value||!name.value.trim()||!ack.checked;recover.disabled=view.busy||!key.value.trim();open.disabled=view.busy||p?.state!=='accepted';retry.hidden=p?.state!=='unknown'||!p.body;retry.disabled=view.busy||!retryAck.checked;retryLabel.hidden=retry.hidden;key.disabled=view.busy;}
 function failed(error){if(!current())return;if(error.httpStatus===403||error.httpStatus===409){clearRunDetail();activeRun=null;$('result').append(row('来源或授权已不可用，已清除原证明；请重新读取当前任务。'));return;}status.textContent=error.message;}
 async function receipt(value,expected=null){
  if(value?.state!=='CANDIDATE_ONLY'||value.source_run_id!==id||value.source_run_status!=='SUCCEEDED'||value.source_task_accepted!==true||value.selected_scope!=='CSV_SUM_ONLY'||value.full_md_report_included!==false||value.candidate_task_acceptance!=='NOT_RUN'||value.semantic_status!=='UNKNOWN'||value.owner_acceptance!=='PENDING'||value.formal_publication_enabled!==false||value.publishable!==false||value.model_requests!==0||value.generator!=='TRUSTED_ORDINARY_CSV_SUM.v1'||!/^app_[a-f0-9]{32}$/.test(value.id)||!naturalGoalFp(value.candidate_fingerprint)||await registeredHash(value.request)!==value.request_fingerprint)throw Error('VERSION_CONFLICT');
  const req=value.request;if(req.source_run_id!==id||req.consent!=='EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT'||req.expected_proof_fingerprint!==value.source_proof_fingerprint)throw Error('VERSION_CONFLICT');
  const {source_run_id,...body}=req;body.request_key=value.request_key;
  if(expected&&goalRunCanonical(expected)!==goalRunCanonical(body))throw Error('VERSION_CONFLICT');
  return {body,state:'accepted',receipt:value};
 }
 const read=make('csv-sum-read','读取求和来源与已有授权CSV',async()=>{
  if(!current()||view.busy||pending())return;view.busy=true;ack.checked=false;render();
  try{const value=await api(`/api/runs/${id}/csv-sum-candidate-options`);if(!current())return;
   if(value.generator!=='TRUSTED_ORDINARY_CSV_SUM.v1'||value.full_md_report_included!==false||value.source_task_accepted!==true||value.proof?.source_run_id!==id||await registeredHash(value.proof)!==value.source_proof_fingerprint)throw Error('VERSION_CONFLICT');
   if(!current())return;view.options=value;choose.replaceChildren(new Option('请选择另一份已有授权CSV',''),...value.targets.map(t=>new Option(t.name,t.id)));proof.textContent=JSON.stringify(value.proof,null,2);status.textContent='请选择目标并核对材料/hash/runtime；不会新增身份或授权。';
  }catch(error){failed(error);}finally{view.busy=false;if(current())render();}
 });
 const submit=make('csv-sum-submit','明确保存仅求和应用',()=>send(false));
 async function send(replay){
  if(!current()||view.busy)return;let p=pending();
  if(replay){if(p?.state!=='unknown'||!retryAck.checked)return;}
  else{if(p||!ack.checked||!view.options||!choose.value||!name.value.trim())return;const t=view.options.targets.find(t=>t.id===choose.value);if(!t)return;p={body:{expected_proof_fingerprint:view.options.source_proof_fingerprint,target_app_id:t.id,expected_target_draft_fingerprint:t.fingerprint,name:name.value.trim(),request_key:crypto.randomUUID(),consent:'EXTRACT_SUM_ONLY_WITHOUT_MD_REPORT'},state:'sending'};csvSumIntents.set(owner,p);key.value=p.body.request_key;}
  p.state='sending';view.busy=true;render();
  try{const value=await api(`/api/runs/${id}/csv-sum-candidates`,'POST',p.body);const accepted=await receipt(value,p.body);if(pending()===p)csvSumIntents.set(owner,accepted);if(current())status.textContent='仅求和候选已保存；请明确打开并验证新输入。';}
  catch(error){p.state='unknown';if(current())status.textContent='受理结果 UNKNOWN；保留原key和正文，先GET恢复。未查到不证明未受理。';if(error.httpStatus===403)failed(error);}
  finally{view.busy=false;if(current())render();}
 }
 const recover=make('csv-sum-recover','仅GET恢复原key回执',async()=>{
  if(!current()||view.busy||!key.value.trim())return;view.busy=true;render();
  try{const requestedKey=key.value.trim(),old=pending(),value=await api(`/api/runs/${id}/csv-sum-requests/${encodeURIComponent(requestedKey)}`);if(value.request_key!==requestedKey)throw Error('VERSION_CONFLICT');const accepted=await receipt(value,old?.body||null);if(!current())return;csvSumIntents.set(owner,accepted);status.textContent='已只读恢复原请求；尚未打开或执行应用。';}
  catch(error){failed(error);}finally{view.busy=false;if(current())render();}
 });
 const retry=make('csv-sum-retry','明确重试原key原正文',()=>send(true));
 const open=make('csv-sum-open','打开仅求和应用并验证新输入',async()=>{
  const p=pending();if(!current()||view.busy||p?.state!=='accepted')return;view.busy=true;render();
  try{const value=await api(`/api/runs/${id}/csv-sum-requests/${encodeURIComponent(p.body.request_key)}`),fresh=await receipt(value,p.body);if(!current())return;
   let handedOff=false,appGeneration=null;
   const appCurrent=()=>handedOff?owner===csvSumOwner(id)&&connection===identityConnectionGeneration&&project===projectSelectionGeneration&&appGeneration===appSelectionGeneration&&activeApp===fresh.receipt.id:current();
   const shown=await showApp(fresh.receipt.id,$('project-select').value,g=>{appGeneration=g;},appCurrent,async a=>{const marker=a.candidate?.task_proof;if(a.fingerprint!==fresh.receipt.candidate_fingerprint||await registeredHash(a.candidate)!==a.fingerprint||a.candidate.manifest.source_run_ref!==id||marker?.proof?.kind!=='completed_ordinary_csv_report_sum_source.v1'||marker.proof_fingerprint!==fresh.receipt.source_proof_fingerprint||marker.target.app_id!==p.body.target_app_id||marker.target.fingerprint!==p.body.expected_target_draft_fingerprint)throw Error('VERSION_CONFLICT');});
   if(shown&&current()&&appGeneration===appSelectionGeneration&&activeApp===fresh.receipt.id){handedOff=true;selectWorkspace('apps');}
  }catch(error){if(current())clearApp();failed(error);}finally{view.busy=false;if(current())render();}
 });
 choose.onchange=()=>{ack.checked=false;const t=view.options?.targets.find(t=>t.id===choose.value);status.textContent=t?`目标材料 ${t.resource_id} · hash ${t.source_hash} · 沿用runtime ${t.runtime_id}`:'';render();};
 name.oninput=()=>{ack.checked=false;render();};ack.onchange=render;retryAck.onchange=render;key.oninput=render;
 view.render=render;node.append(read,choose,name,label,submit,proof,key,recover,retryLabel,retry,open,status);$('result').append(node);render();
}
renderCsvReportForm();
