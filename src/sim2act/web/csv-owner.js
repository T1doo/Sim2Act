"use strict";
// Same sealed owner protocol, with an independent prospective CSV sum-only scope.
const csvOwnerIntents=new Map();
let csvOwnerView=null;
function csvReviewStartScope(v){return goalRunCanonical([v.identity,identityConnectionGeneration,v.project,v.id,v.instance?.revision,v.instance?.release_fingerprint,$('use-column').value,workspaceSelectionGeneration]);}
function renderCsvReviewStart(v,release){
 $('use-csv-review-start')?.remove();
 const node=document.createElement('div');node.id='use-csv-review-start';
 const ack=document.createElement('input');ack.type='checkbox';ack.id='use-csv-review-optin';
 const label=document.createElement('label');label.append(ack,'为下一次新Run事前冻结本人适用范围声明：仅固定CSV所选列的结构化求和，不含MD报告。');
 const preview=document.createElement('pre');preview.id='use-csv-review-scope';
 function changed(){ack.checked=false;v.csvReviewScope=csvReviewStartScope(v);preview.textContent=JSON.stringify({scope:'SUM_ONLY_WITHOUT_MD',release_id:release.id,release_fingerprint:release.fingerprint,instance_id:v.id,revision:v.instance?.revision,resource_id:v.app.candidate.manifest.data_bindings[0].resource_ref,source_hash:v.app.candidate.source_hash,column:$('use-column').value},null,2);}
 const column=$('use-column');if(v.csvReviewChange){column.removeEventListener('change',v.csvReviewChange);column.removeEventListener('input',v.csvReviewChange);}v.csvReviewChange=changed;changed();column.addEventListener('change',changed);column.addEventListener('input',changed);ack.onchange=()=>{if(v.csvReviewScope!==csvReviewStartScope(v))changed();};
 const details=document.createElement('details'),summary=document.createElement('summary');summary.textContent='查看本次声明的精确范围';details.append(summary,preview);
 node.append(label,details);$('use-form').append(node);
}
function csvOwnerRedact(v){for(const id of ['use-output','use-provenance','use-column','use-history'])$(id).replaceChildren();$('use-csv-review-start')?.remove();v.instance=null;$('use-form').hidden=true;$('use-info').textContent='当前材料或版本不可核验；仅保留本人声明元数据及停止入口。';}
function resumeCsvOwnerReview(){const v=applicationUse;if(applicationUseCurrent(v)&&v.selected){csvOwnerView=null;$('csv-owner-review')?.remove();safe(()=>readApplicationUse(v))();}}
function renderCsvOwnerReview(v,run,release,metadataOnly=false){
 const rid=v.selected;if(!rid)return;
 $('csv-owner-review')?.remove();
 const connection=identityConnectionGeneration,workspace=workspaceSelectionGeneration,read=v.readGeneration;
 const principal=v.principal||v.instance?.principal_id;
 const view={csv:true,spec:true,principal,project:v.project,iid:v.id,app:v.appId,rid,state:null,busy:false};csvOwnerView=view;
 const node=document.createElement('section');node.id='csv-owner-review';
 const current=()=>csvOwnerView===view&&node.isConnected&&applicationUseCurrent(v)&&v.selected===rid&&v.readGeneration===read&&connection===identityConnectionGeneration&&workspace===workspaceSelectionGeneration&&!$('apps').hidden;
 const key=JSON.stringify([v.identity,v.project,v.id,rid]),pending=()=>csvOwnerIntents.get(key);
 const endpoint=`/api/internal/instances/${v.id}/runs/${rid}/csv-owner-review`;
 const title=document.createElement('h3');title.textContent='此Run的本人适用范围声明 · 仅求和，不含MD';
 const status=document.createElement('p');status.id='csv-owner-status';status.setAttribute('role','status');
 const body=document.createElement('div');body.id='csv-owner-body';let generation=0;
 function button(id,label,fn){const b=document.createElement('button');b.type='button';b.id=id;b.textContent=label;b.onclick=safe(fn);return b;}
 const readButton=button('csv-owner-read','读取此Run当前声明及精确证据',()=>load());
 const recover=button('csv-owner-recover','只读恢复原key回执',()=>load(pending()?.body.request_key));
 const retryAck=document.createElement('input');retryAck.type='checkbox';retryAck.id='csv-owner-retry-ack';
 const retryLabel=document.createElement('label');retryLabel.append(retryAck,'核对原请求，明确只重试原key原声明');
 const retry=button('csv-owner-retry','明确重试原声明',()=>send(null,null,true));retryAck.onchange=controls;
 function controls(){const p=pending();if(p)p.renderCurrent=()=>{if(current())controls();};readButton.disabled=view.busy;recover.hidden=!p;recover.disabled=view.busy;retry.hidden=!p||p.state!=='unknown';retryLabel.hidden=retry.hidden;retry.disabled=view.busy||!retryAck.checked;}
 function forget(p){if(pending()===p)csvOwnerIntents.delete(key);}
 async function verify(state,requestKey=null){
  if(!view.principal)view.principal=state.principal_id;
  if(!await ownerValidate(view,state,requestKey,current))return false;
  if(state.full_md_report_included!==false||state.semantic_goal_acceptance!=='NOT_RUN')throw Error('VERSION_CONFLICT');
  if(state.content_access){const c=state.current;if(metadataOnly)throw Error('请重新打开完整实例与Run，再读取精确证据。');
   if(c.run_id!==rid||c.release_id!==release.id||c.release_fingerprint!==release.fingerprint||c.result_version!==run.result_version||goalRunCanonical(c.output)!==goalRunCanonical(run.result)||c.prospective?.scope!=='SUM_ONLY_WITHOUT_MD'||c.full_md_report_included!==false)throw Error('VERSION_CONFLICT');}
  return current();
 }
 function render(state){if(!current())return;view.state=state;body.replaceChildren();status.textContent=`本人适用范围声明：${state.owner_acceptance} · 目标语义 NOT_RUN / UNKNOWN · 不含MD，发布关闭${state.invalidation_reason?' · '+state.invalidation_reason:''}`;
  const history=document.createElement('pre');history.id='csv-owner-history';history.textContent=JSON.stringify({history:state.history,recovered:state.recovered?{id:state.recovered.id,request_key:state.recovered.request_key,status:state.recovered.status}:null},null,2);body.append(history);
  if(!state.content_access)csvOwnerRedact(v);
  if(pending()){status.textContent+='；请先恢复原key。';controls();return;}
  const last=state.latest;
  if(state.content_access){const proof=document.createElement('pre');proof.id='csv-owner-proof';proof.textContent=JSON.stringify(state.current,null,2);body.append(proof);
   if(state.record?.kind==='DECIDE'){const result=document.createElement('pre');result.id='csv-owner-declaration';result.textContent=JSON.stringify(state.record.payload.choices,null,2);body.append(result);}
   if(state.owner_acceptance==='PENDING'&&state.record?.kind==='PREPARE'){
    const form=document.createElement('form');form.id='csv-owner-form';const fields=[];
    for(const item of state.current.items){const label=document.createElement('label');label.textContent=item.text;const select=document.createElement('select');select.required=true;select.dataset.item=item.id;select.append(new Option('请本人逐项选择',''),new Option('接受','ACCEPT'),new Option('拒绝','REJECT'));const reason=document.createElement('textarea');reason.required=true;reason.maxLength=500;reason.dataset.reason=item.id;label.append(select,reason);form.append(label);fields.push({item,select,reason});}
    const ack=document.createElement('input');ack.type='checkbox';ack.id='csv-owner-ack';const label=document.createElement('label');label.append(ack,'本人已核对精确Release、Run、材料、列、结果版本及逐项理由；只提交求和适用范围声明，不接受原MD合同。');
    const submit=document.createElement('button');submit.id='csv-owner-decide';submit.textContent='提交此Run的逐项声明';submit.disabled=true;ack.onchange=()=>{submit.disabled=!ack.checked||view.busy;};form.append(label,submit);
    form.onsubmit=safe(async()=>{if(!current()||view.busy||!ack.checked||!form.reportValidity()||fields.some(f=>!f.reason.value.trim()))return;await send({command:'DECIDE',review_id:state.record.id,review_fingerprint:state.record.fingerprint,choices:fields.map(f=>({item_id:f.item.id,decision:f.select.value,reason:f.reason.value})),expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);});body.append(form);
   }else if(!last||['CANCEL','REVOKE'].includes(last.kind)||state.owner_acceptance==='EXPIRED')body.append(button('csv-owner-prepare','准备此精确结果的逐项声明（15分钟）',async()=>{if(current()&&!view.busy)await send({command:'PREPARE',expected_contract_fingerprint:await ownerHash(state.current),expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);}));
  }
  if(last&&['PREPARE','DECIDE'].includes(last.kind)){const reason=document.createElement('input');reason.id='csv-owner-stop-reason';reason.maxLength=500;reason.placeholder='停止理由';const ack=document.createElement('input');ack.type='checkbox';ack.id='csv-owner-stop-ack';const label=document.createElement('label');label.append(ack,'明确停止此精确声明，历史保留');body.append(reason,label,button('csv-owner-stop',last.kind==='PREPARE'?'取消待声明':'撤回本人声明',async()=>{if(current()&&!view.busy&&ack.checked&&reason.value.trim())await send({command:last.kind==='PREPARE'?'CANCEL':'REVOKE',target_id:last.id,target_fingerprint:last.fingerprint,reason:reason.value,expected_sequence:state.sequence,request_key:crypto.randomUUID()},state);}));}
  controls();
 }
 async function load(requestKey=null){if(!current()||view.busy)return;view.busy=true;const g=++generation;controls();
  try{const state=await api(endpoint+(requestKey?'?request_key='+encodeURIComponent(requestKey):''));if(!current()||g!==generation||!await verify(state,requestKey))return;
   if(requestKey){const p=pending();if(!p||state.recovered?.request_key!==p.body.request_key||state.recovered.request_fingerprint!==await ownerHash(p.body))throw Error('VERSION_CONFLICT');if(!current()||g!==generation||pending()!==p)return;forget(p);}render(state);
  }catch(error){if(current()&&g===generation){body.replaceChildren();if(error.httpStatus===403)csvOwnerRedact(v);status.textContent=`声明读取未确认：${error.message}。不自动提交。`;}}
  finally{view.busy=false;if(current())controls();}
 }
 async function send(intent,expected,replay=false){if(!current()||view.busy||(!replay&&pending()))return;let p=pending();if(replay){if(!p||p.state!=='unknown'||!retryAck.checked)return;intent=p.body;}else{p={body:structuredClone(intent),principal:expected.principal_id,project:expected.project_id,state:'checking'};csvOwnerIntents.set(key,p);}
  view.busy=true;generation++;controls();body.querySelectorAll('button,input,select,textarea').forEach(e=>e.disabled=true);
  try{if(!replay){const fresh=await api(endpoint);if(!current()){forget(p);return;}if(!await verify(fresh))return;if(fresh.sequence!==expected.sequence||goalRunCanonical(fresh.current)!==goalRunCanonical(expected.current)||fresh.record?.fingerprint!==expected.record?.fingerprint){render(fresh);throw Error('VERSION_CONFLICT');}}
   if(!current())return;p.state='sending';const receipt=await api(endpoint+'-requests','POST',p.body);
   if(receipt.formal_publication_enabled!==false||!ownerScope(view,receipt.record)||receipt.record.run_id!==rid||receipt.record.request_fingerprint!==await ownerHash(p.body))throw Error('VERIFICATION_FAILED');forget(p);if(current()){view.busy=false;await load();}
  }catch(error){if(p.state==='checking')forget(p);else{const proof=error.submissionRejection,hash=await ownerHash(p.body);const rejected=proof?.namespace==='csv-owner-submission-rejection.v1'&&proof.principal_id===p.principal&&proof.project_id===p.project&&proof.instance_id===v.id&&proof.run_id===rid&&proof.request_key===p.body.request_key&&proof.request_fingerprint===hash&&proof.acceptance==='NOT_ACCEPTED'&&proof.previous_request==='ABSENT'&&proof.phase==='TRANSACTION_ROLLED_BACK';p.state=rejected?'rejected':'unknown';if(rejected)forget(p);}
   if(current()){body.replaceChildren();if(error.httpStatus===403)csvOwnerRedact(v);status.textContent=`声明未确认：${error.message}；原请求未知时仅恢复原key。`;}
  }finally{if(p.state==='checking')forget(p);view.busy=false;if(current())controls();else if(pending()===p)p.renderCurrent?.();}
 }
 node.append(title,readButton,recover,retryLabel,retry,body,status);$('use-acceptance').append(node);controls();status.textContent=pending()?'原声明请求待恢复，不会自动重发。':'请先读取证据；旧Run未事前冻结范围时不能补签。';
}
