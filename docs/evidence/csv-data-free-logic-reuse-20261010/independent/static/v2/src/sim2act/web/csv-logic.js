"use strict";
// No original goal, column, result or source bytes enter this project registry.
const csvLogicVersion="internal.csv-data-free-logic.v1",csvLogicIntents=new Map();
let csvLogicEpoch=0,csvLogicContext=null;
const csvLogicKey=c=>JSON.stringify([c.identity,c.project]);
const csvLogicCurrent=c=>!!c&&c===csvLogicContext&&c.epoch===csvLogicEpoch&&c.identity===token&&c.connection===identityConnectionGeneration&&c.project===$("project-select").value&&c.selection===appSelectionGeneration;
const csvLogicFields=["resource_id","column","count","sum","source_hash"];
function csvLogicRecipe(version,column=null){
  const nodes=[{step_id:"read",action:"resource.read",depends_on:[],inputs:{resource_id:{source:"data",ref:"source",field:"resource_id"}}},{step_id:"aggregate",action:"data.aggregate_csv",depends_on:["read"],inputs:{resource_id:{source:"step",ref:"read",field:"resource_id"},column:{source:"input",field:"aggregate_column"}}}];
  if(column!==null)nodes[1].column=column;
  if(version==="internal.csv-read-sum-report.v1")nodes.push({step_id:"report",action:"intern.csv_report.v1",depends_on:["aggregate"],inputs:Object.fromEntries(csvLogicFields.map(k=>[k,{source:"step",ref:"aggregate",field:k}]))});
  return {version:"csv.composition.v1",nodes};
}
function csvLogicSchema(){const obj=fields=>({type:"object",properties:fields,required:Object.keys(fields),additionalProperties:false});return obj({result:obj(Object.fromEntries(csvLogicFields.map(k=>[k,{type:k==="count"?"integer":"string"}])))});}
function clearCsvLogic(){
  csvLogicEpoch++;csvLogicContext=null;
  for(const id of ["selected","target","column"])$("csv-logic-"+id).replaceChildren();
  for(const id of ["proof","status"])$("csv-logic-"+id).textContent="";
  for(const id of ["confirm","revoke-confirm","authorize-confirm"])$("csv-logic-"+id).checked=false;
  csvLogicButtons();
}
function csvLogicContextNow(){
  if(!csvLogicCurrent(csvLogicContext)){clearCsvLogic();csvLogicContext={identity:token,project:$("project-select").value,connection:identityConnectionGeneration,selection:appSelectionGeneration,epoch:csvLogicEpoch,busy:false,logic:null,items:[],materials:[],plan:null};}
  return csvLogicContext;
}
function csvLogicButtons(){
  const c=csvLogicContext,live=c&&csvLogicCurrent(c),intent=c?csvLogicIntents.get(csvLogicKey(c)):csvLogicIntents.get(JSON.stringify([token,$("project-select").value])),locked=!!intent||!!c?.busy;
  for(const id of ["history","selected","read","options","target","column","confirm","plan","open","revoke","revoke-confirm"])$("csv-logic-"+id).disabled=locked;
  $("csv-logic-read").disabled=locked||!live||!c.logic;
  $("csv-logic-options").disabled=locked||!live||c.logic?.status!=="ACTIVE";
  $("csv-logic-plan").disabled=locked||!live||!c.materials.some(v=>v.target_app_id===$("csv-logic-target").value)||!$("csv-logic-column").value||!$("csv-logic-confirm").checked;
  $("csv-logic-open").disabled=locked||!live||!c.plan;
  $("csv-logic-revoke").disabled=locked||!live||!c.logic||!$("csv-logic-revoke-confirm").checked;
  $("csv-logic-recover").hidden=!intent;$("csv-logic-recover").disabled=!!c?.busy;
  $("csv-logic-authorize").disabled=locked||!csvDagContext?.reuse?.release||!csvDagCurrent(csvDagContext)||!$("csv-logic-authorize-confirm").checked;
  $("csv-logic-authorize-confirm").disabled=locked;
}
async function csvLogicSeal(obj,c,expected=null){
  if(!obj||obj.namespace!==csvLogicVersion||!/^csvlogic_[a-f0-9]{32}$/.test(obj.id)||!/^user_[a-f0-9]{32}$/.test(obj.owner_id)||obj.project_id!==c.project||!Number.isFinite(obj.expires_at)||obj.scope!=="EXISTING_AUTHORIZED_CSV_DRAFTS_SAME_OWNER_PROJECT"||!["internal.csv-read-sum.v1","internal.csv-read-sum-report.v1"].includes(obj.execution_version)||obj.audit_ref!==obj.id||obj.model_requests!==0||obj.semantic_status!=="UNKNOWN"||obj.owner_acceptance!=="PENDING"||obj.formal_publication_enabled!==false||!deliveryHash(obj.implementation_fingerprint)||!["ACTIVE","REVOKED","EXPIRED"].includes(obj.status)||!deliverySame(obj.recipe,csvLogicRecipe(obj.execution_version))||!deliverySame(obj.data_schema,csvLogicSchema()))return false;
  const keys=["namespace","id","owner_id","project_id","expires_at","scope","execution_version","recipe","data_schema","limits","implementation_fingerprint","audit_ref","model_requests","semantic_status","owner_acceptance","formal_publication_enabled","fingerprint","status"];
  if(!deliverySame(Object.keys(obj).sort(),keys.sort())||!deliverySame(Object.keys(obj.limits).sort(),["max_requests","max_total_tokens","max_tools","max_repairs","run_seconds"].sort())||Object.entries(obj.limits).some(([k,v])=>!Number.isFinite(v)||v<0||k!=="run_seconds"&&!Number.isInteger(v)))return false;
  const {fingerprint,status,...body}=obj;if(await deliveryDigest(body)!==fingerprint)return false;
  if(expected){const e=expected.snapshot.execution_source;if(obj.owner_id!==expected.principal_id||obj.execution_version!==e.version||!deliverySame(obj.limits,e.limits))return false;}
  return true;
}
async function csvLogicPlanSeal(m,i,c){
  const b=m?.binding,p=m?.plan,t=i.target,l=i.logic,key="logic-plan-"+(await deliveryDigest([l.id,i.body.request_key])).slice(0,48);
  if(!m||m.namespace!==csvLogicVersion||m.model_requests!==0||m.formal_publication_enabled!==false||!b||!p||!await csvLogicSeal(b.logic,c)||!deliverySame(b.logic,l)||!deliverySame(b.target,t)||b.version!==csvLogicVersion||b.column!==i.body.column||b.request_key!==i.body.request_key||b.principal_id!==l.owner_id||b.model_requests!==0||b.formal_publication_enabled!==false||!deliverySame(b.limits,l.limits)||m.binding_fingerprint!==await deliveryDigest(b)||p.request_key!==key||p.app_id!==t.target_app_id||p.project_id!==c.project||p.runtime_id!==t.runtime_id||p.source_hash!==t.source_hash||p.candidate_fingerprint!==t.candidate_fingerprint||p.graph_fingerprint!==t.graph_fingerprint||p.model_requests!==0||p.model_generated!==false||p.business_writes!==0||p.publishable!==false||p.formal_publication_enabled!==false||p.semantic_status!=="UNKNOWN"||p.owner_acceptance!=="PENDING"||p.state!=="DRAFT_PLAN"||!deliverySame(p.definition?.manifest?.runtime_limits,l.limits)||!deliverySame(p.composition?.definition,csvLogicRecipe(l.execution_version,i.body.column))||!deliverySame(p.input,{aggregate_column:i.body.column})||!deliverySame(p.logical_reuse,{version:csvLogicVersion,logic_id:l.id,logic_fingerprint:l.fingerprint,origin_key:key,binding_fingerprint:m.binding_fingerprint}))return false;
  const expected={expected_candidate_fingerprint:t.candidate_fingerprint,expected_graph_fingerprint:t.graph_fingerprint,column:i.body.column,composition:csvLogicRecipe(l.execution_version,i.body.column),request_key:key};
  if(!deliverySame(b.plan_input,expected))return false;
  const {cached,plan_fingerprint,...value}=p;return await deliveryDigest(value)===plan_fingerprint;
}
async function csvLogicAction(fn){const c=csvLogicContextNow();if(c.busy)return;c.busy=true;csvLogicButtons();try{await fn(c);}catch(e){if(csvLogicCurrent(c))$("csv-logic-status").textContent=e.message;}finally{c.busy=false;if(csvLogicCurrent(c))csvLogicButtons();}}
function csvLogicPaint(c,obj){c.logic=obj;c.plan=null;c.materials=[];$("csv-logic-proof").textContent=JSON.stringify(obj,null,2);$("csv-logic-status").textContent=`独立结构授权 ${obj.status}；24h固定期限，目标仍须当前授权。语义 UNKNOWN，用户 PENDING。`;$("csv-logic-revoke-confirm").checked=false;}
function csvLogicPick(c){c.plan=null;$("csv-logic-confirm").checked=false;$("csv-logic-proof").textContent="";const t=c.materials.find(v=>v.target_app_id===$("csv-logic-target").value);$("csv-logic-column").replaceChildren(...(t?.columns||[]).map(v=>new Option(v,v)));csvLogicButtons();}
async function csvLogicSubmit(kind,recover=false){
  const c=csvLogicContextNow(),scope=csvLogicKey(c);if(c.busy)return;
  let i=csvLogicIntents.get(scope);
  if(!recover){if(i)return;
    if(kind==="authorize"){const r=csvDagContext?.reuse?.release;if(!r||!csvDagCurrent(csvDagContext)||!$("csv-logic-authorize-confirm").checked)return;i={kind,release:r,path:`/api/internal/releases/${r.id}/csv-logic-authorizations`,body:{expected_release_fingerprint:r.fingerprint,consent:"AUTHORIZE_DATA_FREE_CSV_LOGIC_IN_THIS_PROJECT",request_key:crypto.randomUUID()}};}
    else if(kind==="plan"){const t=c.materials.find(v=>v.target_app_id===$("csv-logic-target").value);if(c.logic?.status!=="ACTIVE"||!t||!t.columns.includes($("csv-logic-column").value)||!$("csv-logic-confirm").checked)return;i={kind,logic:c.logic,target:t,path:`/api/internal/csv-logics/${c.logic.id}/material-plans`,body:{expected_logic_fingerprint:c.logic.fingerprint,target_app_id:t.target_app_id,expected_candidate_fingerprint:t.candidate_fingerprint,expected_graph_fingerprint:t.graph_fingerprint,expected_resource_id:t.resource_id,expected_source_hash:t.source_hash,column:$("csv-logic-column").value,request_key:crypto.randomUUID()}};}
    else {if(!c.logic||!$("csv-logic-revoke-confirm").checked)return;i={kind,logic:c.logic,path:`/api/internal/csv-logics/${c.logic.id}/revoke`,body:{expected_logic_fingerprint:c.logic.fingerprint,consent:"REVOKE_DATA_FREE_CSV_LOGIC",request_key:crypto.randomUUID()}};}
    csvLogicIntents.set(scope,i);
  }
  if(!i)return;c.busy=true;csvLogicButtons();
  try{
    let response;
    if(!i.accepted){response=await api(i.path,"POST",i.body);
      if(i.kind==="authorize"){
        const exact="csvlogic_"+(await deliveryDigest([i.release.principal_id,i.release.id,i.body.request_key])).slice(0,32);
        if(response.model_requests!==0||response.formal_publication_enabled!==false||!await csvLogicSeal(response.logic,c,i.release)||response.logic.id!==exact||response.logic.status!=="ACTIVE")throw Error("VERIFICATION_FAILED");
        i.accepted=response.logic;
      }else if(i.kind==="plan"){if(!await csvLogicPlanSeal(response,i,c))throw Error("VERIFICATION_FAILED");i.accepted=response;}
      else {if(response.namespace!==csvLogicVersion||response.id!==i.logic.id||response.logic_fingerprint!==i.logic.fingerprint||response.status!=="REVOKED"||response.request_key!==i.body.request_key||response.model_requests!==0||response.formal_publication_enabled!==false)throw Error("VERIFICATION_FAILED");i.accepted=response;}
    }
    // Store a verified late receipt before checking selection; no late painting.
    if(!csvLogicCurrent(c))return;
    if(i.kind==="plan"){
      const got=await api(`${i.path}/${i.target.target_app_id}/${i.accepted.plan.request_key}`);
      if(!await csvLogicPlanSeal(got,i,c)||got.plan.plan_fingerprint!==i.accepted.plan.plan_fingerprint)throw Error("VERIFICATION_FAILED");
      if(!csvLogicCurrent(c))return;c.logic=i.logic;c.plan=got;$("csv-logic-proof").textContent=JSON.stringify(got,null,2);$("csv-logic-status").textContent="目标计划已核读回；打开后另行确认执行。尚未执行或写入结果。";
    }else{
      const got=await api(`/api/internal/csv-logics/${i.kind==="authorize"?i.accepted.id:i.logic.id}`);
      if(!await csvLogicSeal(got,c)||got.fingerprint!==(i.kind==="authorize"?i.accepted.fingerprint:i.logic.fingerprint)||i.kind==="revoke"&&got.status!=="REVOKED")throw Error("VERIFICATION_FAILED");
      if(!csvLogicCurrent(c))return;csvLogicPaint(c,got);c.items=[got];$("csv-logic-selected").replaceChildren(new Option(`${got.id} · ${got.status}`,got.id));
    }
    csvLogicIntents.delete(scope);
  }catch(e){if(csvLogicCurrent(c))$("csv-logic-status").textContent=`UNKNOWN ${e.message}；保留完整确认与原键。已核接受仅GET回读；未知接受原键重试。`;}
  finally{c.busy=false;if(csvLogicCurrent(c))csvLogicButtons();}
}
$("csv-logic-history").onclick=()=>csvLogicAction(async c=>{c.logic=null;c.plan=null;$("csv-logic-proof").textContent="";const m=await api(`/api/projects/${c.project}/csv-logics`);if(m.namespace!==csvLogicVersion||m.model_requests!==0||m.formal_publication_enabled!==false||!Array.isArray(m.items))throw Error("VERIFICATION_FAILED");for(const v of m.items)if(!await csvLogicSeal(v,c))throw Error("VERIFICATION_FAILED");if(!csvLogicCurrent(c))return;c.items=m.items;$("csv-logic-selected").replaceChildren(...m.items.map(v=>new Option(`${v.id} · ${v.status}`,v.id)));if(m.items[0])csvLogicPaint(c,m.items[0]);else $("csv-logic-status").textContent="尚无独立授权；不能从失效来源补发。";});
$("csv-logic-selected").onchange=()=>{const c=csvLogicContextNow(),v=c.items.find(v=>v.id===$("csv-logic-selected").value);if(v)csvLogicPaint(c,v);csvLogicButtons();};
$("csv-logic-read").onclick=()=>csvLogicAction(async c=>{const expected=c.logic;const v=await api(`/api/internal/csv-logics/${expected.id}`);if(!await csvLogicSeal(v,c)||v.fingerprint!==expected.fingerprint)throw Error("VERIFICATION_FAILED");if(csvLogicCurrent(c))csvLogicPaint(c,v);});
$("csv-logic-options").onclick=()=>csvLogicAction(async c=>{const l=c.logic;c.plan=null;c.materials=[];$("csv-logic-proof").textContent="";const m=await api(`/api/internal/csv-logics/${l.id}/materials`);if(m.namespace!==csvLogicVersion||m.model_requests!==0||m.formal_publication_enabled!==false||!await csvLogicSeal(m.logic,c)||!deliverySame(m.logic,l)||!Array.isArray(m.items)||m.items.some(t=>t.project_id!==c.project||!/^app_[a-f0-9]{32}$/.test(t.target_app_id)||!/^res_[a-f0-9]{32}$/.test(t.resource_id)||!deliveryHash(t.source_hash)||!deliveryHash(t.candidate_fingerprint)||!deliveryHash(t.graph_fingerprint)||!Array.isArray(t.columns)||t.columns.some(v=>typeof v!=="string")))throw Error("VERIFICATION_FAILED");if(!csvLogicCurrent(c))return;c.materials=m.items;$("csv-logic-target").replaceChildren(...m.items.map(t=>new Option(`${t.name} · ${t.resource_id} · ${t.source_hash}`,t.target_app_id)));csvLogicPick(c);$("csv-logic-status").textContent=`${m.items.length}份当前授权目标；冻结预算 ${JSON.stringify(l.limits)}。`;});
$("csv-logic-target").onchange=()=>csvLogicPick(csvLogicContextNow());
$("csv-logic-column").onchange=()=>{const c=csvLogicContextNow();c.plan=null;$("csv-logic-confirm").checked=false;$("csv-logic-proof").textContent="";csvLogicButtons();};
for(const id of ["confirm","revoke-confirm","authorize-confirm"])$("csv-logic-"+id).onchange=csvLogicButtons;
$("csv-logic-authorize").onclick=()=>csvLogicSubmit("authorize");
$("csv-logic-plan").onclick=()=>csvLogicSubmit("plan");
$("csv-logic-revoke").onclick=()=>csvLogicSubmit("revoke");
$("csv-logic-recover").onclick=()=>csvLogicSubmit(null,true);
$("csv-logic-open").onclick=()=>csvLogicAction(async c=>{const m=c.plan;if(!m)return;let generation=null;await showApp(m.binding.target.target_app_id,c.project,g=>{generation=g;});const next=csvDagContext;if(!next||!csvDagCurrent(next)||next.parent.generation!==generation||next.parent.identity!==c.identity||next.parent.project!==c.project||next.parent.id!==m.binding.target.target_app_id)return;const p=await api(csvDagBase(next)+"/"+m.plan.request_key);if(!csvDagCurrent(next))return;if(p.plan_fingerprint!==m.plan.plan_fingerprint||!await csvDagPlanSeal(p,next))throw Error("VERIFICATION_FAILED");if(!csvDagCurrent(next))return;next.plan=p;next.job=null;$("csv-dag-definition").textContent=JSON.stringify(p,null,2);$("csv-dag-confirm").checked=false;$("csv-dag-status").textContent="独立逻辑目标计划已打开；请另行确认执行。";csvDagButtons(next);});
csvLogicButtons();
