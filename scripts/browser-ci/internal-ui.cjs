'use strict';
// Official Playwright against installed Microsoft Edge, genuine renderer/HTTP only.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const {execFileSync} = require('node:child_process');
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
async function login(page, bearer) {
  await page.goto(base, {waitUntil:'networkidle'});
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
  await login(activePage, 'synthetic-browser-A');
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
  let unblock, acceptedPrepare;
  const received = new Promise(resolve=>{acceptedPrepare=resolve;});
  const gate = new Promise(resolve=>{unblock=resolve;});
  await activePage.route(switchUrl,async route=>{if(route.request().method()!=='POST')return route.continue();const response=await route.fetch();acceptedPrepare();await gate;await route.fulfill({response});});
  await activePage.locator('#internal-switch-target').selectOption(targetRelease);
  await activePage.locator('#internal-switch-prepare').click();await received;
  await activePage.locator('#internal-switch-cancel').click();
  await activePage.locator('#internal-back').click();unblock();
  await activePage.unroute(switchUrl);
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
  result.status='PASS';
  result.syntheticBindings={app,first,second,cancelled,accepted};
})().catch(async error => {
  result.status='FAIL';result.error={name:error.name,message:error.message};
  if(activePage && !activePage.isClosed()) {
    try {await activePage.screenshot({path:path.join(root,'failure.png'),fullPage:true});} catch {}
  }
  process.exitCode=1;
}).finally(async () => {
  if(browser) await browser.close();
  fs.writeFileSync(path.join(root,'browser-results.json'),JSON.stringify(result,null,2)+'\n');
  console.log(`Protected browser ${result.status}: ${result.checks.length} passed checks; Win11 NOT_RUN; model requests 0.`);
});
