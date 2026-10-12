"use strict";

// Only actual resource markup, category controls, and the existing metadata GET
// adapter are loaded. Identity changes are synthetic catalog-only signals. No
// project loading, material/grant handlers, business modules, or server runs.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const web = path.join(__dirname, "../src/sim2act/web");
const app = fs.readFileSync(path.join(web, "app.js"), "utf8");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const css = fs.readFileSync(path.join(web, "app.css"), "utf8");
const controls = app.match(/^function selectResourceCategory\(category\) \{[\s\S]*?(?=^function createHealthSampler)/m)?.[0];
const resourceMarkup = html.match(/^<section id="resources" hidden>[^\n]+/m)?.[0];
const workspaceNav = html.match(/<nav id="workspace-nav"[^>]*>[\s\S]*?<\/nav>/)?.[0];
const workspaceSelect = app.match(/^function selectWorkspace\(id\) \{[\s\S]*?^\}/m)?.[0];
const api = app.match(/^async function api\([^\n]+\{[\s\S]*?^\}/m)?.[0];
const current = app.match(/  const current=\(\)=>identity===token && connection===identityConnectionGeneration;/)?.[0];
const read = app.match(/    const capabilities=await api\("\/api\/capabilities"\);if\(current\(\)\)renderResourceCatalog\(capabilities\);/)?.[0];
const catchRead = app.match(/  \} catch\(error\) \{if\(current\(\)\)throw error;\}/)?.[0];
const identityClear = app.match(/for\(const id of (\[[^\n]+\])\)\{\$\(id\)\.replaceChildren\(\);\}/)?.[1];
assert.ok(controls && resourceMarkup && workspaceNav && workspaceSelect && api && current && read && catchRead && identityClear);
assert.doesNotMatch(controls, /\b(?:fetch|api|import|require|setInterval|innerHTML)\b/);
const catalogIds = JSON.parse(identityClear).filter(id => ["capabilities", "connections"].includes(id));
assert.deepEqual(catalogIds, ["capabilities", "connections"]);
const catalog = {materials: ["txt", "md", "csv", "json"], tools: ["resource.read", "data.aggregate_csv", "artifact.save_text"], connection: {model: "synthetic-model", mode: "MOCK", status: "MOCK_ENGINEERING"}, code_execution: "DISABLED"};
const categories = ["materials", "capabilities", "connections"];

test("isolated resource category controls and catalog metadata", async t => {
  const browser = await chromium.launch({executablePath: process.env.RESOURCE_CATEGORIES_CHROMIUM || "/usr/bin/chromium", headless: true});
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block"});
    const network = [], errors = [];
    await context.route("**/*", async route => {network.push(route.request().url()); await route.abort();});
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    await page.setContent(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>${css}</style></head><body><header>隔离界面示例</header>${workspaceNav}<p id="error"></p><main><section id="projects"></section><section id="apps" hidden></section>${resourceMarkup}</main></body></html>`);

    async function state(selected) {
      const actual = await page.evaluate(() => ({
        buttons: Array.from(document.querySelectorAll("#resource-filters button"), b => ({category: b.dataset.resourceCategory, current: b.getAttribute("aria-current"), controls: b.getAttribute("aria-controls"), type: b.type, role: b.getAttribute("role"), tabIndex: b.tabIndex})),
        panels: ["materials", "capabilities", "connections"].map(id => ({id, hidden: document.getElementById("resource-" + id).hidden, display: getComputedStyle(document.getElementById("resource-" + id)).display})),
        workspaces: Array.from(document.querySelectorAll("#workspace-nav button"), b => b.dataset.tab),
      }));
      assert.deepEqual(actual.workspaces, ["projects", "apps", "resources"]);
      assert.deepEqual(actual.buttons.map(b => b.category), categories);
      assert.equal(actual.buttons.filter(b => b.current !== null).length, 1);
      for (const b of actual.buttons) {
        assert.equal(b.current, b.category === selected ? "true" : null);
        assert.equal(b.controls, "resource-" + b.category);
        assert.equal(b.type, "button"); assert.equal(b.role, null); assert.equal(b.tabIndex, 0);
      }
      for (const panel of actual.panels) {
        assert.equal(panel.hidden, panel.id !== selected);
        // The workspace can itself be hidden before initialization.
        if (await page.locator("#resources").isVisible()) assert.equal(panel.display === "none", panel.hidden);
      }
      if (await page.locator("#resources").isVisible()) await selectedStyle();
    }
    const button = category => page.locator(`[data-resource-category="${category}"]`);
    // The real stylesheet animates backgrounds for 120ms. Assert the settled
    // selected colors and capture them instead of an intermediate transition.
    const selectedStyle = () => page.waitForFunction(() => {
      const b = document.querySelector('#resource-filters [aria-current="true"]');
      const s = getComputedStyle(b);
      return s.backgroundColor === "rgb(22, 100, 83)" && s.color === "rgb(255, 255, 255)";
    });
    const texts = () => page.evaluate(() => ["capabilities", "connections"].map(id => document.getElementById(id).textContent));
    const render = data => page.evaluate(data => renderResourceCatalog(data), data);
    const begin = async identity => {
      await page.evaluate(identity => window.pending.push(window.readCatalog(identity)), identity);
      return (await page.evaluate(() => window.calls.length)) - 1;
    };
    const settle = (index, data = catalog, failure = null) => page.evaluate(async ({index, data, failure}) => {
      const call = window.calls[index];
      if (failure) call.reject(Error(failure));
      else call.resolve({ok: true, headers: {get: () => null}, json: async () => data});
      await window.pending[index];
    }, {index, data, failure});

    await t.test("HTML default, initialization, and current/hidden semantics agree", async () => {
      await state("materials");
      await page.evaluate(() => document.querySelectorAll("#resource-filters button").forEach(b => b.setAttribute("aria-current", "true")));
      await page.addScriptTag({content: `
        const $ = id => document.getElementById(id);
        let token = "", identityConnectionGeneration = 0;
        window.calls = []; window.pending = [];
        window.fetch = (url, options) => new Promise((resolve, reject) => window.calls.push({url, options, resolve, reject}));
        ${api}
        ${workspaceSelect}
        ${controls}
        selectWorkspace("resources");
        window.readCatalog = async next => {
          token = next; const connection = ++identityConnectionGeneration;
          for (const id of ${JSON.stringify(catalogIds)}) $(id).replaceChildren();
          const identity = token;
          ${current}
          try {
            ${read}
          ${catchRead}
        };
        window.readCatalog = ((readOnly) => async next => {
          try { await readOnly(next); } catch (error) { $("error").textContent = error.message; }
        })(window.readCatalog);
      `});
      await state("materials");
    });
    await t.test("click switches each category without any request", async () => {
      for (const id of [...categories, "materials", "materials"]) {await button(id).click(); await state(id);}
      assert.equal(await page.evaluate(() => window.calls.length), 0);
    });
    await t.test("native Tab/Enter/Space/Shift+Tab and visible focus remain", async () => {
      await button("materials").focus(); await page.keyboard.press("Tab"); await page.keyboard.press("Enter"); await state("capabilities");
      await page.keyboard.press("Tab"); await page.keyboard.press("Space"); await state("connections");
      assert.equal(await button("connections").evaluate(b => b === document.activeElement), true);
      const styles = await page.locator("#resource-filters button").evaluateAll(items => items.map(b => {const s=getComputedStyle(b); return [s.backgroundColor, s.textDecorationLine, s.outlineStyle];}));
      assert.notEqual(styles[0][0], styles[2][0]); assert.equal(styles[2][1], "underline"); assert.notEqual(styles[2][2], "none");
      await page.keyboard.press("Shift+Tab"); await page.keyboard.press("Shift+Tab"); await page.keyboard.press("Enter"); await state("materials");
    });
    await t.test("filter round trips preserve local draft, material list, grants, and preview", async () => {
      await page.locator("#resource-name").fill("未保存草稿"); await page.locator("#content").fill("line 1\nline 2");
      await page.evaluate(() => {for (const id of ["materials", "grants", "resource-preview"]) document.getElementById(id).textContent = "synthetic " + id; document.getElementById("resource-preview").hidden = false;});
      for (const id of ["capabilities", "connections", "materials"]) await button(id).click();
      assert.equal(await page.locator("#resource-name").inputValue(), "未保存草稿"); assert.equal(await page.locator("#content").inputValue(), "line 1\nline 2");
      for (const id of ["materials", "grants", "resource-preview"]) assert.equal(await page.locator("#"+id).textContent(), "synthetic " + id);
      assert.equal(await page.locator("#resource-preview").isVisible(), true);
      await page.evaluate(() => selectResourceCategory("unknown")); await state("materials");
    });
    await t.test("workspace selection remains separate from resource category selection", async () => {
      await button("connections").click(); await page.evaluate(() => selectWorkspace("apps"));
      assert.equal(await page.locator("#resources").isVisible(), false);
      await page.evaluate(() => selectWorkspace("resources")); await state("connections");
      assert.equal(await page.locator('#workspace-nav [aria-current="true"]').getAttribute("data-tab"), "resources");
    });
    await t.test("existing authenticated GET splits known MOCK fields and drops extra data", async () => {
      const index = await begin("synthetic-A");
      assert.deepEqual(await texts(), ["", ""]);
      await settle(index, {...catalog, secret: "must-not-render", connection: {...catalog.connection, secret: "must-not-render"}});
      const [tools, connection] = (await texts()).map(JSON.parse);
      assert.deepEqual(tools, {tools: catalog.tools, code_execution: "DISABLED"}); assert.deepEqual(connection, catalog.connection);
      assert.deepEqual(await page.evaluate(() => window.calls.map(c => ({url: c.url, options: c.options}))), [{url: "/api/capabilities", options: {method: "GET", headers: {Authorization: "Bearer synthetic-A", "Content-Type": "application/json"}}}]);
      for (const id of categories) await button(id).click();
      assert.equal(await page.evaluate(() => window.calls.length), 1);
    });
    await t.test("LIVE metadata retains its unaccepted status; registry does not imply grants", async () => {
      await render({...catalog, connection: {model: "synthetic-live", mode: "LIVE", status: "LIVE_NOT_ACCEPTED"}});
      assert.equal(JSON.parse((await texts())[1]).status, "LIVE_NOT_ACCEPTED");
      assert.match(await page.locator("#resource-capabilities").textContent(), /目录不代表材料已获授权/);
      assert.match(await page.locator("#resource-connections").textContent(), /MOCK 工程模拟不代表真实模型接入/);
      assert.equal(await page.locator("#grants").textContent(), "synthetic grants");
    });
    await t.test("catalog strings are inert text, including HTML-looking model/tool names", async () => {
      await render({...catalog, tools: ['<img src=x onerror="window.injected=true">'], connection: {...catalog.connection, model: "<script>window.injected=true</script>"}});
      assert.equal(await page.locator("#capabilities img, #connections script").count(), 0);
      assert.equal(await page.evaluate(() => window.injected), undefined);
      assert.match((await texts())[0], /<img/);
    });
    await t.test("malformed catalog clears previous data and reports a current read error", async () => {
      const invalid = [null, {}, {...catalog, tools: [123]}, {...catalog, code_execution: "ENABLED"}, {...catalog, connection: null}, {...catalog, connection: {...catalog.connection, model: 42}}, {...catalog, connection: {...catalog.connection, mode: "OTHER"}}, {...catalog, connection: {...catalog.connection, status: "ACCEPTED"}}];
      for (const data of invalid) {
        await render(catalog); const index = await begin("synthetic-A"); await settle(index, data);
        assert.deepEqual(await texts(), ["", ""]); assert.equal(await page.locator("#error").textContent(), "能力与连接目录响应无效");
      }
    });
    await t.test("A to B to A late responses cannot refill the new catalog", async () => {
      const a1 = await begin("synthetic-A"), b = await begin("synthetic-B"), a2 = await begin("synthetic-A");
      await settle(a2, {...catalog, connection: {...catalog.connection, model: "latest-A"}});
      const latest = await texts(); await settle(a1); await settle(b);
      assert.deepEqual(await texts(), latest);
    });
    await t.test("same-identity reconnect ignores old success and stale error", async () => {
      const oldSuccess = await begin("synthetic-A"), oldFailure = await begin("synthetic-A"), latest = await begin("synthetic-A");
      await page.locator("#error").evaluate(el => el.textContent = "new view feedback");
      await settle(latest, {...catalog, connection: {...catalog.connection, model: "reconnected"}});
      const expected = await texts(); await settle(oldSuccess); await settle(oldFailure, null, "old connection failure");
      assert.deepEqual(await texts(), expected); assert.equal(await page.locator("#error").textContent(), "new view feedback");
    });
    await t.test("current GET failure keeps both catalogs empty and reports feedback", async () => {
      const index = await begin("synthetic-B"); assert.deepEqual(await texts(), ["", ""]);
      await settle(index, null, "synthetic metadata unavailable");
      assert.deepEqual(await texts(), ["", ""]); assert.equal(await page.locator("#error").textContent(), "synthetic metadata unavailable");
    });
    await t.test("capture separate catalog panels with synthetic metadata", async () => {
      await render(catalog); await page.locator("#error").evaluate(el => el.textContent = "");
      if (process.env.RESOURCE_CATEGORIES_EVIDENCE_DIR) {
        fs.mkdirSync(process.env.RESOURCE_CATEGORIES_EVIDENCE_DIR, {recursive: true});
        for (const id of ["capabilities", "connections"]) {await button(id).click(); await selectedStyle(); await page.screenshot({path: path.join(process.env.RESOURCE_CATEGORIES_EVIDENCE_DIR, id + ".png"), fullPage: true});}
      }
    });
    await t.test("no real network, browser errors, business POSTs, or model probes", async () => {
      assert.deepEqual(network, []); assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => window.calls.every(c => c.url === "/api/capabilities" && c.options.method === "GET" && !c.options.body)), true);
    });
  } finally {await browser.close();}
});
