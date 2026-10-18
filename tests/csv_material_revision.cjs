'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],checks=[],assets=[];let serial=0,dom,w,$,hold=null,release=null,drop=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(fn,label,timeout=60000)=>{const end=Date.now()+timeout;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait '+label);};
function visible(el){if(!el?.isConnected)return false;for(let p=el;p;p=p.parentElement)if(p.hidden||w.getComputedStyle(p).display==='none')return false;return true;}
async function action(el,type='click'){
 if(typeof el==='string')el=$(el);assert(visible(el),'visible '+(el?.id||el?.textContent));assert(!el.matches(':disabled'),'enabled '+el.id);
 const work=[],restore=[];
 for(const [node,name]of [[el,type==='change'?'onchange':'onclick'],[type==='click'?el.form:null,'onsubmit']]){const fn=node?.[name];if(typeof fn!=='function')continue;const wrap=function(e){const p=fn.call(this,e);work.push(Promise.resolve(p));return p;};node[name]=wrap;restore.push(()=>{if(node[name]===wrap)node[name]=fn;});}
 try{if(type==='click')el.click();else el.dispatchEvent(new w.Event(type,{bubbles:true}));await Promise.all(work);}finally{restore.forEach(fn=>fn());}
}
const posts=suffix=>requests.filter(r=>r.method==='POST'&&r.path.endsWith(suffix));
async function nav(tab){await action(w.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));}
async function project(id){$('project-select').value=id;await action('project-select','change');}
async function open(id=info.instance){await nav('apps');await action([...$('use-list').children].find(x=>x.dataset.instanceId===id).querySelector('button'));}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={path,method:options.method||'GET',body:options.body?JSON.parse(options.body):undefined};requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}
  if(drop===path&&request.method==='POST'){drop=null;request.delivery=`ACTUAL_${r.status}_LOST`;throw Error('synthetic lost accepted material revision response');}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);await open();
 check(visible($('csv-material-next'))&&$('use-info').textContent.includes('CSV'),'ordinary directory selected adopted instance exposes material replacement');
 check(posts('/previews').length===0&&posts('/checks').length===0,'opening adopted instance only reads');
 await action('csv-material-next');check(visible($('csv-goal-baseline'))&&!visible($('csv-goal-edit')),'explicit material cycle keeps old controller and no Goal editing');
 const mark=requests.length;await action('csv-goal-baseline');
 check(!requests.slice(mark).some(x=>x.method==='POST'),'current material context reads without creating graph or work');
 const ctx=JSON.parse($('csv-goal-revision-proof').textContent).context;
 check(ctx.revision_contract==='csv-material-revision.v1'&&ctx.parent.spec_revision===2&&ctx.parent.column==='quantity'&&ctx.parent.release_id===info.release,'material context freezes verified effective parent v2');
 check(ctx.goal.version===2&&ctx.goal_mode==='KEEP_ADOPTED_GOAL'&&ctx.goal.snapshot.content.resource_refs.includes(info.sourceA),'unchanged adopted Goal retains original A provenance');
 check(ctx.source.resource_id===info.sourceA&&ctx.source.hash===info.hashA&&ctx.data_version===info.dataVersion,'actual current material and result version frozen');
 check($('csv-goal-from').value==='quantity'&&$('csv-goal-to').value==='quantity'&&$('csv-goal-from').disabled&&$('csv-goal-to').disabled,'same adopted column locked across material change');
 const abandonedKey=w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).key'),beforeReturn=requests.length;
 await action('csv-material-back');
 check(visible($('csv-material-next'))&&visible($('csv-goal-next'))&&!requests.slice(beforeReturn).some(x=>x.method==='POST'),'unsubmitted material cycle returns to current instance entry without mutation');
 check(w.eval(`csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).history.some(x=>x.key===${JSON.stringify(abandonedKey)}&&x.mode==='material'&&x.state==='abandoned'&&x.ctx.revision_contract==='csv-material-revision.v1')`),'abandoned material cycle preserves original key, context and ledger in history');
 await action('csv-material-next');await action('csv-goal-baseline');
 check(w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).key')!==abandonedKey,'new material cycle needs explicit entry action and fresh key');
 check($('csv-material-target').value===''&&$('csv-goal-preview').disabled,'another authorized material requires explicit choice without default');
 check([...$('csv-material-target').options].some(x=>x.value===info.material),'authorized target B available');
 $('csv-material-target').value=info.material;await action('csv-material-target','change');
 check($('csv-material-provenance').textContent.includes(info.sourceA)&&$('csv-material-provenance').textContent.includes(info.material)&&$('csv-material-provenance').textContent.includes(info.hashA)&&$('csv-material-provenance').textContent.includes(info.hashB),'visible provenance distinguishes original Goal A and current/target complete hashes');
 const b=$('csv-goal-preview'),sending=action(b);await b.onclick(new w.Event('click'));await sending;
 check(posts('/csv-material-revisions/previews').length===1&&posts('/csv-goal-revisions/previews').length===0,'double click sends one material preview to new adapter only');
 const preview=posts('/csv-material-revisions/previews')[0];
 check(preview.status===201&&preview.response.namespace==='csv-material-revision.v1'&&preview.response.material.resource_id===info.material&&preview.response.material.hash===info.hashB,'actual material preview response identifies exact authorized target');
 check(preview.body.expected_data_version===info.dataVersion&&preview.body.resource_id===info.material&&preview.body.source_hash===info.hashB&&preview.body.column==='quantity'&&preview.body.baseline_column==='quantity','explicit POST freezes new resource/hash and unchanged column/data version');
 check($('csv-goal-check').disabled&&$('csv-material-target').disabled&&$('csv-material-back').disabled,'accepted preview locks material and return while waiting for distinct CHECK consent');
}
async function confirmationReturn(stage,ack,submit){
 const preview=posts('/csv-material-revisions/previews').at(-1).response;
 const frozen=stage==='preview'?preview:posts('/csv-goal-revisions/'+(stage==='release'?'version-approvals':'adoption-approvals')).at(-1).response;
 await action(ack);check(!$(submit).disabled,stage+' explicit visible consent enables next action');
 const begin=requests.length,before=$('csv-goal-revision');await nav('resources');await nav('apps');
 await wait(()=>visible($('csv-goal-revision'))&&$('csv-goal-revision')!==before&&!$(ack).disabled,stage+' material proof restored');
 const segment=requests.slice(begin),shown=JSON.parse($('csv-goal-revision-proof').textContent);
 check(segment.every(x=>x.method==='GET'),stage+' navigation performs read-only revalidation');
 assert.deepEqual(shown[stage==='preview'?'preview':stage==='release'?'release_approval':'adoption_approval'],frozen);
 check($('csv-material-target').value===info.material&&$('csv-material-target').disabled&&$('csv-goal-from').value==='quantity'&&$('csv-goal-to').value==='quantity','restored material mode locks same exact B and column');
 check(!$(ack).checked&&$(submit).disabled,stage+' navigation requires fresh explicit consent');
 const contextAt=segment.findIndex(x=>x.method==='GET'&&x.path.endsWith('/csv-material-revisions/context'));
 const previewAt=segment.findIndex(x=>x.method==='GET'&&x.path.endsWith('/csv-goal-revisions/previews/'+preview.request_key));
 check(contextAt>=0&&previewAt>contextAt,stage+' reads new context then exact old common preview journal');
}
async function lost(stage,button,path,status){
 hold=path;drop=path;const before=requests.filter(x=>x.method==='POST'&&x.path===path).length;
 const b=$(button),sending=action(b);await b.onclick(new w.Event('click'));
 await wait(()=>release,'accepted '+stage+' response held');
 await nav('resources');await nav('apps');await wait(()=>visible($('csv-goal-revision')),'navigation retains original unresolved '+stage);
 const done=release;release=null;done();await sending;
 await wait(()=>visible($('csv-goal-recover'))&&!$('csv-goal-recover').disabled,'material UNKNOWN '+stage+' recovery');
 check($(button).disabled&&$('csv-material-back').disabled,stage+' UNKNOWN forbids a duplicate submission or abandoning original intent');const mark=requests.length;await action('csv-goal-recover');
 check(requests.slice(mark).every(x=>x.method==='GET'),stage+' recovery only GETs original durable intent');
 const sent=requests.filter(x=>x.method==='POST'&&x.path===path);
 check(sent.length===before+1&&sent.at(-1).status===status&&sent.at(-1).delivery===`ACTUAL_${status}_LOST`,stage+' exactly one actual accepted POST despite lost response');
 check(w.eval(`csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).steps.${stage}.state`)==='accepted',stage+' accepted original key recovered');
}
async function navigation(){
 await action('csv-goal-check-ack');hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`;
 const sending=action('csv-goal-check');await wait(()=>release,'accepted material CHECK held');
 await nav('projects');await project(info.other);const mark=requests.length,done=release;release=null;done();await sending;
 check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late material CHECK callback cannot populate another project');
 check(!requests.slice(mark).some(x=>x.path.includes('/csv-goal-revisions/')),'late material CHECK sends no original-scope follow-up GET');
 await project(info.project);await open();await action('csv-goal-recover');
 check(posts('/csv-goal-revisions/checks').length===1,'return recovers one original same-instance accepted CHECK');
 const key=posts('/csv-material-revisions/previews')[0].body.request_key;
 hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks/${key}`;
 const reading=action('csv-goal-outcome');await wait(()=>release,'material CHECK read held');
 await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance2).querySelector('button'));
 const finish=release;release=null;finish();await reading;
 check(w.eval('applicationUse.id')===info.instance2&&!$('csv-goal-revision-proof').textContent.includes(posts('/csv-goal-revisions/checks')[0].response.run_id),'late material CHECK proof cannot replace another instance');
 hold=`/api/internal/instances/${info.instance}/csv-material-revisions/context`;
 const opening=action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance).querySelector('button'));
 await wait(()=>release,'original material context read held');
 await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');
 const accountMark=requests.length,last=release;release=null;last();await opening;
 check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late material context cannot populate another account');
 check(!requests.slice(accountMark).some(x=>x.path.includes('/csv-goal-revisions/')),'late account context does not read private frozen preview or submit');
}
(async()=>{try{
 await boot();
 if(info.case==='navigation')await navigation();else{
  await confirmationReturn('preview','csv-goal-check-ack','csv-goal-check');
  await action('csv-goal-check-ack');
  await lost('check','csv-goal-check',`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`,202);
  const checked=posts('/csv-goal-revisions/checks')[0].response;await rpc({command:'worker',run:checked.run_id});await action('csv-goal-outcome');
  check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'),'actual existing Worker and independent oracle pass target B CHECK');
  await action('csv-goal-version');await confirmationReturn('release','csv-goal-release-ack','csv-goal-release');
  await action('csv-goal-release-ack');await action('csv-goal-release');
  check($('csv-goal-adopt').disabled,'new Release requires separate same-instance CAS confirmation');
  await action('csv-goal-adopt-prepare');await confirmationReturn('adoption','csv-goal-adopt-ack','csv-goal-adopt');
  await action('csv-goal-adopt-ack');const adoption=posts('/csv-goal-revisions/adoption-approvals')[0].response;
  await lost('adoptCommit','csv-goal-adopt',`/api/internal/instances/${info.instance}/switch-approvals/${adoption.id}/commit`,200);
  check(w.eval('applicationUse.id')===info.instance&&[...$('use-column').options].map(x=>x.value).join()==='quantity'&&$('use-info').textContent.includes('Goal v2'),'original business instance exposes B with same column and unchanged Goal');
  check(visible($('csv-material-next')),'adopted material revision remains discoverable');
  const provenance=JSON.parse($('use-provenance').textContent);
  check($('use-info').textContent.includes(info.material)&&$('use-info').textContent.includes(info.hashB)&&$('use-info').textContent.includes(info.sourceA),'adopted use summary shows actual B hash with original Goal A provenance');
  check(provenance.resource_id===info.material&&provenance.resource_hash===info.hashB&&provenance.material_revision.original_goal_resources.includes(info.sourceA)&&provenance.material_revision.reference.purpose==='USE','use provenance reads exact frozen effective B and original Goal sources');
  $('use-csv-review-optin').checked=true;await action('use-submit');const run=posts('/runs').at(-1).response.run_id;
  await rpc({command:'worker',run});await action('use-refresh');
  check($('use-output').textContent.includes('合计 18')&&$('use-output').textContent.includes(run),'same instance new actual Run sums target B quantity18');
  await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING')&&$('csv-owner-body').textContent.includes('18'),'same new B Run has independent human PENDING entry');
  const owner=requests.filter(x=>x.method==='GET'&&x.path===`/api/internal/instances/${info.instance}/runs/${run}/csv-owner-review`).at(-1);
  check(owner?.status===200&&owner.response.owner_acceptance==='PENDING','actual owner-review GET identifies exact new business Run');
  await rpc({command:'proof',run});
  check(requests.filter(x=>x.method==='PUT'&&x.path.startsWith('/api/goal-cards/')).length===0,'material revision never fabricates or edits Goal version');
  check(posts('/csv-material-revisions/previews').length===1&&posts('/csv-goal-revisions/checks').length===1&&posts('/csv-goal-revisions/version-approvals').length===1&&posts('/csv-goal-revisions/adoption-approvals').length===1,'all visible material lifecycle submissions occur once');
 }
 await wait(()=>requests.every(x=>Number.isInteger(x.status)),'all actual replies settle');
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',checks,requests,assets},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(0);
}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,requests,assets},null,2));if(dom)dom.window.close();process.stderr.write(error.stack+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(1);}})();
