'use strict';
// Dedicated read-only comparison. No legacy directory-failure state machine.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),crypto=require('node:crypto');
const repo=path.resolve(__dirname,'../..');
const contract=JSON.parse(fs.readFileSync(path.join(repo,'docs/evidence/catalog-four-frame-wiring-20261026/execution.json'),'utf8'));
function baselineAsset(pathname){
 const name=({'/':'index.html','/app.css':'app.css','/app.js':'app.js'})[pathname];
 if(!name)return null;
 const body=fs.readFileSync(path.join(repo,'docs/evidence/catalog-four-frame-plan-20261026/before-assets',name));
 const sha256=crypto.createHash('sha256').update(body).digest('hex');
 assert.equal(sha256,contract.before_assets[name]);
 return {body,sha256,contentType:name.endsWith('.html')?'text/html; charset=utf-8':name.endsWith('.css')?'text/css; charset=utf-8':'application/javascript; charset=utf-8'};
}
async function responseFor(info,method,pathname){
 assert.equal(method,'GET');
 // These are labelled presentation data, not persisted task facts. Metadata
 // and health are never intercepted and still use original API authorization.
 if(pathname==='/api/projects')return {body:[{id:info.project,name:'合成目录视觉核查'}]};
 if(pathname==='/api/apps')return {body:{items:[]}};
 const prefix=`/api/projects/${info.project}/`;
 if(pathname.startsWith(prefix)){
  const suffix=pathname.slice(prefix.length);
  if(['resources','runs','grants'].includes(suffix))return {body:[]};
  if(['goal-cards','protocol/contracts','conditional-apps'].includes(suffix))return {body:{items:[]}};
 }
 return undefined;
}
async function runWorkspaceVisual({page,info,result,check,shot,until,audit,setBeforeAssets}){
 assert.deepEqual(info.catalog_comparison,contract);
 for(const [name,hash] of Object.entries(contract.after_assets))assert.equal(info.visual_source.asset_lf_sha256['src/sim2act/web/'+name],hash);
 const read=()=>page.evaluate(()=>({capabilities:JSON.parse(document.getElementById('capabilities').textContent),connections:JSON.parse(document.getElementById('connections').textContent)}));
 const intent=()=>page.evaluate(()=>({run:activeRun,app:activeApp,goal:activeGoalCard,trial:[...trialEntries],keys:[...goalRunRequests]}));
 const initial=await intent();let original;
 result.catalogComparison={before:contract.before_product,after:contract.after_product,execution:info.visual_source.commit,frames:[],scope:'SYNTHETIC_METADATA_READBACK_NOT_MODEL_ACCEPTANCE'};
 for(const revision of ['before','after']){
  if(revision==='after'){
   setBeforeAssets(false);
   await page.reload({waitUntil:'domcontentloaded'});await audit();
   await page.locator('#token').fill('secret test token');await page.locator('#connect').click();
   await page.locator('#login').waitFor({state:'hidden'});
  }
  await until(()=>document.getElementById('connections').textContent.trim().length>0);
  const metadata=await read();
  assert.equal(metadata.connections.mode,'MOCK');assert.equal(metadata.connections.status,'MOCK_ENGINEERING');
  assert.equal(metadata.capabilities.code_execution,'DISABLED');
  if(revision==='before')original=metadata;else assert.deepEqual(metadata,original);
  await page.locator('#workspace-nav [data-tab="resources"]').click();
  await page.locator('#resource-filters [data-resource-category="connections"]').click();
  if(revision==='after'){
   await until(()=>!document.getElementById('resource-catalog-refresh').disabled);
   assert.equal(await page.locator('#connections').evaluate(el=>el.closest('details').open),false);
   assert.equal(await page.locator('#connection-summary').isVisible(),true);
  }
  for(const [width,height] of [[1366,900],[390,844]]){
   await page.setViewportSize({width,height});
   await page.locator('#resource-connections').scrollIntoViewIfNeeded();
   await page.evaluate(()=>document.fonts.ready);
   await page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
   await page.waitForTimeout(220);
   const geometry=await page.evaluate(()=>({width:innerWidth,height:innerHeight,scrollX,scrollY,overflow:document.documentElement.scrollWidth>innerWidth,section:document.getElementById('resource-connections').getBoundingClientRect().toJSON()}));
   assert.equal(geometry.overflow,false);
   await shot(`${revision}-connections-${width}.png`);
   result.catalogComparison.frames.push({revision,geometry,metadata});
  }
  assert.deepEqual(await intent(),initial);
 }
 const served=new Set(result.requests.filter(r=>r.baseline_asset).map(r=>r.path.split('?')[0]));
 for(const name of ['/','/app.css','/app.js'])assert.ok(served.has(name),'exact before asset was actually served: '+name);
 check('four source-bound connection frames; same original metadata; no task intent change',result.screenshots===4&&result.catalogComparison.frames.length===4);
 check('GET-only readback with no page error or blocked request',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0);
 result.receipts=[];result.status='PASS';
}
module.exports={baselineAsset,responseFor,runWorkspaceVisual};
