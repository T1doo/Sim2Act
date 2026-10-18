'use strict';
// Installed package, real loopback HTTP and original product event handlers.
// No project, resource, candidate, Run, receipt or result is seeded by this driver.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {JSDOM} = require('jsdom');
const [base, output, mode, previous] = process.argv.slice(2);
const proof = {status: 'RUNNING', mode, browser: 'NOT_RUN', visual: 'NOT_RUN', checks: [], requests: [], assets: []};
let dom, w, $, phase = 'boot', pending = 0, holdPath = null, held = null;
const save = () => fs.writeFileSync(output, JSON.stringify({...proof, phase}, null, 2) + '\n');
const check = (value, label) => {assert(value, label); proof.checks.push(label); save();};
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
async function wait(fn, label) {
  const end = Date.now() + 15000;
  while (Date.now() < end) {if (fn()) return; await delay(25);}
  throw Error('Timed out: ' + label);
}
async function request(url, options = {}, label = 'product') {
  const target = new URL(url, base); assert.equal(target.origin, base);
  const record = {label, method: options.method || 'GET', path: target.pathname,
    ...(options.body ? {request_body: JSON.parse(options.body)} : {})};
  proof.requests.push(record); pending++; let counted = true;
  try {
    const response = await fetch(target, options), bytes = Buffer.from(await response.arrayBuffer());
    record.status = response.status; record.sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    if (target.pathname.startsWith('/api/')) record.response = JSON.parse(bytes.toString('utf8'));
    save();
    if(record.method==='GET'&&target.pathname===holdPath){
      holdPath=null;pending--;counted=false;record.delivery_delayed=true;
      await new Promise(resolve=>{held={record,release:resolve};save();});
      record.delivery_released=true;save();
    }
    return new Response(bytes, {status: response.status, headers: response.headers});
  } finally {if(counted)pending--;}
}
async function action(id, event = 'click') {
  const el = typeof id === 'string' ? $(id) : id;
  assert(visible(el), 'visible control: ' + (el?.id || id));
  assert(el && !el.disabled, 'enabled control: ' + (el?.id || id));
  const key = event === 'submit' ? 'onsubmit' : 'onclick', handler = el[key];
  assert.equal(typeof handler, 'function');
  let completion;
  el[key] = function (e) {completion = handler.call(this, e); return completion;};
  try {
    if (event === 'submit') el.dispatchEvent(new w.Event('submit', {cancelable: true}));
    else el.click();
    await completion; await wait(() => pending === 0, 'HTTP completion');
    assert.equal($('error').textContent, '', 'product error');
  } finally {el[key] = handler;}
}
async function readRun(path) {
  const response = await request(path, {headers: {Authorization: 'Bearer public-synthetic-blank-workspace'}}, 'bounded-result-read');
  assert.equal(response.status, 200); return response.json();
}
async function terminal(path) {
  const end = Date.now() + 18000;
  do {
    const run = await readRun(path);
    if (['SUCCEEDED', 'FAILED', 'PARTIAL'].includes(run.status)) return run;
    await delay(300);
  } while (Date.now() < end);
  throw Error('Worker terminal state not reached');
}
async function boot() {
  const root = await request('/', {}, 'root-page');
  proof.root_headers = Object.fromEntries(root.headers);
  check(root.headers.get('x-content-type-options') === 'nosniff' && root.headers.get('cache-control') === 'no-store'
    && root.headers.get('content-security-policy').includes("script-src 'self'"), 'root retains original three security headers');
  dom = new JSDOM(await root.text(), {url: base, runScripts: 'dangerously'});
  w = dom.window; $ = id => w.document.getElementById(id);
  w.crypto.randomUUID = crypto.randomUUID; w.crypto.subtle = crypto.webcrypto.subtle;
  w.TextEncoder = TextEncoder; w.TextDecoder = TextDecoder; w.structuredClone = structuredClone;
  w.fetch = request; w.setInterval = () => 0; // No page polling; launcher owns a Worker thread in the real server process.
  for (const src of [...w.document.querySelectorAll('script[src]')].map(el => el.getAttribute('src'))) {
    const response = await request(src, {}, 'installed-asset'), text = await response.text();
    assert.equal(response.status, 200); proof.assets.push({src, sha256: crypto.createHash('sha256').update(text).digest('hex')});
    const script = w.document.createElement('script');
    script.textContent = text + '\n//# sourceURL=' + src; w.document.body.append(script);
  }
  const css = await (await request('/app.css', {}, 'installed-css')).text();
  const style = w.document.createElement('style'); style.textContent = css; w.document.head.append(style);
  check($('synthetic-workspace-banner').textContent.includes('仅供非敏感练习材料'), 'explicit synthetic banner visible in installed page');
  $('token').value = 'public-synthetic-blank-workspace'; await action('connect');
  check($('login').hidden, 'connect through original product UI');
}
function visible(el) {for (let p=el;p;p=p.parentElement) if(p.hidden||w.getComputedStyle(p).display==='none') return false;return !!el?.isConnected;}
function choose(id, value) {$(id).value=value;$(id).dispatchEvent(new w.Event('change',{bubbles:true}));}
function consent(id) {assert(visible($(id))&&!$(id).disabled,id);$(id).checked=true;$(id).dispatchEvent(new w.Event('change',{bubbles:true}));}
async function stage(name) {save();process.stdout.write(JSON.stringify({stage:name})+'\n');await new Promise(resolve=>process.stdin.once('data',resolve));}
async function openInstance(instance) {
  w.document.querySelector('[data-tab="apps"]').click();
  const row=[...$('use-list').children].find(el=>el.dataset.instanceId===instance);
  assert(row,'directory has exact original instance');await action(row.querySelector('button'));
}
const posts=tail=>proof.requests.filter(r=>r.method==='POST'&&r.path.endsWith(tail));
(async()=>{
 try {
  const prior=JSON.parse(fs.readFileSync(previous,'utf8'));
  if(['new','authorize'].includes(mode))for(const key of ['project_id','resource_id','B_id','A_hash','B_hash','app_id','instance_id','old_release_id','goal'])proof[key]=prior[key];
  await boot();
  if(['new','authorize'].includes(mode)) {
   phase='original';await openInstance(proof.instance_id);
   check(w.eval('applicationUse.instance.revision')===1&&w.eval('applicationUse.instance.data_version')===0,'real initial Release1 has no previous revision, adoption or result');
   choose('use-column','amount');await action('use-form','submit');assert.equal(posts('/runs').at(-1).status,202);proof.old_run_id=w.eval('applicationUse.selected');
   proof.old_result=await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.old_run_id}`);
   check(proof.old_result.status==='SUCCEEDED'&&proof.old_result.result.sum==='30'&&proof.old_result.result.resource_id===proof.resource_id&&proof.old_result.result.source_hash===proof.A_hash&&proof.old_result.result_version===1,'original Worker computes old material A30/v1');
   await action('use-refresh');await stage('before-edit');
   if(mode==='authorize'){
    phase='explicit-app-authority';
    $('csv-access-lookup-key').value='nonexistent-read-only-key';$('csv-access-lookup-key').dispatchEvent(new w.Event('input'));
    await action('csv-access-lookup');check(w.eval('csvMaterialAccessIntents.get(csvMaterialAccessKey(applicationUse)).current')===null&&!$('use-form').hidden&&!$('csv-access-lookup-key').disabled,'failed read-only key query preserves no-write state and remains correctable');
    await action('csv-goal-baseline');proof.pre_authorization_baseline_key=w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).baselineKey');
    await action('csv-access-read');check($('csv-access-target').value===''&&$('csv-access-authorize').disabled,'authority list does not select or grant a material');
    choose('csv-access-target',proof.B_id);check($('csv-access-scope').textContent.includes(proof.B_hash)&&$('csv-access-scope').textContent.includes('全部实例')&&$('csv-access-scope').textContent.includes('24小时'),'exact B hash App runtime READ SUM all-instances and24h scope is visible');
    check($('csv-access-authorize').disabled,'App business authorization requires separate positive consent');consent('csv-access-ack');await stage('before-authorize');
    const sending=action('csv-access-authorize');$('csv-access-authorize').click();await sending;
    const auth=posts('/csv-material-access/authorizations');check(auth.length===1&&auth[0].status===201,'double click sends exactly one explicit App material authorization POST');
    proof.authorization=auth[0].response;proof.authorization_key=auth[0].request_body.request_key;
    check(proof.authorization.app_material_status==='ACTIVE'&&proof.authorization.receipt.grants.length===2&&proof.authorization.receipt.record.resource_id===proof.B_id,'server grants only selected B to exact existing App runtime');await stage('after-authorize');
    check(posts('/csv-material-revisions/previews').length===0&&posts('/adoption-approvals').length===0,'authorization alone creates no material proposal Release adoption or Run');
    await action('csv-access-next');proof.post_authorization_baseline_key=w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).baselineKey');
    check(proof.post_authorization_baseline_key!==proof.pre_authorization_baseline_key&&w.eval('csvGoalRevisionIntents.get(applicationUseKey(applicationUse)).history.some(x=>Object.keys(x.steps).includes("baseline"))'),'explicit new material cycle retains old accepted baseline key and uses a fresh key');
   }else{
    phase='direct-material';check(visible($('csv-material-first'))&&!$('csv-material-first').disabled,'first saved instance exposes direct material entry');
    await action('csv-material-first');await action('csv-material-back');
    check(visible($('csv-material-first'))&&w.eval('applicationUse.id')===proof.instance_id,'unsubmitted first-material choice returns to same original instance');
    await action('csv-material-first');
   }
   await action('csv-goal-baseline');
   check($('csv-goal-revision-status').textContent.includes('首版直接更换材料')&&$('csv-goal-revision-status').textContent.includes('Goal v1'),'UI distinguishes direct first material replacement and unchanged original Goal1');
   check($('csv-goal-preview').disabled,'material preview needs explicit target selection');
   const options=[...$('csv-material-target').options].filter(o=>o.value);check(options.length===1&&options[0].value===proof.B_id,'catalog offers exact already App-authorized B and excludes A');
   choose('csv-material-target',proof.B_id);choose('csv-goal-from','amount');
   check($('csv-goal-to').value==='amount'&&$('csv-goal-to').disabled&&!$('csv-goal-from').disabled&&!$('csv-goal-preview').disabled,'first user fixes shared amount column without changing column or Goal first');
   await stage('before-preview');const sending=action('csv-goal-preview');$('csv-goal-preview').click();await sending;
   const post=posts('/csv-material-revisions/previews');assert.equal(post.length,1);assert.equal(post[0].status,201);proof.preview=post[0].response;
   const changed=proof.preview.parent_graph.graph.nodes.filter(n=>proof.preview.impact.changed_nodes.includes(n.id)).map(n=>n.key).sort();
   check(changed.join()===['action:aggregate','source:'+proof.resource_id].sort().join()&&proof.preview.impact.revalidation_scope==='APP','SOURCE plus explicit ACTION input constraint undergo complete APP recheck');
   check(proof.preview.context.initial_material===true&&proof.preview.context.parent.spec_revision===1&&proof.preview.context.parent.column===null&&proof.preview.context.goal.version===1&&proof.preview.spec_revision===2&&proof.preview.material.resource_id===proof.B_id&&proof.preview.material.hash===proof.B_hash,'first proposal freezes B hash directly from original spec1 and Goal1');
   await stage('after-preview');
   phase='check';check($('csv-goal-check').disabled,'independent CHECK requires separate explicit consent');consent('csv-goal-check-ack');await action('csv-goal-check');proof.check_run_id=posts('/csv-goal-revisions/checks').at(-1).response.run_id;
   const end=Date.now()+20000;do {await action('csv-goal-outcome');if($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'))break;await delay(300);}while(Date.now()<end);
   check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'),'original background Worker actually completes isolated material B CHECK');
   phase='release-adopt';await action('csv-goal-version');check($('csv-goal-release').disabled,'new Release requires explicit confirmation');consent('csv-goal-release-ack');await action('csv-goal-release');
   check(posts('/adoption-approvals').length===0,'saving new Release never automatically adopts');await action('csv-goal-adopt-prepare');consent('csv-goal-adopt-ack');await action('csv-goal-adopt');
   proof.new_release_id=w.eval('applicationUse.instance.release_id');
   check(w.eval('applicationUse.id')===proof.instance_id&&w.eval('applicationUse.instance.revision')===2&&proof.new_release_id!==proof.old_release_id&&[...$('use-column').options].map(o=>o.value).join()==='amount','same original instance adopts first material Release2 and fixed amount');await stage('after-adopt');
   phase='new-run';consent('use-csv-review-optin');await action('use-form','submit');assert.equal(posts('/runs').at(-1).status,202);proof.new_run_id=w.eval('applicationUse.selected');assert.match(proof.new_run_id,/^run_[a-f0-9]{32}$/);
   proof.new_result=await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.new_run_id}`);
   check(proof.new_result.status==='SUCCEEDED'&&proof.new_result.result.sum==='350'&&proof.new_result.result_version===2&&proof.new_result.result.resource_id===proof.B_id&&proof.new_result.result.source_hash===proof.B_hash&&proof.new_result.release_id===proof.new_release_id,'new explicit Run actually reads B amount350/v2, not A or alternate column');
   await action('use-refresh');await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING'),'same new Run has independent PENDING human entry');
   check(!proof.requests.some(r=>r.method==='PUT')&&posts('/csv-goal-revisions/previews').length===0,'no Goal edit or preliminary column revision was used');await stage('after-new-run');
  }else if(mode==='withdraw'){
   phase='cold-metadata-withdraw';
   await openInstance(prior.instance_id);
   const resultRow=[...$('use-history').children].find(el=>el.textContent.includes(prior.new_run_id.slice(0,18))&&el.querySelector('button'));assert(resultRow);await action(resultRow.querySelector('button'));
   check($('use-output').textContent.includes('合计 350')&&$('use-column').options.length>0,'actual B result and private column view visible before source authority loss');
   const rows=await readRun(`/api/projects/${prior.project_id}/grants`),gid=rows.find(r=>r.principal_id===prior.authorization.receipt.record.principal_id&&r.resource_id===prior.resource_id&&r.tool_ref==='resource.read');assert(gid);
   proof.upstream_revoked_gid=gid.id;
   const removed=await request(`/api/grants/${gid.id}/revoke`,{method:'POST',headers:{Authorization:'Bearer public-synthetic-blank-workspace','Content-Type':'application/json'},body:JSON.stringify({command:'revoke',version:gid.revision})},'existing-owner-Grant-withdrawal');assert.equal(removed.status,200);
   await action('csv-access-read');check($('use-output').textContent===''&&$('use-column').options.length===0&&!$('csv-goal-revision')&&$('use-form').hidden&&visible($('csv-access-state')),'403 clears private results columns and frozen Goal review while metadata withdrawal remains reachable');
   w.document.querySelector('[data-tab="apps"]').click();
   const open=async()=>{const row=[...$('use-list').children].find(el=>el.dataset.appId===prior.app_id&&el.dataset.useFamily==='CSV_MATERIAL_ACCESS');assert(row,'App-level material authority entry survives unreadable current result');await action(row.querySelector('button'));};
   await open();
   $('csv-access-lookup-key').value=prior.authorization_key;$('csv-access-lookup-key').dispatchEvent(new w.Event('input'));await action('csv-access-lookup');
   check($('csv-access-proof').textContent.includes('"receipt_status": "ACTIVE"'),'cold original authorization key is metadata-only and currently active');
   holdPath=`/api/apps/${prior.app_id}/csv-material-access/authorizations/${prior.authorization_key}`;
   const delayed=action('csv-access-recover');await wait(()=>held,'actual ACTIVE metadata response held before UI delivery');
   await open();await action('csv-access-state');choose('csv-access-target',prior.B_id);consent('csv-access-stop-ack');await stage('before-withdraw');
   const sending=action('csv-access-revoke');$('csv-access-revoke').click();await sending;
   const revokes=posts('/csv-material-access/revocations');check(revokes.length===1&&revokes[0].status===201,'explicit atomic withdrawal double click sends one POST');
   proof.withdrawal=revokes[0].response;check(proof.withdrawal.receipt_status==='REVOKED'&&proof.withdrawal.app_material_status==='INACTIVE','exact App material pair is withdrawn');
   held.release();await delayed;
   check(w.eval('applicationUse.authOnly')&&$('use-output').textContent===''&&$('csv-access-next').disabled&&!$('csv-access-proof').textContent.includes('"receipt_status": "ACTIVE"'),'late former ACTIVE response cannot install in new App view or restore next-step access');
   await action('csv-access-recover');check($('csv-access-proof').textContent.includes('"receipt_status": "REVOKED"'),'current original withdrawal receipt remains revoked');
   const fresh=await readRun(`/api/apps/${prior.app_id}/csv-material-access/authorizations/${prior.authorization_key}`);check(fresh.receipt_status==='REVOKED'&&fresh.app_material_status==='INACTIVE','original authorization key now reads withdrawn current state');
   const denied=await request(`/api/internal/instances/${prior.instance_id}/runs/${prior.new_run_id}`,{headers:{Authorization:'Bearer public-synthetic-blank-workspace'}},'withdrawn-private-result');check(denied.status===403,'new B result remains inaccessible after withdrawal');
   check(posts('/csv-material-access/authorizations').length===0&&posts('/runs').length===0,'withdrawal and delayed callback never grant or compute');await stage('after-withdraw');
  }else{
   assert.equal(mode,'cold');await openInstance(prior.instance_id);check($('project-select').value===prior.project_id&&w.eval('applicationUse.instance.release_id')===prior.new_release_id,'cold original project and iid retain new material Release');
   for(const[id,sum,release,resource,hash]of [[prior.old_run_id,'30',prior.old_release_id,prior.resource_id,prior.A_hash],[prior.new_run_id,'350',prior.new_release_id,prior.B_id,prior.B_hash]]){
    const row=[...$('use-history').children].find(el=>el.textContent.includes(id.slice(0,18))&&el.querySelector('button'));assert(row);await action(row.querySelector('button'));
    check(w.eval('applicationUse.selected')===id&&$('use-output').textContent.includes('合计 '+sum),'cold exact historical Run '+id+' sum'+sum);
    const dto=await readRun(`/api/internal/instances/${prior.instance_id}/runs/${id}`);check(dto.release_id===release&&dto.result.resource_id===resource&&dto.result.source_hash===hash,'historical Run retains exact Release and actual material hash');
   }
   check(proof.requests.every(r=>r.method==='GET'),'cold page entirely GET, neither old nor new computation replayed');
  }
  proof.status='PASS';phase='complete';save();
 }catch(error){proof.status='FAIL';proof.error={name:error.name,message:error.message,stack:error.stack};save();process.exitCode=1;}
 finally {dom?.window.close();process.stdin.pause();}
})();
