"use strict";
// Protocol tasks share the project canvas; they do not claim AppManifest/publication compatibility.
let protocolGeneration=0,protocolContext=null,protocolCatalog=[],protocolMaterials=[];
const protocolIntents=new Map();
function protocolCurrent(ctx){return protocolContext===ctx&&ctx.generation===protocolGeneration&&ctx.token===token&&ctx.project===$("project-select").value;}
function clearProtocol(){clearProtocolCompletionReadback();clearProtocolCompletion();protocolGeneration++;protocolContext=null;protocolCatalog=[];protocolMaterials=[];$("protocol-detail").hidden=true;$("protocol-result").textContent="";$("protocol-state").textContent="";$("protocol-cold-form").hidden=true;$("protocol-extract").hidden=true;$("protocol-recover-retry").hidden=true;$("protocol-source-submit").disabled=true;$("protocol-contract").replaceChildren();$("protocol-source-materials").replaceChildren();$("protocol-inputs").replaceChildren();$("protocol-source-goal").textContent="";$("protocol-source-status").textContent="";$("protocol-run-id").textContent="";$("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();$("protocol-cold-contract").replaceChildren();}
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
function renderProtocolRun(ctx){if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden)return;const run=ctx.run;$("protocol-detail").hidden=false;$("protocol-run-id").textContent=run.run_id;protocolStatus(ctx,protocolProjectionUnconfirmed(ctx)?"当前协议状态不可确认；原成果与核查投影已关闭，请只读重新核对。":`${run.phase} · ${run.status} · 语义 ${run.semantic_status} · ${run.semantic_review} · owner ${run.owner_semantic_acceptance||"PENDING"}。注册核查不等于 owner 对真实任务签收；未发布。`);$("protocol-result").textContent=protocolProjectionUnconfirmed(ctx)?"":JSON.stringify(run.result||run.error||{},null,2);$("protocol-extract").hidden=protocolProjectionUnconfirmed(ctx)||!(run.phase==="source"&&run.status==="SUCCEEDED"&&run.semantic_status==="PASS"&&run.semantic_review==="APPROVED");$("protocol-cold-form").hidden=protocolProjectionUnconfirmed(ctx)||!(run.phase==="extract"&&run.status==="SUCCEEDED"&&run.result?.compiled_plan);$("protocol-recover").disabled=ctx.busy;$("protocol-recover-retry").hidden=!ctx.recoveryPending;renderProtocolCompletion(ctx);renderProtocolReview(ctx);renderProtocolCompletionReadback(ctx);if(!$("protocol-cold-form").hidden){const plan=run.result.compiled_plan;if(ctx.renderedPlan===plan.plan_fingerprint)return;ctx.renderedPlan=plan.plan_fingerprint;ctx.plan=plan;$("protocol-cold-contract").replaceChildren(...protocolCatalog.filter(item=>item.phase==="cold").map(item=>new Option(`${item.family} · v${item.version}`,item.contract_id)));renderProtocolCold();}}
function renderProtocolCold(){const ctx=protocolContext,contract=protocolContract($("protocol-cold-contract").value);if(!ctx?.plan||!protocolCurrent(ctx)||!contract)return;protocolInputFields($("protocol-cold-inputs"),contract.public_inputs,ctx.coldInputContract===contract.contract_id);ctx.coldInputContract=contract.contract_id;const allowed=protocolMaterials.filter(resource=>contract.resource_hashes.includes(resource.hash));$("protocol-cold-materials").replaceChildren(...Object.entries(ctx.plan.candidate.resources).map(([name,id])=>{const source=protocolMaterials.find(resource=>resource.id===id);const label=protocolMaterialField(`${name} · 来源 ${source?.name||id}`,allowed,allowed.length===1?allowed[0].id:"");label.querySelector("select").dataset.binding=name;return label;}));$("protocol-cold-submit").disabled=contract.resource_hashes.some(hash=>!allowed.some(resource=>resource.hash===hash));}
async function showProtocolRun(id,ctx=protocolContext){if(!ctx||!protocolCurrent(ctx)||$("projects").hidden)return;const selection=++ctx.selection,workspace=workspaceSelectionGeneration;try{const run=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${id}`);if(!protocolCurrent(ctx)||selection!==ctx.selection||activeRun!==id||workspace!==workspaceSelectionGeneration||$("projects").hidden)return;if(ctx.run?.run_id!==run.run_id)ctx.recoveryPending=null;ctx.run=run;acceptProtocolReviewBackgroundRead(ctx,run,selection);acceptProtocolCompletionReadbackBackground(ctx,run,selection);renderProtocolRun(ctx);}catch(error){if(protocolCurrent(ctx)&&selection===ctx.selection&&workspace===workspaceSelectionGeneration&&!$("projects").hidden){ctx.run=null;ctx.plan=null;ctx.renderedPlan=null;$("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();$("protocol-detail").hidden=true;$("protocol-result").textContent="";protocolStatus(ctx,error.message);throw error;}}}
async function renderSelectedProtocol(run,id,current=()=>true){if(!current())return;await refreshProtocol();const ctx=protocolContext;if(!ctx||!protocolCurrent(ctx)||activeRun!==id||!current())return;await showProtocolRun(id,ctx);if(!current()||!protocolCurrent(ctx)||activeRun!==id||ctx.run?.run_id!==id)return;$("result").textContent="协议成果与核对状态见下方。";$("commands").replaceChildren();$("reconcile-panel").hidden=true;$("events").textContent="";$("raw-result").textContent="";}
async function protocolSubmit(phase,payload){const ctx=protocolContext;if(!ctx||!protocolCurrent(ctx)||ctx.busy)return;const fingerprint=JSON.stringify({token:ctx.token,project:ctx.project,phase,payload});let intent=protocolIntents.get(fingerprint);if(!intent){intent={body:{...payload,request_key:crypto.randomUUID()}};protocolIntents.set(fingerprint,intent);}const intentEpoch=ctx.intent,selectedRun=activeRun;ctx.busy=true;protocolStatus(ctx,"正在提交；已接受任务不会随页面关闭取消。");try{const made=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/${phase}`,"POST",intent.body);if(!protocolCurrent(ctx)||ctx.intent!==intentEpoch||activeRun!==selectedRun)return;activeRun=made.run_id;ctx.run=made;ctx.recoveryPending=null;renderProtocolRun(ctx);await showProtocolRun(made.run_id,ctx);}catch(error){if(ctx.intent===intentEpoch&&activeRun===selectedRun)protocolStatus(ctx,`${error.message}。提交回执不明时，仅再次提交同一输入可使用原请求键核对；不会自动重发。`);}finally{ctx.busy=false;if(protocolCurrent(ctx)&&ctx.intent===intentEpoch&&ctx.run)renderProtocolRun(ctx);}}
async function recoverProtocol(retry=false){const ctx=protocolContext,run=ctx?.run;if(!ctx||!run||!protocolCurrent(ctx)||ctx.busy)return;let pending=ctx.recoveryPending;if(!retry){pending={expected_version:run.version,expected_fence:run.fence,request_key:crypto.randomUUID()};ctx.recoveryPending=pending;}if(!pending)return;ctx.busy=true;try{const receipt=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${run.run_id}/recover`,"POST",pending);if(!protocolCurrent(ctx)||ctx.run?.run_id!==run.run_id)return;ctx.recoveryPending=null;await showProtocolRun(run.run_id,ctx);if(!protocolCurrent(ctx)||activeRun!==run.run_id||ctx.run?.run_id!==run.run_id)return;protocolStatus(ctx,`核对结果 ${receipt.recovery} · provider请求 ${receipt.provider_requests} · 不自动重发。${receipt.global_send_blocked?"共享发送已停止。":""}`);}catch(error){if(protocolCurrent(ctx)&&ctx.run?.run_id===run.run_id){protocolStatus(ctx,`${error.message}。可用原核对键重新读取，不继续执行。`);$("protocol-recover-retry").hidden=false;}}finally{ctx.busy=false;if(protocolCurrent(ctx))$("protocol-recover").disabled=false;}}
$("protocol-contract").onchange=renderProtocolSource;$("protocol-cold-contract").onchange=renderProtocolCold;
$("protocol-source-form").onsubmit=safe(()=>{const contract=protocolContract($("protocol-contract").value);if(!contract)throw Error("请先读取注册任务");const resources=[...$("protocol-source-materials").querySelectorAll("select")].map(field=>field.value);if(resources.some(id=>!id)||new Set(resources).size!==resources.length)throw Error("请选择不同的匹配材料");return protocolSubmit("source",{contract_id:contract.contract_id,goal:contract.public_goal,inputs:protocolInputs($("protocol-inputs")),resource_ids:resources});});
$("protocol-extract").onclick=safe(()=>{const run=protocolContext?.run;if(!run||protocolProjectionUnconfirmed(protocolContext)||run.phase!=="source"||run.status!=="SUCCEEDED"||run.semantic_status!=="PASS")throw Error("来源尚未通过独立注册核查");return protocolSubmit("extract",{source_run_id:run.run_id,expected_source_fingerprint:run.result_fingerprint});});
$("protocol-cold-form").onsubmit=safe(()=>{const ctx=protocolContext,contract=protocolContract($("protocol-cold-contract").value);if(!ctx?.plan||!contract)throw Error("请先读取协议草案与冷输入契约");const bindings=Object.fromEntries([...$("protocol-cold-materials").querySelectorAll("select")].map(field=>[field.dataset.binding,field.value]));if(Object.values(bindings).some(id=>!id)||new Set(Object.values(bindings)).size!==Object.values(bindings).length)throw Error("请选择不同的新材料");return protocolSubmit("cold",{contract_id:contract.contract_id,extraction_run_id:ctx.run.run_id,expected_plan_fingerprint:ctx.plan.plan_fingerprint,inputs:protocolInputs($("protocol-cold-inputs")),resource_bindings:bindings});});
$("protocol-read").onclick=safe(()=>{const ctx=protocolContext;if(ctx?.run)return readProtocolFreshRun(ctx);});$("protocol-recover").onclick=safe(()=>recoverProtocol());$("protocol-recover-retry").onclick=safe(()=>recoverProtocol(true));

// A completion command is separate from state-only /recover and never sends a model request.
// Page memory retains the exact command across Run/project selection; nothing stores a bearer on disk.
const protocolCompletionIntents=new Map();
function protocolCompletionKey(ctx,rid){return JSON.stringify([ctx.token,ctx.project,rid]);}
function clearProtocolCompletion(){
  clearProtocolReview();
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
  ctx.completionSignature=null;ctx.reviewSignature=null;
  if($("projects").hidden){
    if(ctx.run)ctx.run={...ctx.run,result:null,result_fingerprint:null};
    ctx.plan=null;ctx.renderedPlan=null;
    $("protocol-result").textContent="";$("protocol-extract").hidden=true;$("protocol-cold-form").hidden=true;
    $("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();
  }else if(ctx.run){renderProtocolCompletion(ctx);renderProtocolReview(ctx);}
}
function protocolCompletionEligible(run){
  return run?.namespace==="protocol_jobs.v1"&&["extract","source"].includes(run.phase)&&run.result===null&&
    ["RUNNING","WAITING_RESOURCE","RECONCILING"].includes(run.status)&&
    run.error?.code!=="OUTCOME_UNKNOWN"&&Number.isSafeInteger(run.version)&&run.version>=1&&
    Number.isSafeInteger(run.fence)&&run.fence>=0&&Number.isSafeInteger(run.version+1)&&Number.isSafeInteger(run.fence+1);
}
function protocolCompletionReceipt(value,rid,body,phase="extract"){
  if(!["source","extract"].includes(phase))return false;
  const source=phase==="source",field=source?"result_fingerprint":"plan_fingerprint";
  const keys=["namespace","run_id","status","version","fence",field,"provider_requests","automatic_resend","cached"];
  return value!==null&&typeof value==="object"&&!Array.isArray(value)&&
    Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key))&&
    value.namespace===(source?"protocol-source-completion.v2":"protocol-extract-completion.v2")&&value.run_id===rid&&value.status===(source?"WAITING_APPROVAL":"SUCCEEDED")&&
    Number.isSafeInteger(value.version)&&value.version===body.expected_version+1&&
    Number.isSafeInteger(value.fence)&&value.fence===body.expected_fence+1&&
    typeof value[field]==="string"&&/^[a-f0-9]{64}$/.test(value[field])&&
    value.provider_requests===0&&value.automatic_resend===false&&typeof value.cached==="boolean";
}
function protocolCompletionReadMatches(run,entry){
  const receipt=entry.receipt;
  if(!receipt||run?.namespace!=="protocol_jobs.v1"||run.run_id!==entry.rid||run.fence!==receipt.fence)return false;
  if(entry.phase==="source")return run.phase==="source"&&run.result_fingerprint===receipt.result_fingerprint&&
    ((run.status==="WAITING_APPROVAL"&&run.version===receipt.version&&run.semantic_status==="UNKNOWN")||
     (run.status==="SUCCEEDED"&&run.version===receipt.version+1&&run.semantic_status==="PASS"&&run.semantic_review==="APPROVED"));
  return run.phase==="extract"&&run.status==="SUCCEEDED"&&run.version===receipt.version&&
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
    if(ctx.completionProjectionInvalid===entry.rid)ctx.completionProjectionInvalid=null;
    entry.state="accepted";entry.message=entry.phase==="source"?"已结算原来源任务；没有新增模型请求。技术完成后仍须独立审核；当前状态按原成果显示。":"已完成原提取；没有新增模型请求。语义验收和发布状态仍按原成果显示。";
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
    entry={rid:run.run_id,phase:run.phase,body:Object.freeze({expected_version:run.version,expected_fence:run.fence,request_key:crypto.randomUUID()}),state:"new",uncertain:false};
    protocolCompletionIntents.set(key,entry);
  }
  const intent=ctx.intent,workspace=workspaceSelectionGeneration,current=()=>protocolCurrent(ctx)&&ctx.intent===intent&&workspace===workspaceSelectionGeneration&&!$("projects").hidden&&activeRun===entry.rid&&ctx.run?.run_id===entry.rid;
  ctx.busy=true;$("protocol-completion-confirm").checked=false;
  try{
    if(entry.state==="accepted-read-error"){
      renderProtocolCompletion(ctx);await readProtocolCompletion(ctx,entry,current);return;
    }
    entry.state="sending";entry.message="正在核对并尝试结算原任务；没有发起模型请求。";renderProtocolCompletion(ctx);
    try{
      const endpoint=entry.phase==="source"?"complete-source":"complete-extraction";
      const receipt=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${entry.rid}/${endpoint}`,"POST",entry.body);
      if(!protocolCompletionReceipt(receipt,entry.rid,entry.body,entry.phase))throw Error("完成回执未通过核对");
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

// Owner may request the existing registered synthetic checker, never choose a verdict.
// Pending commands stay in page memory; accepted reviews can be located by an authenticated read.
const protocolReviewIntents=new Map();
const protocolReviewReads=new WeakMap();
function clearProtocolReview(){
  clearProtocolCompletionReadback();
  $("protocol-review").hidden=true;
  $("protocol-review-confirm").checked=false;
  $("protocol-review-submit").disabled=true;
  $("protocol-review-retry").hidden=true;
  $("protocol-review-status").textContent="";
  $("protocol-review-locate-status").textContent="";
  $("protocol-review-locate-receipt").textContent="";
}
function protocolReviewEligible(run){
  return run?.namespace==="protocol_jobs.v1"&&["source","cold"].includes(run.phase)&&
    run.status==="WAITING_APPROVAL"&&run.semantic_status==="UNKNOWN"&&run.semantic_review==="WAITING_APPROVAL"&&
    run.owner_semantic_acceptance==="PENDING"&&run.formal_publication_enabled===false&&
    !run.error&&run.result!==null&&typeof run.result==="object"&&
    typeof run.contract_id==="string"&&new RegExp(`^protocol\\.synthetic\\.[ab]-${run.phase}\\.v1$`).test(run.contract_id)&&
    typeof run.result_fingerprint==="string"&&/^[a-f0-9]{64}$/.test(run.result_fingerprint)&&
    Number.isSafeInteger(run.version)&&run.version>=1&&Number.isSafeInteger(run.version+1)&&
    Number.isSafeInteger(run.fence)&&run.fence>=1;
}
function protocolReviewReceipt(value,entry){
  const keys=["id","run_id","contract_id","namespace","decision","reason","fingerprint","publishable","model_requests"];
  return value!==null&&typeof value==="object"&&!Array.isArray(value)&&
    Object.keys(value).length===keys.length&&keys.every(key=>Object.hasOwn(value,key))&&
    typeof value.id==="string"&&/^review_[a-f0-9]{32}$/.test(value.id)&&
    value.run_id===entry.rid&&value.contract_id===entry.body.contract_id&&value.namespace==="protocol-review.v1"&&
    ["PASS","FAIL","UNKNOWN"].includes(value.decision)&&typeof value.reason==="string"&&
    typeof value.fingerprint==="string"&&/^[a-f0-9]{64}$/.test(value.fingerprint)&&
    value.publishable===false&&value.model_requests===0;
}
function protocolReviewReadMatches(run,entry){
  const body=entry.body,receipt=entry.receipt;
  return !!receipt&&run?.namespace==="protocol_jobs.v1"&&run.run_id===entry.rid&&run.phase===entry.phase&&
    run.contract_id===body.contract_id&&run.result_fingerprint===body.expected_result_fingerprint&&
    run.fence===body.expected_fence&&!run.error&&run.result!==null&&typeof run.result==="object"&&
    run.owner_semantic_acceptance==="PENDING"&&run.formal_publication_enabled===false&&
    (receipt.decision==="PASS"?
      run.status==="SUCCEEDED"&&run.version===body.expected_version+1&&run.semantic_status==="PASS"&&run.semantic_review==="APPROVED":
      run.status==="WAITING_APPROVAL"&&run.version===body.expected_version&&run.semantic_status==="UNKNOWN"&&run.semantic_review==="WAITING_APPROVAL");
}
function renderProtocolReview(ctx){
  if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden){clearProtocolReview();return;}
  const run=ctx.run,entry=protocolReviewIntents.get(protocolCompletionKey(ctx,run.run_id));
  const eligible=!protocolCompletionProjectionUnconfirmed(ctx)&&protocolReviewEligible(run),pending=["sending","unknown","accepted-read-error"].includes(entry?.state);
  // Keep a completed evaluation visible without offering another key for the same result.
  $("protocol-review").hidden=!eligible&&!pending&&entry?.state!=="accepted";
  const signature=JSON.stringify([ctx.intent,workspaceSelectionGeneration,run.run_id,run.contract_id,run.result_fingerprint,run.version,run.fence]);
  if(ctx.reviewSignature!==signature){ctx.reviewSignature=signature;$("protocol-review-confirm").checked=false;}
  const blocked=ctx.busy||pending||entry?.state==="accepted"||ctx.reviewLocateClosed===run.run_id||protocolCompletionProjectionUnconfirmed(ctx);
  $("protocol-review-confirm").disabled=!eligible||blocked;
  $("protocol-review-submit").hidden=!eligible||pending||entry?.state==="accepted";
  $("protocol-review-submit").disabled=!eligible||blocked||!$("protocol-review-confirm").checked;
  $("protocol-review-retry").hidden=!["unknown","accepted-read-error"].includes(entry?.state);
  $("protocol-review-retry").disabled=ctx.busy||ctx.reviewLocateClosed===run.run_id||protocolCompletionProjectionUnconfirmed(ctx);
  $("protocol-review-retry").textContent=entry?.state==="accepted-read-error"?"重新读取核查状态（不再提交）":"用原核查键核对";
  $("protocol-review-locate").disabled=ctx.busy||!["source","cold"].includes(run.phase);
  $("protocol-review-locate-status").textContent=ctx.reviewLocateRun===run.run_id?ctx.reviewLocateMessage:
    "可只读找回当前任务的已接受核查；无记录不证明未提交，不恢复未持久化的 UNKNOWN。";
  $("protocol-review-locate-receipt").textContent=entry?.state==="accepted"&&!protocolCompletionProjectionUnconfirmed(ctx)&&protocolReviewReadMatches(run,entry)?
    JSON.stringify({request:entry.body,receipt:entry.receipt},null,2):"";
  $("protocol-review-status").textContent=protocolCompletionProjectionUnconfirmed(ctx)?"当前成果不可确认；只读重新核对完成回执，不继续核查。":entry?.message||`冻结契约 ${run.contract_id}；核查不会代替真实任务签收。冷页可只读找回已接受核查；未持久化的未知请求不能据此恢复。`;
}
async function readProtocolReview(ctx,entry,current){
  const selection=++ctx.selection,readGeneration=entry.readGeneration=(entry.readGeneration||0)+1;
  protocolReviewReads.set(entry,{ctx,selection,current});
  try{
    const run=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${entry.rid}`);
    if(!protocolReviewReadMatches(run,entry))throw Error("原成果与核查回执不匹配");
    if(entry.readGeneration!==readGeneration||!current()||selection!==ctx.selection)return;
    entry.state="accepted";entry.message=`注册合成核查 ${entry.receipt.decision}；原成果已复读确认。owner 真实任务签收仍 PENDING，未发布。`;
    ctx.reviewProjectionInvalid=null;ctx.run=run;renderProtocolRun(ctx);
  }catch(error){
    if(entry.readGeneration!==readGeneration)return;
    entry.state="accepted-read-error";entry.message="核查回执已记录，原成果读取未通过；只能重读状态，不再提交核查。";
    if(current()){
      invalidateProtocolReviewProjection(ctx);
      renderProtocolReview(ctx);
    }
  }
}
async function requestProtocolReview(retry=false){
  const ctx=protocolContext,run=ctx?.run;
  if(!ctx||!run||!protocolCurrent(ctx)||$("projects").hidden||activeRun!==run.run_id||ctx.busy||ctx.reviewLocateClosed===run.run_id||protocolCompletionProjectionUnconfirmed(ctx))return;
  const key=protocolCompletionKey(ctx,run.run_id);
  let entry=protocolReviewIntents.get(key);
  if(retry){
    if(!entry||!["unknown","accepted-read-error"].includes(entry.state))return;
  }else{
    if(!protocolReviewEligible(run)||!$("protocol-review-confirm").checked||
       (ctx.reviewLocateClosed===run.run_id||["sending","unknown","accepted-read-error","accepted"].includes(entry?.state)))return;
    entry={rid:run.run_id,phase:run.phase,body:Object.freeze({contract_id:run.contract_id,
      expected_result_fingerprint:run.result_fingerprint,expected_version:run.version,
      expected_fence:run.fence,request_key:crypto.randomUUID()}),state:"new",uncertain:false};
    protocolReviewIntents.set(key,entry);
  }
  const intent=ctx.intent,workspace=workspaceSelectionGeneration,current=()=>protocolCurrent(ctx)&&ctx.intent===intent&&
    workspace===workspaceSelectionGeneration&&!$("projects").hidden&&activeRun===entry.rid&&ctx.run?.run_id===entry.rid;
  ctx.busy=true;$("protocol-review-confirm").checked=false;$("protocol-recover").disabled=true;
  try{
    if(entry.state==="accepted-read-error"){
      renderProtocolReview(ctx);await readProtocolReview(ctx,entry,current);return;
    }
    entry.state="sending";entry.message="正在请求原契约的注册合成核查；没有发起模型请求。";renderProtocolReview(ctx);
    try{
      const receipt=await protocolRequest(ctx,`/api/internal/protocol/runs/${entry.rid}/reviews`,"POST",entry.body);
      if(!protocolReviewReceipt(receipt,entry))throw Error("核查回执未通过核对");
      entry.receipt=receipt;entry.state="accepted-read-error";entry.message="核查回执已记录，正在复读原成果。";
    }catch(error){
      const rejected=!entry.uncertain&&Number.isInteger(error.httpStatus)&&error.httpStatus>=400&&error.httpStatus<500&&![408,425,429].includes(error.httpStatus);
      entry.state=rejected?"rejected":"unknown";if(!rejected)entry.uncertain=true;
      entry.message=rejected?`服务端拒绝核查：${error.message}。请先读取当前状态。`:
        "核查回执 UNKNOWN；只可显式使用原核查键核对，不自动重发、不另选契约或补传判定。";
      return;
    }
    if(current())await readProtocolReview(ctx,entry,current);
  }finally{
    ctx.busy=false;
    if(current()){renderProtocolReview(ctx);$("protocol-recover").disabled=false;}
  }
}
$("protocol-review-confirm").onchange=()=>{if(protocolContext)renderProtocolReview(protocolContext);};
$("protocol-review-submit").onclick=safe(()=>requestProtocolReview());
$("protocol-review-retry").onclick=safe(()=>requestProtocolReview(true));

function acceptProtocolReviewBackgroundRead(ctx,run,selection){
  const entry=protocolReviewIntents.get(protocolCompletionKey(ctx,run.run_id));
  const witness=entry&&protocolReviewReads.get(entry);
  if(entry?.state!=="accepted-read-error"||!witness||witness.ctx!==ctx||
     selection<=witness.selection||!witness.current()||!protocolReviewReadMatches(run,entry))return;
  // This authenticated read began after receipt registration and the explicit
  // read. An older response cannot downgrade this newer matching view.
  entry.readGeneration=(entry.readGeneration||0)+1;
  entry.state="accepted";entry.message=`注册合成核查 ${entry.receipt.decision}；原成果已复读确认。owner 真实任务签收仍 PENDING，未发布。`;
  ctx.reviewProjectionInvalid=null;
}
function protocolReviewProjectionUnconfirmed(ctx){
  return !!ctx?.run&&ctx.reviewProjectionInvalid===ctx.run.run_id&&ctx.run.result===null;
}
function invalidateProtocolReviewProjection(ctx){
  const entry=protocolReviewIntents.get(protocolCompletionKey(ctx,ctx.run.run_id));
  if(entry){
    if(entry.receipt)entry.state="accepted-read-error";
    entry.message="当前核查状态不可确认；原请求键保持不变，仅可只读重核，不可继续。";
  }
  ctx.reviewProjectionInvalid=ctx.run.run_id;
  ctx.run={...ctx.run,result:null,result_fingerprint:null};ctx.plan=null;ctx.renderedPlan=null;
  protocolStatus(ctx,"当前协议状态不可确认；原成果与核查投影已关闭，请只读重新核对。");
  $("protocol-result").textContent="";$("protocol-extract").hidden=true;$("protocol-cold-form").hidden=true;
  $("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();
}
function protocolReviewLocated(value,run){
  const keys=["namespace","run_id","phase","state","request","receipt"];
  if(!value||typeof value!=="object"||Array.isArray(value)||Object.keys(value).length!==keys.length||
     !keys.every(key=>Object.hasOwn(value,key))||value.namespace!=="protocol-review-readback.v1"||
     value.run_id!==run.run_id||value.phase!==run.phase||!["source","cold"].includes(value.phase))return null;
  if(value.state==="NOT_FOUND")return value.request===null&&value.receipt===null?{missing:true}:null;
  const body=value.request,fields=["contract_id","expected_result_fingerprint","expected_version","expected_fence","request_key"];
  if(value.state!=="FOUND"||!body||typeof body!=="object"||Array.isArray(body)||
     Object.keys(body).length!==fields.length||!fields.every(key=>Object.hasOwn(body,key))||
     body.contract_id!==run.contract_id||typeof body.expected_result_fingerprint!=="string"||
     !/^[a-f0-9]{64}$/.test(body.expected_result_fingerprint)||
     !Number.isSafeInteger(body.expected_version)||body.expected_version<1||!Number.isSafeInteger(body.expected_version+1)||
     !Number.isSafeInteger(body.expected_fence)||body.expected_fence<1||
     typeof body.request_key!=="string"||![...body.request_key].length||[...body.request_key].length>100)return null;
  const entry={rid:value.run_id,phase:value.phase,body:Object.freeze({...body}),receipt:value.receipt,state:"accepted-read-error"};
  return protocolReviewReceipt(value.receipt,entry)?entry:null;
}
async function locateProtocolReview(){
  const ctx=protocolContext,run=ctx?.run;
  if(!ctx||!run||!protocolCurrent(ctx)||$("projects").hidden||activeRun!==run.run_id||ctx.busy||
     !["source","cold"].includes(run.phase))return;
  const intent=ctx.intent,workspace=workspaceSelectionGeneration;++ctx.selection;
  const current=()=>protocolCurrent(ctx)&&ctx.intent===intent&&
    workspace===workspaceSelectionGeneration&&!$("projects").hidden&&activeRun===run.run_id&&ctx.run?.run_id===run.run_id;
  ctx.busy=true;ctx.reviewLocateRun=run.run_id;ctx.reviewLocateClosed=run.run_id;
  ctx.reviewLocateMessage="正在只读定位已接受核查；不会提交命令。";renderProtocolReview(ctx);
  try{
    const value=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${run.run_id}/review-receipt`);
    if(!current())return;
    const entry=protocolReviewLocated(value,run);
    if(!entry)throw Error("已接受核查回执未通过核对");
    if(entry.missing){
      throw Error("未找到持久接受回执；不代表未提交，本只读恢复保持关闭");
    }
    const key=protocolCompletionKey(ctx,run.run_id),old=protocolReviewIntents.get(key);
    if(old&&!Object.keys(entry.body).every(name=>old.body[name]===entry.body[name]))throw Error("持久回执与页内原请求不匹配");
    entry.message="已定位原核查键，正在重新读取原成果。";
    protocolReviewIntents.set(key,entry);ctx.reviewLocateClosed=null;
    // readProtocolReview advances selection itself; the immutable context witness
    // below deliberately excludes the preceding discovery read's selection.
    const sameContext=()=>protocolCurrent(ctx)&&ctx.intent===intent&&workspace===workspaceSelectionGeneration&&
      !$("projects").hidden&&activeRun===run.run_id&&ctx.run?.run_id===run.run_id;
    await readProtocolReview(ctx,entry,sameContext);
    if(sameContext())ctx.reviewLocateMessage=entry.state==="accepted"?
      "原核查请求与回执已只读找回；后续仅重读，不再提交。":"已定位原回执，成果读取未通过；只能重读，不解锁。";
  }catch(error){
    if(current()){
      ctx.reviewLocateMessage=`只读找回未通过：${error.message}。不推断未提交，不生成新键。`;
      invalidateProtocolReviewProjection(ctx);
    }
  }finally{
    ctx.busy=false;
    if(protocolCurrent(ctx)&&ctx.intent===intent&&workspace===workspaceSelectionGeneration&&
       !$("projects").hidden&&activeRun===run.run_id&&ctx.run?.run_id===run.run_id)renderProtocolReview(ctx);
  }
}
$("protocol-review-locate").onclick=safe(locateProtocolReview);

// Persisted completion readback is separate from completion commands and reviews.
const protocolCompletionReadbacks=new Map(),protocolCompletionReadbackReads=new WeakMap();
function clearProtocolCompletionReadback(){
  $("protocol-completion-locate").disabled=true;
  $("protocol-completion-locate-status").textContent="";
  $("protocol-completion-locate-receipt").textContent="";
}
function protocolCompletionProjectionUnconfirmed(ctx){
  return !!ctx?.run&&ctx.completionProjectionInvalid===ctx.run.run_id;
}
function protocolProjectionUnconfirmed(ctx){
  return protocolReviewProjectionUnconfirmed(ctx)||protocolCompletionProjectionUnconfirmed(ctx);
}
function protocolCompletionLocatedMatches(run,entry){
  return protocolCompletionReadMatches(run,entry)&&!run.error&&run.result!==null&&typeof run.result==="object"&&
    run.owner_semantic_acceptance==="PENDING"&&run.formal_publication_enabled===false;
}
function renderProtocolCompletionReadback(ctx){
  if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden){clearProtocolCompletionReadback();return;}
  const run=ctx.run,entry=protocolCompletionReadbacks.get(protocolCompletionKey(ctx,run.run_id));
  $("protocol-completion-locate").disabled=ctx.busy||!["source","extract"].includes(run.phase);
  $("protocol-completion-locate-status").textContent=protocolCompletionProjectionUnconfirmed(ctx)?
    "当前完成状态不可确认；仅可只读重核，不生成新键、不再次提交。":
    entry?.message||ctx.completionReadbackNotice||"仅找回已持久完成命令的原键与回执；无记录不证明未执行，不恢复未持久 UNKNOWN。";
  $("protocol-completion-locate-receipt").textContent=entry?.state==="accepted"&&!protocolProjectionUnconfirmed(ctx)&&protocolCompletionLocatedMatches(run,entry)?
    JSON.stringify({request:entry.body,receipt:entry.receipt},null,2):"";
}
function invalidateProtocolCompletionReadback(ctx,entry){
  if(entry){entry.state="read-error";entry.message="当前完成状态不可确认；原历史键与回执保留，仅可只读重核。";}
  ctx.completionProjectionInvalid=ctx.run.run_id;
  ctx.completionReadbackNotice="历史完成回执不可确认；没有找到不等于未执行，不生成新键。";
  ctx.run={...ctx.run,result:null,result_fingerprint:null};ctx.plan=null;ctx.renderedPlan=null;
  $("protocol-result").textContent="";$("protocol-extract").hidden=true;$("protocol-cold-form").hidden=true;
  $("protocol-cold-inputs").replaceChildren();$("protocol-cold-materials").replaceChildren();
  protocolStatus(ctx,"当前完成状态不可确认；原成果投影已关闭，请只读重新核对。");
}
async function readProtocolFreshRun(ctx){
  if(!protocolCurrent(ctx)||!ctx.run||$("projects").hidden||activeRun!==ctx.run.run_id)return;
  const rid=ctx.run.run_id,workspace=workspaceSelectionGeneration,intent=ctx.intent=(ctx.intent||0)+1;
  const selection=ctx.selection+1;
  // Explicit fresh inspection restores the original Run view, not a missing
  // optional completion command. Automatic polling never clears this closure.
  await showProtocolRun(rid,ctx);
  if(!protocolCurrent(ctx)||ctx.intent!==intent||ctx.selection!==selection||workspace!==workspaceSelectionGeneration||
    $("projects").hidden||activeRun!==rid||ctx.run?.run_id!==rid)return;
  ctx.completionProjectionInvalid=null;
  const entry=protocolCompletionReadbacks.get(protocolCompletionKey(ctx,rid));
  if(entry&&entry.state!=="accepted"){
    entry.readGeneration=(entry.readGeneration||0)+1;protocolCompletionReadbackReads.delete(entry);
    entry.state="read-error";entry.message="当前Run已新鲜复读；历史完成回执仍不可确认，仅可另行只读找回。";
  }
  ctx.completionReadbackNotice="当前Run已新鲜复读；未找到的历史完成回执不会因此补造。";
  renderProtocolRun(ctx);
}
function protocolCompletionLocated(value,run){
  const keys=["namespace","run_id","phase","state","request","receipt"];
  if(!value||typeof value!=="object"||Array.isArray(value)||Object.keys(value).length!==keys.length||
    !keys.every(k=>Object.hasOwn(value,k))||value.namespace!=="protocol-completion-readback.v1"||
    value.run_id!==run.run_id||value.phase!==run.phase||!["source","extract"].includes(value.phase))return null;
  if(value.state==="NOT_FOUND")return value.request===null&&value.receipt===null?{missing:true}:null;
  const body=value.request,fields=["expected_version","expected_fence","request_key"];
  if(value.state!=="FOUND"||!body||typeof body!=="object"||Array.isArray(body)||Object.keys(body).length!==3||
    !fields.every(k=>Object.hasOwn(body,k))||!Number.isSafeInteger(body.expected_version)||body.expected_version<1||
    !Number.isSafeInteger(body.expected_version+1)||!Number.isSafeInteger(body.expected_fence)||body.expected_fence<0||
    !Number.isSafeInteger(body.expected_fence+1)||typeof body.request_key!=="string"||!/^[A-Za-z0-9_-]{1,100}$/.test(body.request_key)||
    !protocolCompletionReceipt(value.receipt,run.run_id,body,run.phase)||value.receipt.cached!==false)return null;
  return {rid:run.run_id,phase:run.phase,body:Object.freeze({...body}),receipt:value.receipt,state:"reading"};
}
function acceptProtocolCompletionReadback(ctx,entry,run){
  entry.readGeneration=(entry.readGeneration||0)+1;entry.state="accepted";
  entry.message="原完成回执已找回、当前成果已复读；仅只读恢复，不代替独立核查或 owner 签收，未发布。";
  ctx.completionProjectionInvalid=null;ctx.run=run;
}
function acceptProtocolCompletionReadbackBackground(ctx,run,selection){
  const entry=protocolCompletionReadbacks.get(protocolCompletionKey(ctx,run.run_id)),witness=entry&&protocolCompletionReadbackReads.get(entry);
  if(!["reading","read-error"].includes(entry?.state)||!witness||witness.ctx!==ctx||selection<=witness.selection||
    !witness.current()||!protocolCompletionLocatedMatches(run,entry))return;
  acceptProtocolCompletionReadback(ctx,entry,run);
}
async function readProtocolCompletionReadback(ctx,entry,current){
  const selection=++ctx.selection,generation=entry.readGeneration=(entry.readGeneration||0)+1;
  protocolCompletionReadbackReads.set(entry,{ctx,selection,current});
  try{
    const run=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${entry.rid}`);
    if(!protocolCompletionLocatedMatches(run,entry))throw Error("当前成果与原完成回执不匹配");
    if(entry.readGeneration!==generation||!current()||selection!==ctx.selection)return;
    acceptProtocolCompletionReadback(ctx,entry,run);renderProtocolRun(ctx);
  }catch(error){
    if(entry.readGeneration!==generation||!current())return;
    invalidateProtocolCompletionReadback(ctx,entry);renderProtocolRun(ctx);
  }
}
async function locateProtocolCompletion(){
  const ctx=protocolContext,run=ctx?.run;
  if(!ctx||!run||!protocolCurrent(ctx)||$("projects").hidden||activeRun!==run.run_id||ctx.busy||
    !["source","extract"].includes(run.phase))return;
  const intent=ctx.intent,workspace=workspaceSelectionGeneration;
  const current=()=>protocolCurrent(ctx)&&ctx.intent===intent&&workspace===workspaceSelectionGeneration&&
    !$("projects").hidden&&activeRun===run.run_id&&ctx.run?.run_id===run.run_id;
  const key=protocolCompletionKey(ctx,run.run_id);
  ctx.busy=true;++ctx.selection;renderProtocolCompletionReadback(ctx);
  try{
    const value=await protocolRequest(ctx,`/api/projects/${ctx.project}/protocol/runs/${run.run_id}/completion-receipt`);
    if(!current())return;
    const entry=protocolCompletionLocated(value,run);
    if(!entry||entry.missing)throw Error("没有可认证的持久完成回执；不能推断未执行");
    for(const old of [protocolCompletionIntents.get(key),protocolCompletionReadbacks.get(key)]){
      if(old&&!Object.keys(entry.body).every(k=>old.body[k]===entry.body[k]))throw Error("原完成键或参数不一致");
    }
    protocolCompletionReadbacks.set(key,entry);
    await readProtocolCompletionReadback(ctx,entry,current);
  }catch(error){
    if(current()){
      const old=protocolCompletionReadbacks.get(key);
      if(old){old.readGeneration=(old.readGeneration||0)+1;protocolCompletionReadbackReads.delete(old);}
      invalidateProtocolCompletionReadback(ctx,old);renderProtocolRun(ctx);
    }
  }finally{
    ctx.busy=false;if(current())renderProtocolCompletionReadback(ctx);
  }
}
$("protocol-completion-locate").onclick=safe(locateProtocolCompletion);

// Progressive read-only presentation. Original controllers remain the sole
// authority for selection, disclosure of results, commands and invalidation.
// If this browser cannot observe DOM changes, the original complete view stays.
(function installProtocolReadingView(){
 if(typeof MutationObserver!=="function"||typeof document.createElement!=="function")return;
 const detail=$("protocol-detail"),raw=$("protocol-result"),status=$("protocol-state");
 const state=document.createElement("section"),summary=document.createElement("section");
 state.id="protocol-state-view";state.setAttribute("aria-live","polite");
 summary.id="protocol-reading-view";summary.setAttribute("aria-label","当前成果摘要（未替代独立核查）");
 detail.insertBefore(state,status);detail.insertBefore(summary,$("protocol-evidence"));
 const text=(tag,value,cls)=>{const e=document.createElement(tag);e.textContent=value;if(cls)e.className=cls;return e;};
 const scalar=value=>typeof value==="string"?value:JSON.stringify(value);
 const object=value=>value!==null&&typeof value==="object"&&!Array.isArray(value);
 let shownContext=null,shownValue=null;
 const clear=()=>{shownContext=null;shownValue=null;state.replaceChildren();summary.replaceChildren();state.hidden=true;summary.hidden=true;delete status.dataset.presented;delete status.dataset.readState;};
 function render(){
  const ctx=protocolContext,run=ctx?.run;
  if(!ctx||!run||!protocolCurrent(ctx)||detail.hidden||$("projects").hidden||activeRun!==run.run_id){clear();return;}
  if(protocolProjectionUnconfirmed(ctx)){
   clear();
   state.append(text("h3","当前成果不可确认","reading-error-title"));state.hidden=false;
   status.dataset.readState="error";return; // Original error and read action stay visible.
  }
  const expected=`${run.phase} · ${run.status} · 语义 ${run.semantic_status} · ${run.semantic_review} · owner ${run.owner_semantic_acceptance||"PENDING"}。注册核查不等于 owner 对真实任务签收；未发布。`;
  if(status.textContent!==expected||raw.textContent!==JSON.stringify(run.result||run.error||{},null,2)){clear();return;}
  // Every current/invalidated/full-text witness above is still evaluated on
  // each refresh. Retain only identical presentation DOM, not a validation PASS.
  // This preserves open disclosures and selections through unchanged polling.
  const value=JSON.stringify(run);
  if(shownContext===ctx&&shownValue===value)return;
  clear();shownContext=ctx;shownValue=value;
  const phase={source:"来源成果",extract:"协议草案",cold:"新材料运行"}[run.phase]||run.phase;
  const technical={WAITING_APPROVAL:"等待独立核查",SUCCEEDED:"技术执行成功",RUNNING:"正在执行",QUEUED:"等待执行",FAILED:"执行失败",UNKNOWN:"执行状态未知",PARTIAL:"仅部分完成"}[run.status]||run.status;
  state.append(text("h3",`${phase}：${technical}`));
  const fields=document.createElement("dl");fields.className="state-facts";
  for(const [label,value] of [["语义状态",run.semantic_status||"UNKNOWN"],["独立核查",run.semantic_review==="WAITING_APPROVAL"?"等待核查":run.semantic_review||"UNKNOWN"],["人工验收",run.owner_semantic_acceptance||"PENDING"],["发布状态",run.formal_publication_enabled===false?"未发布":"未确认"]]){
   const pair=document.createElement("div");
   // Presentation only: retain each original value and never derive approval
   // or publication from a successful technical run.
   pair.dataset.tone = value==="UNKNOWN"||value==="未确认" ? "uncertain" : value==="PENDING"||value==="等待核查" ? "waiting" : "neutral";
   pair.append(text("dt",label),text("dd",value));fields.append(pair);
  }
  state.append(fields);
  const identifiers=document.createElement("details");identifiers.className="reading-identifiers";
  identifiers.append(text("summary","完整状态与标识"),text("pre",`${run.run_id}\n${expected}`),text("p","注册核查不替代人工签收；技术执行成功也不代表目标语义通过。","reading-boundary"));state.append(identifiers);
  state.hidden=false;status.dataset.presented="true";
  const payload=run.result?.protocol_result;
  if(run.phase!=="source"||!object(payload)||payload.kind!=="model-protocol.v1"||!object(payload.evidence?.output))return;
  const output=payload.evidence.output;
  summary.append(text("h3","已记录的来源结论"));
  if(typeof output.case?.required_next_step==="string")summary.append(text("p",output.case.required_next_step,"reading-next-step"));
  summary.append(text("p","以下仅整理原成果的可读展示，语义与人工验收状态以上方为准。","reading-boundary"));
  if(object(output.case)){
   const facts=document.createElement("dl");facts.className="reading-case";
   for(const key of ["decision","may_submit_now","blocking_rule"]){if(Object.hasOwn(output.case,key)){facts.append(text("dt",{decision:"原记录判断",may_submit_now:"当前是否可提交",blocking_rule:"阻断规则"}[key]),text("dd",scalar(output.case[key])));}}
   summary.append(facts);
  }
  if(Object.hasOwn(output,"absolute_deadline"))summary.append(text("p",`绝对截止时间：${scalar(output.absolute_deadline)}`,output.absolute_deadline==="UNKNOWN"?"reading-unknown":"reading-fact"));
  if(object(output.obligations)){
   const list=document.createElement("ol");list.className="reading-obligations";
   // This is explicitly a summary; full fields and original aliases remain in
   // the unchanged JSON disclosure. No missing facts are filled or inferred.
   for(const [key,item] of Object.entries(output.obligations).slice(0,12)){
    if(!object(item)||typeof item.action!=="string")continue;
    const li=document.createElement("li");li.append(text("strong",item.action));
    if(typeof item.actor==="string")li.append(text("p",`适用对象：${item.actor}`));
    if(Object.hasOwn(item,"condition")){
     const c=item.condition,known=object(c)&&["field","operator","value"].every(k=>Object.hasOwn(c,k))&&Object.keys(c).every(k=>["field","operator","value","unit"].includes(k));
     li.append(text("p",`条件：${known?`${scalar(c.field)} ${scalar(c.operator)} ${scalar(c.value)}${Object.hasOwn(c,"unit")?` ${scalar(c.unit)}`:""}`:scalar(c)}`));
    }
    if(object(item.deadline))for(const [key,value] of Object.entries(item.deadline))li.append(text("p",`${{amount:"期限数量",unit:"期限单位",start_event:"起算事件",absolute_date:"绝对日期"}[key]||key}：${scalar(value)}`,value==="UNKNOWN"?"reading-unknown":""));
    if(Array.isArray(item.lines))li.append(text("small",`原文行号：${item.lines.map(scalar).join("、")}`));
    li.append(text("small",`记录标识：${key}`));list.append(li);
   }
   if(list.children.length)summary.append(list);
   if(Object.keys(output.obligations).length>12)summary.append(text("p","摘要仅列前12项；全部记录请展开下方完整成果。"));
  }
  summary.hidden=false;
 }
 const observer=new MutationObserver(render);
 for(const node of [raw,status])observer.observe(node,{subtree:true,childList:true,characterData:true});
 for(const node of [detail,$("projects")])observer.observe(node,{attributes:true,attributeFilter:["hidden"]});
 render();
})();
