"use strict";
// Targeted actual-loopback HTTP/JSDOM driver. This is not native-browser evidence.
// Usage: NODE_PATH=scripts/engineering-ci/node_modules node <this-file> <tmpdir>
// Fixture: normal single P-A generation and one successful business Worker.
// Project history opens the exact existing result. This driver invokes no Worker.
// The only controlled boundary delays delivery of a complete real HTTP response.
const fs = require("node:fs");
const path = require("node:path");
const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const {JSDOM} = require("jsdom");

const root = process.argv[2];
const info = JSON.parse(fs.readFileSync(path.join(root, "info.json"), "utf8"));
const base = new URL(info.base);
assert(["127.0.0.1", "localhost", "[::1]"].includes(base.hostname), "owned loopback only");
const browser = require(path.join(process.cwd(), "tests/durable_browser.cjs"))(
  path.join(root, "browser-storage.json"),
);
const checks = [], actions = [], requests = [], assets = [], errors = [], lifecycle = [];
const instancePath = `/api/internal/instances/${info.instance}`;
const runDetailPath = `${instancePath}/runs/${info.run}`;
const artifactPath = `/api/internal/app-run-jobs/${info.run}/spec-artifact`;
let dom, window, $, page, openedScope, selectedRun, artifactProof, otherScope, syntheticCompatibility;
let holdNextInstance = false, heldProof = null, resumeHeld = null;
const downloads = [];
const copy = value => JSON.parse(JSON.stringify(value));
const sha = value => crypto.createHash("sha256").update(value).digest("hex");
function canonical(value) {
  if (Array.isArray(value)) return "[" + value.map(canonical).join(",") + "]";
  if (value && typeof value === "object") return "{" + Object.keys(value).sort()
    .map(key => JSON.stringify(key) + ":" + canonical(value[key])).join(",") + "}";
  return JSON.stringify(value);
}
const hash = value => sha(canonical(value));
const check = (condition, label) => { assert(condition, label); checks.push(label); };
const postRows = (start = 0) => requests.slice(start).filter(row => row.method === "POST");
const evaluate = source => copy(window.eval(source));
function progress(event, fields = {}) {
  fs.appendFileSync(path.join(root, "page-progress.jsonl"),
    JSON.stringify({time: new Date().toISOString(), event, ...fields}) + "\n");
}

async function bounded(promise, label, budget = 180000) {
  let timer;
  try {
    return await Promise.race([promise, new Promise((_, reject) => {
      timer = setTimeout(() => reject(Error("bounded driver await: " + label)), budget);
    })]);
  } finally { clearTimeout(timer); }
}
async function wait(test, label, budget = 60000) {
  const end = Date.now() + budget;
  while (Date.now() < end) {
    if (test()) return;
    await new Promise(resolve => setTimeout(resolve, 10));
  }
  throw Error("bounded driver readiness timeout: " + label);
}
function trackHandlers(current) {
  for (const name of ["onclick", "onchange", "oninput", "onsubmit"]) {
    const descriptor = Object.getOwnPropertyDescriptor(window.HTMLElement.prototype, name);
    assert(descriptor?.set, "JSDOM DOM handler setter: " + name);
    Object.defineProperty(window.HTMLElement.prototype, name, {
      ...descriptor,
      set(handler) {
        descriptor.set.call(this, typeof handler !== "function" ? handler : function (...args) {
          const result = handler.apply(this, args);
          if (result && typeof result.then === "function") {
            const action = Promise.resolve(result);
            current.actions.add(action);
            action.then(() => current.actions.delete(action), error => {
              errors.push({kind: "handler", error: error.stack || String(error)});
              current.actions.delete(action);
            });
          }
          return result;
        });
      },
    });
  }
  window.addEventListener("error", event => errors.push({kind: "window", error: event.error?.stack || event.message}));
  window.addEventListener("unhandledrejection", event => errors.push({kind: "rejection", error: String(event.reason)}));
}
process.on("unhandledRejection", error => errors.push({kind: "node-rejection", error: error?.stack || String(error)}));
async function idlePage() {
  await wait(() => page.requests === 0 && page.actions.size === 0, "owned handlers and HTTP drained");
  await new Promise(resolve => setImmediate(resolve));
  assert.equal(page.requests, 0);
  assert.equal(page.actions.size, 0);
  assert.deepEqual(errors, [], "no unhandled page errors");
}
function visible(node) {
  if (!node?.isConnected) return false;
  for (let parent = node; parent; parent = parent.parentElement) {
    const style = window.getComputedStyle(parent);
    if (parent.hidden || parent.hasAttribute("inert") || parent.getAttribute("aria-hidden") === "true" ||
        style.display === "none" || ["hidden", "collapse"].includes(style.visibility)) return false;
    if (parent.tagName === "DETAILS" && !parent.open && !parent.querySelector("summary")?.contains(node)) return false;
  }
  return true;
}
async function gesture(nodeOrId, kind, perform, {drain = true} = {}) {
  const node = typeof nodeOrId === "string" ? $(nodeOrId) : nodeOrId;
  assert(visible(node), "visible control " + (node?.id || node?.textContent));
  assert(!node.matches(":disabled"), "enabled control " + (node.id || node.textContent));
  node.focus();
  const action = {kind, id: node.id || null, text: node.textContent, visible: true, enabled: true,
    workspace: window.document.querySelector("#workspace-nav [aria-current=true]")?.dataset.tab};
  actions.push(action);
  const start = Date.now();
  progress("action_start", {index: actions.length - 1, kind, id: action.id});
  const previous = new Set(page.actions);
  try {
    perform(node);
    // During the one held-delivery boundary, await only this user's new handler.
    // Waiting for every old handler here would deadlock the project-change gesture.
    const own = [...page.actions].filter(action => !previous.has(action));
    await bounded(Promise.all(own), "gesture " + kind + " " + (node.id || node.textContent));
    if (drain) await idlePage();
  }
  finally {
    action.elapsed_ms = Date.now() - start;
    progress("action_end", {index: actions.indexOf(action), kind, id: action.id, elapsed_ms: action.elapsed_ms});
  }
}
const click = (id, options) => gesture(id, "CLICK", node => node.click(), options);
const doubleClick = (id, options) => gesture(id, "DOUBLE_CLICK", node => { node.click(); node.click(); }, options);
const edit = (id, value, options) => gesture(id, "SELECT", node => {
  node.value = value;
  node.dispatchEvent(new window.Event("input", {bubbles: true}));
  node.dispatchEvent(new window.Event("change", {bubbles: true}));
}, options);
const navigate = tab => click(window.document.querySelector(`#workspace-nav [data-tab="${tab}"]`));

async function loadAsset(pathname) {
  const response = await fetch(new URL(pathname, base));
  const bytes = Buffer.from(await response.arrayBuffer());
  assert.equal(response.status, 200, "actual static asset " + pathname);
  assets.push({boot: 1, path: pathname, status: response.status, bytes: bytes.length, sha256: sha(bytes)});
  return bytes.toString("utf8");
}
async function setup() {
  const html = await loadAsset("/");
  dom = new JSDOM(html, {url: base.href, runScripts: "dangerously", pretendToBeVisual: true});
  window = dom.window;
  $ = id => window.document.getElementById(id);
  page = {requests: 0, actions: new Set()};
  trackHandlers(page);
  browser.install(window);
  window.TextEncoder = TextEncoder;
  window.structuredClone = structuredClone;
  Object.defineProperty(window, "crypto", {value: crypto.webcrypto});
  window.setInterval = () => 0; // Explicit manual reads only; no scheduler acceptance claim.
  window.URL.createObjectURL = blob => {
    downloads.push({kind: "BLOB_URL_ATTEMPT", bytes: blob.size});
    return "blob:controlled-download-observer/" + downloads.length;
  };
  window.URL.revokeObjectURL = () => {};
  window.document.addEventListener("click", event => {
    const anchor = event.target.closest?.("a[download]");
    if (anchor) { downloads.push({kind: "DOWNLOAD_ANCHOR_ATTEMPT", name: anchor.download}); event.preventDefault(); }
  }, true);
  window.fetch = async (url, options = {}) => {
    const target = new URL(url, base);
    assert.equal(target.origin, base.origin, "all product requests stay on owned loopback");
    const row = {method: options.method || "GET", path: target.pathname + target.search,
      headers: Object.fromEntries(new Headers(options.headers || {}).entries()),
      body_text: options.body ?? null, body: options.body ? JSON.parse(options.body) : null};
    requests.push(row);
    page.requests++;
    const start = Date.now();
    progress("http_start", {index: requests.length - 1, method: row.method, path: row.path});
    try {
      const response = await fetch(target, options);
      const raw = Buffer.from(await response.arrayBuffer());
      row.status = response.status;
      row.elapsed_ms = Date.now() - start;
      row.response_text = raw.toString("utf8");
      row.response_utf8_sha256 = sha(raw);
      row.body_sha256 = row.body_text === null ? null : sha(row.body_text);
      try { row.response = JSON.parse(row.response_text); } catch { row.response = null; }
      let gate = null;
      if (holdNextInstance && row.method === "GET" && row.path === instancePath) {
        holdNextInstance = false;
        assert.equal(row.status, 200, "hold an actual successful instance response only");
        heldProof = {kind: "CONTROLLED_DELIVERY_OF_COMPLETE_ACTUAL_HTTP_RESPONSE", path: row.path,
          request_index: requests.indexOf(row), status: row.status,
          response_utf8_sha256: row.response_utf8_sha256, server_received: true,
          response_complete_before_hold: true, released: false};
        row.delivery_control = heldProof.kind;
        gate = new Promise(resolve => { resumeHeld = resolve; });
      }
      fs.appendFileSync(path.join(root, "http-responses.jsonl"), JSON.stringify(row) + "\n");
      progress("http_end", {index: requests.indexOf(row), method: row.method, path: row.path,
        status: row.status, sha256: row.response_utf8_sha256, elapsed_ms: row.elapsed_ms});
      if (gate) {
        progress("hold_actual_instance_response", heldProof);
        await gate;
        heldProof.released = true;
        row.delivery_released = true;
        progress("release_actual_instance_response", heldProof);
      }
      return new Response([204, 205, 304].includes(response.status) ? null : raw,
        {status: response.status, headers: response.headers});
    } catch (error) {
      row.transport_error = error.stack || String(error);
      row.elapsed_ms = Date.now() - start;
      fs.appendFileSync(path.join(root, "http-responses.jsonl"), JSON.stringify(row) + "\n");
      throw error;
    } finally { page.requests--; }
  };
  const style = window.document.createElement("style");
  style.textContent = await loadAsset("/app.css");
  window.document.head.append(style);
  const scripts = [...window.document.querySelectorAll("script[src]")];
  for (const source of scripts) {
    const script = window.document.createElement("script");
    script.textContent = await loadAsset(source.getAttribute("src"));
    window.document.body.append(script);
  }
  check(assets.length === 27 && scripts.length === 25, "actual index plus CSS and all 25 production scripts loaded");
  await edit("token", "synthetic-test-A");
  await click("connect");
  await wait(() => $("login").hidden && $("project-select").value === info.project, "exact synthetic fixture account/project connected");
  await idlePage();
}

function workspace() {
  return window.document.querySelector("#workspace-nav [aria-current=true]")?.dataset.tab;
}
function scope() {
  return {project: $("project-select").value, workspace: workspace(),
    ...evaluate(`({active_app:activeApp,active_run:activeRun,
      engineering:engineering ? {app:engineering.app,instance:engineering.instance?.id||null,
        run:engineering.run?.id||null,app_run:engineering.run?.app_run_id||null} : null,
      owner:ownerView ? {instance:ownerView.iid,run:ownerView.rid||null} : null})`),
    internal_visible: visible($("internal-panel")),
    internal_data_text: $("internal-data").textContent, result_text: $("result").textContent};
}
async function selectProjectRun() {
  assert.equal(workspace(), "projects", "project history is visible");
  const rows = [...$("runs").children].filter(row => row.textContent.includes(info.run.slice(0, 16)));
  check(rows.length === 1, "actual project history has one visible button for the fixture Run prefix");
  await click(rows[0].querySelector("button"));
  const reply = requests.filter(row => row.method === "GET" && row.path === `/api/runs/${info.run}`).at(-1);
  check(reply?.status === 200 && reply.response.id === info.run && reply.response.namespace === "INTERNAL_APPRUN" &&
    reply.response.instance_id === info.instance && reply.response.app_run_id === info.app_run &&
    reply.response.release_id === info.release && reply.response.status === "SUCCEEDED",
  "visible history selection reads the exact existing successful internal Run and its identity");
  selectedRun = copy(reply.response);
  const text = $("result").textContent;
  check(!text.includes("undefined") && !/0\s*模型请求/.test(text),
    "project summary has no undefined values or unverified zero-model claim");
  check(visible($("internal-task-open-result")) && !$("internal-task-open-result").disabled,
    "project Run summary offers the explicit original-result navigation button");
  assert.equal(evaluate("activeRun"), info.run);
}
function verifyOpenedScope() {
  const current = scope(), detail = JSON.parse($("internal-run-detail").textContent);
  check(current.workspace === "apps" && current.project === info.project && current.active_app === info.app &&
    current.engineering.app === info.app && current.engineering.instance === info.instance &&
    current.engineering.run === info.run && current.engineering.app_run === info.app_run &&
    detail.id === info.run && detail.instance_id === info.instance && detail.app_run_id === info.app_run &&
    detail.release_id === info.release && detail.status === "SUCCEEDED",
  "explicit result navigation selects the exact app, instance, machine Run, AppRun and Release");
  const owner = evaluate("ownerView.state"), contract = owner.current;
  check(current.owner.instance === info.instance && current.owner.run === info.run && $("owner-run").value === info.run &&
    owner.content_access === true && owner.owner_acceptance === "PENDING" && owner.sequence === 0 &&
    owner.history.length === 0 && !owner.record && contract.instance_id === info.instance &&
    contract.run_id === info.run && contract.app_run_id === info.app_run && contract.release_id === info.release,
  "owner entry and machine detail share this Run with independent PENDING state and no declaration");
  const typed = evaluate("engineering.instance.data");
  check(typed.length === 1 && typed[0].version === 1 && typed[0].run_id === info.app_run &&
    typed[0].release_id === info.release && contract.result_version === 1,
  "existing typed result version1 belongs to the same original AppRun and Release");
  assert.deepEqual(contract.output, typed[0].data.result);
  const articles = [...$("internal-data").querySelectorAll(".spec-result")];
  check(articles.length === 1 && visible(articles[0]) &&
    articles[0].querySelector("h3").textContent === "规范成果 v1",
  "existing same-Run specification result is visible in the application's result collection");
  openedScope = {...current, result_version: 1, owner_sequence: owner.sequence,
    owner_acceptance: owner.owner_acceptance, output_fingerprint: hash(contract.output)};
  return {article: articles[0], typed: typed[0]};
}
async function readSavedResult(article, typed) {
  const start = requests.length;
  await click(article.querySelector('[data-spec-action="view"]'));
  const reads = requests.slice(start);
  check(reads.length === 1 && reads[0].method === "GET" && reads[0].path === artifactPath && reads[0].status === 200,
    "explicit result view reads one real authorized saved-artifact response without a download");
  const row = reads[0], saved = row.response, output = typed.data.result;
  check(saved.namespace === "spec-saved-artifact.v1" && saved.project_id === info.project && saved.app_id === info.app &&
    saved.instance_id === info.instance && saved.run_id === info.run && saved.app_run_id === info.app_run &&
    saved.release_id === info.release && saved.result_version === 1 && saved.output_fingerprint === hash(output),
  "actual artifact response is independently bound to this Run, version, Release and output SHA");
  check(saved.resource.content === canonical(output.checklist) && saved.resource.hash === sha(saved.resource.content) &&
    saved.resource.resource_id === output.resource_id && saved.resource.hash === output.hash &&
    saved.citation_status === "PASS" && saved.semantic_status === "UNKNOWN" && saved.owner_acceptance === "PENDING" &&
    saved.formal_publication_enabled === false && saved.new_model_requests === 0 && saved.project_writes === 0,
  "saved JSON bytes and hash match the original typed checklist without semantic acceptance or writes");
  check(article.textContent.includes(output.checklist.source_content) &&
    article.textContent.includes("已核对成果 v1") && !article.textContent.includes("undefined"),
  "same-version checklist view renders its complete original source after fresh authorization");
  assert.deepEqual(downloads, [], "view performs no Blob or download attempt");
  artifactProof = {request_index: requests.indexOf(row), path: row.path,
    response_utf8_sha256: row.response_utf8_sha256, content_utf8_sha256: sha(saved.resource.content),
    output_fingerprint: saved.output_fingerprint, resource_id: saved.resource.resource_id,
    run_id: saved.run_id, app_run_id: saved.app_run_id, instance_id: saved.instance_id,
    release_id: saved.release_id, result_version: saved.result_version};
  verifyOpenedScope();
}

async function delayedInstanceRead() {
  await navigate("projects");
  await selectProjectRun();
  holdNextInstance = true;
  const first = requests.length;
  // This click remains owned and pending; no forced lock release or fake response.
  const pendingOpen = click("internal-task-open-result", {drain: false});
  await wait(() => heldProof !== null && resumeHeld !== null, "complete real instance GET held before client delivery");
  check(heldProof.status === 200 && heldProof.server_received && heldProof.response_complete_before_hold &&
    heldProof.path === instancePath, "only delivery of the complete real HTTP200 instance response is controlled");
  check([...$("project-select").options].some(option => option.value === info.other_project),
    "another authorized fixture project is available through the visible project selector");
  await edit("project-select", info.other_project, {drain: false});
  await wait(() => page.requests === 1 && page.actions.size === 1,
    "new project refresh is complete while only the old owned read remains held");
  otherScope = scope();
  check(otherScope.project === info.other_project && otherScope.workspace === "projects" &&
    otherScope.active_app === null && otherScope.active_run === null && otherScope.engineering === null &&
    otherScope.owner === null && !otherScope.internal_visible && !otherScope.internal_data_text &&
    !otherScope.result_text.includes(info.run),
  "explicit project change clears the old app, instance, Run, owner content and application view");
  const afterProject = requests.length;
  progress("other_project_scope_before_release", otherScope);
  heldProof.scope_before_release = copy(otherScope);
  resumeHeld();
  resumeHeld = null;
  await pendingOpen;
  await idlePage();
  assert.deepEqual(scope(), otherScope, "released old response cannot repaint or change the new project scope");
  check(requests.length === afterProject && postRows(first).length === 0,
    "late source-instance callback starts no follow-up request, workspace navigation or POST");
  heldProof.scope_after_release = scope();
}

function syntheticRendererCompatibility() {
  const start = requests.length;
  // Explicitly authorized isolated renderer check, separate from actual HTTP evidence.
  const text = window.eval(`(() => {
    $("result").replaceChildren();
    renderInternalTaskResult({namespace:"INTERNAL_APPRUN",status:"SUCCEEDED",result_version:1,
      result:{column:"金额",sum:"9007199254740993.01",count:2}},()=>true);
    return $("result").textContent;
  })()`);
  check(text.includes("金额 合计 9007199254740993.01，共 2 条记录。") &&
    !text.includes("undefined") && !/0\s*模型请求/.test(text) && !$("internal-task-open-result"),
  "synthetic renderer preserves exact decimal-string sum and creates no navigation button without IDs");
  assert.equal(requests.length, start, "isolated renderer check has no HTTP effects");
  syntheticCompatibility = {classification: "CONTROLLED_ISOLATED_RENDERER_NOT_ACTUAL_BACKEND",
    input: {column: "金额", sum: "9007199254740993.01", count: 2}, rendered_text: text,
    navigation_button_present: false, http_requests: 0};
}

async function run() {
  await setup();
  await selectProjectRun();
  check(requests.every(row => row.method === "GET"), "project-history discovery is read-only");
  const start = requests.length;
  await doubleClick("internal-task-open-result");
  const reads = requests.slice(start);
  check(reads.filter(row => row.method === "GET" && row.path === runDetailPath).length === 1 &&
    reads.filter(row => row.method === "GET" && row.path === instancePath).length === 2,
  "double click opens one result navigation: one Run-detail read plus instance precheck and controller read");
  const {article, typed} = verifyOpenedScope();
  await readSavedResult(article, typed);
  await delayedInstanceRead();
  check(requests.every(row => row.method === "GET") && downloads.length === 0,
    "all actual project/result navigation and late-delivery checks are GET-only with no downloads");
  syntheticRendererCompatibility();
}

(async () => {
  let status = "FAIL", error = null;
  progress("driver_start", {classification: "ACTUAL_HTTP_JSDOM_PROJECT_RUN_RESULT_NAVIGATION"});
  try { await run(); status = "PASS"; }
  catch (failure) { error = failure.stack || String(failure); process.stderr.write(error + "\n"); }
  finally {
    // Release only the fixture's known response-delivery gate before owned drain.
    if (resumeHeld) { resumeHeld(); resumeHeld = null; }
    if (dom) {
      try { await idlePage(); lifecycle.push({owned_http: page.requests, owned_actions: page.actions.size}); }
      catch (failure) {
        status = "FAIL";
        error ||= failure.stack || String(failure);
        process.stderr.write((failure.stack || String(failure)) + "\n");
      }
      window.close();
    }
    if (errors.length) {
      status = "FAIL";
      if (!error) { error = JSON.stringify(errors); process.stderr.write(error + "\n"); }
    }
    progress("driver_finally", {status, requests: requests.length, errors: errors.length});
    fs.writeFileSync(path.join(root, "results.json"), JSON.stringify({status, error,
      classification: "ACTUAL_HTTP_JSDOM_PROJECT_RUN_RESULT_NAVIGATION", checks, actions, requests,
      static_resource_loads: assets, boots: dom ? 1 : 0, page_errors: errors, lifecycle, downloads,
      selected_run: selectedRun, opened_scope: openedScope, artifact_proof: artifactProof,
      delayed_actual_instance_response: heldProof, other_project_scope: otherScope,
      synthetic_renderer_compatibility: syntheticCompatibility,
      browser_platform: "JSDOM_WITH_CONTROLLED_STORAGE_WEB_LOCKS_NOT_NATIVE",
      delayed_response_scope: "ONE_COMPLETE_ACTUAL_INSTANCE_GET_RESPONSE_DELIVERY_ONLY",
      fixture_scope: "BACKEND_NORMAL_SINGLE_PA_GENERATION_AND_SUCCESSFUL_WORKER_NOT_PAGE_CREATED",
      real_model: "NOT_RUN", page_worker: "NOT_RUN", interval_scheduler: "DISABLED_MANUAL_READS_ONLY",
      automatic_posts: "NONE", db_scope: "PARENT_VERIFIES_BEFORE_AFTER_ALL_TABLES_READONLY",
    }, null, 2));
    process.stdout.write(JSON.stringify({status, checks: checks.length}) + "\n");
    process.exitCode = status === "PASS" ? 0 : 1;
  }
})();

