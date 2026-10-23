'use strict';
// One protected read-only content window; sealed before frames stay untouched.
const assert=require('node:assert/strict');
function baselineAsset(){throw Error('Content window never substitutes production assets');}
async function runWorkspaceVisual({page,info,result,check,shot,until,choose,audit,setFailLocator,setFailContent}){
 const item=info.cases[0];assert.equal(item.current.phase,'source');
 const source=info.visual_source;assert.match(source.commit,/^[a-f0-9]{40}$/);
 assert.deepEqual(Object.keys(source.asset_lf_sha256).sort(),['src/sim2act/web/app.css','src/sim2act/web/app.js','src/sim2act/web/index.html','src/sim2act/web/protocol.js','src/sim2act/web/use.js']);
 for(const hash of Object.values(source.asset_lf_sha256))assert.match(hash,/^[a-f0-9]{64}$/);
 result.visual={capture_revision:'research-desk-content-v1',product_source:source.commit,product_asset_lf_sha256:{...source.asset_lf_sha256},before_native_execution:'5f814c4831d84f5cdec0636c49740a6ad1c97429',layouts:[],content:[]};
 const view=width=>page.setViewportSize({width,height:width<500?844:900});
 async function stable(){
  await until(()=>document.getElementById('health').textContent.startsWith('健康检查：')&&!backgroundRefreshInFlight&&!protocolContext?.busy&&!applicationUse?.busy);
  await page.mouse.move(1,1);await page.waitForTimeout(200);await page.evaluate(()=>document.fonts.ready);
  await page.evaluate(()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r))));
 }
 async function frame(name,width,target){await view(width);if(target)await page.locator(target).scrollIntoViewIfNeeded();else await page.evaluate(()=>scrollTo(0,0));await stable();await shot(name);}
 async function geometry(workspace,width){
  await view(width);await stable();
  const m=await page.evaluate(id=>{const visible=e=>e.getClientRects().length&&getComputedStyle(e).visibility!=='hidden',nodes=[...document.getElementById(id).querySelectorAll('button,input,select,textarea,summary,pre')].filter(visible);return {workspace:id,width:innerWidth,documentWidth:document.documentElement.scrollWidth,overflow:nodes.filter(e=>{const r=e.getBoundingClientRect();return r.left<-.5||r.right>innerWidth+1;}).map(e=>e.id||e.tagName),hiddenLeaks:[...document.querySelectorAll('[hidden]')].filter(visible).map(e=>e.id)};},workspace);
  result.visual.layouts.push(m);check(`${workspace} ${width}px no overflow or hidden leak`,m.documentWidth<=width+1&&!m.overflow.length&&!m.hiddenLeaks.length);
 }
 await choose(info.run);await until(()=>!document.getElementById('protocol-reading-view').hidden);
 assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),item.current.result);
 check('source summary keeps UNKNOWN, PENDING and exact original JSON',await page.locator('#protocol-state-view').textContent().then(t=>t.includes('UNKNOWN')&&t.includes('PENDING'))&&await page.locator('#protocol-reading-view').textContent().then(t=>t.includes('UNKNOWN')));
 check('complete original JSON starts collapsed',await page.locator('#protocol-evidence').getAttribute('open')===null);
 const identifiers=await page.locator('.reading-identifiers').elementHandle();await page.locator('.reading-identifiers > summary').click();await page.waitForTimeout(2800);
 check('real unchanged 2500ms poll preserves expanded identifiers',await identifiers.evaluate(e=>e.isConnected&&e.open));await page.locator('.reading-identifiers > summary').click();
 for(const width of [1366,390])await geometry('projects',width);
 await frame('after-projects-wide.png',1366,'#protocol-state-view');await frame('after-projects-narrow.png',390,'#protocol-state-view');
 async function locate(){await page.locator('#protocol-completion-locate').click();await until(id=>!protocolContext.busy&&protocolCompletionReadbacks.get(protocolCompletionKey(protocolContext,id))?.state==='accepted',item.current.run_id);assert.deepEqual(JSON.parse(await page.locator('#protocol-result').textContent()),item.current.result);}
 await locate();setFailLocator(item.current.run_id);await page.locator('#protocol-completion-locate').click();await until(()=>!protocolContext.busy&&document.getElementById('protocol-state').textContent.includes('不可确认'));
 check('failed Source read clears summary and keeps true Run unchanged',await page.evaluate(()=>document.getElementById('protocol-reading-view').hidden&&document.getElementById('protocol-state-view').textContent.includes('不可确认')&&document.getElementById('protocol-result').textContent===''&&protocolContext.run.status==='WAITING_APPROVAL'&&document.getElementById('protocol-extract').hidden));
 await frame('after-source-error-narrow.png',390,'#protocol-state-view');await locate();
 await page.locator('[data-tab="resources"]').click();for(const width of [1366,390])await geometry('resources',width);
 await frame('after-resources-wide.png',1366);await frame('after-resources-narrow.png',390);
 const content=info.content;await page.goto(content.base,{waitUntil:'domcontentloaded'});await page.locator('#token').fill(content.token);await page.locator('#connect').click();await page.locator('#login').waitFor({state:'hidden'});await audit();
 assert.equal(await page.locator('#project-select').inputValue(),content.project_id);await page.locator('[data-tab="apps"]').click();
 const instance=page.locator(`#use-list [data-use-family="CSV"][data-instance-id="${content.instance_id}"]`);await instance.waitFor();
 for(const width of [1366,390])await geometry('apps',width);
 await frame('after-apps-wide.png',1366);await frame('after-apps-narrow.png',390);
 check('directory retains complete restrictions behind disclosure and original instance action',await instance.locator('details').count()===1&&await instance.getByRole('button',{name:'使用此本地实例',exact:true}).count()===1);
 await instance.locator('summary').click();await page.waitForTimeout(2800);check('real directory polling preserves the same-context disclosure',await instance.locator('details').getAttribute('open')!==null);await instance.locator('summary').click();
 await instance.getByRole('button',{name:'使用此本地实例',exact:true}).click();await until(id=>applicationUse?.id===id&&!document.getElementById('use-form').hidden,content.instance_id);
 const history=page.locator('#use-history').getByRole('button',{name:'查看这次运行',exact:true});assert.equal(await history.count(),1);await history.click();await until(id=>applicationUse?.selected===id&&document.getElementById('use-output').textContent.includes('合计 30'),content.run_id);
 const saved=await page.evaluate(c=>{const run=applicationUse.instance.runs.find(r=>r.id===c.run_id);return {historical:applicationUse.historical,status:run.status,result:run.result};},content);assert.deepEqual(saved,{historical:true,status:'SUCCEEDED',result:content.result.result});
 check('original saved instance/history reads exact real persisted result',true);
 for(const width of [1366,390])await geometry('apps',width);
 await frame('app-result-wide.png',1366,'#use-output');await frame('app-result-narrow.png',390,'#use-output');
 setFailContent();await page.locator('#use-refresh').click();await until(()=>document.getElementById('use-info').textContent.includes('无法读取'));
 check('failed instance read clears historical output and closes run form',await page.locator('#use-output').textContent()===''&&await page.locator('#use-form').isHidden()&&await page.locator('#use-refresh').isVisible());
 await frame('app-read-error-narrow.png',390,'#use-info');await page.locator('#use-refresh').click();await until(()=>document.getElementById('use-output').textContent.includes('合计 30'));
 check('explicit read-only recovery restores same Run without a new command',await page.evaluate(c=>applicationUse.selected===c.run_id&&applicationUse.id===c.instance_id,content));
 await page.locator('#use-list [data-use-family="CSV_MATERIAL_ACCESS"]').getByRole('button').click();check('material access view does not retain previous result-read error',await page.locator('#use-info').getAttribute('data-read-state')===null);
 result.visual.content.push({kind:'Source',run:item.current.run_id,exact_original_json:true,semantic:item.current.semantic_status,owner:item.current.owner_semantic_acceptance},{kind:'sealed CSV',instance:content.instance_id,run:content.run_id,result_version:content.result.result_version,sum:content.result.result.sum,read_failure_then_fresh_recovery:true,business_clock:content.business_at});
 check('entire content window only GET with no new command, page error or overrun',result.counts.business_post===0&&result.counts.blocked===0&&result.pageErrors.length===0&&result.requests.every(r=>r.method==='GET'));
 result.receipts=result.located.map(x=>x.receipt);result.status='PASS';
}
module.exports={baselineAsset,runWorkspaceVisual};
