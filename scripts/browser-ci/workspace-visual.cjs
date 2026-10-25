'use strict';
// One protected native window, fixed historical assets and unchanged sealed data.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const base='ef678365900f079971928f1a4631da0e6256cd82',product='384e332cbdfaa12f0dc7b70c16f8db49710a67de';
const hashes={
 'index.html':'34843288a1aefa8939eb6dcf67ab67dbab26444c5f67f42166a772e017fe26b6',
 'app.js':'114849ec122f2cd68b5b0d4c4f4b2191b46f67bb34d48c8be0eae21b6cbea467',
 'protocol.js':'6a6b537347b57e377f1d95d4758f4fe7a026de1ddc8aa0ff7786e89d588e60fd',
 'app.css':'771e555f5eb6528488b6649bd157a584ed92c9628cc21e6433d8ba1a2d3c6661'
};
const baselineRoot=path.resolve(__dirname,'../../docs/evidence/workspace-task-hierarchy-20261025/before-assets');
const manifest=JSON.parse(fs.readFileSync(path.join(baselineRoot,'manifest.json'),'utf8'));
assert.equal(manifest.commit,base);assert.deepEqual(Object.keys(manifest.assets).sort(),Object.keys(hashes).sort());
const baseline=new Map();
for(const name of Object.keys(hashes)){
 const body=fs.readFileSync(path.join(baselineRoot,name),'utf8').replace(/\r\n/g,'\n'),sha256=crypto.createHash('sha256').update(body).digest('hex');
 assert.equal(sha256,manifest.assets[name].sha256);assert.equal(Buffer.byteLength(body),manifest.assets[name].bytes);
 baseline.set(name,{body,sha256,contentType:name.endsWith('.js')?'application/javascript':name.endsWith('.css')?'text/css':'text/html'});
}
// Exact allowlist, no path concatenation or alternate asset/network source.
function baselineAsset(url){return baseline.get({'/':'index.html','/index.html':'index.html','/app.css':'app.css','/app.js':'app.js','/protocol.js':'protocol.js'}[url]);}
async function runWorkspaceVisual({page,info,result,check,shot,until,choose,audit,setBeforeAssets}){
 const original=info.cases[0];assert.equal(original.current.phase,'source');
 for(const [name,hash] of Object.entries(hashes))assert.equal(info.visual_source.asset_lf_sha256['src/sim2act/web/'+name],hash);
 result.visual={capture_revision:'task-hierarchy-before-after-v1',before_product:base,after_product:product,execution_source:info.visual_source.commit,product_asset_lf_sha256:info.visual_source.asset_lf_sha256,baseline:manifest,layouts:[],states:[],motion:[]};
 async function stable(){
  await until(()=>document.getElementById('health').textContent.startsWith('健康检查：')&&!backgroundRefreshInFlight&&!protocolContext?.busy);
  await page.mouse.move(1,1);await page.waitForTimeout(220);await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 }
 async function frame(name,width,target){
  await page.setViewportSize({width,height:width<500?844:900});
  if(target)await page.locator(target).scrollIntoViewIfNeeded();else await page.evaluate(()=>scrollTo(0,0));
  await stable();await shot(name);
  const geometry=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,scrollY,hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden').map(e=>e.id)}));
  result.visual.layouts.push({name,...geometry});check(name+' no horizontal document overflow or hidden leak',geometry.documentWidth<=width+1&&!geometry.hiddenLeaks.length);
 }
 const states=[];
 for(const version of ['before','after']){
  if(version==='after'){
   setBeforeAssets(false);await page.goto(info.base,{waitUntil:'domcontentloaded'});await audit();
   await page.locator('#token').fill('secret test token');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});
  }
  await page.emulateMedia({reducedMotion:'no-preference'});await choose(info.run);await until(()=>!document.getElementById('protocol-reading-view').hidden);await stable();
  const observed=await page.evaluate(()=>({run:protocolContext.run,result:JSON.parse(document.getElementById('protocol-result').textContent),facts:[...document.querySelectorAll('.state-facts > div')].map(e=>({label:e.querySelector('dt').textContent,value:e.querySelector('dd').textContent})),reviewChecked:document.getElementById('protocol-review-confirm').checked,reviewDisabled:document.getElementById('protocol-review-submit').disabled,extractHidden:document.getElementById('protocol-extract').hidden,coldHidden:document.getElementById('protocol-cold-form').hidden}));
  assert.deepEqual(observed.result,original.current.result);check(version+' original UNKNOWN/PENDING remain unapproved with both downstream routes closed',observed.facts.some(p=>p.value==='UNKNOWN')&&observed.facts.some(p=>p.value==='PENDING')&&!observed.reviewChecked&&observed.reviewDisabled&&observed.extractHidden&&observed.coldHidden);
  states.push(observed);result.visual.states.push({version,...observed});
  await frame(version+'-projects-wide.png',1366);await frame(version+'-projects-narrow.png',390);
  await frame(version+'-tasks-wide.png',1366,'#task-list-panel');await frame(version+'-tasks-narrow.png',390,'#task-list-panel');
 }
 assert.deepEqual(states[0],states[1]);check('before and after use the exact same persisted Run, output and four independent states',true);
 check('after history retains original Run identifier and presents an independently labelled execution status',await page.locator('#runs .task-history-item').count()>0&&await page.locator('#runs .task-status').first().textContent().then(t=>t.startsWith('执行 · '))&&await page.locator('#runs').textContent().then(t=>t.includes(info.run.slice(0,16))));
 const summary=page.locator('#task-create > summary');await summary.focus();await page.keyboard.press('Enter');
 check('native Enter opens the original task form',await page.locator('#goal').isVisible());
 await page.keyboard.press('Tab');check('native Tab focuses goal with visible keyboard outline',await page.locator('#goal').evaluate(e=>document.activeElement===e&&e.matches(':focus-visible')&&getComputedStyle(e).outlineStyle!=='none'));
 await page.locator('#goal').fill('合成界面草稿：核对材料与来源（不提交）');
 check('empty CSV selection keeps the original disabled prepare gate',await page.locator('#csv-report-prepare').isDisabled());
 await frame('task-focus-wide.png',1366,'#goal');
 const normal=await summary.evaluate(e=>({reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,transition:getComputedStyle(e.querySelector('span')).transitionDuration,transform:getComputedStyle(e.querySelector('span')).transform}));
 await page.emulateMedia({reducedMotion:'reduce'});
 await summary.focus();await page.keyboard.press('Enter');await page.keyboard.press('Enter');
 const reduced=await summary.evaluate(e=>({reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,transition:getComputedStyle(e.querySelector('span')).transitionDuration,animation:getComputedStyle(e.querySelector('span')).animationName,goalVisible:!!document.getElementById('goal').getClientRects().length}));
 result.visual.motion.push({normal,reduced});check('real reduced-motion setting removes disclosure transition and retains native interaction',!normal.reduce&&normal.transition!=='0s'&&reduced.reduce&&reduced.transition==='0s'&&reduced.animation==='none'&&reduced.goalVisible);
 await page.locator('#goal').focus();await frame('task-reduced-narrow.png',390,'#goal');
 const substitutions=result.requests.filter(r=>r.baseline_asset).map(r=>new URL('http://fixture'+r.path).pathname).sort();
 assert.deepEqual(substitutions,['/','/app.css','/app.js','/protocol.js'].sort());
 check('only the four fixed historical assets were substituted, keeping original HTTP headers and data',true);
 check('one protected native window stays GET-only with no page errors or overrun',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0&&result.requests.every(r=>r.method==='GET'));
 result.receipts=[];result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
