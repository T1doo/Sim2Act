"use strict";
// Existing authorized CSV instances only; no publication, grants, or model adapter.
let applicationUse=null,applicationUseGeneration=0,applicationUseListGeneration=0,applicationUseContextGeneration=0;
const applicationUseRequests=new Map();
const csvUseApp=a=>a?.candidate?.manifest?.validation_suite_ref==="receipt.readback.v1" && a.candidate.actions?.length===1 && a.candidate.actions[0].executor?.kind==="registered_tool" && a.candidate.actions[0].executor.ref==="data.aggregate_csv";
const applicationUseCurrent=v=>!!v && applicationUse===v && v.identity===token && v.project===$("project-select").value && v.generation===applicationUseGeneration;
const applicationUseKey=v=>JSON.stringify([v.identity,v.project,v.id]);
function clearApplicationUse(clearList=false){
 applicationUseGeneration++;applicationUse=null;
 if(clearList)clearConditionalChecks(true);
 for(const id of ["use-info","use-output","use-history","use-provenance","use-column","use-acceptance"])$(id).replaceChildren();
 $("use-form").hidden=true;$("use-refresh").hidden=true;$("use-recover").hidden=true;
 if(clearList){applicationUseListGeneration++;applicationUseContextGeneration++;$("use-list").replaceChildren();}
}
async function refreshApplicationUse(apps){
 const identity=token,project=$("project-select").value,generation=++applicationUseListGeneration,context=applicationUseContextGeneration;
 const current=()=>identity===token&&project===$("project-select").value&&generation===applicationUseListGeneration;
 const rows=[];
 for(const summary of apps){
  let app,reply;
  try{app=await api(`/api/apps/${summary.id}`);if(!current())return;if(!csvUseApp(app))continue;reply=await api(`/api/internal/apps/${app.id}/instances`);}
  catch(error){if(!current())return;rows.push(row(`${summary.name} · 当前版本不可读取；请核对授权与来源。`));if(applicationUse?.appId===summary.id&&applicationUseCurrent(applicationUse))clearApplicationUseData(applicationUse);continue;}
  if(!current())return;
  for(const instance of reply.items){
   if(instance.project_id!==project||instance.source_app_id!==app.id)throw Error("VERSION_CONFLICT");
   rows.push(row(`${app.name} · 未发布内部版本 · 结果版本 ${instance.data_version} · ${instance.id.slice(0,18)}`,async()=>{
    if(identity===token&&project===$("project-select").value&&context===applicationUseContextGeneration)await openApplicationUse(app.id,instance.id);
   },"使用此本地实例"));
  }
 }
 if(current())$("use-list").replaceChildren(...(rows.length?rows:[row("暂无可使用的CSV实例。先在草案中核查、保存内部版本并创建实例；此处不会自动创建或授权。") ]));
}
function applicationUseButtons(v){
 if(!applicationUseCurrent(v))return;
 const pending=applicationUseRequests.get(applicationUseKey(v));
 const locked=pending&&["sending","unknown","accepted-read-error"].includes(pending.state);
 if(locked&&[...$("use-column").options].some(o=>o.value===pending.body.input.column))$("use-column").value=pending.body.input.column;
 $("use-submit").disabled=v.busy||locked||!$("use-column").value;
 $("use-column").disabled=v.busy||locked;
 $("use-recover").hidden=!pending||!["unknown","accepted-read-error"].includes(pending.state);
 $("use-recover").disabled=v.busy;
 $("use-recover").textContent=pending?.state==="unknown"?"恢复同一运行的接受回执":"重新读取已接受运行";
 $("use-refresh").disabled=v.busy;
}
async function openApplicationUse(appId,id){
 clearApp();clearApplicationUse();
 const v={id,appId,identity:token,project:$("project-select").value,generation:applicationUseGeneration,readGeneration:0,busy:false,instance:null,selected:null,historical:false};applicationUse=v;
 $("use-info").textContent="正在读取保存的版本与材料范围…";
 try{
  const app=await api(`/api/apps/${appId}`);if(!applicationUseCurrent(v))return;
  if(!csvUseApp(app)||app.project_id!==v.project)throw Error("UNSUPPORTED_CAPABILITY");
  v.app=app;
  const pending=applicationUseRequests.get(applicationUseKey(v));v.selected=pending?.runId||null;
  await readApplicationUse(v);
 }catch(error){if(applicationUseCurrent(v)){clearApplicationUseData(v);throw error;}}
}
function clearApplicationUseData(v){
 v.instance=null;
 for(const id of ["use-output","use-history","use-provenance","use-column","use-acceptance"])$(id).replaceChildren();
 $("use-form").hidden=true;$("use-refresh").hidden=false;
 $("use-info").textContent="当前版本或结果无法读取，请核对授权、来源和版本。读取失败不表示任务执行失败。";
 applicationUseButtons(v);
}
// Projection of authorized immutable evidence only. It cannot confirm or publish an app.
function renderApplicationAcceptance(v,release,run){
 const evidence=release.snapshot.check_evidence;
 const hash=value=>typeof value==="string"&&/^[a-f0-9]{64}$/.test(value);
 const checked=evidence?.ref==="csv.exact_integer_sum.v1"&&evidence.status==="PASS"&&
  evidence.candidate_fingerprint===v.app.fingerprint&&
  [evidence.input_fingerprint,evidence.output_fingerprint,evidence.plan_fingerprint].every(hash)&&
  release.snapshot.model_requests===0;
 const record=run&&v.instance.data.find(r=>r.instance_id===v.id&&r.run_id===run.app_run_id&&
  r.release_id===run.release_id&&r.version===run.result_version);
 const verified=run?.status==="SUCCEEDED"&&run.result&&record&&
  record.data.result.resource_id===run.result.resource_id&&record.data.result.column===run.result.column&&
  record.data.result.sum===run.result.sum&&record.data.result.count===run.result.count;
 const status=run&&["QUEUED","RUNNING","SUCCEEDED","FAILED","PARTIAL","UNKNOWN","PAUSED","CANCELLED"].includes(run.status)?run.status:"UNKNOWN";
 $("use-acceptance").replaceChildren(
  row(`固定版本样本工具检查：${checked?"PASS":"UNKNOWN"}。仅一个冻结样本的整数求和检查，不代表全部新输入或业务目标通过。`),
  row(run?`${v.historical?"所选历史":"本次"}技术执行：${status}；结果核对：${verified?`PASS · v${run.result_version}`:"尚无可核对的成功结果"}。`:"尚未选择运行；历史成功不作为本次验收。"),
  row("目标语义验收：NOT_RUN；用户确认：PENDING；正式发布：关闭。内部版本批准不替代这些验收。"),
  row("适用范围：固定CSV材料，仅数值列参数可变；当前模型请求0。")
 );
}
async function readApplicationUse(v){
 const generation=++v.readGeneration,current=()=>applicationUseCurrent(v)&&generation===v.readGeneration;
 try{
  const instance=await api(`/api/internal/instances/${v.id}`);if(!current())return;
  if(instance.project_id!==v.project||instance.source_app_id!==v.appId||instance.id!==v.id||instance.formal_publication_enabled!==false)throw Error("VERSION_CONFLICT");
  const release=await api(`/api/internal/releases/${instance.release_id}`);if(!current())return;
  const app=await api(`/api/apps/${v.appId}`);if(!current())return;
  if(!csvUseApp(app)||app.project_id!==v.project||release.project_id!==v.project||release.fingerprint!==instance.release_fingerprint||release.snapshot.draft.id!==v.appId||release.snapshot.draft.fingerprint!==app.fingerprint)throw Error("VERSION_CONFLICT");
  v.instance=instance;v.app=app;
  const previous=$("use-column").value,pending=applicationUseRequests.get(applicationUseKey(v));
  $("use-column").replaceChildren(...app.input_guidance.columns.filter(c=>c.numeric).map(c=>new Option(c.name,c.name)));
  if([...$("use-column").options].some(o=>o.value===(pending?.state==="unknown"?pending.body.input.column:previous)))$("use-column").value=pending?.state==="unknown"?pending.body.input.column:previous;
  const material=release.snapshot.draft.candidate.manifest.data_bindings[0].resource_ref;
  $("use-info").textContent=`${app.name} · 未发布内部版本 · 固定材料 ${material} · 只读CSV求和；仅数值列可变，0模型请求，目标语义验收未执行。`;
  $("use-provenance").textContent=JSON.stringify({instance_id:v.id,release_id:instance.release_id,revision:instance.revision,release_fingerprint:instance.release_fingerprint,resource_id:material,source:app.candidate.task_proof||app.candidate.extraction||null},null,2);
  $("use-form").hidden=false;$("use-refresh").hidden=false;
  $("use-output").replaceChildren();
  const run=instance.runs.find(r=>r.id===v.selected);
  if(v.selected&&!run)throw Error("VERSION_CONFLICT: accepted run is not bound to this instance");
  if(run){
   if(run.instance_id!==v.id)throw Error("VERSION_CONFLICT");
   const label=v.historical?"已选择的历史运行":"本次运行";
   $("use-output").append(row(`${label} ${run.id} · ${run.status} · 结果版本 ${run.result_version??"尚无"}`));
   if(run.status==="SUCCEEDED"&&run.result)$("use-output").append(row(`${run.result.column} 合计 ${run.result.sum}，共 ${run.result.count} 条。工具结果已核验；目标语义验收未执行。`));
   else $("use-output").append(row(run.error?.code?`本次没有可展示的新结果：${run.error.code}。` : "尚无本次新结果；下方历史成功不表示本次成功。"));
  }else $("use-output").append(row("本页尚未选择或发起运行；下方仅为持久历史，不是本次新结果。"));
  $("use-history").replaceChildren(...instance.runs.map(r=>row(`${r.id.slice(0,18)} · ${r.status} · 结果版本 ${r.result_version??"无"}`,async()=>{
   if(!applicationUseCurrent(v)||v.busy)return;v.selected=r.id;v.historical=true;await readApplicationUse(v);
  },"查看这次运行")),...instance.data.map(record=>row(`历史结果 v${record.version} · ${record.data.result.column} 合计 ${record.data.result.sum}，${record.data.result.count} 条 · ${record.release_id}`)));
  renderApplicationAcceptance(v,release,run);
  applicationUseButtons(v);
 }catch(error){if(!current())return;clearApplicationUseData(v);throw error;}
}
async function submitApplicationUse(v,recover=false){
 if(!applicationUseCurrent(v)||v.busy)return;
 const key=applicationUseKey(v);let pending=applicationUseRequests.get(key);
 if(!recover){
  if(!v.instance||pending&&["sending","unknown","accepted-read-error"].includes(pending.state))return;
  pending={state:"new",body:{expected_revision:v.instance.revision,expected_release_fingerprint:v.instance.release_fingerprint,input:{column:$("use-column").value},request_key:crypto.randomUUID()},runId:null,uncertain:false};applicationUseRequests.set(key,pending);
 }
 if(!pending)return;
 if(!recover){$("use-acceptance").replaceChildren();v.selected=null;v.historical=false;$("use-output").replaceChildren(row("正在确认新运行的接受回执；下方历史结果不是本次新结果。"));}
 v.busy=true;applicationUseButtons(v);
 try{
  if(pending.state!=="accepted-read-error"){
   pending.state="sending";
   try{
    const reply=await api(`/api/internal/instances/${v.id}/runs`,"POST",pending.body);
    if(typeof reply.run_id!=="string"||!/^run_[a-f0-9]{32}$/.test(reply.run_id))throw Error("Invalid receipt");
    pending.runId=reply.run_id;pending.state="accepted-read-error";
   }catch(error){
    const rejected=!pending.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
    pending.state=rejected?"rejected":"unknown";if(!rejected)pending.uncertain=true;
    if(applicationUseCurrent(v)){$("use-output").replaceChildren(row(rejected?`提交被拒绝：${error.message}`:"接受回执未确认；输入已冻结。显式恢复使用原请求键，不会另建运行。"));if(error.httpStatus===403)clearApplicationUseData(v);}
    return;
   }
  }
  if(!applicationUseCurrent(v))return;
  v.selected=pending.runId;v.historical=false;
  await readApplicationUse(v);if(applicationUseCurrent(v))pending.state="accepted";
 }finally{
  v.busy=false;applicationUseButtons(v);
  const live=applicationUse;
  if(live!==v&&applicationUseCurrent(live)&&applicationUseKey(live)===key&&applicationUseRequests.get(key)===pending){
   applicationUseButtons(live);
   if(["unknown","accepted-read-error"].includes(pending.state))$("use-output").replaceChildren(row(pending.state==="unknown"?"原运行接受回执未确认；请恢复同一运行，不能另建重复任务。":"原运行已接受；请重新读取该持久运行，不会再次提交。"));
  }
 }
}
$("use-form").onsubmit=safe(()=>submitApplicationUse(applicationUse));
$("use-recover").onclick=safe(()=>submitApplicationUse(applicationUse,true));
$("use-refresh").onclick=safe(async()=>{const v=applicationUse;if(v&&applicationUseCurrent(v)&&!v.busy)await readApplicationUse(v);});

// Explicit source selection only; no cached claims survive a context change or cold page.
let conditionalContext=null,conditionalGeneration=0;
function clearConditionalChecks(clearList=false){
 conditionalGeneration++;conditionalContext=null;
 if(typeof clearConditionalRuns==="function")clearConditionalRuns();
 $("condition-form").hidden=true;$("condition-recheck").hidden=true;
 $("condition-source").replaceChildren();$("condition-results").replaceChildren();
 $("condition-status").textContent="旧证据已清除。请显式打开当前授权资料。";
 $("condition-form").reset();$("condition-submit").disabled=false;
 if(clearList)$("condition-resource").replaceChildren(new Option("请选择", ""));
}
function conditionCurrent(c){return conditionalContext===c&&c.identity===token&&c.project===$("project-select").value&&c.generation===conditionalGeneration;}
async function listConditionalSources(){
 clearConditionalChecks(true);
 const c={identity:token,project:$("project-select").value,generation:conditionalGeneration};conditionalContext=c;
 try{
  const items=await api(`/api/projects/${c.project}/resources`);if(!conditionCurrent(c))return;
  $("condition-resource").replaceChildren(new Option("请选择", ""),...items.filter(r=>["txt","md"].includes(r.format)).map(r=>new Option(`${r.name} · 内容版本 ${r.hash.slice(0,12)}`,r.id)));
  $("condition-status").textContent="仅列出当前授权文本资料；选择后再读取。仅支持 A-S 固定资料，其他内容将拒绝。";
 }catch(error){if(conditionCurrent(c)){clearConditionalChecks(true);$("condition-status").textContent=`资料列表不可读：${error.message}；旧证据失效。`;}}
}
async function openConditionalSource(){
 const rid=$("condition-resource").value;if(!rid)return;
 clearConditionalChecks();
 const c={identity:token,project:$("project-select").value,generation:conditionalGeneration,rid};conditionalContext=c;
 $("condition-status").textContent="正在核对授权与实际内容版本…";
 try{
  const source=await api(`/api/projects/${c.project}/conditional-checks/sources/${rid}`);if(!conditionCurrent(c))return;
  if(source.resource_id!==rid||source.contract.source_hash!==source.hash)throw Error("VERSION_CONFLICT");
  c.source=source;
  if(typeof showConditionalRuns==="function")showConditionalRuns(source);
  $("condition-source").replaceChildren(row(`资料 ${rid} · 内容 SHA256 ${source.hash} · 注册规则 ${source.contract.id} v${source.contract.version} · 合同 ${source.contract.fingerprint}`),...source.rules.map(r=>row(`${r.rule_id} · 第${r.line}行：${r.quote}`)));
  $("condition-form").hidden=false;
  $("condition-status").textContent="资料版本已核查。填写假设事实及人工报告；检查不确认真实事实。";
 }catch(error){if(conditionCurrent(c)){clearConditionalChecks();$("condition-status").textContent=`资料不支持、已变化或权限不足：${error.message}；旧证据失效。`;}}
}
function conditionBody(c){
 const bool=id=>$("condition-"+id).value===""?null:$("condition-"+id).value==="true";
 const number=id=>$("condition-"+id).value===""?null:Number($("condition-"+id).value);
 return {resource_id:c.rid,expected_source_hash:c.source.hash,expected_contract_fingerprint:c.source.contract.fingerprint,
  scenario:{kind:"HYPOTHETICAL_EMPLOYEE",trip_ended:bool("trip"),amount:number("amount"),receipt_present:bool("receipt"),approved:bool("approved"),elapsed_days:number("days")},
  report:{findings:c.source.rules.map(r=>({rule_id:r.rule_id,applies:$("condition-"+r.rule_id).value,citation:{line:r.line,quote:r.quote}})),decision:$("condition-decision").value,next_actions:[...$("condition-actions").selectedOptions].map(o=>o.value),deadline_days:number("deadline"),absolute_date:$("condition-date").value,receipt_restarts_deadline:bool("restart"),explanation:$("condition-explanation").value}};
}
async function runConditionalCheck(recheck=false){
 const c=conditionalContext;if(!c?.source||!conditionCurrent(c)||c.busy)return;
 const body=recheck?c.body:conditionBody(c);if(!body)return;
 const read=(c.readGeneration||0)+1;c.readGeneration=read;
 const current=()=>conditionCurrent(c)&&c.readGeneration===read;
 c.busy=true;$("condition-submit").disabled=true;$("condition-results").replaceChildren();$("condition-recheck").hidden=true;
 $("condition-status").textContent="正在重新授权读取资料并核对；此前证据不作为当前结果。";
 try{
  const result=await api(`/api/projects/${c.project}/conditional-checks`,"POST",body);if(!current())return;
  if(result.source.resource_id!==c.rid||result.source.hash!==body.expected_source_hash||result.contract_fingerprint!==body.expected_contract_fingerprint)throw Error("VERSION_CONFLICT");
  c.body=body;
  const names={SATISFIED:"满足",UNSATISFIED:"不满足",UNKNOWN:"未知",NOT_APPLICABLE:"不适用"};
  $("condition-results").replaceChildren(row(`结构化报告核对 ${result.check_status} · 注册规则决策 ${result.decision}；PASS 不表示可以提交或用户已确认。`),...result.rule_results.map(r=>row(`${r.rule_id}：${names[r.satisfaction]} · ${r.reason} 引用资料 ${result.source.resource_id} 内容版本 ${result.source.hash} 第${r.citation.line}行：${r.citation.quote}`)),...result.checks.map(r=>row(`${r.id}：${r.status}`)),row(`语义 ${result.semantic_status}；用户确认 ${result.owner_acceptance}；自由说明 ${result.explanation_status}；正式发布关闭。仅本页证据，刷新/冷会话需重新核对。`));
  $("condition-status").textContent="核对完成；真实事实与开放语言解释未验收。";$("condition-recheck").hidden=false;
 }catch(error){if(current()){
  c.body=null;c.source=null;$("condition-source").replaceChildren();$("condition-form").hidden=true;
  $("condition-status").textContent=`核对未完成，旧证据失效：${error.message}。资料变化/撤权需重新选择；请求失败不等于业务条件不满足。`;
 }}finally{c.busy=false;if(conditionCurrent(c))$("condition-submit").disabled=false;}
}
$("condition-list").onclick=safe(listConditionalSources);
$("condition-open").onclick=safe(openConditionalSource);
$("condition-resource").onchange=()=>clearConditionalChecks();
$("condition-form").onsubmit=safe(()=>runConditionalCheck());
$("condition-recheck").onclick=safe(()=>runConditionalCheck(true));
$("condition-form").oninput=()=>{if(conditionalContext){conditionalContext.readGeneration=(conditionalContext.readGeneration||0)+1;conditionalContext.body=null;}$("condition-results").replaceChildren();$("condition-recheck").hidden=true;$("condition-status").textContent="输入已变化，旧证据失效；请重新核对。";};

function invalidateConditionalSource(reason){
 if(typeof clearConditionalRuns==="function"){clearConditionalRuns();$("condition-run-status").textContent=`旧来源绑定证据失效：${reason}。请重新打开当前授权资料；已接受Run未取消，同键回执仍保留。`;}
 if(!conditionalContext?.source)return;
 clearConditionalChecks();$("condition-status").textContent=`旧证据失效：${reason}。请重新选择并核对授权资料。`;
}
function reconcileConditionalSources(items){
 if(typeof reconcileBoundedSources==="function")reconcileBoundedSources(items);
 const c=conditionalContext;if(!c?.source||!conditionCurrent(c))return;
 const item=items.find(r=>r.id===c.rid);
 if(!item||item.hash!==c.source.hash||!["txt","md"].includes(item.format))invalidateConditionalSource("资料版本变化或授权撤销");
}
