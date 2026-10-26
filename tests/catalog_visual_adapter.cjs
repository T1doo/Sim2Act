'use strict';
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const visual=require('../scripts/browser-ci/catalog-visual.cjs');
const contract=JSON.parse(fs.readFileSync(path.resolve(__dirname,'../docs/evidence/catalog-four-frame-wiring-20261026/execution.json'),'utf8'));
async function exercise(badMetadata=false){
 let after=false,viewport={width:1366,height:900};const names=[];
 const metadata={capabilities:{tools:['resource.read'],code_execution:'DISABLED'},connections:{model:'synthetic',mode:'MOCK',status:'MOCK_ENGINEERING'}};
 const loc=selector=>({click:async()=>{},fill:async()=>{},waitFor:async()=>{},scrollIntoViewIfNeeded:async()=>{},isVisible:async()=>true,evaluate:async()=>false});
 const page={locator:loc,reload:async()=>{after=true;},setViewportSize:async value=>{viewport=value;},waitForTimeout:async()=>{},evaluate:async fn=>{
  const text=fn.toString();if(text.includes('JSON.parse'))return {...metadata,connections:{...metadata.connections,model:badMetadata&&after?'drift':'synthetic'}};
  if(text.includes('activeRun'))return {run:null,app:null,goal:null,trial:[],keys:[]};
  if(text.includes('overflow'))return {...viewport,overflow:false,scrollX:0,scrollY:0,section:{}};
 }};
 const result={requests:['/','/app.css','/app.js'].map(p=>({path:p,baseline_asset:true})),screenshots:0,counts:{business_post:0,blocked:0},pageErrors:[]};
 await visual.runWorkspaceVisual({page,info:{catalog_comparison:contract,visual_source:{commit:'synthetic-adapter-test',asset_lf_sha256:Object.fromEntries(Object.entries(contract.after_assets).map(([n,h])=>['src/sim2act/web/'+n,h]))}},result,check:(n,v)=>assert.ok(v,n),shot:async name=>{names.push(name);result.screenshots++;},until:async()=>{},audit:async()=>{},setBeforeAssets:value=>assert.equal(value,false)});
 assert.deepEqual(names,['before-connections-1366.png','before-connections-390.png','after-connections-1366.png','after-connections-390.png']);assert.equal(result.status,'PASS');
}
(async()=>{
 for(const url of ['/','/app.css','/app.js'])assert.ok(visual.baselineAsset(url).body.length);
 assert.equal(visual.baselineAsset('/protocol.js'),null);
 assert.equal(await visual.responseFor({project:'p'},'GET','/api/capabilities'),undefined);
 assert.equal(await visual.responseFor({project:'p'},'GET','/health'),undefined);
 await assert.rejects(()=>visual.responseFor({project:'p'},'POST','/api/projects'));
 assert.deepEqual((await visual.responseFor({project:'p'},'GET','/api/projects/p/resources')).body,[]);
 await exercise();await assert.rejects(()=>exercise(true));
 console.log('PASS: baseline bytes/export, original metadata passthrough, GET-only routes, four frame order and metadata-drift rejection. Adapter harness only; no browser/PNG/HTTP.');
})().catch(e=>{console.error(e);process.exitCode=1;});
