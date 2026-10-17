'use strict';
const fs=require('node:fs'),crypto=require('node:crypto'),readline=require('node:readline'),assert=require('node:assert/strict'),{JSDOM}=require('jsdom');
const info=JSON.parse(fs.readFileSync(process.argv[2])),pending=new Map(),requests=[],checks=[],assets=[];let serial=0,dom,w,$,drop=false,dropAdoption=false,dropRelease=false,dropBaseline=false,hold=null,release=null,directoryAudit=null;
readline.createInterface({input:process.stdin}).on('line',line=>{const r=JSON.parse(line),resolve=pending.get(r.id);assert(resolve);pending.delete(r.id);resolve(r);});
const rpc=body=>new Promise(resolve=>{const id=++serial;pending.set(id,resolve);process.stdout.write(JSON.stringify({id,...body})+'\n');});
const check=(ok,label)=>{assert(ok,label);checks.push(label);};
const wait=async(fn,label,timeout=15000)=>{const end=Date.now()+timeout;while(Date.now()<end){if(fn())return;await new Promise(r=>setTimeout(r,5));}throw Error('bounded wait '+label);};
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
async function open(){await nav('apps');await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance).querySelector('button'));}
async function boot(){
 const load=async path=>{const r=await rpc({method:'GET',path});assert.equal(r.status,200);assets.push({path,sha256:crypto.createHash('sha256').update(r.text).digest('hex')});return r.text;};
 dom=new JSDOM(await load('/'),{url:'http://testserver/',runScripts:'dangerously',pretendToBeVisual:true});w=dom.window;$=id=>w.document.getElementById(id);w.TextEncoder=TextEncoder;w.structuredClone=structuredClone;Object.defineProperty(w,'crypto',{value:crypto.webcrypto});w.setInterval=()=>0;
 const style=w.document.createElement('style');style.textContent=await load('/app.css');w.document.head.append(style);
 w.fetch=async(path,options={})=>{const request={path,method:options.method||'GET',body:options.body?JSON.parse(options.body):undefined};requests.push(request);const r=await rpc({...request,headers:options.headers});request.status=r.status;request.response=JSON.parse(r.text);
  if(hold===path){hold=null;await new Promise(resolve=>{release=resolve;});}
  if(drop&&request.method==='POST'&&path.endsWith('/csv-goal-revisions/checks')){drop=false;assert.equal(r.status,202);request.delivery='ACTUAL_202_LOST';throw Error('synthetic lost CHECK response');}
  if(dropBaseline&&request.method==='POST'&&path.endsWith('/delivery-graph/derive')){dropBaseline=false;assert.equal(r.status,201);request.delivery='ACTUAL_DERIVE_201_LOST';throw Error('synthetic lost baseline derive response');}
  if(dropRelease&&request.method==='POST'&&path.startsWith('/api/internal/approvals/')&&path.endsWith('/commit')){dropRelease=false;assert.equal(r.status,200);request.delivery='ACTUAL_RELEASE_200_LOST';throw Error('synthetic lost Release response');}
  if(dropAdoption&&request.method==='POST'&&path.includes('/switch-approvals/')&&path.endsWith('/commit')){dropAdoption=false;assert.equal(r.status,200);request.delivery='ACTUAL_CAS_200_LOST';throw Error('synthetic lost original CAS response');}
  return new Response(r.text,{status:r.status,headers:{'Content-Type':r.content_type||'application/json'}});
 };
 for(const script of [...w.document.querySelectorAll('script[src]')]){const node=w.document.createElement('script');node.textContent=await load(script.getAttribute('src'));w.document.body.append(node);}
 $('token').value='synthetic-test-A';await action('connect');await project(info.project);await open();
 check(visible($('csv-goal-next'))&&$('use-info').textContent.includes('CSV'),'directory-selected adopted v2 exposes explicit next revision entry');
 check(posts('/previews').length===0&&posts('/checks').length===0,'opening adopted instance only reads');
 await action('csv-goal-next');check(visible($('csv-goal-baseline')),'explicit next starts one cycle on current Release');
}

async function revise(){
 if(info.case==='next-unknown'){
  await action('csv-goal-edit');check($('goal-card-status').textContent.includes('v2'),'same source Goal opens at adopted v2');
  $('goal-card-title').value='明确下一目标 v3';$('goal-card-goal').value='明确下一目标：汇总 amount，保留同一材料';await action('goal-card-save');
  check($('goal-card-status').textContent.includes('v3'),'explicit Goal editor saves same card v3');await open();
 }
 const before=requests.length;
 if(info.case==='same-navigation'){
  const graphPath=`/api/projects/${info.project}/apps/${info.app}/delivery-graph`;
  hold=graphPath+'/derive';dropBaseline=true;const sending=action('csv-goal-baseline');
  await wait(()=>release,'actual upgraded baseline derive201 held',90000);await nav('resources');await nav('apps');
  await wait(()=>visible($('csv-goal-revision')),'return retains original baseline intent',60000);
  const done=release;release=null;done();await sending;
  await wait(()=>visible($('csv-goal-recover'))&&!$('csv-goal-recover').disabled,'lost baseline exposes original GET recovery',60000);
  const mark=requests.length;await action('csv-goal-recover');
  check(requests.slice(mark).every(x=>x.method==='GET'),'lost baseline201 recovers original key using GET only');
  const sent=requests.filter(x=>x.method==='POST'&&x.path===graphPath+'/derive');
  check(sent.length===1&&sent[0].status===201&&sent[0].delivery==='ACTUAL_DERIVE_201_LOST','explicit baseline derives stale software anchor exactly once');
  check(requests.slice(before).some(x=>x.path===graphPath&&x.status===409&&x.response.error.message==='Current graph baseline changed; explicitly derive a new anchor'),'only exact actual stale software baseline conflict enables derive');
  check(requests.slice(mark).some(x=>x.method==='GET'&&x.path===graphPath+'/derive-requests/'+sent[0].body.request_key&&x.status===200),'recovery reads exact accepted derive request key');
 }else{
  await action('csv-goal-baseline');
  check(!requests.slice(before).some(x=>x.method==='POST'),'current baseline GET does not derive or mutate root graph');
 }
 const shown=JSON.parse($('csv-goal-revision-proof').textContent),ctx=shown.context;
 check(ctx.parent.spec_revision===2&&ctx.parent.column==='quantity'&&ctx.parent.release_id===info.release,'baseline comes from current verified effective v2 binding');
 check(ctx.goal.version===(info.case==='next-unknown'?3:2)&&ctx.goal_mode===(info.case==='next-unknown'?'EXPLICIT_NEXT_GOAL':'KEEP_ADOPTED_GOAL'),'Goal version is independently frozen and not manufactured for same-target column edit');
 check($('csv-goal-from').value==='quantity'&&$('csv-goal-from').disabled,'current effective old column is displayed and locked');
 $('csv-goal-to').value='amount';await action('csv-goal-to','change');
 const b=$('csv-goal-preview'),sending=action(b);await b.onclick(new w.Event('click'));await sending;
 check(posts('/csv-goal-revisions/previews').length===1&&$('csv-goal-check').disabled,'double click submits one child preview and awaits explicit CHECK consent');
}
async function confirmationReturn(stage,ack,submit){
 const suffix={preview:'/previews',release:'/version-approvals',adoption:'/adoption-approvals'}[stage];
 const preview=posts('/csv-goal-revisions/previews').at(-1).response;
 const frozen=stage==='adoption'?requests.filter(x=>x.method==='GET'&&x.path.endsWith(suffix+'/'+preview.request_key)&&x.status===200).at(-1).response:posts('/csv-goal-revisions'+suffix).at(-1).response;
 const hint=posts('/csv-goal-revisions'+suffix).at(-1).response;assert.equal(frozen.id,hint.id);assert.equal(frozen.fingerprint,hint.fingerprint);
 await action(ack);check(!$(submit).disabled,stage+' explicit consent enables next action');
 const begin=requests.length,before=$('csv-goal-revision');await nav('resources');await nav('apps');
 await wait(()=>visible($('csv-goal-revision'))&&$('csv-goal-revision')!==before&&!$(ack).disabled,stage+' restored current proof',60000);
 const segment=requests.slice(begin),shown=JSON.parse($('csv-goal-revision-proof').textContent);
 check(segment.every(x=>x.method!=='POST'),stage+' navigation/revalidation does not submit');
 assert.deepEqual(shown[stage==='preview'?'preview':stage==='release'?'release_approval':'adoption_approval'],frozen);assert.deepEqual(shown.preview,preview);
 checks.push(stage+' return displays complete exact server-frozen payload');
 check($('csv-goal-from').value==='quantity'&&$('csv-goal-to').value==='amount'&&$('csv-goal-from').disabled&&$('csv-goal-to').disabled,stage+' restores and locks actual parent-to-child mapping');
 check(!$(ack).checked&&$(submit).disabled,stage+' requires fresh visible consent');
 const contextAt=segment.findIndex(x=>x.method==='GET'&&x.path.endsWith('/context'));
 const previewAt=segment.findIndex(x=>x.method==='GET'&&x.path.endsWith('/previews/'+preview.request_key));
 check(contextAt>=0&&previewAt>contextAt,stage+' fresh return segment reads current context then exact original preview');
 if(stage==='release')check(segment.some(x=>x.method==='GET'&&x.path===`/api/internal/approvals/${frozen.id}`),stage+' fresh segment checks live original approval');
 if(stage==='adoption')check(segment.some(x=>x.method==='GET'&&x.path.endsWith('/adoption-approvals/'+preview.request_key)),stage+' fresh segment rereads exact original CAS preflight');
}
async function lost(stage,button,path,status){
 hold=path;if(stage==='check')drop=true;else if(stage==='commit')dropRelease=true;else dropAdoption=true;
 const before=requests.filter(x=>x.method==='POST'&&x.path===path).length;
 const b=$(button),sending=action(b);await b.onclick(new w.Event('click'));
 await wait(()=>release,'actual '+stage+' accepted and held',90000);
 await nav('resources');await nav('apps');await wait(()=>visible($('csv-goal-revision')),'navigation retains unresolved '+stage,60000);
 const done=release;release=null;done();await sending;
 await wait(()=>visible($('csv-goal-recover'))&&!$('csv-goal-recover').disabled,'original UNKNOWN '+stage+' can recover',60000);
 check($(button).disabled,stage+' UNKNOWN forbids duplicate submission');const mark=requests.length;await action('csv-goal-recover');
 check(requests.slice(mark).every(x=>x.method==='GET'),stage+' UNKNOWN recovery only GET');
 const sent=requests.filter(x=>x.method==='POST'&&x.path===path);
 check(sent.length===before+1&&sent.at(-1).status===status,stage+' one actual accepted POST survives response loss and navigation');
 check(w.eval(`csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).steps.${stage}.state`)==='accepted',stage+' exact original durable intent accepted after recovery');
}
async function navigation(){
 await action('csv-goal-check-ack');hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`;
 const sending=action('csv-goal-check');await wait(()=>release,'accepted child CHECK held',90000);
 await nav('projects');await project(info.other);const mark=requests.length,done=release;release=null;done();await sending;
 check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late child CHECK callback cannot populate another project');
 check(!requests.slice(mark).some(x=>x.method==='GET'&&x.path.includes('/csv-goal-revisions/')),'late child CHECK callback sends no old-scope follow-up GET');
 await project(info.project);await open();await action('csv-goal-recover');
 check(posts('/csv-goal-revisions/checks').length===1,'same owner recovers one original accepted child CHECK');
 const key=posts('/csv-goal-revisions/previews')[0].body.request_key;
 hold=`/api/internal/instances/${info.instance}/csv-goal-revisions/checks/${key}`;const reading=action('csv-goal-outcome');await wait(()=>release,'child CHECK read held',60000);
 await action([...$('use-list').children].find(x=>x.dataset.instanceId===info.instance2).querySelector('button'));
 const finish=release;release=null;finish();await reading;
 check(w.eval('applicationUse.id')===info.instance2&&!$('csv-goal-revision-proof').textContent.includes(posts('/csv-goal-revisions/checks')[0].response.run_id),'late child proof cannot replace another instance');
 hold=`/api/internal/instances/${info.instance2}/csv-goal-revisions/context`;const baseline=action('csv-goal-baseline');await wait(()=>release,'other instance context held',60000);
 await action('identity-switch');$('token').value='synthetic-test-B';await action('connect');const accountMark=requests.length,last=release;release=null;last();await baseline;
 check(!visible($('csv-goal-revision'))&&w.eval('applicationUse===null'),'late context cannot populate another account');
 check(!requests.slice(accountMark).some(x=>x.method==='POST'),'late account callback does not submit');
}
(async()=>{try{
 await boot();await revise();
 if(info.case==='navigation')await navigation();else{
  if(info.case==='same-navigation')await confirmationReturn('preview','csv-goal-check-ack','csv-goal-check');
  await action('csv-goal-check-ack');
  if(info.case==='next-unknown')await lost('check','csv-goal-check',`/api/internal/instances/${info.instance}/csv-goal-revisions/checks`,202);
  else{const b=$('csv-goal-check'),sending=action(b);await b.onclick(new w.Event('click'));await sending;}
  check(posts('/csv-goal-revisions/checks').length===1,'one accepted isolated CHECK for this child');
  const checked=posts('/csv-goal-revisions/checks')[0].response;await rpc({command:'worker',run:checked.run_id});await action('csv-goal-outcome');
  check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'),'actual original Worker/oracle verifies child');
  await action('csv-goal-version');
  if(info.case==='same-navigation')await confirmationReturn('release','csv-goal-release-ack','csv-goal-release');
  await action('csv-goal-release-ack');
  const approval=posts('/csv-goal-revisions/version-approvals').at(-1).response;
  if(info.case==='next-unknown')await lost('commit','csv-goal-release',`/api/internal/approvals/${approval.id}/commit`,200);else await action('csv-goal-release');
  check($('csv-goal-adopt').disabled,'new Release does not silently adopt');await action('csv-goal-adopt-prepare');
  if(info.case==='same-navigation')await confirmationReturn('adoption','csv-goal-adopt-ack','csv-goal-adopt');
  await action('csv-goal-adopt-ack');
  const adoption=posts('/csv-goal-revisions/adoption-approvals').at(-1).response;
  if(info.case==='next-unknown')await lost('adoptCommit','csv-goal-adopt',`/api/internal/instances/${info.instance}/switch-approvals/${adoption.id}/commit`,200);else await action('csv-goal-adopt');
  check([...$('use-column').options].map(x=>x.value).join()==='amount'&&$('use-info').textContent.includes(info.case==='next-unknown'?'Goal v3':'Goal v2'),'same business instance exposes child column and independently frozen Goal');
  check(visible($('csv-goal-next')),'adopted child exposes explicit further revision entry');
  $('use-csv-review-optin').checked=true;await action('use-submit');const run=posts('/runs').at(-1).response.run_id;
  await rpc({command:'worker',run});await action('use-refresh');
  check($('use-output').textContent.includes('合计 30')&&$('use-output').textContent.includes(run),'new actual Run has amount30 on same-instance v3');
  await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING')&&$('csv-owner-body').textContent.includes('30'),'same new Run human acceptance is independently PENDING');
  const owner=requests.filter(x=>x.method==='GET'&&x.path===`/api/internal/instances/${info.instance}/runs/${run}/csv-owner-review`).at(-1);
  check(owner?.status===200&&owner.response.owner_acceptance==='PENDING','actual human-review GET belongs to exact new business Run');
  await rpc({command:'proof',run});
  check(requests.filter(x=>x.method==='PUT'&&x.path.startsWith('/api/goal-cards/')).length===(info.case==='next-unknown'?1:0),'only explicit Goal save creates a Goal version');
 }
 await wait(()=>requests.every(x=>Number.isInteger(x.status)),'all actual replies settle',60000);
 fs.writeFileSync(info.output,JSON.stringify({status:'PASS',checks,requests,assets,directoryAudit},null,2));dom.window.close();process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(0);
}catch(error){fs.writeFileSync(info.output,JSON.stringify({status:'FAIL',error:error.stack,checks,requests,assets,directoryAudit},null,2));if(dom)dom.window.close();process.stderr.write(error.stack+'\n');process.stdout.write(JSON.stringify({done:true})+'\n');process.exit(1);}})();
