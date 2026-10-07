'use strict';
// Called only by the existing protected Windows Edge path; never launches a browser.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {execFile}=require('node:child_process');
const execFileAsync=require('node:util').promisify(execFile);
module.exports=async function runAgentChecks({browser,root,outputRoot,python,audit}){
 const repo=path.resolve(__dirname,'../..');
 const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8')),base=`http://127.0.0.1:${info.port}`;
 const result={kind:'Agent regression plus registered generation / same actual protected Windows Edge / synthetic HTTP',platform:process.platform,modelRequests:0,legacyChecksCounted:0,checks:[],screenshots:[],unexpectedPageErrors:[],sandbox:[],visualReview:'NOT_REVIEWED',win11:'NOT_RUN'};
 let page,context;const held=[];let baselineRendererPids=new Set();
 async function verifySandbox(){
  const observed=await audit();result.sandbox.push(observed);
  check('agent actual browser/renderer arguments preserve protection',observed.some(p=>p.type==='browser')&&observed.every(p=>p.security_args_verified));
  const renderers=observed.filter(p=>p.type==='renderer');
  check('agent context has an actual renderer beyond the legacy PID baseline',renderers.some(p=>!baselineRendererPids.has(p.pid)));
  check('agent actual Windows renderers have restricted low-integrity or AppContainer tokens',renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)));
 }
 async function holdResponse(pattern){
  let release,accept,done,failure;
  const gate=new Promise(r=>{release=r;}),accepted=new Promise(r=>{accept=r;}),delivered=new Promise(r=>{done=r;});
  const handler=async route=>{try{const response=await route.fetch();accept();await gate;await route.fulfill({response});}catch(error){failure=error;accept();}finally{done();}};
  await page.route(pattern,handler);held.push(release);
  return {accepted,deliver:async()=>{release();await delivered;await page.unroute(pattern,handler);if(failure)throw failure;}};
 }
function check(name,value){assert.ok(value,name);result.checks.push({name,status:'PASS'});}
async function action(name,args=[]){return (await execFileAsync(python,['scripts/agent-ui/fixture.py','--root',root,'--action',name,...args],{cwd:repo,env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'})).stdout.trim();}
async function idle(){await page.waitForFunction(()=>engineering && !engineering.busy);}
async function instanceResultsReady(id,version){await page.waitForFunction(({id,version})=>{
 const view=engineering,data=document.getElementById('internal-data');
 const titles=Array.from(data.querySelectorAll('.agent-result > p:first-child'),p=>p.textContent);
 return view && engineeringCurrent(view) && !view.busy && view.instance?.id===id && view.instance.data_version===version
  && data.querySelectorAll('.agent-result').length===version
  && Array.from({length:version},(_,i)=>i+1).every(v=>titles.some(t=>t.startsWith('历史结果 v'+v+' ·')));
},{id,version});}
async function open(id){await page.locator('#app-list .row').filter({hasText:id===info.derived_app?'已完成任务的 agent 候选':id===info.initial_app?'evidence app':'existing R0 app domain'}).getByRole('button').click();await page.waitForFunction(id=>activeApp===id && engineering?.app===id && engineering.project===document.getElementById('project-select').value && !engineering.busy && document.getElementById('internal-status').textContent==='内部历史已读回；正式发布与部署仍关闭。',id);}
async function selectProject(pid){
 await page.locator('[data-tab="projects"]').click();await page.locator('#project-select').waitFor({state:'visible'});
 const refreshed=page.waitForResponse(r=>r.url()===`${base}/api/projects/${pid}/grants`&&r.request().method()==='GET'&&r.status()===200);
 await page.locator('#project-select').selectOption(pid);await refreshed;
 await page.waitForFunction(pid=>document.getElementById('project-select').value===pid,pid);
 await page.locator('[data-tab="apps"]').click();
}
async function inputs(file,term){await page.locator('#app-agent-term').fill(term);if(await page.locator('#internal-term').isVisible())await page.locator('#internal-term').fill(term);await page.locator('#internal-replay-file').setInputFiles(path.join(root,file));await page.waitForFunction(()=>engineering.offlineReplay!==null);}
async function layout(label){
 const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('#internal-panel button,#internal-panel input,#internal-panel blockquote')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));
 check(`${label}: no document/control/quote horizontal overflow`,bounds.scroll<=bounds.width+1&&bounds.overflow===0);
 // Prior agent screenshots remain in their earlier source CI. This run archives
 // only the new generation milestone below, with explicit scope and actual hashes.
}
async function captureRegistered(label,scope){
 assert.ok(scope && scope.flow==='registered CSV Run -> server generated app -> cold new input' && scope.source?.run && scope.generated?.run,'Explicit registered generation milestone required');
 assert.ok(['agent-desktop','agent-narrow'].includes(label));
 const observed=await audit(),renderers=observed.filter(p=>p.type==='renderer');
 assert.ok(observed.some(p=>p.type==='browser')&&observed.every(p=>p.security_args_verified),'Generation capture browser arguments preserve protection');
 assert.ok(renderers.some(p=>!baselineRendererPids.has(p.pid)),'Generation capture has an actual renderer beyond legacy baseline');
 assert.ok(renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)),'Generation capture actual renderer tokens remain protected');
 result.generationCaptureSandbox??=[];result.generationCaptureSandbox.push({phase:label,observed});
 const diagnostic=await page.evaluate(()=>({scrollY,fonts:document.fonts.status,viewport:{width:innerWidth,height:innerHeight},nodes:['app-title','app-origin','app-frozen-goal-text','internal-status','internal-data','registered-extraction-proof'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect(),style=getComputedStyle(e);return{id,characters:(e.value??e.textContent).trim().length,display:style.display,visibility:style.visibility,color:style.color,opacity:style.opacity,width:r.width,height:r.height,inViewport:r.bottom>0&&r.top<innerHeight};})}));
 result.captureDiagnostics??={};result.captureDiagnostics[label]={scope:'registered-run-generation',milestone:scope,...diagnostic};
 await page.evaluate(async()=>{await document.fonts.ready;const viewport=innerHeight,total=document.documentElement.scrollHeight;if(total>viewport*24)throw Error('Synthetic screenshot viewport bound exceeded');for(let y=0;y<total;y+=Math.max(1,Math.floor(viewport*.75))){scrollTo(0,y);await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));}scrollTo(0,0);await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));});
 result.captureDiagnostics[label].capturePreparation='fonts ready; bounded normal scroll; actual original full-page PNG, no pixel editing; old blank cause remains UNKNOWN';
 const file=label+'.png';await page.screenshot({path:path.join(outputRoot,file),fullPage:true});
 const bytes=fs.readFileSync(path.join(outputRoot,file));
 const metadata={name:file,scope:'registered-run-generation',milestone:scope,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),visualReview:'NOT_REVIEWED'};
 result.screenshots.push(metadata);return metadata;
}

 try{
  const baseline=await audit();baselineRendererPids=new Set(baseline.filter(p=>p.type==='renderer').map(p=>p.pid));
  result.legacyRendererBaseline=[...baselineRendererPids];
  context=await browser.newContext({viewport:{width:1280,height:900},bypassCSP:false,acceptDownloads:false});
  await context.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
  page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',e=>result.unexpectedPageErrors.push(e.message));
  await page.goto(base,{waitUntil:'networkidle'});await verifySandbox();await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});
  await selectProject(info.project);await open(info.derived_app);
  check('agent hides the CSV-only parameter label',await page.locator('#app-column-label').isHidden());
  check('existing authenticated app path opens agent',await page.locator('#internal-agent').isVisible());
  check('offline supplied candidate and semantic UNKNOWN are clear',(await page.locator('#internal-agent').innerText()).includes('尚无真实模型自主生成')&&(await page.locator('#app-origin').innerText()).includes('UNKNOWN'));
  await page.locator('#app-frozen-goal summary').click();await page.locator('#app-frozen-goal-text').waitFor({state:'visible'});
  check('displayed trusted source Run and bounded resource match seeded chain',(await page.locator('#app-origin').innerText()).includes(info.source_run)&&(await page.locator('#app-frozen-goal-text').innerText()).includes(info.resource_b));
  check('missing Replay blocks approval',await page.locator('#internal-prepare').isDisabled());
  await inputs('derived-replay.json',info.term_b);await page.locator('#internal-prepare').click();await idle();
  check('approval binds explicit responses',(await page.locator('#internal-approval-detail').innerText()).includes('offline_replay_fingerprint'));
  check('no default acknowledgement',await page.locator('#internal-commit').isDisabled());
  await page.locator('#internal-approval-ack').check();await page.locator('#internal-commit').click();await idle();
  await page.locator('#internal-releases button').last().click();await page.waitForFunction(()=>engineering.instance && !engineering.busy);
  const iid=await page.evaluate(()=>engineering.instance.id);
  await page.locator('#internal-run-form').waitFor({state:'visible'});await inputs('derived-replay.json',info.term_b);
  await page.locator('#internal-run-submit').click();await idle();await action('worker');await page.locator('#internal-refresh').click();await idle();await instanceResultsReady(iid,1);
  check('cold default worker persisted independent result v1',(await page.locator('#internal-data').innerText()).includes('历史结果 v1'));
  check('literal citations and UNKNOWN shown',(await page.locator('#internal-data blockquote').count())>0&&(await page.locator('#internal-data').innerText()).includes('语义 UNKNOWN'));
  let deliveredLost;
  const lostDelivered=new Promise(resolve=>{deliveredLost=resolve;});let lostFailure;
  const runPattern=`**/api/internal/instances/${iid}/runs`;
  const lostHandler=async route=>{try{const response=await route.fetch();assert.equal(response.status(),202);await route.abort('failed');}catch(error){lostFailure=error;}finally{deliveredLost();}};
  await page.route(runPattern,lostHandler);await page.locator('#internal-run-submit').click();
  await lostDelivered;await page.unroute(runPattern,lostHandler);if(lostFailure)throw lostFailure;await idle();
  check('lost actual acceptance delivery preserves one frozen retry intent',await page.evaluate(()=>engineeringPending.size===1));
  await inputs('initial-replay.json','other-input');const beforeRetry=JSON.parse(await action('counts'));
  await page.locator('#internal-retry').click();await idle();const afterRetry=JSON.parse(await action('counts'));
  check('manual retry uses frozen accepted key/input/Replay without duplicate Run',afterRetry.internal_app_runs===beforeRetry.internal_app_runs&&await page.evaluate(()=>engineeringPending.size===0));
  await action('worker');await page.locator('#internal-refresh').click();await idle();await instanceResultsReady(iid,2);
  check('cold retry produces independent result v2 and retains v1',(await page.locator('#internal-data').innerText()).includes('历史结果 v2')&&await page.locator('#internal-data .agent-result').count()===2);
  await layout('agent-desktop');await page.setViewportSize({width:390,height:844});await layout('agent-narrow');await verifySandbox();
  await page.reload({waitUntil:'networkidle'});await verifySandbox();await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await selectProject(info.project);await open(info.derived_app);
  await page.locator('#internal-instances .row').filter({hasText:iid}).getByRole('button').click();await page.waitForFunction(()=>engineering.instance && !engineering.busy);
  check('fresh page reopens both persisted versions without execution',await page.locator('#internal-data .agent-result').count()===2);
  await inputs('derived-replay.json',info.term_b);await page.locator('#internal-prepare').click();await idle();
  await page.evaluate(()=>{engineering.approval.expires_at=Date.now()/1000-1;engineeringButtons(engineering);});await page.locator('#internal-approval-ack').check();check('client expiry gate disables confirmation (server expiry covered by HTTP suite)',await page.locator('#internal-commit').isDisabled());
  const approvalHold=await holdResponse('**/release-approvals');
  await page.locator('#internal-prepare').click();await approvalHold.accepted;
  await page.locator('#app-agent-term').fill('changed-input');await approvalHold.deliver();await idle();
  check('late approval cannot restore changed-input confirmation',await page.locator('#internal-approval').isHidden());
  await page.evaluate(()=>{window._agentOriginalFileText=File.prototype.text;File.prototype.text=function(){const file=this;return new Promise(resolve=>{window._agentFinishFile=async()=>resolve(await window._agentOriginalFileText.call(file));});};});
  await page.locator('#internal-replay-file').setInputFiles(path.join(root,'derived-replay.json'));await open(info.csv_app);await page.evaluate(async()=>{await window._agentFinishFile();File.prototype.text=window._agentOriginalFileText;});
  check('late actual File read cannot attach Replay to CSV',await page.evaluate(()=>engineering.offlineReplay===null));
  const appHold=await holdResponse(`**/api/apps/${info.initial_app}`);
  await page.locator('#app-list .row').filter({hasText:'evidence app'}).getByRole('button').click();await appHold.accepted;
  await open(info.derived_app);await appHold.deliver();
  check('late source app response cannot replace selection',await page.evaluate(id=>activeApp===id,info.derived_app));
  const projectHold=await holdResponse(`**/api/apps/${info.initial_app}`);
  await page.locator('#app-list .row').filter({hasText:'evidence app'}).getByRole('button').click();await projectHold.accepted;
  await selectProject(info.other_project);await projectHold.deliver();
  await page.waitForFunction(()=>document.querySelectorAll('#app-list button').length===0);
  check('late previous-project response cannot reveal source or internal panel',await page.locator('#internal-panel').isHidden()&&await page.locator('#app-manifest').textContent()==='');
  await selectProject(info.project);await open(info.derived_app);
  await action('corrupt');await page.locator('#internal-refresh').click();await idle();check('provenance tamper clears protected snapshots',await page.locator('#internal-data').textContent()===''&&await page.locator('#app-manifest').textContent()==='');
  await open(info.initial_app);await action('revoke');await page.locator('#internal-refresh').click();await idle();check('current revocation clears protected results',await page.locator('#internal-data').textContent()===''&&await page.locator('#internal-run-form').isHidden());
  check('UI actions grant nothing',JSON.parse(await action('counts')).grants===info.grant_count);
  check('no unexpected page errors',result.unexpectedPageErrors.length===0);
  assert.equal(result.checks.length,33,'Existing agent checks must remain separately counted');
  result.registeredGeneration=await require('./registered-generation-ui.cjs')({page,base,info,action,capture:captureRegistered});
  assert.equal(result.registeredGeneration.status,'PASS','Registered generation native flow failed');
  const observed=await audit();result.registeredGeneration.sandbox=observed;
  const renderers=observed.filter(p=>p.type==='renderer');
  assert.ok(observed.some(p=>p.type==='browser')&&observed.every(p=>p.security_args_verified),'Generation browser arguments preserve protection');
  assert.ok(renderers.some(p=>!baselineRendererPids.has(p.pid)),'Generation page uses actual renderer beyond legacy baseline');
  assert.ok(renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)),'Generation actual renderer tokens remain protected');
  result.registeredGeneration.securityStatus='PASS';
  result.registeredGeneration.captureSandbox=result.generationCaptureSandbox;
  assert.equal(result.generationCaptureSandbox?.length,2,'Both actual generation capture stages audited');
  assert.equal(result.unexpectedPageErrors.length,0,'No new generation page runtime errors');
  assert.equal(result.screenshots.length,2,'Only the two named generation milestone screenshots');
  // Separate integrated phase; original 33 agent and 29 generation assertions retain their scope.
  let integrationOutsideRequests=0;
  page.on('request',request=>{if(!request.url().startsWith(base+'/'))integrationOutsideRequests++;});
  await page.addInitScript(()=>{window.setInterval=()=>0;});
  await page.reload({waitUntil:'networkidle'});
  const integrationBefore=JSON.parse(await action('integration-counts'));
  const integrationAudit=async()=>{
   const observed=await audit(),renderers=observed.filter(p=>p.type==='renderer');
   assert.ok(observed.some(p=>p.type==='browser')&&observed.every(p=>p.security_args_verified),'Integration arguments preserve protection');
   assert.ok(renderers.some(p=>!baselineRendererPids.has(p.pid)),'Integration has actual renderer beyond baseline');
   assert.ok(renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)),'Integration renderer tokens remain protected');
   return observed;
  };
  const integrationSandboxBefore=await integrationAudit();
  result.integration=await require('./product-integration-ui.cjs')({evaluate:code=>page.evaluate(code),
   reload:()=>page.reload({waitUntil:'networkidle'}),worker:id=>action('integration-worker',['--run-id',id]),info:info.integration});
  assert.equal(result.integration.status,'PASS');assert.equal(result.integration.checks.length,16);
  const integrationAfter=JSON.parse(await action('integration-counts'));
  assert.equal(integrationBefore.authority_fingerprint,integrationAfter.authority_fingerprint,'Whole authority rows remain identical');
  assert.equal(integrationAfter.application_runs-integrationBefore.application_runs,3);
  assert.deepEqual(integrationAfter.data_versions,[1,2]);
  assert.equal(integrationAfter.attempts.length,2);assert.ok(integrationAfter.attempts.every(a=>a.mode==='MOCK'&&a.status==='RECEIVED'));
  result.integration.durable={before:integrationBefore,after:integrationAfter};
  assert.equal(result.unexpectedPageErrors.length,0,'No integration runtime page errors');
  assert.equal(integrationOutsideRequests,0,'Integration never requests another origin');
  result.integration.outsideOriginRequests=integrationOutsideRequests;
  result.integration.sandboxBefore=integrationSandboxBefore;result.integration.sandboxAfter=await integrationAudit();
  result.integration.screenshots=[];
  for(const [label,width] of [['desktop',1280],['mobile',390]]){
   await page.setViewportSize({width,height:900});await page.locator('[data-tab="apps"]').click();
   await page.evaluate(async()=>{await document.fonts.ready;scrollTo(0,0);await new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)));});
   const layout=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
    visibleControls:[...document.querySelectorAll('#application-use button,#application-use select')].filter(e=>e.getClientRects().length).map(e=>{const r=e.getBoundingClientRect();return {left:r.left,right:r.right,height:r.height};}),
    current:document.getElementById('use-output').textContent,history:document.getElementById('use-history').textContent}));
   assert.ok(layout.documentWidth<=width+1&&layout.visibleControls.length>0&&layout.visibleControls.every(r=>r.left>=0&&r.right<=width+1&&r.height>=40),'Integration controls fit actual viewport');
   assert.ok(layout.current.includes('本页尚未选择')&&layout.history.includes('历史结果 v1')&&layout.history.includes('历史结果 v2'));
   const sandbox=await integrationAudit();await page.screenshot({path:path.join(outputRoot,label+'.png'),fullPage:true});
   result.integration.screenshots.push({name:label+'.png',scope:'integrated-cold-application-use',layout,sandbox,visualReview:'NOT_REVIEWED'});
  }
  assert.equal(result.unexpectedPageErrors.length,0,'No integration errors through both captures');
  assert.equal(integrationOutsideRequests,0,'No integration outside requests through both captures');
  result.integration.outsideOriginRequests=integrationOutsideRequests;
  result.status='PASS';
 }catch(error){result.status='FAIL';result.error={name:error.name,message:error.message};if(page&&!page.isClosed()){try{await page.screenshot({path:path.join(outputRoot,'agent-failure.png'),fullPage:true});}catch{}}}
 finally{
  held.forEach(release=>release());
  try{await context?.close();}catch(error){result.status='FAIL';result.cleanupError=error.name;}
  finally{fs.writeFileSync(path.join(outputRoot,'agent-results.json'),JSON.stringify(result,null,2)+'\n');}
 }
 console.log(`Additional agent ${result.status}: ${result.checks.length} regression checks; registered generation ${result.registeredGeneration?.status || 'NOT_RUN'} (${result.registeredGeneration?.checks?.length || 0} checks); scoped generation screenshots ${result.screenshots.length}; visual NOT_REVIEWED; model requests 0.`);
 if(result.status!=='PASS')throw Error('Additional agent native checks failed; see named agent-results.json');
 return result;
};
