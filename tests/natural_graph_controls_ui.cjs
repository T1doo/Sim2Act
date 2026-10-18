"use strict";
// Targeted actual-loopback HTTP/JSDOM driver. This is not native-browser evidence.
// Usage: NODE_PATH=scripts/engineering-ci/node_modules node <this-file> <tmpdir>
// Fixture: normal parallel P-A generation, one Release and one empty instance;
// no business Worker and no pre-derived graph. This driver never invokes a Worker.
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
const graphBase = `/api/projects/${info.project}/apps/${info.app}/delivery-graph`;
const logicBase = `/api/internal/instances/${info.instance}/logic-patches`;
let dom, window, $, page, originalDraft, originalInstance, originalReleases;
let firstGraph, lockedGraph, unlockedGraph, lockReceipt, unlockReceipt, acceptedPreview;
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
async function gesture(nodeOrId, kind, perform) {
  const node = typeof nodeOrId === "string" ? $(nodeOrId) : nodeOrId;
  assert(visible(node), "visible control " + (node?.id || node?.textContent));
  assert(!node.matches(":disabled"), "enabled control " + (node.id || node.textContent));
  node.focus();
  const action = {kind, id: node.id || null, text: node.textContent, visible: true, enabled: true,
    workspace: window.document.querySelector("#workspace-nav [aria-current=true]")?.dataset.tab};
  actions.push(action);
  const start = Date.now();
  progress("action_start", {index: actions.length - 1, kind, id: action.id});
  try { perform(node); await idlePage(); }
  finally {
    action.elapsed_ms = Date.now() - start;
    progress("action_end", {index: actions.indexOf(action), kind, id: action.id, elapsed_ms: action.elapsed_ms});
  }
}
const click = id => gesture(id, "CLICK", node => node.click());
const doubleClick = id => gesture(id, "DOUBLE_CLICK", node => { node.click(); node.click(); });
const edit = (id, value) => gesture(id, "SELECT", node => {
  node.value = value;
  node.dispatchEvent(new window.Event("input", {bubbles: true}));
  node.dispatchEvent(new window.Event("change", {bubbles: true}));
});
const confirm = id => gesture(id, "EXPLICIT_CONFIRM", node => {
  node.checked = true;
  node.dispatchEvent(new window.Event("change", {bubbles: true}));
});
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
      fs.appendFileSync(path.join(root, "http-responses.jsonl"), JSON.stringify(row) + "\n");
      progress("http_end", {index: requests.indexOf(row), method: row.method, path: row.path,
        status: row.status, sha256: row.response_utf8_sha256, elapsed_ms: row.elapsed_ms});
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

function currentGraph() { return evaluate("deliveryContext.anchor"); }
function nodeOf(graph) {
  const node = graph.graph.nodes.find(item => item.key === info.changed_node_key);
  assert(node, "exact fixture logical node exists");
  return node;
}
function verifyGraph(graph, locked) {
  const {graph_fingerprint, ...body} = graph.graph;
  check(graph.namespace === "delivery-graph-apps.v1" && graph.app_id === info.app &&
    graph.project_id === info.project && graph.candidate_fingerprint === originalDraft.fingerprint &&
    graph.graph_fingerprint === graph_fingerprint && hash(body) === graph_fingerprint,
  "independent actual graph identity and canonical graph SHA verified");
  check(nodeOf(graph).locked === locked && graph.semantic_status === "UNKNOWN" &&
    graph.owner_acceptance === "PENDING" && !graph.patch_executed && !graph.business_write_performed &&
    !graph.publishable && !graph.formal_publication_enabled, "graph records exact lock state without execution or acceptance");
  const rendered = JSON.parse($("delivery-proof").textContent);
  assert.deepEqual(rendered.graph, graph.graph);
  if (firstGraph) assert.deepEqual(graph.graph.nodes.map(node => [node.key, node.id]),
    firstGraph.graph.nodes.map(node => [node.key, node.id]), "derive retains stable original node identities");
}
async function derive(locked, twice = false) {
  const start = requests.length;
  await (twice ? doubleClick("delivery-derive") : click("delivery-derive"));
  const posts = postRows(start);
  check(posts.length === 1 && posts[0].path === graphBase + "/derive" && posts[0].status === 201,
    "explicit derive" + (twice ? " double click" : "") + " saves one real graph receipt");
  const graph = currentGraph(), {cached, ...made} = posts[0].response;
  assert.deepEqual(graph, made, "derived receipt is read back and sealed before display");
  check(requests.slice(start).some(row => row.method === "GET" && row.path === graphBase && row.status === 200),
    "derive reads the persisted exact graph through normal GET");
  verifyGraph(graph, locked);
  return graph;
}
async function readLocks(locked) {
  await click("manual-lock-read");
  const state = evaluate("deliveryContext.manualState");
  const node = nodeOf(currentGraph()), selected = state.nodes.find(item => item.node_id === node.id);
  check(state.namespace === "manual-edit-lock.v1" && !state.needs_derive &&
    state.graph_fingerprint === currentGraph().graph_fingerprint && selected.locked === locked,
  "explicit lock read is current for the exact derived graph and node");
  await edit("manual-lock-node", node.id);
  return {node, selected};
}
async function writeLock(locked, twice) {
  const {node, selected} = await readLocks(!locked);
  await edit("manual-lock-target", String(locked));
  check(!$("manual-lock-confirm").checked && $("manual-lock-submit").disabled,
    "selecting exact lock target cannot write without a separate confirmation");
  await confirm("manual-lock-confirm");
  const start = requests.length;
  await (twice ? doubleClick("manual-lock-submit") : click("manual-lock-submit"));
  const posts = postRows(start);
  check(posts.length === 1 && posts[0].path === graphBase + "/manual-locks" && posts[0].status === 201,
    "explicit " + (locked ? "lock double click" : "unlock") + " writes one real lock receipt");
  const post = posts[0];
  check(post.body.change.node_id === node.id && post.body.locked === locked &&
    post.body.expected_lock_revision === selected.lock_revision && post.body.consent === "CONFIRM_EXACT_PROJECT_EDIT_LOCK",
  "lock request binds displayed node, exact lock revision and explicit consent");
  const get = requests.slice(start).find(row => row.method === "GET" &&
    row.path === graphBase + "/manual-locks/receipt?request_key=" + encodeURIComponent(post.body.request_key));
  const normalize = value => { const {cached, ...rest} = value; return rest; };
  check(get?.status === 200, "original request-key lock receipt is explicitly read after acceptance");
  assert.deepEqual(normalize(get.response), normalize(post.response));
  check(get.response.lock.locked === locked && get.response.lock.revision === selected.lock_revision + 1 &&
    get.response.is_current && get.response.receipt_status === "CURRENT" && !get.response.business_write_performed,
  "persisted lock receipt is exact and changes no business data");
  check(!$("manual-lock-confirm").checked && !$("delivery-proof").textContent,
    "accepted lock clears old graph proof and confirmation until explicit rederive");
  return copy(get.response);
}

async function run() {
  await setup();
  await navigate("apps");
  const catalog = $("use-list").querySelector(`[data-use-family="NATURAL_PA"][data-app-id="${info.app}"]`);
  check(!!catalog && visible(catalog), "unified directory classifies exact saved natural P-A app");
  await click(catalog.querySelector("button"));
  const instance = [...$("internal-instances").children].find(row => row.textContent.includes(info.instance));
  check(!!instance, "user can find the fixture's existing empty instance");
  await click(instance.querySelector("button"));
  originalDraft = evaluate("engineering.draft");
  originalInstance = evaluate("engineering.instance");
  originalReleases = evaluate("engineering.releases");
  check(originalDraft.candidate.namespace === "pa-natural-spec-app.v1" &&
    originalInstance.id === info.instance && originalInstance.data_version === 0 &&
    originalInstance.data.length === 0 && originalInstance.runs.length === 0,
  "normal generated six-step P-A opens its exact empty instance without a business Run");
  check(visible($("delivery-panel")) && visible($("manual-lock-panel")) && visible($("natural-logic-panel")),
    "natural app exposes graph, manual edit protection and existing local-logic entries");
  check($("column-patch-panel").hidden && $("csv-dag-panel").hidden,
    "natural app keeps unrelated CSV column and DAG controls hidden");
  check(postRows().length === 0 && currentGraph() === null && !$("delivery-proof").textContent,
    "opening saved app and instance performs no POST and has no derived graph proof");
  // This normal read proves the fixture did not smuggle in a saved graph.
  const beforeMissing = requests.length;
  await click("delivery-read");
  const missing = requests.slice(beforeMissing).find(row => row.path === graphBase);
  check(missing?.status === 409 && missing.response.error.code === "VERSION_CONFLICT" &&
    $("delivery-status").textContent.includes("尚未保存派生图") && postRows().length === 0,
  "normal page GET confirms no graph anchor exists before explicit derive");

  firstGraph = await derive(false, true);
  lockReceipt = await writeLock(true, true);
  lockedGraph = await derive(true);
  await edit("natural-logic-mode", "true");
  const beforeBlocked = requests.length;
  await click("natural-logic-preview");
  const blocked = postRows(beforeBlocked);
  check(blocked.length === 1 && blocked[0].path === logicBase + "/previews" && blocked[0].status === 400 &&
    blocked[0].response.error.code === "LOCK_CONFLICT" && $("natural-logic-status").textContent.includes("LOCK_CONFLICT"),
  "real natural preview stops at server LOCK_CONFLICT for the manually protected node");
  check($("natural-logic-check").disabled && $("natural-logic-version").disabled && $("natural-logic-commit").disabled,
    "rejected preview cannot CHECK or create a version");

  unlockReceipt = await writeLock(false, false);
  unlockedGraph = await derive(false);
  const beforeAllowed = requests.length;
  await click("natural-logic-preview");
  const allowed = postRows(beforeAllowed);
  check(allowed.length === 1 && allowed[0].path === logicBase + "/previews" && allowed[0].status === 201,
    "explicit unlock and rederive allow one normal natural logic preview");
  acceptedPreview = copy(allowed[0].response);
  const {preview_fingerprint, ...previewBody} = acceptedPreview;
  check(hash(previewBody) === preview_fingerprint && acceptedPreview.context.instance_id === info.instance &&
    acceptedPreview.context.graph_fingerprint === unlockedGraph.graph_fingerprint &&
    acceptedPreview.owner_acceptance === "PENDING" && acceptedPreview.semantic_status === "UNKNOWN",
  "successful preview is sealed to the unlocked graph and original instance without acceptance");
  check(!$("natural-logic-check-ack").checked && $("natural-logic-check").disabled,
    "successful preview still cannot CHECK until the user supplies independent consent");

  // A normal workspace round trip must not retain showApp's temporary open fence.
  const beforeNavigation = requests.length;
  await navigate("projects");
  await navigate("apps");
  check(visible($("delivery-panel")) && visible($("manual-lock-panel")),
    "normal projects-to-apps navigation keeps the selected graph entry available");
  await click("delivery-read");
  check(requests.slice(beforeNavigation).some(row => row.method === "GET" && row.path === graphBase && row.status === 200),
    "graph read remains live after the opening selection callback has expired");
  assert.deepEqual(currentGraph(), unlockedGraph);
  check(postRows(beforeNavigation).length === 0, "workspace navigation and graph read are GET-only");
  await click("internal-refresh");
  assert.deepEqual(evaluate("engineering.draft"), originalDraft);
  assert.deepEqual(evaluate("engineering.instance"), originalInstance);
  assert.deepEqual(evaluate("engineering.releases"), originalReleases);
  check(postRows().length === 7 && requests.every(row => row.method === "GET" ||
    [graphBase + "/derive", graphBase + "/manual-locks", logicBase + "/previews"].includes(row.path)),
  "all seven POSTs are bounded graph derive, edit-lock or logic-preview intents; no CHECK, Run or Release writes");
  check(originalDraft.candidate.spec_recipe.steps.length === 6 &&
    !originalDraft.candidate.spec_recipe.steps[2].inputs.prior_items &&
    acceptedPreview.effective_candidate.spec_recipe.steps[2].inputs.prior_items,
  "original parallel six-step definition and empty instance remain intact; changed logic is only a preview");
}

(async () => {
  let status = "FAIL", error = null;
  progress("driver_start", {classification: "ACTUAL_HTTP_JSDOM_NATURAL_GRAPH_CONTROLS"});
  try { await run(); status = "PASS"; }
  catch (failure) { error = failure.stack || String(failure); process.stderr.write(error + "\n"); }
  finally {
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
      classification: "ACTUAL_HTTP_JSDOM_NATURAL_GRAPH_CONTROLS", checks, actions, requests,
      static_resource_loads: assets, boots: dom ? 1 : 0, page_errors: errors, lifecycle,
      first_graph: firstGraph, locked_graph: lockedGraph, unlocked_graph: unlockedGraph,
      lock_receipt: lockReceipt, unlock_receipt: unlockReceipt, accepted_preview: acceptedPreview,
      original_draft: originalDraft, original_instance: originalInstance, original_releases: originalReleases,
      browser_platform: "JSDOM_WITH_CONTROLLED_STORAGE_WEB_LOCKS_NOT_NATIVE", real_model: "NOT_RUN",
      business_worker: "NOT_RUN", check_worker: "NOT_RUN", interval_scheduler: "DISABLED_MANUAL_READS_ONLY",
      fault_injections: "NONE", automatic_posts: "NONE", db_scope: "PARENT_VERIFIES_ALL_TABLES_BEFORE_AFTER",
    }, null, 2));
    process.stdout.write(JSON.stringify({status, checks: checks.length}) + "\n");
    process.exitCode = status === "PASS" ? 0 : 1;
  }
})();
