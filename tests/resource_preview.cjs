"use strict";

// Execute only the existing API/row adapters and saved-resource UI controllers.
// HTTP is synthetic; no identity/business modules or backend fixtures load.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const app = fs.readFileSync(path.join(__dirname, "../src/sim2act/web/app.js"), "utf8");
const api = app.match(/^async function api\([^\n]*\) \{\n[\s\S]*?^\}/m)?.[0];
const safe = app.match(/^const safe = [^\n]+;/m)?.[0];
const row = app.match(/^function row\([^\n]*\) \{\n[\s\S]*?^\}/m)?.[0];
const controls = app.match(/^let resourceDownloadGeneration = 0;\n[\s\S]*?^\$\("project-select"\)\.addEventListener\("change", [^\n]+;/m)?.[0];
assert.ok(api && safe && row && controls);
assert.match(app, /^function clearIdentityView\(\) \{\n  invalidateResourcePreview\(\);/m);
assert.doesNotMatch(controls, /\b(?:refresh|showRun|proof|rederive|grant)\s*\(/);
const A = {id: "res-A", project_id: "project-A", name: "材料 A", format: "txt", content: "中文 A\r\n", hash: "0123456789abcdef"};
const B = {...A, id: "res-B", name: "材料 B", format: "md", content: "# 中文 B\n<script>window.contentExecuted=true</script>"};

test("isolated saved-resource preview", async t => {
  const browser = await chromium.launch({
    executablePath: process.env.RESOURCE_PREVIEW_CHROMIUM || "/usr/bin/chromium",
    headless: true,
  });
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block"});
    const requests = [], errors = [], downloads = [];
    await context.route("**/*", async route => {
      requests.push(route.request().url()); await route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.on("pageerror", error => errors.push(error.message));
    page.on("download", download => downloads.push(download));
    await page.setContent('<!doctype html><html lang="zh-CN"><body><select id="project-select"><option value="project-A">项目 A</option><option value="project-B">项目 B</option></select><p id="error" role="alert"></p><div id="materials"></div><pre id="resource-preview" hidden></pre></body></html>');
    await page.addScriptTag({content: `
      const $ = id => document.getElementById(id);
      let token = "identity-A", identityConnectionGeneration = 1;
      window.reads = []; window.tasks = []; window.contentExecuted = false;
      window.fetch = (url, options) => new Promise((resolve, reject) => {
        window.reads.push({url, method: options.method, auth: options.headers.Authorization, body: options.body ?? null, resolve, reject});
      });
      ${api}
      ${safe}
      ${row}
      ${controls}
      window.switchIdentity = identity => {
        token = identity; identityConnectionGeneration++;
        // This is the verified first statement of the real identity-clear hook.
        invalidateResourcePreview();
      };
      window.renderRows = resources => {
        $("materials").replaceChildren(...resources.map(resourceMaterialRow));
        $("materials").querySelectorAll(".row").forEach(div => {
          const button = div.querySelector("button"), handler = button.onclick;
          button.onclick = event => {
            const task = handler(event); window.tasks.push(task); return task;
          };
        });
      };
    `});
    async function reset() {
      await page.evaluate(resources => {
        window.switchIdentity("identity-A");
        $("project-select").value = "project-A";
        $("project-select").dispatchEvent(new Event("change"));
        $("error").textContent = "";
        window.reads = []; window.tasks = [];
        window.renderRows(resources);
      }, [A, B]);
    }
    const view = index => page.getByRole("button", {name: "查看", exact: true}).nth(index).click();
    async function finish(index, resource, {status = 200, raw, transportError} = {}) {
      await page.evaluate(async ({index, resource, status, raw, transportError}) => {
        const read = window.reads[index];
        if (transportError) read.reject(Error(transportError));
        else read.resolve(new Response(raw === undefined ? JSON.stringify(resource) : raw, {status}));
        await window.tasks[index];
      }, {index, resource, status, raw, transportError});
    }
    async function assertPreview(content = null, error) {
      assert.equal(await page.locator("#resource-preview").textContent(), content ?? "");
      assert.equal(await page.locator("#resource-preview").isHidden(), content === null);
      if (error !== undefined) assert.equal(await page.locator("#error").textContent(), error);
    }

    await t.test("each explicit view re-reads through GET and renders only current plain text", async () => {
      await reset();
      assert.equal(await page.evaluate(() => window.reads.length), 0);
      await view(0); await assertPreview(); await finish(0, A); await assertPreview(A.content, "");
      await view(0); await assertPreview();
      const fresh = {...A, content: "当前新内容\n"};
      await finish(1, fresh); await assertPreview(fresh.content, "");
      assert.deepEqual(await page.evaluate(() => window.reads.map(({url, method, auth, body}) => ({url, method, auth, body}))), [
        {url: "/api/resources/res-A", method: "GET", auth: "Bearer identity-A", body: null},
        {url: "/api/resources/res-A", method: "GET", auth: "Bearer identity-A", body: null},
      ]);
      await view(1); await finish(2, B); await assertPreview(B.content);
      assert.equal(await page.locator("#resource-preview script").count(), 0);
    });

    await t.test("slow A cannot overwrite fast B after a newer view intent", async () => {
      await reset(); await view(0); await view(1);
      await finish(1, B); await assertPreview(B.content, "");
      await finish(0, A); await assertPreview(B.content, "");
    });

    await t.test("same-resource repeated views also reject older content", async () => {
      await reset(); await view(0); await view(0);
      const latest = {...A, content: "latest version"};
      await finish(1, latest); await finish(0, A); await assertPreview(latest.content, "");
    });

    await t.test("older denial and transport failure cannot clear or replace the latest result/error feedback", async () => {
      for (const oldError of ["PERMISSION_DENIED", "transport"]) {
        await reset(); await view(0); await view(1); await finish(1, B);
        await page.locator("#error").evaluate(element => element.textContent = "new context feedback");
        if (oldError === "transport") await finish(0, null, {transportError: "old transport failure"});
        else await finish(0, {error: {code: oldError}}, {status: 403});
        await assertPreview(B.content, "new context feedback");
      }
    });

    await t.test("a newer failed view stays empty even when an older success arrives", async () => {
      await reset(); await view(0); await view(1);
      await finish(1, {error: {code: "PERMISSION_DENIED"}}, {status: 403});
      await assertPreview(null, "PERMISSION_DENIED");
      await finish(0, A); await assertPreview(null, "PERMISSION_DENIED");
    });

    await t.test("project changes clear displayed content immediately and discard late success including round trips", async () => {
      for (const roundTrip of [false, true]) {
        await reset(); await view(0); await finish(0, A); await view(1);
        await page.locator("#project-select").selectOption("project-B");
        await assertPreview();
        if (roundTrip) await page.locator("#project-select").selectOption("project-A");
        await finish(1, B); await assertPreview();
      }
    });

    await t.test("identity changes/reconnections clear immediately and discard late success including round trips", async () => {
      for (const identities of [["identity-B"], ["identity-B", "identity-A"], ["identity-A"]]) {
        await reset(); await view(0); await finish(0, A); await view(1);
        for (const identity of identities) {
          await page.evaluate(identity => window.switchIdentity(identity), identity);
          await assertPreview();
        }
        await finish(1, B); await assertPreview();
      }
    });

    await t.test("explicit identity-view clearing invalidates an in-flight preview even if identity values stay equal", async () => {
      await reset(); await view(0);
      await page.evaluate(() => invalidateResourcePreview());
      await finish(0, A); await assertPreview();
    });

    await t.test("stale rows and absent identity/project cause zero requests and preserve newer feedback", async () => {
      for (const change of ["project", "identity", "empty-identity", "empty-project"]) {
        await reset();
        await page.evaluate(change => {
          if (change === "project") {$("project-select").value = "project-B"; $("project-select").dispatchEvent(new Event("change"));}
          if (change === "identity") window.switchIdentity("identity-B");
          if (change === "empty-identity") window.switchIdentity("");
          if (change === "empty-project") {$("project-select").value = ""; $("project-select").dispatchEvent(new Event("change"));}
          $("resource-preview").textContent = "new authorized context result";
          $("resource-preview").hidden = false;
          $("error").textContent = "new context feedback";
        }, change);
        await view(0); await assertPreview("new authorized context result", "new context feedback");
        assert.equal(await page.evaluate(() => window.reads.length), 0);
      }
    });

    await t.test("current denial, retirement, HTTP errors, corrupt JSON and transport failure hide the current preview", async () => {
      const cases = [
        {resource: {error: {code: "PERMISSION_DENIED"}}, status: 403},
        {resource: {error: {code: "RESOURCE_UNAVAILABLE"}}, status: 410},
        {resource: {error: {code: "REQUEST_FAILED"}}, status: 500},
        {raw: "not-json"}, {transportError: "current transport failure"},
      ];
      for (const {resource = A, ...options} of cases) {
        await reset(); await view(0); await finish(0, A);
        await view(0); await assertPreview(); await finish(1, resource, options);
        await assertPreview(); assert.notEqual(await page.locator("#error").textContent(), "");
        assert.equal(await page.evaluate(() => window.reads.length), 2);
      }
    });

    await t.test("bad response ID, project, format and non-string content never display", async () => {
      for (const resource of [null, {}, {...A, id: "res-wrong"}, {...A, project_id: "project-B"},
        {...A, format: "html"}, {...A, content: null}, {...A, content: {text: "wrong"}}]) {
        await reset(); await view(0); await finish(0, resource);
        await assertPreview(null, "材料响应无效，未显示预览");
      }
    });

    await t.test("late bad responses after identity/project switches cannot erase new preview or feedback", async () => {
      for (const change of ["identity", "project"]) {
        await reset(); await view(0);
        await page.evaluate(change => {
          if (change === "identity") window.switchIdentity("identity-B");
          else {$("project-select").value = "project-B"; $("project-select").dispatchEvent(new Event("change"));}
          $("resource-preview").textContent = "new result"; $("resource-preview").hidden = false;
          $("error").textContent = "new feedback";
        }, change);
        await finish(0, {error: {code: "PERMISSION_DENIED"}}, {status: 403});
        await assertPreview("new result", "new feedback");
      }
    });

    await t.test("all preview work stays offline and creates no download, execution or browser error", async () => {
      assert.deepEqual(requests, []); assert.deepEqual(errors, []); assert.deepEqual(downloads, []);
      assert.equal(await page.evaluate(() => window.contentExecuted), false);
    });
  } finally {
    await browser.close();
  }
});
