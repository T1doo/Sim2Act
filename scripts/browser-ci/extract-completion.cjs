'use strict';
// Real DOM and production scripts, actual sealed SQLite API. No VM adapter.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFileSync}=require('node:child_process');
const {chromium}=require('playwright-core');
const root=process.argv[2],python=process.argv[3];
const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8'));
const result={status:'UNKNOWN',scope:'real installed Edge / production full page / sealed synthetic SQLite',checks:[],receipts:[],screenshots:0,counts:{business_get:0,static_get:0,completion_post:0,blocked:0},requests:[],pageErrors:[],sandbox:[]};
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
let browser,page,timer,watcher,failGet=false,holdGet=false,held,releaseHeld,cancelled=false,fail;
const bodies=[];
function check(name,condition){assert.ok(condition,name);result.checks.push(name);}
function write(){fs.writeFileSync(path.join(root,'browser.json'),JSON.stringify(result,null,2));}
function failWindow(error){cancelled=true;fail(error);}
async function cleanupWait(promise,until){let clock;try{return await Promise.race([promise,new Promise((_,reject)=>{clock=setTimeout(()=>reject(Error('Shared cleanup deadline')),Math.max(1,until-Date.now()));})]);}finally{clearTimeout(clock);}}
async function shot(name){assert.ok(result.screenshots<4);result.screenshots++;await page.screenshot({path:path.join(root,name),fullPage:false,timeout:3000});}
async function until(fn,arg){await page.waitForFunction(fn,arg,{timeout:8000});}
function row(id){return page.locator('#runs > .row').filter({hasText:id.slice(0,16)}).getByRole('button',{name:'查看任务',exact:true});}
async function choose(id){await row(id).click();await until(id=>protocolContext?.run?.run_id===id&&document.getElementById('protocol-run-id').textContent===id,id);}
async function audit(){
 const cdp=await browser.newBrowserCDPSession();
 const pids=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
 const file=path.join(root,'owned-browser-pids.json');fs.writeFileSync(file,JSON.stringify(pids));
 const remaining=Math.min(10000,info.until_ms-Date.now());assert.ok(remaining>0);
 const observed=JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',file],{encoding:'utf8',timeout:remaining}));
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
  else if(allowed&&method==='POST'&&url.pathname===`/api/projects/${info.project}/protocol/runs/${info.run}/complete-extraction`)kind='completion_post';
  else allowed=false;
  if(kind){result.counts[kind]++;allowed=result.counts[kind]<=(kind==='business_get'?30:kind==='completion_post'?3:40);}
  if(!allowed||cancelled||Date.now()>=info.until_ms){result.counts.blocked++;await route.abort();throw Error('Business/request/time budget stop; no retry');}
  result.requests.push({method,path:url.pathname,kind});
  if(method==='POST'){
   bodies.push(request.postDataJSON());
   const response=await route.fetch({maxRedirects:0,maxRetries:0,timeout:8000});
   assert.equal(response.status(),200);const receipt=await response.json();result.receipts.push(receipt);
   if(bodies.length===1){await route.abort('connectionfailed');return;}
   assert.equal(bodies.length,2);failGet=true;await route.fulfill({response});return;
  }
  if(business&&url.pathname===`/api/projects/${info.project}/protocol/runs/${info.run}`){
   if(failGet){failGet=false;await route.fulfill({status:403,contentType:'application/json',body:JSON.stringify({error:{code:'CONTROLLED_RESPONSE_READ_FAILURE'}})});return;}
   if(holdGet){
    holdGet=false;const response=await route.fetch({maxRedirects:0,maxRetries:0,timeout:8000});
    held();await new Promise(resolve=>releaseHeld=resolve);await route.fulfill({response});return;
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
 check('explicit acknowledgement starts unchecked and submission disabled',!await page.locator('#protocol-completion-confirm').isChecked()&&await page.locator('#protocol-completion-submit').isDisabled());
 await page.locator('#protocol-completion').scrollIntoViewIfNeeded();await shot('initial.png');
 await page.locator('#protocol-completion-confirm').check();
 await page.locator('#protocol-completion-submit').dblclick();
 await until(()=>!protocolContext.busy&&document.getElementById('protocol-completion-status').textContent.includes('UNKNOWN'));
 check('double click made exactly one actual POST; lost receipt remains UNKNOWN',bodies.length===1&&await page.locator('#protocol-completion-submit').isDisabled());
 await shot('unknown.png');
 await choose(info.other);await choose(info.run);
 check('same-page Run switch retains original UNKNOWN command',await page.locator('#protocol-completion-retry').isVisible());
 await page.locator('#protocol-completion-retry').click();
 await until(()=>!protocolContext.busy&&document.getElementById('protocol-completion-status').textContent.includes('成果读取未通过'));
 assert.deepEqual(bodies[1],bodies[0]);
 assert.deepEqual(result.receipts[1],{...result.receipts[0],cached:true});
 check('same original body/key returned exact cached receipt; result read failed closed',bodies.length===2&&!(await page.locator('#protocol-result').textContent()).includes('compiled_plan')&&await page.locator('#protocol-cold-form').isHidden());
 await page.locator('#protocol-completion-retry').click();
 await until(()=>!protocolContext.busy&&protocolContext.run?.result?.compiled_plan);
 check('known accepted read failure recovers by GET only',bodies.length===2);
 const actual=JSON.parse(await page.locator('#protocol-result').textContent());
 assert.deepEqual(actual.protocol_result,info.captured.result);assert.deepEqual(actual.compiled_plan,info.captured.compiled);
 check('exact original compiled plan and source receipt rendered',true);
 check('completed command has no new completion submit control',await page.locator('#protocol-completion').isHidden());
 await page.locator('#protocol-detail').scrollIntoViewIfNeeded();await shot('completed.png');
 // Hold one genuine detail response, close/return the real workspace, then
 // release it. No page-global/controller function or timer is replaced.
 const reached=new Promise(resolve=>held=resolve);holdGet=true;
 await page.locator('#protocol-read').click();await reached;
 await page.locator('[data-tab="apps"]').click();await page.locator('[data-tab="projects"]').click();
 const count=result.requests.length;releaseHeld();
 await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
 check('workspace close/return clears content and late detail cannot restore it',await page.locator('#protocol-result').textContent()===''&&await page.locator('#protocol-cold-form').isHidden());
 check('no new command after workspace return',bodies.length===2);
 result.closeReturnRequestOffset=count;
 check('no DOM script errors',result.pageErrors.length===0);
 check('all request limits respected without blocked overrun',result.counts.blocked===0&&result.counts.business_get<=30&&result.counts.completion_post<=3);
 // Page memory is deliberately not persisted: no refresh/close key recovery
 // claim, storage write, or second browser window.
 result.refreshKeyRecovery='NOT_SUPPORTED_PAGE_MEMORY_ONLY';
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
  clearTimeout(timer);clearInterval(watcher);if(releaseHeld)releaseHeld();
  cancelled=true;
  const cleanupUntil=Math.min(Date.now()+10000,info.until_ms+10000);fs.writeFileSync(path.join(root,'cleanup-until.json'),JSON.stringify(cleanupUntil/1000));
  try{
   if(browser)await cleanupWait(browser.close(),cleanupUntil);
   await cleanupWait(work.catch(()=>{}),cleanupUntil); // No orphaned launch/run continuation.
   if(browser?.isConnected())await cleanupWait(browser.close(),cleanupUntil);
   result.browserClosed=true;
  }
  catch(error){result.status='UNKNOWN';result.cleanupError=error.message;}
  write();if(result.status!=='PASS')process.exitCode=1;
 }
})().catch(error=>{result.status='UNKNOWN';result.error=error.stack;write();process.exitCode=1;});
