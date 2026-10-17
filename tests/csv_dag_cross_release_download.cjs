'use strict';
// Product page + actual ASGI HTTP via IPC. JSDOM is not native browser acceptance.
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const same=require('node:util').isDeepStrictEqual;
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],assets=[],checks=[],mutations=[];
let unknownHint=false;
let serial=0,dom,w,$,boots=0,active=0,hold=null,releaseRead=null;
const httpReplies=[],heldWaits=[];
const downloadBlobs=[],downloadAnchors=[];
let downloadMutation=null,anchorFailure=false;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(test,label)=>{const until=Date.now()+12000;while(Date.now()<until){if(test())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait: '+label);};
// Opening includes several real authorization reads. Keep the 12s no-progress
// limit while bounding the complete chain at 60s; only actual HTTP replies renew it.
const waitHeld=async label=>{
 const start=Date.now(),initial=httpReplies.length;let last=start,seen=initial;
 const record=outcome=>heldWaits.push({label,outcome,elapsed_ms:Date.now()-start,http_reply_offsets_ms:httpReplies.slice(initial).map(at=>at-start),idle_limit_ms:12000,total_limit_ms:60000});
 while(true){
  if(Date.now()-start>=60000){record('total limit');throw Error('bounded wait: '+label+' (60s total)');}
  for(;seen<httpReplies.length;seen++){
   const at=httpReplies[seen];
   if(at-last>=12000){record('HTTP reply gap');throw Error('bounded wait: '+label+' (12s HTTP reply gap)');}
   last=at;
  }
  if(Date.now()-last>=12000){record('no HTTP progress');throw Error('bounded wait: '+label+' (12s without HTTP progress)');}
  if(releaseRead){record('exact gate reached');return;}
  await new Promise(r=>setTimeout(r,5));
 }
};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function click(value){
 const el=typeof value==='string'?$(value):value;assert(visible(el),'visible click '+value);assert(!el.matches(':disabled'),'enabled click '+value);
 const restore=[],work=[];
 for(const [node,key]of [[el,'onclick'],[el.form,'onsubmit']]){const fn=node?.[key];if(typeof fn!=='function')continue;const wrap=function(e){const promise=fn.call(this,e);work.push(Promise.resolve(promise));return promise;};node[key]=wrap;restore.push(()=>{if(node[key]===wrap)node[key]=fn;});}
 try{el.focus();el.click();await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=()=>requests.filter(r=>r.method==='POST');
const entry=()=>$('use-list').querySelector(`[data-use-family="CSV_DAG"][data-instance-id="${info.instance}"] button`);
const nav=name=>click(w.document.querySelector(`[data-tab="${name}"]`));
async function close(){if(!dom)return;await wait(()=>active===0&&pending.size===0,'HTTP drained');dom.window.close();dom=null;}
async function boot(){
 await close();boots++;
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);
 w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 if(info.download){
  w.Blob=Blob;
  w.URL.createObjectURL=blob=>{const url='blob:dag-test-'+downloadBlobs.length;downloadBlobs.push({url,blob,revoked:false});return url;};
  w.URL.revokeObjectURL=url=>{const value=downloadBlobs.find(b=>b.url===url);assert(value);value.revoked=true;};
  w.HTMLAnchorElement.prototype.click=function(){if(anchorFailure)throw Error('synthetic anchor failure');downloadAnchors.push({url:this.href,filename:this.download});};
 }
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{active++;const request={method:options.method||'GET',path,body:options.body?JSON.parse(options.body):undefined};requests.push(request);
  try{const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);httpReplies.push(Date.now());
   if(hold&&path===hold.path&&--hold.remaining===0){const gate=hold;hold=null;await new Promise(resolve=>{releaseRead=resolve;});if(gate.error){mutations.push({path,kind:'synthetic late response403',actual_status:r.status});return new Response(JSON.stringify({error:{code:'PERMISSION_DENIED',message:'synthetic delayed error'}}),{status:403,headers:{'Content-Type':'application/json'}});}}
   if(downloadMutation&&/^\/api\/internal\/instances\/[^/]+\/runs\/[^/]+$/.test(path)){
    const action=downloadMutation;downloadMutation=null;const value=JSON.parse(r.text);action.change(value);
    mutations.push({path,kind:action.label,actual_status:r.status,returned_response:value});
    return new Response(JSON.stringify(value),{status:r.status,headers:{'Content-Type':'application/json'}});
   }
   if(unknownHint&&path.endsWith('/dag-releases')){const modified=JSON.parse(r.text);for(const rel of modified.items)rel.snapshot.execution_source.version='toString';mutations.push({path,kind:'synthetic discovery version hint',actual_status:r.status});return new Response(JSON.stringify(modified),{status:r.status,headers:{'Content-Type':'application/json'}});}
   return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
  }finally{active--;}};
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await click('connect');await nav('apps');
 await wait(()=>!!entry(),'DAG directory entry');
}
async function open(){await click(entry());
 check(w.eval('csvDagContext?.savedUse&&csvDagContext.reuse.instance?.id')===info.instance&&visible($('dag-reuse-panel')),'directory opens original DAG controller and exact instance');
 check(!w.eval('applicationUse')&&$('use-form').hidden&&$('internal-panel').hidden,'DAG does not expose single-step CSV submission');
}
async function readonly(){assert.equal((await rpc({command:'readonly'})).status,200);}
const selected=()=>JSON.parse($('dag-reuse-proof').textContent);
const resultButton=version=>$('dag-reuse-results').querySelector(`[data-result-version="${version}"] button`);
const sourceReleases=new Map([info.old,info.target].map(r=>[r.id,r]));
const savedFiles=[],forbidden=[];
function visibleRelease(id){return $('dag-reuse-release').value===id&&$('dag-reuse-release').selectedOptions[0]?.value===id;}
async function submit(column,release,revision,version,total){
 const before=posts().length;
 $('dag-reuse-column').value=column;$('dag-reuse-column').dispatchEvent(new w.Event('change'));
 check($('dag-reuse-run').disabled&&!$('dag-reuse-run-confirm').checked,'new input requires separate confirmation at revision '+revision);
 $('dag-reuse-run-confirm').checked=true;$('dag-reuse-run-confirm').dispatchEvent(new w.Event('change'));
 const work=click('dag-reuse-run');$('dag-reuse-run').click();await work;
 const sent=posts().slice(before);check(sent.length===1&&sent[0].body.expected_revision===revision&&sent[0].body.expected_release_fingerprint===release.fingerprint&&same(sent[0].body.input,{column}),'one explicit Run POST binds adopted Release and revision '+revision);
 let detail=selected().instance,queued=detail.runs.find(r=>r.status==='QUEUED');assert(queued);
 check(queued.release_id===release.id&&queued.expected_revision===revision&&queued.output===null&&queued.result_version===null,'queued Run has own Release/revision and no borrowed output');
 assert.equal((await rpc({command:'worker'})).status,200);await click('dag-reuse-read');detail=selected().instance;
 const run=detail.runs.find(r=>r.run_id===queued.run_id),record=detail.data.find(r=>r.run_id===run.app_run_id);
 check(run.status==='SUCCEEDED'&&run.result_version===version&&run.output.column===column&&run.output.sum===total&&record.release_id===release.id&&record.version===version,'cold Worker appends own exact result v'+version);
 check(run.proof.steps.length===3&&run.proof.steps.every(s=>s.status==='VERIFIED')&&run.proof.business_writes===1&&run.proof.model_requests===0&&run.proof.result.instance_result.record_fingerprint===record.fingerprint,'full original proof and one typed write remain bound v'+version);
 await readonly();return {run,record};
}
async function capture(index,version){
 await wait(()=>downloadBlobs[index]?.revoked,'Blob URL revoked');
 const text=await downloadBlobs[index].blob.text(),value=JSON.parse(text),detail=selected().instance;
 const record=detail.data.find(r=>r.version===version),run=detail.runs.find(r=>r.app_run_id===record.run_id),rel=sourceReleases.get(run.release_id),e=rel.snapshot.execution_source;
 assert.equal(Buffer.byteLength(text,'utf8'),downloadBlobs[index].blob.size);assert.equal(downloadBlobs[index].blob.type,'application/json;charset=utf-8');
 assert.equal(text,JSON.stringify(value,null,2)+'\n');
 assert.equal(value.instance_id,detail.id);assert.equal(value.run_id,run.run_id);assert.equal(value.app_run_id,record.run_id);
 assert.equal(value.instance_revision,run.expected_revision);assert.equal(value.release_id,rel.id);assert.equal(value.release_fingerprint,rel.fingerprint);
 assert.equal(value.result_version,version);assert.equal(value.record_fingerprint,record.fingerprint);assert.equal(value.execution_version,e.version);
 assert(same(value.input,run.input)&&same(value.result,record.data.result)&&same(value.output,run.proof.result.output));
 assert(same(value.source,{app_id:detail.source_app_id,run_id:e.run_id,plan_key:e.plan_key,plan_fingerprint:e.plan_fingerprint,source_hash:e.source_hash}));
 assert.equal(value.run_plan_fingerprint,run.proof.plan_fingerprint);
 assert(same(Object.keys(value.node_outputs).sort(),[e.aggregate_step,e.report_step].sort()));
 for(const id of [e.aggregate_step,e.report_step])assert(same(value.node_outputs[id],run.proof.result.steps.find(s=>s.step_id===id).data));
 assert.equal(typeof value.node_outputs[e.aggregate_step].sum,'string');assert.equal(value.node_outputs[e.report_step].text,`列 ${run.output.column}；行数 2；合计 ${run.output.sum}`);
 assert.equal(value.model_requests,0);assert.equal(value.semantic_status,'UNKNOWN');assert.equal(value.owner_acceptance,'PENDING');assert.equal(value.formal_publication_enabled,false);
 assert(!text.includes('item,amount,quantity')&&!text.includes('synthetic-test-A')&&!text.includes('authorization_fingerprint'));
 assert(downloadAnchors.some(a=>a.url===downloadBlobs[index].url&&a.filename===`csv-dag-${detail.id}-${run.run_id}-v${version}.json`));
 const filename=`download-blob-${index}-v${version}.json`;fs.writeFileSync(info.output.replace('result.json',filename),text);savedFiles.push({filename,version,run_id:run.run_id,release_id:rel.id,revision:run.expected_revision,bytes:Buffer.byteLength(text,'utf8'),sha256:crypto.createHash('sha256').update(text).digest('hex')});
 check(true,`actual Blob v${version} binds own historical Release/revision/source and complete report output`);await readonly();return text;
}
async function flow(){
 await open();
 check(visibleRelease(info.old.id),'initial visible Release equals the opened instance current Release');
 const first=await submit('amount',info.old,1,1,'30');
 let index=downloadBlobs.length;await click(resultButton(1));const beforeSwitch=await capture(index,1);
 const original=selected().instance,preparePosts=posts().length;
 check([...$('dag-reuse-switch-target').options].some(o=>o.value===info.target.id),'existing adoption UI offers exact compatible target');
 $('dag-reuse-switch-target').value=info.target.id;$('dag-reuse-switch-target').dispatchEvent(new w.Event('change'));
 await click('dag-reuse-switch-prepare');
 const approval=w.eval('csvDagContext.reuse.switchApproval');assert(approval);
 check(posts().length===preparePosts+1&&approval.payload.from_release_id===info.old.id&&approval.payload.target_release_id===info.target.id&&approval.payload.revision===1&&approval.data_preserved===true&&approval.new_grants===false,'visible prepare/read approval binds both Releases and preserves data without grants');
 check(selected().instance.release_id===info.old.id&&$('dag-reuse-switch-commit').disabled,'preparation does not adopt and requires manual confirmation');
 assert.equal((await rpc({command:'checkpoint',stage:'prepare'})).status,200);await readonly();
 $('dag-reuse-switch-confirm').checked=true;$('dag-reuse-switch-confirm').dispatchEvent(new w.Event('change'));
 await click('dag-reuse-switch-commit');
 let detail=selected().instance;
 check(detail.id===original.id&&detail.release_id===info.target.id&&detail.revision===2&&detail.data_version===1&&same(detail.data,original.data),'visible exact adoption changes pointer/revision and preserves the old typed record');
 check(detail.history.some(h=>h.kind==='switch'&&h.previous_release_id===info.old.id&&h.release_id===info.target.id&&h.approval_id===approval.id),'adoption persists consumed approval provenance');
 check(visibleRelease(info.target.id),'visible Release selector follows the actually adopted target');
 assert.equal((await rpc({command:'checkpoint',stage:'commit'})).status,200);await readonly();
 const second=await submit('quantity',info.target,2,2,'15');
 check(first.run.run_id!==second.run.run_id&&first.run.release_id!==second.run.release_id&&info.old.snapshot.execution_source.run_id!==info.target.snapshot.execution_source.run_id&&info.old.snapshot.execution_source.plan_fingerprint!==info.target.snapshot.execution_source.plan_fingerprint,'old/new actual Run and immutable Release sources are distinct');
 const beforeCold=posts().length;await boot();await open();detail=selected().instance;
 check(posts().length===beforeCold&&detail.release_id===info.target.id&&detail.revision===2&&detail.data_version===2&&visibleRelease(info.target.id),'cold directory opens adopted Release/revision with zero POST');
 check(same(detail.data[0],first.record)&&detail.runs.some(r=>r.run_id===first.run.run_id&&r.release_id===info.old.id&&r.expected_revision===1)&&detail.runs.some(r=>r.run_id===second.run.run_id&&r.release_id===info.target.id&&r.expected_revision===2),'cold history retains both own Release/revision bindings');
 index=downloadBlobs.length;await click(resultButton(1));const afterSwitch=await capture(index,1);
 check(beforeSwitch===afterSwitch,'cold old-file bytes remain identical after adopting the new Release');
 index=downloadBlobs.length;await click(resultButton(2));await capture(index,2);
 const oldPath=`/api/internal/instances/${info.instance}/runs/${first.run.run_id}`,newPath=`/api/internal/instances/${info.instance}/runs/${second.run.run_id}`;
 index=downloadBlobs.length;hold={path:oldPath,remaining:1};const delayed=click(resultButton(1));await waitHeld('held old-Release historical download');
 await click(resultButton(2));await capture(index,2);const release=releaseRead;releaseRead=null;release();await delayed;
 check(downloadBlobs.length===index+1,'later new-result download invalidates late old-Release response');
 index=downloadBlobs.length;await click(resultButton(1));await capture(index,1);
 const oldCallback=resultButton(2).onclick,count=downloadBlobs.length;
 assert.equal((await rpc({command:'revoke'})).status,200);
 await click(resultButton(1));
 const oldReply=requests.filter(r=>r.path===oldPath).at(-1);assert.equal(oldReply.status,403);forbidden.push({run_id:first.run.run_id,status:403,via:'explicit visible old-result download'});
 check(downloadBlobs.length===count&&!w.eval('csvDagContext')&&!$('dag-reuse-results').textContent&&!$('dag-reuse-proof').textContent,'revoked old-result download403 clears protected current/old results without Blob');
 const calls=requests.length;await oldCallback(new w.Event('click'));
 check(requests.length===calls&&downloadBlobs.length===count,'detached new-result control cannot create a request or Blob');
 let denied=false;try{await w.api(newPath);}catch(error){denied=error.httpStatus===403;}
 check(denied&&requests.at(-1).path===newPath&&requests.at(-1).status===403,'new-result endpoint also actually403 after view cleared (direct existing API read)');forbidden.push({run_id:second.run.run_id,status:403,via:'direct existing API read after protected view cleared'});
 check(downloadBlobs.length===count&&w.eval('dagReuseDownloads.size')===0&&downloadBlobs.every(b=>b.revoked),'both versions remain undownloaded after revocation and all URL/keys are released');await readonly();
 const runPosts=posts().filter(r=>r.path===`/api/internal/instances/${info.instance}/runs`),prepare=posts().filter(r=>r.path===`/api/internal/instances/${info.instance}/switch-approvals`),commit=posts().filter(r=>r.path.includes('/switch-approvals/')&&r.path.endsWith('/commit'));
 check(runPosts.length===2&&prepare.length===1&&commit.length===1&&posts().length===4,'entire loop has two explicit Run posts plus one real prepare/commit, zero download POST');
}
(async()=>{
 let status='FAIL',error;
 try{await boot();await flow();status='PASS';}catch(e){error=e.stack;process.stderr.write(error+'\n');process.exitCode=1;}
 finally{
  if(releaseRead){releaseRead();releaseRead=null;}
  try{await close();}catch(e){status='FAIL';error=error||e.stack;process.exitCode=1;}
  fs.writeFileSync(info.output,JSON.stringify({status,error,checks,requests,assets,boots,mutations,heldWaits,saved_files:savedFiles,forbidden_after_revoke:forbidden,
   download_blobs:downloadBlobs.map(({url,blob,revoked})=>({url,type:blob.type,bytes:blob.size,revoked})),download_anchors:downloadAnchors,
   scope:'One actual ASGI/JSDOM compatible adoption + own-Release cold downloads; synthetic SQLite/NoModel. Direct post-clear endpoint probe is labelled separately.',pg:'NOT_RUN',native_browser:'NOT_RUN',real_models_semantics:'NOT_RUN'},null,2)+'\n');
  process.stdout.write(JSON.stringify({done:true})+'\n');
 }
})();
