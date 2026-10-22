"use strict";
// Protocol tasks share the project canvas; they do not claim AppManifest/publication compatibility.
let protocolGeneration=0,protocolContext=null,protocolCatalog=[],protocolMaterials=[];
const protocolIntents=new Map();
function protocolCurrent(ctx){return protocolContext===ctx&&ctx.generation===protocolGeneration&&ctx.token===token&&ctx.project===$("project-select").value;}
function clearProtocol(){clearProtocolCompletion();protocolGeneration++;protocolContext=null;protocolCatalog=[];protocolMaterials=[];$("protocol-detail").hidden=true;$("protocol-result").textContent="";$("protocol-state").textContent="";$("protocol-cold-form").hidden=true;$("protocol-extract").hidden=true;$("protocol-recover-retry").hidden=true;$("protocol-source-submit").disabled=true;$("protocol-contract").replaceChildren();$("protocol-source-materials").replaceChildren();$("protocol-inputs").replaceChildren();$("protocol-source-goal").textContent="";$("protocol-source-status").textContent="";$("protocol-run-id").textContent="";$("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();$("protocol-cold-contract").replaceChildren();}
async function protocolRequest(ctx,path,method="GET",body){const r=await fetch(path,{method,headers:{Authorization:`Bearer ${ctx.token}`,"Content-Type":"application/json"},...(body?{body:JSON.stringify(body)}:{})});const data=await r.json();if(!r.ok){const error=new Error(data.error?.code||"请求失败");error.detail=data.error?.message;error.httpStatus=r.status;throw error;}return data;}
function protocolStatus(ctx,text){if(protocolCurrent(ctx))$("protocol-state").textContent=text;}
function protocolContract(id){return protocolCatalog.find(item=>item.contract_id===id);}
function protocolInputFields(container,value,preserve=false){const previous=preserve?Object.fromEntries([...container.querySelectorAll("[data-protocol-input]")].map(field=>[field.dataset.protocolInput,field.value])):{};container.replaceChildren(...Object.entries(value||{}).map(([name,input])=>{const label=document.createElement("label");label.textContent=name;const field=document.createElement("input");field.dataset.protocolInput=name;field.value=previous[name]??(typeof input==="string"?input:JSON.stringify(input));field.dataset.valueType=typeof input;field.required=true;label.append(field);return label;}));}
function protocolInputs(container){return Object.fromEntries([...container.querySelectorAll("[data-protocol-input]")].map(field=>[field.dataset.protocolInput,field.dataset.valueType==="string"?field.value:JSON.parse(field.value)]));}
function protocolMaterialField(labelText,allowed,selected=""){const label=document.createElement("label");label.textContent=labelText;const select=document.createElement("select");select.required=true;select.append(new Option("请选择本项目已授权材料",""));for(const resource of allowed)select.append(new Option(`${resource.name} · ${resource.hash.slice(0,12)}`,resource.id));select.value=selected;label.append(select);return label;}
function clearProtocolSelection(){clearProtocolCompletion();const ctx=protocolContext;if(ctx){ctx.selection++;ctx.run=null;ctx.plan=null;ctx.renderedPlan=null;ctx.recoveryPending=null;}$("protocol-detail").hidden=true;$("protocol-result").textContent="";$("protocol-state").textContent="";$("protocol-cold-form").hidden=true;$("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();$("protocol-extract").hidden=true;}
function protocolSelectRun(id,userSelection=true){const ctx=protocolContext;if(!ctx)return;if(userSelection)ctx.intent=(ctx.intent||0)+1;if(ctx.run&&ctx.run.run_id!==id)clearProtocolSelection();}
function renderProtocolSource(){const ctx=protocolContext,contract=protocolContract($("protocol-contract").value);if(!ctx||!protocolCurrent(ctx)||!contract)return;$("protocol-source-goal").textContent=contract.public_goal;protocolInputFields($("protocol-inputs"),contract.public_inputs,ctx.inputContract===contract.contract_id);ctx.inputContract=contract.contract_id;$("protocol-source-materials").replaceChildren(...contract.resource_hashes.map((hash,index)=>{const matches=protocolMaterials.filter(resource=>resource.hash===hash);return protocolMaterialField(`材料 ${index+1}`,matches,matches.length===1?matches[0].id:"");}));$("protocol-source-submit").disabled=contract.resource_hashes.some(hash=>!protocolMaterials.some(resource=>resource.hash===hash));$("protocol-source-status").textContent=$("protocol-source-submit").disabled?"缺少此注册任务匹配的已授权材料，请先在资源工作区保存材料。":"注册契约已冻结；任务输出仍须独立核查。默认未配置协议 provider 时会等待资源。";}
async function refreshProtocol(materialRead=null){
  const project=$("project-select").value;
  if(!project||!token){clearProtocol();return;}
  // A supplied read belongs only to its originating refresh, including its
  // generation witness. Stale/ABA reads stop here; they cannot fall back to
  // another request or overwrite a newer batch in the same project.
  const readCurrent=()=>!materialRead||(materialRead.project===project&&materialRead.token===token&&
    project===$("project-select").value&&typeof materialRead.current==="function"&&materialRead.current());
  if(!readCurrent())return;
  const previous=protocolContext;
  if(previous?.project===project&&previous.token===token&&previous.catalogReady){
    const materials=materialRead?materialRead.materials:await protocolRequest(previous,`/api/projects/${project}/resources`);
    if(!protocolCurrent(previous)||!readCurrent())return;
    if(JSON.stringify(materials)!==JSON.stringify(protocolMaterials)){
      protocolMaterials=materials;renderProtocolSource();if(previous.plan)renderProtocolCold();
    }
    return;
  }
  // An overlapping initial batch may invalidate an in-flight catalog. The
  // next current batch must initialize it rather than leave a partial context.
  clearProtocol();
  const ctx={project,token,generation:protocolGeneration,selection:0,intent:0,run:null,busy:false,catalogReady:false};
  protocolContext=ctx;
  try{
    const [catalog,materials]=await Promise.all([
      protocolRequest(ctx,`/api/projects/${project}/protocol/contracts`),
      materialRead?Promise.resolve(materialRead.materials):protocolRequest(ctx,`/api/projects/${project}/resources`)
    ]);
    if(!protocolCurrent(ctx)||!readCurrent())return;
    protocolCatalog=catalog.items;protocolMaterials=materials;ctx.catalogReady=true;
    $("protocol-contract").replaceChildren(...protocolCatalog.filter(item=>item.phase==="source").map(item=>new Option(`${item.family} · v${item.version}`,item.contract_id)));
    renderProtocolSource();
  }catch(error){if(protocolCurrent(ctx)&&readCurrent())$("protocol-source-status").textContent=error.message;}
}
function renderProtocolRun(ctx){if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden)return;const run=ctx.run;$("protocol-detail").hidden=false;$("protocol-run-id").textContent=run.run_id;protocolStatus(ctx,`${run.phase} · ${run.status} · 语义 ${run.semantic_status} · ${run.semantic_review} · owner ${run.owner_semantic_acceptance||"PENDING"}。注册核查不等于 owner 对真实任务签收；未发布。`);$("protocol-result").textContent=JSON.stringify(run.result||run.error||{},null,2);$("protocol-extract").hidden=!(run.phase==="source"&&run.status==="SUCCEEDED"&&run.semantic_status==="PASS"&&run.semantic_review==="APPROVED");$("protocol-cold-form").hidden=!(run.phase==="extract"&&run.status==="SUCCEEDED"&&run.result?.compiled_plan);$("protocol-recover").disabled=ctx.busy;$("protocol-recover-retry").hidden=!ctx.recoveryPending;renderProtocolCompletion(ctx);if(!$("protocol-cold-form").hidden){const plan=run.result.compiled_plan;if(ctx.renderedPlan===plan.plan_fingerprint)return;ctx.renderedPlan=plan.plan_fingerprint;ctx.plan=plan;$("protocol-cold-contract").replaceChildren(...protocolCatalog.filter(item=>item.phase==="cold").map(item=>new Option(`${item.family} · v${item.version}`,item.contract_id)));renderProtocolCold();}}
function renderProtocolCold(){const ctx=protocolContext,contract=protocolContract($("protocol-cold-contract").value);if(!ctx?.plan||!protocolCurrent(ctx)||!contract)return;protocolInputFields($("protocol-cold-inputs"),contract.public_inputs,ctx.coldInputContract===contract.contract_id);ctx.coldInputContract=contract.contract_id;const allowed=protocolMaterials.filter(resource=>contract.resource_hashes.includes(resource.hash));$("protocol-cold-materials").replaceChildren(...Object.entries(ctx.plan.candidate.resources).map(([name,id])=>{const source=protocolMaterials.find(resource=>resource.id===id);const label=protocolMaterialField(`${name} · 来源 ${source?.name||id}`,allowed,allowed.length===1?allowed[0].id:"");label.querySelector("select").dataset.binding=name;return label;}));$("protocol-cold-submit").disabled=contract.resource_hashes.some(hash=>!allowed.some(resource=>resource.hash===hash));}
async function showProtocolRun(id,ctx=protocolContext){if(!ctx||!protocolCurrent(ctx)||$("projects").hidden)return;const selection=++ctx.selection,workspace=workspaceSelectionGeneration;try{const run=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${id}`);if(!protocolCurrent(ctx)||selection!==ctx.selection||activeRun!==id||workspace!==workspaceSelectionGeneration||$("projects").hidden)return;if(ctx.run?.run_id!==run.run_id)ctx.recoveryPending=null;ctx.run=run;renderProtocolRun(ctx);}catch(error){if(protocolCurrent(ctx)&&selection===ctx.selection&&workspace===workspaceSelectionGeneration&&!$("projects").hidden){ctx.run=null;ctx.plan=null;ctx.renderedPlan=null;$("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();$("protocol-detail").hidden=true;$("protocol-result").textContent="";protocolStatus(ctx,error.message);throw error;}}}
async function renderSelectedProtocol(run,id,current=()=>true){if(!current())return;await refreshProtocol();const ctx=protocolContext;if(!ctx||!protocolCurrent(ctx)||activeRun!==id||!current())return;await showProtocolRun(id,ctx);if(!current()||!protocolCurrent(ctx)||activeRun!==id||ctx.run?.run_id!==id)return;$("result").textContent="协议成果与核对状态见下方。";$("commands").replaceChildren();$("reconcile-panel").hidden=true;$("events").textContent="";$("raw-result").textContent="";}
async function protocolSubmit(phase,payload){const ctx=protocolContext;if(!ctx||!protocolCurrent(ctx)||ctx.busy)return;const fingerprint=JSON.stringify({token:ctx.token,project:ctx.project,phase,payload});let intent=protocolIntents.get(fingerprint);if(!intent){intent={body:{...payload,request_key:crypto.randomUUID()}};protocolIntents.set(fingerprint,intent);}const intentEpoch=ctx.intent,selectedRun=activeRun;ctx.busy=true;protocolStatus(ctx,"正在提交；已接受任务不会随页面关闭取消。");try{const made=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/${phase}`,"POST",intent.body);if(!protocolCurrent(ctx)||ctx.intent!==intentEpoch||activeRun!==selectedRun)return;activeRun=made.run_id;ctx.run=made;ctx.recoveryPending=null;renderProtocolRun(ctx);await showProtocolRun(made.run_id,ctx);}catch(error){if(ctx.intent===intentEpoch&&activeRun===selectedRun)protocolStatus(ctx,`${error.message}。提交回执不明时，仅再次提交同一输入可使用原请求键核对；不会自动重发。`);}finally{ctx.busy=false;if(protocolCurrent(ctx)&&ctx.intent===intentEpoch&&ctx.run)renderProtocolRun(ctx);}}
async function recoverProtocol(retry=false){const ctx=protocolContext,run=ctx?.run;if(!ctx||!run||!protocolCurrent(ctx)||ctx.busy)return;let pending=ctx.recoveryPending;if(!retry){pending={expected_version:run.version,expected_fence:run.fence,request_key:crypto.randomUUID()};ctx.recoveryPending=pending;}if(!pending)return;ctx.busy=true;try{const receipt=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${run.run_id}/recover`,"POST",pending);if(!protocolCurrent(ctx)||ctx.run?.run_id!==run.run_id)return;ctx.recoveryPending=null;await showProtocolRun(run.run_id,ctx);if(!protocolCurrent(ctx)||activeRun!==run.run_id||ctx.run?.run_id!==run.run_id)return;protocolStatus(ctx,`核对结果 ${receipt.recovery} · provider请求 ${receipt.provider_requests} · 不自动重发。${receipt.global_send_blocked?"共享发送已停止。":""}`);}catch(error){if(protocolCurrent(ctx)&&ctx.run?.run_id===run.run_id){protocolStatus(ctx,`${error.message}。可用原核对键重新读取，不继续执行。`);$("protocol-recover-retry").hidden=false;}}finally{ctx.busy=false;if(protocolCurrent(ctx))$("protocol-recover").disabled=false;}}
$("protocol-contract").onchange=renderProtocolSource;$("protocol-cold-contract").onchange=renderProtocolCold;
$("protocol-source-form").onsubmit=safe(()=>{const contract=protocolContract($("protocol-contract").value);if(!contract)throw Error("请先读取注册任务");const resources=[...$("protocol-source-materials").querySelectorAll("select")].map(field=>field.value);if(resources.some(id=>!id)||new Set(resources).size!==resources.length)throw Error("请选择不同的匹配材料");return protocolSubmit("source",{contract_id:contract.contract_id,goal:contract.public_goal,inputs:protocolInputs($("protocol-inputs")),resource_ids:resources});});
$("protocol-extract").onclick=safe(()=>{const run=protocolContext?.run;if(!run||run.phase!=="source"||run.status!=="SUCCEEDED"||run.semantic_status!=="PASS")throw Error("来源尚未通过独立注册核查");return protocolSubmit("extract",{source_run_id:run.run_id,expected_source_fingerprint:run.result_fingerprint});});
$("protocol-cold-form").onsubmit=safe(()=>{const ctx=protocolContext,contract=protocolContract($("protocol-cold-contract").value);if(!ctx?.plan||!contract)throw Error("请先读取协议草案与冷输入契约");const bindings=Object.fromEntries([...$("protocol-cold-materials").querySelectorAll("select")].map(field=>[field.dataset.binding,field.value]));if(Object.values(bindings).some(id=>!id)||new Set(Object.values(bindings)).size!==Object.values(bindings).length)throw Error("请选择不同的新材料");return protocolSubmit("cold",{contract_id:contract.contract_id,extraction_run_id:ctx.run.run_id,expected_plan_fingerprint:ctx.plan.plan_fingerprint,inputs:protocolInputs($("protocol-cold-inputs")),resource_bindings:bindings});});
$("protocol-read").onclick=safe(()=>{const ctx=protocolContext;if(ctx?.run)return showProtocolRun(ctx.run.run_id,ctx);});$("protocol-recover").onclick=safe(()=>recoverProtocol());$("protocol-recover-retry").onclick=safe(()=>recoverProtocol(true));

// A completion command is separate from state-only /recover and never sends a model request.
// Page memory retains the exact command across Run/project selection; nothing stores a bearer on disk.
const protocolCompletionIntents=new Map();
function protocolCompletionKey(ctx,rid){return JSON.stringify([ctx.token,ctx.project,rid]);}
function clearProtocolCompletion(){
  $("protocol-completion").hidden=true;
  $("protocol-completion-confirm").checked=false;
  $("protocol-completion-submit").disabled=true;
  $("protocol-completion-retry").hidden=true;
  $("protocol-completion-status").textContent="";
}
function protocolCompletionWorkspaceChanged(){
  clearProtocolCompletion();
  const ctx=protocolContext;
  if(!ctx||!protocolCurrent(ctx))return;
  ctx.intent=(ctx.intent||0)+1;ctx.selection++;
  ctx.completionSignature=null;
  if($("projects").hidden){
    if(ctx.run)ctx.run={...ctx.run,result:null,result_fingerprint:null,error:null};
    ctx.plan=null;ctx.renderedPlan=null;
    $("protocol-result").textContent="";$("protocol-cold-form").hidden=true;
    $("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();
  }else if(ctx.run)renderProtocolCompletion(ctx);
}
function protocolCompletionEligible(run){
  return run?.namespace==="protocol_jobs.v1"&&run.phase==="extract"&&run.result===null&&
    ["RUNNING","WAITING_RESOURCE","RECONCILING"].includes(run.status)&&
    run.error?.code!=="OUTCOME_UNKNOWN"&&Number.isSafeInteger(run.version)&&run.version>=1&&
    Number.isSafeInteger(run.fence)&&run.fence>=0&&Number.isSafeInteger(run.version+1)&&Number.isSafeInteger(run.fence+1);
}
function protocolCompletionReceipt(value,rid,body){
  const keys=["namespace","run_id","status","version","fence","plan_fingerprint","provider_requests","automatic_resend","cached"];
  return value!==null&&typeof value==="object"&&!Array.isArray(value)&&
    Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key))&&
    value.namespace==="protocol-extract-completion.v2"&&value.run_id===rid&&value.status==="SUCCEEDED"&&
    Number.isSafeInteger(value.version)&&value.version===body.expected_version+1&&
    Number.isSafeInteger(value.fence)&&value.fence===body.expected_fence+1&&
    typeof value.plan_fingerprint==="string"&&/^[a-f0-9]{64}$/.test(value.plan_fingerprint)&&
    value.provider_requests===0&&value.automatic_resend===false&&typeof value.cached==="boolean";
}
function protocolCompletionReadMatches(run,entry){
  const receipt=entry.receipt;
  return !!receipt&&run?.namespace==="protocol_jobs.v1"&&run.phase==="extract"&&
    run.run_id===entry.rid&&run.status==="SUCCEEDED"&&run.version===receipt.version&&run.fence===receipt.fence&&
    run.result?.compiled_plan?.plan_fingerprint===receipt.plan_fingerprint;
}
function renderProtocolCompletion(ctx){
  if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden){clearProtocolCompletion();return;}
  const run=ctx.run,entry=protocolCompletionIntents.get(protocolCompletionKey(ctx,run.run_id));
  if(entry?.state==="accepted-read-error"&&protocolCompletionReadMatches(run,entry))entry.state="accepted";
  const eligible=protocolCompletionEligible(run),pending=["sending","unknown","accepted-read-error"].includes(entry?.state);
  $("protocol-completion").hidden=!eligible&&!pending;
  const signature=JSON.stringify([ctx.intent,workspaceSelectionGeneration,run.run_id,run.version,run.fence]);
  if(ctx.completionSignature!==signature){ctx.completionSignature=signature;$("protocol-completion-confirm").checked=false;}
  const blocked=ctx.busy||pending||entry?.state==="accepted";
  $("protocol-completion-confirm").disabled=!eligible||blocked;
  $("protocol-completion-submit").hidden=!eligible||pending||entry?.state==="accepted";
  $("protocol-completion-submit").disabled=!eligible||blocked||!$("protocol-completion-confirm").checked;
  $("protocol-completion-retry").hidden=!["unknown","accepted-read-error"].includes(entry?.state);
  $("protocol-completion-retry").disabled=ctx.busy;
  $("protocol-completion-retry").textContent=entry?.state==="accepted-read-error"?"重新读取已完成成果（不再提交）":"用原完成键核对回执";
  $("protocol-completion-status").textContent=entry?.message||"是否可完成由服务端核对；此处不表示租约已到期或证据已经齐备。";
}
async function readProtocolCompletion(ctx,entry,current){
  const selection=++ctx.selection;
  try{
    const run=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${entry.rid}`);
    if(!protocolCompletionReadMatches(run,entry))throw Error("完成成果与回执不匹配");
    if(!current()||selection!==ctx.selection)return;
    entry.state="accepted";entry.message="已完成原提取；没有新增模型请求。语义验收和发布状态仍按原成果显示。";
    ctx.run=run;renderProtocolRun(ctx);
  }catch(error){
    entry.state="accepted-read-error";entry.message="完成回执已确认，成果读取未通过；只能重新读取原成果，不再提交完成命令。";
    if(current()&&selection===ctx.selection){
      ctx.run={...ctx.run,result:null,result_fingerprint:null,error:null};ctx.plan=null;ctx.renderedPlan=null;
      $("protocol-result").textContent="";$("protocol-cold-form").hidden=true;
      $("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();
      renderProtocolCompletion(ctx);
    }
  }
}
async function completeProtocolExtraction(retry=false){
  const ctx=protocolContext,run=ctx?.run;
  if(!ctx||!run||!protocolCurrent(ctx)||$("projects").hidden||activeRun!==run.run_id||ctx.busy)return;
  const key=protocolCompletionKey(ctx,run.run_id),old=protocolCompletionIntents.get(key);
  let entry=old;
  if(retry){
    if(!entry||!["unknown","accepted-read-error"].includes(entry.state))return;
  }else{
    if(!protocolCompletionEligible(run)||!$("protocol-completion-confirm").checked||
        ["sending","unknown","accepted-read-error","accepted"].includes(entry?.state))return;
    entry={rid:run.run_id,body:Object.freeze({expected_version:run.version,expected_fence:run.fence,request_key:crypto.randomUUID()}),state:"new",uncertain:false};
    protocolCompletionIntents.set(key,entry);
  }
  const intent=ctx.intent,workspace=workspaceSelectionGeneration,current=()=>protocolCurrent(ctx)&&ctx.intent===intent&&workspace===workspaceSelectionGeneration&&!$("projects").hidden&&activeRun===entry.rid&&ctx.run?.run_id===entry.rid;
  ctx.busy=true;$("protocol-completion-confirm").checked=false;
  try{
    if(entry.state==="accepted-read-error"){
      renderProtocolCompletion(ctx);await readProtocolCompletion(ctx,entry,current);return;
    }
    entry.state="sending";entry.message="正在核对并尝试结算原提取；没有发起模型请求。";renderProtocolCompletion(ctx);
    try{
      const receipt=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${entry.rid}/complete-extraction`,"POST",entry.body);
      if(!protocolCompletionReceipt(receipt,entry.rid,entry.body))throw Error("完成回执未通过核对");
      entry.receipt=receipt;entry.state="accepted-read-error";entry.message="完成回执已确认，正在读取原成果。";
    }catch(error){
      const rejected=!entry.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
      entry.state=rejected?"rejected":"unknown";if(!rejected)entry.uncertain=true;
      entry.message=rejected?`服务端拒绝完成：${error.message}。请先读取当前状态；没有新增模型请求。`:
        "完成命令回执 UNKNOWN；仅可显式使用原完成键核对，不另建运行、不补传响应、不自动重发。";
      return;
    }
    if(current())await readProtocolCompletion(ctx,entry,current);
  }finally{
    ctx.busy=false;
    if(current()){renderProtocolCompletion(ctx);$("protocol-recover").disabled=false;}
  }
}
$("protocol-completion-confirm").onchange=()=>{if(protocolContext)renderProtocolCompletion(protocolContext);};
$("protocol-completion-submit").onclick=safe(()=>completeProtocolExtraction());
$("protocol-completion-retry").onclick=safe(()=>completeProtocolExtraction(true));
