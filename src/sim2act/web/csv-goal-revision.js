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
 const title=document.createElement("h3");title.textContent="修订此应用的 Goal 与列绑定";node.append(title);
 const currentRelease=release.snapshot.csv_goal_revision_source;
 if(currentRelease){node.append(row(`已采用 Goal v${currentRelease.goal.version}：${currentRelease.goal.snapshot.content.goal}。新列固定为 ${currentRelease.input.column}；每次新运行的人工声明独立，初始 PENDING。`));$("use-info").after(node);return;}
 const owner=applicationUseKey(v);let entry=csvGoalRevisionIntents.get(owner);
 if(!entry){entry={key:crypto.randomUUID(),baselineKey:crypto.randomUUID(),steps:{},state:"new"};csvGoalRevisionIntents.set(owner,entry);}
 const c={signature,node,connection:identityConnectionGeneration,workspace:workspaceSelectionGeneration,busy:false};v.csvGoalRevision=c;
 const here=()=>applicationUseCurrent(v)&&v.csvGoalRevision===c&&node.isConnected&&c.connection===identityConnectionGeneration&&c.workspace===workspaceSelectionGeneration&&!$("apps").hidden;
 const path=`/api/internal/instances/${v.id}/csv-goal-revisions`;
 const status=document.createElement("p");status.id="csv-goal-revision-status";status.setAttribute("role","status");
 const proof=document.createElement("pre");proof.id="csv-goal-revision-proof";
 const from=document.createElement("select"),to=document.createElement("select");from.id="csv-goal-from";to.id="csv-goal-to";
 const ack=(id,label)=>{const input=document.createElement("input");input.type="checkbox";input.id=id;input.onchange=controls;return [input,csvFullReportLabel(label,input)];};
 const [checkAck,checkLabel]=ack("csv-goal-check-ack","已核对 Goal、旧列→新列和影响范围，确认在独立实例实际重验");
 const [releaseAck,releaseLabel]=ack("csv-goal-release-ack","已核对本次实际重验，确认保存新内部 Release");
 const [adoptAck,adoptLabel]=ack("csv-goal-adopt-ack","已核对原实例、目标 Release 和保留结果，明确采用此版本");
 const button=(id,label,fn)=>csvFullReportButton(label,id,fn);
 function deny(error){
  if(!here()||![403,409].includes(error.httpStatus))return false;
  delete entry.ctx;delete entry.preview;delete entry.proof;delete entry.approval;delete entry.release;delete entry.adoption;
  entry.message="当前来源、权限或版本已失效。保留原键；已证明未受理的请求可明确重新准备。";
  clearApplicationUseData(v);return true;
 }
 async function action(fn){if(!here()||c.busy||v.busy)return;c.busy=true;controls();applicationUseButtons(v);try{await fn();}catch(error){if(here()&&!deny(error)){entry.message=`核查未完成：${error.message}。原键保留，未知请求只读恢复。`;controls();}}finally{c.busy=false;if(here()){controls();applicationUseButtons(v);}}}
 const edit=button("csv-goal-edit","打开来源 Goal，保存下一版本",()=>action(async()=>{const pid=v.project;clearApp();selectWorkspace("projects");await showGoalCard(generation.goal_card_id,pid);}));
 const read=button("csv-goal-baseline","读取新 Goal 与修订基线",()=>action(async()=>{
  const graphPath=`/api/projects/${v.project}/apps/${v.appId}/delivery-graph`;
  // This explicit action saves a missing/stale graph with the existing bounded
  // derive controller. Its deterministic key also handles a lost derive reply.
  if(!entry.baselineAccepted){
   if(entry.baselineUnknown){const saved=await api(graphPath);if(!here())return;if(saved.derivation_key!==entry.baselineKey)throw Error("原图锚回执尚未确认");}
   else{entry.baselineUnknown=true;await api(graphPath+"/derive","POST",{request_key:entry.baselineKey,expected_candidate_fingerprint:v.app.fingerprint});if(!here())return;}
   entry.baselineAccepted=true;entry.baselineUnknown=false;
  }
  const ctx=await api(path+"/context");if(!here())return;
  if(ctx.instance_id!==v.id||ctx.app_id!==v.appId||ctx.project_id!==v.project||ctx.release_fingerprint!==v.instance.release_fingerprint||ctx.instance_revision!==v.instance.revision)throw Error("修订基线与所选实例不匹配");
  entry.ctx=ctx;entry.message=`来源 Goal v${ctx.original_goal_version} → 当前 v${ctx.goal.version}。请明确选择旧列和新列，再提交修订草案。`;
  checkAck.checked=releaseAck.checked=adoptAck.checked=false;
  from.replaceChildren(...ctx.columns.map(x=>new Option(x,x)));to.replaceChildren(...ctx.columns.map(x=>new Option(x,x)));if(ctx.columns.length>1)to.selectedIndex=1;
  proof.textContent=JSON.stringify(ctx,null,2);controls();
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
 const save=button("csv-goal-preview","提交 Goal 与列的修订草案",()=>action(async()=>{
  const ctx=entry.ctx;if(!ctx)return;
  const body=entry.steps.preview?.body||{request_key:entry.key,expected_revision:ctx.instance_revision,expected_release_fingerprint:ctx.release_fingerprint,expected_graph_fingerprint:ctx.graph_fingerprint,goal_version:ctx.goal.version,goal_fingerprint:ctx.goal.fingerprint,baseline_column:from.value,column:to.value};
  await request("preview",path+"/previews",body,path+`/previews/${entry.key}`,async(saved,b)=>{
   if(saved.request_key!==b.request_key||saved.context?.instance_id!==v.id||saved.context.goal.version!==b.goal_version||saved.context.goal.fingerprint!==b.goal_fingerprint||saved.input?.column!==b.column||saved.baseline_input?.column!==b.baseline_column||saved.context.release_fingerprint!==b.expected_release_fingerprint)throw Error("修订回执不匹配");return saved;
  },value=>{entry.preview=value;checkAck.checked=releaseAck.checked=adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const check=button("csv-goal-check","确认并排队独立重验",()=>action(async()=>{
  if(!entry.preview||(!entry.steps.check&&!checkAck.checked))return;
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
  if(!entry.proof)return;
  const body={request_key:entry.key,expected_check_fingerprint:entry.proof.check_fingerprint,consent:"CREATE_EXACT_CHECKED_CSV_GOAL_RELEASE"};
  await request("version",path+"/version-approvals",body,path+`/version-approvals/${entry.key}`,async(saved,b)=>{
   if(saved.snapshot?.csv_goal_revision_source?.check_fingerprint!==b.expected_check_fingerprint||saved.snapshot.csv_goal_revision_source.reference.preview_key!==entry.key||saved.snapshot.draft.fingerprint!==v.app.fingerprint||!/^iapproval_[a-f0-9]{32}$/.test(saved.id))throw Error("Release 批准来源不匹配");return saved;
  },value=>{entry.approval=value;releaseAck.checked=adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const commit=button("csv-goal-release","确认保存新 Release",()=>action(async()=>{
  if(!entry.approval||(!entry.steps.commit&&!releaseAck.checked))return;const a=entry.approval;
  await request("commit",`/api/internal/approvals/${a.id}/commit`,{fingerprint:a.fingerprint},`/api/internal/apps/${v.appId}/releases`,async(saved)=>{
   const found=saved.items?.find(x=>x.approval_id===a.id);
   if(!found||found.snapshot.csv_goal_revision_source?.reference.preview_key!==entry.key||found.snapshot.draft.id!==v.appId)throw Error("原批准的新 Release 尚未读回");return found;
  },value=>{entry.release=value;proof.textContent=JSON.stringify(value,null,2);releaseAck.checked=false;});
 }));
 const adoptPrepare=button("csv-goal-adopt-prepare","核查原实例采用与保留结果",()=>action(async()=>{
  if(!entry.release)return;const target=entry.release;
  const body={request_key:entry.key,expected_revision:entry.ctx.instance_revision,target_release_id:target.id,expected_target_fingerprint:target.fingerprint};
  await request("adopt",path+"/adoption-approvals",body,path+`/adoption-approvals/${entry.key}`,async(saved,b)=>{
   const p=saved.payload;if(p?.instance_id!==v.id||p.target_release_id!==b.target_release_id||p.target_fingerprint!==b.expected_target_fingerprint||p.revision!==b.expected_revision)throw Error("采用批准与原实例不匹配");return saved;
  },value=>{entry.adoption=value;adoptAck.checked=false;proof.textContent=JSON.stringify(value,null,2);});
 }));
 const adopt=button("csv-goal-adopt","明确采用到原实例",()=>action(async()=>{
  if(!entry.adoption||(!entry.steps.adoptCommit&&!adoptAck.checked))return;const a=entry.adoption;
  await request("adoptCommit",`/api/internal/instances/${v.id}/switch-approvals/${a.id}/commit`,{fingerprint:a.fingerprint},`/api/internal/instances/${v.id}`,async(saved)=>{
   if(saved.id!==v.id||saved.release_id!==entry.release.id||saved.revision!==entry.ctx.instance_revision+1||saved.runtime_id!==entry.ctx.runtime_id)throw Error("原实例采用尚未读回");return saved;
  },()=>{entry.state="adopted";adoptAck.checked=false;});
  if(here()&&entry.state==="adopted")await readApplicationUse(v);
 }));
 const recover=button("csv-goal-recover","只读恢复原请求",()=>action(async()=>{
  const stage=Object.keys(entry.steps).find(k=>["unknown","accepted-read-error"].includes(entry.steps[k].state));
  const actions={preview:save,check,version:prepare,commit,adopt:adoptPrepare,adoptCommit:adopt};
  // Release the local guard only for the original stage handler; its ledger
  // forces GET recovery and never sends a second POST.
  if(stage){c.busy=false;await actions[stage].onclick();}
 }));
 const reset=button("csv-goal-reset","明确重新准备一个新修订",()=>{
  if(!here()||c.busy||v.busy||!canReset())return;
  // Accepted/unknown keys remain in the map's audit history, never silently
  // reused. Only proved rejection or a terminal CHECK enables this.
  const replacement={key:crypto.randomUUID(),baselineKey:crypto.randomUUID(),steps:{},state:"new",history:[...(entry.history||[]),{key:entry.key,steps:entry.steps}]};
  csvGoalRevisionIntents.set(owner,replacement);clearCsvGoalRevision(v);renderCsvGoalRevision(v,release);
 });
 function canReset(){return !Object.values(entry.steps).some(p=>["sending","unknown","accepted-read-error"].includes(p.state))&&(Object.values(entry.steps).some(p=>p.state==="rejected")||["FAILED","CANCELLED"].includes(entry.check?.status));}
 function controls(){
  if(!here())return;
  const pending=Object.entries(entry.steps).find(([,p])=>["sending","unknown","accepted-read-error"].includes(p.state));
  const busy=c.busy||v.busy,locked=!!pending;
  for(const b of [edit,read,save,check,outcome,prepare,commit,adoptPrepare,adopt])b.disabled=busy||locked;
  save.disabled||=!entry.ctx||!!entry.preview||entry.ctx.goal.version!==entry.ctx.original_goal_version+1||from.value===to.value;
  check.disabled||=!entry.preview||!!entry.check||!checkAck.checked;
  outcome.disabled||=!entry.check;prepare.disabled||=!entry.proof||!!entry.approval;
  commit.disabled||=!entry.approval||!!entry.release||!releaseAck.checked;
  adoptPrepare.disabled||=!entry.release||!!entry.adoption;adopt.disabled||=!entry.adoption||!adoptAck.checked;
  from.disabled=to.disabled=busy||!!entry.steps.preview;
  checkAck.disabled=busy||!entry.preview||!!entry.check;releaseAck.disabled=busy||!entry.approval||!!entry.release;adoptAck.disabled=busy||!entry.adoption;
  recover.hidden=!pending||pending[1].state==="sending";recover.disabled=busy;
  reset.hidden=!canReset();reset.disabled=busy;
  status.textContent=entry.message||(pending?"原请求结果未知；仅恢复原键。":"先保存来源 Goal 的下一版本，再核查修订基线。每步独立确认。");
 }
 c.controls=controls;from.onchange=to.onchange=()=>{checkAck.checked=releaseAck.checked=adoptAck.checked=false;controls();};
 node.append(row("同一应用与运行身份，保留原来源及历史。按明确列映射执行，模型请求0；内部未发布，目标语义 UNKNOWN，人工 PENDING。"),edit,read,
  csvFullReportLabel("原绑定列",from),csvFullReportLabel("新定义列",to),save,checkLabel,check,outcome,prepare,releaseLabel,commit,adoptPrepare,adoptLabel,adopt,recover,reset,status,proof);
 $("use-info").after(node);controls();
}
