'use strict';
// Genuine installed browser only. Functional DOM tests never count as these checks.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const {execFile}=require('node:child_process');
const execFileAsync=require('node:util').promisify(execFile);
const {chromium}=require('../browser-ci/node_modules/playwright-core');
const root=process.argv[2],python=process.argv[3],repo=path.resolve(__dirname,'../..');
const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8')),base=`http://127.0.0.1:${info.port}`;
const executable=process.argv[4] || (process.platform==='win32' ? path.join(process.env['ProgramFiles(x86)'],'Microsoft/Edge/Application/msedge.exe'):'/usr/bin/chromium');
const result={kind:'Installed native protected browser / synthetic agent UI',platform:process.platform,executable,modelRequests:0,checks:[],screenshots:[],unexpectedPageErrors:[]};let browser,page;
const removedSecurityDefaults=['--enable-unsafe-swiftshader','--unsafely-disable-devtools-self-xss-warnings','--disable-ipc-flooding-protection','--disable-client-side-phishing-detection','--password-store=basic','--use-mock-keychain','--disable-features='+['AvoidUnnecessaryBeforeUnloadCheckSync','DestroyProfileOnBrowserClose','DialMediaRouteProvider','GlobalMediaControls','HttpsUpgrades','LensOverlay','MediaRouter','PaintHolding','ThirdPartyStoragePartitioning','BlockOriginHeaderModificationOnRedirect','Translate','AutoDeElevate','OptimizationHints','msForceBrowserSignIn','msEdgeUpdateLaunchServicesPreferredVersion'].join(',')];
function check(name,value){assert.ok(value,name);result.checks.push({name,status:'PASS'});}
async function action(name){return (await execFileAsync(python,['scripts/agent-ui/fixture.py','--root',root,'--action',name],{cwd:repo,env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'})).stdout.trim();}
async function latch(get){const until=Date.now()+12000;while(!get()){assert.ok(Date.now()<until,"delayed response hook timed out");await page.waitForTimeout(20);}}
async function idle(){await page.waitForFunction(()=>engineering && !engineering.busy);}
async function open(id){await page.locator('#app-list .row').filter({hasText:id===info.derived_app?'已完成任务的 agent 候选':id===info.initial_app?'evidence app':'existing R0 app domain'}).getByRole('button').click();await page.waitForFunction(id=>activeApp===id && engineering && !engineering.busy,id);}
async function inputs(file,term){await page.locator('#app-agent-term').fill(term);await page.locator('#internal-term').fill(term);await page.locator('#internal-replay-file').setInputFiles(path.join(root,file));await page.waitForFunction(()=>engineering.offlineReplay!==null);}
async function layout(label){const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('#internal-panel button,#internal-panel input,#internal-panel blockquote')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));check(`${label}: no document/control/quote horizontal overflow`,bounds.scroll<=bounds.width+1&&bounds.overflow===0);const file=label+'.png';await page.screenshot({path:path.join(root,file),fullPage:true});result.screenshots.push(file);}
(async()=>{
 try{
  browser=await chromium.launch({executablePath:executable,chromiumSandbox:true,ignoreDefaultArgs:removedSecurityDefaults,headless:true,timeout:20000});
  const cdp=await browser.newBrowserCDPSession();const argv=(await cdp.send('Browser.getBrowserCommandLine')).arguments;
  check('actual browser command line preserves sandbox/security',!argv.some(a=>['--no-sandbox','--disable-setuid-sandbox','--disable-web-security','--ignore-certificate-errors','--single-process'].includes(a)));
  result.browserVersion=browser.version();
  const context=await browser.newContext({viewport:{width:1280,height:900},bypassCSP:false,acceptDownloads:false});
  await context.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
  page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',e=>result.unexpectedPageErrors.push(e.message));
  await page.goto(base,{waitUntil:'networkidle'});await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});
  await page.locator('#project-select').selectOption(info.project);await page.locator('[data-tab="apps"]').click();await open(info.derived_app);
  check('existing authenticated app path opens agent',await page.locator('#internal-agent').isVisible());
  check('offline supplied candidate and semantic UNKNOWN are clear',(await page.locator('#internal-agent').innerText()).includes('尚无真实模型自主生成')&&(await page.locator('#app-origin').innerText()).includes('UNKNOWN'));
  check('missing Replay blocks approval',await page.locator('#internal-prepare').isDisabled());
  await inputs('derived-replay.json',info.term_b);await page.locator('#internal-prepare').click();await idle();
  check('approval binds explicit responses',(await page.locator('#internal-approval-detail').innerText()).includes('offline_replay_fingerprint'));
  check('no default acknowledgement',await page.locator('#internal-commit').isDisabled());
  await page.locator('#internal-approval-ack').check();await page.locator('#internal-commit').click();await idle();
  await page.locator('#internal-releases button').last().click();await page.waitForFunction(()=>engineering.instance && !engineering.busy);
  const iid=await page.evaluate(()=>engineering.instance.id);
  await page.locator('#internal-run-submit').click();await idle();await action('worker');await page.locator('#internal-refresh').click();await idle();
  check('cold default worker persisted independent result v1',(await page.locator('#internal-data').innerText()).includes('历史结果 v1'));
  check('literal citations and UNKNOWN shown',(await page.locator('#internal-data blockquote').count())>0&&(await page.locator('#internal-data').innerText()).includes('语义 UNKNOWN'));
  await layout('agent-desktop');await page.setViewportSize({width:390,height:844});await layout('agent-narrow');
  await page.reload({waitUntil:'networkidle'});await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await page.locator('#project-select').selectOption(info.project);await page.locator('[data-tab="apps"]').click();await open(info.derived_app);
  await page.locator('#internal-instances .row').filter({hasText:iid}).getByRole('button').click();await page.waitForFunction(()=>engineering.instance && !engineering.busy);
  check('fresh page reopens stored history without execution',(await page.locator('#internal-data').innerText()).includes('历史结果 v1'));
  await inputs('derived-replay.json',info.term_b);await page.locator('#internal-prepare').click();await idle();
  await page.evaluate(()=>{engineering.approval.expires_at=Date.now()/1000-1;engineeringButtons(engineering);});await page.locator('#internal-approval-ack').check();check('expired approval disabled',await page.locator('#internal-commit').isDisabled());
  let release;await page.route('**/release-approvals',async route=>{const response=await route.fetch();await new Promise(r=>{release=r;});await route.fulfill({response});});
  await page.locator('#internal-prepare').click();await page.waitForTimeout(100);await latch(()=>release);await page.locator('#app-agent-term').fill('changed-input');release();await idle();await page.unroute('**/release-approvals');
  check('late approval cannot restore changed-input confirmation',await page.locator('#internal-approval').isHidden());
  await page.evaluate(()=>{window._agentOriginalFileText=File.prototype.text;File.prototype.text=function(){const file=this;return new Promise(resolve=>{window._agentFinishFile=async()=>resolve(await window._agentOriginalFileText.call(file));});};});
  await page.locator('#internal-replay-file').setInputFiles(path.join(root,'derived-replay.json'));await open(info.csv_app);await page.evaluate(async()=>{await window._agentFinishFile();File.prototype.text=window._agentOriginalFileText;});
  check('late actual File read cannot attach Replay to CSV',await page.evaluate(()=>engineering.offlineReplay===null));
  let releaseApp;await page.route(`**/api/apps/${info.initial_app}`,async route=>{const response=await route.fetch();await new Promise(r=>{releaseApp=r;});await route.fulfill({response});});
  await page.locator('#app-list .row').filter({hasText:'evidence app'}).getByRole('button').click();await latch(()=>releaseApp);await open(info.derived_app);releaseApp();await page.unroute(`**/api/apps/${info.initial_app}`);await page.waitForTimeout(100);
  check('late source app response cannot replace selection',await page.evaluate(id=>activeApp===id,info.derived_app));
  await action('corrupt');await page.locator('#internal-refresh').click();await idle();check('provenance tamper clears protected snapshots',await page.locator('#internal-data').innerText()===''&&await page.locator('#app-manifest').innerText()==='');
  await open(info.initial_app);await action('revoke');await page.locator('#internal-refresh').click();await idle();check('current revocation clears protected results',await page.locator('#internal-data').innerText()===''&&await page.locator('#internal-run-form').isHidden());
  check('UI actions grant nothing',JSON.parse(await action('counts')).grants===info.grant_count);
  check('no unexpected page errors',result.unexpectedPageErrors.length===0);result.status='PASS';
 }catch(error){result.status=browser?'FAIL':'BLOCKED';result.error=error.message;process.exitCode=1;}
 finally{await browser?.close();fs.writeFileSync(path.join(root,'protected-browser-results.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result,null,2));}
})();
