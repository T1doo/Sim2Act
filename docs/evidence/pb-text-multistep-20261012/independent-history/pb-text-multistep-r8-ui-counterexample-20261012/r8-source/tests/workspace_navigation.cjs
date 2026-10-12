"use strict";

// Only the navigation markup, empty workspace sections, CSS, and navigation
// functions are loaded. No application scripts, server, or database are used.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");

const web = path.join(__dirname, "../src/sim2act/web");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const app = fs.readFileSync(path.join(web, "app.js"), "utf8");
const css = fs.readFileSync(path.join(web, "app.css"), "utf8");
const ids = ["projects", "apps", "resources"];
const nav = html.match(/<nav id="workspace-nav"[^>]*>[\s\S]*?<\/nav>/)?.[0];
const select = app.match(/^function selectWorkspace\(id\) \{\n[\s\S]*?^\}/m)?.[0];
const initialize = app.match(/^document\.querySelectorAll\("#workspace-nav \[data-tab\]"\)\.forEach\([^\n]+\);\nselectWorkspace\("projects"\);$/m)?.[0];
assert.ok(nav && select && initialize, "extract the actual navigation implementation");
assert.doesNotMatch(select + initialize, /\b(?:api|fetch|import|require|setInterval)\b/);
const sections = ids.map(id => {
  const opening = html.match(new RegExp(`<section id="${id}"[^>]*>`))?.[0];
  assert.ok(opening, `find the ${id} workspace`);
  return opening + "</section>";
}).join("");
const fixture = `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>${css}</style></head><body>${nav}<main>${sections}</main></body></html>`;
const navigationScript = `const $ = id => document.getElementById(id);\n${select}\n${initialize}`;

test("isolated workspace navigation", async t => {
  const browser = await chromium.launch({
    executablePath: process.env.WORKSPACE_NAV_CHROMIUM || "/usr/bin/chromium",
    headless: true,
  });
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block"});
    const requests = [];
    await context.route("**/*", async route => {
      requests.push(route.request().url());
      await route.abort();
    });
    const page = await context.newPage();
    const errors = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setContent(fixture);
    const buttons = page.locator("#workspace-nav button");

    async function assertState(current) {
      const state = await page.evaluate(workspaces => ({
        buttons: Array.from(document.querySelectorAll("#workspace-nav button"), button => ({
          id: button.dataset.tab,
          current: button.getAttribute("aria-current"),
          controls: button.getAttribute("aria-controls"),
          type: button.type,
          tabIndex: button.tabIndex,
          role: button.getAttribute("role"),
        })),
        sections: workspaces.map(id => ({
          id,
          hidden: document.getElementById(id).hidden,
          display: getComputedStyle(document.getElementById(id)).display,
        })),
      }), ids);
      assert.deepEqual(state.buttons.map(button => button.id), ids);
      assert.equal(state.buttons.filter(button => button.current !== null).length, 1);
      for (const button of state.buttons) {
        assert.equal(button.current, button.id === current ? "true" : null);
        assert.equal(button.controls, button.id);
        assert.equal(button.type, "button");
        assert.equal(button.tabIndex, 0);
        assert.equal(button.role, null, "retain native button semantics");
      }
      for (const section of state.sections) {
        assert.equal(section.hidden, section.id !== current);
        assert.equal(section.display === "none", section.hidden);
      }
    }

    await t.test("HTML default and JavaScript initialization agree", async () => {
      await assertState("projects");
      // Start stale to prove initialization sets both visibility and current state.
      await page.evaluate(() => {
        document.querySelectorAll("#workspace-nav button").forEach(button => button.setAttribute("aria-current", "true"));
        document.getElementById("projects").hidden = true;
        document.getElementById("resources").hidden = false;
      });
      await page.addScriptTag({content: navigationScript});
      await assertState("projects");
    });

    await t.test("clicking each workspace keeps exactly one current item", async () => {
      for (const id of ["apps", "resources", "projects", "projects"]) {
        await page.locator(`[data-tab="${id}"]`).click();
        await assertState(id);
      }
    });

    await t.test("Tab, Enter, Space, and Shift+Tab retain native behavior", async () => {
      await buttons.nth(0).focus();
      await page.keyboard.press("Tab");
      assert.equal(await buttons.nth(1).evaluate(button => button === document.activeElement), true);
      await page.keyboard.press("Enter");
      await assertState("apps");
      await page.keyboard.press("Tab");
      assert.equal(await buttons.nth(2).evaluate(button => button === document.activeElement), true);
      await page.keyboard.press("Space");
      await assertState("resources");
      await page.keyboard.press("Shift+Tab");
      await page.keyboard.press("Shift+Tab");
      assert.equal(await buttons.nth(0).evaluate(button => button === document.activeElement), true);
      await page.keyboard.press("Enter");
      await assertState("projects");
    });

    await t.test("existing programmatic navigation shares current state", async () => {
      for (const id of ["resources", "apps", "projects"]) {
        await page.evaluate(workspace => selectWorkspace(workspace), id);
        await assertState(id);
      }
    });

    await t.test("current styling is distinct and keyboard focus stays visible", async () => {
      await buttons.nth(0).focus();
      await page.keyboard.press("Tab");
      await page.keyboard.press("Enter");
      const styles = await buttons.evaluateAll(items => items.map(button => {
        const style = getComputedStyle(button);
        return {background: style.backgroundColor, decoration: style.textDecorationLine, outline: style.outlineStyle};
      }));
      assert.notEqual(styles[0].background, styles[1].background);
      assert.equal(styles[1].decoration, "underline");
      assert.notEqual(styles[1].outline, "none");
      await assertState("apps");
    });

    await t.test("fixture performed no network requests and raised no browser errors", () => {
      assert.deepEqual(requests, []);
      assert.deepEqual(errors, []);
    });
  } finally {
    await browser.close();
  }
});
