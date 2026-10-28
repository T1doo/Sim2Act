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
async function restartPreparation(oldKey, pendingHistory = false) {
  const length = w.history.length, state = JSON.stringify(w.history.state);
  if ($("trial-new").disabled) {
    if (w.eval("Boolean(trialEntry()?.receipt?.approved)")) { tick("trial-withdraw-ack"); await click("trial-withdraw"); }
    else { tick("trial-end-ack"); await click("trial-end"); }
  }
  await click("trial-new");
  check($("trial-original-key").value !== oldKey, "explicit new clears old visible key");
  check(w.history.length === length && JSON.stringify(w.history.state) === state && new URLSearchParams(w.location.search).get("kept") === "query" && new URLSearchParams(w.location.hash.slice(1)).get("kept") === "fragment", "explicit new replaces current address while preserving query unrelated fragment and history state");
  await click("trial-refresh");
  check(!$("trial-prepare").disabled, "explicit new followed by refresh enables preparation");
  check(w.eval("trialEntry() === undefined"), "explicit new refresh has no revived old UNKNOWN entry");
  check($("trial-original-key").value !== oldKey && new URLSearchParams(w.location.hash.slice(1)).get("trial-key") !== oldKey, "new view and URL no longer contain old key");
  $("trial-source").value = info.source; $("trial-cold").value = info.cold;
  if (pendingHistory) fault = "late-preparation";
  const work = click("trial-prepare");
  if (pendingHistory) {
    await wait(() => held);
    const pendingKey = $("trial-original-key").value;
    w.history.back();
    await new Promise(resolve => setTimeout(resolve, 40));
    check($("trial-original-key").value === pendingKey && new URLSearchParams(w.location.hash.slice(1)).get("trial-key") === pendingKey && $("trial-new").disabled && $("trial-prepare").disabled, "back history cannot replace a different pending original key");
    await click("trial-recover");
    const scope = $("trial-scope").textContent;
    release(); await work;
    check($("trial-original-key").value === pendingKey && $("trial-scope").textContent === scope && $("trial-new").disabled, "held preparation reply cannot overwrite newer original-key GET");
  } else await work;
  const prepared = requests.filter(r => r.method === "POST" && r.path.endsWith("/preparation"));
  check(prepared.length === 2 && prepared[0].path !== prepared[1].path, "second actual preparation POST uses a different fresh key");
  check($("trial-original-key").value !== oldKey && $("trial-scope").textContent.includes("共 7 槽"), "second exact scope displayed under new key");
}
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
    if (fault === "late-preparation" && request.method === "POST" && path.endsWith("/preparation")) { fault = ""; check(result.status === 200, "held second preparation actually committed"); held = true; await new Promise(resolve => release = resolve); }
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
  if (originalScenario.startsWith("new-")) {
    const url = new URL(w.location.href); url.search = "?kept=query"; url.hash = "kept=fragment";
    w.history.replaceState({marker: "kept"}, "", url);
  }
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
  if(originalScenario === "live-config-blocked") {
    const message=$("trial-status").textContent;
    check(message.includes("postgresql_application_database") && message.includes("SIM2ACT_APPLICATION_GENERATION_ACTIVATION_ENABLED=true"),"actual server configuration detail reaches the visible status");
    check(message.includes("无需重新确认免费模型许可") && !message.includes("修正目标或授权"),"configuration failure is not presented as missing model fee permission");
    check($("trial-consent").disabled && $("trial-export-selection").disabled && !$("trial-new").disabled,"refused new preparation creates no approval or export and permits explicit corrected new intent");
    check(posts("/consent")===0 && !requests.some(r=>r.method==="POST" && /\/runs|\/admission/.test(r.path)),"configuration diagnosis does not dispatch or request authorization");
    fs.writeFileSync(info.output,JSON.stringify({status:"PASS",scenario:info.scenario,checks,requests,static_resource_loads:loads,loaded_source_sha256:hashes,boots},null,2));
    dom.window.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
  }
  if (originalScenario === "unknown400") {
    check($("trial-new").disabled && $("trial-consent").disabled && $("trial-prepare").disabled, "actual API400 OUTCOME_UNKNOWN locks all new mutations");
    await click("trial-recover");
    check(posts("/preparation") === 1 && posts("/consent") === 0, "API400 unknown recovers by original GET only");
    check($("trial-new").disabled && $("trial-scope").textContent === "", "incomplete original pair never exposes scope or enables new key");
    fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
    dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
  }

  check($("trial-scope").textContent.includes("共 7 槽") && $("trial-scope").textContent.includes("192000") && $("trial-scope").textContent.includes("7168"), "full original budget visible");
  check($("trial-scope").textContent.includes("V2 审阅截止") && $("trial-scope").textContent.includes("执行截止") && $("trial-scope").textContent.includes("不是七槽完成保证"), "both frozen deadlines and finite handoff limits visible without a completion guarantee");
  check(info.goalTexts.every(text => $("trial-scope").textContent.includes(text)), "both complete goals and materials visible");
  check($("trial-consent").disabled && !$("trial-ack").checked, "no implicit consent after preparation");
  if (originalScenario.startsWith("manual-b-")) {
    $("trial-original-key").value = "manual-B"; await click("trial-recover");
    check(new URLSearchParams(w.location.hash.slice(1)).get("trial-key") === "manual-B", "manual recovery synchronizes B into reload URL");
    if (originalScenario === "manual-b-consent") fault = "consent";
    tick("trial-ack"); await click("trial-consent");
    if (originalScenario === "manual-b-withdrawal") { fault = "withdrawal"; tick("trial-withdraw-ack"); await click("trial-withdraw"); }
    check($("trial-new").disabled && $("trial-consent").disabled, "lost manual B mutation remains UNKNOWN");
    const boundary = requests.length, savedHash = w.location.hash;
    await boot(savedHash); await click("trial-recover");
    const recovery = requests.slice(boundary).filter(r => r.path.includes("/natural-trials/"));
    check(recovery.length > 0 && recovery.every(r => r.method === "GET" && r.path.includes("/manual-B/")), "reload recovery only GETs B, never A or another POST");
    check($("trial-original-key").value === "manual-B" && $("trial-status").textContent.includes(originalScenario === "manual-b-consent" ? "精确批准已持久保存" : "已撤回"), "B durable mutation recovered after lost response and reload");
    fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
    dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
  }
  if (originalScenario === "new-prepared") await restartPreparation(key);
  if (["new-history", "new-history-pending"].includes(originalScenario)) {
    w.history.pushState(w.history.state, "", w.location.href);
    await restartPreparation(key, originalScenario === "new-history-pending");
    if (originalScenario === "new-history") {
      const secondKey = $("trial-original-key").value, count = requests.length;
      w.history.back();
      await wait(() => $("trial-original-key").value === key); await new Promise(resolve => setTimeout(resolve, 40));
      check($("trial-scope").textContent === "" && $("trial-new").disabled && $("trial-consent").disabled && requests.length === count, "back restores old key as read-only UNKNOWN without automatic HTTP");
      await click("trial-recover");
      const afterBack = requests.length;
      w.history.forward();
      await wait(() => $("trial-original-key").value === secondKey); await new Promise(resolve => setTimeout(resolve, 40));
      check($("trial-scope").textContent === "" && $("trial-new").disabled && $("trial-consent").disabled && requests.length === afterBack, "forward restores second key as read-only UNKNOWN without automatic HTTP");
      await click("trial-recover");
      check(posts("/preparation") === 2 && $("trial-original-key").value === secondKey, "history recovery only GETs exact keys without another preparation");
    }
  }
  if (originalScenario === "new-late") {
    fault = "late"; tick("trial-ack"); const work = click("trial-consent");
    await wait(() => held);
    await click(w.document.querySelector('[data-tab="resources"]')); await click(w.document.querySelector('[data-tab="projects"]')); await click("trial-recover");
    check($("trial-status").textContent.includes("精确批准已持久保存"), "old consent is known through GET before explicit new");
    await restartPreparation(key);
    const secondKey = $("trial-original-key").value, scope = $("trial-scope").textContent;
    release(); await work;
    check($("trial-original-key").value === secondKey && $("trial-scope").textContent === scope && $("trial-new").disabled && !$("trial-ack").checked, "late abandoned consent cannot contaminate new key scope state or acknowledgement");
    check(posts("/consent") === 1 && posts("/preparation") === 2, "new intent never retries old consent");
    check(!requests.some(r => /\/application-runs|\/runs(?:$|\/)|\/admission|\/stage-approval/.test(r.path) && r.method === "POST"), "new intent never creates Run or dispatches");
    fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
    dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
  }

  if (originalScenario === "cold") {
    await boot(hash); check($("trial-original-key").value === key, "cold page restores only original project and key from link");
    check($("trial-consent").disabled && $("trial-scope").textContent === "", "cold page has no cached scope or approval");
    check($("trial-prepare").disabled && $("trial-new").disabled, "cold original-key intent locks all new preparation until GET recovery");
    await click("trial-recover"); check(posts("/preparation") === 1, "cold recovery only GETs original preparation");
  }
  if (["goal", "goal-close-lost", "revoke-read", "expiry"].includes(originalScenario)) {
    await rpc({command: originalScenario === "goal-close-lost" ? "goal" : originalScenario}); tick("trial-ack"); await click("trial-consent");
    check($("trial-consent").disabled && $("trial-new").disabled, "changed version authority or expiry cannot be approved or silently replaced");
    await click("trial-recover"); check(posts("/consent") === 1, "failed consent recovery never reposts consent");
    check(!$("trial-status").textContent.includes("精确批准已持久保存"), "refusal never displayed as approval");
    if (["goal", "goal-close-lost"].includes(originalScenario)) {
      check($("trial-new").disabled && $("trial-end").disabled, "transient unapproved metadata cannot unlock new or end without confirmation");
      if (originalScenario === "goal-close-lost") fault = "end-preparation";
      tick("trial-end-ack"); await click("trial-end");
      if (originalScenario === "goal-close-lost") {
        check($("trial-new").disabled, "lost close receipt stays UNKNOWN");
        const at = requests.length; await boot(w.location.hash); await click("trial-recover");
        check(requests.slice(at).filter(r => r.path.includes("/natural-trials/")).every(r => r.method === "GET" && r.path.includes(`/${key}/`)), "lost close reload only GETs original key");
      }
      check(!$("trial-new").disabled && $("trial-status").textContent.includes("永久结束"), "durable closed proof unlocks explicit new intent");
      check(posts("/end-preparation") === 1, "end never automatically retried");
      await click("trial-new"); await click("trial-refresh");
      check(!$("trial-prepare").disabled, "Goal revision no longer strands old preparation");
    }

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
    if(originalScenario === "configured-selection") {
      const blobs=[],downloads=[];
      w.Blob=Blob;w.URL.createObjectURL=blob=>{blobs.push(blob);return "blob:synthetic-selection";};
      w.URL.revokeObjectURL=()=>{};w.HTMLAnchorElement.prototype.click=function(){downloads.push(this.download);};
      const button=$("trial-export-selection");button.closest("details").open=true;
      check(!button.disabled,"only approved fixed-account scope enables selection export");
      const before=requests.length;await click("trial-export-selection");
      check(blobs.length===1 && downloads.join(",")==="trial-selection.json","actual export gesture creates one JSON attachment");
      const selected=JSON.parse(await blobs[0].text());
      assert.deepEqual(Object.keys(selected).sort(),["account","approval","project","trial","user"]);
      check(selected.account==="intern-ai-configured-account" && selected.project===info.project && selected.trial===key,"export binds original project/trial and fixed account without credentials");
      check(requests.slice(before).length===1 && requests[before].method==="GET" && requests[before].path.endsWith("/preparation"),"export freshly reauthorizes exact original scope by GET only");
      w.eval("trialEntry().receipt.worker_selection.user='user_'+ '0'.repeat(32);renderTrialConsent()");
      check(button.disabled,"identity mismatch disables export rather than creating a guessed selection");
      await click("trial-recover");
      const originalFetch=w.fetch;let releaseExport,heldExport=false;
      w.fetch=async (...args)=>{const response=await originalFetch(...args);if(args[0].endsWith("/preparation")){heldExport=true;await new Promise(resolve=>releaseExport=resolve);}return response;};
      const late=click("trial-export-selection");await wait(()=>heldExport);
      await click(w.document.querySelector('[data-tab="resources"]'));releaseExport();await late;
      check(blobs.length===1 && $("error").textContent==="","late export after view switch creates no attachment or error in another view");
      w.fetch=originalFetch;await click(w.document.querySelector('[data-tab="projects"]'));await click("trial-recover");
    }
    if (originalScenario === "after-read-revoke") { await rpc({command: "revoke-read"}); await click("trial-recover"); check($("trial-scope").textContent.includes("仅恢复同意元数据"), "revoked READ yields metadata only without cached TXT"); }
    if (originalScenario === "lost-withdrawal") fault = "withdrawal";
    tick("trial-withdraw-ack"); await click("trial-withdraw");
    if (originalScenario === "lost-withdrawal") { check($("trial-new").disabled, "lost withdrawal stays unknown"); await click("trial-recover"); }
    check(posts("/withdrawal") === 1, "withdrawal posted once");
    check($("trial-status").textContent.includes("已撤回") && $("trial-consent").disabled, "withdrawn approval cannot be reused");
    if(originalScenario === "configured-selection")check($("trial-export-selection").disabled,"revoked approval cannot export a runnable selection");
    if (originalScenario === "new-revoked") await restartPreparation(key);
  }
  check(!requests.some(r => /\/application-runs|\/runs(?:$|\/)|\/admission|\/stage-approval/.test(r.path) && r.method === "POST"), "page never creates Run reserves slot or asks for LIVE admission");
  fs.writeFileSync(info.output, JSON.stringify({status: "PASS", scenario: info.scenario, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2));
  dom.window.close(); process.stdout.write(JSON.stringify({done: true}) + "\n"); process.exit(0);
})().catch(error => { fs.writeFileSync(info.output, JSON.stringify({status: "FAIL", error: error.stack, checks, requests, static_resource_loads: loads, loaded_source_sha256: hashes, boots}, null, 2)); if (dom) dom.window.close(); console.error(error.stack); process.exit(1); });
