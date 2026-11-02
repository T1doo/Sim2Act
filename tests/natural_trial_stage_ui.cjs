"use strict";
const fs = require("node:fs"), assert = require("node:assert/strict"), crypto = require("node:crypto"), readline = require("node:readline"), {JSDOM} = require("jsdom");
const info = JSON.parse(fs.readFileSync(process.argv[2])), pending = new Map(), checks = [], requests = [], loads = [], hashes = {};
let serial = 0, dom, w, $, fault = "", release = null, held = false, boots = 0;
let durable={};const locks=new Set();
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
  if(dom){durable=Object.fromEntries(Object.entries(w.localStorage));w.dispatchEvent(new w.Event("pagehide"));dom.window.close();}boots++;
  const load = async path => { const r = await rpc({path, method: "GET"}); assert.equal(r.status, 200); loads.push({boot: boots, path, status: r.status, sha256: crypto.createHash("sha256").update(r.text).digest("hex")}); return r.text; };
  const html = await load("/"); hashes["index.html"] = crypto.createHash("sha256").update(html).digest("hex");
  dom = new JSDOM(html, {url: "http://offline.test/" + hash, runScripts: "dangerously", pretendToBeVisual: true}); w = dom.window; $ = id => w.document.getElementById(id);
  for(const [k,v] of Object.entries(durable))w.localStorage.setItem(k,v);
  Object.defineProperty(w.navigator,"locks",{value:{request:async(key,options,fn)=>{if(locks.has(key))return fn(null);locks.add(key);try{return await fn({name:key});}finally{locks.delete(key);}}},configurable:true});
  w.TextEncoder = TextEncoder; w.structuredClone = structuredClone; w.crypto.randomUUID = info.scenario === "unknown400" ? () => "seeded-key" : crypto.randomUUID; Object.defineProperty(w.crypto, "subtle", {value: crypto.webcrypto.subtle}); w.setInterval = () => 0;
  const css = await load("/app.css"); hashes["app.css"] = crypto.createHash("sha256").update(css).digest("hex"); const style = w.document.createElement("style"); style.textContent = css; w.document.head.append(style);
  w.fetch = async (path, options = {}) => {
    const request = {path, method: options.method || "GET", body: options.body && JSON.parse(options.body), headers: options.headers}; requests.push(request);
    const result = await rpc(request);
    if(fault==="bad-stage"&&path.endsWith("/stage-approval")){fault="";const value=JSON.parse(result.text);value.authority.run_id="run_"+"e".repeat(32);result.text=JSON.stringify(value);}
    if(fault==="late-stage"&&path.endsWith("/stage-review")){fault="";held=true;await new Promise(resolve=>release=resolve);}
    if (request.method === "POST" && path.endsWith("/" + fault)) { fault = ""; check(result.status === 200, path.endsWith("/stage-approval") ? "lost response follows simulated typed stage acceptance" : "lost response follows actual root server commit"); throw Error("controlled response loss after accepted response"); }
    if (fault === "late-preparation" && request.method === "POST" && path.endsWith("/preparation")) { fault = ""; check(result.status === 200, "held second preparation actually committed"); held = true; await new Promise(resolve => release = resolve); }
    if (fault === "late" && request.method === "POST" && path.endsWith("/consent")) { fault = ""; check(result.status === 200, "held consent actually committed"); held = true; await new Promise(resolve => release = resolve); }
    return new Response(result.text, {status: result.status, headers: {"Content-Type": result.content_type || "application/json"}});
  };
  for (const script of [...w.document.querySelectorAll("script[src]")]) { const name = script.getAttribute("src").slice(1), text = await load("/" + name); hashes[name] = crypto.createHash("sha256").update(text).digest("hex"); const node = w.document.createElement("script"); node.textContent = text; w.document.body.append(node); }
  $("token").value = "synthetic-test-A"; await click("connect");
  await wait(() => $("login").hidden && $("project-select").value === info.project);
  w.document.querySelector('.section-links a[href="#goal-cards-panel"]').click();
  check(visible($("goal-cards-panel")), "explicit project navigation exposes stage review workspace");
  await click("trial-refresh"); $("trial-source").value = info.source; $("trial-cold").value = info.cold;
  check(visible($("trial-panel")), "preparation entry appears in actual project page");
}
(async()=>{
 await boot();await click("trial-prepare");$("trial-ack").checked=true;$("trial-ack").dispatchEvent(new w.Event("change"));await click("trial-consent");
 const rootKey=$("trial-original-key").value,hash=w.location.hash;
 await click("trial-stage-list");$("trial-stage-run").value=info.sourceRun;$("trial-stage-run").dispatchEvent(new w.Event("change"));
 if(info.scenario==="late"){
   fault="late-stage";const work=click("trial-stage-review");await wait(()=>held);
   $("trial-stage-kind").value="cold";$("trial-stage-kind").dispatchEvent(new w.Event("change"));release();await work;
   check($("trial-stage-preview").textContent===""&&!$("trial-stage-ack").checked,"late review cannot reveal old stage or enable consent");
   check(posts("/stage-approval")===0,"late response did not approve");
 }else{
   await click("trial-stage-review");
   if(info.scenario==="wrong-review"){
     check($("trial-stage-preview").textContent===""&&!$("trial-stage-ack").checked&&posts("/stage-approval")===0,"foreign target with valid digest cannot be approved");
     fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,loaded_source_sha256:hashes,stage_endpoints:"CONTROLLED_TYPED_WIRE_ONLY"},null,2));w.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
   }
   check($("trial-stage-preview").textContent.includes(info.sourceText),"complete actual fixture material shown as text");
   check(!$("trial-stage-preview").textContent.includes('"contract_fingerprint":'),"review is a readable workflow without JSON");
   check($("trial-stage-confirm").disabled,"no default consent");
   if(info.scenario==="revoke"){
     await rpc({command:"revoke-read"});await click("trial-stage-review");
     check($("trial-scope").textContent===""&&$("trial-stage-preview").textContent==="","403 clears parent and stage private material");
     check(posts("/stage-approval")===0,"revocation cannot approve");
   }else if(info.scenario==="stale"){
     await rpc({command:"change-version"});$("trial-stage-ack").checked=true;$("trial-stage-ack").dispatchEvent(new w.Event("change"));await click("trial-stage-confirm");
     check(posts("/stage-approval")===0,"changed fresh authority cannot be approved");
     check($("trial-stage-key").value==="","readonly rejection did not create an unknown mutation intent");
   }else if(info.scenario==="storage"){
     Object.defineProperty(w.Storage.prototype,"setItem",{value:()=>{throw Error("controlled storage failure");}});
     $("trial-stage-ack").checked=true;$("trial-stage-ack").dispatchEvent(new w.Event("change"));await click("trial-stage-confirm");
     check(posts("/stage-approval")===0,"failed durable key prevents every mutation");
   }else{
     if(info.scenario==="lost")fault="stage-approval";
     if(info.scenario==="bad")fault="bad-stage";
     $("trial-stage-ack").checked=true;$("trial-stage-ack").dispatchEvent(new w.Event("change"));if(info.scenario==="double")await Promise.all([click("trial-stage-confirm"),click("trial-stage-confirm")]);else await click("trial-stage-confirm");
     const originalKey=$("trial-stage-key").value;
     check(originalKey&&posts("/stage-approval")===1,"one explicit approval with durable original key");
     check($("trial-stage-confirm").disabled&&!$("trial-stage-ack").checked,"no repeat approval after known or unknown response");
     const records=Object.entries(w.localStorage).filter(([k])=>k.startsWith("sim2act.stage-intent.v1:"));
     check(records.length===1&&!JSON.stringify(records).includes("synthetic-test-A")&&!JSON.stringify(records).includes(info.sourceText),"durable intent contains no bearer or private material");
     if(info.scenario==="lost"){
       await boot(hash);await click("trial-recover");await click("trial-stage-recover");
       check($("trial-stage-key").value===originalKey,"close/reopen restores same original stage key");
     }else await click("trial-stage-recover");
     check($("trial-stage-status").textContent.includes("只读核对"),"persisted original stage recovery verified");
     check(posts("/stage-approval")===1,"recovery never reposts approval");
     if(info.scenario==="happy"){
       $("trial-stage-kind").value="cold";$("trial-stage-kind").dispatchEvent(new w.Event("change"));await click("trial-stage-list");
       $("trial-stage-run").value=info.coldRun;$("trial-stage-run").dispatchEvent(new w.Event("change"));await click("trial-stage-review");
       check($("trial-stage-preview").textContent.includes(info.coldText),"Cold shows independent target material");
       $("trial-stage-ack").checked=true;$("trial-stage-ack").dispatchEvent(new w.Event("change"));await click("trial-stage-confirm");await click("trial-stage-recover");
       check(posts("/stage-approval")===2&&$("trial-stage-status").textContent.includes("只读核对"),"Cold requires its own explicit consent and recovery");
       await click("trial-stage-withdraw-link");check(!$("trial-withdraw-ack").checked,"withdraw navigation never supplies consent");
       $("trial-withdraw-ack").checked=true;$("trial-withdraw-ack").dispatchEvent(new w.Event("change"));await click("trial-withdraw");
       check($("trial-stage-confirm").disabled,"root withdrawal blocks further phase approval");
     }
   }
 }
 fs.writeFileSync(info.output,JSON.stringify({status:"PASS",checks,requests,loaded_source_sha256:hashes,stage_endpoints:"CONTROLLED_TYPED_WIRE_ONLY"},null,2));
 w.close();process.stdout.write(JSON.stringify({done:true})+"\n");process.exit(0);
})().catch(error=>{console.error(error.stack);process.exit(1);});
