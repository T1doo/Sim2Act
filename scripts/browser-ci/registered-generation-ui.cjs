'use strict';
// Reuses a caller-owned protected page. Never launches a browser or supplies a candidate.
const assert=require('node:assert/strict');
module.exports=async function registeredGenerationChecks({page,base,info,action,capture}) {
 const result={kind:'Registered CSV Run generation UI / real local HTTP',checks:[],modelRequests:0,formalPublication:false,metadata:{},screenshots:[],layouts:[],screenshotScope:'registered CSV source Run -> server-generated draft -> cold new-input result; not prior agent Replay'};
 const sourceApp=info.registered_source_app,targetApp=info.registered_target_app;
 const held=[];
 function check(name,value){assert.ok(value,name);result.checks.push({name,status:'PASS'});}
 async function idle(){await page.waitForFunction(()=>engineering && !engineering.busy);}
 async function selectProject(pid){
  await page.locator('[data-tab="projects"]').click();await page.locator('#project-select').waitFor({state:'visible'});
  const refreshed=page.waitForResponse(r=>r.url()===`${base}/api/projects/${pid}/grants` && r.request().method()==='GET' && r.status()===200);
  await page.locator('#project-select').selectOption(pid);await refreshed;
  await page.locator('[data-tab="apps"]').click();
 }
 async function open(app){
  // Obtain the existing row label without bypassing the user's actual app button.
  const name=await page.evaluate(async id=>(await api('/api/apps/'+id)).name,app);
  await page.locator('#app-list .row').filter({hasText:new RegExp('^'+name.replace(/[.*+?^${}()|[\]\\]/g,'\\$&')+' · 未发布草案')}).getByRole('button').click();
  await page.waitForFunction(id=>activeApp===id && engineering?.app===id && engineering.project===document.getElementById('project-select').value && !engineering.busy && document.getElementById('internal-status').textContent==='内部历史已读回；正式发布与部署仍关闭。',app);
 }
 async function prepareInstance(column){
  await page.locator('#app-column').selectOption(column);await page.locator('#internal-prepare').click();await idle();
  check('independent sample check precedes manual internal release confirmation',(await page.locator('#internal-approval-detail').innerText()).includes('"status": "PASS"') && await page.locator('#internal-commit').isDisabled());
  await page.locator('#internal-approval-ack').check();await page.locator('#internal-commit').click();await idle();
  const release=await page.evaluate(()=>engineering.releases.at(-1).id);
  const created=page.waitForResponse(r=>r.url()===base+'/api/internal/releases/'+release+'/instances' && r.request().method()==='POST' && r.status()===201);
  await page.locator('#internal-releases .row').filter({hasText:release}).getByRole('button').click();const iid=(await (await created).json()).id;await page.waitForFunction(id=>engineering.instance?.id===id && !engineering.busy,iid);
  await page.locator('#internal-run-form').waitFor({state:'visible'});return {release,instance:iid};
 }
 async function run(column){
  await page.locator('#internal-run-form').waitFor({state:'visible'});
  await page.locator('#internal-column').selectOption(column);await page.locator('#internal-run-submit').click();await idle();
  const rid=await page.evaluate(()=>engineering.run.id);await action('worker');
  await page.locator('#internal-refresh').click();await idle();
  await page.locator('#internal-runs .row').filter({hasText:rid}).getByRole('button').click();
  await page.waitForFunction(id=>engineering.run?.id===id && engineering.run.status==='SUCCEEDED',rid);
  return {id:rid,...await page.evaluate(()=>({status:engineering.run.status,result:engineering.run.result,resultVersion:engineering.run.result_version,instance:engineering.instance.id}))};
 }
 async function reopenSource(source){
  await open(sourceApp);await page.locator('#internal-instances .row').filter({hasText:source.instance}).getByRole('button').click();await page.waitForFunction(id=>engineering.instance?.id===id && !engineering.busy,source.instance);
  await page.locator('#internal-runs .row').filter({hasText:source.id}).getByRole('button').click();
  await page.waitForFunction(id=>engineering.run?.id===id && engineering.run.status==='SUCCEEDED',source.id);
 }
 async function options(){await page.locator('#registered-extraction-open').click();await page.waitForFunction(()=>registeredExtraction && !registeredExtraction.busy);}
 async function target(name){await page.locator('#registered-extraction-target').selectOption(targetApp);await page.locator('#registered-extraction-name').fill(name);}
 async function extract(name){await options();await target(name);await page.locator('#registered-extraction-submit').click();await page.waitForFunction(()=>engineering && engineering.project===document.getElementById('project-select').value && !engineering.busy && document.getElementById('internal-status').textContent==='内部历史已读回；正式发布与部署仍关闭。' && document.getElementById('app-origin').textContent.includes('已成功内部 CSV AppRun'));return page.evaluate(()=>activeApp);}
 async function holdOptions(source){
  let accept,release,done,failure;const accepted=new Promise(r=>accept=r),gate=new Promise(r=>release=r),delivered=new Promise(r=>done=r);
  const pattern=`**/api/internal/instances/${source.instance}/runs/${source.id}/extraction-options`;
  const handler=async route=>{try{const response=await route.fetch();assert.equal(response.status(),200);accept();await gate;await route.fulfill({response});}catch(e){failure=e;accept();}finally{done();}};
  await page.route(pattern,handler);held.push(release);
  return {accepted,deliver:async()=>{release();await delivered;await page.unroute(pattern,handler);if(failure)throw failure;}};
 }
 async function layout(label){
  const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('#app-origin,#app-frozen-goal-text,#internal-data,#internal-panel button,#internal-panel select,#internal-panel input')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));
  result.layouts.push({label,...bounds});check(label+': document, proof, results and visible controls fit horizontal viewport',bounds.scroll<=bounds.width+1&&bounds.overflow===0);
 }
 async function apiOutcome(url,method='GET',body,auth='synthetic-agent-ui-A'){
  return page.evaluate(async({url,method,body,auth})=>{const r=await fetch(url,{method,headers:{Authorization:'Bearer '+auth,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});return {status:r.status,data:await r.json()};},{url:base+url,method,body,auth});
 }
 try {
  assert.ok(sourceApp && targetApp,'Registered source/target existing app fixture required');
  const authorityBefore=JSON.parse(await action('generation-counts'));
  await page.setViewportSize({width:1280,height:900});await selectProject(info.project);await open(sourceApp);
  check('registered source app uses CSV input and needs no wire Replay',await page.locator('#internal-agent').isHidden() && await page.locator('#app-column').isVisible());
  const sourceInstance=await prepareInstance('amount'),source=await run('amount');
  check('source success comes from actual accepted UI Run and cold worker',source.status==='SUCCEEDED' && source.result.sum==='3' && source.resultVersion===1);
  result.metadata.source={app:sourceApp,release:sourceInstance.release,instance:source.instance,run:source.id,status:source.status,resource:info.registered_source_resource,hash:source.result.source_hash};
  await options();check('server verifies source proof and exposes existing target scope',(await page.locator('#registered-extraction-proof').innerText()).includes('completed_registered_csv_apprun.v1'));
  await target('从成功任务保存的真实可复用汇总');
  check('target selection visibly describes existing shared authorization',(await page.locator('#registered-extraction-target-info').innerText()).includes(info.registered_target_resource) && (await page.locator('#registered-extraction-target-info').innerText()).includes('共享授权撤回'));
  const bodyBefore=await page.evaluate(()=>registeredBody(registeredExtraction));
  check('caller sends only source/target fingerprints and a name',Object.keys(bodyBefore).sort().join(',')==='expected_proof_fingerprint,expected_target_draft_fingerprint,name,target_app_id');
  const pattern=`**/api/internal/instances/${source.instance}/runs/${source.id}/extract`;let lostBody,lostApp,lostDone,lostFailure;const lostDelivered=new Promise(r=>lostDone=r);
  const lostHandler=async route=>{try{lostBody=route.request().postDataJSON();const response=await route.fetch();assert.equal(response.status(),201);lostApp=(await response.json()).id;await route.abort('failed');}catch(e){lostFailure=e;}finally{lostDone();}};
  await page.route(pattern,lostHandler);await page.locator('#registered-extraction-submit').click();await lostDelivered;await page.unroute(pattern,lostHandler);if(lostFailure)throw lostFailure;
  await page.waitForFunction(()=>registeredExtraction && !registeredExtraction.busy);
  check('actual lost acceptance preserves manual recovery without auto resend',await page.locator('#registered-extraction-retry').isVisible() && (await page.locator('#registered-extraction-status').innerText()).includes('不会自动重发'));
  await page.locator('#registered-extraction-name').fill('临时不同输入');check('different accepted input does not reuse prior pending key',await page.locator('#registered-extraction-retry').isHidden());
  await page.locator('#registered-extraction-name').fill(lostBody.name);
  const retryResponse=page.waitForResponse(r=>r.url()===base+`/api/internal/instances/${source.instance}/runs/${source.id}/extract` && r.request().method()==='POST');
  await page.locator('#registered-extraction-retry').click();const retried=await retryResponse;
  check('manual recovery preserves exact original request key/body and app',JSON.stringify(retried.request().postDataJSON())===JSON.stringify(lostBody) && (await retried.json()).id===lostApp);
  await page.waitForFunction(id=>activeApp===id && engineering?.app===id && engineering.project===document.getElementById('project-select').value && !engineering.busy && document.getElementById('internal-status').textContent==='内部历史已读回；正式发布与部署仍关闭。',lostApp);
  const generated=lostApp;check('server-generated app shows genuine source proof and NOT_RUN boundary',(await page.locator('#app-origin').innerText()).includes(source.id) && (await page.locator('#app-origin').innerText()).includes('NOT_RUN'));
  const generatedInstance=await prepareInstance('quantity'),fresh=await run('quantity');
  check('cold generated app actually computes unseen column/result',fresh.status==='SUCCEEDED' && fresh.result.sum==='15' && fresh.result.sum!==source.result.sum && fresh.resultVersion===1 && fresh.id!==source.id);
  result.metadata.generated={app:generated,release:generatedInstance.release,instance:fresh.instance,run:fresh.id,status:fresh.status,resource:info.registered_target_resource,hash:fresh.result.source_hash,resultVersion:fresh.resultVersion};
  check('generated data binding uses different authorized source hash',fresh.result.source_hash!==source.result.source_hash);
  await page.locator('#app-frozen-goal summary').click();await page.locator('#app-frozen-goal-text').waitFor({state:'visible'});
  check('screenshot state contains source proof, generated draft and fresh result',(await page.locator('#app-frozen-goal-text').innerText()).includes('completed_registered_csv_apprun.v1') && (await page.locator('#internal-data').innerText()).includes('15'));
  const authorityAfter=JSON.parse(await action('generation-counts'));
  check('normal UI generation and cold execution preserve all existing Grants and Principals',authorityAfter.grant_fingerprint===authorityBefore.grant_fingerprint && authorityAfter.principal_fingerprint===authorityBefore.principal_fingerprint);
  const scope={flow:'registered CSV Run -> server generated app -> cold new input',...result.metadata,semanticGoalAcceptance:'NOT_RUN',formalPublication:false};
  await layout('registered-desktop');if(capture)result.screenshots.push(await capture('agent-desktop',scope));
  await page.setViewportSize({width:390,height:844});await layout('registered-narrow');if(capture)result.screenshots.push(await capture('agent-narrow',scope));
  // Fresh page must recover persisted source/generated state without any test-inserted candidate.
  await page.reload({waitUntil:'networkidle'});await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await selectProject(info.project);await open(generated);
  await page.locator('#internal-instances .row').filter({hasText:fresh.instance}).getByRole('button').click();await page.waitForFunction(id=>engineering.instance?.id===id && !engineering.busy,fresh.instance);
  check('fresh page reads generated persisted result without rerun',(await page.locator('#internal-data').innerText()).includes('15'));
  const cross=await apiOutcome(`/api/internal/instances/${source.instance}/runs/${source.id}/extraction-options`,'GET',null,'synthetic-agent-ui-B');check('other identity cannot read source options',cross.status===403);
  const foreignDraft=await apiOutcome('/api/apps/'+info.empty_target_source_app);assert.equal(foreignDraft.status,200);
  const foreign=await apiOutcome(`/api/internal/instances/${source.instance}/runs/${source.id}/extract`,'POST',{...bodyBefore,target_app_id:info.empty_target_source_app,expected_target_draft_fingerprint:foreignDraft.data.fingerprint,request_key:'negative-cross-project'});check('cross-project existing target extraction refused',foreign.status===403);
  for(const mode of ['app','project','identity']){
   await selectProject(info.project);await reopenSource(source);const delayed=await holdOptions(source);await page.locator('#registered-extraction-open').click();await delayed.accepted;
   if(mode==='app')await open(targetApp);
   if(mode==='project')await selectProject(info.other_project);
   if(mode==='identity')await page.evaluate(()=>{token='synthetic-agent-ui-B';clearApp();}); // Explicit session-change fault, not hidden login UI.
   await delayed.deliver();check(`late options after ${mode} switch cannot render protected proof`,await page.locator('#registered-extraction-proof').textContent()==='' && await page.locator('#registered-extraction-form').isHidden());
   if(mode==='identity')await page.evaluate(()=>{token='synthetic-agent-ui-A';});
  }
  await selectProject(info.project);await reopenSource(source);const corrupted=await extract('用于明确篡改负例的第二草案');
  await action('generation-corrupt',['--app-id',corrupted]);await page.locator('#internal-refresh').click();await idle();
  check('rehashed generated candidate tamper clears protected content',await page.locator('#app-manifest').textContent()==='' && await page.locator('#internal-data').textContent()==='');
  await open(generated);await action('generation-revoke');await page.locator('#internal-refresh').click();await idle();
  check('current target revoke rejects healthy generated draft and clears it',await page.locator('#app-manifest').textContent()==='' && await page.locator('#internal-run-form').isHidden());
  await reopenSource(source);await options();check('target revoke leaves explicit needs-input rather than new permissions',(await page.locator('#registered-extraction-status').innerText()).includes('Existing authorized app') && await page.locator('#registered-extraction-form').isHidden());
  await action('generation-source-revoke');await page.locator('#internal-refresh').click();await idle();check('current source revoke clears source state before new extraction',await page.locator('#registered-extraction').isHidden() && await page.locator('#app-manifest').textContent()==='');
  await selectProject(info.empty_target_project);await open(info.empty_target_source_app);await prepareInstance('amount');const emptySource=await run('amount');await options();
  const emptyOutcome=await apiOutcome(`/api/internal/instances/${emptySource.instance}/runs/${emptySource.id}/extraction-options`);
  check('real successful single-app project has no distinct target and returns NEEDS_INPUT',emptyOutcome.data.error?.code==='NEEDS_INPUT' && await page.locator('#registered-extraction-form').isHidden());
  result.status='PASS';return result;
 }catch(error){result.status='FAIL';result.error={name:error.name,message:error.message};return result;}
 finally{held.forEach(release=>release());}
};
