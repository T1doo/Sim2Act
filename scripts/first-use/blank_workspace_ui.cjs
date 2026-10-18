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
  check($('synthetic-workspace-banner').textContent.includes('仅供非敏感练习材料'), 'explicit synthetic banner visible in installed page');
  $('token').value = 'public-synthetic-blank-workspace'; await action('connect');
  check($('login').hidden, 'connect through original product UI');
}
(async () => {
  try {
    await boot();
    if (mode === 'new') {
      check($('project-select').options.length === 0, 'new workspace has zero projects');
      phase = 'project'; $('project-name').value = '空白工程 安装包合成练习'; await action('project-form', 'submit');
      proof.project_id = $('project-select').value; check(/^proj_/.test(proof.project_id), 'user creates a project through original form');
      phase = 'csv'; w.document.querySelector('[data-tab="resources"]').click();
      $('resource-name').value = 'synthetic.csv'; $('format').value = 'csv';
      $('content').value = 'item,amount\nA,10\nB,20\n'; await action('resource-form', 'submit');
      proof.resource_id = $('app-resource').value; check(/^res_/.test(proof.resource_id), 'user saves actual CSV through original resource form');
      phase = 'model-refusal'; w.document.querySelector('[data-tab="projects"]').click();
      $('goal').value = 'Synthetic unsupported model task; no provider may be invoked';
      Array.from($('run-materials').options).forEach(el => el.selected = el.value === proof.resource_id);
      await action('run-form', 'submit'); proof.refused_run_id = w.eval('activeRun');
      const refused = await terminal('/api/runs/' + proof.refused_run_id);
      check(refused.status === 'FAILED' && refused.error.code === 'UNSUPPORTED_CAPABILITY', 'unsupported model task fails without stopping service');
      phase = 'goal'; w.document.querySelector('[data-tab="projects"]').click(); await action('goal-card-new');
      const content = {title: '合成求和工程目标', goal: '明确汇总合成CSV的amount列并核对结果30',
        known: '两条合成记录10和20', assumptions: '仅用于固定工具练习', unresolved: '真实目标语义未验收',
        constraints: '不调用真实模型，不正式发布', acceptance_checks: '合计30且记录数2'};
      for (const [key, value] of Object.entries(content)) $('goal-card-' + key).value = value;
      Array.from($('goal-card-resources').options).forEach(el => el.selected = el.value === proof.resource_id);
      await action('goal-card-form', 'submit'); proof.goal = w.eval('activeGoalCard');
      check(proof.goal?.version === 1 && !$('goal-candidate-form').hidden, 'complete Goal v1 saved and fixed candidate choice available');
      phase = 'candidate'; $('goal-candidate-resource').value = proof.resource_id; $('goal-candidate-capability').value = 'csv.sum';
      await action('goal-candidate-form', 'submit'); proof.app_id = w.eval('activeApp');
      check(!!proof.app_id && !$('app-preview-form').hidden, 'explicit fixed capability creates ordinary private candidate');
      phase = 'preview'; $('app-column').value = 'amount'; await action('app-preview-form', 'submit');
      check($('app-output').textContent.includes('30') && $('app-output').textContent.includes('SUCCEEDED'), 'actual registered-tool preview produces 30');
      phase = 'release'; await action('internal-prepare');
      $('internal-approval-ack').checked = true; $('internal-approval-ack').dispatchEvent(new w.Event('change'));
      await action('internal-commit'); await action($('internal-releases').querySelector('button'));
      proof.instance_id = w.eval('engineering.instance.id'); proof.release_id = w.eval('engineering.instance.release_id');
      check(!$('internal-run-form').hidden, 'explicit internal Release and instance available');
      phase = 'worker-run'; $('internal-column').value = 'amount'; await action('internal-run-form', 'submit');
      proof.run_id = w.eval('engineering.run.id');
      const result = await terminal(`/api/internal/instances/${proof.instance_id}/runs/${proof.run_id}`);
      check(result.status === 'SUCCEEDED' && result.result.sum === '30' && result.result.count === 2 && result.result_version === 1,
        'ordinary background Worker produces persistent result 30 version1');
      await action('internal-refresh'); check($('internal-data').textContent.includes('30'), 'same Run result visible through original UI refresh');
      proof.result = result;
    } else {
      assert.equal(mode, 'cold'); const old = JSON.parse(fs.readFileSync(previous, 'utf8'));
      check($('project-select').value === old.project_id, 'cold installed page selects same persistent project');
      phase = 'cold-directory'; w.document.querySelector('[data-tab="apps"]').click();
      const row = [...$('use-list').children].find(el => el.dataset.appId === old.app_id);
      check(!!row, 'same saved application discoverable in unified directory'); await action(row.querySelector('button'));
      check(w.eval('applicationUse.id') === old.instance_id && !$('use-form').hidden, 'directory opens same persisted instance');
      const history = [...$('use-history').querySelectorAll('button')]; check(history.length === 1, 'exactly one persistent application Run available');
      await action(history[0]);
      check(w.eval('applicationUse.selected') === old.run_id && $('use-output').textContent.includes('合计 30'), 'cold page reads same Run and result30');
      check(proof.requests.every(r => r.method === 'GET'), 'entire cold page performs GET only with no new Run');
      proof.project_id = old.project_id; proof.instance_id = old.instance_id; proof.run_id = old.run_id;
    }
    await wait(() => pending === 0, 'final HTTP completion'); proof.status = 'PASS'; phase = 'complete'; save();
  } catch (error) {
    proof.status = 'FAIL'; proof.error = {name: error.name, message: error.message, stack: error.stack}; save(); process.exitCode = 1;
  } finally {dom?.window.close();}
})();
