"use strict";
const fs = require("node:fs"), assert = require("node:assert/strict"), crypto = require("node:crypto"), readline = require("node:readline"), {JSDOM} = require("jsdom");
const info = JSON.parse(fs.readFileSync(process.argv[2])), pending = new Map(), checks = [], requests = [], loads = [], hashes = {};
let serial = 0, dom, w, $, fault = "", release = null, held = false, boots = 0;
readline.createInterface({input: process.stdin}).on("line", line => { const r = JSON.parse(line); pending.get(r.id)(r); pending.delete(r.id); });
const rpc = body => new Promise(resolve => { const id = ++serial; pending.set(id, resolve); process.stdout.write(JSON.stringify({id, ...body}) + "\n"); });
const check = (v, name) => { assert(v, name); checks.push(name); };
const wait = async predicate => { const end = Date.now() + 12000; while (!predicate()) { if (Date.now() > end) throw Error("bounded DOM wait expired"); await new Promise(r => setTimeout(r, 5)); } };
function visible(e) { for (let n = e; n; n = n.parentElement) if (n.hidden || w.getComputedStyle(n).display === "none") return false; return !!e?.isConnected; }
async function click(id) { const e = typeof id === "string" ? $(id) : id; check(visible(e) && !e.disabled, `visible enabled gesture ${e.id || e.textContent}`); const original = e.onclick; let work; e.onclick = function (event) { return work = original.call(this, event); }; e.click(); e.onclick = original; await work; }
function tick(id) { check(visible($(id)) && !$(id).disabled, `checkbox ${id} visible`); $(id).checked = true; $(id).dispatchEvent(new w.Event("change", {bubbles: true})); }
const posts = suffix => requests.filter(r => r.method === "POST" && r.path.endsWith(suffix)).length;
async function boot(hash = "") {
  if (dom) dom.window.close(); boots++;
  const load = async path => { const r = await rpc({path, method: "GET"}); assert.equal(r.status, 200); loads.push({boot: boots, path, status: r.status, sha256: crypto.createHash("sha256").update(r.text).digest("hex")}); return r.text; };
  const html = await load("/"); hashes["index.html"] = crypto.createHash("sha256").update(html).digest("hex");
  dom = new JSDOM(html, {url: "http://offline.test/" + hash, runScripts: "dangerously", pretendToBeVisual: true}); w = dom.window; $ = id => w.document.getElementById(id);
  w.TextEncoder = TextEncoder; w.structuredClone = structuredClone; w.crypto.randomUUID = info.scenario === "unknown400" ? () => "seeded-key" : crypto.randomUUID; Object.defineProperty(w.crypto, "subtle", {value: crypto.webcrypto.subtle}); w.setInterval = () => 0;
  const css = await load("/app.css"); hashes["app.css"] = crypto.createHash("sha256").update(css).digest("hex"); const style = w.document.createElement("style"); style.textContent = css; w.document.head.append(style);
  w.fetch = async (path, options = {}) => {
    const request = {path, method: options.method || "GET", body: options.body && JSON.parse(options.body), headers: options.headers}; requests.push(request);
    const result = await rpc(request);
    if (request.method === "POST" && path.endsWith("/" + fault)) { fault = ""; check(result.status === 200, "lost response follows actual server commit"); throw Error("controlled response loss after real HTTP commit"); }
    if (fault === "late" && request.method === "POST" && path.endsWith("/consent")) { fault = ""; check(result.status === 200, "held consent actually committed"); held = true; await new Promise(resolve => release = resolve); }
    return new Response(result.text, {status: result.status, headers: {"Content-Type": result.content_type || "application/json"}});
  };
  for (const script of [...w.document.querySelectorAll("script[src]")]) { const name = script.getAttribute("src").slice(1), text = await load("/" + name); hashes[name] = crypto.createHash("sha256").update(text).digest("hex"); const node = w.document.createElement("script"); node.textContent = text; w.document.body.append(node); }
  $("token").value = "synthetic-test-A"; await click("connect");
  await wait(() => $("login").hidden && $("project-select").value === info.project);
  await click("trial-refresh"); $("trial-source").value = info.source; $("trial-cold").value = info.cold;
  check(visible($("trial-panel")), "preparation entry appears in actual project page");
}
(async () => {
  await boot(); const originalScenario = info.scenario;
  if (["lost-preparation", "lost-cold"].includes(originalScenario)) fault = "preparation";
  await click("trial-prepare");
  const key = $("trial-original-key").value, hash = w.location.hash;
  check(/^[A-Za-z0-9_-]+$/.test(key), "server scope key generated without handwritten JSON or hash");
  if (originalScenario === "lost-preparation") { check($("trial-new").disabled && $("trial-consent").disabled, "unknown preparation locks new key and consent"); await click("trial-recover"); }
  if (originalScenario === "lost-cold") {
    check($("trial-new").disabled && $("trial-consent").disabled, "lost preparation remains unknown before reload");
    await boot(hash);
    check($("trial-original-key").value === key && $("trial-prepare").disabled && $("trial-new").disabled && $("trial-consent").disabled, "lost response cold page locks all new mutations under original URL key");
    await click("trial-recover");
    check(posts("/preparation") === 1, "lost response cold recovery never reposts preparation");
  }
  check(posts("/preparation") === 1, "one original preparation POST");
  if (originalScenario === "unknown400") {
    check($("trial-new").disabled && $("trial-consent").disabled && $("trial-prepare").disabled, "actual API400 OUTCOME_UNKNOWN locks all new mutations");
    await click("trial-recover");
    check(posts("/preparation") === 1 && posts("/consent") === 0, "API400 unknown recovers by original GET only");
    check($("trial-new").disabled && $("trial-scope").textContent === "", "incomplete original pair never exposes scope or enables new key");
    fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
    dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
  }

  check($("trial-scope").textContent.includes("共 7 槽") && $("trial-scope").textContent.includes("192000") && $("trial-scope").textContent.includes("7168"), "full original budget visible");
  check(info.goalTexts.every(text => $("trial-scope").textContent.includes(text)), "both complete goals and materials visible");
  check($("trial-consent").disabled && !$("trial-ack").checked, "no implicit consent after preparation");
  if (originalScenario === "cold") {
    await boot(hash); check($("trial-original-key").value === key, "cold page restores only original project and key from link");
    check($("trial-consent").disabled && $("trial-scope").textContent === "", "cold page has no cached scope or approval");
    check($("trial-prepare").disabled && $("trial-new").disabled, "cold original-key intent locks all new preparation until GET recovery");
    await click("trial-recover"); check(posts("/preparation") === 1, "cold recovery only GETs original preparation");
  }
  if (["goal", "revoke-read", "expiry"].includes(originalScenario)) {
    await rpc({command: originalScenario}); tick("trial-ack"); await click("trial-consent");
    check($("trial-consent").disabled && $("trial-new").disabled, "changed version authority or expiry cannot be approved or silently replaced");
    await click("trial-recover"); check(posts("/consent") === 1, "failed consent recovery never reposts consent");
    check(!$("trial-status").textContent.includes("精确批准已持久保存"), "refusal never displayed as approval");
  } else {
    if (originalScenario === "lost-consent") fault = "consent";
    if (originalScenario === "late-navigation") fault = "late";
    tick("trial-ack");
    const submission = click("trial-consent");
    if (originalScenario === "late-navigation") {
      await wait(() => held); await click(w.document.querySelector('[data-tab="resources"]'));
      check($("trial-scope").textContent === "" && !$("trial-ack").checked, "late accepted consent cannot populate or acknowledge another view");
      await click(w.document.querySelector('[data-tab="projects"]')); await click("trial-recover");
      check($("trial-status").textContent.includes("精确批准已持久保存"), "original-key GET recovers before old POST response is released");
      const recoveredScope = $("trial-scope").textContent; release(); await submission;
      check($("trial-status").textContent.includes("精确批准已持久保存") && $("trial-scope").textContent === recoveredScope, "late old POST cannot overwrite newer GET recovery");
    } else { await submission; if (originalScenario === "lost-consent") { check($("trial-consent").disabled && $("trial-new").disabled, "lost consent locks mutating controls"); await click("trial-recover"); } }
    check(posts("/consent") === 1, "exact consent posted once");
    check($("trial-status").textContent.includes("精确批准已持久保存"), "durable approval recovered through actual HTTP");
    check(!$("trial-ack").checked && $("trial-consent").disabled, "duplicate approval disabled after durable receipt");
    if (originalScenario === "after-read-revoke") { await rpc({command: "revoke-read"}); await click("trial-recover"); check($("trial-scope").textContent.includes("仅恢复同意元数据"), "revoked READ yields metadata only without cached TXT"); }
    if (originalScenario === "lost-withdrawal") fault = "withdrawal";
    tick("trial-withdraw-ack"); await click("trial-withdraw");
    if (originalScenario === "lost-withdrawal") { check($("trial-new").disabled, "lost withdrawal stays unknown"); await click("trial-recover"); }
    check(posts("/withdrawal") === 1, "withdrawal posted once");
    check($("trial-status").textContent.includes("已撤回") && $("trial-consent").disabled, "withdrawn approval cannot be reused");
  }
  check(!requests.some(r => /\/application-runs|\/runs(?:$|\/)|\/admission|\/stage-approval/.test(r.path) && r.method === "POST"), "page never creates Run reserves slot or asks for LIVE admission");
  fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
  dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
})().catch(error => { fs.writeFileSync(info.output, JSON.stringify({status: "FAIL", error: error.stack, checks, requests}, null, 2)); if (dom) dom.window.close(); console.error(error.stack); process.exit(1); });
