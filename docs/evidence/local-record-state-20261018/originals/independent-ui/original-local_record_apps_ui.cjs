'use strict';
// UI-author qualification using actual served assets and ASGI HTTP via Python IPC.
// Synthetic inputs/NoModel Worker only. Controlled response delivery is explicit.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),actions=[],static_resource_loads=[],checks=[],run_ids=[],request_keys=[];
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
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};actions.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response_text=r.text;
   if(hold&&request.method==='GET'&&path===hold.path&&--hold.remaining===0){hold=null;request.controlled_delivery='HELD_AFTER_ACTUAL_HTTP';await new Promise(resolve=>{releaseRead=resolve;});}
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
 if(version===2)record_b=state.records.find(r=>r.title===info.title_b).record_id;
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
(async()=>{
 let status='FAIL',error;
 try{await boot();if(info.scenario==='navigation')await navigation();else await flow();status='PASS';}
 catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,scenario:info.scenario,checks,actions,static_resource_loads,boots,app_id,release_id,instance_id,run_ids,request_keys,first_history,
   classification:info.scenario==='navigation'?'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_NAVIGATION_NO_WORKER':'ACTUAL_HTTP_JSDOM_LOCAL_RECORD_FLOW',qualification_role:'UI_AUTHOR',scope:'Actual served JavaScript and ASGI HTTP; only receipt delivery is controlled, synthetic typed inputs and NoModel Worker',native_browser:'NOT_RUN',pg:'NOT_RUN',real_model:'NOT_RUN',real_semantic_acceptance:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
