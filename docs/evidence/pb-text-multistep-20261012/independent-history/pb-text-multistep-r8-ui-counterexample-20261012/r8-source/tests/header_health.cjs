"use strict";

// Extract only health control and polling orchestration. All business callbacks
// are synthetic; no application modules, service, database, or network is loaded.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const web = path.join(__dirname, "../src/sim2act/web");
const app = fs.readFileSync(path.join(web, "app.js"), "utf8");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const sampler = app.match(/^function createHealthSampler\(render\) \{\n[\s\S]*?^\}/m)?.[0];
const polling = app.match(/^const sampleHealth = createHealthSampler[^\n]*;\nlet backgroundRefreshInFlight=false;\nsetInterval\([\s\S]*?^\},2500\);/m)?.[0];
const output = html.match(/<output id="health"[^>]*>[\s\S]*?<\/output>/)?.[0];
const error = html.match(/<p id="error"[^>]*><\/p>/)?.[0];
assert.ok(sampler && polling && output && error, "extract only actual health control and output");
assert.doesNotMatch(sampler, /\b(?:api|refresh|showRun|fetch)\s*\(/);
const HEALTH = {mode: "MOCK", api: "UP", worker: "UP"};
const SUCCESS = "健康检查：MOCK · API UP · worker UP";
const FAILURE = "后台健康检查失败";

test("isolated header health status", async t => {
  const browser = await chromium.launch({
    executablePath: process.env.HEADER_HEALTH_CHROMIUM || "/usr/bin/chromium",
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
    await page.setContent(`<!doctype html><html lang="zh-CN"><body><header>${output}</header>${error}<p id="synthetic-business-status"></p></body></html>`);
    await page.addScriptTag({content: `
      const $ = id => document.getElementById(id);
      const token = "synthetic-identity", activeRun = "synthetic-run";
      const api = path => {
        if (path !== "/health") throw Error("Unexpected business request");
        window.calls.push("health"); return window.readHealth();
      };
      const refresh = () => window.refreshFixture();
      const showRun = (...args) => window.showRunFixture(...args);
      const setInterval = (callback, delay) => {
        window.backgroundTick = callback; window.pollDelay = delay;
      };
      ${sampler}
      ${polling}
    `});

    async function configure(options = {}) {
      await page.evaluate(({health, healthError, refreshError, runError}) => {
        window.calls = [];
        document.getElementById("health").textContent = "正在检查后台";
        document.getElementById("error").textContent = "";
        document.getElementById("synthetic-business-status").textContent = "";
        window.readHealth = async () => {
          if (healthError) throw Error(healthError);
          return health;
        };
        window.refreshFixture = async () => {
          window.calls.push("refresh");
          if (refreshError) {
            document.getElementById("synthetic-business-status").textContent = "specific business feedback retained";
            throw Error(refreshError);
          }
        };
        window.showRunFixture = async (...args) => {
          window.calls.push(["showRun", ...args]);
          if (runError) throw Error(runError);
        };
      }, {health: HEALTH, ...options});
    }
    const tick = () => page.evaluate(() => window.backgroundTick());
    const message = () => page.locator("#health").textContent();

    await t.test("health success with business refresh failure retains health and reports the error", async () => {
      await configure({refreshError: "synthetic refresh failure"});
      await tick();
      assert.equal(await message(), SUCCESS);
      assert.equal(await page.locator("#error").textContent(), "synthetic refresh failure");
      assert.equal(await page.locator("#synthetic-business-status").textContent(), "specific business feedback retained");
      assert.deepEqual(await page.evaluate(() => window.calls), ["health", "refresh"]);
    });

    await t.test("showRun failure also reports a business error without a false disconnect", async () => {
      await configure({runError: "synthetic run read failure"});
      await tick();
      assert.equal(await message(), SUCCESS);
      assert.equal(await page.locator("#error").textContent(), "synthetic run read failure");
      assert.deepEqual(await page.evaluate(() => window.calls), ["health", "refresh", ["showRun", "synthetic-run", false]]);
    });

    await t.test("health failure skips business callbacks and preserves existing business feedback", async () => {
      await configure({healthError: "synthetic health failure"});
      await page.locator("#error").evaluate(element => element.textContent = "previous business error");
      await tick();
      assert.equal(await message(), FAILURE);
      assert.equal(await page.locator("#error").textContent(), "previous business error");
      assert.deepEqual(await page.evaluate(() => window.calls), ["health"]);
    });

    await t.test("a later successful tick recovers health and retains the original polling behavior", async () => {
      await configure({healthError: "synthetic health failure"});
      await tick();
      assert.equal(await message(), FAILURE);
      await page.evaluate(health => {
        window.calls = [];
        window.readHealth = async () => health;
      }, HEALTH);
      await tick();
      assert.equal(await message(), SUCCESS);
      assert.deepEqual(await page.evaluate(() => window.calls), ["health", "refresh", ["showRun", "synthetic-run", false]]);
      assert.equal(await page.evaluate(() => window.pollDelay), 2500);
    });

    await t.test("invalid health payloads fail sampling while worker OFFLINE remains explicit", async () => {
      for (const health of [null, {}, {...HEALTH, api: "UNKNOWN"}, {...HEALTH, mode: "invalid"}]) {
        await configure({health});
        await tick();
        assert.equal(await message(), FAILURE);
        assert.deepEqual(await page.evaluate(() => window.calls), ["health"]);
      }
      await configure({health: {...HEALTH, worker: "OFFLINE"}});
      await tick();
      assert.equal(await message(), "健康检查：MOCK · API UP · worker OFFLINE");
    });

    await t.test("older asynchronous success or failure never overwrites newer state", async () => {
      for (const [oldFails, newFails] of [[false, false], [true, false], [false, true]]) {
        const result = await page.evaluate(async ({oldFails, newFails, health}) => {
          const messages = [];
          const sample = createHealthSampler(message => messages.push(message));
          let finishOld, rejectOld;
          const old = sample(() => new Promise((resolve, reject) => {
            finishOld = resolve; rejectOld = reject;
          }));
          const newer = await sample(async () => {
            if (newFails) throw Error("new synthetic failure");
            return {...health, mode: "LIVE"};
          });
          if (oldFails) rejectOld(Error("old synthetic failure"));
          else finishOld(health);
          return {messages, newer, old: await old};
        }, {oldFails, newFails, health: HEALTH});
        assert.deepEqual(result.messages, [newFails ? FAILURE : "健康检查：LIVE · API UP · worker UP"]);
        assert.equal(result.newer, !newFails);
        assert.equal(result.old, false);
      }
    });

    await t.test("health status has polite atomic screen reader semantics and errors keep alert semantics", async () => {
      const status = page.getByRole("status");
      assert.equal(await status.count(), 1);
      assert.equal(await status.getAttribute("aria-live"), "polite");
      assert.equal(await status.getAttribute("aria-atomic"), "true");
      assert.match(await status.ariaSnapshot(), /健康检查：MOCK · API UP · worker OFFLINE/);
      assert.equal(await page.getByRole("alert").count(), 1);
    });

    await t.test("fixture raised no browser errors and made no network requests", () => {
      assert.deepEqual(requests, []);
      assert.deepEqual(errors, []);
    });
  } finally {
    await browser.close();
  }
});
