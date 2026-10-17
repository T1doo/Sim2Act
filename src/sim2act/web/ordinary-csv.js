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
renderCsvReportForm();
