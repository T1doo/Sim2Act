'use strict';
// Official Playwright against installed Microsoft Edge, genuine renderer/HTTP only.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync, execFile} = require('node:child_process');
const {promisify} = require('node:util');
const execFileAsync = promisify(execFile);
const {chromium} = require('playwright-core');
const root = process.argv[2], python = process.argv[3];
const info = JSON.parse(fs.readFileSync(path.join(root, 'info.json'), 'utf8'));
const base = `http://127.0.0.1:${info.port}`;
const result = {kind:'Actual Windows Server installed Edge / protected Chromium / synthetic HTTP UI',
  commit:info.commit, inventory:info.inventory, chromiumSandbox:true, win11:'NOT_RUN',
  mobileDevice:'NOT_RUN - viewport only', modelRequests:0, checks:[], consoleErrors:[], sandbox:[]};
let browser, activePage;
// Exact defaults from integrity-locked 1.63.0. Remove browser protection weakening;
// preserve the installed Edge's normal sandbox, security features and privilege handling.
const removedSecurityDefaults = [
  '--enable-unsafe-swiftshader', '--unsafely-disable-devtools-self-xss-warnings',
  '--disable-ipc-flooding-protection', '--disable-client-side-phishing-detection',
  '--password-store=basic', '--use-mock-keychain',
  '--disable-features=' + ['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose',
    'DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter',
    'PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect',
    'Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn',
    'msEdgeUpdateLaunchServicesPreferredVersion'].join(',')
];
result.removedSDKSecurityDefaults = removedSecurityDefaults;
function check(name, condition) { assert.ok(condition, name); result.checks.push({name,status:'PASS'}); }
async function until(page, predicate, arg=null) { await page.waitForFunction(predicate, arg, {timeout:12000}); }
async function idle(page) { await until(page, () => engineering && !engineering.busy); }
async function login(page, bearer, alreadyLoaded=false) {
  if(!alreadyLoaded)await page.goto(base, {waitUntil:'networkidle'});
  await page.locator('#token').fill(bearer);
  await page.locator('#connect').click();
  await page.locator('#login').waitFor({state:'hidden'});
  await page.locator('[data-tab="apps"]').click();
  await page.locator('#app-list button').first().click();
  await page.locator('#internal-panel').waitFor({state:'visible'});
  await idle(page);
}
async function context(viewport) {
  const c = await browser.newContext({viewport, acceptDownloads:false, bypassCSP:false});
  await c.route('**/*', route => route.request().url().startsWith(base + '/') ? route.continue() : route.abort());
  const p = await c.newPage();
  p.setDefaultTimeout(12000);
  p.on('pageerror', e => result.consoleErrors.push({kind:'pageerror',message:e.message}));
  p.on('console', m => {if(m.type()==='error') result.consoleErrors.push({kind:'console',message:m.text(),url:m.location().url});});
  return {c,p};
}
async function layout(page, label) {
  const measure = await page.evaluate(() => {
    const panel = document.querySelector('#internal-panel');
    const rect = panel.getBoundingClientRect();
    const buttons = [...panel.querySelectorAll('button')].filter(b => b.getClientRects().length);
    return {viewport:innerWidth, documentWidth:document.documentElement.scrollWidth,
      panelWidth:rect.width, gridColumns:getComputedStyle(panel.querySelector('.grid')).gridTemplateColumns,
      buttons:buttons.map(b => ({width:b.getBoundingClientRect().width, height:b.getBoundingClientRect().height,
        left:b.getBoundingClientRect().left,right:b.getBoundingClientRect().right}))};
  });
  result[label] = measure;
  check(`${label} real layout has no horizontal page overflow`, measure.documentWidth <= measure.viewport + 1);
  check(`${label} rendered controls fit viewport and have usable height`, measure.buttons.length > 0 && measure.buttons.every(b => b.height >= 40 && b.left >= 0 && b.right <= measure.viewport+1));
  await page.locator('#internal-panel').scrollIntoViewIfNeeded();
  await page.screenshot({path:path.join(root,`${label}.png`),fullPage:true});
}
(async () => {
  // chromiumSandbox false is Playwright's default: explicit true is mandatory.
  // Only remove pinned SDK security-weakening defaults; no custom flags or unsafe fallback.
  browser = await chromium.launch({channel:'msedge',chromiumSandbox:true,headless:true,ignoreDefaultArgs:removedSecurityDefaults,timeout:20000,env:process.env});
  result.browserVersion = browser.version();
  const desktop = await context({width:1366,height:900});
  activePage = desktop.p;
  await activePage.goto(base, {waitUntil:'networkidle'});
  const cdp = await browser.newBrowserCDPSession();
  const processes = (await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
  const audit = path.join(root,'owned-browser-pids.json');
  fs.writeFileSync(audit,JSON.stringify(processes));
  result.sandbox = JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',audit], {encoding:'utf8',timeout:10000}));
  check('actual browser and renderer args contain no sandbox-disabling switches', result.sandbox.length>0 && result.sandbox.every(p=>p.security_args_verified));
  const actualBrowser = result.sandbox.find(p=>p.type==='browser');
  check('SDK security-weakening defaults absent from actual browser args', !!actualBrowser && !actualBrowser.command_switches.includes('--disable-features'));
  result.observedCommandSwitches=actualBrowser.command_switches;
  const renderers = result.sandbox.filter(p=>p.type==='renderer');
  check('actual Windows renderers have restricted low-integrity or AppContainer tokens', renderers.length>0 && renderers.every(p=>p.app_container || (p.restricted_token && p.integrity_rid<=4096)));
  await login(activePage, 'synthetic-browser-A', true);
  check('authenticated real page and explicit internal-only publication status render', (await activePage.locator('#internal-panel').innerText()).includes('正式发布与部署仍关闭'));
  await activePage.locator('#internal-prepare').click();
  await activePage.locator('#internal-approval').waitFor({state:'visible'});
  check('frozen trusted manifest checks shown before confirmation', (await activePage.locator('#internal-approval-detail').innerText()).includes('csv.exact_integer_sum.v1'));
  check('approval requires explicit acknowledgement', await activePage.locator('#internal-commit').isDisabled());
  await activePage.locator('#internal-approval-ack').check();
  await activePage.locator('#internal-commit').click();
  await activePage.locator('#internal-releases button').first().waitFor();
  await idle(activePage);
  await activePage.locator('#internal-releases button').first().click();
  await activePage.locator('#internal-run-form').waitFor({state:'visible'});
  await idle(activePage);
  const first = await activePage.evaluate(() => engineering.instance.id);
  const app = await activePage.evaluate(() => engineering.app);
  check('new instance initially has independent empty result ledger', (await activePage.locator('#internal-data').innerText()).trim()==='');
  await activePage.locator('#internal-run-submit').click();
  await until(activePage, () => engineering.run?.status === "QUEUED" && !engineering.busy);
  const cancelled = await activePage.evaluate(() => engineering.run.id);
  await activePage.locator('#internal-controls button').filter({hasText:'暂停'}).click();
  await until(activePage, () => engineering.run?.status === "PAUSED" && !engineering.busy);
  check('real pause persisted and resume control rendered', await activePage.locator('#internal-controls button').filter({hasText:'继续'}).isVisible());
  await activePage.locator('#internal-controls button').filter({hasText:'继续'}).click();
  await until(activePage, () => engineering.run?.status === "QUEUED" && !engineering.busy);
  check('real resume command persists queued status before pause/cancel', (await activePage.locator('#internal-run-status').innerText()).includes('QUEUED'));
  await activePage.locator('#internal-controls button').filter({hasText:'暂停'}).click();
  await until(activePage, () => engineering.run?.status === "PAUSED" && !engineering.busy);
  await activePage.locator('#internal-controls button').filter({hasText:'取消'}).click();
  await until(activePage, () => engineering.run?.status === "CANCELLED" && !engineering.busy);
  check('cancel persists terminal status and explicit cancel intent', (await activePage.locator('#internal-run-detail').textContent()).includes('"cancel_intent": true'));
  await activePage.locator('#internal-run-submit').click();
  await until(activePage, () => engineering.run?.status === "QUEUED" && !engineering.busy);
  const accepted = await activePage.evaluate(() => engineering.run.id);
  await activePage.locator('#internal-back').click();
  await activePage.locator('#internal-panel').waitFor({state:'hidden'});
  check('return hides selection after accepted work', !(await activePage.locator('#internal-panel').isVisible()));
  await activePage.locator('#app-list button').first().click();
  await activePage.locator('#internal-panel').waitFor({state:'visible'});
  await idle(activePage);
  await activePage.locator('#internal-instances button').first().click();
  await until(activePage, id => engineering.instance?.id === id && !engineering.busy, first);
  check('reopen reads accepted queued and cancelled persisted history', (await activePage.locator('#internal-runs').innerText()).includes('QUEUED') && (await activePage.locator('#internal-runs').innerText()).includes('CANCELLED'));
  execFileSync(python, ['scripts/windows_browser_ci.py','--root',root,'--worker-once'], {timeout:15000,stdio:'pipe'});
  await activePage.locator('#internal-refresh').click();
  await until(activePage, () => engineering.instance?.data.length === 1 && !engineering.busy);
  check('actual separate worker result 40 and immutable result v1 render', (await activePage.locator('#internal-data').innerText()).includes('40') && (await activePage.locator('#internal-data').innerText()).includes('结果 v1'));
  const runRead = await activePage.evaluate(async ids => {
    const r = await api(`/api/internal/instances/${ids.first}/runs/${ids.accepted}`);
    return {status:r.status,sum:r.result?.sum,version:r.result_version};
  }, {first,accepted});
  check('authenticated current Run readback succeeds without model', runRead.status==='SUCCEEDED' && runRead.sum==='40' && runRead.version===1);
  const originalRelease = await activePage.evaluate(()=>engineering.instance.release_id);
  let retainedBefore = await activePage.evaluate(()=>({data:engineering.instance.data,runs:engineering.instance.runs}));
  // A second compatible immutable Release is created through the existing manual UI.
  await activePage.locator('#internal-prepare').click();
  await activePage.locator('#internal-approval').waitFor({state:'visible'});
  await idle(activePage);
  await activePage.locator('#internal-approval-ack').check();
  await activePage.locator('#internal-commit').click();
  await until(activePage,()=>engineering.releases.length===2 && !engineering.busy);
  const targetRelease = await activePage.evaluate(old=>engineering.releases.find(r=>r.id!==old).id,originalRelease);
  // Refresh the selected instance to acquire its target options without default approval.
  await activePage.locator('#internal-refresh').click();await idle(activePage);
  check('switch target and acknowledgement have no default selection', await activePage.locator('#internal-switch-target').inputValue()==='' && !(await activePage.locator('#internal-switch-ack').isChecked()));
  const switchUrl = `${base}/api/internal/instances/${first}/switch-approvals`;
  let posted=0;
  activePage.on('request',request=>{if(request.url()===switchUrl && request.method()==='POST')posted++;});
  // Delay delivery only after the real server accepted the approval. Cancel/return cannot repaint it.
  let unblock, acceptedPrepare, deliveredPrepare, routeFailure;
  const received = new Promise(resolve=>{acceptedPrepare=resolve;});
  const gate = new Promise(resolve=>{unblock=resolve;});
  const delivered = new Promise(resolve=>{deliveredPrepare=resolve;});
  const delayedHandler=async route=>{try {if(route.request().method()!=='POST')return await route.continue();const response=await route.fetch();acceptedPrepare();await gate;await route.fulfill({response});} catch(error){routeFailure=error;acceptedPrepare();} finally {deliveredPrepare();}};
  await activePage.route(switchUrl,delayedHandler);
  await activePage.locator('#internal-switch-target').selectOption(targetRelease);
  await activePage.locator('#internal-switch-prepare').click();await received;
  await activePage.locator('#internal-switch-cancel').click();
  await activePage.locator('#internal-back').click();unblock();
  // Keep interception registered until its actual accepted response is delivered.
  await delivered;if(routeFailure)throw routeFailure;
  await activePage.unroute(switchUrl,delayedHandler);
  await activePage.locator('#app-list button').first().click();await idle(activePage);
  await activePage.locator('#internal-instances button').first().click();await idle(activePage);
  check('accepted late prepare cannot restore cancelled/returned approval', !(await activePage.locator('#internal-switch-approval').isVisible()) && await activePage.locator('#internal-switch-target').inputValue()==='');
  await activePage.locator('#internal-switch-target').selectOption(targetRelease);
  const beforePosts=posted;
  await activePage.evaluate(()=>{document.querySelector('#internal-switch-prepare').click();document.querySelector('#internal-switch-prepare').click();});
  await activePage.locator('#internal-switch-approval').waitFor({state:'visible'});await idle(activePage);
  check('duplicate prepare click creates one request and exact data scope is rendered', posted-beforePosts===1 && (await activePage.locator('#internal-switch-summary').innerText()).includes('保留 1 条结果'));
  check('switch requires fresh manual acknowledgement', await activePage.locator('#internal-switch-commit').isDisabled());
  const approval=await activePage.evaluate(()=>({id:engineering.switchApproval.id,fingerprint:engineering.switchApproval.fingerprint}));
  let commitPosts=0;activePage.on('request',r=>{if(r.url().endsWith(`/switch-approvals/${approval.id}/commit`))commitPosts++;});
  await activePage.locator('#internal-switch-ack').check();
  await activePage.evaluate(()=>{document.querySelector('#internal-switch-commit').click();document.querySelector('#internal-switch-commit').click();});
  await until(activePage,id=>engineering.instance?.release_id===id && !engineering.busy,targetRelease);
  check('compatible upgrade commits once and retains result and Run lineage', commitPosts===1 && await activePage.evaluate(before=>JSON.stringify(engineering.instance.data)===JSON.stringify(before.data) && JSON.stringify(engineering.instance.runs)===JSON.stringify(before.runs) && engineering.instance.revision===2,retainedBefore));
  await activePage.locator('#internal-run-submit').click();
  await until(activePage,()=>engineering.run?.status==='QUEUED' && !engineering.busy);
  const upgradedRun=await activePage.evaluate(()=>engineering.run.id);
  execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--worker-once'],{timeout:15000,stdio:'pipe'});
  await activePage.locator('#internal-refresh').click();
  await until(activePage,()=>engineering.instance?.data.length===2 && !engineering.busy);
  check('new accepted worker Run pins upgraded Release and appends result v2',await activePage.evaluate(args=>engineering.instance.data[1].release_id===args.targetRelease && engineering.instance.data[1].version===2 && engineering.instance.runs.some(r=>r.id===args.upgradedRun && r.status==='SUCCEEDED' && r.release_id===args.targetRelease),{targetRelease,upgradedRun}));
  retainedBefore=await activePage.evaluate(()=>({data:engineering.instance.data,runs:engineering.instance.runs}));
  const consumed=await activePage.evaluate(async args=>{const r=await fetch(`/api/internal/instances/${args.first}/switch-approvals/${args.approval.id}/commit`,{method:'POST',headers:{Authorization:'Bearer synthetic-browser-A','Content-Type':'application/json'},body:JSON.stringify({fingerprint:args.approval.fingerprint})});return r.status;},{first,approval});
  check('consumed exact switch approval cannot create a second history event',consumed===409);
  await activePage.locator('#internal-switch-target').selectOption(originalRelease);
  await activePage.locator('#internal-switch-prepare').click();await activePage.locator('#internal-switch-approval').waitFor({state:'visible'});await idle(activePage);
  await activePage.locator('#internal-switch-ack').check();await activePage.locator('#internal-switch-commit').click();
  await until(activePage,id=>engineering.instance?.release_id===id && engineering.instance.revision===3 && !engineering.busy,originalRelease);
  check('compatible rollback retains exact data and three pointer history events',await activePage.evaluate(before=>JSON.stringify(engineering.instance.data)===JSON.stringify(before.data) && JSON.stringify(engineering.instance.runs)===JSON.stringify(before.runs) && engineering.instance.history.length===3,retainedBefore));
  // Existing service creates a synthetic incompatible target, not a production fixture endpoint.
  const bad=JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--incompatible-release',originalRelease],{encoding:'utf8',timeout:15000}));
  await activePage.locator('#internal-refresh').click();await idle(activePage);
  await activePage.locator('#internal-switch-target').selectOption(bad.id);
  await activePage.locator('#internal-switch-prepare').click();await idle(activePage);
  check('incompatible target has readable rejection and no approval/pointer change',(await activePage.locator('#internal-switch-status').innerText()).includes('Incompatible instance schema') && !(await activePage.locator('#internal-switch-approval').isVisible()) && await activePage.evaluate(()=>engineering.instance.revision===3));
  // Explicit one-approval synthetic TTL fault before its first receipt; no production clock/lifetime override.
  execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--next-short-switch-ttl'],{timeout:10000,stdio:'pipe'});
  await activePage.locator('#internal-switch-target').selectOption(targetRelease);
  await activePage.locator('#internal-switch-prepare').click();await activePage.locator('#internal-switch-approval').waitFor({state:'visible'});await idle(activePage);
  const expired=await activePage.evaluate(()=>({id:engineering.switchApproval.id,fingerprint:engineering.switchApproval.fingerprint,expires_at:engineering.switchApproval.expires_at}));
  await activePage.locator('#internal-switch-ack').check();
  await until(activePage,()=>engineering.switchApproval.expires_at*1000<=Date.now() && document.querySelector('#internal-switch-commit').disabled);
  const expiryResponse=await activePage.evaluate(async args=>{const r=await fetch(`/api/internal/instances/${args.first}/switch-approvals/${args.expired.id}/commit`,{method:'POST',headers:{Authorization:'Bearer synthetic-browser-A','Content-Type':'application/json'},body:JSON.stringify({fingerprint:args.expired.fingerprint})});return {status:r.status,text:await r.text()};},{first,expired});
  check('expired synthetic TTL approval disabled in UI and exact server commit rejected',expiryResponse.status===409 && expiryResponse.text.includes('expired') && (await activePage.locator('#internal-switch-status').innerText()).includes('到期'));
  result.expiryOracle={kind:'one owned synthetic approval TTL narrowed to 3 seconds before receipt',productionTTLSeconds:300,productionClockChanged:false,approval:expired,status:expiryResponse.status};
  await activePage.locator('#internal-switch-cancel').click();
  await activePage.locator('#internal-refresh').click();await idle(activePage);
  check('refresh after rejected/expired intents preserves original release/data/history',await activePage.evaluate(args=>engineering.instance.release_id===args.originalRelease && engineering.instance.revision===3 && engineering.instance.history.length===3 && JSON.stringify(engineering.instance.data)===JSON.stringify(args.retainedBefore.data),{originalRelease,retainedBefore}));
  await layout(activePage, 'desktop');
  // Independent cold context, actual mobile viewport; not a physical phone/Win11.
  const mobile = await context({width:390,height:844});
  activePage = mobile.p;
  await login(activePage,'synthetic-browser-A');
  await activePage.locator('#internal-instances button').first().click();
  await until(activePage,() => engineering.instance?.data.length === 2 && !engineering.busy);
  check('cold mobile context reads server result/history rather than JS memory', (await activePage.locator('#internal-data').innerText()).includes('40') && (await activePage.locator('#internal-runs').innerText()).includes('CANCELLED'));
  check('cold mobile reads compatible upgrade/rollback history',await activePage.evaluate(()=>engineering.instance.revision===3 && engineering.instance.history.length===3) && (await activePage.locator('#internal-switch-history').innerText()).includes('revision 3'));
  await layout(activePage,'mobile');
  // Another instance remains independent; requests are rejected by existing real API.
  await activePage.locator('#internal-releases button').first().click();
  await idle(activePage);
  await until(activePage, id => engineering.instance?.id !== id && !engineering.busy, first);
  const second = await activePage.evaluate(()=>engineering.instance.id);
  check('second instance has no inherited results', (await activePage.locator('#internal-data').innerText()).trim()==='');
  const wrong = await activePage.evaluate(async ids => {
    const r = await fetch(`/api/internal/instances/${ids.second}/runs/${ids.accepted}`,{headers:{Authorization:'Bearer synthetic-browser-A'}});
    return {status:r.status,text:await r.text()};
  },{second,accepted});
  check('wrong instance cannot read accepted result', wrong.status===403 && !wrong.text.includes('"result"') && !wrong.text.includes('"sum"'));
  const foreign = await context({width:1366,height:900});
  activePage = foreign.p;
  await login(activePage,'synthetic-browser-B');
  check('foreign owner page lists only own synthetic application', !(await activePage.locator('#app-list').innerText()).includes('browser A'));
  const denied = await activePage.evaluate(async ids => {
    const urls=[`/api/internal/instances/${ids.first}`,`/api/internal/instances/${ids.first}/runs/${ids.accepted}`,`/api/internal/instances/${ids.first}/runs/${ids.accepted}/control-status`];
    return await Promise.all(urls.map(async url=>{const r=await fetch(url,{headers:{Authorization:'Bearer synthetic-browser-B'}});return {status:r.status,text:await r.text()};}));
  },{first,accepted});
  check('foreign owner instance/history/control reject without another result', denied.every(r=>r.status===403 && !r.text.includes('"result"') && !r.text.includes('"sum"')));
  check('foreign UI does not render another result', !(await activePage.locator('#internal-data').innerText()).includes('40'));
  // Reopened A task is terminal and stop button cannot issue another mutation.
  const retained = await desktop.p.evaluate(async ids=>await api(`/api/internal/instances/${ids.first}/runs/${ids.cancelled}`),{first,cancelled});
  check('cancelled history preserved after independent worker completion', retained.status==='CANCELLED' && retained.cancel_intent===true);
  // Expected 403 fetches are negative cases, not script/runtime failures.
  const expectedErrorUrls = new Set([base+'/favicon.ico', `${base}/api/internal/instances/${second}/runs/${accepted}`, `${base}/api/internal/instances/${first}`, `${base}/api/internal/instances/${first}/runs/${accepted}`, `${base}/api/internal/instances/${first}/runs/${accepted}/control-status`]);
  expectedErrorUrls.add(switchUrl);expectedErrorUrls.add(`${switchUrl}/${approval.id}/commit`);expectedErrorUrls.add(`${switchUrl}/${expired.id}/commit`);
  result.unexpectedConsoleErrors = result.consoleErrors.filter(e=>e.kind==='pageerror' || !expectedErrorUrls.has(e.url));
  check('no browser script/runtime errors beyond recorded expected HTTP negatives', result.unexpectedConsoleErrors.length===0);
  // New ordinary history flow shares the already protected installed Edge.
  // Preserve all preceding internal checks; final desktop/mobile slots now show this slice.
  const historyInfo={...info.task_history,base};
  const historyPage=desktop.p;activePage=historyPage;
  await historyPage.addInitScript(()=>{window.setInterval=()=>0;});
  await historyPage.goto(base,{waitUntil:'networkidle'});
  const historyErrors=[];let historyOutsideRequests=0;
  historyPage.on('pageerror',e=>historyErrors.push({kind:'pageerror',message:e.message}));
  historyPage.on('console',m=>{if(m.type()==='error')historyErrors.push({kind:'console',message:m.text(),url:m.location().url});});
  historyPage.on('request',r=>{if(!r.url().startsWith(base+'/'))historyOutsideRequests++;});
  const auditHistory=async()=>{
    const observed=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
    const file=path.join(root,'owned-history-browser-pids.json');fs.writeFileSync(file,JSON.stringify(observed));
    return JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',file],{encoding:'utf8',timeout:10000}));
  };
  const assertHistorySandbox=(observed,label)=>{
    check(`task history ${label} actual args preserve sandbox`,observed.length>0&&observed.every(p=>p.security_args_verified));
    const renderers=observed.filter(p=>p.type==='renderer');
    check(`task history ${label} actual renderer tokens remain protected`,renderers.length>0&&renderers.every(p=>p.app_container||(p.restricted_token&&p.integrity_rid<=4096)));
    const main=observed.find(p=>p.type==='browser');
    check(`task history ${label} SDK weakening remains absent`,!!main&&!main.command_switches.includes('--disable-features'));
  };
  const historyBefore=await auditHistory();assertHistorySandbox(historyBefore,'before');
  result.taskHistory=await require('./task-history-ui.cjs')({
    evaluate:code=>historyPage.evaluate(code),reload:()=>historyPage.reload({waitUntil:'networkidle'}),info:historyInfo,
    workerOnce:async id=>{await execFileAsync(python,['scripts/windows_browser_ci.py','--root',root,'--task-history-worker-once',id],{encoding:'utf8',timeout:15000});},
    snapshot:async()=>JSON.parse((await execFileAsync(python,['scripts/windows_browser_ci.py','--root',root,'--task-history-snapshot'],{encoding:'utf8',timeout:10000})).stdout)
  });
  const historyLayout=async(page,label)=>{
    await page.locator('[data-tab="projects"]').click();
    const measure=await page.evaluate(()=>({viewport:innerWidth,documentWidth:document.documentElement.scrollWidth,
      rows:document.querySelectorAll('#runs .row').length,goal:document.querySelector('#runs').textContent,
      buttons:[...document.querySelectorAll('#run-form button,#runs button,#run-history-refresh')].filter(b=>b.getClientRects().length).map(b=>({left:b.getBoundingClientRect().left,right:b.getBoundingClientRect().right,height:b.getBoundingClientRect().height}))}));
    check(`task history ${label} has real rows and no horizontal overflow`,measure.rows===7&&measure.documentWidth<=measure.viewport+1);
    check(`task history ${label} readable controls fit viewport`,measure.buttons.length>0&&measure.buttons.every(b=>b.height>=40&&b.left>=0&&b.right<=measure.viewport+1));
    await page.locator('#runs').scrollIntoViewIfNeeded();
    await page.screenshot({path:path.join(root,`${label}.png`),fullPage:true});return measure;
  };
  result.taskHistory.desktop=await historyLayout(historyPage,'desktop');
  activePage=mobile.p;
  activePage.on('pageerror',e=>historyErrors.push({kind:'pageerror',message:e.message}));
  activePage.on('console',m=>{if(m.type()==='error')historyErrors.push({kind:'console',message:m.text(),url:m.location().url});});
  activePage.on('request',r=>{if(!r.url().startsWith(base+'/'))historyOutsideRequests++;});
  await activePage.addInitScript(()=>{window.setInterval=()=>0;});
  await activePage.goto(base,{waitUntil:'networkidle'});
  await activePage.locator('#token').fill('synthetic-browser-A');await activePage.locator('#connect').click();
  await activePage.locator('#login').waitFor({state:'hidden'});
  await activePage.locator('#project-select').selectOption(historyInfo.project);
  await until(activePage,()=>document.querySelector('#runs').textContent.includes('Newest history'));
  check('task history cold narrow context locates persisted goal/mode without cached intent',await activePage.evaluate(()=>ordinarySubmissions.size===0&&document.querySelector('#runs').textContent.includes('提交模式 MOCK')));
  await activePage.evaluate(id=>{const target=[...document.querySelectorAll('#runs .row')].find(r=>r.textContent.includes('Lost acceptance, preserve exact input'));if(!target)throw Error('Missing recovered history');target.querySelector('button').click();},result.taskHistory.bindings.firstRun);
  await until(activePage,id=>document.querySelector('#raw-result').textContent.includes(id)&&document.querySelector('#result').textContent.includes('部分完成'),result.taskHistory.bindings.firstRun);
  result.taskHistory.mobile=await historyLayout(activePage,'mobile');
  result.taskHistory.sandboxBefore=historyBefore;result.taskHistory.sandboxAfter=await auditHistory();assertHistorySandbox(result.taskHistory.sandboxAfter,'after');
  result.taskHistory.outsideRequests=historyOutsideRequests;
  const expectedHistoryError=e=>{if(e.kind!=='console')return false;let u;try{u=new URL(e.url);}catch{return false;}return u.origin===new URL(base).origin&&((u.pathname==='/favicon.ico'&&e.message.includes('404'))||((u.pathname==='/api/projects'||u.pathname===`/api/projects/${historyInfo.project}/runs`)&&(e.message.includes('403')||e.message.includes('422'))));};
  result.taskHistory.consoleErrors=historyErrors;result.taskHistory.unexpectedConsoleErrors=historyErrors.filter(e=>!expectedHistoryError(e));
  check('task history no outside request or unexpected browser script error',historyOutsideRequests===0&&result.taskHistory.unexpectedConsoleErrors.length===0);
  result.taskHistory.screenshots=['desktop.png','mobile.png'];result.taskHistory.visualReview='NOT_REVIEWED';
  result.status='PASS';
  result.syntheticBindings={app,first,second,cancelled,accepted};
  result.agent=await require('./agent-ui.cjs')({browser,root:path.join(root,'agent'),outputRoot:root,python,
    audit:async()=>{
      const observed=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
      const file=path.join(root,'owned-agent-browser-pids.json');fs.writeFileSync(file,JSON.stringify(observed));
      return JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',file],{encoding:'utf8',timeout:10000}));
    }});
  result.taskHistory.screenshotsSupersededBy='agent.integration integrated-cold-application-use desktop/mobile; history layout checks retained';
  result.taskHistory.screenshots=[];
  const protocolRoot=path.join(root,'protocol');
  const protocolInfo=JSON.parse(fs.readFileSync(path.join(protocolRoot,'info.json'),'utf8'));
  const protocolBase=`http://127.0.0.1:${protocolInfo.port}`;
  const protocolContext=await browser.newContext({viewport:{width:1440,height:1000},acceptDownloads:false,bypassCSP:false});
  try {
    await protocolContext.route('**/*',route=>route.request().url().startsWith(protocolBase+'/')?route.continue():route.abort());
    const protocolPage=await protocolContext.newPage();activePage=protocolPage;protocolPage.setDefaultTimeout(12000);
    const protocolErrors=[];
    protocolPage.on('pageerror',e=>protocolErrors.push({kind:'pageerror',message:e.message}));
    protocolPage.on('console',m=>{if(m.type()==='error')protocolErrors.push({kind:'console',message:m.text(),url:m.location().url});});
    const auditProtocol=async()=>{
      const observed=(await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
      const file=path.join(protocolRoot,'owned-browser-pids.json');fs.writeFileSync(file,JSON.stringify(observed));
      return JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',file],{encoding:'utf8',timeout:10000}));
    };
    const action=async(name,args=[])=>{
      const r=await execFileAsync(python,['scripts/protocol-ui/fixture.py','--root',protocolRoot,'--action',name,...args],{encoding:'utf8',timeout:30000,env:{...process.env,PYTHONPATH:'src'}});return r.stdout.trim();
    };
    const sandboxBefore=await auditProtocol();
    result.protocol=await require('./protocol-ui.cjs')({page:protocolPage,base:protocolBase,info:protocolInfo,action});
    result.protocol.sandboxBefore=sandboxBefore;result.protocol.sandboxAfter=await auditProtocol();
    const expectedProtocolError=e=>{
      if(e.kind!=='console')return false;
      const u=new URL(e.url||protocolBase);
      if(u.origin!==new URL(protocolBase).origin)return false;
      const failedReceipt=e.message.includes('net::ERR_FAILED')&&(u.pathname===`/api/projects/${protocolInfo.project}/protocol/source`||/^\/api\/projects\/[^/]+\/protocol\/runs\/[^/]+\/recover$/.test(u.pathname));
      const denied=e.message.includes('403')&&(u.pathname===`/api/projects/${protocolInfo.project}/protocol/contracts`||u.pathname===`/api/projects/${protocolInfo.other_project}/protocol/runs/${result.protocol.metadata.source?.id}`);
      const missingIcon=e.message.includes('404')&&u.pathname==='/favicon.ico';
      const conditionalNegative=result.protocol.conditional?.expectedNegativeURLs.includes(u.pathname)&&(e.message.includes('403')||e.message.includes('409'));
      return failedReceipt||denied||missingIcon||conditionalNegative;
    };
    // Old sealed experiment DB is retained; one normally seeded independent test pool.
    check('old protocol26 complete before independent test fixture transition',result.protocol.status==='PASS'&&result.protocol.checks.length===26);
    await protocolPage.goto('about:blank');
    const fresh=await require('./protocol-transition.cjs')(protocolRoot);
    result.protocol.fixtureTransition=fresh.receipt;
    await protocolPage.goto(protocolBase+'/',{waitUntil:'networkidle'});
    const conditionalSandboxBefore=await auditProtocol();
    const conditionalFixture=require('./conditional-fixture-session.cjs')({python,root:fresh.freshRoot});
    try{
      result.protocol.boundRuns=await require('./conditional-runs-ui.cjs')({evaluate:code=>protocolPage.evaluate(code),reload:()=>protocolPage.goto(protocolBase+'/',{waitUntil:'networkidle'}),info:fresh.info,action:conditionalFixture.action});
      result.protocol.boundRuns.sourceSHA256=require('node:crypto').createHash('sha256').update(fs.readFileSync('scripts/browser-ci/conditional-runs-ui.cjs')).digest('hex');
      check('actual bound Run source/check/extract/cold/check preserves UNKNOWN and NOT_ACCEPTED',result.protocol.boundRuns.status==='PASS'&&result.protocol.boundRuns.actual_mock_requests===4&&result.protocol.boundRuns.semanticStatus==='UNKNOWN'&&result.protocol.boundRuns.overallAcceptance==='NOT_ACCEPTED');
      result.protocol.conditional=await require('./conditional-checks-ui.cjs')({evaluate:code=>protocolPage.evaluate(code),reload:()=>protocolPage.goto(protocolBase+'/',{waitUntil:'networkidle'}),info:fresh.info,action:conditionalFixture.action,
        capture:async(label,milestone)=>{
          const width=label==='protocol-desktop'?1280:390;
          await protocolPage.setViewportSize({width,height:label==='protocol-desktop'?1000:844});
          const bounds=await protocolPage.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,
            overflow:[...document.querySelectorAll('#conditional-panel button,#conditional-panel select,#conditional-panel input,#conditional-panel textarea,#condition-source,#condition-results')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));
          check(`${label}: conditional report and controls fit actual viewport`,bounds.width===width&&bounds.documentWidth<=width+1&&bounds.overflow===0);
          const sandbox=await auditProtocol();
          require('./conditional-checks-ui.cjs').assertSandboxSafety(sandbox,check,`conditional ${label} capture`);
          await protocolPage.screenshot({path:path.join(protocolRoot,`${label}.png`),fullPage:true});
          await protocolPage.setViewportSize({width:1280,height:900});
          return {label,scope:milestone.scope,milestone,bounds,emitted:false,visualReview:'NOT_REVIEWED',sandbox};
        }});
      result.protocol.conditional.fixtureTimings=conditionalFixture.timings;
    }finally{result.protocol.fixtureDiagnostics=conditionalFixture.diagnostics;await conditionalFixture.close();}
    await require('./protocol-transition.cjs').verifyOld({root:protocolRoot,python,receipt:result.protocol.fixtureTransition});
    result.protocol.screenshotsSupersededBy='conditional-hand-report PASS/BLOCK desktop and PASS/UNKNOWN narrow; old protocol26 and layouts retained';
    result.protocol.screenshots=result.protocol.conditional.screenshots;
    result.protocol.conditional.sandboxBefore=conditionalSandboxBefore;
    result.protocol.conditional.sandboxAfter=await auditProtocol();
    for(const [label,observed] of [['before',conditionalSandboxBefore],['after',result.protocol.conditional.sandboxAfter]]){
      require('./conditional-checks-ui.cjs').assertSandboxSafety(observed,check,`conditional ${label}`);
    }
    check('bounded conditional native phase passes without semantic promotion',result.protocol.conditional.status==='PASS'&&result.protocol.conditional.semanticStatus==='UNKNOWN'&&result.protocol.conditional.ownerAcceptance==='PENDING');
    result.protocol.consoleErrors=protocolErrors;result.protocol.unexpectedConsoleErrors=protocolErrors.filter(e=>!expectedProtocolError(e));
    check('protocol native has no unexpected script or console failures',result.protocol.unexpectedConsoleErrors.length===0);
    fs.writeFileSync(path.join(protocolRoot,'protocol-results.json'),JSON.stringify(result.protocol,null,2)+'\n');
    check('separate protocol/recover native flow passes',result.protocol.status==='PASS');
  } finally {await protocolContext.close();}
})().catch(async error => {
  result.status='FAIL';result.error={name:error.name,message:error.message};
  if(activePage && !activePage.isClosed()) {
    try {await activePage.screenshot({path:path.join(root,'failure.png'),fullPage:true});} catch {}
  }
  process.exitCode=1;
}).finally(async () => {
  try {if(browser) await browser.close();}
  catch(error){result.status='FAIL';result.cleanupError=error.name;process.exitCode=1;}
  finally {
    fs.writeFileSync(path.join(root,'browser-results.json'),JSON.stringify(result,null,2)+'\n');
    console.log(`Protected browser ${result.status}: ${result.checks.length} legacy checks; additional agent recorded separately; Win11 NOT_RUN; model requests 0.`);
  }
});
