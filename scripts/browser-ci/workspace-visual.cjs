'use strict';
// Exactly one final-state window. Original sealed stores and command gates remain.
const assert=require('node:assert/strict');
function baselineAsset(){throw Error('No runtime asset substitution');}
async function runWorkspaceVisual({page,info,result,check,shot,until,choose,audit,wait,holdNextContentRead,setFailContent}){
 const sourceCase=info.cases[0],content=info.content;assert.equal(sourceCase.current.phase,'source');
 const source=info.visual_source;assert.match(source.commit,/^[a-f0-9]{40}$/);
 assert.deepEqual(Object.keys(source.asset_lf_sha256).sort(),['app.css','app.js','csv-goal-revision.js','csv-owner.js','index.html','protocol.js','use.js'].map(n=>'src/sim2act/web/'+n).sort());
 for(const hash of Object.values(source.asset_lf_sha256))assert.match(hash,/^[a-f0-9]{64}$/);
 result.visual={capture_revision:'final-state-reading-v1',product_source:source.commit,product_asset_lf_sha256:{...source.asset_lf_sha256},prior_native_execution:'944545ac9e26b3e11a1e5c383e5cb318430fa301',prior_followup_product:'5fec2a068d80bbbec3f30eb78b5024b528a7aeb2',layouts:[],states:[],motion:[]};
 const view=width=>page.setViewportSize({width,height:width<500?844:900});
 async function stable(){
  await until(()=>document.getElementById('health').textContent.startsWith('健康检查：')&&!backgroundRefreshInFlight&&!protocolContext?.busy&&!applicationUse?.busy);
  await page.mouse.move(1,1);await page.waitForTimeout(200);await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 }
 async function frame(name,width,target){await view(width);if(target)await page.locator(target).scrollIntoViewIfNeeded();else await page.evaluate(()=>scrollTo(0,0));await stable();await shot(name);}
 async function geometry(workspace,width){
  await view(width);await stable();
  const value=await page.evaluate(id=>{const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden',nodes=[...document.getElementById(id).querySelectorAll('button,input,select,textarea,summary,pre')].filter(visible);return {workspace:id,width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:nodes.filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+1;}).map(e=>e.id||e.tagName),hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(visible).map(e=>e.id)};},workspace);
  result.visual.layouts.push(value);check(`${workspace} ${width}px no overflow or hidden leak`,value.documentWidth<=width+1&&!value.overflow.length&&!value.hiddenLeaks.length);
 }
 await page.emulateMedia({reducedMotion:'no-preference'});await choose(info.run);await until(()=>!document.getElementById('protocol-reading-view').hidden);
 assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),sourceCase.current.result);
 check('source summary retains exact output, UNKNOWN, PENDING and full identifiers',await page.locator('#protocol-state-view').textContent().then(t=>t.includes('UNKNOWN')&&t.includes('PENDING')&&t.includes(sourceCase.current.run_id)));
 await page.locator('.section-links a[href="#protocol-panel"]').click();await until(()=>document.querySelector('.section-links a[aria-current="location"]')?.hash==='#protocol-panel');
 await page.locator('.section-links a[href="#task-workbench"]').click();await until(()=>document.querySelector('.section-links a[aria-current="location"]')?.hash==='#task-workbench');
 check('real same-page navigation has one current location for keyboard/clicked section',await page.locator('.section-links [aria-current="location"]').count()===1);
 for(const width of [1366,390])await geometry('projects',width);
 await frame('after-projects-wide.png',1366);await frame('after-projects-narrow.png',390);
 const first=await page.locator('.reading-next-step').boundingBox();result.visual.states.push({name:'source narrow first viewport',box:first,viewport:{width:390,height:844},scrollY:await page.evaluate(()=>scrollY)});
 check('390px source next step is readable in actual first viewport without scrolling',await page.evaluate(()=>scrollY===0)&&first.y>=0&&first.y+first.height<=844);
 check('source uncertainty stays visible before readable next step',await page.locator('.state-facts').boundingBox().then(r=>r.y+r.height<first.y));
 await page.locator('[data-tab="resources"]').click();for(const width of [1366,390])await geometry('resources',width);
 await frame('after-resources-wide.png',1366);await frame('after-resources-narrow.png',390);
 const rows=await page.locator('#materials .resource-row').evaluateAll(nodes=>nodes.map(e=>({height:e.getBoundingClientRect().height,name:e.querySelector('.resource-name').textContent,metadata:e.querySelector('.resource-metadata').textContent,actions:[...e.querySelectorAll('button')].map(b=>b.textContent)})));result.visual.states.push({name:'material row hierarchy',rows});check('two original resource rows remain compact with name metadata and original actions',rows.length===2&&rows.every(r=>r.height<=85&&r.name&&r.metadata&&r.actions.join('|')==='查看|下载文件'));
 await page.goto(content.base,{waitUntil:'domcontentloaded'});await page.locator('#token').fill(content.token);await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await audit();
 assert.equal(await page.locator('#project-select').inputValue(),content.project_id);await page.locator('[data-tab="apps"]').click();
 const instance=page.locator(`#use-list [data-use-family="CSV"][data-instance-id="${content.instance_id}"]`);await instance.waitFor();
 const held=holdNextContentRead();await instance.getByRole('button',{name:'使用此本地实例',exact:true}).click();await wait(held.arrived);
 try{
  await until(()=>document.getElementById('use-info').dataset.readState==='loading');
  check('opening has immediate real read feedback and no run control before completion',await page.locator('#use-form').isHidden()&&await page.locator('#use-info').textContent().then(t=>t.includes('正在')));
  await frame('app-loading-wide.png',1366,'#use-info');
  result.visual.motion.push(await page.locator('#use-info').evaluate(e=>({stage:'normal loading',reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,animation:getComputedStyle(e,'::before').animationName,duration:getComputedStyle(e,'::before').animationDuration})));
 }finally{held.release();}
 await until(id=>applicationUse?.id===id&&!document.getElementById('use-form').hidden&&document.getElementById('use-info').dataset.readState!=='loading',content.instance_id);
 check('empty selection is explicit and does not pass off history as a new result',await page.locator('#use-output').textContent().then(t=>t.includes('本页尚未选择')&&t.includes('不是本次新结果')));
 await frame('app-empty-narrow.png',390,'#use-output');result.visual.states.push({name:'no Run selected',kind:'real empty selection with sealed history; not empty account'});
 const scope=page.locator('#use-csv-review-scope'),disclosure=scope.locator('..'),scopeValue=JSON.parse(await scope.textContent());
 const expected=await page.evaluate(()=>({scope:'SUM_ONLY_WITHOUT_MD',release_id:applicationUse.instance.release_id,release_fingerprint:applicationUse.instance.release_fingerprint,instance_id:applicationUse.id,revision:applicationUse.instance.revision,resource_id:applicationUse.app.candidate.manifest.data_bindings[0].resource_ref,source_hash:applicationUse.app.candidate.source_hash,column:document.getElementById('use-column').value}));assert.deepEqual(scopeValue,expected);
 check('scope JSON alone is collapsed with visible original unchecked opt-in',await disclosure.getAttribute('open')===null&&await page.locator('#use-csv-review-optin').isVisible()&&!await page.locator('#use-csv-review-optin').isChecked());
 await disclosure.locator('summary').focus();await page.keyboard.press('Enter');check('native keyboard opens exact complete scope JSON without checking opt-in',await scope.isVisible()&&!await page.locator('#use-csv-review-optin').isChecked());await page.keyboard.press('Enter');
 const history=page.locator('#use-history').getByRole('button',{name:'查看这次运行',exact:true});assert.equal(await history.count(),1);await history.click();await until(id=>applicationUse?.selected===id&&document.getElementById('use-output').textContent.includes('合计 30'),content.run_id);
 const saved=await page.evaluate(c=>{const run=applicationUse.instance.runs.find(r=>r.id===c.run_id);return {historical:applicationUse.historical,status:run.status,result:run.result};},content);assert.deepEqual(saved,{historical:true,status:'SUCCEEDED',result:content.result.result});
 check('completed historical result and all scope limits stay exact',await page.locator('.csv-result-total strong').textContent()==='30'&&await page.locator('#use-output').textContent().then(t=>t.includes('目标语义验收未执行')));
 for(const width of [1366,390])await geometry('apps',width);
 await frame('app-result-wide.png',1366,'#use-output');await frame('app-result-narrow.png',390,'#use-output');
 check('optional permission editing follows result history rather than preceding recovery',await page.evaluate(()=>!!(document.getElementById('use-history').compareDocumentPosition(document.getElementById('csv-material-access'))&Node.DOCUMENT_POSITION_FOLLOWING)));
 setFailContent();await page.locator('#use-refresh').click();await until(()=>document.getElementById('use-info').dataset.readState==='error');
 check('read failure removes old result and new-run form without altering persisted Run',await page.locator('#use-output').textContent()===''&&await page.locator('#use-form').isHidden());
 for(const width of [1366,390]){
  await geometry('apps',width);await frame(`app-read-error-${width===1366?'wide':'narrow'}.png`,width,'#use-info');
  const position=await page.evaluate(()=>{const a=document.getElementById('use-info').getBoundingClientRect(),b=document.getElementById('use-refresh').getBoundingClientRect();return {width:innerWidth,infoBottom:a.bottom,buttonTop:b.top,buttonBottom:b.bottom,height:innerHeight,enabled:!document.getElementById('use-refresh').disabled};});result.visual.states.push({name:'error recovery position',...position});check(`${width}px original read-only recovery is enabled next to error within viewport`,position.enabled&&position.buttonTop>=position.infoBottom&&position.buttonTop-position.infoBottom<50&&position.buttonBottom<=position.height);
 }
 await page.emulateMedia({reducedMotion:'reduce'});const reduced=holdNextContentRead();await page.locator('#use-refresh').click();await wait(reduced.arrived);
 try{
  const motion=await page.evaluate(()=>{const node=document.getElementById('use-info');return {stage:'reduced-motion retry',reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,state:node.dataset.readState,animation:getComputedStyle(node,'::before').animationName,duration:getComputedStyle(node,'::before').animationDuration,transition:getComputedStyle(document.getElementById('use-refresh')).transitionDuration,readDisabled:document.getElementById('use-refresh').disabled,runDisabled:document.getElementById('use-submit').disabled};});result.visual.motion.push(motion);
  check('real reduced-motion media disables loading animation and transitions while preserving immediate read feedback',motion.reduce&&motion.state==='loading'&&motion.animation==='none'&&motion.duration==='0s'&&motion.transition==='0s'&&motion.readDisabled&&motion.runDisabled);
 }finally{reduced.release();}
 await until(()=>document.getElementById('use-output').textContent.includes('合计 30')&&document.getElementById('use-info').dataset.readState!=='loading');
 check('reduced-motion recovery finishes by fresh GET of the same instance/Run only',await page.evaluate(c=>applicationUse.selected===c.run_id&&applicationUse.id===c.instance_id&&!document.getElementById('use-refresh').disabled,content));
 const refresh=page.locator('#use-refresh');await refresh.focus();await page.keyboard.press('Tab');await page.keyboard.press('Shift+Tab');check('primary read action keeps keyboard visible focus',await refresh.evaluate(e=>document.activeElement===e&&e.matches(':focus-visible')&&getComputedStyle(e).outlineStyle!=='none'));
 result.visual.states.push({name:'complete',instance:content.instance_id,run:content.run_id,result_version:content.result.result_version,sum:content.result.result.sum,owner:'not signed by test',semantic:'not promoted',business_clock:content.business_at});
 check('one final-state window is GET-only with no page errors or overrun',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0&&result.requests.every(r=>r.method==='GET'));
 result.receipts=[];result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
