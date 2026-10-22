'use strict';
// Private harness waits must settle on cancellation; closing Edge cannot
// resolve a Promise created by this script (for example a not-yet-seen GET).
function stoppedWait(promise,signal){
 return new Promise((resolve,reject)=>{
  let done=false;
  const settle=(fn,value)=>{if(done)return;done=true;signal.removeEventListener('abort',abort);fn(value);};
  const abort=()=>settle(reject,signal.reason);
  signal.addEventListener('abort',abort,{once:true});
  Promise.resolve(promise).then(value=>settle(resolve,value),error=>settle(reject,error));
  if(signal.aborted)abort();
 });
}
function cleanupDeadlines(now,workUntil){const shared=Math.min(now+10000,workUntil+10000);return {shared,node:Math.min(shared,now+4000)};}
module.exports={stoppedWait,cleanupDeadlines};
if(require.main===module){
// Real DOM and production scripts, actual sealed SQLite API. No VM adapter.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require('playwright-core');
const root=process.argv[2],python=process.argv[3];
const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8'));
assert.ok(['source','extract'].includes(info.phase),'Unknown explicit completion phase');
const source=info.phase==='source',review=info.action==='review';
assert.ok(info.action==='completion'||review,'Unknown explicit action');
assert.ok(!review||source,'Review fixture only supports sealed Source');
const control=review?'protocol-review':'protocol-completion',postKind=review?'review_post':'completion_post';
if(source)assert.ok(!Object.hasOwn(info,'other'),'Source fixture must not manufacture another Run');
else assert.equal(typeof info.other,'string');
const completionPath=review?`/api/internal/protocol/runs/${info.run}/reviews`:`/api/projects/${info.project}/protocol/runs/${info.run}/${source?'complete-source':'complete-extraction'}`;
const result={status:'UNKNOWN',phase:info.phase,action:info.action,nativeCrossRunABA:source?'NOT_TESTED_SINGLE_RUN_FIXTURE':'COVERED_RUN_SWITCH',screenshotFiles:[],scope:'real installed Edge / production full page / sealed synthetic SQLite',checks:[],receipts:[],screenshots:0,counts:{business_get:0,static_get:0,[postKind]:0,blocked:0},requests:[],pageErrors:[],sandbox:[]};
// Exactly the already reviewed installed-Edge route, not a new launch policy.
const removedSecurityDefaults=[
 '--enable-unsafe-swiftshader','--unsafely-disable-devtools-self-xss-warnings',
 '--disable-ipc-flooding-protection','--disable-client-side-phishing-detection',
 '--password-store=basic','--use-mock-keychain',
 '--disable-features='+['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose',
 'DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter',
 'PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect',
 'Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn',
 'msEdgeUpdateLaunchServicesPreferredVersion'].join(',')
];
let browser,page,timer,watcher,failGet=false,holdGet=false,held,releaseHeld,heldRequest,delivered,cancelled=false,fail;
const cancellation=new AbortController(),wait=promise=>stoppedWait(promise,cancellation.signal);
const bodies=[];
function check(name,condition){assert.ok(condition,name);result.checks.push(name);}
function write(){fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2));}
function failWindow(error){cancelled=true;cancellation.abort(error);fail(error);}
async function cleanupWait(promise,until){let clock;try{return await Promise.race([promise,new Promise((_,reject)=>{clock=setTimeout(()=>reject(Error('Shared cleanup deadline')),Math.max(1,until-Date.now()));})]);}finally{clearTimeout(clock);}}
async function shot(name){assert.ok(result.screenshots<4);result.screenshots++;await page.screenshot({path:path.join(root,name),fullPage:false,timeout:3000});const data=fs.readFileSync(path.join(root,name));result.screenshotFiles.push({name,bytes:data.length,sha256:require('node:crypto').createHash('sha256').update(data).digest('hex'),visualReview:'PENDING_PIXEL_REVIEW'});}
async function until(fn,arg){await page.waitForFunction(fn,arg,{timeout:8000});}
function row(id){return page.locator('#runs > .row').filter({hasText:id.slice(0,16)}).getByRole('button',{name:'查看任务',exact:true});}
async function choose(id){await row(id).click();await until(id=>protocolContext?.run?.run_id===id&&document.getElementById('protocol-run-id').textContent===id,id);}
async function audit(){
 const cdp=await browser.newBrowserCDPSession();
 const pids=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
 const file=path.join(root,'owned-browser-pids.json');fs.writeFileSync(file,JSON.stringify(pids));
 const remaining=Math.min(10000,info.until_ms-Date.now());assert.ok(remaining>0);
 const observed=JSON.parse(execFileSync(python,[path.resolve(__dirname,'..','windows_browser_ci.py'),'--root',root,'--audit',file],{encoding:'utf8',timeout:remaining,cwd:path.resolve(__dirname,'..','..')}));
 await cdp.detach();
 check('actual processes preserve sandbox and SDK protections',observed.length>0&&observed.every(p=>p.security_args_verified));
 const renderers=observed.filter(p=>p.type==='renderer');
 check('actual renderer token is restricted low integrity or AppContainer',renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)));
 result.sandbox.push(observed);
}
async function run(){
 const launchRemaining=Math.min(20000,info.until_ms-Date.now());assert.ok(launchRemaining>0);
 browser=await chromium.launch({channel:'msedge',chromiumSandbox:true,headless:true,ignoreDefaultArgs:removedSecurityDefaults,timeout:launchRemaining,env:process.env});
 if(cancelled)throw Error('Window stopped during browser launch');
 result.browserVersion=browser.version();
 const context=await browser.newContext({viewport:{width:1366,height:900},acceptDownloads:false,bypassCSP:false});
 await context.route('**/*',async route=>{
  try{
  const request=route.request(),url=new URL(request.url()),method=request.method();
  let allowed=url.origin===info.base;
  const business=url.pathname.startsWith('/api/')||url.pathname==='/health';
  let kind;
  if(allowed&&method==='GET')kind=business?'business_get':'static_get';
  else if(allowed&&method==='POST'&&url.pathname===completionPath)kind=postKind;
  else allowed=false;
  if(kind){result.counts[kind]++;allowed=result.counts[kind]<=(kind==='business_get'?30:kind===postKind?3:40);}
  if(!allowed||cancelled||Date.now()>=info.until_ms){result.counts.blocked++;result.rejectedRequest??={method,path:url.pathname,kind,counts:{...result.counts},cancelled,at_ms:Date.now(),until_ms:info.until_ms};await route.abort();throw Error('Business/request/time budget stop; no retry');}
  result.requests.push({method,path:url.pathname,kind});
  if(method==='POST'){
   bodies.push(request.postDataJSON());
   const body=bodies[bodies.length-1];
   assert.deepEqual(Object.keys(body).sort(),review?['contract_id','expected_fence','expected_result_fingerprint','expected_version','request_key']:['expected_fence','expected_version','request_key']);
   if(review){assert.equal(body.contract_id,info.contract_id);assert.equal(body.expected_result_fingerprint,info.expected_result_fingerprint);}
   assert.equal(body.expected_version,info.expected_version);assert.equal(body.expected_fence,info.expected_fence);
   assert.match(body.request_key,/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/);
   if(bodies.length>1)assert.deepEqual(body,bodies[0]);
   result.commandBodies=bodies;write();
   const response=await route.fetch({maxRedirects:0,maxRetries:0,timeout:8000});
   assert.equal(response.status(),review?201:200);const receipt=await response.json();result.receipts.push(receipt);
   if(review){
    assert.deepEqual(Object.keys(receipt).sort(),['id','run_id','contract_id','namespace','decision','reason','fingerprint','publishable','model_requests'].sort());
    assert.equal(receipt.namespace,'protocol-review.v1');assert.equal(receipt.run_id,info.run);assert.equal(receipt.contract_id,info.contract_id);
    assert.equal(receipt.decision,'PASS');assert.equal(receipt.publishable,false);assert.equal(receipt.model_requests,0);assert.match(receipt.fingerprint,/^[a-f0-9]{64}$/);
   }else if(source){
    assert.deepEqual(Object.keys(receipt).sort(),['namespace','run_id','status','version','fence','result_fingerprint','provider_requests','automatic_resend','cached'].sort());
    assert.equal(receipt.namespace,'protocol-source-completion.v2');assert.equal(receipt.run_id,info.run);
    assert.equal(receipt.status,'WAITING_APPROVAL');assert.equal(receipt.version,body.expected_version+1);
    assert.equal(receipt.fence,body.expected_fence+1);assert.match(receipt.result_fingerprint,/^[a-f0-9]{64}$/);
    assert.equal(receipt.provider_requests,0);assert.equal(receipt.automatic_resend,false);assert.equal(receipt.cached,bodies.length===2);
   }
   write();
   if(bodies.length===1){await route.abort('connectionfailed');return;}
   assert.equal(bodies.length,2);failGet=true;await route.fulfill({response});return;
  }
  if(business&&url.pathname===`/api/projects/${info.project}/protocol/runs/${info.run}`){
   if(failGet){failGet=false;await route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:{code:'CONTROLLED_RESPONSE_READ_FAILURE'}})});return;}
   if(holdGet){
    holdGet=false;const response=await route.fetch({maxRedirects:0,maxRetries:0,timeout:8000});
    heldRequest=request;held();await wait(new Promise(resolve=>releaseHeld=resolve));await wait(route.fulfill({response}));delivered();return;
   }
  }
  await route.continue();
  }catch(error){failWindow(error);try{await route.abort();}catch{}}
 });
 page=await context.newPage();page.setDefaultTimeout(8000);
 page.on('pageerror',e=>result.pageErrors.push(e.message));
 await page.goto(info.base,{waitUntil:'domcontentloaded'});
 await audit(); // Actual application renderer, not a blank-page substitute.
 await page.locator('#token').fill('secret test token');
 await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});
 check('original project selected from real authenticated UI',await page.locator('#project-select').inputValue()===info.project);
 await choose(info.run);
 check('explicit acknowledgement starts unchecked and submission disabled',!await page.locator(`#${control}-confirm`).isChecked()&&await page.locator(`#${control}-submit`).isDisabled());
 await page.locator(`#${control}`).scrollIntoViewIfNeeded();await shot('initial.png');
 await page.locator(`#${control}-confirm`).check();
 await page.locator(`#${control}-submit`).dblclick();
 await until(id=>!protocolContext.busy&&document.getElementById(id).textContent.includes('UNKNOWN'),control+'-status');
 check('double click made exactly one actual POST; lost receipt remains UNKNOWN',bodies.length===1&&await page.locator(`#${control}-submit`).isDisabled());
 await shot('unknown.png');
 if(source){
  await page.locator('[data-tab="apps"]').click();await page.locator('[data-tab="projects"]').click();
  check('real workspace close/return retains Source UNKNOWN command without another Run',await page.locator(`#${control}-retry`).isVisible()&&bodies.length===1);
 }else{
  await choose(info.other);await choose(info.run);
  check('same-page Run switch retains original UNKNOWN command',await page.locator(`#${control}-retry`).isVisible());
 }
 await page.locator(`#${control}-retry`).click();
 await until(id=>!protocolContext.busy&&document.getElementById(id).textContent.includes('成果读取未通过'),control+'-status');
 assert.deepEqual(bodies[1],bodies[0]);
 assert.deepEqual(result.receipts[1],review?result.receipts[0]:{...result.receipts[0],cached:true});
 check('same original body/key returned original receipt; result read failed closed',bodies.length===2&&(await page.locator('#protocol-result').textContent())===''&&await page.locator('#protocol-cold-form').isHidden()&&(!review||await page.locator('#protocol-extract').isHidden()));
 if(review){await page.locator(`#${control}`).scrollIntoViewIfNeeded();await shot('read-failed.png');}
 await page.locator(`#${control}-retry`).click();
 if(review)await until(fp=>!protocolContext.busy&&protocolContext.run?.status==='SUCCEEDED'&&protocolContext.run?.semantic_status==='PASS'&&protocolContext.run?.semantic_review==='APPROVED'&&protocolContext.run?.result_fingerprint===fp,info.expected_result_fingerprint);
 else if(source)await until(fp=>!protocolContext.busy&&protocolContext.run?.phase==='source'&&protocolContext.run?.status==='WAITING_APPROVAL'&&protocolContext.run?.result_fingerprint===fp&&!!protocolContext.run?.result?.protocol_result,result.receipts[0].result_fingerprint);
 else await until(()=>!protocolContext.busy&&protocolContext.run?.result?.compiled_plan);
 check('known accepted read failure recovers by GET only',bodies.length===2);
 const actual=JSON.parse(await page.locator('#protocol-result').textContent());
 assert.deepEqual(actual.protocol_result,info.captured.result);
 if(source){
  assert.equal(Object.hasOwn(actual,'compiled_plan'),false);
  const state=await page.evaluate(()=>({status:protocolContext.run.status,semantic:protocolContext.run.semantic_status,result_fingerprint:protocolContext.run.result_fingerprint}));
  assert.deepEqual(state,{status:review?'SUCCEEDED':'WAITING_APPROVAL',semantic:review?'PASS':'UNKNOWN',result_fingerprint:review?info.expected_result_fingerprint:result.receipts[0].result_fingerprint});
  check('exact original Source result and receipts rendered',true);
  if(review){
   check('registered PASS alone unlocks existing explicit extraction button, no automatic extraction or Cold',await page.locator('#protocol-extract').isVisible()&&await page.locator('#protocol-cold-form').isHidden());
   check('owner remains PENDING, publication disabled; no compiled plan',await page.evaluate(()=>protocolContext.run.owner_semantic_acceptance==='PENDING'&&protocolContext.run.formal_publication_enabled===false&&protocolContext.run.result.compiled_plan===undefined));
  }else check('Source technical completion unlocks neither extraction nor Cold',await page.locator('#protocol-extract').isHidden()&&await page.locator('#protocol-cold-form').isHidden());
  result.sourceResult=state;
 }else{
  assert.deepEqual(actual.compiled_plan,info.captured.compiled);
  check('exact original compiled plan and source receipt rendered',true);
 }
 check('completed command has no new submit control',review?(await page.locator(`#${control}-submit`).isHidden()&&await page.locator(`#${control}-retry`).isHidden()&&await page.locator(`#${control}-confirm`).isDisabled()):await page.locator(`#${control}`).isHidden());
 await page.locator(review?`#${control}`:'#protocol-detail').scrollIntoViewIfNeeded();await shot('completed.png');
 // Hold one genuine detail response, close/return the real workspace, then
 // release it. No page-global/controller function or timer is replaced.
 const reached=new Promise(resolve=>held=resolve),delivery=new Promise(resolve=>delivered=resolve);holdGet=true;
 await page.locator('#protocol-read').click();await wait(reached);
 await page.locator('[data-tab="apps"]').click();await page.locator('[data-tab="projects"]').click();
 const count=result.requests.length,returned=page.waitForResponse(response=>response.request()===heldRequest);
 releaseHeld();const [,response]=await wait(Promise.all([delivery,returned]));assert.equal(await wait(response.finished()),null);
 await wait(page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))));
 check('workspace close/return clears content and late detail cannot restore it',await page.locator('#protocol-result').textContent()===''&&await page.locator('#protocol-cold-form').isHidden()&&(!source||await page.locator('#protocol-extract').isHidden()));
 check('no new command after workspace return',bodies.length===2);
 result.closeReturnRequestOffset=count;
 check('no DOM script errors',result.pageErrors.length===0);
 check('all request limits respected without blocked overrun',result.counts.blocked===0&&result.counts.business_get<=30&&result.counts[postKind]<=3);
 // Page memory is deliberately not persisted: no refresh/close key recovery
 // claim, storage write, or second browser window.
 result.refreshKeyRecovery='NOT_SUPPORTED_PAGE_MEMORY_ONLY';
 if(cancelled)throw cancellation.signal.reason;
 result.status='PASS';
}
(async()=>{
 const budget=new Promise((_,reject)=>{
  fail=reject;timer=setTimeout(()=>failWindow(Error('Single absolute work deadline')),Math.max(1,info.until_ms-Date.now()));
  watcher=setInterval(()=>{if(fs.existsSync(path.join(root,'stop')))failWindow(Error('Owned window stop requested'));},100);
 });
 const work=run();
 try{await Promise.race([work,budget]);}
 catch(error){result.status='FAIL';result.error=error.stack;console.error(error.stack);if(page&&!page.isClosed()&&result.screenshots<4&&Date.now()<info.until_ms)try{await shot('failure.png');}catch{};}
 finally{
  clearTimeout(timer);clearInterval(watcher);cancelled=true;cancellation.abort(Error('Owned window cleanup'));if(releaseHeld)releaseHeld();
  // One shared ten seconds, not a new allowance for each process. Node uses
  // at most four, leaving the coordinator six for monitor/API/AnyIO cleanup.
  const deadlines=cleanupDeadlines(Date.now(),info.until_ms),cleanupUntil=deadlines.node;fs.writeFileSync(path.join(root,'cleanup-until.json'),JSON.stringify(deadlines.shared/1000));
  result.cleanupDeadlines={shared_ms:deadlines.shared,node_ms:deadlines.node};
  try{
   if(browser)await cleanupWait(browser.close(),cleanupUntil);
   await cleanupWait(work.catch(()=>{}),cleanupUntil); // No orphaned launch/run continuation.
   if(browser?.isConnected())await cleanupWait(browser.close(),cleanupUntil);
   result.browserClosed=true;
  }
  catch(error){result.status='UNKNOWN';result.cleanupError=error.message;}
  write();if(result.status!=='PASS')process.exitCode=1;
  // A failed browser.close may retain Node handles. Return control to the
  // parent for exact owned-process cleanup; never turn this into PASS.
  if(result.cleanupError)process.exit(1);
 }
})().catch(error=>{result.status='UNKNOWN';result.error=error.stack;write();process.exitCode=1;});
}
