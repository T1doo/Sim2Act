"use strict";
// Explicit local-record lifecycle. Existing authenticated API/Worker own all writes.
let localRecordsView=null,localRecordsEpoch=0;
const localRecordsIntents=new Map();
const localRecordsControlIntents=new Map();
const localRecordsVersion="local-record-app.v1";
const localRecordsSame=(a,b)=>goalRunCanonical(a)===goalRunCanonical(b);
function clearLocalRecordsView(){
 localRecordsEpoch++;localRecordsView=null;
 const panel=$("local-records-panel");if(panel){panel.hidden=true;panel.replaceChildren();}
}
function localRecordsCurrent(v){return !!v&&localRecordsView===v&&v.epoch===localRecordsEpoch&&v.identity===token&&v.connection===identityConnectionGeneration&&v.project===$("project-select").value&&v.workspace===workspaceSelectionGeneration&&v.generation===appSelectionGeneration&&!$("apps").hidden&&v.panel.isConnected&&(v.selectionCurrent?.()??true)&&(v.app?activeApp===v.app.id:activeApp===null);}
function localRecordsFence(v,{edit=true,read=true,selection=true}={}){
 const epoch=v.epoch,edited=v.edit,serial=v.read,selected=v.selection;
 return ()=>localRecordsCurrent(v)&&epoch===v.epoch&&(!edit||edited===v.edit)&&(!read||serial===v.read)&&(!selection||selected===v.selection);
}
function localRecordsScope(v,stage,anchor=""){return JSON.stringify([v.identity,v.project,v.app?.id||"",v.instance?.id||"",stage,anchor]);}
function localRecordsNode(tag,id,text){const node=document.createElement(tag);if(id)node.id=id;if(text!==undefined)node.textContent=text;return node;}
function localRecordsLabel(text,input){const label=document.createElement("label");label.append(document.createTextNode(text),input);return label;}
function localRecordsButton(label,id,action){const button=localRecordsNode("button",id,label);button.type="button";button.onclick=safe(action);return button;}
function localRecordsInput(id,options={}){const input=localRecordsNode(options.multiline?"textarea":"input",id);if(!options.multiline)input.type=options.type||"text";if(options.maxLength)input.maxLength=options.maxLength;if(options.required)input.required=true;input.autocomplete="off";return input;}
function localRecordsSelect(id,choices){const input=localRecordsNode("select",id);input.append(...choices.map(([label,value])=>new Option(label,value)));return input;}
function localRecordsEdited(v){if(!localRecordsCurrent(v))return;v.edit++;v.preview=null;v.previewCurrent=null;v.runAck.checked=false;v.previewText.textContent="输入已变化，请重新预览精确变更。已有未知请求仍须用原 key 核对。";v.previewProof.textContent="";localRecordsButtons(v);}
function localRecordsStatus(v,message){if(localRecordsCurrent(v))v.status.textContent=message;}
function localRecordsBusy(v,busy){v.busyCount=Math.max(0,(v.busyCount||0)+(busy?1:-1));v.busy=v.busyCount>0;if(localRecordsCurrent(v))localRecordsButtons(v);}
function localRecordsProof(parent,id,label){const detail=localRecordsNode("details"),summary=localRecordsNode("summary",null,label),proof=localRecordsNode("pre",id);detail.append(summary,proof);parent.append(detail);return proof;}
function localRecordsBuild(app,generation,selectionCurrent=()=>true){
 const panel=$("local-records-panel");panel.hidden=false;panel.replaceChildren();
 const v={identity:token,connection:identityConnectionGeneration,project:$("project-select").value,workspace:workspaceSelectionGeneration,generation,epoch:localRecordsEpoch,panel,app,ready:!app,selectionCurrent,selection:0,edit:0,read:0,busy:false,delivery:null,instance:null,preview:null,previewCurrent:null,run:null};localRecordsView=v;
 panel.append(localRecordsNode("h2",null,app?app.name:"新建本地记录应用"),localRecordsNode("p",null,"固定类型表单：创建记录或明确修改状态。每次变更先预览，再单独确认后台写入；0 模型请求，内部版本未发布。记录 ID 与修订保留，历史不会被状态变更覆盖。"));
 v.status=localRecordsNode("p","local-records-status");v.status.setAttribute("role","status");v.status.setAttribute("aria-live","polite");panel.append(v.status);
 const creation=localRecordsNode("section","local-records-create");creation.hidden=!!app;creation.append(localRecordsNode("h3",null,"1. 保存固定表单应用"));
 v.name=localRecordsInput("local-records-name",{maxLength:200,required:true});v.name.value="本地记录与状态";
 v.goal=localRecordsInput("local-records-goal",{maxLength:4000,multiline:true,required:true});v.goal.value="保存本项目的本地记录，保留标题与正文，并明确将 OPEN 状态修改为 DONE；保留每条记录的修订和历史。";
 v.createAck=localRecordsInput("local-records-create-ack",{type:"checkbox"});v.create=localRecordsButton("明确保存本地记录应用","local-records-save-app",()=>localRecordsCreate(v));
 creation.append(localRecordsLabel("应用名称 ",v.name),localRecordsLabel("用途与约束 ",v.goal),localRecordsLabel("我确认保存本项目的固定本地记录表单应用；不自动创建版本或运行。",v.createAck),v.create);
 v.savedAppOpen=localRecordsButton("打开已保存的本地记录应用","local-records-open-saved-app",()=>localRecordsOpenSaved(v));creation.append(v.savedAppOpen);panel.append(creation);
 const lifecycle=localRecordsNode("section","local-records-lifecycle");lifecycle.hidden=!app;lifecycle.append(localRecordsNode("h3",null,"2. 单独保存内部 Release"));
 v.prepareRelease=localRecordsButton("准备精确内部版本","local-records-release-prepare",()=>localRecordsPrepareRelease(v));
 v.releaseAck=localRecordsInput("local-records-release-ack",{type:"checkbox"});v.commitRelease=localRecordsButton("确认保存此内部 Release","local-records-release-commit",()=>localRecordsCommitRelease(v));
 lifecycle.append(v.prepareRelease);v.releaseProof=localRecordsProof(lifecycle,"local-records-release-proof","精确版本快照与指纹");lifecycle.append(localRecordsLabel("已阅读精确快照，明确保存此内部 Release。",v.releaseAck),v.commitRelease,localRecordsNode("h3",null,"3. 明确创建或选择实例"));
 v.releaseSelect=localRecordsSelect("local-records-release-select",[["请明确选择已保存 Release",""]]);v.instanceAck=localRecordsInput("local-records-instance-ack",{type:"checkbox"});v.createInstance=localRecordsButton("明确创建所选 Release 的实例","local-records-instance-create",()=>localRecordsCreateInstance(v));
 v.instanceSelect=localRecordsSelect("local-records-instance-select",[["请明确选择实例",""]]);v.deliveryRefresh=localRecordsButton("读取版本与实例目录（只读）","local-records-delivery-read",()=>localRecordsReadDelivery(v));
 lifecycle.append(localRecordsLabel("已保存版本 ",v.releaseSelect),localRecordsLabel("明确创建独立记录集合实例；不会自动写入业务记录。",v.instanceAck),v.createInstance,localRecordsLabel("独立实例 ",v.instanceSelect),v.deliveryRefresh);panel.append(lifecycle);
 const operations=localRecordsNode("section","local-records-operations");operations.hidden=true;v.operations=operations;operations.append(localRecordsNode("h3",null,"4. 填写并预览本次变更"));
 v.instanceInfo=localRecordsNode("p","local-records-instance-info");operations.append(v.instanceInfo);
 v.command=localRecordsSelect("local-records-command",[["创建记录","CREATE"],["修改记录状态","SET_STATE"]]);operations.append(localRecordsLabel("本次操作 ",v.command));
 v.createFields=localRecordsNode("fieldset");v.createFields.append(localRecordsNode("legend",null,"新记录"));v.title=localRecordsInput("local-records-title",{maxLength:200,required:true});v.details=localRecordsInput("local-records-details",{maxLength:2000,multiline:true,required:true});v.createFields.append(localRecordsLabel("标题 ",v.title),localRecordsLabel("记录正文 ",v.details),localRecordsNode("p",null,"新记录初始状态为 OPEN；保存后使用稳定 record_id 和 revision=1。"));
 v.stateFields=localRecordsNode("fieldset");v.stateFields.hidden=true;v.stateFields.append(localRecordsNode("legend",null,"更新已有记录"));v.recordSelect=localRecordsSelect("local-records-record-select",[["请选择当前记录",""]]);v.state=localRecordsSelect("local-records-state",[["完成（仅 OPEN → DONE）","DONE"]]);v.reason=localRecordsInput("local-records-reason",{multiline:true,maxLength:500,required:true});v.stateFields.append(localRecordsLabel("记录及当前修订 ",v.recordSelect),localRecordsLabel("目标状态 ",v.state),localRecordsLabel("本次变更依据 ",v.reason));operations.append(v.createFields,v.stateFields);
 v.previewButton=localRecordsButton("预览本次精确变更","local-records-preview",()=>localRecordsPreview(v));operations.append(v.previewButton);v.previewText=localRecordsNode("div","local-records-preview-summary");operations.append(v.previewText);v.previewProof=localRecordsProof(operations,"local-records-preview-proof","本次合同、输入、权限与版本指纹");
 v.runAck=localRecordsInput("local-records-run-ack",{type:"checkbox"});v.confirm=localRecordsButton("单独确认并提交本次写入 Run","local-records-confirm",()=>localRecordsConfirm(v));operations.append(localRecordsLabel("我已核对具体记录、原修订、目标状态和正文；明确确认本次写入。",v.runAck),v.confirm);panel.append(operations);
 const result=localRecordsNode("section","local-records-result");result.hidden=!app;result.append(localRecordsNode("h3",null,"5. 手动读取同一 Run 和当前记录"));v.refresh=localRecordsButton("刷新当前实例、Run 与记录（只读）","local-records-refresh",()=>localRecordsRefresh(v));v.runSelect=localRecordsSelect("local-records-run-select",[["请明确选择已接受 Run",""]]);v.runRead=localRecordsButton("读取所选同一 Run（只读）","local-records-run-read",()=>localRecordsReadRun(v));v.runStatus=localRecordsNode("p","local-records-run-status");v.runStatus.setAttribute("role","status");result.append(v.refresh,localRecordsLabel("运行历史 ",v.runSelect),v.runRead,v.runStatus);v.runProof=localRecordsProof(result,"local-records-run-proof","原 Run、合同与真实工具回执");
 v.control=null;v.controlCommands={};const control=localRecordsNode("section","local-records-controls");control.append(localRecordsNode("p",null,"仅控制已明确读取的同一 Run。暂停或取消在安全边界生效，不撤销此前已保存的记录。"));
 for(const [command,label]of [["pause","暂停这次写入"],["resume","继续这次写入"],["cancel","取消这次写入"]]){const button=localRecordsButton(label,`local-records-${command}`,()=>localRecordsControl(v,command));v.controlCommands[command]=button;control.append(button);}
 v.controlStatus=localRecordsNode("p","local-records-control-status");v.controlStatus.setAttribute("role","status");control.append(v.controlStatus);result.append(control);v.records=localRecordsNode("div","local-records-current");
 v.exportCollection=localRecordsButton("下载当前集合 JSON 快照","local-records-export",()=>localRecordsExportCollection(v));v.exportStatus=localRecordsNode("p","local-records-export-status");v.exportStatus.setAttribute("role","status");
 result.append(localRecordsNode("h3",null,"当前记录集合"),localRecordsNode("p",null,"下载前重新核对当前权限与已保存集合；JSON 保留记录 ID、修订和事件来源，仅代表该集合版本的观察快照。"),v.exportCollection,v.exportStatus,v.records);v.history=localRecordsNode("div","local-records-history");result.append(localRecordsNode("h3",null,"所选记录的不可变历史"),v.history);panel.append(result);
 const recovery=localRecordsNode("section","local-records-recovery");recovery.append(localRecordsNode("h3",null,"原请求恢复"),localRecordsNode("p",null,"未知结果不重发写入。保留或输入原请求 key，选择原阶段后仅 GET 核对；冷页需先重新打开同一应用、版本或实例。"));v.recoveryStage=localRecordsSelect("local-records-recovery-stage",[["保存应用","CREATE_APP"],["准备内部版本","PREPARE_RELEASE"],["保存内部版本","COMMIT_RELEASE"],["创建实例","CREATE_INSTANCE"],["本次变更预览","PREVIEW"],["提交写入 Run","RUN"]]);v.recoveryKey=localRecordsInput("local-records-recovery-key",{maxLength:100});v.recover=localRecordsButton("仅 GET 读取原 key 回执","local-records-recover",()=>localRecordsRecover(v));recovery.append(localRecordsLabel("原阶段 ",v.recoveryStage),localRecordsLabel("原 key ",v.recoveryKey),v.recover);v.recoveryProof=localRecordsProof(recovery,"local-records-recovery-proof","原请求与恢复回执");panel.append(recovery);
 for(const input of [v.name,v.goal,v.createAck,v.releaseAck,v.instanceAck,v.runAck,v.recoveryKey])for(const event of ["input","change"])input.addEventListener(event,()=>{if(localRecordsCurrent(v))localRecordsButtons(v);});
 for(const input of [v.name,v.goal,v.recoveryKey,v.recoveryStage])for(const event of ["input","change"])input.addEventListener(event,()=>{if(localRecordsCurrent(v)){v.edit++;localRecordsButtons(v);}});
 for(const input of [v.command,v.title,v.details,v.recordSelect,v.state,v.reason])for(const event of ["input","change"])input.addEventListener(event,()=>{v.createFields.hidden=v.command.value!=="CREATE";v.stateFields.hidden=v.command.value!=="SET_STATE";localRecordsEdited(v);});
 v.releaseSelect.onchange=()=>{v.selection++;v.releaseAck.checked=v.instanceAck.checked=false;localRecordsButtons(v);};
 v.instanceSelect.onchange=safe(()=>localRecordsSelectInstance(v,v.instanceSelect.value));
 v.runSelect.onchange=()=>{v.read++;localRecordsClearControl(v);v.run=null;v.runStatus.textContent="已改变 Run 选择，请明确读取该 Run。";v.runProof.textContent="";localRecordsButtons(v);};
 return v;
}
const localRecordsHash=value=>ownerHash(value);
const localRecordsHashShape=value=>typeof value==="string"&&/^[a-f0-9]{64}$/.test(value);
const localRecordsInteger=value=>Number.isSafeInteger(value)&&value>=0;
const localRecordsApp=a=>a?.namespace===localRecordsVersion&&a.input_guidance?.mode==="LOCAL_RECORDS"&&a.formal_publication_enabled===false&&a.candidate?.actions?.length===1&&a.candidate.actions[0].executor?.kind==="registered_tool"&&a.candidate.actions[0].executor?.ref==="artifact.save_text"&&a.candidate.actions[0].executor?.version==="1";
function localRecordsError(){throw Error("本地记录回执的身份、精确输入或版本指纹不一致");}
function localRecordsOwn(v){return {identity:v.identity,project:v.project,principal:v.app?.principal_id||null,app:v.app?.id||null,instance:v.instance?.id||v.selectedIid||null,release:v.instance?.release_id||v.selectedRelease||null};}
function localRecordsEnvelope(reply,scope){if(reply?.namespace!==localRecordsVersion||reply.formal_publication_enabled!==false) localRecordsError();if(scope.project&&reply.project_id!==undefined&&reply.project_id!==scope.project)localRecordsError();if(scope.principal&&reply.principal_id!==undefined&&reply.principal_id!==scope.principal)localRecordsError();if(scope.app&&reply.app_id!==undefined&&reply.app_id!==scope.app)localRecordsError();if(scope.instance&&reply.instance_id!==undefined&&reply.instance_id!==scope.instance)localRecordsError();}
function localRecordsPending(v){return [...localRecordsIntents.values()].filter(i=>["SENDING","UNKNOWN"].includes(i.state)&&i.scope.identity===v.identity&&i.scope.project===v.project&&i.scope.app===(v.app?.id||null)&&(!i.scope.instance||i.scope.instance===(v.instance?.id||v.selectedIid||null)));}
function localRecordsButtons(v){
 if(!localRecordsCurrent(v))return;
 const pending=localRecordsPending(v),blocked=!!pending.length,busy=v.busy;
 v.create.disabled=busy||blocked||!v.createAck.checked||!v.name.value.trim()||!v.goal.value.trim()||!!v.savedApp;
 v.savedAppOpen.disabled=busy||!v.savedApp;
 v.prepareRelease.disabled=busy||blocked||!v.app||!v.ready||!!v.approval;
 v.commitRelease.disabled=busy||blocked||!v.approval||!!v.approval.release||!v.releaseAck.checked||v.approval.approval.expires_at*1000<=Date.now();
 v.createInstance.disabled=busy||blocked||!v.releaseSelect.value||!v.instanceAck.checked;
 v.previewButton.disabled=busy||blocked||!v.instance||(v.acceptedRun&&!localRecordsTerminal(v.acceptedRun.status))||(v.command.value==="CREATE"?!v.title.value.trim():!v.recordSelect.value||!v.reason.value.trim());
 v.confirm.disabled=busy||blocked||!v.preview||!v.previewCurrent?.()||!v.instance||v.preview.preview.data_version!==v.instance.data_version||v.preview.preview.instance_revision!==v.instance.revision||v.preview.preview.release_fingerprint!==v.instance.release_fingerprint||!!v.preview.run||!v.runAck.checked||v.preview.preview.expires_at*1000<=Date.now();
 v.deliveryRefresh.disabled=busy||!v.app;v.refresh.disabled=busy||!v.selectedIid;v.runRead.disabled=busy||!v.selectedIid||!v.runSelect.value;
 v.exportCollection.disabled=busy||!v.instance;
 v.recover.disabled=busy||!v.recoveryKey.value.trim();
 localRecordsControlButtons(v);
 for(const input of [v.name,v.goal,v.createAck,v.releaseAck,v.instanceAck,v.command,v.title,v.details,v.recordSelect,v.state,v.reason,v.runAck])input.disabled=busy||blocked;
}
function localRecordsRemember(v,intent){v.recoveryStage.value=intent.stage;v.recoveryKey.value=intent.key;v.recoveryProof.textContent=JSON.stringify({stage:intent.stage,request_key:intent.key,request_fingerprint:intent.requestFingerprint,state:intent.state},null,2);}
async function localRecordsValidateApp(v,app,intent,current){
 if(!localRecordsApp(app)||app.project_id!==v.project||typeof app.id!=="string"||typeof app.principal_id!=="string"||typeof app.runtime_id!=="string"||!app.definition||!localRecordsHashShape(app.fingerprint))localRecordsError();
 if(["id","name","principal_id","project_id","runtime_id"].some(key=>app[key]!==app.definition[key])||!localRecordsSame(app.candidate,app.definition.candidate))localRecordsError();
 if(intent?.originalInput?.name&&(app.name!==intent.originalInput.name||app.definition.purpose!==intent.originalInput.goal))localRecordsError();
 const hash=await localRecordsHash(app.definition);if(!current())return false;if(hash!==app.fingerprint)localRecordsError();
 if(intent&&app.request_fingerprint!==undefined&&app.request_fingerprint!==intent.originFingerprint)localRecordsError();
 return current();
}
async function localRecordsValidateApproval(v,reply,intent,current){
 localRecordsEnvelope(reply,intent.scope);const a=reply.approval,s=a?.payload?.snapshot;
 if(reply.app_id!==intent.scope.app||reply.request_key!==intent.key||reply.request_fingerprint!==intent.originFingerprint||!a||typeof a.id!=="string"||!localRecordsHashShape(a.fingerprint)||!Number.isFinite(a.expires_at)||s?.namespace!==localRecordsVersion||s.app_id!==intent.scope.app||s.principal_id!==intent.scope.principal||s.project_id!==intent.scope.project||s.definition_fingerprint!==v.app.fingerprint||!localRecordsSame(s.definition,v.app.definition))localRecordsError();
 const hash=await localRecordsHash(a.payload);if(!current())return false;if(hash!==a.fingerprint)localRecordsError();
 if(reply.release&&(typeof reply.release.id!=="string"||!localRecordsHashShape(reply.release.fingerprint)||reply.release.source_app_id!==intent.scope.app||reply.release.project_id!==intent.scope.project))localRecordsError();
 return current();
}
function localRecordsValidateInstanceReceipt(v,reply,intent){
 localRecordsEnvelope(reply,intent.scope);const i=reply.instance;
 if(reply.request_key!==intent.key||reply.request_fingerprint!==intent.originFingerprint||!i||typeof i.id!=="string"||i.source_app_id!==intent.scope.app||i.project_id!==intent.scope.project||i.release_id!==intent.anchor||!localRecordsInteger(i.revision)||i.revision<1||!localRecordsInteger(i.data_version))localRecordsError();return true;
}
async function localRecordsValidatePreview(v,reply,intent,current){
 localRecordsEnvelope(reply,intent.scope);const p=reply.preview,e=p?.event;
 if(reply.principal_id!==intent.scope.principal||reply.project_id!==intent.scope.project||reply.instance_id!==intent.scope.instance||reply.app_id!==intent.scope.app||reply.request_key!==intent.key||reply.request_fingerprint!==intent.originFingerprint||!p||!localRecordsHashShape(reply.preview_fingerprint)||!localRecordsHashShape(p.event_fingerprint)||!Number.isFinite(p.expires_at)||p.instance_revision!==intent.originalInput.expected_revision||p.data_version!==intent.originalInput.expected_data_version||p.release_fingerprint!==intent.originalInput.expected_release_fingerprint||p.release_id!==intent.scope.release||!localRecordsSame(p.input,intent.originalInput)||e?.namespace!=="local-record-event.v1"||e.app_id!==intent.scope.app||e.instance_id!==intent.scope.instance||e.principal_id!==intent.scope.principal||e.release_id!==intent.scope.release||e.kind!==intent.originalInput.command||e.collection_version!==p.data_version+1||typeof e.record_id!=="string"||!e.record_id||!localRecordsInteger(e.record_revision)||e.record_revision<1)localRecordsError();
 const ph=await localRecordsHash(p);if(!current())return false;if(ph!==reply.preview_fingerprint)localRecordsError();
 const eh=await localRecordsHash(e);if(!current())return false;if(eh!==p.event_fingerprint)localRecordsError();
 const body=intent.originalInput;
 if(body.command==="CREATE"&&(e.title!==body.title||e.details!==body.details||e.state!=="OPEN"||e.record_revision!==1||e.reason!==""||e.previous_event_fingerprint!==null))localRecordsError();
 if(body.command==="SET_STATE"){
  const old=intent.originalRecord;
  if(!old||e.record_id!==body.record_id||old.record_id!==body.record_id||old.record_revision!==body.expected_record_revision||e.record_revision!==body.expected_record_revision+1||old.state!=="OPEN"||e.state!=="DONE"||e.title!==old.title||e.details!==old.details||e.reason!==body.reason||e.previous_event_fingerprint!==old.last_event_fingerprint)localRecordsError();
 }
 if(reply.run&&(typeof reply.run.run_id!=="string"||typeof reply.run.app_run_id!=="string"||typeof reply.run.status!=="string"||!localRecordsInteger(reply.run.version)))localRecordsError();
 return current();
}
async function localRecordsPost(v,stage,url,body,recoveryUrl,check,{key=body.request_key,anchor="",originalInput=body,originalRecord=null,originFingerprint=null}={}){
 if(!localRecordsCurrent(v)||v.busy||localRecordsPending(v).length)return null;
 const intent={stage,key,anchor,scope:localRecordsOwn(v),body:structuredClone(body),originalInput:structuredClone(originalInput),originalRecord:originalRecord?structuredClone(originalRecord):null,recoveryUrl,check,state:"SENDING",originFingerprint};
 const storage=localRecordsScope(v,stage,anchor),current=localRecordsFence(v);
 localRecordsIntents.set(storage,intent);localRecordsRemember(v,intent);localRecordsBusy(v,true);let attempted=false;
 try{
  intent.requestFingerprint=await localRecordsHash(intent.body);if(!current()){intent.state="NOT_SENT";return null;}
  intent.originFingerprint=originFingerprint||intent.requestFingerprint;attempted=true;
  const reply=await api(url,"POST",intent.body);if(!current()){intent.state="UNKNOWN";return null;}
  if(!await check(v,reply,intent,current)||!current()){intent.state="UNKNOWN";return null;}
  if((stage==="COMMIT_RELEASE"&&!reply.release)||(stage==="RUN"&&!reply.run))localRecordsError();
  intent.state="ACCEPTED";intent.reply=reply;localRecordsRemember(v,intent);return {reply,intent};
 }catch(error){
  intent.state=attempted?"UNKNOWN":"NOT_SENT";
  const proof=error.submissionRejection;
  if(attempted&&error.httpStatus>=400&&error.httpStatus<500&&proof?.namespace==="local-record-submission-rejection.v1"&&proof.principal_id===intent.scope.principal&&proof.project_id===intent.scope.project&&proof.instance_id===intent.scope.instance&&proof.request_key===intent.key&&proof.request_fingerprint===intent.requestFingerprint&&proof.acceptance==="NOT_ACCEPTED"&&proof.previous_request==="ABSENT"&&proof.phase==="TX_ROLLED_BACK")intent.state="REJECTED";
  if(current()){localRecordsClearPrivate(v);localRecordsRemember(v,intent);localRecordsStatus(v,`${error.detail||error.message}；${intent.state==="REJECTED"?"服务端已确认本次未接受，请重新读取当前版本后明确预览。":"回执未确认，保留原 key，仅 GET 恢复，不重发写入。"}`);}
  return null;
 }finally{localRecordsBusy(v,false);}
}
async function localRecordsCreate(v){
 if(!localRecordsCurrent(v)||v.create.disabled)return;
 const body={name:v.name.value,goal:v.goal.value,request_key:crypto.randomUUID(),consent:"SAVE_LOCAL_RECORD_FORM"},current=localRecordsFence(v);
 const saved=await localRecordsPost(v,"CREATE_APP",`/api/projects/${v.project}/record-apps`,body,`/api/projects/${v.project}/record-app-requests/${encodeURIComponent(body.request_key)}`,localRecordsValidateApp);
 if(!current()||!saved)return;v.savedApp=saved.reply;localRecordsStatus(v,"固定本地记录应用已保存；请单独打开后准备内部版本，尚未写入记录。");localRecordsButtons(v);
}
async function localRecordsOpenSaved(v){if(!localRecordsCurrent(v)||!v.savedApp)return;const id=v.savedApp.id,project=v.project,identity=v.identity,connection=v.connection,workspace=v.workspace;await showApp(id,project,null,()=>identity===token&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration&&project===$("project-select").value,a=>{if(!localRecordsApp(a))localRecordsError();});}
async function localRecordsReadDelivery(v){
 if(!localRecordsCurrent(v)||!v.app||v.busy)return;
 v.read++;const current=localRecordsFence(v,{edit:false});localRecordsBusy(v,true);
 try{
  const reply=await api(`/api/apps/${v.app.id}/record-delivery`);if(!current())return;localRecordsEnvelope(reply,localRecordsOwn(v));
  if(reply.app_id!==v.app.id||reply.definition_fingerprint!==v.app.fingerprint||!Array.isArray(reply.releases)||!Array.isArray(reply.instances)||new Set(reply.releases.map(r=>r.id)).size!==reply.releases.length||new Set(reply.instances.map(i=>i.id)).size!==reply.instances.length)localRecordsError();
  for(const r of reply.releases)if(typeof r.id!=="string"||!localRecordsHashShape(r.fingerprint)||r.project_id!==v.project||r.source_app_id!==v.app.id)localRecordsError();
  for(const i of reply.instances)if(typeof i.id!=="string"||i.project_id!==v.project||i.source_app_id!==v.app.id||!reply.releases.some(r=>r.id===i.release_id)||!localRecordsInteger(i.revision)||i.revision<1||!localRecordsInteger(i.data_version))localRecordsError();
  v.delivery=reply;const release=v.releaseSelect.value,instance=v.instanceSelect.value;
  v.releaseSelect.replaceChildren(new Option("请明确选择已保存 Release",""),...reply.releases.map(r=>new Option(`${r.id} · ${r.fingerprint}`,r.id)));
  v.instanceSelect.replaceChildren(new Option("请明确选择实例",""),...reply.instances.map(i=>new Option(`${i.id} · 修订 ${i.revision} · 数据版本 ${i.data_version}`,i.id)));
  if(reply.releases.some(r=>r.id===release))v.releaseSelect.value=release;if(reply.instances.some(i=>i.id===instance))v.instanceSelect.value=instance;
  v.releaseAck.checked=v.instanceAck.checked=false;localRecordsStatus(v,"已读取本应用内部版本和实例；请选择或单独确认下一步。");
 }catch(error){if(current()){localRecordsClearPrivate(v);localRecordsStatus(v,`目录读取未通过：${error.detail||error.message}`);}}finally{localRecordsBusy(v,false);}
}
async function localRecordsPrepareRelease(v){
 if(!localRecordsCurrent(v)||v.prepareRelease.disabled)return;const current=localRecordsFence(v),body={expected_definition_fingerprint:v.app.fingerprint,request_key:crypto.randomUUID(),consent:"FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY"};
 const saved=await localRecordsPost(v,"PREPARE_RELEASE",`/api/apps/${v.app.id}/record-release-approvals`,body,`/api/apps/${v.app.id}/record-release-requests/${encodeURIComponent(body.request_key)}`,localRecordsValidateApproval);
 if(!current()||!saved)return;v.approval=saved.reply;v.approvalIntent=saved.intent;v.releaseProof.textContent=JSON.stringify(saved.reply,null,2);v.releaseAck.checked=false;localRecordsStatus(v,"精确内部版本已准备；请阅读快照，再单独勾选确认保存。");localRecordsButtons(v);
}
async function localRecordsCommitRelease(v){
 if(!localRecordsCurrent(v)||v.commitRelease.disabled)return;const a=v.approval,origin=v.approvalIntent,current=localRecordsFence(v),body={fingerprint:a.approval.fingerprint};
 const saved=await localRecordsPost(v,"COMMIT_RELEASE",`/api/apps/${v.app.id}/record-release-requests/${encodeURIComponent(a.request_key)}/commit`,body,origin.recoveryUrl,localRecordsValidateApproval,{key:a.request_key,originFingerprint:a.request_fingerprint,anchor:a.approval.id});
 if(!current()||!saved)return;if(!saved.reply.release)localRecordsError();v.approval=saved.reply;v.releaseAck.checked=false;v.releaseProof.textContent=JSON.stringify(saved.reply,null,2);localRecordsStatus(v,"内部 Release 已保存；请读取目录并明确选择 Release，再单独创建实例。");localRecordsButtons(v);
}
async function localRecordsCreateInstance(v){
 if(!localRecordsCurrent(v)||v.createInstance.disabled)return;const release=v.delivery?.releases.find(r=>r.id===v.releaseSelect.value);if(!release)return;
 const current=localRecordsFence(v),body={expected_release_fingerprint:release.fingerprint,request_key:crypto.randomUUID()};
 const saved=await localRecordsPost(v,"CREATE_INSTANCE",`/api/internal/record-releases/${release.id}/instances`,body,`/api/internal/record-releases/${release.id}/instance-requests/${encodeURIComponent(body.request_key)}`,localRecordsValidateInstanceReceipt,{anchor:release.id});
 if(!current()||!saved)return;v.instanceAck.checked=false;v.recoveryProof.textContent=JSON.stringify(saved.reply,null,2);localRecordsStatus(v,`独立实例 ${saved.reply.instance.id} 已保存；请读取目录，再明确选择该实例。尚未写入业务记录。`);localRecordsButtons(v);
}
const localRecordsTerminal=status=>["SUCCEEDED","PARTIAL","FAILED","CANCELLED"].includes(status);
async function localRecordsExportCollection(v){
 if(!localRecordsCurrent(v)||v.busy||!v.instance)return;
 const iid=v.selectedIid;v.read++;const current=localRecordsFence(v,{edit:false});localRecordsBusy(v,true);
 v.exportStatus.textContent="正在重新核对当前集合与读取权限；尚未下载。";
 try{
  const reply=await api(`/api/internal/record-instances/${iid}`);if(!current())return;
  if(!await localRecordsValidateProjection(v,reply,iid,current)||!current())return;
  const snapshot={namespace:"local-record-collection-snapshot.v1",snapshot_kind:"OBSERVED_COMMITTED_COLLECTION",principal_id:reply.principal_id,project_id:reply.project_id,app_id:reply.source_app_id,instance_id:reply.id,release_id:reply.release_id,release_fingerprint:reply.release_fingerprint,instance_revision:reply.revision,data_version:reply.data_version,
   records:[...reply.records].sort((a,b)=>a.record_id.localeCompare(b.record_id)).map(r=>({record_id:r.record_id,record_revision:r.record_revision,title:r.title,details:r.details,state:r.state,last_event_fingerprint:r.last_event_fingerprint})),
   history:reply.history.map(r=>({version:r.version,run_id:r.run_id,app_run_id:r.app_run_id,event_fingerprint:r.event_fingerprint,artifact:{resource_id:r.artifact.resource_id,hash:r.artifact.hash},event:r.event}))};
  if(!current())return;
  const url=URL.createObjectURL(new Blob([JSON.stringify(snapshot,null,2)+"\n"],{type:"application/json;charset=utf-8"}));
  try{if(!current())return;const link=document.createElement("a");link.href=url;link.download=`local-records-${iid}-v${reply.data_version}.json`;v.panel.append(link);try{link.click();}finally{link.remove();}}finally{URL.revokeObjectURL(url);}
  if(current())v.exportStatus.textContent=`已下载集合 v${reply.data_version} 的观察快照：${reply.records.length} 条记录、${reply.history.length} 条已保存事件。未提交写入不包含在文件内。`;
 }catch(error){if(current()){localRecordsClearPrivate(v);localRecordsStatus(v,"集合读取未通过，已清除当前正文；请重新核验实例。");v.exportStatus.textContent=`集合下载未通过：${error.detail||error.message}。没有生成下载文件；请重新读取实例。`;}}
 finally{localRecordsBusy(v,false);}
}
const localRecordsRunStates=["QUEUED","RUNNING","WAITING_INPUT","WAITING_APPROVAL","WAITING_RESOURCE","PAUSE_REQUESTED","PAUSED","CANCEL_REQUESTED","RECONCILING","SUCCEEDED","PARTIAL","FAILED","CANCELLED"];
function localRecordsControlKey(v,rid){return JSON.stringify([v.identity,v.project,v.app.id,v.app.principal_id,v.selectedIid,rid]);}
function localRecordsClearControl(v){v.control=null;if(v.controlStatus)v.controlStatus.textContent="";}
function localRecordsControlButtons(v){
 if(!v.controlCommands)return;
 const r=v.control,current=r&&v.instance&&r.id===v.runSelect.value,pending=current&&localRecordsControlIntents.get(localRecordsControlKey(v,r.id)),blocked=v.busy||!current||!!pending;
 v.controlCommands.pause.disabled=blocked||!["QUEUED","RUNNING"].includes(r?.status);
 v.controlCommands.resume.disabled=blocked||r?.status!=="PAUSED";
 v.controlCommands.cancel.disabled=blocked||localRecordsTerminal(r?.status)||r?.status==="CANCEL_REQUESTED";
}
function localRecordsReadControl(v,run){
 if(!localRecordsRunStates.includes(run.status)||!localRecordsInteger(run.version)||run.version<1)localRecordsError();
 const key=localRecordsControlKey(v,run.id),pending=localRecordsControlIntents.get(key);
 if(pending&&run.version<pending.version)localRecordsError();
 if(pending&&pending.state!=="SENDING"&&(run.version>pending.version||pending.state==="REJECTED"))localRecordsControlIntents.delete(key);
 v.control={id:run.id,status:run.status,version:run.version};
 v.controlStatus.textContent=localRecordsControlIntents.has(key)?`原控制结果尚未确认；同一 Run ${run.id} 当前读取为 ${run.status} / 版本 ${run.version}。控制保持锁定，仅可手动读取，不会重发。`:`已读取同一 Run ${run.id} · ${run.status} · 版本 ${run.version}。请明确选择控制操作。`;
}
async function localRecordsControl(v,command){
 if(!localRecordsCurrent(v)||v.controlCommands[command]?.disabled||!v.control||v.busy)return;
 const r={...v.control},iid=v.selectedIid,key=localRecordsControlKey(v,r.id);if(localRecordsControlIntents.has(key))return;
 const currentScope=localRecordsFence(v,{edit:false}),current=()=>currentScope()&&v.selectedIid===iid&&v.runSelect.value===r.id;
 const intent={state:"SENDING",version:r.version,command};localRecordsControlIntents.set(key,intent);localRecordsBusy(v,true);
 v.run=null;v.runProof.textContent="";v.control=null;v.controlStatus.textContent=`正在请求 ${command}：同一 Run ${r.id}，版本 ${r.version}；结果尚未确认。`;
 try{
  const reply=await api(`/api/internal/record-instances/${iid}/runs/${r.id}/commands`,"POST",{command,version:r.version});
  const expected=command==="pause"?(r.status==="RUNNING"?"PAUSE_REQUESTED":"PAUSED"):command==="resume"?"QUEUED":["RUNNING","PAUSE_REQUESTED"].includes(r.status)?"CANCEL_REQUESTED":"CANCELLED";
  if(Object.keys(reply||{}).sort().join()!==["namespace","id","status","version","content_access","formal_publication_enabled"].sort().join()||reply.namespace!==localRecordsVersion||reply.id!==r.id||reply.version!==r.version+1||reply.status!==expected||reply.content_access!==false||reply.formal_publication_enabled!==false)localRecordsError();
  if(localRecordsControlIntents.get(key)!==intent)return;
  localRecordsControlIntents.delete(key);if(!current())return;
  v.control={id:r.id,status:reply.status,version:reply.version};
  if(v.acceptedRun?.run_id===r.id)v.acceptedRun={...v.acceptedRun,status:reply.status,version:reply.version};
  v.runStatus.textContent=`控制回执：同一 Run ${r.id} · ${reply.status} · 版本 ${reply.version}。结果正文须另行手动读取。`;
  v.controlStatus.textContent=reply.status.endsWith("_REQUESTED")?"停止意图已记录，仍须读取后台最终状态；不会撤销此前已保存的记录。":"控制回执已确认；未重发业务写入，也未撤销此前已保存的记录。";
 }catch(error){
  if(localRecordsControlIntents.get(key)!==intent)return;
  intent.state=Number.isInteger(error.httpStatus)&&[400,401,403,404,409,422].includes(error.httpStatus)?"REJECTED":"UNKNOWN";
  if(current()){v.runStatus.textContent="控制请求没有获知可核验的成功回执，不能判断最新状态。";v.controlStatus.textContent=`${intent.state==="REJECTED"?"控制被拒绝":"控制结果未确认"}：${error.detail||error.message}。请仅点击“读取所选同一 Run”核对；不会自动重发控制或写入。`;}
 }finally{localRecordsBusy(v,false);}
}
function localRecordsClearInstance(v){localRecordsClearControl(v);if(v.exportStatus)v.exportStatus.textContent="";v.instance=null;v.run=null;v.preview=null;v.previewCurrent=null;v.acceptedRun=null;v.historyRecord=null;v.operations.hidden=true;v.records.replaceChildren();v.history.replaceChildren();v.runProof.textContent="";v.runStatus.textContent="";v.runSelect.replaceChildren(new Option("请明确选择已接受 Run",""));v.previewText.replaceChildren();v.previewProof.textContent="";v.runAck.checked=false;v.recoveryProof.textContent="";v.recoveryKey.value="";}
function localRecordsClearPrivate(v){
 const key=v.recoveryKey.value;v.read++;v.edit++;localRecordsClearInstance(v);v.recoveryKey.value=key;
 v.title.value=v.details.value=v.reason.value="";v.recordSelect.replaceChildren(new Option("请重新核验当前记录",""));
}
async function localRecordsValidateProjection(v,reply,iid,current){
 localRecordsEnvelope(reply,{...localRecordsOwn(v),instance:iid});
 if(reply.id!==iid||reply.principal_id!==v.app.principal_id||reply.project_id!==v.project||reply.source_app_id!==v.app.id||reply.runtime_id!==v.app.runtime_id||!localRecordsHashShape(reply.release_fingerprint)||!localRecordsInteger(reply.revision)||reply.revision<1||!localRecordsInteger(reply.data_version)||!Array.isArray(reply.records)||reply.records.length>32||!Array.isArray(reply.history)||reply.history.length!==reply.data_version||reply.history.length>64||!Array.isArray(reply.runs))localRecordsError();
 const release=v.delivery?.releases.find(r=>r.id===reply.release_id);if(!release||release.fingerprint!==reply.release_fingerprint)localRecordsError();
 const keys=["namespace","app_id","instance_id","release_id","principal_id","kind","collection_version","record_id","record_revision","previous_event_fingerprint","previous_collection_fingerprint","title","details","state","reason"].sort().join(),fold=new Map(),runIds=new Set(),appRunIds=new Set();
 for(const [index,row]of reply.history.entries()){
  const e=row.event,old=fold.get(e?.record_id);
  if(row.version!==index+1||!localRecordsHashShape(row.event_fingerprint)||typeof row.run_id!=="string"||typeof row.app_run_id!=="string"||runIds.has(row.run_id)||appRunIds.has(row.app_run_id)||typeof row.artifact?.resource_id!=="string"||!localRecordsHashShape(row.artifact.hash)||!e||Object.keys(e).sort().join()!==keys||e.namespace!=="local-record-event.v1"||e.app_id!==v.app.id||e.instance_id!==iid||e.release_id!==reply.release_id||e.principal_id!==v.app.principal_id||e.collection_version!==row.version||typeof e.record_id!=="string"||!e.record_id||!localRecordsInteger(e.record_revision)||e.record_revision<1||typeof e.title!=="string"||!e.title.trim()||Array.from(e.title).length>200||typeof e.details!=="string"||Array.from(e.details).length>2000||typeof e.reason!=="string"||(index===0?e.previous_collection_fingerprint!==null:!localRecordsHashShape(e.previous_collection_fingerprint)))localRecordsError();
  const hash=await localRecordsHash(e);if(!current())return false;if(hash!==row.event_fingerprint||row.artifact.hash!==row.event_fingerprint||e.previous_collection_fingerprint!==(index?reply.history[index-1].event_fingerprint:null))localRecordsError();
  if(e.kind==="CREATE"){
   if(old||e.record_revision!==1||e.state!=="OPEN"||e.previous_event_fingerprint!==null||e.reason!=="")localRecordsError();
  }else if(e.kind==="SET_STATE"){
   if(!old||old.state!=="OPEN"||e.state!=="DONE"||e.record_revision!==old.record_revision+1||e.previous_event_fingerprint!==old.last_event_fingerprint||e.title!==old.title||e.details!==old.details||!e.reason.trim()||Array.from(e.reason).length>500)localRecordsError();
  }else localRecordsError();
  fold.set(e.record_id,{record_id:e.record_id,record_revision:e.record_revision,title:e.title,details:e.details,state:e.state,last_event_fingerprint:row.event_fingerprint});runIds.add(row.run_id);appRunIds.add(row.app_run_id);
 }
 const sort=items=>[...items].sort((a,b)=>a.record_id.localeCompare(b.record_id));
 if(!localRecordsSame(sort(reply.records),sort(fold.values())))localRecordsError();
 if(new Set(reply.runs.map(r=>r.id)).size!==reply.runs.length||new Set(reply.runs.map(r=>r.app_run_id)).size!==reply.runs.length||reply.runs.some(r=>typeof r.id!=="string"||typeof r.app_run_id!=="string"||typeof r.status!=="string"||!localRecordsInteger(r.version)||(r.result_version!==null&&(!localRecordsInteger(r.result_version)||r.result_version<1))))localRecordsError();
 return current();
}
function localRecordsRenderHistory(v,recordId){
 v.history.replaceChildren();if(!recordId)return;
 for(const row of v.instance.history.filter(h=>h.event.record_id===recordId)){
  const e=row.event,card=localRecordsNode("article");card.append(localRecordsNode("h4",null,`${e.kind} · 记录修订 ${e.record_revision} · 集合版本 ${row.version}`),localRecordsNode("p",null,`记录 ${e.record_id} · ${e.state} · Run ${row.run_id}`),localRecordsNode("p",null,`标题：${e.title}`),localRecordsNode("pre",null,e.details),localRecordsNode("p",null,`变更依据：${e.reason||"创建记录，无状态变更依据"}`),localRecordsNode("p",null,`事件 SHA-256 ${row.event_fingerprint} · JSON 制品 ${row.artifact.resource_id} · ${row.artifact.hash}`));v.history.append(card);
 }
}
function localRecordsRenderProjection(v){
 const i=v.instance;v.operations.hidden=false;v.instanceInfo.textContent=`实例 ${i.id} · Release ${i.release_id} · 修订 ${i.revision} · 当前集合版本 ${i.data_version}`;
 const chosen=v.recordSelect.value;v.recordSelect.replaceChildren(new Option("请选择当前 OPEN 记录",""),...i.records.filter(r=>r.state==="OPEN").map(r=>new Option(`${r.title} · ${r.record_id} · 修订 ${r.record_revision}`,r.record_id)));if(i.records.some(r=>r.record_id===chosen&&r.state==="OPEN"))v.recordSelect.value=chosen;
 v.records.replaceChildren(localRecordsNode("p",null,`已核验集合版本 ${i.data_version} · ${i.records.length} 条记录`));
 if(!i.records.length)v.records.append(localRecordsNode("p",null,"当前集合为空；请明确预览并确认创建第一条记录。"));
 for(const record of i.records){
  const card=localRecordsNode("article"),history=localRecordsButton("重新核对并查看此记录历史",null,async()=>{if(!localRecordsCurrent(v)||v.busy)return;v.historyRecord=record.record_id;await localRecordsRefresh(v);});card.dataset.recordId=record.record_id;card.append(localRecordsNode("h4",null,record.title),localRecordsNode("p",null,`${record.record_id} · 修订 ${record.record_revision} · 状态 ${record.state}`),localRecordsNode("pre",null,record.details),history);v.records.append(card);
 }
 localRecordsRenderHistory(v,v.historyRecord);
 if(v.acceptedRun){const known=i.runs.find(r=>r.id===v.acceptedRun.run_id);if(known)v.acceptedRun={...v.acceptedRun,status:known.status,version:known.version};}
 const selected=v.runSelect.value;v.runSelect.replaceChildren(new Option("请明确选择已接受 Run",""),...i.runs.map(r=>new Option(`${r.id} · ${r.status} · 结果 ${r.result_version??"尚无"}`,r.id)));if(i.runs.some(r=>r.id===selected))v.runSelect.value=selected;
}
async function localRecordsSelectInstance(v,iid){
 if(!localRecordsCurrent(v))return;v.selection++;v.read++;v.edit++;localRecordsClearInstance(v);v.selectedIid=iid||null;v.title.value=v.details.value=v.reason.value="";v.command.value="CREATE";v.createFields.hidden=false;v.stateFields.hidden=true;v.selectedRelease=v.delivery?.instances.find(i=>i.id===iid)?.release_id||null;localRecordsButtons(v);
 if(!iid)return;if(!v.selectedRelease)localRecordsError();const pending=localRecordsPending(v)[0];if(pending)localRecordsRemember(v,pending);await localRecordsRefresh(v,true);
}
async function localRecordsRunValue(v,run,rid,current){
 localRecordsEnvelope(run,localRecordsOwn(v));
 if(run.id!==rid||run.instance_id!==v.selectedIid||run.release_id!==v.instance.release_id||typeof run.app_run_id!=="string"||typeof run.status!=="string"||!localRecordsInteger(run.version))localRecordsError();
 const known=v.instance.runs.find(r=>r.id===rid);if(!known||known.app_run_id!==run.app_run_id)localRecordsError();
 if(run.status==="SUCCEEDED"){
  const event=v.instance.history.find(h=>h.run_id===rid);
  if(!event||event.app_run_id!==run.app_run_id||event.version!==run.result_version||!localRecordsSame(event.event,run.event)||!localRecordsSame(event.artifact,run.output)||run.receipt?.status!=="VERIFIED"||!localRecordsSame(run.receipt.data,run.output)||!localRecordsSame(run.receipt.artifact_refs,[run.output.resource_id])||!localRecordsSame(run.receipt.check_results,[{check:"receipt.readback.v1",status:"PASS"}])||run.receipt.error!==null)localRecordsError();
  const hash=await localRecordsHash(run.event);if(!current())return false;if(hash!==event.event_fingerprint)localRecordsError();
 }else if(run.output!==null||run.event!==null||run.result_version!==null)localRecordsError();
 return current();
}
function localRecordsRenderRun(v,run){v.run=run;v.runStatus.textContent=`同一 Run ${run.id} · ${run.status} · ${run.result_version!==null?"已保存集合版本 "+run.result_version:"尚无已核验业务事件"}${run.error?" · "+(run.error.code||"运行错误"):""}`;if(run.status==="SUCCEEDED")v.runStatus.textContent+=` · 记录 ${run.event.record_id} 修订 ${run.event.record_revision} → ${run.event.state} · 实际工具输出 JSON 制品 ${run.output.resource_id}，SHA-256 ${run.output.hash}`;v.runProof.textContent=JSON.stringify(run,null,2);localRecordsReadControl(v,run);if(v.acceptedRun?.run_id===run.id)v.acceptedRun={...v.acceptedRun,status:run.status,version:run.version};}
async function localRecordsRefresh(v,allowBusy=false){
 if(!localRecordsCurrent(v)||!v.selectedIid||(v.busy&&!allowBusy))return;v.read++;const current=localRecordsFence(v,{edit:false}),iid=v.selectedIid,selected=v.runSelect.value;localRecordsBusy(v,true);v.runStatus.textContent="正在重新鉴权并读取同一实例；读取失败不表示后台任务失败。";
 try{
  const reply=await api(`/api/internal/record-instances/${iid}`);if(!current())return;if(!await localRecordsValidateProjection(v,reply,iid,current)||!current())return;
  v.instance=reply;v.preview=null;v.previewCurrent=null;v.runAck.checked=false;v.previewText.replaceChildren();v.previewProof.textContent="";localRecordsRenderProjection(v);
  if(selected){if(!reply.runs.some(r=>r.id===selected))localRecordsError();v.runSelect.value=selected;const run=await api(`/api/internal/record-instances/${iid}/runs/${selected}`);if(!current())return;if(!await localRecordsRunValue(v,run,selected,current)||!current())return;localRecordsRenderRun(v,run);}
  else{localRecordsClearControl(v);v.run=null;v.runProof.textContent="";v.runStatus.textContent="当前集合已重新核验；请明确选择需要读取的同一 Run。";}
  localRecordsStatus(v,`已核验当前实例与集合版本 ${reply.data_version}；没有提交新的写入。`);
 }catch(error){if(current()){localRecordsClearPrivate(v);v.runStatus.textContent=`读取未确认：${error.detail||error.message}。已清除当前正文；原请求 key 保留，不代表任务失败。`;}}
 finally{localRecordsBusy(v,false);}
}
async function localRecordsReadRun(v){if(!localRecordsCurrent(v)||!v.selectedIid||!v.runSelect.value||v.busy)return;await localRecordsRefresh(v);}
async function localRecordsPreview(v){
 if(!localRecordsCurrent(v)||v.previewButton.disabled)return;
 const i=v.instance,base={command:v.command.value,expected_revision:i.revision,expected_data_version:i.data_version,expected_release_fingerprint:i.release_fingerprint,request_key:crypto.randomUUID()},old=i.records.find(r=>r.record_id===v.recordSelect.value);
 const body=base.command==="CREATE"?{...base,title:v.title.value,details:v.details.value}:{...base,record_id:v.recordSelect.value,expected_record_revision:old?.record_revision,target_state:"DONE",reason:v.reason.value};
 const current=localRecordsFence(v),saved=await localRecordsPost(v,"PREVIEW",`/api/internal/record-instances/${i.id}/previews`,body,`/api/internal/record-instances/${i.id}/record-requests/${encodeURIComponent(body.request_key)}`,localRecordsValidatePreview,{originalRecord:old||null});
 if(!current()||!saved)return;localRecordsAcceptPreview(v,saved.reply,saved.intent);
}
function localRecordsAcceptPreview(v,reply,intent){
 v.preview=reply;v.previewIntent=intent;v.previewCurrent=localRecordsFence(v);v.runAck.checked=false;v.previewProof.textContent=JSON.stringify(reply,null,2);const e=reply.preview.event;v.previewText.replaceChildren(localRecordsNode("h4",null,`本次 ${e.kind} · ${e.record_id} · 修订 ${e.record_revision} · ${e.state}`),localRecordsNode("p",null,`标题：${e.title}`),localRecordsNode("pre",null,e.details),localRecordsNode("p",null,`变更依据：${e.reason||"创建初始 OPEN 记录"} · 集合版本 ${reply.preview.data_version} → ${e.collection_version}`));localRecordsStatus(v,"精确变更已预览；尚未执行写入，请单独勾选确认本次 Run。");localRecordsButtons(v);
}
async function localRecordsConfirm(v){
 if(!localRecordsCurrent(v)||v.confirm.disabled)return;const p=v.preview,intent=v.previewIntent,current=localRecordsFence(v),body={expected_preview_fingerprint:p.preview_fingerprint,consent:"WRITE_THIS_EXACT_LOCAL_RECORD_EVENT"};
 const saved=await localRecordsPost(v,"RUN",`/api/internal/record-instances/${v.instance.id}/previews/${encodeURIComponent(p.request_key)}/commit`,body,intent.recoveryUrl,localRecordsValidatePreview,{key:p.request_key,originFingerprint:p.request_fingerprint,originalInput:intent.originalInput,originalRecord:intent.originalRecord});
 if(!current()||!saved)return;if(!saved.reply.run)localRecordsError();v.preview=saved.reply;v.runAck.checked=false;v.acceptedRun=saved.reply.run;v.run=null;v.runProof.textContent="";const run=saved.reply.run;
 if(![...v.runSelect.options].some(o=>o.value===run.run_id))v.runSelect.append(new Option(`${run.run_id} · ${run.status} · 只读刷新核对结果`,run.run_id));v.runSelect.value=run.run_id;v.runStatus.textContent=`已接受同一 Run ${run.run_id} · ${run.status}；尚未读取实际结果。请手动刷新，不会自动轮询或再次提交。`;localRecordsStatus(v,"本次写入 Run 已接受；后台状态与最终记录须手动读取。新点击不会重发已接受请求。");localRecordsButtons(v);
}
function localRecordsOriginalRecord(v,input){
 if(input.command!=="SET_STATE")return null;const rows=v.instance?.history.filter(h=>h.version<=input.expected_data_version&&h.event.record_id===input.record_id)||[];const last=rows.at(-1);if(!last)return null;const e=last.event;return {record_id:e.record_id,record_revision:e.record_revision,title:e.title,details:e.details,state:e.state,last_event_fingerprint:last.event_fingerprint};
}
function localRecordsAcceptedRun(v,reply){
 const run=reply.run;if(!run)localRecordsError();v.preview=reply;v.runAck.checked=false;v.acceptedRun=run;v.run=null;v.runProof.textContent="";
 if(![...v.runSelect.options].some(o=>o.value===run.run_id))v.runSelect.append(new Option(`${run.run_id} · ${run.status} · 只读刷新核对结果`,run.run_id));v.runSelect.value=run.run_id;v.runStatus.textContent=`已接受同一 Run ${run.run_id} · ${run.status}；尚未读取实际结果。请手动刷新，不会自动轮询或再次提交。`;localRecordsStatus(v,"本次写入 Run 已接受；后台状态与最终记录须手动读取。新点击不会重发已接受请求。");localRecordsButtons(v);
}
async function localRecordsRecover(v){
 if(!localRecordsCurrent(v)||v.busy)return;const stage=v.recoveryStage.value,key=v.recoveryKey.value.trim();if(!key)return;
 const existing=[...localRecordsIntents.values()].find(i=>i.key===key&&i.stage===stage&&i.scope.identity===v.identity&&i.scope.project===v.project&&i.scope.app===(v.app?.id||null)&&(!i.scope.instance||i.scope.instance===v.selectedIid));
 let path=existing?.recoveryUrl,scope=localRecordsOwn(v),anchor="",body=null;
 if(!path){
  if(stage==="CREATE_APP")path=`/api/projects/${v.project}/record-app-requests/${encodeURIComponent(key)}`;
  else if(["PREPARE_RELEASE","COMMIT_RELEASE"].includes(stage)&&v.app){path=`/api/apps/${v.app.id}/record-release-requests/${encodeURIComponent(key)}`;body={expected_definition_fingerprint:v.app.fingerprint,request_key:key,consent:"FREEZE_RECORD_FORM_AND_WRITE_BOUNDARY"};}
  else if(stage==="CREATE_INSTANCE"&&v.app){const release=v.delivery?.releases.find(r=>r.id===v.releaseSelect.value);if(!release)throw Error("请先明确选择原请求所属 Release");anchor=release.id;path=`/api/internal/record-releases/${release.id}/instance-requests/${encodeURIComponent(key)}`;body={expected_release_fingerprint:release.fingerprint,request_key:key};}
  else if(["PREVIEW","RUN"].includes(stage)&&v.selectedIid)path=`/api/internal/record-instances/${v.selectedIid}/record-requests/${encodeURIComponent(key)}`;
  else throw Error("请先重新打开原应用并明确选择原 Release 或实例");
 }
 const current=localRecordsFence(v);localRecordsBusy(v,true);
 try{
  const reply=await api(path);if(!current())return;let intent=existing;
  if(!intent){
   if(stage==="CREATE_APP"){
    if(!await localRecordsValidateApp(v,reply,null,current)||!current())return;if(!localRecordsHashShape(reply.request_fingerprint))localRecordsError();
    const originalInput={name:reply.name,goal:reply.definition.purpose,request_key:key,consent:"SAVE_LOCAL_RECORD_FORM"};const originFingerprint=await localRecordsHash(originalInput);if(!current())return;if(originFingerprint!==reply.request_fingerprint)localRecordsError();
    intent={stage,key,scope,anchor,originalInput,originFingerprint,recoveryUrl:path,state:"ACCEPTED",reply};
   }else{
    if(["PREVIEW","RUN"].includes(stage)){if(!v.instance||reply.preview?.input?.request_key!==key)localRecordsError();body=reply.preview.input;}
    const originFingerprint=await localRecordsHash(body);if(!current())return;
    intent={stage,key,scope,anchor,originalInput:body,originalRecord:localRecordsOriginalRecord(v,body),originFingerprint,recoveryUrl:path,state:"UNKNOWN"};
   }
  }
  let valid=true;
  if(stage==="CREATE_APP")valid=await localRecordsValidateApp(v,reply,intent,current);
  else if(["PREPARE_RELEASE","COMMIT_RELEASE"].includes(stage))valid=await localRecordsValidateApproval(v,reply,intent,current);
  else if(stage==="CREATE_INSTANCE")valid=localRecordsValidateInstanceReceipt(v,reply,intent);
  else valid=await localRecordsValidatePreview(v,reply,intent,current);
  if(!valid||!current())return;
  if((stage==="COMMIT_RELEASE"&&!reply.release)||(stage==="RUN"&&!reply.run)){intent.state="UNKNOWN";localRecordsIntents.set(localRecordsScope(v,stage,intent.anchor),intent);localRecordsRemember(v,intent);localRecordsStatus(v,"原提交尚无接受回执，继续仅 GET 原 key；不会自动重发或换 key。");return;}
  intent.reply=reply;intent.state="ACCEPTED";localRecordsIntents.set(localRecordsScope(v,stage,intent.anchor),intent);localRecordsRemember(v,intent);v.recoveryProof.textContent=JSON.stringify(reply,null,2);
  if(stage==="CREATE_APP"){v.savedApp=reply;localRecordsStatus(v,"已只读恢复原 key 对应应用；请另行打开，不会自动准备版本或运行。");}
  else if(["PREPARE_RELEASE","COMMIT_RELEASE"].includes(stage)){v.approval=reply;v.approvalIntent=intent;v.releaseAck.checked=false;v.releaseProof.textContent=JSON.stringify(reply,null,2);localRecordsStatus(v,reply.release?"原内部版本已保存；请读取目录，明确选择后单独创建实例。":"已恢复原版本预览，请阅读并另行确认保存。");}
  else if(stage==="CREATE_INSTANCE"){v.instanceAck.checked=false;localRecordsStatus(v,`已只读恢复实例 ${reply.instance.id}；请读取目录，再明确选择实例。`);}
  else{
   const input=reply.preview.input;v.command.value=input.command;v.title.value=input.title||"";v.details.value=input.details||"";if(input.command==="SET_STATE")v.recordSelect.value=input.record_id;v.reason.value=input.reason||"";v.createFields.hidden=input.command!=="CREATE";v.stateFields.hidden=input.command!=="SET_STATE";
   localRecordsAcceptPreview(v,reply,intent);if(reply.run)localRecordsAcceptedRun(v,reply);
  }
 }catch(error){if(current()){localRecordsClearPrivate(v);localRecordsStatus(v,`原 key 读取未确认：${error.detail||error.message}。不会重发写入；已有原请求仍保留。`);}}
 finally{localRecordsBusy(v,false);}
}
function renderLocalRecordTaskResult(receipt,current){
 if(!current())return;
 if(receipt.project_id!==$("project-select").value||receipt.id!==activeRun||receipt.formal_publication_enabled!==false||![receipt.id,receipt.instance_id,receipt.app_id,receipt.app_run_id,receipt.release_id,receipt.principal_id].every(id=>typeof id==="string"&&id))localRecordsError();
 const result=$("result");result.replaceChildren(row(`本地记录任务 ${receipt.id} · ${receipt.status} · 集合结果版本 ${receipt.result_version??"尚无"}`));
 if(receipt.status==="SUCCEEDED"){
  const e=receipt.event;
  if(!e||e.app_id!==receipt.app_id||e.instance_id!==receipt.instance_id||e.principal_id!==receipt.principal_id||e.release_id!==receipt.release_id||e.collection_version!==receipt.result_version||receipt.receipt?.status!=="VERIFIED")localRecordsError();
  result.append(row(`本次记录「${e.title}」 · ${e.state} · 记录修订 ${e.record_revision}；已保存本次事件，目标语义未验收。`));
 }else result.append(row("本次尚无已保存业务事件；历史成功不代表本次完成。"));
 const button=document.createElement("button");button.id="local-record-task-open-result";button.type="button";button.textContent="在本地记录应用中打开此Run与事件历史";
 button.disabled=!!internalTaskNavigation?.current();button.onclick=safe(()=>openLocalRecordTaskResult(receipt,button,current));result.append(button);
}
async function openLocalRecordTaskResult(receipt,button,selectedCurrent){
 if(!selectedCurrent()||internalTaskNavigation?.current())return;
 const identity=token,connection=identityConnectionGeneration,project=$("project-select").value,userSelection=runUserSelectionGeneration;
 let workspace=workspaceSelectionGeneration,generation=appSelectionGeneration,view=null,selection=null,reading=null;
 // Same-Run background reads may replace the Projects summary. Human selection,
 // connection, workspace and exact typed-view selections own this navigation.
 const scopeCurrent=()=>identity===token&&connection===identityConnectionGeneration&&project===$("project-select").value&&activeRun===receipt.id&&userSelection===runUserSelectionGeneration&&workspace===workspaceSelectionGeneration&&generation===appSelectionGeneration&&(!view||localRecordsView===view);
 const current=()=>scopeCurrent()&&(selection===null||view.selection===selection)&&(reading===null||view.read===reading);
 const navigation={current};internalTaskNavigation=navigation;button.disabled=true;
 try{
  selectWorkspace("apps");workspace=workspaceSelectionGeneration;
  const loaded=await showApp(receipt.app_id,project,value=>{generation=value;},scopeCurrent,app=>{
   if(!localRecordsApp(app)||app.principal_id!==receipt.principal_id||app.project_id!==project)localRecordsError();
  });
  if(!loaded||!current())return;view=localRecordsView;
  if(!view||!localRecordsCurrent(view)||view.app.id!==receipt.app_id)localRecordsError();
  const selecting=localRecordsSelectInstance(view,receipt.instance_id);selection=view.selection;await selecting;
  if(!current())return;
  if(view.instance?.id!==receipt.instance_id||view.instance.release_id!==receipt.release_id||!view.instance.runs.some(run=>run.id===receipt.id&&run.app_run_id===receipt.app_run_id))localRecordsError();
  view.runSelect.value=receipt.id;
  const loading=localRecordsReadRun(view);reading=view.read;await loading;
  if(!current())return;
  if(view.runSelect.value!==receipt.id||view.run?.id!==receipt.id||view.run.app_run_id!==receipt.app_run_id||view.run.release_id!==receipt.release_id)localRecordsError();
  view.runStatus.scrollIntoView?.({block:"nearest"});
 }catch(error){if(current())throw error;}
 finally{
  if(view?.selectionCurrent===scopeCurrent){if(scopeCurrent())view.selectionCurrent=null;else if(localRecordsView===view)clearLocalRecordsView();}
  // showApp can fail while constructing the typed view, before assignment.
  else if(!view&&localRecordsView?.selectionCurrent===scopeCurrent){if(scopeCurrent())localRecordsView.selectionCurrent=null;else clearLocalRecordsView();}
  if(internalTaskNavigation===navigation)internalTaskNavigation=null;
  if(selectedCurrent())button.disabled=false;
 }
}
async function openLocalRecordsApp(app,generation,selectionCurrent=()=>true){
 if(!localRecordsApp(app))localRecordsError();const v=localRecordsBuild(app,generation,selectionCurrent),current=localRecordsFence(v);localRecordsButtons(v);
 if(!await localRecordsValidateApp(v,app,null,current)||!current())return false;v.ready=true;
 $("app-title").textContent=app.name+" · 本地记录与状态 · 内部未发布";$("app-origin").textContent="固定类型表单应用；当前项目已有写入权限仍由每次预览、后台提交与成果读取独立核查。";$("app-preview-form").hidden=true;$("csv-extraction-panel").hidden=true;
 const pending=localRecordsPending(v)[0];if(pending)localRecordsRemember(v,pending);await localRecordsReadDelivery(v);return localRecordsCurrent(v);
}
$("local-records-new").onclick=safe(()=>{
 if(!token||!$("project-select").value)throw Error("请先连接并选择项目");selectWorkspace("apps");clearApp();const v=localRecordsBuild(null,appSelectionGeneration);const pending=localRecordsPending(v)[0];if(pending)localRecordsRemember(v,pending);localRecordsButtons(v);localRecordsStatus(v,"填写用途与约束，明确保存固定表单应用；此步骤不创建版本、实例或业务记录。");
});
