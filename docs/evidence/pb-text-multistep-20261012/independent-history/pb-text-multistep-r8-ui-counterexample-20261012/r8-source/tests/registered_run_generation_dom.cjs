'use strict';
// Real local HTTP + jsdom only. No layout, visual, native browser or provider claim.
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const {JSDOM}=require('jsdom');
const info=JSON.parse(process.argv[2]),base=info.base,calls=[];
let drop=true,hold=false,releaseHeld,dropReadPath=null;
const dom=new JSDOM(fs.readFileSync('src/sim2act/web/index.html','utf8'),{url:base,runScripts:'outside-only'}),w=dom.window;
w.structuredClone=structuredClone;w.TextEncoder=TextEncoder;w.crypto.randomUUID=require('node:crypto').randomUUID;
w.fetch=async(url,options={})=>{
 const response=await fetch(new URL(url,base),options);
 calls.push({url,method:options.method || 'GET',body:options.body && JSON.parse(options.body)});
 if(hold && url.endsWith('/extraction-options')){hold=false;await new Promise(resolve=>releaseHeld=resolve);}
 if(drop && options.method==='POST' && url.endsWith('/extract')){drop=false;assert.equal(response.status,201);throw Error('Injected lost delivery after real server accepted generation');}
 if(options.method==='POST' && url.endsWith('/extract'))dropReadPath='/api/apps/'+(await response.clone().json()).id;
 if(dropReadPath===url){dropReadPath=null;throw Error('Injected accepted draft readback delivery loss');}
 return response;
};
for(const file of ['app.js','internal.js'])vm.runInContext(fs.readFileSync(`src/sim2act/web/${file}`,'utf8'),dom.getInternalVMContext());
const $=id=>w.document.getElementById(id),checks=[];
function check(name,value){assert.ok(value,name);checks.push(name);}
async function wait(fn){const end=Date.now()+10000;while(!fn()){assert.ok(Date.now()<end,'DOM wait timed out');await new Promise(r=>setTimeout(r,20));}}
async function openSource(){await w.eval(`showApp(${JSON.stringify(info.sourceApp)})`);await w.eval(`showInternalInstance(${JSON.stringify(info.iid)})`);await w.eval(`showInternalRun(${JSON.stringify(info.rid)})`);}
(async()=>{
 try{
  $('token').value='synthetic-test-A';$('connect').click();await wait(()=>$('login').hidden);
  $('project-select').value=info.pid;await w.eval('refresh()');await openSource();
  check('real successful registered Run exposes generation entry',!$('registered-extraction').hidden);
  await $('registered-extraction-open').onclick();
  check('server verified proof and target selection render',!$('registered-extraction-form').hidden && $('registered-extraction-proof').textContent.includes('completed_registered_csv_apprun.v1'));
  $('registered-extraction-target').value=info.target;$('registered-extraction-target').onchange();
  check('existing shared authorization domain is visible',$('registered-extraction-target-info').textContent.includes('共享授权撤回'));
  await w.eval('submitRegisteredExtraction()');
  check('lost accepted receipt offers manual retry',!$('registered-extraction-retry').hidden && $('registered-extraction-status').textContent.includes('不会自动重发'));
  const first=calls.find(c=>c.url.endsWith('/extract')).body;
  check('user sends no candidate wire or privilege fields',Object.keys(first).sort().join(',')==='expected_proof_fingerprint,expected_target_draft_fingerprint,name,request_key,target_app_id');
  $('registered-extraction-name').value='Another name';$('registered-extraction-name').oninput();
  check('changed accepted configuration does not reuse original pending body',$('registered-extraction-retry').hidden);
  $('registered-extraction-name').value=first.name;$('registered-extraction-name').oninput();
  check('restored original configuration restores its pending request',!$('registered-extraction-retry').hidden);
  await $('registered-extraction-retry').onclick();
  const mutations=calls.filter(c=>c.url.endsWith('/extract'));
  check('manual retry sends exact original key and body',JSON.stringify(mutations[0].body)===JSON.stringify(mutations[1].body));
  check('accepted generated draft readback failure exposes read-only recovery',!$('app-read-retry').hidden && $('app-create-status').textContent.includes('草案已创建'));
  await $('app-read-retry').onclick();
  check('generated app opens through actual HTTP view' ,$('app-origin').textContent.includes('已成功内部 CSV AppRun') && $('app-origin').textContent.includes('NOT_RUN'));
  const generated=w.eval('activeApp');check('generated app differs from both existing apps',generated!==info.sourceApp && generated!==info.target);
  await openSource();await $('registered-extraction-open').onclick();
  $('registered-extraction-name').value='Private prior-owner name';$('registered-extraction-name').oninput();
  await w.eval(`showInternalRun(${JSON.stringify(info.rid)})`);
  check('same-source same-version polling preserves current name',$('registered-extraction-name').value==='Private prior-owner name');
  hold=true;const reading=$('registered-extraction-open').onclick();await wait(()=>!!releaseHeld);
  await w.eval(`showApp(${JSON.stringify(info.target)})`);releaseHeld();await reading;
  check('late previous-source options cannot render protected form',$('registered-extraction').hidden && $('registered-extraction-proof').textContent==='');
  check('source switch clears prior-owner edited name',$('registered-extraction-name').value==='从成功任务保存的汇总');
  await openSource();await $('registered-extraction-open').onclick();
  w.eval('token="synthetic-test-B"');$('registered-extraction-target').value=info.target;$('registered-extraction-target').onchange();
  const count=calls.filter(c=>c.url.endsWith('/extract')).length;await w.eval('submitRegisteredExtraction()');
  check('identity change blocks stale source submission',count===calls.filter(c=>c.url.endsWith('/extract')).length);
  w.eval('token="synthetic-test-A"');await openSource();await $('registered-extraction-open').onclick();
  $('registered-extraction-target').value=info.target;$('registered-extraction-target').onchange();$('registered-extraction-name').value='Revoked target';$('registered-extraction-name').oninput();
  const target=w.eval('registeredExtraction.options.targets.find(t=>t.id===document.getElementById("registered-extraction-target").value)');
  const grant=(await w.eval(`api('/api/projects/${info.pid}/grants')`)).find(g=>g.principal_id===target.runtime_id && g.resource_id===target.resource_id && !g.revoked);
  assert.ok(grant,'existing target grant');
  await w.eval(`api('/api/grants/${grant.id}/revoke','POST',{command:'revoke',version:${grant.revision}})`);
  await w.eval('submitRegisteredExtraction()');
  check('revocation after options clears protected source/target and refuses generation',$('registered-extraction').hidden && $('registered-extraction-proof').textContent==='' && $('internal-status').dataset.state==='error');
  console.log(JSON.stringify({kind:'HTTP-backed jsdom',browser:'NOT_RUN',visual:'NOT_RUN',checks,generated,revokedGrantId:grant.id}));
 }finally{dom.window.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
