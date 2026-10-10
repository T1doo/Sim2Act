"use strict";

// Only the existing API adapter/row helper and new download control execute.
// fetch is synthetic; no business modules, services, grants or database fixtures load.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const app = fs.readFileSync(path.join(__dirname, "../src/sim2act/web/app.js"), "utf8");
const api = app.match(/^async function api\([^\n]*\) \{\n[\s\S]*?^\}/m)?.[0];
const safe = app.match(/^const safe = [^\n]+;/m)?.[0];
const row = app.match(/^function row\([^\n]*\) \{\n[\s\S]*?^\}/m)?.[0];
const downloadControl = app.match(/^let resourceDownloadGeneration = 0;\n[\s\S]*?^\$\("project-select"\)\.addEventListener\("change", [^\n]+;/m)?.[0];
assert.ok(api && safe && row && downloadControl, "extract only resource download code and its existing adapters");
assert.doesNotMatch(downloadControl, /\b(?:refresh|showRun|proof|rederive|grant)\s*\(/);
const RESOURCE = {id: "res-synthetic", project_id: "project-A", name: "中文材料", format: "txt", content: "中文原文\r\n第二行\n", hash: "0123456789abcdef"};

test("isolated authorized resource download", async t => {
  const evidence = fs.mkdtempSync(path.join(os.tmpdir(), "sim2act-resource-download-"));
  console.log(`Downloaded byte evidence: ${evidence}`);
  const browser = await chromium.launch({
    executablePath: process.env.RESOURCE_DOWNLOAD_CHROMIUM || "/usr/bin/chromium",
    headless: true,
  });
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block", acceptDownloads: true});
    const requests = [];
    await context.route("**/*", async route => {
      requests.push(route.request().url());
      await route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    const downloads = [];
    const errors = [];
    page.on("download", download => downloads.push(download));
    page.on("pageerror", error => errors.push(error.message));
    await page.setContent('<!doctype html><html lang="zh-CN"><body><select id="project-select"><option value="project-A">A</option><option value="project-B">B</option></select><p id="error" role="alert"></p><div id="materials"></div><pre id="resource-preview" hidden></pre></body></html>');
    await page.addScriptTag({content: `
      const $ = id => document.getElementById(id);
      let token = "identity-A", identityConnectionGeneration = 1;
      window.readCalls = []; window.blobs = []; window.contentExecuted = false;
      window.fetch = (url, options) => {
        window.readCalls.push({url, method: options.method, auth: options.headers.Authorization, body: options.body ?? null});
        return window.syntheticRead(url, options);
      };
      const createURL = URL.createObjectURL.bind(URL), revokeURL = URL.revokeObjectURL.bind(URL);
      URL.createObjectURL = blob => {
        const url = createURL(blob); window.blobs.push({url, blob, revoked: false}); return url;
      };
      URL.revokeObjectURL = url => {
        const entry = window.blobs.find(item => item.url === url);
        if (entry) entry.revoked = true;
        revokeURL(url);
      };
      const nativeClick = HTMLAnchorElement.prototype.click;
      HTMLAnchorElement.prototype.click = function () {
        if (window.failDownloadClick) throw Error("synthetic file-save failure");
        return nativeClick.call(this);
      };
      ${api}
      ${safe}
      ${row}
      ${downloadControl}
    `});

    async function configure({resource = RESOURCE, metadata = resource, status = 200, body, deferred = false, transportError = false} = {}) {
      await page.evaluate(({resource, metadata, status, body, deferred, transportError}) => {
        token = "identity-A"; identityConnectionGeneration++;
        $("project-select").value = "project-A";
        $("project-select").dispatchEvent(new Event("change"));
        $("error").textContent = ""; window.readCalls = [];
        window.failDownloadClick = false;
        window.fixtureMetadata = metadata;
        window.syntheticResponse = () => new Response(body === undefined ? JSON.stringify(resource) : body, {status});
        window.syntheticRead = () => {
          if (transportError) return Promise.reject(Error("synthetic connection failure"));
          if (deferred) return new Promise(resolve => {window.finishRead = () => resolve(window.syntheticResponse());});
          return Promise.resolve(window.syntheticResponse());
        };
        $("materials").replaceChildren(resourceMaterialRow(metadata));
      }, {resource, metadata, status, body, deferred, transportError});
    }
    const button = () => page.getByRole("button", {name: "下载文件", exact: true});
    async function clean() {
      await page.waitForFunction(() => resourceDownloadRequests.size === 0 && window.blobs.every(item => item.revoked));
      assert.equal(await page.locator('a[download]').count(), 0);
      assert.equal(await page.evaluate(() => window.contentExecuted), false);
    }
    async function successfulDownload(resource, label) {
      const pending = page.waitForEvent("download");
      await button().click();
      const saved = await pending;
      assert.equal(saved.suggestedFilename(), `sim2act-resource.${resource.format}`);
      assert.equal(await saved.failure(), null);
      const destination = path.join(evidence, `${label}.${resource.format}`);
      await saved.saveAs(destination);
      assert.deepEqual(fs.readFileSync(destination), Buffer.from(resource.content, "utf8"));
      await clean();
      assert.equal(await button().isEnabled(), true);
    }
    async function noDownload() {
      const count = downloads.length, blobs = await page.evaluate(() => window.blobs.length);
      await button().click();
      await clean();
      assert.equal(downloads.length, count);
      assert.equal(await page.evaluate(() => window.blobs.length), blobs);
    }

    await t.test("row rendering makes no request or automatic download; view still reads the saved text", async () => {
      await configure();
      assert.equal(await page.evaluate(() => window.readCalls.length), 0);
      assert.equal(downloads.length, 0);
      await page.getByRole("button", {name: "查看", exact: true}).click();
      await page.waitForFunction(() => !document.getElementById("resource-preview").hidden);
      assert.equal(await page.locator("#resource-preview").textContent(), RESOURCE.content);
      assert.equal(downloads.length, 0);
    });

    await t.test("TXT, MD, CSV and JSON download exact UTF-8 bytes with Chinese and original line endings", async () => {
      const contents = {
        txt: "中文😀\r\n第二行\n末尾\r\n",
        md: "\ufeff# 中文成果\r\n<script>window.contentExecuted=true</script>\n",
        csv: '名称,值\r\n中文,"=1+1"\r\n',
        json: '{\r\n  "中文": "<script>window.contentExecuted=true</script>",\n  "值": 1\r\n}\n',
      };
      for (const [format, content] of Object.entries(contents)) {
        const resource = {...RESOURCE, format, content};
        await configure({resource});
        await successfulDownload(resource, `original-${format}`);
        const calls = await page.evaluate(() => window.readCalls);
        assert.deepEqual(calls, [{url: `/api/resources/${RESOURCE.id}`, method: "GET", auth: "Bearer identity-A", body: null}]);
        assert.equal(await page.evaluate(() => window.blobs.at(-1).blob.type), "text/plain;charset=utf-8");
      }
    });

    await t.test("each later explicit download re-reads the resource instead of exporting cached content", async () => {
      await configure();
      await successfulDownload(RESOURCE, "fresh-first");
      const changed = {...RESOURCE, content: "服务器当前返回的新内容\n"};
      await page.evaluate(resource => window.syntheticRead = async () => new Response(JSON.stringify(resource), {status: 200}), changed);
      await successfulDownload(changed, "fresh-second");
      assert.equal(await page.evaluate(() => window.readCalls.length), 2);
    });

    await t.test("repeated clicks and rerendered rows share one in-flight read", async () => {
      await configure({deferred: true});
      await button().click();
      assert.equal(await page.getByRole("button", {name: "正在读取…", exact: true}).isDisabled(), true);
      await page.evaluate(async () => {
        const pending = $("materials").querySelector('button[type="button"]');
        await pending.onclick(new Event("click"));
        $("materials").replaceChildren(resourceMaterialRow(window.fixtureMetadata));
      });
      await button().click();
      assert.equal(await page.evaluate(() => window.readCalls.length), 1);
      const pending = page.waitForEvent("download");
      await page.evaluate(() => window.finishRead());
      const saved = await pending;
      await saved.saveAs(path.join(evidence, "single-in-flight.txt"));
      assert.deepEqual(fs.readFileSync(path.join(evidence, "single-in-flight.txt")), Buffer.from(RESOURCE.content, "utf8"));
      await clean();
    });

    await t.test("identity/project changes including switching away and back discard late success", async () => {
      for (const change of ["identity", "identity-back", "project", "project-back"]) {
        await configure({deferred: true});
        const count = downloads.length, blobs = await page.evaluate(() => window.blobs.length);
        await button().click();
        await page.evaluate(change => {
          if (change.startsWith("identity")) {
            token = "identity-B"; identityConnectionGeneration++;
            if (change.endsWith("back")) {token = "identity-A"; identityConnectionGeneration++;}
          } else {
            $("project-select").value = "project-B";
            $("project-select").dispatchEvent(new Event("change"));
            if (change.endsWith("back")) {
              $("project-select").value = "project-A";
              $("project-select").dispatchEvent(new Event("change"));
            }
          }
          window.finishRead();
        }, change);
        await clean();
        assert.equal(downloads.length, count);
        assert.equal(await page.evaluate(() => window.blobs.length), blobs);
      }
    });

    await t.test("stale material rows and missing identity/project make no GET or download", async () => {
      for (const change of ["project", "identity", "missing-project"]) {
        await configure();
        await page.evaluate(change => {
          if (change === "identity") token = "";
          else $("project-select").value = change === "project" ? "project-B" : "";
        }, change);
        await noDownload();
        assert.equal(await page.evaluate(() => window.readCalls.length), 0);
      }
    });

    await t.test("retirement, permission denial, HTTP errors, broken JSON and transport failure never download or retry", async () => {
      const cases = [
        {status: 403, body: JSON.stringify({error: {code: "PERMISSION_DENIED"}})},
        {status: 410, body: JSON.stringify({error: {code: "RESOURCE_UNAVAILABLE"}})},
        {status: 500, body: JSON.stringify({error: {code: "REQUEST_FAILED"}})},
        {body: "not-json"}, {transportError: true},
      ];
      for (const options of cases) {
        await configure(options);
        await noDownload();
        assert.equal(await page.evaluate(() => window.readCalls.length), 1);
        assert.notEqual(await page.locator("#error").textContent(), "");
        assert.equal(await button().isEnabled(), true);
      }
    });

    await t.test("invalid response identity, project, format and content produce zero downloads", async () => {
      for (const resource of [null, {}, {...RESOURCE, id: "wrong"}, {...RESOURCE, project_id: "project-B"},
        {...RESOURCE, format: "html"}, {...RESOURCE, format: "../exe"}, {...RESOURCE, format: "TXT"},
        {...RESOURCE, content: null}, {...RESOURCE, content: {text: "wrong"}}]) {
        await configure({resource, metadata: RESOURCE});
        await noDownload();
        assert.equal(await page.locator("#error").textContent(), "材料响应无效，未下载文件");
      }
    });

    await t.test("late denial preserves new-context feedback and creates no Blob", async () => {
      await configure({deferred: true, status: 403, body: JSON.stringify({error: {code: "PERMISSION_DENIED"}})});
      const count = downloads.length, blobs = await page.evaluate(() => window.blobs.length);
      await button().click();
      await page.evaluate(() => {
        token = "identity-B"; identityConnectionGeneration++;
        $("error").textContent = "new context feedback";
        window.finishRead();
      });
      await clean();
      assert.equal(downloads.length, count);
      assert.equal(await page.evaluate(() => window.blobs.length), blobs);
      assert.equal(await page.locator("#error").textContent(), "new context feedback");
    });

    await t.test("dangerous names cannot select paths or executable extensions and content remains inert", async () => {
      const resource = {...RESOURCE, name: '../CON\\..\\evil.exe\u202e.html\n<script>window.contentExecuted=true</script>', format: "txt", content: '<script>window.contentExecuted=true</script>\n'};
      await configure({resource});
      await successfulDownload(resource, "dangerous-name");
      assert.equal(await page.locator("#materials script").count(), 0);
    });

    await t.test("failed local download activation still cleans the anchor and Blob URL", async () => {
      await configure();
      await page.evaluate(() => window.failDownloadClick = true);
      const count = downloads.length;
      await button().click();
      await clean();
      assert.equal(downloads.length, count);
      assert.equal(await page.locator("#error").textContent(), "synthetic file-save failure");
      assert.equal(await button().isEnabled(), true);
    });

    await t.test("fixture made no real network request, leaked no Blob URL and raised no browser errors", async () => {
      await clean();
      assert.deepEqual(requests, []);
      assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => window.blobs.every(item => item.revoked)), true);
    });
  } finally {
    await browser.close();
  }
});
