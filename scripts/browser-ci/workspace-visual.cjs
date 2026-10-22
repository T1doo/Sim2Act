'use strict';
// One explicitly selected visual window. Actual production scripts + sealed API;
// old HTML/CSS bytes are served only for the two labelled before frames.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const repo=path.resolve(__dirname,'../..'),before=path.join(repo,'docs/evidence/workspace-refinement-native-20261022/before');
function baselineAsset(url){
 const name=url==='/'?'index.html':url==='/app.css'?'app.css':null;
 if(!name)return null;
 const body=fs.readFileSync(path.join(before,name)),expected={'index.html':'e47994e83f35e17779a1bc37292e7273688fc86f54758e3d875b67234c151b22','app.css':'4a39c8afbf8911a0e97094fcee09d6114ddd85ed65e0c9a63b2a65ddccecf329'};
 assert.equal(crypto.createHash('sha256').update(body).digest('hex'),expected[name],'Exact old source bytes required');
 return {status:200,contentType:name.endsWith('.html')?'text/html; charset=utf-8':'text/css; charset=utf-8',body};
}
async function runWorkspaceVisual({page,info,result,check,shot,until,choose,audit,setBaseline,setFailLocator}){
 result.visual={before_source:'51bcbcde3d9188420081802aa9aa35aebe5d009a',candidate_source:'b538ce79b80db7bca4016fcf5b825d39adfc4be1',layouts:[],focus:[],baseline_assets:Object.fromEntries(['index.html','app.css'].map(name=>[name,crypto.createHash('sha256').update(fs.readFileSync(path.join(before,name))).digest('hex')]))};
 const view=async(width,height=900)=>page.setViewportSize({width,height});
 const top=async()=>{await page.locator('#projects > h1, #projects .workspace-heading').first().scrollIntoViewIfNeeded();await page.evaluate(()=>scrollTo(0,0));};
 await view(1366);await top();await shot('before-projects-wide.png');
 await view(390,844);await top();await shot('before-projects-narrow.png');
 setBaseline(false);
 await view(1366);await page.goto(info.base,{waitUntil:'domcontentloaded'});
 await page.locator('#token').fill('secret test token');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await audit();
 check('candidate full page is current production template',await page.locator('#projects-title').count()===1&&await page.locator('#project-tools').count()===1);
 // Seed focus, then use genuine keyboard activation/navigation, not a controller replacement.
 await page.locator('.skip-link').focus();await page.keyboard.press('Enter');
 check('keyboard skip link reaches actual main landmark',await page.evaluate(()=>document.activeElement.id==='main-content'));
 const summary=page.locator('#project-tools > summary');await summary.focus();
 const ring=await summary.evaluate(e=>({outline:getComputedStyle(e).outlineStyle,width:getComputedStyle(e).outlineWidth,focused:e.matches(':focus-visible')}));result.visual.focus.push({element:'maintenance summary',...ring});
 check('keyboard focus is visibly outlined',ring.focused&&ring.outline!=='none'&&parseFloat(ring.width)>=2);
 await page.keyboard.press('Enter');check('real keyboard opens maintenance with all four original tools',await page.locator('#project-tools').getAttribute('open')!==null&&await page.locator('#pn-read').isVisible()&&await page.locator('#text-logic-history').isVisible()&&await page.locator('#text-continuation-list').isVisible()&&await page.locator('#csv-logic-history').isVisible());
 await page.keyboard.press('Space');check('real keyboard collapses tools without changing original hidden gates',await page.locator('#project-tools').getAttribute('open')===null&&!await page.locator('#pn-read').isVisible());
 await page.keyboard.press('Tab');check('Tab passes closed tool controls to actual task form',await page.evaluate(()=>document.activeElement.id==='goal'));
 async function layout(workspace,width){
  await view(width,width<500?844:900);
  const measure=await page.evaluate(id=>{
   const root=document.getElementById(id),visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden';
   const nodes=[...root.querySelectorAll('button,input,select,textarea,summary,pre')].filter(visible);
   return {workspace:id,width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:nodes.filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+1;}).map(e=>e.id||e.tagName),smallButtons:nodes.filter(e=>e.tagName==='BUTTON'&&e.getBoundingClientRect().height<43.5).map(e=>e.id),hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(visible).map(e=>e.id)};
  },workspace);result.visual.layouts.push(measure);
  check(`${workspace} at ${width}px has no horizontal/control overflow or hidden gate leak`,measure.documentWidth<=width+1&&measure.overflow.length===0&&measure.hiddenLeaks.length===0&&measure.smallButtons.length===0);
 }
 for(const workspace of ['projects','apps','resources']){
  if(workspace!=='projects')await page.locator(`[data-tab="${workspace}"]`).click();
  for(const width of [1366,768,390,320])await layout(workspace,width);
  for(const [label,width] of [['wide',1366],['narrow',390]]){
   await view(width,width<500?844:900);await page.evaluate(()=>scrollTo(0,0));await shot(`after-${workspace}-${label}.png`);
  }
 }
 await page.locator('[data-tab="projects"]').click();await view(1366);await choose(info.run);
 const item=info.cases[0];assert.equal(item.current.phase,'source');
 async function locate(){
  await page.locator('#protocol-completion-locate').click();
  await until(id=>!protocolContext.busy&&protocolCompletionReadbacks.get(protocolCompletionKey(protocolContext,id))?.state==='accepted',item.current.run_id);
  assert.deepEqual(JSON.parse(await page.locator('#protocol-completion-locate-receipt').textContent()),{request:item.locator.request,receipt:item.locator.receipt});
  assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),item.current.result);
 }
 await locate();
 const receipt=page.locator('#protocol-completion-locate-receipt');await receipt.focus();
 const scrollBefore=await receipt.evaluate(e=>e.scrollTop);await page.keyboard.press('PageDown');
 await page.waitForFunction(previous=>document.getElementById('protocol-completion-locate-receipt').scrollTop>previous,scrollBefore,{timeout:2000});
 const scroll=await receipt.evaluate(e=>({active:document.activeElement===e,height:e.clientHeight,fullHeight:e.scrollHeight,scrollTop:e.scrollTop,outline:getComputedStyle(e).outlineStyle,focusVisible:e.matches(':focus-visible')}));result.visual.focus.push({element:'full original completion receipt',...scroll});
 check('original full receipt is keyboard scrollable with visible focus',scroll.active&&scroll.height<=240&&scroll.fullHeight>scroll.height&&scroll.scrollTop>0&&scroll.focusVisible&&scroll.outline!=='none');
 await layout('projects',390);await layout('projects',1366);
 await page.locator('#protocol-state').scrollIntoViewIfNeeded();await shot('after-source-receipt-wide.png');
 setFailLocator(item.current.run_id);await page.locator('#protocol-completion-locate').click();
 await until(()=>!protocolContext.busy&&document.getElementById('protocol-state').textContent.includes('不可确认'));
 check('read error clears current output without changing actual Run or enabling actions',await page.evaluate(()=>protocolContext.run.status==='WAITING_APPROVAL'&&document.getElementById('protocol-result').textContent===''&&document.getElementById('protocol-extract').hidden&&document.getElementById('protocol-cold-form').hidden));
 await view(390,844);await page.locator('#protocol-state').scrollIntoViewIfNeeded();await shot('after-source-error-narrow.png');
 await locate();
 check('new fresh GET restores the exact original receipt and original key',await page.locator('#protocol-completion-locate-receipt').textContent().then(s=>s.includes(item.locator.request.request_key)));
 check('visual work used only bounded GET with no new command or page errors',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0&&await page.evaluate(()=>protocolCompletionIntents.size===0&&protocolReviewIntents.size===0));
 result.receipts=result.located.map(x=>x.receipt);result.visual.original_key=item.locator.request.request_key;result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
