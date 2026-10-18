"use strict";
// Explicit same-instance revision, original durable CHECK/Release/CAS controllers.
const csvGoalRevisionIntents=new Map();
function clearCsvGoalRevision(v=null){if(v)v.csvGoalRevision=null;$("csv-goal-revision")?.remove();}
function resumeCsvGoalRevision(){const v=applicationUse;if(applicationUseCurrent(v)&&v.instance&&v.app?.candidate?.generation)safe(()=>readApplicationUse(v))();}
function renderCsvGoalRevision(v,release){
 const generation=v.app?.candidate?.generation;if(!generation)return;
 const signature=JSON.stringify([v.id,v.instance.release_id,v.instance.revision,v.instance.data_version]);
 if(v.csvGoalRevision?.signature===signature&&$("csv-goal-revision")?.isConnected){v.csvGoalRevision.controls();return;}
 clearCsvGoalRevision(v);
 const node=document.createElement("section");node.id="csv-goal-revision";
 const title=document.createElement("h3");title.textContent="修订此应用的 Goal 或列绑定";node.append(title);
 const owner=applicationUseKey(v);let entry=csvGoalRevisionIntents.get(owner);
 const currentRelease=release.snapshot.csv_goal_revision_source;
 const pendingAdoption=entry?.steps.adoptCommit&&["sending","unknown","accepted-read-error"].includes(entry.steps.adoptCommit.state);
 const unresolvedEntry=entry&&Object.values(entry.steps).some(p=>["sending","unknown","accepted-read-error"].includes(p.state));
 const continuing=entry?.cycleRelease===release.id&&!["adopted","abandoned"].includes(entry?.state);
 if(currentRelease&&!pendingAdoption&&!continuing&&!unresolvedEntry){
  node.append(row(`已采用 Goal v${currentRelease.goal.version}：${currentRelease.goal.snapshot.content.goal}。当前列 ${currentRelease.input.column}；每次新运行的人工声明独立，初始 PENDING。`));
  const startCycle=(mode)=>{
   if(!applicationUseCurrent(v)||!node.isConnected||v.busy||signature!==JSON.stringify([v.id,v.instance?.release_id,v.instance?.revision,v.instance?.data_version])||Object.values(entry?.steps||{}).some(p=>["sending","unknown","accepted-read-error"].includes(p.state)))return;
   const replacement={key:crypto.randomUUID(),baselineKey:crypto.randomUUID(),steps:{},state:"new",mode,cycleRelease:release.id,
    history:entry?(entry.state==="abandoned"?entry.history:[...(entry.history||[]),{key:entry.key,mode:entry.mode||"column",steps:entry.steps,release:entry.release?.id}]):[]};
   csvGoalRevisionIntents.set(owner,replacement);clearCsvGoalRevision(v);renderCsvGoalRevision(v,release);
  };
  node.append(csvFullReportButton("基于当前版本再次修订 Goal 或列","csv-goal-next",()=>startCycle("column")),
   csvFullReportButton("更换此实例的已授权 CSV 材料","csv-material-next",()=>startCycle("material")));
  $("use-info").after(node);return;
 }
 if(!entry){entry={key:crypto.randomUUID(),baselineKey:crypto.randomUUID(),steps:{},state:"new",cycleRelease:release.id};csvGoalRevisionIntents.set(owner,entry);}
 const materialMode=entry.mode==="material",materialVersion="csv-material-revision.v1";
 if(materialMode)title.textContent="更换此实例的已授权 CSV 材料";
 const c={signature,node,connection:identityConnectionGeneration,workspace:workspaceSelectionGeneration,busy:false,reviewReady:false,materials:[]};v.csvGoalRevision=c;
 const here=()=>applicationUseCurrent(v)&&v.csvGoalRevision===c&&node.isConnected&&c.connection===identityConnectionGeneration&&c.workspace===workspaceSelectionGeneration&&c.signature===JSON.stringify([v.id,v.instance?.release_id,v.instance?.revision,v.instance?.data_version])&&!$("apps").hidden;
 const path=`/api/internal/instances/${v.id}/csv-goal-revisions`;
 const materialPath=`/api/internal/instances/${v.id}/csv-material-revisions`;
 const contextPath=materialMode?materialPath:path;
 const status=document.createElement("p");status.id="csv-goal-revision-status";status.setAttribute("role","status");
 const proof=document.createElement("pre");proof.id="csv-goal-revision-proof";
 const from=document.createElement("select"),to=document.createElement("select");from.id="csv-goal-from";to.id="csv-goal-to";
 const material=document.createElement("select");material.id="csv-material-target";
 const materialInfo=document.createElement("p");materialInfo.id="csv-material-provenance";
 const ack=(id,label)=>{const input=document.createElement("input");input.type="checkbox";input.id=id;input.onchange=controls;return [input,csvFullReportLabel(label,input)];};
 const [checkAck,checkLabel]=ack("csv-goal-check-ack",materialMode?"已核对原 Goal 来源、当前与目标材料及哈希、保留列和影响范围，确认在独立实例实际重验":"已核对新 Goal、保留或修改的列及影响范围；计算不会自动解释目标，确认独立重验");
 const [releaseAck,releaseLabel]=ack("csv-goal-release-ack","已核对本次实际重验，确认保存新内部 Release");
 const [adoptAck,adoptLabel]=ack("csv-goal-adopt-ack","已核对原实例、目标 Release 和保留结果，明确采用此版本");
 const button=(id,label,fn)=>csvFullReportButton(label,id,fn);
 function deny(error){
  if(!here()||![403,409].includes(error.httpStatus))return false;
  // Keep exact accepted/unknown handles. A new view must reauthorize and reread
  // their bodies before displaying them or enabling any fresh confirmation.
  c.reviewReady=false;
  entry.message="当前来源、权限或版本已失效。保留原键；已证明未受理的请求可明确重新准备。";
  clearApplicationUseData(v);return true;
 }
 const unresolved=()=>Object.values(entry.steps).some(p=>["sending","unknown","accepted-read-error"].includes(p.state));
 const same=(a,b)=>goalRunCanonical(a)===goalRunCanonical(b);
 const changedGoal=ctx=>!!ctx&&ctx.goal.version===(ctx.parent?.goal.version??ctx.original_goal_version)+1&&!same(ctx.goal.snapshot.content,ctx.parent?.goal.snapshot.content||v.app.candidate.goal);
 const unexpired=a=>Number.isFinite(a?.expires_at)&&a.expires_at*1000>Date.now();
 const requireReview=(ok)=>{if(!ok)throw Error("冻结修订与当前归属、版本或原请求不匹配，请重新核查");};
 async function readContext(){
  const value=await api(contextPath+"/context");if(!here())return null;
  if(!materialMode)return value;
  const ctx=value?.context;
  requireReview(ctx?.revision_contract===materialVersion&&Array.isArray(value.materials)&&ctx.instance_id===v.id&&ctx.principal_id===v.principal&&ctx.project_id===v.project&&ctx.app_id===v.appId&&ctx.runtime_id===v.instance.runtime_id&&ctx.release_id===v.instance.release_id&&ctx.release_fingerprint===v.instance.release_fingerprint&&ctx.instance_revision===v.instance.revision&&ctx.data_version===v.instance.data_version);
  c.materials=value.materials;return value.context;
 }
 function selectedMaterial(){
  if(entry.preview)return entry.preview.material;
  return c.materials.find(x=>x.resource_id===entry.selection?.resource_id&&x.hash===entry.selection?.source_hash);
 }
 function drawReview(){
  const ctx=entry.ctx,selection=entry.preview?{from:entry.preview.baseline_input.column,to:entry.preview.input.column}:entry.selection;
  if(!ctx||(!c.reviewReady&&!c.staleCheckReady))return;
  from.replaceChildren(...ctx.columns.map(x=>new Option(x,x)));to.replaceChildren(...ctx.columns.map(x=>new Option(x,x)));
  if(selection){from.value=selection.from;to.value=selection.to;}
  if(materialMode){
   const chosen=selectedMaterial(),options=[new Option("请明确选择已授权的另一份 CSV","")];
   const available=entry.preview?[entry.preview.material]:c.materials;
   for(const item of available)options.push(new Option(`${item.name||item.resource_id} · ${item.resource_id} · SHA-256 ${item.hash}`,item.resource_id));
   material.replaceChildren(...options);material.value=chosen?.resource_id||"";
   materialInfo.textContent=`原 Goal 来源：${ctx.goal.snapshot.content.resource_refs.join("、")}；保留 Goal v${ctx.goal.version} 与列 ${ctx.parent.column}。当前材料：${ctx.source.resource_id}，SHA-256 ${ctx.source.hash}。${chosen?`目标材料：${chosen.resource_id}，SHA-256 ${chosen.hash}。`:"目标材料尚未选择。"}采用后由同一实例的新 Run 使用目标材料；旧 Goal 来源与历史保持原样。`;
  }
  proof.textContent=JSON.stringify({context:ctx,current_context:c.currentContext,review_status:c.staleCheckReady?"FROZEN_BASELINE_RESULTS_CHANGED":"CURRENT_FROZEN_REVIEW",preview:entry.preview,check:entry.check,release_approval:entry.approval,release:entry.release,adoption_approval:entry.adoption},null,2);
 }
 async function restoreReview(){
  c.reviewReady=c.staleCheckReady=false;checkAck.checked=releaseAck.checked=adoptAck.checked=false;
  proof.textContent="正在只读核对原修订的当前归属及冻结内容；尚未确认下一步。";controls();
  const ctx=await readContext();if(!here())return;
  requireReview(ctx.instance_id===v.id&&ctx.principal_id===v.principal&&ctx.app_id===v.appId&&ctx.project_id===v.project&&ctx.runtime_id===v.instance.runtime_id&&ctx.release_id===v.instance.release_id&&ctx.release_fingerprint===v.instance.release_fingerprint&&ctx.instance_revision===v.instance.revision&&ctx.data_version===v.instance.data_version);
  // A new result cannot roll back. Keep only the existing explicit CHECK
  // rejection path available, with its original frozen body/key, so its
  // server-proved NOT_ACCEPTED receipt can authorize fresh preparation.
  const stale=!!entry.preview&&!entry.steps.check&&ctx.data_version>entry.ctx.data_version&&same({...ctx,data_version:entry.ctx.data_version},entry.ctx);
  requireReview(same(ctx,entry.ctx)||stale);
  if(entry.preview){
   const saved=await api(path+`/previews/${entry.key}`);if(!here())return;
   requireReview(same(saved,entry.preview)&&same(saved.context,entry.ctx)&&saved.request_key===entry.key);
  }
  if(stale){c.currentContext=ctx;c.staleCheckReady=true;drawReview();entry.message="冻结基线之后已有新结果；本草案已失效。请核对原冻结内容，再明确提交原键 CHECK 由服务器判定；仅取得未受理证明后才能重新准备。Release 与采用仍禁用。";return;}
  if(entry.check){
   const saved=await api(path+`/checks/${entry.key}`);if(!here())return;
   requireReview(saved.request_key===entry.key&&saved.accepted_request_fingerprint===await ownerHash(entry.steps.check.body)&&saved.run_id===entry.check.run_id);
   if(!here())return;
   if(entry.proof)requireReview(saved.status==="PASS"&&saved.check_fingerprint===entry.proof.check_fingerprint);
  }
  if(entry.approval){
   const saved=await api(path+`/version-approvals/${entry.key}`);if(!here())return;
   requireReview(same(saved,entry.approval));
   const live=await api(`/api/internal/approvals/${saved.id}`);if(!here())return;
   requireReview(live.id===saved.id&&live.principal_id===v.principal&&live.project_id===v.project&&live.fingerprint===saved.fingerprint&&same(live.payload.snapshot,saved.snapshot)&&(entry.release||(unexpired(live)&&!live.consumed)));
  }
  if(entry.release){
   const saved=await api(`/api/internal/releases/${entry.release.id}`);if(!here())return;
   requireReview(Object.entries(entry.release).every(([key,value])=>same(saved[key],value))&&saved.namespace==="INTERNAL_ENGINEERING_ONLY"&&saved.formal_publication_enabled===false&&saved.approval_id===entry.approval.id&&saved.snapshot.draft.id===v.appId);
  }
  if(entry.adoption){
   const saved=await api(path+`/adoption-approvals/${entry.key}`);if(!here())return;
   requireReview(same(saved,entry.adoption)&&saved.principal_id===v.principal&&saved.project_id===v.project&&saved.payload.instance_id===v.id&&saved.payload.target_release_id===entry.release.id&&unexpired(saved));
  }
  if(!here())return;c.currentContext=ctx;c.reviewReady=true;drawReview();entry.message="已回读原修订并核对当前归属；请阅读完整冻结内容后重新勾选，下一步尚未提交。";
 }
 async function action(fn){if(!here()||c.busy||v.busy)return;c.busy=true;controls();applicationUseButtons(v);try{await fn();if(here()&&entry.ctx&&!c.reviewReady&&!c.staleCheckReady&&!unresolved())await restoreReview();}catch(error){if(here()&&!deny(error)){entry.message=`核查未完成：${error.message}。原键保留，未知请求只读恢复。`;controls();}}finally{c.busy=false;if(here()){controls();applicationUseButtons(v);}}}
 const edit=button("csv-goal-edit",currentRelease?"可选：编辑 Goal 并明确保存下一版本":"打开来源 Goal，保存下一版本",()=>action(async()=>{const pid=v.project;clearApp();selectWorkspace("projects");await showGoalCard(generation.goal_card_id,pid);}));
 const read=button("csv-goal-baseline",materialMode?"读取当前实例与已授权 CSV 材料":"读取新 Goal 与修订基线",()=>action(async()=>{
  const graphPath=`/api/projects/${v.project}/apps/${v.appId}/delivery-graph`;
  // This explicit action reuses the existing derive only for its exact stale
  // baseline conflict. A current parent anchor is read without mutation.
  if(!entry.baselineAccepted){
   let derive=!currentRelease||!!entry.steps.baseline;
   if(currentRelease&&!entry.steps.baseline){
    try{await api(graphPath);if(!here())return;}
    catch(error){if(!here())return;if(error.httpStatus!==409||error.message!=="VERSION_CONFLICT"||error.detail!=="Current graph baseline changed; explicitly derive a new anchor")throw error;derive=true;}
   }
   if(derive){
    const body=entry.steps.baseline?.body||{request_key:entry.baselineKey,expected_candidate_fingerprint:v.app.fingerprint};
    await request("baseline",graphPath+"/derive",body,graphPath+`/derive-requests/${entry.baselineKey}`,async(saved,b,hint)=>{
     const value=saved.response;
     if(saved.namespace!=="delivery-graph-derive-request.v1"||saved.principal_id!==v.principal||saved.project_id!==v.project||saved.app_id!==v.appId||saved.request_key!==entry.baselineKey||!same(saved.request,b)||saved.request_fingerprint!==await ownerHash(b)||value?.app_id!==v.appId||value.project_id!==v.project||value.runtime_id!==v.instance.runtime_id||value.candidate_fingerprint!==v.app.fingerprint)throw Error("原图锚回执尚未确认");
     if(hint){const {cached,...accepted}=hint;if(!same(value,accepted))throw Error("原图锚接受回执不匹配");}
     return value;
    },()=>{entry.baselineAccepted=true;});
    if(!here())return;
   }else entry.baselineAccepted=true;
  }
  const ctx=await readContext();if(!here())return;
  if(ctx.instance_id!==v.id||ctx.app_id!==v.appId||ctx.project_id!==v.project||ctx.release_fingerprint!==v.instance.release_fingerprint||ctx.instance_revision!==v.instance.revision)throw Error("修订基线与所选实例不匹配");
  entry.ctx=ctx;c.reviewReady=true;entry.message=materialMode?`保留已采用 Goal v${ctx.goal.version} 与列 ${ctx.parent.column}；请明确选择另一份已授权 CSV，核对资源与哈希后提交。`:ctx.parent?`基于规格 v${ctx.parent.spec_revision}、原实例修订 ${ctx.instance_revision}；${ctx.goal_mode==="KEEP_ADOPTED_GOAL"?"保留已采用的 Goal，不创建新目标版本":"使用已明确保存的下一 Goal"} v${ctx.goal.version}。新 Goal 可保留原列，也可明确修改列；下一规格独立重验。`:`来源 Goal v${ctx.original_goal_version} → 当前 v${ctx.goal.version}。两列相同表示保留该列、只修订 Goal；新版本将固定所选列。`;
  checkAck.checked=releaseAck.checked=adoptAck.checked=false;
  entry.selection={from:ctx.parent?.column||ctx.columns[0],to:materialMode?ctx.parent.column:ctx.columns.find(x=>x!==(ctx.parent?.column||ctx.columns[0]))||ctx.columns[0]};controls();
 }));
 async function request(stage,url,body,recoverUrl,verify,install){
  let p=entry.steps[stage];
  if(!p){p={body,state:"new"};entry.steps[stage]=p;}
  if(goalRunCanonical(p.body)!==goalRunCanonical(body))throw Error("已有请求输入已冻结；请恢复原请求");
  if(p.state==="sending")return;
  const recovery=p.state!=="new";p.state="sending";controls();
  try{
   let hint=null;
   if(!recovery){hint=await api(url,"POST",p.body);p.state="accepted-read-error";if(!here())return;}
   const saved=await api(recoverUrl);if(!here())return;
   const value=await verify(saved,p.body,hint);if(!here())return;
   install(value);p.state="accepted";entry.message="原键回读已核对；下一步需要单独确认。";
  }catch(error){
   const rejected=error.submissionRejection,stages={preview:"previews",check:"checks",version:"version-approvals",adopt:"adoption-approvals"};
   const proven=!recovery&&p.state==="sending"&&rejected?.namespace==="csv-goal-revision.v1.rejection"&&rejected.instance_id===v.id&&rejected.principal_id===v.principal&&rejected.stage===stages[stage]&&rejected.request_key===p.body.request_key&&rejected.request_fingerprint===await ownerHash(p.body)&&rejected.acceptance==="NOT_ACCEPTED"&&rejected.previous_request==="ABSENT"&&rejected.phase==="TX_ROLLED_BACK";
   p.state=proven?"rejected":"unknown";throw error;
  }
  finally{
   if(p.state==="sending")p.state="unknown";
   const live=applicationUse;if(applicationUseCurrent(live)&&applicationUseKey(live)===owner&&live.csvGoalRevision&&live.csvGoalRevision!==c){entry.message="原视图已离开；显式恢复原请求，未自动提交下一步。";live.csvGoalRevision.controls();}
  }
 }
 const save=button("csv-goal-preview",materialMode?"提交同一实例的材料替换草案":"提交 Goal 或列的修订草案",()=>action(async()=>{
  const ctx=entry.ctx;if(!ctx||(!entry.steps.preview&&!c.reviewReady))return;
  const chosen=selectedMaterial();
  if(materialMode&&!entry.steps.preview&&!chosen)return;
  const body=entry.steps.preview?.body||{request_key:entry.key,expected_revision:ctx.instance_revision,expected_release_fingerprint:ctx.release_fingerprint,expected_graph_fingerprint:ctx.graph_fingerprint,goal_version:ctx.goal.version,goal_fingerprint:ctx.goal.fingerprint,baseline_column:from.value,column:to.value,
   ...(materialMode?{expected_data_version:ctx.data_version,resource_id:chosen.resource_id,source_hash:chosen.hash}:{})};
  await request("preview",(materialMode?materialPath:path)+"/previews",body,path+`/previews/${entry.key}`,async(saved,b)=>{
   if(saved.request_key!==b.request_key||saved.context?.instance_id!==v.id||saved.context.goal.version!==b.goal_version||saved.context.goal.fingerprint!==b.goal_fingerprint||saved.input?.column!==b.column||saved.baseline_input?.column!==b.baseline_column||saved.context.release_fingerprint!==b.expected_release_fingerprint)throw Error("修订回执不匹配");
   if(materialMode&&(saved.namespace!==materialVersion||saved.context.revision_contract!==materialVersion||!same(saved.context,ctx)||saved.context.data_version!==b.expected_data_version||saved.material?.resource_id!==b.resource_id||saved.material.hash!==b.source_hash||saved.material.format!=="csv"||saved.material.revision!==1||b.baseline_column!==b.column||b.column!==ctx.parent.column))throw Error("材料替换的冻结回执不匹配");return saved;
  },value=>{entry.preview=value;checkAck.checked=releaseAck.checked=adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const check=button("csv-goal-check","确认并排队独立重验",()=>action(async()=>{
  if(!entry.preview||(!entry.steps.check&&(!(c.reviewReady||c.staleCheckReady)||!checkAck.checked)))return;
  const body={request_key:entry.key,expected_preview_fingerprint:entry.preview.preview_fingerprint,consent:"RUN_EXACT_CSV_GOAL_CHECK_KEEP_ORIGINAL"};
  await request("check",path+"/checks",body,path+`/checks/${entry.key}`,async(saved,b)=>{
   if(saved.request_key!==entry.key||saved.accepted_request_fingerprint!==await ownerHash(b)||!/^run_[a-f0-9]{32}$/.test(saved.run_id))throw Error("重验接受回执不匹配");return saved;
  },value=>{entry.check=value;if(value.status==="PASS")entry.proof=value;proof.textContent=JSON.stringify(value,null,2);checkAck.checked=false;});
 }));
 const outcome=button("csv-goal-outcome","只读刷新本次重验",()=>action(async()=>{
  const p=entry.steps.check;if(!p)return;const value=await api(path+`/checks/${entry.key}`);if(!here())return;
  if(value.accepted_request_fingerprint!==await ownerHash(p.body)||value.request_key!==entry.key)throw Error("重验原键不匹配");
  entry.check=value;if(value.status==="PASS")entry.proof=value;proof.textContent=JSON.stringify(value,null,2);entry.message=`本次重验 ${value.status}；语义 UNKNOWN，人工 PENDING。`;
  releaseAck.checked=adoptAck.checked=false;
 }));
 const prepare=button("csv-goal-version","准备本次已重验的 Release",()=>action(async()=>{
  if(!entry.proof||(!entry.steps.version&&!c.reviewReady))return;
  const body={request_key:entry.key,expected_check_fingerprint:entry.proof.check_fingerprint,consent:"CREATE_EXACT_CHECKED_CSV_GOAL_RELEASE"};
  await request("version",path+"/version-approvals",body,path+`/version-approvals/${entry.key}`,async(saved,b)=>{
   if(saved.snapshot?.csv_goal_revision_source?.check_fingerprint!==b.expected_check_fingerprint||saved.snapshot.csv_goal_revision_source.reference.preview_key!==entry.key||saved.snapshot.draft.fingerprint!==v.app.fingerprint||!/^iapproval_[a-f0-9]{32}$/.test(saved.id))throw Error("Release 批准来源不匹配");return saved;
  },value=>{entry.approval=value;releaseAck.checked=adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const commit=button("csv-goal-release","确认保存新 Release",()=>action(async()=>{
  if(!entry.approval||(!entry.steps.commit&&(!c.reviewReady||!releaseAck.checked||!unexpired(entry.approval))))return;const a=entry.approval;
  await request("commit",`/api/internal/approvals/${a.id}/commit`,{fingerprint:a.fingerprint},`/api/internal/apps/${v.appId}/releases`,async(saved)=>{
   const found=saved.items?.find(x=>x.approval_id===a.id);
   if(!found||found.snapshot.csv_goal_revision_source?.reference.preview_key!==entry.key||found.snapshot.draft.id!==v.appId)throw Error("原批准的新 Release 尚未读回");return found;
  },value=>{entry.release=value;proof.textContent=JSON.stringify(value,null,2);releaseAck.checked=false;});
 }));
 const adoptPrepare=button("csv-goal-adopt-prepare","核查原实例采用与保留结果",()=>action(async()=>{
  if(!entry.release||(!entry.steps.adopt&&!c.reviewReady))return;const target=entry.release;
  const body={request_key:entry.key,expected_revision:entry.ctx.instance_revision,target_release_id:target.id,expected_target_fingerprint:target.fingerprint};
  await request("adopt",path+"/adoption-approvals",body,path+`/adoption-approvals/${entry.key}`,async(saved,b)=>{
   const p=saved.payload;if(p?.instance_id!==v.id||p.target_release_id!==b.target_release_id||p.target_fingerprint!==b.expected_target_fingerprint||p.revision!==b.expected_revision)throw Error("采用批准与原实例不匹配");return saved;
  },value=>{entry.adoption=value;adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const adopt=button("csv-goal-adopt","明确采用到原实例",()=>action(async()=>{
  if(!entry.adoption||(!entry.steps.adoptCommit&&(!c.reviewReady||!adoptAck.checked||!unexpired(entry.adoption))))return;const a=entry.adoption;
  await request("adoptCommit",`/api/internal/instances/${v.id}/switch-approvals/${a.id}/commit`,{fingerprint:a.fingerprint},`/api/internal/instances/${v.id}`,async(saved)=>{
   const exact=saved.history?.some(h=>h.kind==="switch"&&h.approval_id===a.id&&h.previous_release_id===entry.ctx.release_id&&h.release_id===entry.release.id&&h.revision===entry.ctx.instance_revision+1);
   if(saved.id!==v.id||saved.principal_id!==v.principal||saved.project_id!==v.project||saved.source_app_id!==v.appId||saved.release_id!==entry.release.id||saved.release_fingerprint!==entry.release.fingerprint||saved.revision!==entry.ctx.instance_revision+1||saved.data_version!==entry.ctx.data_version||saved.runtime_id!==entry.ctx.runtime_id||!exact)throw Error("原实例采用尚未读回");return saved;
  },()=>{entry.state="adopted";adoptAck.checked=false;});
  if(here()&&entry.state==="adopted"){clearCsvGoalRevision(v);await readApplicationUse(v);}
 }));
 const recover=button("csv-goal-recover","只读恢复原请求",()=>action(async()=>{
  const stage=Object.keys(entry.steps).find(k=>["unknown","accepted-read-error"].includes(entry.steps[k].state));
  const actions={baseline:read,preview:save,check,version:prepare,commit,adopt:adoptPrepare,adoptCommit:adopt};
  // Release the local guard only for the original stage handler; its ledger
  // forces GET recovery and never sends a second POST.
  if(stage){c.busy=false;await actions[stage].onclick();}
 }));
 const reset=button("csv-goal-reset","明确重新准备一个新修订",()=>{
  if(!here()||c.busy||v.busy||!canReset())return;
  // Accepted/unknown keys remain in the map's audit history, never silently
  // reused. Only proved rejection or a terminal CHECK enables this.
  const replacement={key:crypto.randomUUID(),baselineKey:crypto.randomUUID(),steps:{},state:"new",mode:entry.mode,cycleRelease:entry.cycleRelease,history:[...(entry.history||[]),{key:entry.key,mode:entry.mode||"column",steps:entry.steps}]};
  csvGoalRevisionIntents.set(owner,replacement);clearCsvGoalRevision(v);renderCsvGoalRevision(v,release);
 });
 function canReturn(){
  return materialMode&&!unresolved()&&![entry.preview,entry.check,entry.proof,entry.approval,entry.release,entry.adoption].some(Boolean)
   &&Object.entries(entry.steps).every(([stage,p])=>stage==="baseline"||p.state==="rejected");
 }
 const back=button("csv-material-back","返回当前实例入口",()=>{
  if(!here()||c.busy||v.busy||!canReturn())return;
  // An unsubmitted/rejected material cycle can be left without deleting its
  // original key or accepted baseline ledger. Unknown and accepted business
  // stages always require their existing recovery/confirmation controller.
  const {history,...saved}=entry;
  entry.history=[...(history||[]),{...saved,state:"abandoned"}];entry.state="abandoned";
  clearCsvGoalRevision(v);renderCsvGoalRevision(v,release);
 });
 const review=button("csv-goal-review-restore","只读重新核对冻结修订",()=>action(restoreReview));
 function canReset(){return !Object.values(entry.steps).some(p=>["sending","unknown","accepted-read-error"].includes(p.state))&&(Object.values(entry.steps).some(p=>p.state==="rejected")||["FAILED","CANCELLED"].includes(entry.check?.status));}
 function controls(){
  if(!here())return;
  const pending=Object.entries(entry.steps).find(([,p])=>["sending","unknown","accepted-read-error"].includes(p.state));
  const busy=c.busy||v.busy,locked=!!pending||!c.reviewReady;
  for(const b of [edit,read,save,check,outcome,prepare,commit,adoptPrepare,adopt])b.disabled=busy||locked;
  edit.disabled=busy||!!pending;read.disabled=busy||!!pending||!!entry.preview;
  save.disabled||=!entry.ctx||!!entry.preview||(!entry.ctx.parent&&entry.ctx.goal.version!==entry.ctx.original_goal_version+1)||(materialMode?!selectedMaterial()||from.value!==entry.ctx?.parent?.column||to.value!==entry.ctx?.parent?.column:from.value===to.value&&!changedGoal(entry.ctx));
  check.disabled=busy||!!pending||!(c.reviewReady||c.staleCheckReady)||!entry.preview||!!entry.check||!checkAck.checked;
  outcome.disabled||=!entry.check;prepare.disabled||=!entry.proof||!!entry.approval;
  commit.disabled||=!entry.approval||!!entry.release||!releaseAck.checked||!unexpired(entry.approval);
  adoptPrepare.disabled||=!entry.release||!!entry.adoption;adopt.disabled||=!entry.adoption||!adoptAck.checked||!unexpired(entry.adoption);
  from.disabled=to.disabled=busy||locked||!!entry.steps.preview;
  from.disabled||=!!entry.ctx?.parent||materialMode;to.disabled||=materialMode;
  material.disabled=busy||locked||!!entry.steps.preview;
  checkAck.disabled=busy||!!pending||!(c.reviewReady||c.staleCheckReady)||!entry.preview||!!entry.check;releaseAck.disabled=busy||locked||!entry.approval||!!entry.release||!unexpired(entry.approval);adoptAck.disabled=busy||locked||!entry.adoption||!unexpired(entry.adoption);
  recover.hidden=!pending||pending[1].state==="sending";recover.disabled=busy;
  review.hidden=!entry.ctx||!!pending||c.reviewReady;review.disabled=busy;
  reset.hidden=!canReset();reset.disabled=busy;
  back.hidden=!materialMode;back.disabled=busy||!canReturn();
  status.textContent=entry.message||(pending?"原请求结果未知；仅恢复原键。":materialMode?"先读取当前有效版本和已授权 CSV，保留已采用 Goal 与列，明确选择另一份材料。每步独立确认。":currentRelease?"先读取当前有效版本基线；可只修订下一 Goal 并保留列，或明确修改列。每步独立确认。":"先保存来源 Goal 的下一版本，再核查修订基线。每步独立确认。");
  drawReview();
 }
 c.controls=controls;from.onchange=to.onchange=()=>{entry.selection={from:from.value,to:to.value};checkAck.checked=releaseAck.checked=adoptAck.checked=false;controls();};
 material.onchange=()=>{const chosen=c.materials.find(x=>x.resource_id===material.value);entry.selection={from:entry.ctx.parent.column,to:entry.ctx.parent.column,resource_id:chosen?.resource_id,source_hash:chosen?.hash};checkAck.checked=releaseAck.checked=adoptAck.checked=false;controls();};
 material.hidden=materialInfo.hidden=!materialMode;edit.hidden=materialMode;
 node.append(row("同一应用与运行身份，保留原来源及历史。按明确列映射执行，模型请求0；内部未发布，目标语义 UNKNOWN，人工 PENDING。"),edit,read,
  csvFullReportLabel("原绑定列",from),csvFullReportLabel(materialMode?"保留绑定列":"新定义列",to),...(materialMode?[csvFullReportLabel("目标 CSV 材料（须明确选择）",material),materialInfo,back]:[]),save,checkLabel,check,outcome,prepare,releaseLabel,commit,adoptPrepare,adoptLabel,adopt,recover,review,reset,status,proof);
 $("use-info").after(node);controls();
 if(entry.ctx&&!unresolved())return action(restoreReview);
}
