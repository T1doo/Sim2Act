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
async function until(page, expression) { await page.waitForFunction(expression, null, {timeout:12000}); }
async function idle(page) { await until(page, 'engineering && !engineering.busy'); }
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
  const c = await browser.newContext({viewport, acceptDownloads:false});
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
  check(`${label} real layout has no horizontal page overflow`, measure.documentWidth <= measure.viewport + 1);
  check(`${label} rendered controls fit viewport and have usable height`, measure.buttons.length > 0 && measure.buttons.every(b => b.height >= 40 && b.left >= 0 && b.right <= measure.viewport+1));
  result[label] = measure;
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
  const commandLine = (await cdp.send('Browser.getBrowserCommandLine')).arguments;
  check('actual browser command line contains no sandbox disabling switches', !commandLine.some(a => /^--(?:no-sandbox|disable-.*sandbox|no-zygote|allow-no-sandbox-job)(?:=|$)/.test(a)));
  check('SDK security-weakening defaults are absent from actual browser args', !commandLine.some(a => removedSecurityDefaults.includes(a) || a.startsWith('--disable-features=')));
  result.observedCommandSwitches = commandLine.filter(a=>a.startsWith('--')).map(a=>a.split('=')[0]);
  const processes = (await cdp.send('SystemInfo.getProcessInfo')).processInfo.filter(p=>['browser','renderer'].includes(p.type));
  const audit = path.join(root,'owned-browser-pids.json');
  fs.writeFileSync(audit,JSON.stringify(processes));
  result.sandbox = JSON.parse(execFileSync(python,['scripts/windows_browser_ci.py','--root',root,'--audit',audit], {encoding:'utf8',timeout:10000}));
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
  await until(activePage, 'engineering.run?.status === "QUEUED" && !engineering.busy');
  const cancelled = await activePage.evaluate(() => engineering.run.id);
  await activePage.locator('#internal-controls button').filter({hasText:'暂停'}).click();
  await until(activePage, 'engineering.run?.status === "PAUSED" && !engineering.busy');
  check('real pause persisted and resume control rendered', await activePage.locator('#internal-controls button').filter({hasText:'继续'}).isVisible());
  await activePage.locator('#internal-controls button').filter({hasText:'取消'}).click();
  await until(activePage, 'engineering.run?.status === "CANCELLED" && !engineering.busy');
  check('cancel persists terminal status and explicit cancel intent', (await activePage.locator('#internal-run-detail').textContent()).includes('"cancel_intent": true'));
  await activePage.locator('#internal-run-submit').click();
  await until(activePage, 'engineering.run?.status === "QUEUED" && !engineering.busy');
  const accepted = await activePage.evaluate(() => engineering.run.id);
  await activePage.locator('#internal-back').click();
  await activePage.locator('#internal-panel').waitFor({state:'hidden'});
  check('return hides selection after accepted work', !(await activePage.locator('#internal-panel').isVisible()));
  await activePage.locator('#app-list button').first().click();
  await activePage.locator('#internal-panel').waitFor({state:'visible'});
  await idle(activePage);
  await activePage.locator('#internal-instances button').first().click();
  await until(activePage, `engineering.instance?.id === ${JSON.stringify(first)} && !engineering.busy`);
  check('reopen reads accepted queued and cancelled persisted history', (await activePage.locator('#internal-runs').innerText()).includes('QUEUED') && (await activePage.locator('#internal-runs').innerText()).includes('CANCELLED'));
  execFileSync(python, ['scripts/windows_browser_ci.py','--root',root,'--worker-once'], {timeout:15000,stdio:'pipe'});
  await activePage.locator('#internal-refresh').click();
  await until(activePage, 'engineering.instance?.data.length === 1 && !engineering.busy');
  check('actual separate worker result 40 and immutable result v1 render', (await activePage.locator('#internal-data').innerText()).includes('40') && (await activePage.locator('#internal-data').innerText()).includes('结果 v1'));
  const runRead = await activePage.evaluate(async ids => {
    const r = await api(`/api/internal/instances/${ids.first}/runs/${ids.accepted}`);
    return {status:r.status,sum:r.result?.sum,version:r.result_version};
  }, {first,accepted});
  check('authenticated current Run readback succeeds without model', runRead.status==='SUCCEEDED' && runRead.sum==='40.00' && runRead.version===1);
  await layout(activePage, 'desktop');
  // Independent cold context, actual mobile viewport; not a physical phone/Win11.
  const mobile = await context({width:390,height:844});
  activePage = mobile.p;
  await login(activePage,'synthetic-browser-A');
  await activePage.locator('#internal-instances button').first().click();
  await until(activePage,'engineering.instance?.data.length === 1 && !engineering.busy');
  check('cold mobile context reads server result/history rather than JS memory', (await activePage.locator('#internal-data').innerText()).includes('40') && (await activePage.locator('#internal-runs').innerText()).includes('CANCELLED'));
  await layout(activePage,'mobile');
  // Another instance remains independent; requests are rejected by existing real API.
  await activePage.locator('#internal-releases button').first().click();
  await idle(activePage);
  await until(activePage, `engineering.instance?.id !== ${JSON.stringify(first)} && !engineering.busy`);
  const second = await activePage.evaluate(()=>engineering.instance.id);
  check('second instance has no inherited results', (await activePage.locator('#internal-data').innerText()).trim()==='');
  const wrong = await activePage.evaluate(async ids => {
    const r = await fetch(`/api/internal/instances/${ids.second}/runs/${ids.accepted}`,{headers:{Authorization:'Bearer synthetic-browser-A'}});
    return {status:r.status,text:await r.text()};
  },{second,accepted});
  check('wrong instance cannot read accepted result', wrong.status===403 && !wrong.text.includes('40.00'));
  const foreign = await context({width:1366,height:900});
  activePage = foreign.p;
  await login(activePage,'synthetic-browser-B');
  check('foreign owner page lists only own synthetic application', !(await activePage.locator('#app-list').innerText()).includes('browser A'));
  const denied = await activePage.evaluate(async ids => {
    const urls=[`/api/internal/instances/${ids.first}`,`/api/internal/instances/${ids.first}/runs/${ids.accepted}`,`/api/internal/instances/${ids.first}/runs/${ids.accepted}/control-status`];
    return await Promise.all(urls.map(async url=>{const r=await fetch(url,{headers:{Authorization:'Bearer synthetic-browser-B'}});return {status:r.status,text:await r.text()};}));
  },{first,accepted});
  check('foreign owner instance/history/control reject without another result', denied.every(r=>r.status===403 && !r.text.includes('40.00')));
  check('foreign UI does not render another result', !(await activePage.locator('#internal-data').innerText()).includes('40'));
  // Reopened A task is terminal and stop button cannot issue another mutation.
  const retained = await desktop.p.evaluate(async ids=>await api(`/api/internal/instances/${ids.first}/runs/${ids.cancelled}`),{first,cancelled});
  check('cancelled history preserved after independent worker completion', retained.status==='CANCELLED' && retained.cancel_intent===true);
  // Expected 403 fetches are negative cases, not script/runtime failures.
  const expectedErrorUrls = new Set([base+'/favicon.ico', `${base}/api/internal/instances/${second}/runs/${accepted}`, `${base}/api/internal/instances/${first}`, `${base}/api/internal/instances/${first}/runs/${accepted}`, `${base}/api/internal/instances/${first}/runs/${accepted}/control-status`]);
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
