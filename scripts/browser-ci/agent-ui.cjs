'use strict';
// Called only by the existing protected Windows Edge path; never launches a browser.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const {execFile}=require('node:child_process');
const execFileAsync=require('node:util').promisify(execFile);
module.exports=async function runAgentChecks({browser,root,outputRoot,python,audit}){
 const repo=path.resolve(__dirname,'../..');
 const info=JSON.parse(fs.readFileSync(path.join(root,'info.json'),'utf8')),base=`http://127.0.0.1:${info.port}`;
 const result={kind:'Additional agent checks / same actual protected Windows Edge / synthetic HTTP',platform:process.platform,modelRequests:0,legacyChecksCounted:0,checks:[],screenshots:[],unexpectedPageErrors:[],sandbox:[],visualReview:'NOT_REVIEWED',win11:'NOT_RUN'};
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
async function action(name){return (await execFileAsync(python,['scripts/agent-ui/fixture.py','--root',root,'--action',name],{cwd:repo,env:{...process.env,PYTHONPATH:'src'},encoding:'utf8'})).stdout.trim();}
async function idle(){await page.waitForFunction(()=>engineering && !engineering.busy);}
async function open(id){await page.locator('#app-list .row').filter({hasText:id===info.derived_app?'已完成任务的 agent 候选':id===info.initial_app?'evidence app':'existing R0 app domain'}).getByRole('button').click();await page.waitForFunction(id=>activeApp===id && engineering && !engineering.busy,id);}
async function inputs(file,term){await page.locator('#app-agent-term').fill(term);if(await page.locator('#internal-term').isVisible())await page.locator('#internal-term').fill(term);await page.locator('#internal-replay-file').setInputFiles(path.join(root,file));await page.waitForFunction(()=>engineering.offlineReplay!==null);}
async function layout(label){const bounds=await page.evaluate(()=>({width:innerWidth,scroll:document.documentElement.scrollWidth,overflow:[...document.querySelectorAll('#internal-panel button,#internal-panel input,#internal-panel blockquote')].filter(e=>e.getClientRects().length).filter(e=>{const r=e.getBoundingClientRect();return r.left<0||r.right>innerWidth+1;}).length}));check(`${label}: no document/control/quote horizontal overflow`,bounds.scroll<=bounds.width+1&&bounds.overflow===0);const diagnostic=await page.evaluate(()=>({scrollY,fonts:document.fonts.status,nodes:['app-title','app-origin','app-frozen-goal-text','app-agent-term','internal-status','internal-data'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect(),style=getComputedStyle(e);return{id,characters:(e.value??e.textContent).trim().length,display:style.display,visibility:style.visibility,color:style.color,opacity:style.opacity,width:r.width,height:r.height,inViewport:r.bottom>0&&r.top<innerHeight};})}));result.captureDiagnostics??={};result.captureDiagnostics[label]={bounds,...diagnostic};const file=label+'.png';await page.screenshot({path:path.join(outputRoot,file),fullPage:true});const bytes=fs.readFileSync(path.join(outputRoot,file));result.screenshots.push({name:file,sha256:crypto.createHash('sha256').update(bytes).digest('hex'),width:bytes.readUInt32BE(16),height:bytes.readUInt32BE(20),visualReview:'NOT_REVIEWED'});}
 try{
  const baseline=await audit();baselineRendererPids=new Set(baseline.filter(p=>p.type==='renderer').map(p=>p.pid));
  result.legacyRendererBaseline=[...baselineRendererPids];
  context=await browser.newContext({viewport:{width:1280,height:900},bypassCSP:false,acceptDownloads:false});
  await context.route('**/*',r=>r.request().url().startsWith(base+'/')?r.continue():r.abort());
  page=await context.newPage();page.setDefaultTimeout(12000);page.on('pageerror',e=>result.unexpectedPageErrors.push(e.message));
  await page.goto(base,{waitUntil:'networkidle'});await verifySandbox();await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});
  await page.locator('#project-select').selectOption(info.project);await page.locator('[data-tab="apps"]').click();await open(info.derived_app);
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
  await page.locator('#internal-run-submit').click();await idle();await action('worker');await page.locator('#internal-refresh').click();await idle();
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
  await action('worker');await page.locator('#internal-refresh').click();await idle();
  check('cold retry produces independent result v2 and retains v1',(await page.locator('#internal-data').innerText()).includes('历史结果 v2')&&await page.locator('#internal-data .agent-result').count()===2);
  await layout('agent-desktop');await page.setViewportSize({width:390,height:844});await layout('agent-narrow');await verifySandbox();
  await page.reload({waitUntil:'networkidle'});await verifySandbox();await page.locator('#token').fill('synthetic-agent-ui-A');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await page.locator('#project-select').selectOption(info.project);await page.locator('[data-tab="apps"]').click();await open(info.derived_app);
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
  await page.locator('[data-tab="projects"]').click();await page.locator('#project-select').waitFor({state:'visible'});
  await page.locator('#project-select').selectOption(info.other_project);await projectHold.deliver();await page.locator('[data-tab="apps"]').click();
  check('late previous-project response cannot reveal source or internal panel',await page.locator('#internal-panel').isHidden()&&await page.locator('#app-manifest').innerText()==='');
  await page.locator('[data-tab="projects"]').click();await page.locator('#project-select').waitFor({state:'visible'});
  await page.locator('#project-select').selectOption(info.project);await page.locator('[data-tab="apps"]').click();await open(info.derived_app);
  await action('corrupt');await page.locator('#internal-refresh').click();await idle();check('provenance tamper clears protected snapshots',await page.locator('#internal-data').innerText()===''&&await page.locator('#app-manifest').innerText()==='');
  await open(info.initial_app);await action('revoke');await page.locator('#internal-refresh').click();await idle();check('current revocation clears protected results',await page.locator('#internal-data').innerText()===''&&await page.locator('#internal-run-form').isHidden());
  check('UI actions grant nothing',JSON.parse(await action('counts')).grants===info.grant_count);
  check('no unexpected page errors',result.unexpectedPageErrors.length===0);result.status='PASS';
 }catch(error){result.status='FAIL';result.error={name:error.name,message:error.message};if(page&&!page.isClosed()){try{await page.screenshot({path:path.join(outputRoot,'agent-failure.png'),fullPage:true});}catch{}}}
 finally{
  held.forEach(release=>release());
  try{await context?.close();}catch(error){result.status='FAIL';result.cleanupError=error.name;}
  finally{fs.writeFileSync(path.join(outputRoot,'agent-results.json'),JSON.stringify(result,null,2)+'\n');}
 }
 console.log(`Additional agent ${result.status}: ${result.checks.length} passed checks; screenshots ${result.screenshots.length}; visual NOT_REVIEWED; model requests 0.`);
 if(result.status!=='PASS')throw Error('Additional agent native checks failed; see named agent-results.json');
 return result;
};
