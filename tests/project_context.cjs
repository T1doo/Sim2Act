"use strict";

// Load only the actual project-context block, navigation, and static controls.
// Project/identity updates below are synthetic DOM signals. No connect/create/
// change business handler, application module, server, or database is executed.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const web = path.join(__dirname, "../src/sim2act/web");
const app = fs.readFileSync(path.join(web, "app.js"), "utf8");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const css = fs.readFileSync(path.join(web, "app.css"), "utf8");
const controls = app.match(/^function renderProjectContext\(\) \{[\s\S]*?(?=^function selectResourceCategory)/m)?.[0];
const nav = html.match(/<nav id="workspace-nav"[^>]*>[\s\S]*?<\/nav>/)?.[0];
const selectWorkspace = app.match(/^function selectWorkspace\(id\) \{[\s\S]*?^\}/m)?.[0];
const navigation = app.match(/^document\.querySelectorAll\("#workspace-nav \[data-tab\]"\)\.forEach\([^\n]+\);\nselectWorkspace\("projects"\);$/m)?.[0];
const login = html.match(/<section id="login">[\s\S]*?<\/section>/)?.[0];
const scope = html.match(/<section id="project-context"[^>]*>[\s\S]*?<\/section>/)?.[0];
const projectForm = html.match(/<form id="project-form">[\s\S]*?<\/form>/)?.[0];
const projectSelect = html.match(/<select id="project-select"[^>]*>[\s\S]*?<\/select>/)?.[0];
const resourceForm = html.match(/<form id="resource-form">[\s\S]*?<\/form>/)?.[0];
const identityNotification = app.match(/\}\n(  renderProjectContext\(\);)\n  \$\("reconcile-panel"\)\.hidden=true;/)?.[1];
assert.ok(controls && nav && selectWorkspace && navigation && login && scope && projectForm && projectSelect && resourceForm && identityNotification);
assert.doesNotMatch(controls, /\b(?:api|fetch|import|require|safe|saveResourceMaterial|clearIdentityView|dispatchEvent|innerHTML)\s*\(/);
const initial = "请先连接本机 API，再选择项目。材料仅在所选项目内保存和授权。";
const unselected = "尚未选择项目。请到项目工作区选择已有项目，或填写名称创建项目。";
const selected = name => `当前所选项目：${name}。保存材料将授权给此项目；切换项目请使用项目工作区的原选择器。`;

test("isolated current-project context and navigation flow", async t => {
  const browser = await chromium.launch({executablePath: process.env.PROJECT_CONTEXT_CHROMIUM || "/usr/bin/chromium", headless: true});
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block"});
    const network = [], errors = [];
    await context.route("**/*", async route => {network.push(route.request().url()); await route.abort();});
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.on("pageerror", e => errors.push(e.message));
    await page.setContent(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><style>${css}</style></head><body><header>隔离界面示例</header>${login}${nav}<main><p id="error" role="alert"></p>${scope}<section id="projects"><h1>项目</h1>${projectForm}<label>项目 ${projectSelect}</label></section><section id="apps" hidden><h1>应用</h1></section><section id="resources" hidden><h1>资源</h1>${resourceForm}</section></main></body></html>`);
    const status = () => page.locator("#project-context-status").textContent();
    const button = page.locator("#project-context-open");
    async function expected(message, label) {
      await page.waitForFunction(message => document.getElementById("project-context-status").textContent === message, message);
      assert.equal(await status(), message); assert.equal(await button.textContent(), label);
    }
    async function focus(id) {assert.equal(await page.evaluate(() => document.activeElement.id), id);}
    async function workspace(id) {
      assert.equal(await page.locator('#workspace-nav [aria-current="true"]').getAttribute("data-tab"), id);
      assert.equal(await page.locator("#workspace-nav [aria-current]").count(), 1);
      for (const name of ["projects", "apps", "resources"]) assert.equal(await page.locator("#" + name).isVisible(), name === id);
    }

    await t.test("HTML default and JS initialization agree; live scope is described to assistive technology", async () => {
      assert.equal(await status(), initial);
      assert.equal(await page.locator("#project-context").getAttribute("aria-label"), "当前项目范围");
      for (const [attr, value] of [["role", "status"], ["aria-live", "polite"], ["aria-atomic", "true"]]) assert.equal(await page.locator("#project-context-status").getAttribute(attr), value);
      assert.equal(await button.getAttribute("type"), "button"); assert.equal(await button.getAttribute("aria-describedby"), "project-context-status");
      await page.locator("#project-context-status").evaluate(el => el.textContent = "stale view");
      await page.addScriptTag({content: `
        const $ = id => document.getElementById(id); let token = "";
        window.actions = []; window.fetch = (...args) => {window.actions.push(["fetch", ...args]); throw Error("Network forbidden");};
        for (const id of ["connect", "project-select"]) $(id).addEventListener(id === "connect" ? "click" : "change", () => window.actions.push(id));
        for (const id of ["project-form", "resource-form"]) $(id).onsubmit = event => {event.preventDefault(); window.actions.push(id);};
        ${selectWorkspace}
        ${navigation}
        ${controls}
        // Only the new ordinary UI notification is extracted from identity
        // clearing. None of that function's business/reset callbacks execute.
        window.identityContextSignal = () => {${identityNotification}};
      `});
      await expected(initial, "填写连接令牌");
    });
    await t.test("first-use button returns from resources and focuses the existing token field without connecting", async () => {
      await page.locator("#token").fill("unsubmitted-token-draft");
      await page.evaluate(() => {selectWorkspace("resources"); document.getElementById("login").hidden = true;});
      await button.focus(); await page.keyboard.press("Enter");
      await workspace("projects"); await focus("token");
      assert.equal(await page.locator("#login").isVisible(), true);
      assert.equal(await page.locator("#token").inputValue(), "unsubmitted-token-draft");
      assert.equal(await page.evaluate(() => token), "");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("a synthetic identity with no project receives the original create-project route", async () => {
      await page.evaluate(() => {token = "synthetic-A"; document.getElementById("project-select").replaceChildren(); document.getElementById("login").hidden = true; selectWorkspace("apps");});
      await expected(unselected, "选择或创建项目");
      await button.focus(); await page.keyboard.press("Space");
      await workspace("projects"); await focus("project-name");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("newly loaded projects display the existing selected name without selecting or authorizing", async () => {
      await page.evaluate(() => document.getElementById("project-select").replaceChildren(new Option("项目甲", "A"), new Option("项目乙", "B")));
      await expected(selected("项目甲"), "选择或切换项目");
      assert.equal(await page.locator("#project-select").inputValue(), "A");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("from either resource or application workspace the route focuses the original selector and preserves drafts", async () => {
      await page.locator("#project-name").fill("未提交项目名");
      await page.evaluate(() => selectWorkspace("resources"));
      await page.locator("#resource-name").fill("未保存材料"); await page.locator("#content").fill("raw\ntext");
      await page.locator("#error").evaluate(el => el.textContent = "existing feedback");
      for (const id of ["resources", "apps"]) {
        await page.evaluate(id => selectWorkspace(id), id); await button.click();
        await workspace("projects"); await focus("project-select");
        assert.equal(await page.locator("#project-select").inputValue(), "A");
      }
      assert.equal(await page.locator("#project-name").inputValue(), "未提交项目名");
      assert.equal(await page.locator("#resource-name").inputValue(), "未保存材料"); assert.equal(await page.locator("#content").inputValue(), "raw\ntext");
      assert.equal(await page.locator("#error").textContent(), "existing feedback");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("native project selection updates scope with the existing change event only", async () => {
      await page.locator("#project-select").selectOption("B");
      await expected(selected("项目乙"), "选择或切换项目");
      assert.deepEqual(await page.evaluate(() => window.actions), ["project-select"]);
      await page.evaluate(() => window.actions = []);
    });
    await t.test("refreshed options and relabels display the final selected project, not an intermediate default", async () => {
      await page.evaluate(() => {const s=document.getElementById("project-select"); s.replaceChildren(new Option("刷新甲", "A"), new Option("刷新乙", "B")); s.value="B";});
      await expected(selected("刷新乙"), "选择或切换项目");
      await page.evaluate(() => document.getElementById("project-select").selectedOptions[0].textContent = "乙新名称");
      await expected(selected("乙新名称"), "选择或切换项目");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("identity reset removes old scope, including native replaceChildren on an already empty selector", async () => {
      await page.evaluate(() => {token="synthetic-B"; document.getElementById("project-select").replaceChildren(); window.identityContextSignal();});
      await expected(unselected, "选择或创建项目"); assert.doesNotMatch(await status(), /乙新名称/);
      await page.evaluate(() => {token=""; document.getElementById("project-select").replaceChildren(); window.identityContextSignal();});
      await expected(initial, "填写连接令牌");
      assert.deepEqual(await page.evaluate(() => window.actions), []);
    });
    await t.test("placeholder-only selection is not a project; routing uses actual available options", async () => {
      await page.evaluate(() => {token="synthetic-B"; document.getElementById("project-select").replaceChildren(new Option("请选择", ""));});
      await expected(unselected, "选择或创建项目"); await button.click(); await focus("project-name");
      await page.evaluate(() => document.getElementById("project-select").append(new Option("候选项目", "candidate")));
      await expected(unselected, "选择或创建项目"); await button.click(); await focus("project-select");
      assert.equal(await page.locator("#project-select").inputValue(), "");
    });
    await t.test("HTML-looking project names are inert text; tokens and IDs are not displayed", async () => {
      await page.evaluate(() => {token="secret-token-synthetic"; document.getElementById("project-select").replaceChildren(new Option('<img src=x onerror="window.injected=true">', "private-project-id"));});
      await expected(selected('<img src=x onerror="window.injected=true">'), "选择或切换项目");
      assert.equal(await page.locator("#project-context img").count(), 0); assert.equal(await page.evaluate(() => window.injected), undefined);
      assert.doesNotMatch(await page.locator("#project-context").textContent(), /secret-token-synthetic|private-project-id/);
    });
    await t.test("button focus and mobile layout remain usable with a long project name", async () => {
      await page.evaluate(() => document.getElementById("project-select").selectedOptions[0].textContent = "一个很长的项目名称".repeat(12));
      await expected(selected("一个很长的项目名称".repeat(12)), "选择或切换项目");
      await page.setViewportSize({width: 390, height: 844}); await page.evaluate(() => selectWorkspace("resources"));
      await page.locator('[data-tab="resources"]').focus(); await page.keyboard.press("Tab"); await focus("project-context-open");
      assert.notEqual(await button.evaluate(el => getComputedStyle(el).outlineStyle), "none");
      const layout = await page.locator("#project-context").evaluate(el => ({width: el.getBoundingClientRect().width, scroll: el.scrollWidth, height: el.getBoundingClientRect().height}));
      assert.ok(layout.scroll <= layout.width + 1); assert.ok(layout.height > 42);
      assert.equal(await button.isVisible(), true);
      await page.setViewportSize({width: 1280, height: 720});
    });
    await t.test("capture project context in resources with synthetic data", async () => {
      if (process.env.PROJECT_CONTEXT_EVIDENCE_DIR) {
        fs.mkdirSync(process.env.PROJECT_CONTEXT_EVIDENCE_DIR, {recursive: true});
        await page.evaluate(() => document.getElementById("project-select").selectedOptions[0].textContent = "示例项目甲（合成）");
        await expected(selected("示例项目甲（合成）"), "选择或切换项目");
        await page.screenshot({path: path.join(process.env.PROJECT_CONTEXT_EVIDENCE_DIR, "resources.png"), fullPage: true});
      }
    });
    await t.test("no business action, real network request, or browser error occurred", async () => {
      assert.deepEqual(await page.evaluate(() => window.actions), []); assert.deepEqual(network, []); assert.deepEqual(errors, []);
      assert.equal(await page.locator("#workspace-nav button").count(), 3);
    });
  } finally {await browser.close();}
});
