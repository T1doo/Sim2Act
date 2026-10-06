'use strict';
// Native-only module: reuse caller's protected Edge page; never launch a browser.
const assert = require('node:assert/strict');
module.exports = async function protocolChecks({page, base, info, action, capture}) {
  const result = {kind:'Protocol source/extract/cold/recover / caller-owned protected Edge / actual HTTP',
    status:'NOT_RUN', checks:[], metadata:{}, screenshots:[], layouts:[], httpSourceHashes:{},
    mockProviderRequests:0, networkProviderRequests:0, ownerSemanticAcceptance:'PENDING',
    formalPublication:false, visualReview:'NOT_REVIEWED', win11:'NOT_RUN'};
  const held = [], registrations = [];
  let outsideOriginRequests = 0, browserReviewRequests = 0;
  const observe = request => {
    if (new URL(request.url()).origin !== new URL(base).origin) outsideOriginRequests++;
    if (request.method()==='POST' && /\/protocol\/runs\/[^/]+\/reviews$/.test(new URL(request.url()).pathname)) browserReviewRequests++;
  };
  const check = (name, value) => {assert.ok(value, name); result.checks.push({name,status:'PASS'});};
  const fixture = async (name, rid) => {
    const raw = await action(name, rid ? ['--run-id',rid] : []);
    return typeof raw==='string' ? JSON.parse(raw) : raw;
  };
  const ready = () => page.waitForFunction(() => protocolContext && !protocolContext.busy);
  const row = id => page.locator('#runs .row').filter({hasText:id.slice(0,16)}).getByRole('button');
  async function selectProject(pid) {
    await page.locator('[data-tab="projects"]').click();
    await page.locator('#project-select').waitFor({state:'visible'});
    const response=page.waitForResponse(r=>r.url()===`${base}/api/projects/${pid}/protocol/contracts`&&r.status()===200);
    await page.locator('#project-select').selectOption(pid);await response;
    await page.waitForFunction(id=>protocolContext?.project===id&&protocolCatalog.length===4,pid);
  }
  async function login() {
    await page.goto(base,{waitUntil:'networkidle'});
    await page.locator('#token').fill(info.bearer);await page.locator('#connect').click();
    await page.locator('#login').waitFor({state:'hidden'});
    await selectProject(info.project);
    await page.locator('#protocol-contract').selectOption(info.source_contract);
    await page.locator('#protocol-source-submit').waitFor({state:'visible'});
    await page.waitForFunction(()=>!document.getElementById('protocol-source-submit').disabled);
  }
  async function accepted(button, phase) {
    const response=page.waitForResponse(r=>r.url()===`${base}/api/projects/${info.project}/protocol/${phase}`&&r.request().method()==='POST'&&r.status()===202);
    await page.locator(button).click();const data=await(await response).json();
    await page.waitForFunction(id=>protocolContext?.run?.run_id===id&&!protocolContext.busy,data.run_id);
    return data;
  }
  async function read(rid, status) {
    const response=page.waitForResponse(r=>r.url()===`${base}/api/projects/${info.project}/protocol/runs/${rid}`&&r.request().method()==='GET'&&r.status()===200);
    await page.locator('#protocol-read').click();await response;
    await page.waitForFunction(({rid,status})=>protocolContext?.run?.run_id===rid&&protocolContext.run.status===status,{rid,status});
    return page.evaluate(()=>({id:protocolContext.run.run_id,phase:protocolContext.run.phase,status:protocolContext.run.status,
      fingerprint:protocolContext.run.result_fingerprint,semantic:protocolContext.run.semantic_status,
      owner:protocolContext.run.owner_semantic_acceptance,version:protocolContext.run.version,fence:protocolContext.run.fence}));
  }
  async function selectRun(rid) {
    await row(rid).waitFor({state:'visible'});await row(rid).click();
    await page.waitForFunction(id=>activeRun===id&&protocolContext?.run?.run_id===id&&!document.getElementById('protocol-detail').hidden,rid);
  }
  async function hold(url) {
    let release,accept,done,failure;
    const gate=new Promise(r=>release=r),accepted=new Promise(r=>accept=r),delivered=new Promise(r=>done=r);
    let used=false;
    const handler=async route=>{
      if(used){await route.continue();return;}used=true;
      try{const response=await route.fetch();assert.equal(response.status(),200+Number(route.request().method()==='POST')*2);accept();await gate;await route.fulfill({response});}
      catch(error){failure=error;accept();}finally{done();}
    };
    await page.route(url,handler);registrations.push([url,handler]);held.push(release);
    return {accepted,deliver:async()=>{release();await delivered;await page.unroute(url,handler);if(failure)throw failure;}};
  }
  async function lose(url, expected) {
    let body,receipt,failure,done;
    const delivered=new Promise(r=>done=r);
    const handler=async route=>{try{body=route.request().postDataJSON();const response=await route.fetch();assert.equal(response.status(),expected);receipt=await response.json();await route.abort('failed');}
      catch(error){failure=error;}finally{done();}};
    await page.route(url,handler);registrations.push([url,handler]);
    return {finish:async()=>{await delivered;await page.unroute(url,handler);if(failure)throw failure;return {body,receipt};}};
  }
  async function layout(label) {
    const bounds=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
      overflow:[...document.querySelectorAll('#protocol-panel button,#protocol-panel select,#protocol-panel input,#protocol-state,#protocol-result')]
        .filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));
    result.layouts.push({label,...bounds});check(label+': actual document and protocol controls/result bounds fit viewport',bounds.documentWidth<=bounds.width+1&&bounds.overflow===0);
  }
  async function apiOutcome(path, bearer=info.bearer) {
    return page.evaluate(async({url,bearer})=>{const response=await fetch(url,{headers:{Authorization:'Bearer '+bearer}});return {status:response.status,data:await response.json()};},{url:base+path,bearer});
  }
  try {
    assert.ok(info.project&&info.other_project&&info.source&&info.cold&&info.other_run&&info.bearer&&info.other_bearer);
    assert.equal(new URL(base).hostname,'127.0.0.1','Owned synthetic loopback API required');
    page.on('request',observe);
    const before=await fixture('counts');
    await page.setViewportSize({width:1280,height:900});await login();
    result.httpSourceHashes=await page.evaluate(async origin=>{
      const files=['index.html','app.js','internal.js','protocol.js'];return Object.fromEntries(await Promise.all(files.map(async file=>{
        const response=await fetch(origin+(file==='index.html'?'/':'/'+file));if(!response.ok)throw Error('Static source read failed');
        const digest=await crypto.subtle.digest('SHA-256',await response.arrayBuffer());return [file,[...new Uint8Array(digest)].map(b=>b.toString(16).padStart(2,'0')).join('')];})));},base);
    check('public catalog contains no private expected output or gold',await page.evaluate(()=>!JSON.stringify(protocolCatalog).includes('expected_output')&&!JSON.stringify(protocolCatalog).includes('gold')));
    const sourceURL=`${base}/api/projects/${info.project}/protocol/source`;
    const lost=await lose(sourceURL,202);await page.locator('#protocol-source-submit').click();const sourceLost=await lost.finish();await ready();
    check('lost actual source acceptance does not invent output',await page.evaluate(()=>protocolContext.run===null));
    const retry=page.waitForResponse(r=>r.url()===sourceURL&&r.request().method()==='POST'&&r.status()===202);
    await page.locator('#protocol-source-submit').click();const retried=await retry;
    check('manual source retry preserves original request key/body and accepted Run',JSON.stringify(retried.request().postDataJSON())===JSON.stringify(sourceLost.body)&&(await retried.json()).run_id===sourceLost.receipt.run_id);
    const source=sourceLost.receipt.run_id;await page.waitForFunction(id=>protocolContext?.run?.run_id===id&&!protocolContext.busy,source);
    check('actual source worker uses two offline Intern mock requests',(await fixture('worker',source)).requests===2);result.mockProviderRequests+=2;
    result.metadata.source=await read(source,'WAITING_APPROVAL');
    check('technical source completion does not enable extract or owner acceptance',await page.locator('#protocol-extract').isHidden()&&result.metadata.source.semantic==='UNKNOWN'&&result.metadata.source.owner==='PENDING');
    check('explicit independent fixture review passes registered source',(await fixture('review',source)).decision==='PASS');
    await read(source,'SUCCEEDED');await page.locator('#protocol-extract').waitFor({state:'visible'});
    check('registered PASS still leaves owner semantic acceptance PENDING',await page.evaluate(()=>protocolContext.run.owner_semantic_acceptance==='PENDING'));
    const extraction=await accepted('#protocol-extract','extract');
    check('actual extract worker compiles provider-produced candidate',(await fixture('worker',extraction.run_id)).requests===1);result.mockProviderRequests++;
    result.metadata.extraction=await read(extraction.run_id,'SUCCEEDED');await page.locator('#protocol-cold-form').waitFor({state:'visible'});
    result.metadata.plan=await page.evaluate(()=>({fingerprint:protocolContext.plan.plan_fingerprint,source:protocolContext.plan.candidate.resources}));
    await page.locator('#protocol-cold-contract').selectOption(info.cold_contract);
    await page.locator('#protocol-cold-materials select').selectOption(info.cold);
    const coldMade=await accepted('#protocol-cold-submit','cold');
    check('cold worker interprets a genuinely new material with one mock request',(await fixture('worker',coldMade.run_id)).requests===1);result.mockProviderRequests++;
    result.metadata.cold=await read(coldMade.run_id,'WAITING_APPROVAL');
    check('cold new-input result stays distinct and pending',coldMade.run_id!==source&&info.cold!==info.source&&result.metadata.cold.semantic==='UNKNOWN'&&result.metadata.cold.owner==='PENDING');
    await page.locator('#protocol-detail details summary').click();
    await layout('protocol-desktop');
    if(capture)result.screenshots.push(await capture('protocol-desktop',{flow:'protocol-source-extract-cold',source,extraction:extraction.run_id,cold:coldMade.run_id,owner:'PENDING',mockProviderRequests:4}));
    await page.setViewportSize({width:390,height:844});await layout('protocol-narrow');
    if(capture)result.screenshots.push(await capture('protocol-narrow',{flow:'protocol-source-extract-cold',source,extraction:extraction.run_id,cold:coldMade.run_id,owner:'PENDING',mockProviderRequests:4}));
    await page.setViewportSize({width:1280,height:900});
    // No selected protocol Run: actual source POST accepted while actual history GET remains pending.
    await selectProject(info.other_project);await selectProject(info.project);
    check('project navigation clears prior selected protocol evidence',await page.evaluate(()=>protocolContext.run===null));
    const pendingSource=await hold(sourceURL);await page.locator('#protocol-source-submit').click();await pendingSource.accepted;
    await row(coldMade.run_id).waitFor({state:'visible'});
    const pendingHistory=await hold(`${base}/api/runs/${coldMade.run_id}`);await row(coldMade.run_id).click();await pendingHistory.accepted;
    await pendingSource.deliver();await ready();
    check('first-context accepted POST cannot steal pending history selection',await page.evaluate(id=>activeRun===id&&(!protocolContext.run||protocolContext.run.run_id===id),coldMade.run_id));
    await pendingHistory.deliver();await page.waitForFunction(id=>protocolContext?.run?.run_id===id,coldMade.run_id);
    // Explicit same-Run re-selection before a late source success/failure.
    const sameSource=await hold(sourceURL);await page.locator('#protocol-source-submit').click();await sameSource.accepted;
    await selectRun(coldMade.run_id);await sameSource.deliver();await ready();
    check('late successful source receipt cannot steal reselected canvas',await page.evaluate(id=>activeRun===id&&protocolContext.run.run_id===id,coldMade.run_id));
    let abortRelease,abortAccepted,abortDone,abortFailure;
    const abortGate=new Promise(r=>abortRelease=r),abortArrival=new Promise(r=>abortAccepted=r),abortDelivered=new Promise(r=>abortDone=r);
    const failedHandler=async route=>{try{const response=await route.fetch();assert.equal(response.status(),202);abortAccepted();await abortGate;await route.abort('failed');}catch(error){abortFailure=error;abortAccepted();}finally{abortDone();}};
    await page.route(sourceURL,failedHandler);registrations.push([sourceURL,failedHandler]);held.push(abortRelease);
    await page.locator('#protocol-source-submit').click();await abortArrival;await selectRun(coldMade.run_id);
    abortRelease();await abortDelivered;await page.unroute(sourceURL,failedHandler);if(abortFailure)throw abortFailure;await ready();
    check('late failed source receipt cannot overwrite selected task status',await page.evaluate(id=>activeRun===id&&protocolContext.run.run_id===id&&!document.getElementById('protocol-state').textContent.includes('提交回执不明'),coldMade.run_id));
    // Real catalog response held across project navigation; cache contains only the new project resources.
    await selectProject(info.other_project);
    const catalogHold=await hold(`${base}/api/projects/${info.project}/protocol/contracts`);
    await page.locator('#project-select').selectOption(info.project);await catalogHold.accepted;
    await selectProject(info.other_project);await catalogHold.deliver();
    check('late old-project catalog cannot restore protected source or cold materials',await page.evaluate(({project,source,cold})=>protocolContext.project===project&&document.getElementById('protocol-detail').hidden&&!protocolMaterials.some(r=>r.id===source||r.id===cold),{project:info.other_project,source:info.source,cold:info.cold}));
    const crossed=await apiOutcome(`/api/projects/${info.other_project}/protocol/runs/${source}`);
    check('project-bound source read rejects a different owned project',crossed.status===403||crossed.status===404);
    const foreign=await apiOutcome(`/api/projects/${info.project}/protocol/contracts`,info.other_bearer);
    check('different identity cannot access owner protocol catalog',foreign.status===403||foreign.status===404);
    // A fresh real page starts a new intent; provider-unavailable default worker must not send.
    await login();const defaultMade=await accepted('#protocol-source-submit','source');
    check('default protocol worker makes zero provider requests',(await fixture('default-worker',defaultMade.run_id)).requests===0);
    result.metadata.default=await read(defaultMade.run_id,'WAITING_RESOURCE');
    const beforeRecover=await fixture('counts');
    const recoverURL=`${base}/api/projects/${info.project}/protocol/runs/${defaultMade.run_id}/recover`;
    const recoverLost=await lose(recoverURL,200);await page.locator('#protocol-recover').click();const lostRecovery=await recoverLost.finish();await ready();
    await page.locator('#protocol-recover-retry').waitFor({state:'visible'});
    const recoverRetry=page.waitForResponse(r=>r.url()===recoverURL&&r.request().method()==='POST'&&r.status()===200);
    await page.locator('#protocol-recover-retry').click();const recovered=await recoverRetry;const recoveryReceipt=await recovered.json();await ready();
    check('lost recovery manual retry preserves exact key/version/fence and receipt',JSON.stringify(recovered.request().postDataJSON())===JSON.stringify(lostRecovery.body)&&recoveryReceipt.recovery===lostRecovery.receipt.recovery&&recoveryReceipt.provider_requests===0);
    await page.waitForFunction(()=>protocolContext.run?.status==='PAUSED');
    const afterRecover=await fixture('counts');
    check('metadata-only recovery never adds an Attempt or continues execution',afterRecover.attempts===beforeRecover.attempts&&await page.evaluate(()=>protocolContext.run.status==='PAUSED'));
    // Actual recovery GET delayed over another native history selection.
    const recoveryRead=await hold(`${base}/api/projects/${info.project}/protocol/runs/${defaultMade.run_id}`);
    await page.locator('#protocol-recover').click();await recoveryRead.accepted;await selectRun(coldMade.run_id);await recoveryRead.deliver();await ready();
    check('late metadata read cannot overwrite a different selected result',await page.evaluate(id=>activeRun===id&&protocolContext.run.run_id===id&&!document.getElementById('protocol-state').textContent.includes('核对结果'),coldMade.run_id));
    const after=await fixture('counts');
    check('protocol UI changes neither Grants nor principals',before.grant_fingerprint===after.grant_fingerprint&&before.principal_fingerprint===after.principal_fingerprint);
    check('only the four expected offline provider Attempts were persisted',after.attempts===before.attempts+4&&after.attempt_states.every(a=>a.status==='RECEIVED'&&a.response_model==='intern-s2'));
    check('browser never submits a review or requests an outside API origin',browserReviewRequests===0&&outsideOriginRequests===0);
    result.metadata.counts={before,after};result.outsideOriginRequests=outsideOriginRequests;result.browserReviewRequests=browserReviewRequests;
    result.status='PASS';
  } catch(error) {result.status='FAIL';result.error={name:error.name,message:error.message};}
  finally {
    held.forEach(release=>release());
    for(const [url,handler] of registrations){try{await page.unroute(url,handler);}catch{}}
    page.off('request',observe);
  }
  return result;
};
