'use strict';
// Preparation only: no launcher import, route registration, browser or sender.
const assert=require('node:assert/strict');
function responseFor(fixture,method,pathname){
 assert.equal(method,'GET','Synthetic presentation forbids writes');
 if(pathname===`/api/projects/${fixture.project}/goal-cards`)return {items:[{id:fixture.card.id,title:fixture.card.content.title,version:3}]};
 if(pathname===`/api/goal-cards/${fixture.card.id}`)return structuredClone(fixture.card);
 if(pathname===`/api/goal-cards/${fixture.card.id}/candidate-options`)return {options:[]};
 return undefined; // Original closed handler still governs every other request.
}
async function capture({page,fixture,shot,check,until,result}){
 // Caller must count/trace the three synthetic GETs in the existing bounded
 // handler AFTER original origin/method/budget gates. This helper sets no routes.
 await page.locator('.section-links a[href="#goal-cards-panel"]').click();
 await page.locator('#goal-card-list').getByRole('button',{name:'打开目标卡',exact:true}).click();
 await until(()=>activeGoalCard?.version===3&&!goalCardLoading);
 for(const [name,value] of Object.entries(fixture.unsaved))await page.locator('#goal-card-'+name).fill(value);
 const state=()=>page.evaluate(()=>({fields:Object.fromEntries(goalCardFields.map(k=>[k,document.getElementById('goal-card-'+k).value])),selected:activeGoalCard,key:goalRunKey(),label:document.getElementById('goal-card-run').textContent,disabled:document.getElementById('goal-card-run').disabled}));
 const current=await state();await page.locator('#goal-card-history').getByRole('button',{name:'回看版本',exact:true}).nth(0).click();assert.deepEqual(await state(),current);
 const labels={title:'名称',goal:'目标',known:'已知',assumptions:'假设',unresolved:'未决项',constraints:'硬条件',acceptance_checks:'验收检查'},v1=fixture.card.history[0].snapshot.content;
 const expected=Object.keys(labels).map(k=>`${labels[k]}：\n${Array.isArray(v1[k])?v1[k].join('\n'):v1[k]}`).join('\n\n')+'\n\n绑定材料 0 份 · 只读历史版本 v1';
 assert.equal(await page.locator('#goal-card-history-detail').textContent(),expected);
 result.goalHistory={classification:fixture.classification,current,selectedHistory:1,frames:[],colocation:[]};
 for(const width of [1366,390]){
  await page.setViewportSize({width,height:width===390?844:900});await page.locator('#goal-card-history').evaluate(e=>e.scrollIntoView({block:'start'}));await page.evaluate(()=>document.fonts.ready);await page.waitForTimeout(220);
  await shot(`goal-history-${width}.png`);result.goalHistory.frames.push({name:`goal-history-${width}.png`,width});
 }
 // Same explicit test-only memory state used by goal_card_hierarchy.cjs.
 // No fabricated server response, contract, acceptance or persisted journal.
 await page.evaluate(f=>{trialEntries.set(trialIndex(trialContext()),structuredClone(f.trial));document.getElementById('trial-original-key').value=f.trial.key;renderTrialConsent();},fixture);
 check('unknown original key, disabled consent and enabled recovery',await page.evaluate(key=>trialEntry().state==='unknown'&&trialEntry().key===key&&document.getElementById('trial-consent').disabled&&!document.getElementById('trial-recover').disabled,fixture.trial.key));
 for(const width of [1366,390]){
  await page.setViewportSize({width,height:width===390?844:900});await page.locator('#trial-recover').evaluate(e=>e.scrollIntoView({block:'start'}));await page.waitForTimeout(220);
  const positions=await page.evaluate(()=>{const box=id=>{const b=document.getElementById(id).getBoundingClientRect();const e=document.getElementById(id);return {top:b.top,bottom:b.bottom,left:b.left,right:b.right,width:b.width,height:b.height,visible:e.checkVisibility({opacityProperty:true,visibilityProperty:true})};};return {width:innerWidth,height:innerHeight,recovery:box('trial-recover'),status:box('trial-status'),documentWidth:document.documentElement.scrollWidth};});
  positions.sameViewport=[positions.recovery,positions.status].every(b=>b.visible&&b.width>0&&b.height>0&&b.top>=0&&b.bottom<=positions.height&&b.left>=0&&b.right<=positions.width);
  result.goalHistory.colocation.push(positions);await shot(`goal-unknown-${width}.png`);
  // Failure remains diagnostic; never move/clone controls or hide intervening
  // confirmations just to fit a screenshot. Caller reports NOT_PROVEN if false.
  // Collect both widths before the final assertion; geometry failure alone
  // cannot prevent the second diagnostic screenshot.

 }
 result.goalHistory.colocationStatus=result.goalHistory.colocation.every(p=>p.sameViewport&&p.documentWidth<=p.width+1)?'PROVED':'NOT_PROVEN';
 check('both UNKNOWN/recovery viewports geometrically proved after collecting both frames',result.goalHistory.colocationStatus==='PROVED');
}
module.exports={responseFor,capture};
