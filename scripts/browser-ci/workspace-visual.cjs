'use strict';
// One protected native window, fixed historical assets and unchanged sealed data.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const base='e02d4a1b12463b02480b100cc42e422ecc9faf09',product='a7f20e14885cc3e20604d52507dd4ce43ced7d18';
const hashes={"index.html": "475393d089cd4de947b08f7c79bb2793efb1322e3dde2de9e6a49edefee8c2b3", "app.css": "2ee9b73ddfc5b9bede4bf09fc4c6643ef5c3316b4a7951ad04e1477fa1d3df09", "app.js": "114849ec122f2cd68b5b0d4c4f4b2191b46f67bb34d48c8be0eae21b6cbea467", "protocol.js": "6a6b537347b57e377f1d95d4758f4fe7a026de1ddc8aa0ff7786e89d588e60fd"};
const baselineRoot=path.resolve(__dirname,'../../docs/evidence/goal-card-native-20261025/before-assets');
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
async function runWorkspaceVisual({page,info,result,check,shot,until,audit,setBeforeAssets}){
 for(const [n,h] of Object.entries(hashes))assert.equal(info.visual_source.asset_lf_sha256['src/sim2act/web/'+n],h);
 result.visual={capture_revision:'goal-card-hierarchy-v1',before_product:base,after_product:product,execution_source:info.visual_source.commit,layouts:[],states:[],motion:[]};
 async function stable(){await until(()=>!backgroundRefreshInFlight);await page.mouse.move(1,1);await page.waitForTimeout(220);await page.evaluate(()=>document.fonts.ready);await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));}
 async function frame(name,width,target){await page.setViewportSize({width,height:width===390?844:900});await page.locator(target).evaluate(e=>e.scrollIntoView({block:'start'}));await stable();await shot(name);const g=await page.evaluate(()=>({width:innerWidth,documentWidth:document.documentElement.scrollWidth,scrollY,hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden').map(e=>e.id)}));result.visual.layouts.push({name,...g});check(name+' fits viewport without hidden leaks',g.documentWidth<=width+1&&!g.hiddenLeaks.length);}
 const draft={title:'合成草稿 · 整理资料中的提交条件',goal:'整理本次材料的提交条件，保留来源与尚待确认的问题。',known:'材料来自当前项目授权范围',assumptions:'提交方具备原材料访问权',unresolved:'实际适用性仍需人工确认',constraints:'不得虚构缺失日期或审批结果',acceptance_checks:'每项结论保留来源；未知明确标记'};
 const states=[];
 for(const version of ['before','after']){
  if(version==='after'){setBeforeAssets(false);await page.goto(info.base,{waitUntil:'domcontentloaded'});await audit();await page.locator('#token').fill('secret test token');await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});}
  await page.locator('.section-links a[href="#goal-cards-panel"]').click();await page.locator('#goal-card-new').click();
  for(const [key,value] of Object.entries(draft))await page.locator('#goal-card-'+key).fill(value);
  const state=await page.evaluate(()=>({fields:Object.fromEntries(['title','goal','known','assumptions','unresolved','constraints','acceptance_checks'].map(k=>[k,document.getElementById('goal-card-'+k).value])),status:document.getElementById('goal-card-status').textContent,runDisabled:document.getElementById('goal-card-run').disabled,consentDisabled:document.getElementById('trial-consent').disabled,ack:document.getElementById('trial-ack').checked,trial:document.getElementById('trial-status').textContent}));states.push(state);result.visual.states.push({version,...state});
  check(version+' unsaved draft cannot execute or grant trial consent',state.runDisabled&&state.consentDisabled&&!state.ack&&state.trial.includes('LIVE'));
  for(const width of [1366,390])await frame(version+'-goals-'+(width===390?'narrow':'wide')+'.png',width,'#goal-cards-panel');
  for(const width of [1366,390])await frame(version+'-editor-'+(width===390?'narrow':'wide')+'.png',width,'#goal-card-form');
 }
 assert.deepEqual(states[0],states[1]);check('same complete unsaved draft and original disabled gates before and after',true);
 await page.locator('#goal-card-goal').focus();check('real goal focus is visible',await page.locator('#goal-card-goal').evaluate(e=>document.activeElement===e&&e.matches(':focus-visible')&&getComputedStyle(e).outlineStyle!=='none'));
 await frame('goal-focus-wide.png',1366,'#goal-card-goal');
 await page.emulateMedia({reducedMotion:'reduce'});
 const motion=await page.locator('#goal-card-save').evaluate(e=>({reduce:matchMedia('(prefers-reduced-motion: reduce)').matches,transition:getComputedStyle(e).transitionDuration,animation:getComputedStyle(e).animationName}));result.visual.motion.push(motion);check('reduced-motion removes transitions without changing original gates',motion.reduce&&motion.transition==='0s'&&motion.animation==='none');
 await frame('goal-trial-narrow.png',390,'#trial-panel');check('full trial recovery and LIVE-closed status stay available',await page.locator('#trial-status').isVisible()&&await page.locator('#trial-recover').isVisible()&&await page.locator('#trial-panel').textContent().then(t=>t.includes('LIVE 关闭')));
 check('one GET-only window without page errors',result.counts.business_post===0&&result.counts.blocked===0&&!result.pageErrors.length&&result.requests.every(r=>r.method==='GET'));
 result.receipts=[];result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
