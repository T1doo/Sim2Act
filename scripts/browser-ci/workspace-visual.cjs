'use strict';
// Explicit after-only density window. Before frames are the prior sealed native originals.
const assert=require('node:assert/strict');
function baselineAsset(){throw Error('Density window never substitutes production assets');}
async function runWorkspaceVisual({page,info,result,check,shot,until,choose,audit,setFailLocator,setEmptyProjects}){
 const item=info.cases[0];assert.equal(item.current.phase,'source');
 const source=info.visual_source;assert.ok(source,'Actual checkout metadata is required');assert.match(source.commit,/^[a-f0-9]{40}$/);
 assert.deepEqual(Object.keys(source.asset_lf_sha256).sort(),['src/sim2act/web/app.css','src/sim2act/web/app.js','src/sim2act/web/index.html','src/sim2act/web/protocol.js']);
 for(const hash of Object.values(source.asset_lf_sha256))assert.match(hash,/^[a-f0-9]{64}$/);
 result.visual={capture_revision:'research-desk-v2',product_source:source.commit,product_asset_lf_sha256:{...source.asset_lf_sha256},before_native_execution:'0ac62f629fd0f82accdf3888149693d182310089',before_product:'7af1af2e7def68d44554bf1d37454fe4971bf478',before_source:'sealed workspace-density-native-20261023 originals; current baseline web bytes matched before edits',layouts:[],focus:[],density:[],content:[]};
 const view=async(width)=>page.setViewportSize({width,height:width<500?844:900});
 async function stable(){
  await until(()=>document.getElementById('health').textContent.startsWith('健康检查：')&&!backgroundRefreshInFlight&&!protocolContext?.busy);
  await page.mouse.move(1,1);await page.waitForTimeout(180);
  await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
  check('capture uses sampled health and idle background read, not initial loading text',!(await page.locator('#health').textContent()).includes('正在检查'));
 }
 async function frame(name){await stable();await shot(name);}
 async function geometry(workspace,width){
  await view(width);
  const m=await page.evaluate(id=>{
   const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
   const nodes=[...document.getElementById(id).querySelectorAll('button,input,select,textarea,summary,pre')].filter(visible);
   const head=[...document.querySelector('header').children].filter(visible).map(e=>({id:e.id||e.tagName,r:e.getBoundingClientRect().toJSON()}));
   const overlaps=[];for(let i=0;i<head.length;i++)for(let j=i+1;j<head.length;j++){const a=head[i],b=head[j];if(Math.min(a.r.right,b.r.right)-Math.max(a.r.left,b.r.left)>1&&Math.min(a.r.bottom,b.r.bottom)-Math.max(a.r.top,b.r.top)>1)overlaps.push([a.id,b.id]);}
   return {workspace:id,width:innerWidth,documentWidth:document.documentElement.scrollWidth,health:document.getElementById('health').textContent,header:head,overlaps,overflow:nodes.filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+1;}).map(e=>e.id||e.tagName),smallButtons:nodes.filter(e=>e.tagName==='BUTTON'&&e.getBoundingClientRect().height<43.5).map(e=>e.id),hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(visible).map(e=>e.id)};
  },workspace);result.visual.layouts.push(m);
  check(`${workspace} ${width}px stable health has no header overlap/overflow/hidden leak`,m.documentWidth<=width+1&&!m.overlaps.length&&!m.overflow.length&&!m.hiddenLeaks.length&&!m.smallButtons.length);
 }
 async function density(workspace,width){
  await view(width);await page.evaluate(()=>scrollTo(0,0));await stable();
  const metric=await page.evaluate(id=>{
   const primary=id==='projects'?'task-result-panel':id==='apps'?'application-use':'resource-materials';
   return {workspace:id,width:innerWidth,primary,top:document.getElementById(primary).getBoundingClientRect().top,scopeBottom:document.getElementById('project-context').getBoundingClientRect().bottom};
  },workspace);result.visual.density.push(metric);
  check(`${workspace} ${width}px primary card reaches first viewport`,metric.top<(width===390?(workspace==='projects'?500:450):400));
 }
 await stable();await choose(info.run);
 assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),item.current.result);
 await page.locator('#protocol-evidence > summary').click();
 const resultPre=page.locator('#protocol-result');await resultPre.focus();await page.keyboard.press('PageDown');await page.waitForFunction(()=>document.getElementById('protocol-result').scrollTop>0,null,{timeout:2000});check('full original result accepts keyboard scrolling',await resultPre.evaluate(e=>document.activeElement===e&&e.matches(':focus-visible')&&getComputedStyle(e).outlineStyle!=='none'));await resultPre.evaluate(e=>{e.scrollTop=0;});
 check('real selected Source evidence is in the primary result canvas',await page.locator('#task-result-panel #protocol-detail').isVisible()&&await page.locator('#protocol-evidence').getAttribute('open')!==null);
 result.visual.content.push({kind:'Source',run:item.current.run_id,exact_result:true,status:item.current.status,semantic:item.current.semantic_status,owner:item.current.owner_semantic_acceptance});
 for(const workspace of ['projects','apps','resources']){
  if(workspace!=='projects')await page.locator(`[data-tab="${workspace}"]`).click();
  if(workspace==='resources'){
   const proof=info.captured.result.evidence.tool_trace[0].data;
   await page.locator('#materials > .row').filter({hasText:proof.hash.slice(0,12)}).getByRole('button',{name:'查看',exact:true}).click();
   await page.locator('#resource-preview').waitFor({state:'visible'});assert.equal(await page.locator('#resource-preview').textContent(),proof.content);
   result.visual.content.push({kind:'saved material',exact_original_text:true,resource:proof.resource_id});
  }
  for(const width of [1366,768,390,320])await geometry(workspace,width);
  for(const [label,width] of [['wide',1366],['narrow',390]]){
   await density(workspace,width);await frame(`after-${workspace}-${label}.png`);
  }
  if(workspace==='apps'){
   const gap=await page.evaluate(()=>{const a=document.getElementById('natural-first-start').getBoundingClientRect(),b=document.getElementById('local-records-new').getBoundingClientRect();return {sameRow:Math.abs(a.top-b.top)<2,gap:b.left-a.right};});result.visual.app_actions=gap;check('narrow creation actions retain a visible gap when on one row',!gap.sameRow||gap.gap>=7.5);
  }
 }
 const materialForm=page.locator('#resource-create > summary');await materialForm.focus();await page.keyboard.press('Enter');await page.keyboard.press('Tab');check('material creation disclosure exposes original file control without selection or submit',await page.locator('#resource-form').isVisible()&&await page.evaluate(()=>document.activeElement.id==='resource-file'));await materialForm.click();
 await page.locator('[data-tab="projects"]').click();await view(1366);await choose(info.run);
 const taskForm=page.locator('#task-create > summary');await taskForm.focus();await page.keyboard.press('Enter');await page.keyboard.press('Tab');check('task creation disclosure exposes original goal field without submit',await page.locator('#run-form').isVisible()&&await page.evaluate(()=>document.activeElement.id==='goal'));await taskForm.click();
 await page.locator('.skip-link').focus();await page.keyboard.press('Enter');check('skip link focuses real main',await page.evaluate(()=>document.activeElement.id==='main-content'));
 const summary=page.locator('#project-tools > summary');await summary.focus();await page.keyboard.press('Enter');
 check('maintenance keyboard opening reveals all four unchanged tools',await page.locator('#pn-read').isVisible()&&await page.locator('#text-logic-history').isVisible()&&await page.locator('#text-continuation-list').isVisible()&&await page.locator('#csv-logic-history').isVisible());
 await summary.scrollIntoViewIfNeeded();await frame('maintenance-expanded-wide.png');await page.keyboard.press('Space');check('maintenance keyboard closes original tools',!await page.locator('#pn-read').isVisible());
 await view(390);await page.locator('#project-create > summary').focus();await page.keyboard.press('Enter');await page.keyboard.press('Tab');
 check('creation disclosure reveals original form and keyboard name focus',await page.locator('#project-form').isVisible()&&await page.evaluate(()=>document.activeElement.id==='project-name'));
 await page.evaluate(()=>scrollTo(0,0));await frame('project-create-narrow.png');await page.locator('#project-create > summary').click();
 async function locate(){await page.locator('#protocol-completion-locate').click();await until(id=>!protocolContext.busy&&protocolCompletionReadbacks.get(protocolCompletionKey(protocolContext,id))?.state==='accepted',item.current.run_id);assert.deepEqual(JSON.parse(await page.locator('#protocol-completion-locate-receipt').textContent()),{request:item.locator.request,receipt:item.locator.receipt});assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),item.current.result);}
 await locate();await view(1366);const receipt=page.locator('#protocol-completion-locate-receipt');await receipt.focus();const prior=await receipt.evaluate(e=>e.scrollTop);await page.keyboard.press('PageDown');await page.waitForFunction(p=>document.getElementById('protocol-completion-locate-receipt').scrollTop>p,prior,{timeout:2000});
 const focus=await receipt.evaluate(e=>({active:document.activeElement===e,visible:e.matches(':focus-visible'),outline:getComputedStyle(e).outlineStyle,top:e.scrollTop}));result.visual.focus.push(focus);check('real receipt retains keyboard scrolling/focus',focus.active&&focus.visible&&focus.outline!=='none'&&focus.top>prior);
 await receipt.scrollIntoViewIfNeeded();await frame('after-source-receipt-wide.png');
 setFailLocator(item.current.run_id);await page.locator('#protocol-completion-locate').click();await until(()=>!protocolContext.busy&&document.getElementById('protocol-state').textContent.includes('不可确认'));
 check('failed read clears primary result and closes routes without changing Run',await page.evaluate(()=>document.getElementById('protocol-result').textContent===''&&document.getElementById('protocol-extract').hidden&&document.getElementById('protocol-cold-form').hidden&&protocolContext.run.status==='WAITING_APPROVAL'));
 await view(390);await page.locator('#protocol-state').scrollIntoViewIfNeeded();await frame('after-source-error-narrow.png');check('stable error capture remains unconfirmed with no old result',await page.evaluate(()=>document.getElementById('protocol-state').textContent.includes('不可确认')&&document.getElementById('protocol-result').textContent===''));await locate();
 await geometry('projects',390);await geometry('projects',1366);
 // One extra genuine page load exercises the empty-project entry after a labelled
 // read-only response filter. It grants nothing and never submits creation.
 setEmptyProjects(true);
 await page.goto(info.base,{waitUntil:'domcontentloaded'});await page.locator('#token').fill('secret test token');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await page.locator('.scope-note > summary').click();await page.locator('#project-context-open').click();
 check('controlled empty project read opens original creation form before real focus, zero submit',await page.locator('#project-form').isVisible()&&await page.evaluate(()=>document.activeElement.id==='project-name'));result.visual.empty_project='controlled GET response [] after authenticated successful server read; not a new account or project';
 check('read-only visual work made no command or blocked overrun',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0);
 result.receipts=result.located.map(x=>x.receipt);result.visual.original_key=item.locator.request.request_key;result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
