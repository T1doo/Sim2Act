'use strict';
// Installed package, real loopback HTTP and original product event handlers.
// No project, resource, candidate, Run, receipt or result is seeded by this driver.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const {JSDOM} = require('jsdom');
const [base, output, mode, previous] = process.argv.slice(2);
const proof = {status: 'RUNNING', mode, browser: 'NOT_RUN', visual: 'NOT_RUN', checks: [], requests: [], assets: []};
let dom, w, $, phase = 'boot', pending = 0;
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
  proof.requests.push(record); pending++;
  try {
    const response = await fetch(target, options), bytes = Buffer.from(await response.arrayBuffer());
    record.status = response.status; record.sha256 = crypto.createHash('sha256').update(bytes).digest('hex');
    if (target.pathname.startsWith('/api/')) record.response = JSON.parse(bytes.toString('utf8'));
    save();
    return new Response(bytes, {status: response.status, headers: response.headers});
  } finally {pending--;}
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
  await boot();
  if(mode==='new') {
   check($('project-select').options.length===0,'blank workspace starts with zero projects');
   phase='project';$('project-name').value='首版列绑定 合成工程';await action('project-form','submit');proof.project_id=$('project-select').value;
   w.document.querySelector('[data-tab="resources"]').click();$('resource-name').value='two-columns.csv';$('format').value='csv';$('content').value='item,amount,quantity\nA,10,7\nB,20,8\n';await action('resource-form','submit');proof.resource_id=$('app-resource').value;
   phase='goal-v1';w.document.querySelector('[data-tab="projects"]').click();await action('goal-card-new');
   const content={title:'明确选列的合成汇总',goal:'对用户明确选定的CSV数值列求和并返回记录数，保留每次结果历史',known:'两条合成记录；两列均为数值',assumptions:'用户明确选择本次绑定列',unresolved:'真实语义与人工签收未执行',constraints:'不调用模型、不新增权限、不正式发布',acceptance_checks:'精确求和所选列并报告两条记录'};
   for(const[key,value]of Object.entries(content))$('goal-card-'+key).value=value;
   Array.from($('goal-card-resources').options).forEach(el=>el.selected=el.value===proof.resource_id);await action('goal-card-form','submit');proof.goal=w.eval('activeGoalCard');
   $('goal-candidate-resource').value=proof.resource_id;$('goal-candidate-capability').value='csv.sum';await action('goal-candidate-form','submit');proof.app_id=w.eval('activeApp');
   phase='initial-release';$('app-column').value='amount';await action('app-preview-form','submit');await action('internal-prepare');consent('internal-approval-ack');await action('internal-commit');await action($('internal-releases').querySelector('button'));
   proof.instance_id=w.eval('engineering.instance.id');proof.old_release_id=w.eval('engineering.instance.release_id');
   phase='old-run';$('internal-column').value='amount';await action('internal-run-form','submit');proof.old_run_id=w.eval('engineering.run.id');proof.old_result=await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.old_run_id}`);
   check(proof.old_result.status==='SUCCEEDED'&&proof.old_result.result.sum==='30'&&proof.old_result.result_version===1,'initial ordinary Worker creates result30 version1');
   await action('internal-refresh');w.document.querySelector('[data-tab="projects"]').click();await action('run-history-refresh');await openInstance(proof.instance_id);await stage('before-edit');
   phase='first-column-preview';check(visible($('csv-goal-baseline')),'first saved instance has visible editing entry');await action('csv-goal-baseline');
   check($('csv-goal-revision-status').textContent.includes('保留原 Goal v1'),'UI explicitly allows original Goal1 without editing it');
   choose('csv-goal-from','amount');choose('csv-goal-to','amount');check($('csv-goal-preview').disabled,'same original Goal and same column cannot submit');
   choose('csv-goal-to','quantity');check(!$('csv-goal-preview').disabled,'different existing column enables first-version edit without Goal PUT');
   await stage('before-preview');
   const sending=action('csv-goal-preview');$('csv-goal-preview').click();await sending;
   const preview=posts('/csv-goal-revisions/previews').at(-1);assert.equal(preview.status,201);proof.preview=preview.response;
   check(posts('/csv-goal-revisions/previews').length===1,'double click sends one preview POST');
   const actionNode=proof.preview.baseline_graph.graph.nodes.find(n=>n.key==='action:aggregate');
   check(proof.preview.context.goal.version===1&&proof.preview.impact.changed_nodes.join()===actionNode.id&&proof.preview.impact.revalidation_scope==='APP','only ACTION explicitly changed and original full APP CHECK retained');
   check(proof.preview.effective_candidate.manifest.revision===2&&proof.preview.effective_candidate.manifest.input_schema.properties.column.enum.join()==='quantity','new specification2 visibly freezes explicit quantity binding');
   await stage('after-preview');
   phase='check';check($('csv-goal-check').disabled,'actual isolated CHECK needs separate consent');consent('csv-goal-check-ack');await action('csv-goal-check');proof.check_run_id=posts('/csv-goal-revisions/checks').at(-1).response.run_id;
   const end=Date.now()+20000;do {await action('csv-goal-outcome');if($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'))break;await delay(300);}while(Date.now()<end);
   check($('csv-goal-revision-proof').textContent.includes('"status": "PASS"'),'original background Worker performs isolated CHECK successfully');
   phase='new-release-adopt';await action('csv-goal-version');check($('csv-goal-release').disabled,'new Release requires its own explicit confirmation');consent('csv-goal-release-ack');await action('csv-goal-release');
   check(posts('/adoption-approvals').length===0,'saving Release does not auto-adopt original instance');await action('csv-goal-adopt-prepare');consent('csv-goal-adopt-ack');await action('csv-goal-adopt');
   proof.new_release_id=w.eval('applicationUse.instance.release_id');
   check(w.eval('applicationUse.id')===proof.instance_id&&w.eval('applicationUse.instance.revision')===2&&proof.new_release_id!==proof.old_release_id&&[...$('use-column').options].map(o=>o.value).join()==='quantity','same original instance explicitly adopts new Release and fixed quantity');
   await stage('after-adopt');
   phase='new-run';consent('use-csv-review-optin');await action('use-form','submit');assert.equal(posts('/runs').at(-1).status,202,'new Run must be accepted before polling');proof.new_run_id=w.eval('applicationUse.selected');assert.match(proof.new_run_id,/^run_[a-f0-9]{32}$/);proof.new_result=await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.new_run_id}`);
   check(proof.new_result.status==='SUCCEEDED'&&proof.new_result.result.sum==='15'&&proof.new_result.result_version===2&&proof.new_result.release_id===proof.new_release_id,'new explicit Run recalculates quantity15 version2 in same instance');
   await action('use-refresh');await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING'),'new result retains independent PENDING human acceptance');
   check(!proof.requests.some(r=>r.method==='PUT'),'complete version change never edits Goal or any resource');
   await stage('after-new-run');
  } else if(mode==='adopted') {
   const old=JSON.parse(fs.readFileSync(previous,'utf8'));
   for(const key of ['project_id','resource_id','goal','app_id','instance_id','old_release_id','old_run_id','old_result','check_run_id','preview'])proof[key]=old[key];
   phase='adopted-continuation';await openInstance(old.instance_id);
   check(w.eval('applicationUse?.instance?.revision')===2,'previously accepted same-instance adoption read back without replay');
   proof.new_release_id=w.eval('applicationUse.instance.release_id');
   check(proof.new_release_id!==old.old_release_id&&[...$('use-column').options].map(o=>o.value).join()==='quantity','adopted original Goal1 exposes quantity binding');
   check(proof.requests.every(r=>r.method==='GET'),'continuation reads accepted state before any new Run');await stage('before-new-run');
   phase='new-run';consent('use-csv-review-optin');await action('use-form','submit');assert.equal(posts('/runs').at(-1).status,202,'new Run must be accepted before polling');proof.new_run_id=w.eval('applicationUse.selected');assert.match(proof.new_run_id,/^run_[a-f0-9]{32}$/);proof.new_result=await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.new_run_id}`);
   check(proof.new_result.status==='SUCCEEDED'&&proof.new_result.result.sum==='15'&&proof.new_result.result_version===2&&proof.new_result.release_id===proof.new_release_id,'new explicit Run recalculates quantity15 version2 in same adopted instance');
   await action('use-refresh');await action('csv-owner-read');check($('csv-owner-status').textContent.includes('PENDING'),'new result human decision remains PENDING');await stage('after-new-run');
  } else {
   assert.equal(mode,'cold');const old=JSON.parse(fs.readFileSync(previous,'utf8'));await openInstance(old.instance_id);
   check($('project-select').value===old.project_id&&w.eval('applicationUse.instance.release_id')===old.new_release_id,'cold original project and instance retain adopted new Release');
   for(const[id,sum,release]of [[old.old_run_id,'30',old.old_release_id],[old.new_run_id,'15',old.new_release_id]]) {
    const row=[...$('use-history').children].find(el=>el.textContent.includes(id.slice(0,18))&&el.querySelector('button'));assert(row);await action(row.querySelector('button'));
    check(w.eval('applicationUse.selected')===id&&$('use-output').textContent.includes('合计 '+sum),'cold page reads exact historical Run '+id+' sum'+sum);
    const dto=await readRun(`/api/internal/instances/${old.instance_id}/runs/${id}`);check(dto.release_id===release,'historical Run retains its exact original Release');
   }
   check(proof.requests.every(r=>r.method==='GET'),'cold full page is entirely GET with no re-execution');
  }
  proof.status='PASS';phase='complete';save();
 }catch(error) {proof.status='FAIL';proof.error={name:error.name,message:error.message,stack:error.stack};save();process.exitCode=1;}
 finally {dom?.window.close();process.stdin.pause();}
})();
