"use strict";
// Targeted actual-loopback HTTP/JSDOM driver. This is not native-browser evidence.
// Usage: NODE_PATH=scripts/engineering-ci/node_modules node <this-file> <tmpdir>
// Fixture: approved LIVE_BLOCKED preparation and synthetic UNKNOWN budget ledger.
// No provider, model or Worker is invoked by this driver or its fixture.
// The only controlled boundary delays delivery of a complete real budget response.
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
const trialPath = key => `/api/projects/${info.project}/natural-trials/${encodeURIComponent(key)}`;
const budgetPath = `${trialPath(info.trial)}/approvals/${encodeURIComponent(info.approval_key)}/budget`;
let dom, window, $, page, emptyPreparation, mainPreparation, budgetProof, emptyFailure, heldProof, otherScope;
let originalBudgetResponse;
const syntheticValidatorChecks = [];
let holdNextBudget = false, resumeHeld = null;
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
      if (holdNextBudget && row.method === "GET" && row.path === budgetPath) {
        holdNextBudget = false;
        assert.equal(row.status, 200, "hold an actual successful budget response only");
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
        progress("hold_actual_budget_response", heldProof);
        await gate;
        heldProof.released = true;
        row.delivery_released = true;
        progress("release_actual_budget_response", heldProof);
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

function entryState() {
  return evaluate(`(() => {
    const entry=trialEntries.get(JSON.stringify([token,$("project-select").value]));
    return entry ? {key:entry.key,state:entry.state,operation:entry.operation,
      receipt_status:entry.receipt?.status||null,review_token:entry.receipt?.review_token||null,
      approved:entry.receipt?.approved??null,has_contract:!!entry.receipt?.contract} : null;
  })()`);
}
function budgetScope() {
  return {project: $("project-select").value, key_input: $("trial-original-key").value,
    workspace: window.document.querySelector("#workspace-nav [aria-current=true]")?.dataset.tab,
    entry: entryState(), trial_scope: $("trial-scope").textContent,
    budget_status: $("trial-budget-status").textContent,
    budget_output: $("trial-budget-output").innerHTML,
    budget_read_disabled: $("trial-budget-read").disabled};
}
function approvalKey(receipt) { return receipt.approval.approval.request.request_key; }
const budgets = (start = 0) => requests.slice(start).filter(row => /\/approvals\/[^/]+\/budget$/.test(row.path));
async function recover(key, {editKey = true, drain = true} = {}) {
  const start = requests.length;
  if (editKey) {
    await edit("trial-original-key", key, {drain});
    check(requests.length === start,
      "typing an original trial key does not automatically recover, read accounting or submit anything");
  }
  await click("trial-recover", {drain});
  const reads = requests.slice(start);
  const row = reads.find(item => item.method === "GET" && item.path === trialPath(key) + "/preparation");
  check(row?.status === 200 && row.response.status === "PREPARED_LIVE_BLOCKED" && row.response.path === "P-A" &&
    row.response.contract.trial_key === key && row.response.contract.project_id === info.project &&
    row.response.approved === true && row.response.live_allowed === false && !row.response.revoked &&
    row.response.actual_model_requests === 0 && row.response.new_runs === 0 && row.response.new_slots === 0,
  "visible original-key recovery reads the complete approved preparation with LIVE still blocked");
  check(row.response.review_token === hash(row.response.contract) &&
    row.response.approval.contract_fingerprint === row.response.review_token &&
    row.response.approval.approval.contract_fingerprint === row.response.review_token,
  "actual preparation and nested consent receipt retain the exact original contract fingerprint");
  check(budgets(start).length === 0 && !$("trial-budget-read").disabled && entryState().state === "known",
    "full approved recovery enables the separate read-only budget button without an automatic budget GET");
  return copy(row.response);
}

async function emptyLedgerBoundary() {
  emptyPreparation = await recover(info.empty_trial);
  const path = `${trialPath(info.empty_trial)}/approvals/${encodeURIComponent(approvalKey(emptyPreparation))}/budget`;
  const start = requests.length;
  await click("trial-budget-read");
  const reads = budgets(start);
  check(reads.length === 1 && reads[0].method === "GET" && reads[0].path === path &&
    reads[0].status === 409 && reads[0].response.error.code === "VERSION_CONFLICT",
  "approved preparation without a ledger returns the actual budget VERSION_CONFLICT instead of an invented zero balance");
  check(!$("trial-budget-output").textContent && !$("trial-scope").textContent &&
    $("trial-budget-status").textContent.includes("不能据此认定零用量") &&
    entryState().state === "unknown" && !entryState().has_contract && $("trial-budget-read").disabled,
  "failed budget read clears private scope and accounting while retaining the original UNKNOWN key and explicit nonzero-warning");
  emptyFailure = {request_index: requests.indexOf(reads[0]), path,
    status: reads[0].status, response_utf8_sha256: reads[0].response_utf8_sha256,
    visible_status: $("trial-budget-status").textContent, scope_after_failure: budgetScope()};
  // The UNKNOWN key guard is respected: recover this same original key before switching.
  await recover(info.empty_trial, {editKey: false});
  check(!$("trial-budget-output").textContent, "recovering the original empty-ledger key does not invent usage data");
}
function verifyActualBudget(row) {
  const value = row.response, projection = value.budget_projection, ledger = value.ledger;
  originalBudgetResponse = copy(value);
  check(value.scope.project_id === info.project && value.scope.trial_key === info.trial &&
    value.scope.approval_key === info.approval_key && value.scope.contract_fingerprint === info.contract_fingerprint &&
    value.scope.principal_id === mainPreparation.contract.principal_id &&
    value.scope.runtime_id === mainPreparation.contract.runtime_id,
  "actual budget GET is scoped to this principal, project, original trial, approval and full contract fingerprint");
  check(value.usage_status === "UNKNOWN" && value.total_tokens === null && value.status === "RECONCILING" &&
    value.dispatch_authorized === false && value.live_admission === "NOT_VERIFIED" && ledger.halted === true &&
    ledger.slots.length === 1 && ledger.stage_runs.generate === info.run &&
    ledger.slots[0].reservation.stage === "generate" && ledger.slots[0].reservation.run_id === info.run &&
    ledger.slots[0].settlement.total_tokens === null,
  "synthetic UNKNOWN settlement remains halted, unverified and unrelated to any model-dispatch permission");
  check(projection.held_requests === info.held_requests && projection.request_limit === 7 &&
    projection.held_token_envelope === info.held_envelope && projection.token_envelope_limit === 192000 &&
    projection.unresolved_usage_requests === 1 && value.reserved_requests === info.held_requests &&
    value.reserved_envelope === info.held_envelope,
  "exact nonrefundable held request and conservative token envelope are read from the existing ledger");
  check(projection.money.actual_paid === null && projection.money.currency === null &&
    projection.money.status === "UNKNOWN" && projection.money.fee_verification === "NOT_LIVE_VERIFIED" &&
    projection.money.live_allowed === false && projection.money.paid_cap === 0,
  "paid cap zero is separate from actual cost UNKNOWN and provides no LIVE or free-quota proof");
  const rendered = $("trial-budget-output").textContent;
  for (const text of [`已保留 ${info.held_requests} / 7 槽`,
    `保守预留 ${info.held_envelope} / 192000`, "完整 total_tokens：未知",
    "已返回 total_tokens 分量：0", "实际费用：UNKNOWN（币种未知）",
    "账本状态 RECONCILING · 已停止 true · 未决用量 1"])
    check(rendered.includes(text), "budget display preserves exact meaning: " + text);
  check(!/实际费用\s*[:：]\s*0(?:\D|$)/.test(rendered) &&
    /未核实|NOT_LIVE_VERIFIED/.test(rendered) && !rendered.includes("undefined"),
  "rendered accounting never substitutes zero actual cost or undefined usage for unknown values");
  const rows = [...$("trial-budget-output").querySelectorAll("tbody tr[data-trial-budget-stage]")];
  assert.deepEqual(rows.map(row => row.dataset.trialBudgetStage), ["generate", "source", "cold"]);
  for (const row of rows) {
    const stage = row.dataset.trialBudgetStage, actual = projection.stages[stage];
    check(actual.request_limit === (stage === "generate" ? 3 : 2) &&
      actual.held_requests === (stage === "generate" ? info.held_requests : 0) &&
      actual.held_token_envelope === (stage === "generate" ? info.held_envelope : 0) &&
      actual.run_id === (stage === "generate" ? info.run : null),
    "actual ledger stage binds only its own held request and original Run: " + stage);
    check(new RegExp(`${actual.held_requests}\\s*/\\s*${actual.request_limit}`).test(row.textContent) &&
      new RegExp(`${actual.held_token_envelope}\\s*/\\s*64000`).test(row.textContent) &&
      (stage === "generate" ? row.textContent.includes(info.run) : !/run_[a-f0-9]{32}/.test(row.textContent)),
    "visible stage row preserves exact held values and Run presence: " + stage);
  }
  budgetProof = {request_index: requests.indexOf(row), path: row.path,
    response_utf8_sha256: row.response_utf8_sha256, scope: value.scope,
    projection: copy(projection), usage_status: value.usage_status, total_tokens: value.total_tokens,
    halted: ledger.halted, rendered_text: rendered,
    stage_rows: rows.map(row => ({stage: row.dataset.trialBudgetStage, text: row.textContent}))};
}
async function readMainBudget() {
  mainPreparation = await recover(info.trial);
  check(mainPreparation.review_token === info.contract_fingerprint && approvalKey(mainPreparation) === info.approval_key,
    "the main recovered preparation matches the Python fixture's exact approval identity");
  const start = requests.length;
  await doubleClick("trial-budget-read");
  const reads = budgets(start);
  check(reads.length === 1 && reads[0].method === "GET" && reads[0].path === budgetPath && reads[0].status === 200,
    "double click on the separate read button makes exactly one real successful budget GET");
  verifyActualBudget(reads[0]);
}
async function delayedBudgetRead() {
  holdNextBudget = true;
  const pendingRead = click("trial-budget-read", {drain: false});
  await wait(() => heldProof && resumeHeld, "complete actual budget GET200 held before client delivery");
  check(heldProof.status === 200 && heldProof.server_received && heldProof.response_complete_before_hold &&
    heldProof.path === budgetPath, "only delivery of a complete actual budget response is controlled");
  await recover(info.empty_trial, {drain: false});
  await wait(() => page.requests === 1 && page.actions.size === 1,
    "new original-key recovery completes with only the old owned budget read still held");
  const switched = budgetScope();
  check(switched.entry.key === info.empty_trial && switched.entry.state === "known" &&
    switched.entry.has_contract && !switched.budget_output && !switched.budget_read_disabled,
  "new full receipt is selected while old budget data stays cleared and the new manual read remains available");
  const start = requests.length;
  heldProof.scope_before_release = copy(switched);
  progress("new_trial_scope_before_release", switched);
  resumeHeld();
  resumeHeld = null;
  await pendingRead;
  await idlePage();
  assert.deepEqual(budgetScope(), switched, "old budget callback cannot paint or change the new original-key scope");
  check(requests.length === start, "releasing the old budget response starts no new request or automatic recovery");
  heldProof.scope_after_release = budgetScope();
}
async function syntheticValidatorBoundaries() {
  const before = {scope: budgetScope(), requests: requests.length, downloads: copy(downloads)};
  const validate = value => window.validateTrialBudget(value, copy(mainPreparation), info.approval_key);
  const record = (name, outcome, error = null) => syntheticValidatorChecks.push({
    classification: "SYNTHETIC_VALIDATOR_ONLY_NOT_HTTP", name, outcome, error,
  });
  // Baseline and mutations are copies of the actual successful HTTP response.
  // Calling this pure validator is separate from the visible actual-page flow.
  await validate(copy(originalBudgetResponse));
  assert.deepEqual(budgetScope(), before.scope, "valid baseline validation does not change the page scope");
  assert.equal(requests.length, before.requests, "valid baseline validation makes no HTTP request");
  assert.deepEqual(downloads, before.downloads, "valid baseline validation makes no download attempt");
  record("original_actual_response_copy", "ACCEPTED");
  const cases = [
    ["projected_generate_run_changed", value => {
      value.budget_projection.stages.generate.run_id = "run_" + "0".repeat(32);
    }],
    ["unknown_slot_relabelled_known_zero", value => {
      value.usage_status = "KNOWN";
      value.total_tokens = 0;
      value.known_total_tokens = 0;
      value.budget_projection.unresolved_usage_requests = 0;
      value.status = "ACCOUNTED";
    }],
    ["unknown_actual_cost_replaced_with_zero", value => {
      value.budget_projection.money.actual_paid = 0;
    }],
  ];
  for (const [name, mutate] of cases) {
    const value = copy(originalBudgetResponse);
    mutate(value);
    let rejection = null;
    try { await validate(value); }
    catch (error) { rejection = error.message || String(error); }
    check(rejection !== null, "isolated synthetic validator rejects: " + name);
    record(name, "REJECTED", rejection);
    assert.deepEqual(budgetScope(), before.scope, "synthetic validation does not change the actual page scope");
    assert.equal(requests.length, before.requests, "synthetic validation makes no HTTP request");
    assert.deepEqual(downloads, before.downloads, "synthetic validation makes no download attempt");
  }
  assert.equal(downloads.length, 0);
}
async function run() {
  await setup();
  check(visible($("trial-panel")) && visible($("trial-budget-read")) && $("trial-budget-read").disabled &&
    !$("trial-budget-output").textContent && budgets().length === 0,
  "normal project connection exposes the manual budget entry without a full receipt, private data or automatic read");
  await emptyLedgerBoundary();
  await readMainBudget();
  await delayedBudgetRead();
  check([...$("project-select").options].some(option => option.value === info.other_project),
    "another authorized project is selectable for one normal content-clear check");
  await edit("project-select", info.other_project);
  otherScope = budgetScope();
  check(otherScope.project === info.other_project && !otherScope.budget_output &&
    !otherScope.trial_scope && otherScope.budget_read_disabled,
  "explicit project change clears protected budget and trial content and requires a new full receipt");
  assert.deepEqual(budgets().map(row => row.status), [409, 200, 200],
    "only the three explicit budget reads occur; recovery and project changes do not poll accounting");
  check(requests.every(row => row.method === "GET") && postRows().length === 0 && downloads.length === 0,
    "all trial recovery and accounting actions are actual GET-only with no consent, dispatch, model, Worker or download action");
  await syntheticValidatorBoundaries();
}

(async () => {
  let status = "FAIL", error = null;
  progress("driver_start", {classification: "ACTUAL_HTTP_JSDOM_NATURAL_TRIAL_BUDGET_VIEW"});
  try { await run(); status = "PASS"; }
  catch (failure) { error = failure.stack || String(failure); process.stderr.write(error + "\n"); }
  finally {
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
      classification: "ACTUAL_HTTP_JSDOM_NATURAL_TRIAL_BUDGET_VIEW", checks, actions, requests,
      static_resource_loads: assets, boots: dom ? 1 : 0, page_errors: errors, lifecycle, downloads,
      empty_preparation: emptyPreparation, main_preparation: mainPreparation,
      empty_budget_failure: emptyFailure, budget_proof: budgetProof,
      synthetic_validator_checks: syntheticValidatorChecks,
      delayed_actual_budget_response: heldProof, other_project_scope: otherScope,
      browser_platform: "JSDOM_WITH_CONTROLLED_STORAGE_WEB_LOCKS_NOT_NATIVE",
      fixture_scope: "SYNTHETIC_LIVE_BLOCKED_PREPARATION_CONSENT_AND_UNKNOWN_LEDGER_NO_MODEL_OR_WORKER",
      delayed_response_scope: "ONE_COMPLETE_ACTUAL_BUDGET_GET_RESPONSE_DELIVERY_ONLY",
      live_authorization: "NOT_VERIFIED_NOT_GRANTED", real_model: "NOT_RUN", worker: "NOT_RUN",
      native_windows: "NOT_RUN", interval_scheduler: "DISABLED_MANUAL_READS_ONLY",
      automatic_posts: "NONE", db_scope: "PARENT_VERIFIES_ALL_TABLES_BEFORE_AFTER_READONLY",
    }, null, 2));
    process.stdout.write(JSON.stringify({status, checks: checks.length}) + "\n");
    process.exitCode = status === "PASS" ? 0 : 1;
  }
})();

