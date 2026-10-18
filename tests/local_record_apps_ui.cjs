'use strict';
// UI-author qualification using actual served assets and ASGI HTTP via Python IPC.
// Synthetic inputs/NoModel Worker only. Controlled response delivery is explicit.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),actions=[],static_resource_loads=[],checks=[],run_ids=[],request_keys=[];
const downloads=[];
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null,lose=null,app_id=info.app||null,instance_id=info.instance||info.iid||null,release_id=info.release||null,first_history=null,record_a=null,record_b=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+20000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
const visible=el=>{if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;};
async function click(value,double=false){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();if(double)el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
function input(id,value){$(id).value=value;$(id).dispatchEvent(new w.Event('input',{bubbles:true}));}
function ack(id){$(id).checked=true;$(id).dispatchEvent(new w.Event('change',{bubbles:true}));}
async function select(id,value){$(id).value=value;assert.equal($(id).value,value,'existing explicit option '+id);if(typeof $(id).onchange==='function')await $(id).onchange(new w.Event('change'));else $(id).dispatchEvent(new w.Event('change',{bubbles:true}));}
const posts=()=>actions.filter(r=>r.method==='POST');
const entry=()=>$('use-list').querySelector(`[data-use-family="LOCAL_RECORDS"][data-app-id="${app_id}"] button`);
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
const view=()=>w.eval('localRecordsView');
const base=()=>`/api/internal/record-instances/${instance_id}`;
const original=key=>base()+'/record-requests/'+encodeURIComponent(key);
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);static_resource_loads.push({boot:boots,status:r.status,path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 if(['collection-export','private-preview'].includes(info.scenario)){
  const blobs=new Map();w.Blob=Blob;
  w.URL.createObjectURL=blob=>{const url='blob:synthetic-test-'+crypto.randomUUID();blobs.set(url,{blob,url,revoked:false});return url;};
  w.URL.revokeObjectURL=url=>{const value=blobs.get(url);assert(value);value.revoked=true;blobs.delete(url);};
  const originalClick=w.HTMLAnchorElement.prototype.click;
  w.HTMLAnchorElement.prototype.click=function(){const value=blobs.get(this.href);if(this.download&&value){value.filename=this.download;downloads.push(value);}else originalClick.call(this);};
 }
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};actions.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response_text=r.text;
   if(hold&&request.method===(hold.method||'GET')&&path===hold.path&&--hold.remaining===0){hold=null;request.controlled_delivery='HELD_AFTER_ACTUAL_HTTP';await new Promise(resolve=>{releaseRead=resolve;});}
   if(lose&&request.method==='POST'&&path===lose.path){lose=null;request.controlled_delivery='RECEIPT_LOST_AFTER_ACTUAL_HTTP';throw new TypeError('controlled accepted receipt loss after actual HTTP');}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');if($('project-select').value!==info.project)await select('project-select',info.project);await nav('apps');
 check(visible($('local-records-new')),'Apps visibly offers new local record app entry');
}
async function open(iid=instance_id){
 await wait(()=>!!entry(),'local record directory entry');const n=posts().length;await click(entry());
 check(view()?.app?.id===app_id&&visible($('local-records-panel'))&&!w.eval('engineering'),'directory opens dedicated verified local-record controller');
 await select('local-records-instance-select',iid);check(view().instance?.id===iid,'explicit selected local-record instance is read through family API');check(posts().length===n,'app/instance opening performs only GET');
}
async function createLifecycle(){
 check(posts().length===0,'cold discovery creates no app, version, instance or Run');await click('local-records-new');input('local-records-name',info.app_name);input('local-records-goal',info.goal);ack('local-records-create-ack');
 let n=posts().length;await click('local-records-save-app',true);const saved=posts().at(-1);assert.equal(saved.status,201,saved.response_text);app_id=JSON.parse(saved.response_text).id;
 check(posts().length===n+1&&saved.path===`/api/projects/${info.project}/record-apps`&&view().savedApp?.id===app_id,'double click saves exactly one explicit fixed typed-form app');
 check(!view().app&&!view().instance&&view().savedApp.input_guidance.mode==='LOCAL_RECORDS','saving app does not automatically open or create delivery state');
 n=posts().length;await click('local-records-open-saved-app');check(posts().length===n&&view().app?.id===app_id,'separate explicit open reauthorizes the saved app without writes');
 n=posts().length;await click('local-records-release-prepare',true);const prepared=posts().at(-1);assert.equal(prepared.status,201,prepared.response_text);
 check(posts().length===n+1&&prepared.path===`/api/apps/${app_id}/record-release-approvals`&&!view().approval.release,'explicit prepare freezes one exact Release approval and creates no Release');
 check($('local-records-release-commit').disabled&&!$('local-records-release-ack').checked,'Release commit requires a separate fresh acknowledgement');
 ack('local-records-release-ack');n=posts().length;await click('local-records-release-commit',true);const committed=posts().at(-1);assert.equal(committed.status,200,committed.response_text);release_id=JSON.parse(committed.response_text).release.id;
 check(posts().length===n+1&&committed.path.endsWith('/commit')&&view().approval.release.id===release_id,'separate double click commits one exact internal Release');
 n=posts().length;await click('local-records-delivery-read');check(posts().length===n,'explicit delivery refresh is read-only');await select('local-records-release-select',release_id);ack('local-records-instance-ack');
 n=posts().length;await click('local-records-instance-create',true);const made=posts().at(-1);assert.equal(made.status,201,made.response_text);instance_id=JSON.parse(made.response_text).instance.id;
 check(posts().length===n+1&&made.path===`/api/internal/record-releases/${release_id}/instances`&&!view().instance,'explicit create saves one empty independent instance without auto-selecting it');
 await click('local-records-delivery-read');await select('local-records-instance-select',instance_id);
 check(view().instance.id===instance_id&&view().instance.data_version===0&&view().instance.records.length===0,'explicit selection reads the actual empty collection at version zero');
}
async function write(command,version,lost=false){
 await select('local-records-command',command);
 if(command==='CREATE'){input('local-records-title',version===1?info.title_a:info.title_b);input('local-records-details',version===1?info.details_a:info.details_b);}
 else{await select('local-records-record-select',record_a);input('local-records-reason',info.done_reason);}
 let n=posts().length;await click('local-records-preview',true);const post=posts().at(-1),prepared=JSON.parse(post.response_text);assert.equal(post.status,201,post.response_text);
 check(posts().length===n+1&&post.path===base()+'/previews'&&!prepared.run,'double click creates one immutable preview without a business Run');
 const event=prepared.preview.event,key=prepared.request_key;request_keys.push(key);
 check(prepared.preview.input.command===command&&prepared.preview.input.expected_data_version===version-1&&event.collection_version===version,'exact typed request and proposed event bind the existing data version');
 if(command==='CREATE')check(event.state==='OPEN'&&event.record_revision===1&&event.title===(version===1?info.title_a:info.title_b)&&event.details===(version===1?info.details_a:info.details_b),'CREATE preview preserves full user title/details and proposes OPEN revision one');
 else check(event.record_id===record_a&&event.record_revision===2&&event.state==='DONE'&&event.title===info.title_a&&event.details===info.details_a&&event.reason===info.done_reason,'SET_STATE preview targets stable A, preserves fields and includes explicit DONE reason');
 check($('local-records-confirm').disabled&&!$('local-records-run-ack').checked,'preview never automatically confirms a write');
 ack('local-records-run-ack');n=posts().length;const offset=actions.length;if(lost)lose={path:base()+'/previews/'+encodeURIComponent(key)+'/commit'};await click('local-records-confirm',true);
 const accepted=posts().at(-1);assert.equal(accepted.status,202,accepted.response_text);
 check(posts().length===n+1&&accepted.path===base()+'/previews/'+encodeURIComponent(key)+'/commit','separate double click accepts exactly one original-key write Run');
 if(lost){
  check($('local-records-recovery-key').value===key&&$('local-records-recovery-stage').value==='RUN'&&$('local-records-confirm').disabled&&w.eval('localRecordsIntents.size')>0,'lost accepted write receipt retains its original key and blocks another submission');
  check(!actions.slice(offset).some(r=>r.method==='GET'),'unknown acceptance causes no automatic retry or read');
  n=posts().length;await click('local-records-recover');check(posts().length===n&&actions.at(-1).method==='GET'&&actions.at(-1).path===original(key),'explicit recovery only GETs the exact original key');
 }
 const rid=view().acceptedRun?.run_id;assert(rid);run_ids.push(rid);
 check(view().runSelect.value===rid&&$('local-records-run-status').textContent.includes(rid)&&!view().run,'accepted receipt selects the same Run without claiming an executed result');
 check(!actions.slice(offset).some(r=>r.method==='GET'&&r.path.endsWith('/runs/'+rid)),'acceptance does not automatically poll the Run');
 await click('local-records-refresh');check(view().run?.id===rid&&view().run.status==='QUEUED'&&view().instance.data_version===version-1,'manual pre-Worker read proves original Run is queued and creates no projected event');
 const worked=await rpc({command:'worker',run:rid});assert.equal(worked.status,200,worked.text);await click('local-records-refresh');
 const state=view().instance,run=view().run;check(run.id===rid&&run.status==='SUCCEEDED'&&run.result_version===version&&state.data_version===version,'normal NoModel Worker commits one exact event and manual refresh reads the same successful Run');
 check(run.output.resource_id&&run.output.hash&&run.receipt.status==='VERIFIED'&&JSON.stringify(run.receipt.data)===JSON.stringify(run.output),'actual tool output remains the independently verified JSON artifact reference');
 check(state.history.length===version&&state.history.at(-1).run_id===rid&&JSON.stringify(state.history.at(-1).event)===JSON.stringify(run.event),'current collection and immutable history bind the same Run event');
 if(version===1){record_a=state.records.find(r=>r.title===info.title_a).record_id;first_history=JSON.parse(JSON.stringify(state.history[0]));}
 if(version===2&&command==='CREATE')record_b=state.records.find(r=>r.title===info.title_b).record_id;
 if(version>1)check(JSON.stringify(state.history[0])===JSON.stringify(first_history),'subsequent writes preserve the entire original event and artifact history row');
 return state;
}
async function flow(){
 await createLifecycle();await write('CREATE',1,true);await write('CREATE',2);const state=await write('SET_STATE',3);
 check(record_a!==record_b&&state.records.length===2,'independent created records retain different stable identities');
 const a=state.records.find(r=>r.record_id===record_a),b=state.records.find(r=>r.record_id===record_b);
 check(a.state==='DONE'&&a.record_revision===2&&a.title===info.title_a&&a.details===info.details_a&&b.state==='OPEN'&&b.record_revision===1&&b.title===info.title_b&&b.details===info.details_b,'current projection is A DONE@2 and unchanged B OPEN@1');
 let n=posts().length;await click($('local-records-current').querySelector(`[data-record-id="${record_a}"] button`));
 check(posts().length===n&&$('local-records-history').children.length===2&&$('local-records-history').textContent.includes(info.done_reason)&&$('local-records-history').textContent.includes('OPEN')&&$('local-records-history').textContent.includes('DONE'),'A history is reauthorized read-only and shows both immutable full states and the change reason');
 check(!$('local-records-history').textContent.includes(info.title_b),'selected A history does not borrow B events');
 const beforeCold=posts().length;await boot();await open();
 check(posts().length===beforeCold&&view().instance.data_version===3&&view().instance.records.find(r=>r.record_id===record_a).state==='DONE'&&view().instance.records.find(r=>r.record_id===record_b).state==='OPEN','cold page reaches persisted independent current records without writes');
 check(JSON.stringify(view().instance.history[0])===JSON.stringify(first_history)&&run_ids.every(id=>[...$('local-records-run-select').options].some(o=>o.value===id)),'cold history retains exact first event and all three original Runs');
 await select('local-records-run-select',run_ids[0]);await click('local-records-run-read');
 check(view().run.id===run_ids[0]&&view().run.event.state==='OPEN'&&view().run.result_version===1&&view().instance.records.find(r=>r.record_id===record_a).state==='DONE','opening old same-Run result preserves its OPEN event beside the separately current DONE record');
 await select('local-records-recovery-stage','RUN');input('local-records-recovery-key',request_keys[0]);n=posts().length;await click('local-records-recover');
 check(posts().length===n&&view().acceptedRun.run_id===run_ids[0]&&JSON.parse($('local-records-recovery-proof').textContent).request_key===request_keys[0],'cold original-key GET recovers the original write without creating a new Run');
 check(posts().filter(r=>r.path===`/api/projects/${info.project}/record-apps`).length===1&&posts().filter(r=>r.path.endsWith('/record-release-approvals')).length===1&&posts().filter(r=>r.path.includes('/record-release-requests/')&&r.path.endsWith('/commit')).length===1&&posts().filter(r=>r.path===`/api/internal/record-releases/${release_id}/instances`).length===1&&posts().filter(r=>r.path===base()+'/previews').length===3&&posts().filter(r=>r.path.includes('/previews/')&&r.path.endsWith('/commit')).length===3,'all page writes are bounded to explicit app, Release, instance and three preview/confirm pairs');
}
async function privatePreview(){
 await open();const business=instance_id;check(view().instance.records[0].title==='Synthetic business anchor A','existing real business A is present before private creation');
 await select('local-records-release-select',release_id);check($('local-records-private-create').disabled,'private creation requires its separate positive acknowledgement');ack('local-records-instance-ack');check($('local-records-private-create').disabled,'business acknowledgement does not authorize private creation');ack('local-records-private-ack');
 let n=posts().length;lose={path:`/api/internal/record-releases/${release_id}/private-previews`};await click('local-records-private-create',true);const made=posts().at(-1);assert.equal(made.status,201,made.response_text);const reply=JSON.parse(made.response_text);instance_id=reply.instance.id;
 check(posts().length===n+1&&made.path.endsWith('/private-previews')&&view().selectedIid===business&&!view().instance,'lost explicit creation keeps business selection, clears unverified body and does not auto-select private space');
 check(!view().recoveryProof.textContent.includes(instance_id)&&$('local-records-recovery-stage').value==='CREATE_PRIVATE'&&$('local-records-private-create').disabled,'lost actual creation receipt preserves UNKNOWN original key and does not install unverified space');
 const originalKey=made.body.request_key;await select('local-records-instance-select',info.second_instance);check(!$('local-records-private-ack').checked&&$('local-records-recovery-key').value===originalKey,'switching existing business instance clears consent and retains App-scoped private original key');check($('local-records-private-ack').disabled&&$('local-records-private-create').disabled&&posts().length===n+1,'UNKNOWN private creation locks consent and cannot issue a fresh key from another selected instance');
 const recoveryOffset=actions.length;await click('local-records-recover');check(actions.slice(recoveryOffset).length===1&&actions.at(-1).method==='GET'&&actions.at(-1).path.endsWith('/private-preview-requests/'+originalKey)&&posts().length===n+1,'explicit original-key GET recovers the actual created space without a second POST');check(JSON.parse($('local-records-recovery-proof').textContent).instance.id===instance_id,'recovered exact creation receipt identifies the original private space');
 check(reply.execution_namespace==='local-record-private-preview.v1'&&made.body.consent==='CREATE_PRIVATE_WRITE_PREVIEW_NO_BUSINESS_PROMOTION','private creation receipt binds the exact separate consent and namespace');
 await click('local-records-delivery-read');check(view().delivery.instances.every(i=>!i.preview_scope)&&view().delivery.preview_instances.length===1,'server catalog keeps private spaces out of business list');
 check([...$('local-records-instance-select').querySelectorAll('optgroup')].map(g=>g.label).join('|')==='业务实例|PREVIEW 私有试写','visible catalog separates business and PREVIEW groups');
 await select('local-records-instance-select',instance_id);await write('CREATE',1);await write('SET_STATE',2);
 check($('local-records-instance-info').textContent.includes('PREVIEW')&&$('local-records-run-status').textContent.includes('PREVIEW')&&$('local-records-confirm').textContent.includes('PREVIEW'),'current instance, Run and confirmation consistently identify PREVIEW');
 await click($('local-records-current').querySelector('article button'));check($('local-records-history').textContent.includes('PREVIEW')&&$('local-records-history').children.length===2,'both immutable record histories identify private trial origin');
 const checkpoint=await rpc({command:'checkpoint_private',instance:instance_id,runs:run_ids});assert.equal(checkpoint.status,200,checkpoint.text);
 n=posts().length;await boot();await open();check(posts().length===n&&view().instance.data_version===2&&view().instance.records[0].state==='DONE'&&view().instance.records[0].record_revision===2,'cold page reopens actual persisted private DONE@2 without writes');
 await select('local-records-run-select',run_ids[0]);await click('local-records-run-read');check(view().run.id===run_ids[0]&&view().run.event.state==='OPEN'&&view().instance.records[0].state==='DONE','same original private Run retains OPEN beside current DONE');
 await click('local-records-export');check(downloads.length===1&&$('local-records-export-status').textContent.includes('PREVIEW'),'private collection export is visible and explicitly labeled PREVIEW');
 await held(base(),()=>click('local-records-refresh'),async()=>{input('local-records-title','must not copy');input('local-records-details','must not copy private body');await select('local-records-instance-select',business);},'private late callback versus business selection');
 check(view().instance.id===business&&view().instance.records[0].title==='Synthetic business anchor A'&&!$('local-records-title').value&&!$('local-records-details').value&&!$('local-records-run-ack').checked&&!view().preview,'business selection clears private inputs, acknowledgements and pending preview');
 await select('local-records-instance-select',instance_id);
 await held(base(),()=>click('local-records-refresh'),async()=>{await nav('resources');await nav('apps');},'private workspace ABA');await open();
 await held(base(),()=>click('local-records-refresh'),async()=>{await select('project-select',info.other);await select('project-select',info.project);await nav('apps');},'private project ABA');await open();
 await held(base(),()=>click('local-records-refresh'),async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');await nav('apps');},'private same-account reconnect');await open();
 await nav('projects');const detail=[...$('runs').querySelectorAll('button')].find(b=>b.closest('.row').textContent.includes(run_ids[0].slice(0,16)));check(detail.closest('.row').textContent.includes('PREVIEW'),'project history metadata labels private Run PREVIEW');await click(detail);check($('result').textContent.includes('PREVIEW'),'project same-Run detail labels private result PREVIEW');await click('local-record-task-open-result');check(view().instance.id===instance_id&&view().run.id===run_ids[0]&&$('local-records-run-status').textContent.includes('PREVIEW'),'project result navigation returns to the exact private instance and Run');
 await select('local-records-instance-select',business);input('local-records-title','Synthetic explicitly submitted business C');input('local-records-details','Separate freshly entered business body');n=posts().length;await click('local-records-preview');check(posts().length===n+1&&view().instance.data_version===1&&!view().preview.run,'business write requires a fresh ordinary preview after explicit business selection');ack('local-records-run-ack');await click('local-records-confirm',true);const rid=view().acceptedRun.run_id;const work=await rpc({command:'worker',run:rid});assert.equal(work.status,200,work.text);await click('local-records-refresh');check(view().run.id===rid&&view().run.status==='SUCCEEDED'&&!view().run.preview_scope&&view().instance.data_version===2&&view().instance.records.length===2,'explicit new ordinary Run writes business C through original writer');
 const end=await rpc({command:'checkpoint_business',instance:business,run:rid});assert.equal(end.status,200,end.text);
 await select('local-records-instance-select',instance_id);input('local-records-title','Synthetic private queued stop');input('local-records-details','Must clear on revocation');await click('local-records-preview');ack('local-records-run-ack');await click('local-records-confirm');const stopRun=view().acceptedRun.run_id;
 const revoked=await rpc({command:'revoke_private_write',instance:instance_id,run:stopRun});assert.equal(revoked.status,200,revoked.text);const offset=actions.length;await click('local-records-refresh');
 check(actions.slice(offset).length===1&&actions.at(-1).status===403&&!view().instance&&!view().run&&!$('local-records-title').value&&!$('local-records-details').value&&!$('local-records-current').textContent&&!$('local-records-run-proof').textContent,'WRITE revocation performs one denied read and clears private form/result without automatic requests');
 check(view().metadataTarget.run_id===stopRun&&$('local-records-run-select').value===stopRun&&!$('local-records-private-control-read').disabled&&$('local-records-cancel').disabled,'denial preserves only the verified exact private stop target, pending explicit fresh metadata read');
 await click('local-records-private-control-read');check(actions.at(-1).path===base()+'/runs/'+stopRun+'/private-control-status'&&actions.at(-1).status===200&&!view().instance&&view().control.metadataOnly&&!$('local-records-cancel').disabled&&$('local-records-pause').disabled&&$('local-records-resume').disabled,'explicit owner metadata GET allows only cancellation with fresh version, without restoring private body');
 n=posts().length;await click('local-records-cancel',true);check(posts().length===n+1&&posts().at(-1).body.command==='cancel'&&posts().at(-1).status===200&&$('local-records-run-status').textContent.includes('PREVIEW')&&$('local-records-run-status').textContent.includes('CANCELLED'),'separate double click cancels the same queued private Run exactly once after revocation');
 const final=await rpc({command:'checkpoint_cancelled',run:stopRun});assert.equal(final.status,200,final.text);

}
async function held(path,start,change,label){
 const n=posts().length;hold={path,remaining:1};const opening=start();await wait(()=>!!releaseRead,'held '+label);await change();const status=$('local-records-status')?.textContent,collection=$('local-records-current')?.textContent,run=$('local-records-run-status')?.textContent;
 const release=releaseRead;releaseRead=null;release();await opening;
 check($('local-records-status')?.textContent===status&&$('local-records-current')?.textContent===collection&&$('local-records-run-status')?.textContent===run,label+' rejects late actual HTTP response without changing current visible state');check(posts().length===n,label+' performs zero POST');
}
async function navigation(){
 await open();check(view().instance.records.length===1&&view().instance.records[0].state==='OPEN','real fixture seed is read through the dedicated family with zero page Worker');
 await held(base(),()=>click('local-records-refresh'),async()=>{await select('local-records-instance-select',info.second_instance);},'instance selection');
 check(view().instance.id===info.second_instance&&view().instance.records.length===0&&!$('local-records-current').textContent.includes(info.title_a),'second empty instance cannot inherit A from the delayed first read');
 await select('local-records-instance-select',instance_id);await select('local-records-run-select',info.seed_run);
 await held(base()+'/runs/'+info.seed_run,()=>click('local-records-run-read'),async()=>{await select('local-records-run-select','');},'Run deselection');
 check(!view().run&&!$('local-records-run-proof').textContent,'Run deselection clears old result and proof');
 await select('local-records-recovery-stage','RUN');input('local-records-recovery-key',info.seed_request_key);
 await held(original(info.seed_request_key),()=>click('local-records-recover'),async()=>{await select('local-records-instance-select',info.second_instance);},'original-key recovery versus instance selection');
 check(view().instance.id===info.second_instance&&!$('local-records-recovery-proof').textContent&&!$('local-records-recovery-key').value,'late original-key response cannot restore another instance body or key');
 await select('local-records-instance-select',instance_id);
 await held(base(),()=>click('local-records-refresh'),async()=>{await nav('resources');await nav('apps');},'workspace ABA');
 check(!view()&&!$('local-records-panel').textContent,'workspace change clears the local-record view');
 await open();await held(base(),()=>click('local-records-refresh'),async()=>{await click('local-records-new');},'app selection to a new typed-form draft');
 check(view()&&!view().app&&!view().instance&&!$('local-records-current').textContent,'new app selection cannot receive old instance content');
 await open();await held(base(),()=>click('local-records-refresh'),async()=>{await select('project-select',info.other);await select('project-select',info.project);},'project ABA');
 check(!view()&&!$('local-records-panel').textContent,'project change clears all prior record content');
 await open();await held(base(),()=>click('local-records-refresh'),async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');await nav('apps');},'same-account reconnect');
 check(!view()&&!$('local-records-panel').textContent,'same-account reconnect cannot restore old account-view contents');
 check(posts().length===0,'all actual HTTP navigation and recovery races create zero writes');
}
async function collectionExport(){
 await open();check(downloads.length===0&&view().instance.data_version===3,'opening a real collection never downloads or treats its queued write as saved');
 await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(view().run.result_version===1&&view().instance.data_version===3,'selected historical Run remains version one beside the current collection at version three');
 let n=actions.length;await click('local-records-export',true);
 check(downloads.length===1&&actions.slice(n).length===1&&actions.at(-1).path===base()&&actions.at(-1).method==='GET','double click downloads one file after one fresh current-instance authorization read');
 const value=JSON.parse(await downloads[0].blob.text()),a=value.records.find(r=>r.title===info.title_a),b=value.records.find(r=>r.title===info.title_b);
 check(value.namespace==='local-record-collection-snapshot.v1'&&value.snapshot_kind==='OBSERVED_COMMITTED_COLLECTION'&&value.app_id===app_id&&value.instance_id===instance_id&&value.project_id===info.project&&value.release_id===release_id&&value.data_version===3,'actual JSON Blob binds original app instance project Release and current collection version');
 check(a.state==='DONE'&&a.record_revision===2&&a.details===info.details_a&&b.state==='OPEN'&&b.record_revision===1&&b.details===info.details_b&&a.record_id!==b.record_id,'portable snapshot contains independently current A DONE and unchanged B OPEN');
 check(value.records.length===2&&value.history.length===3&&value.history[0].run_id===info.seed_run&&value.history.at(-1).event.reason===info.done_reason,'snapshot preserves immutable event provenance rather than exporting only the selected old Run');
 check(!('runs' in value)&&!('request_key' in value)&&!('runtime_id' in value)&&!(await downloads[0].blob.text()).includes(info.pending_title),'file excludes queued writes controller state keys runtime identity and other non-whitelisted fields');
 check(downloads[0].revoked&&downloads[0].filename===`local-records-${instance_id}-v3.json`&&view().run.result_version===1,'download filename identifies the snapshot version object URL is released and selected Run is unchanged');
 await boot();await open();await click('local-records-export');
 check(downloads.length===2&&(await downloads[1].blob.text())===(await downloads[0].blob.text()),'cold page exports the same persisted collection with deterministic UTF-8 bytes');
 n=downloads.length;await held(base(),()=>click('local-records-export'),async()=>{await select('local-records-instance-select',info.second_instance);},'collection download versus newer instance');
 check(downloads.length===n&&view().instance.id===info.second_instance&&!$('local-records-export-status').textContent,'late verified collection cannot download or repaint after a different instance is selected');
 await select('local-records-instance-select',instance_id);
 const revoked=await rpc({command:'revoke_seed_artifact_read',run:info.seed_run,resource:info.seed_artifact});assert.equal(revoked.status,200,revoked.text);
 n=actions.length;await click('local-records-export');
 check(actions.slice(n).length===1&&actions.at(-1).status===403&&downloads.length===2,'export rechecks actual current permission and a real denial creates no file or automatic request');
 check(!view().instance&&!$('local-records-current').textContent&&!$('local-records-history').textContent&&$('local-records-export').disabled&&$('local-records-export-status').textContent.includes('没有生成下载文件'),'denied export clears protected cached collection and disables stale download claims');
 check(posts().length===0,'the complete collection export page performs zero POST and invokes zero Worker');
}
async function controls(){
 await open();
 const disabled=()=>['pause','resume','cancel'].every(command=>$('local-records-'+command).disabled);
 check(disabled(),'control buttons remain disabled until the same Run is explicitly read');
 await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(view().run.id===info.seed_run&&view().run.status==='QUEUED'&&view().control.version===1,'existing typed GET verifies the original queued Run before control');
 check(!$('local-records-pause').disabled&&$('local-records-resume').disabled&&!$('local-records-cancel').disabled,'only pause and cancel are available for the verified queued Run');
 let n=posts().length;await click('local-records-pause',true);
 check(posts().length===n+1&&view().control.id===info.seed_run&&view().control.status==='PAUSED'&&view().control.version===2,'double click sends one pause at the original version and receives the same Run PAUSED at version two');
 check(!view().run&&!$('local-records-run-proof').textContent&&$('local-records-pause').disabled&&!$('local-records-resume').disabled,'metadata-only pause receipt never impersonates a full Run result and enables explicit resume');
 const path=base()+'/runs/'+info.seed_run+'/commands';n=posts().length;hold={path,method:'POST',remaining:1};const opening=click('local-records-resume',true);
 await wait(()=>!!releaseRead,'held actual resume receipt');await select('local-records-instance-select',info.second_instance);
 const status=$('local-records-control-status').textContent,collection=$('local-records-current').textContent;
 const release=releaseRead;releaseRead=null;release();await opening;
 check(posts().length===n+1&&posts().at(-1).body.command==='resume'&&posts().at(-1).body.version===2,'held resume actually advances the original Run with one versioned POST');
 check(view().instance.id===info.second_instance&&!view().control&&!view().run&&$('local-records-control-status').textContent===status&&$('local-records-current').textContent===collection&&disabled(),'late accepted control receipt cannot repaint or enable commands in the newer empty instance');
 await select('local-records-instance-select',instance_id);await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(view().run.status==='QUEUED'&&view().run.version===3&&view().control.id===info.seed_run,'explicit original-instance read finds the same resumed Run at version three');
 n=actions.length;lose={path};await click('local-records-cancel',true);
 check(actions.slice(n).length===1&&posts().length===3&&posts().at(-1).body.command==='cancel'&&posts().at(-1).body.version===3&&posts().at(-1).status===200,'cancel double click sends one actual accepted POST and lost delivery triggers no automatic request');
 check(disabled()&&!view().run&&!view().control&&$('local-records-control-status').textContent.includes('未确认')&&w.eval('[...localRecordsControlIntents.values()].some(i=>i.state==="UNKNOWN")'),'lost control receipt keeps commands locked without inventing a final state');
 n=posts().length;await click('local-records-run-read');
 check(posts().length===n&&view().run.id===info.seed_run&&view().run.status==='CANCELLED'&&view().run.version===4&&view().run.output===null&&view().run.event===null,'explicit GET reads original cancelled Run at version four without replaying control or business writes');
 check(disabled()&&w.eval('localRecordsControlIntents.size')===0&&view().instance.data_version===0&&!view().instance.records.length&&!view().instance.history.length,'fresh advanced version resolves uncertainty while terminal controls and empty collection remain truthful');
 await boot();await open();await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(posts().length===3&&view().run.status==='CANCELLED'&&view().run.version===4&&disabled(),'cold page retains the original terminal Run and never resubmits it');
 check(actions.filter(row=>row.method==='POST').every(row=>row.path===path),'page mutations are confined to three explicit controls on the one original Run');
}
async function projectHistory(){
 const detail=()=>[...$('runs').querySelectorAll('button')].find(button=>button.closest('.row').textContent.includes(info.seed_run.slice(0,16)));
 const summary=async()=>{await nav('projects');await wait(()=>!!detail(),'project history Run');await click(detail());check($('result').textContent.includes(info.title_a)&&visible($('local-record-task-open-result')),'project history reads exact typed event and exposes dedicated application entry');check(!$('commands').children.length,'typed history never offers legacy ordinary commands');};
 await summary();let n=actions.length;await click('local-record-task-open-result',true);
 check(view()?.run?.id===info.seed_run&&view().run.event.title===info.title_a&&view().run.result_version===1,'history entry opens the exact verified typed Run and event in its own instance');
 check(actions.slice(n).filter(row=>row.path===`/api/apps/${app_id}`).length===1,'double click starts only one typed application navigation');
 check(view().selectionCurrent===null,'successful history navigation releases its temporary opening fence');
 await nav('projects');await held(`/api/runs/${info.seed_run}`,()=>click(detail()),async()=>{await nav('resources');await nav('projects');},'typed history detail workspace ABA');
 check(!$('result').textContent.includes(info.title_a),'late typed detail does not paint after workspace reselection');
 await summary();await held(base(),()=>click('local-record-task-open-result'),async()=>{await select('local-records-instance-select',info.second_instance);},'history entry versus new instance selection');
 check(view()?.instance?.id===info.second_instance&&!view().instance.records.length&&view().selectionCurrent===null,'newer empty instance remains usable without old event or poisoned opening fence');
 await summary();n=actions.length;await held(`/api/apps/${app_id}`,()=>click('local-record-task-open-result'),async()=>{await select('project-select',info.other);await select('project-select',info.project);await nav('projects');},'history entry project ABA');
 check(!view()&&actions.slice(n).every(row=>!row.path.startsWith('/api/internal/record-instances/')),'late application read cannot follow an old project into private instance reads');
 await summary();await held(`/api/apps/${app_id}`,()=>click('local-record-task-open-result'),async()=>{await click('identity-switch');$('token').value='synthetic-test-A';await click('connect');await nav('projects');},'history entry same-account reconnect');
 check(!view()&&posts().length===0,'all typed history navigation races are read-only and isolated from a new connection');
 await summary();const revoked=await rpc({command:'revoke_seed_artifact_read',run:info.seed_run,resource:info.seed_artifact});assert.equal(revoked.status,200,revoked.text);
 await held(`/api/runs/${info.seed_run}`,()=>click(detail()),async()=>{await nav('resources');await nav('projects');$('result').textContent='CURRENT CLEAN';},'typed history late permission 403');
 check($('result').textContent==='CURRENT CLEAN'&&actions.filter(row=>row.path===`/api/runs/${info.seed_run}`).at(-1).status===403,'late actual permission denial cannot clear the current selection or paint an old error');
 check(posts().length===0,'history opening and late permission denial perform zero page POST');
}
async function revocation(){
 await open();
 await select('local-records-run-select',info.seed_run);await click('local-records-run-read');
 check(view().run?.id===info.seed_run&&view().run.status==='SUCCEEDED','seed same-Run result is genuinely re-read before revocation');
 await select('local-records-recovery-stage','RUN');input('local-records-recovery-key',info.seed_request_key);await click('local-records-recover');
 check($('local-records-current').textContent.includes(info.title_a)&&$('local-records-recovery-proof').textContent.includes(info.details_a)&&$('local-records-details').value===info.details_a,'real original-key recovery visibly restores seed body and form before denial');
 check(posts().length===0,'pre-revocation instance and original-key reads perform zero POST');
 const revoked=await rpc({command:'revoke_seed_artifact_read',run:info.seed_run,resource:info.seed_artifact});assert.equal(revoked.status,200,revoked.text);
 const cleared=label=>{
  for(const id of ['local-records-current','local-records-history','local-records-run-proof','local-records-preview-proof','local-records-preview-summary','local-records-recovery-proof'])check(!$(id).textContent,label+' clears '+id);
  for(const id of ['local-records-title','local-records-details','local-records-reason'])check(!$(id).value,label+' clears form '+id);
  check(!view().instance&&!view().preview&&!view().run&&$('local-records-confirm').disabled,label+' clears current claims and blocks confirmation');
  check($('local-records-recovery-key').value===info.seed_request_key&&$('local-records-recovery-stage').value==='RUN',label+' preserves exact original key and stage');
  check(!view().panel.textContent.includes(info.title_a)&&!view().panel.textContent.includes(info.details_a),label+' leaves no seed record text in any panel node');
 };
 let offset=actions.length;await click('local-records-refresh');
 let reads=actions.slice(offset);check(reads.length===1&&reads[0].method==='GET'&&reads[0].path===base()&&reads[0].status===403,'manual refresh receives one actual authorization 403 without automatic follow-up');cleared('refresh 403');
 offset=actions.length;await click('local-records-recover');
 reads=actions.slice(offset);check(reads.length===1&&reads[0].method==='GET'&&reads[0].path===original(info.seed_request_key)&&reads[0].status===403,'explicit original-key recovery receives actual 403 with zero automatic requests');cleared('recovery 403');
 check(posts().length===0,'the entire revocation page performs zero POST and invokes no page Worker');
}
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='navigation')await navigation();else if(info.scenario==='revocation')await revocation();else if(info.scenario==='project-history')await projectHistory();else if(info.scenario==='controls')await controls();else if(info.scenario==='private-preview')await privatePreview();else if(info.scenario==='collection-export')await collectionExport();else await flow();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  const files=await Promise.all(downloads.map(async file=>{const bytes=Buffer.from(await file.blob.arrayBuffer());return {filename:file.filename,type:file.blob.type,bytes:bytes.length,base64:bytes.toString('base64'),sha256:crypto.createHash('sha256').update(bytes).digest('hex'),revoked:file.revoked};}));
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,actions,static_resource_loads,boots,app_id,release_id,instance_id,run_ids,request_keys,first_history,downloads:files,
   classification:info.scenario==='private-preview'?'ACTUAL_HTTP_JSDOM_PRIVATE_RECORD_PREVIEW':info.scenario==='collection-export'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_CURRENT_COLLECTION_EXPORT':info.scenario==='controls'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_SAME_RUN_CONTROLS':info.scenario==='project-history'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_PROJECT_HISTORY_NO_PAGE_WORKER':info.scenario==='navigation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER':info.scenario==='revocation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_REVOCATION_NO_WORKER':'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_FLOW',qualification_role:'UI_AUTHOR',scope:'Actual served JavaScript and ASGI HTTP; only receipt delivery is controlled, synthetic typed inputs and NoModel Worker',native_browser:'NOT_RUN',pg:'NOT_RUN',real_model:'NOT_RUN',real_semantic_acceptance:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
