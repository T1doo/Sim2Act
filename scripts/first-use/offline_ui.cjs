'use strict';
// Actual product UI events + loopback HTTP. No gold result/candidate is seeded.
const fs = require('node:fs');
const assert = require('node:assert/strict');
const {randomUUID} = require('node:crypto');
const {JSDOM} = require('jsdom');
const base = process.argv[2], output = process.argv[3];
const checks = [], writes = [], requests = [];
let dom, w, $, phase = 'connect', pending = 0, intervals = [];
async function closePage() {
  if (!dom) return;
  for (const id of intervals) w.clearInterval(id);
  intervals = [];
  await wait(() => pending === 0);
  await new Promise(r => setTimeout(r, 50));
  dom.window.close(); dom = null;
}
const check = (ok, name) => {assert(ok, name); checks.push(name);};
const wait = async (fn) => {
  const end = Date.now() + 8000;
  while (Date.now() < end) {if (fn()) return; await new Promise(r => setTimeout(r, 20));}
  throw Error('UI state not reached');
};
const submit = id => $(id).dispatchEvent(new w.Event('submit', {cancelable: true}));
const tab = name => w.document.querySelector(`[data-tab="${name}"]`).click();
async function connect() {
  await closePage();
  dom = new JSDOM(await (await fetch(base)).text(), {url: base, runScripts: 'dangerously'});
  w = dom.window; $ = id => w.document.getElementById(id);
  w.crypto.randomUUID = randomUUID;
  const setInterval = w.setInterval.bind(w);
  w.setInterval = (...args) => {const id = setInterval(...args); intervals.push(id); return id;};
  w.fetch = async (url, options = {}) => {
    const target = new URL(url, base); assert.equal(target.origin, base);
    const method = (options.method || 'GET').toUpperCase();
    requests.push({method, path: target.pathname});
    if (method === 'POST') writes.push(target.pathname);
    pending++;
    try {
      const response = await fetch(target, options);
      const body = await response.arrayBuffer();
      return new Response(body, {status: response.status, headers: response.headers});
    } finally {pending--;}

  };
  const files = [...w.document.querySelectorAll('script[src]')].map(s => s.getAttribute('src'));
  for (const file of files) {
    const script = w.document.createElement('script');
    script.textContent = await (await fetch(base + file)).text();
    w.document.body.append(script);
  }
  $('token').value = 'synthetic-first-use-A'; $('connect').click();
  await wait(() => $('login').hidden);
}
(async () => {
  try {
    await connect();
    check($('project-select').options.length === 0, 'new synthetic database has no project');
    phase = 'create-project';
    $('project-name').value = '首次体验 合成材料'; submit('project-form');
    await wait(() => $('project-select').value);
    const project = $('project-select').value;
    phase = 'import-csv'; tab('resources');
    $('resource-name').value = 'first-use.csv'; $('format').value = 'csv';
    $('content').value = 'item,amount,quantity\nA,10,7\nB,20,8\n';
    submit('resource-form'); await wait(() => $('app-resource').options.length === 1);
    check($('app-resource').selectedOptions[0].textContent.includes('first-use.csv'), 'CSV text saved through resource UI');
    phase = 'private-draft'; tab('apps');
    $('app-name').value = '首次体验 私有求和'; $('app-goal').value = '汇总所选数值列';
    submit('app-form'); await wait(() => !$('app-preview-form').hidden);
    const app = w.eval('activeApp');
    const manifest = JSON.parse($('app-manifest').textContent);
    check(manifest.candidate.manifest.app_id === app, 'draft has real server candidate identity');
    phase = 'preview'; $('app-column').value = 'amount'; submit('app-preview-form');
    await wait(() => $('app-output').textContent.includes('30'));
    check($('app-output').textContent.includes('SUCCEEDED'), 'new CSV preview succeeded');
    const preview = await (await fetch(base + '/api/apps/' + app,
      {headers: {Authorization: 'Bearer synthetic-first-use-A'}})).json();
    check(preview.history[0].output.sum === '30' && preview.history[0].output.count === 2,
      'preview receipt independently read back from the real API');
    phase = 'confirm-version'; $('internal-prepare').click();
    await wait(() => !!w.eval('engineering.approval'));
    $('internal-approval-ack').checked = true; $('internal-approval-ack').dispatchEvent(new w.Event('change'));
    $('internal-commit').click(); await wait(() => $('internal-releases').querySelector('button'));
    $('internal-releases').querySelector('button').click();
    await wait(() => !$('internal-run-form').hidden);
    const instance = w.eval('engineering.instance.id');
    const release = w.eval('engineering.instance.release_id');
    const results = [];
    for (const [column, expected, version] of [['amount', '30', 1], ['quantity', '15', 2]]) {
      phase = 'new-app-run-' + column;
      const previousRun = w.eval('engineering.run?.id');
      $('internal-column').value = column; submit('internal-run-form');
      await wait(() => !!w.eval('engineering.run') && w.eval('engineering.run.id') !== previousRun);
      const run = w.eval('engineering.run.id');
      await wait(() => !w.eval('engineering.busy'));
      await wait(() => w.eval('engineering.run?.status') === 'SUCCEEDED');
      // Refresh uses the product GET path; real Worker runs independently.
      $('internal-refresh').click();
      await wait(() => $('internal-data').textContent.includes('v' + version));
      await wait(() => !w.eval('engineering.busy'));
      const response = await fetch(base + `/api/internal/instances/${instance}/runs/${run}`,
        {headers: {Authorization: 'Bearer synthetic-first-use-A'}});
      const result = await response.json();
      check(response.status === 200 && result.status === 'SUCCEEDED', column + ' normal persistent AppRun succeeds');
      check(result.result.sum === expected && result.result_version === version, column + ' independent result version matches arithmetic');
      results.push({column, run_id: run, sum: result.result.sum, result_version: result.result_version});
    }
    check(results[0].run_id !== results[1].run_id, 'new parameters create a new run');
    phase = 'cold-history'; const beforeCold = writes.length, beforeColdRequests = requests.length;
    await connect(); tab('apps');
    await wait(() => $('use-list').querySelector('button'));
    $('use-list').querySelector('button').click();
    await wait(() => !$('use-form').hidden && $('use-history').textContent.includes('v2'));
    check($('use-history').textContent.includes('v1') && $('use-history').textContent.includes('v2'), 'fresh page reads both persistent results');
    check(writes.length === beforeCold, 'cold read sends zero POST');
    const coldRequests = requests.slice(beforeColdRequests);
    check(coldRequests.length > 0 && coldRequests.every(r => ['GET', 'HEAD'].includes(r.method)),
      'every cold page API request is read-only GET or HEAD');
    check($('use-info').textContent.includes('未发布内部版本'), 'internal version is not formal publication');
    fs.writeFileSync(output, JSON.stringify({status: 'PASS', driver: 'real loopback HTTP and product JS in JSDOM',
      browser: 'NOT_RUN', visual: 'NOT_RUN', project_id: project, app_id: app,
      release_id: release, instance_id: instance, results, checks,
      post_paths: writes, cold_requests: coldRequests, cold_posts: writes.length - beforeCold}, null, 2) + '\n');
  } catch (error) {
    fs.writeFileSync(output, JSON.stringify({status: 'FAIL', phase, error_type: error.name,
      browser: 'NOT_RUN', visual: 'NOT_RUN', checks}, null, 2) + '\n');
    process.exitCode = 1;
  } finally {await closePage();}
})();
