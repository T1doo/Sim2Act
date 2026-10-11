"use strict";

// Load only the local reader/form controls. Save and receipt-recovery functions
// never execute; two unchanged draft-body expressions are evaluated without I/O.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const test = require("node:test");
const {chromium} = require("playwright-core");
const web = path.join(__dirname, "../src/sim2act/web");
const app = fs.readFileSync(path.join(web, "app.js"), "utf8");
const html = fs.readFileSync(path.join(web, "index.html"), "utf8");
const css = fs.readFileSync(path.join(web, "app.css"), "utf8");
const controls = app.match(/^"use strict";\n\/\/ Browser-local import;[\s\S]*?(?=^async function saveResourceMaterial\(\))/m)?.[0];
const form = html.match(/<form id="resource-form">[\s\S]*?<\/form>/)?.[0];
const bindings = [
  app.match(/^\$\("resource-file"\)\.onchange=selectResourceFile;$/m)?.[0],
  app.match(/^\$\("resource-file-clear"\)\.onclick=[^\n]+;$/m)?.[0],
  app.match(/^for\(const id of \["resource-name","format","content"\]\)[^\n]+;$/m)?.[0],
];
const original = app.match(/^  const original=file [^\n]+;$/m)?.[0];
const body = app.match(/^  const body=\{name:\$\("resource-name"\)[^\n]+;$/m)?.[0];
assert.ok(controls && form && original && body && bindings.every(Boolean));
assert.doesNotMatch(controls, /\b(?:api|fetch|refresh|saveResourceMaterial)\s*\(/);

test("isolated local text file reader", async t => {
  const evidence = process.env.LOCAL_TEXT_EVIDENCE_DIR || fs.mkdtempSync(path.join(os.tmpdir(), "sim2act-local-text-files-"));
  fs.mkdirSync(evidence, {recursive: true});
  console.log(`Screenshots: ${evidence}`);
  const browser = await chromium.launch({
    executablePath: process.env.LOCAL_TEXT_CHROMIUM || "/usr/bin/chromium",
    headless: true,
  });
  try {
    const context = await browser.newContext({offline: true, serviceWorkers: "block", viewport: {width: 1180, height: 1050}});
    const requests = [], errors = [];
    await context.route("**/*", async route => {
      requests.push(route.request().url()); await route.abort();
    });
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    page.on("pageerror", error => errors.push(error.message));
    await page.setContent(`<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><style>${css}</style></head><body><header><strong>Sim2Act</strong><span>本地材料预览 · 隔离界面示例</span></header><main><h1>资源 · 材料</h1><label>当前项目<select id="project-select"><option value="project-A">本地测试项目 A</option><option value="project-B">本地测试项目 B</option></select></label>${form}</main></body></html>`);
    await page.addScriptTag({content: `
      const $ = id => document.getElementById(id);
      let token = "synthetic-identity-A", identityConnectionGeneration = 1;
      window.networkAttempts = 0; window.submitAttempts = 0; window.contentExecuted = false;
      window.fetch = () => {window.networkAttempts++; throw Error("No network permitted");};
      window.NativeFileReader = window.FileReader;
      window.useControlledReader = () => {
        window.readers = [];
        window.FileReader = class {
          static LOADING = 1;
          readyState = 0;
          readAsArrayBuffer(file) {this.file = file; this.readyState = 1; window.readers.push(this);}
          abort() {this.readyState = 2; this.onabort?.();}
          succeed(bytes) {this.result = new Uint8Array(bytes).buffer; this.readyState = 2; this.onload?.();}
          fail() {this.readyState = 2; this.onerror?.();}
        };
      };
      ${controls}
      ${bindings.join("\n")}
      window.draftBody = () => {
        const file = resourceFileSnapshot;
        ${original}
        ${body}
        return body;
      };
      $("resource-form").addEventListener("submit", event => {event.preventDefault(); window.submitAttempts++;});
      renderResourceMaterial();
    `});
    async function reset(controlled = false) {
      await page.evaluate(controlled => {
        clearResourceMaterial();
        token = "synthetic-identity-A"; identityConnectionGeneration++;
        $("project-select").value = "project-A";
        window.FileReader = window.NativeFileReader;
        if (controlled) window.useControlledReader();
        renderResourceMaterial();
      }, controlled);
    }
    const select = (name, bytes) => page.locator("#resource-file").setInputFiles({name, mimeType: "application/octet-stream", buffer: Buffer.isBuffer(bytes) ? bytes : Buffer.from(bytes, "utf8")});
    async function finished() {
      await page.waitForFunction(() => !resourceFileReader && !document.getElementById("resource-file-status").textContent.startsWith("正在"));
    }
    async function draft() {
      return page.evaluate(() => ({
        name: $("resource-name").value, format: $("format").value, content: $("content").value,
        preview: $("resource-file-preview").textContent, hidden: $("resource-file-preview").hidden,
        status: $("resource-file-status").textContent, body: window.draftBody(),
      }));
    }

    await t.test("TXT, MD and JSON fill the native final-text draft and inert preview without saving", async () => {
      for (const [format, raw] of [
        ["txt", "中文😀\r\n第二行\n末行\r"],
        ["md", "# 中文报告\r\n<script>window.contentExecuted=true</script>\n"],
        ["json", '{\r\n  "中文": "文本",\n  "数值": 1\r\n}\n'],
      ]) {
        await reset(); await select(`中文材料.${format.toUpperCase()}`, raw); await finished();
        const state = await draft(), expected = raw.replace(/\r\n?/g, "\n");
        assert.equal(state.format, format); assert.equal(state.content, expected);
        assert.equal(state.preview, expected); assert.equal(state.body.content, expected);
        assert.equal(state.hidden, false); assert.match(state.status, /尚未保存或授权/);
        if (format === "json") assert.match(state.status, /JSON 语法已检查，保存仍需原校验/);
        assert.equal(await page.locator("#resource-file-preview script").count(), 0);
      }
    });

    await t.test("CSV keeps its original raw newline snapshot and unchanged draft-body path", async () => {
      await reset();
      const raw = "名称,值\r\n中文,2\r\n第二项,3\n";
      await select("原有路径.CSV", raw); await finished();
      const state = await draft();
      assert.equal(state.format, "csv"); assert.equal(state.content, raw.replace(/\r\n/g, "\n"));
      assert.equal(state.preview, raw); assert.equal(state.body.content, raw);
    });

    await t.test("TXT/MD preserve BOM in final text while CSV/JSON reject it", async () => {
      for (const format of ["txt", "md", "csv", "json"]) {
        await reset(); await select(`编码.${format}`, "\ufeff" + (format === "json" ? '{"中文":1}' : "中文\r\n")); await finished();
        const state = await draft();
        if (["txt", "md"].includes(format)) {
          assert.equal(state.content, "\ufeff中文\n"); assert.equal(state.preview, state.content);
        } else {
          assert.equal(state.content, ""); assert.equal(state.hidden, true); assert.match(state.status, /无 BOM/);
        }
      }
    });

    await t.test("empty, oversized, unsupported and excessive-name files fail before a local read", async () => {
      for (const [name, bytes] of [["empty.txt", ""], ["large.md", "x".repeat(32769)], ["bad.html", "text"], ["n".repeat(201) + ".txt", "text"]]) {
        await reset(true); await select(name, bytes);
        assert.equal(await page.evaluate(() => window.readers.length), 0);
        const state = await draft(); assert.equal(state.content, ""); assert.equal(state.hidden, true);
      }
      await reset(); await select("边界.txt", "a".repeat(32768)); await finished();
      assert.equal((await draft()).content.length, 32768);
    });

    await t.test("invalid UTF-8 and binary NUL bytes are rejected for every format", async () => {
      for (const format of ["txt", "md", "csv", "json"]) {
        for (const bytes of [Buffer.from([0xff, 0xfe, 0x41, 0]), Buffer.from([0x41, 0, 0x42])]) {
          await reset(); await select(`错误.${format}`, bytes); await finished();
          const state = await draft(); assert.equal(state.content, ""); assert.equal(state.hidden, true);
          assert.match(state.status, /UTF-8|空字节|二进制/);
        }
      }
      await reset(); await select("控制字符.txt", Buffer.from([65, 1, 66])); await finished();
      assert.match((await draft()).status, /二进制/);
    });

    await t.test("JSON syntax failures never fill or reformat the draft", async () => {
      for (const raw of ['{"x":}', '{"x": NaN}', '{"x":1,}', "// comment\n{}", "[".repeat(1000)]) {
        await reset(); await select("错误.json", raw); await finished();
        const state = await draft(); assert.equal(state.content, ""); assert.equal(state.hidden, true);
        assert.match(state.status, /JSON 语法无效/);
      }
    });

    await t.test("dangerous filenames and HTML-like content remain plain text", async () => {
      await reset();
      const name = '../<img src=x onerror="window.contentExecuted=true">.md';
      const raw = '<script>window.contentExecuted=true</script>\n<img src=x onerror="window.contentExecuted=true">';
      await select(name, raw); await finished();
      const state = await draft(); assert.equal(state.content, raw); assert.equal(state.preview, raw);
      assert.equal(await page.locator("#resource-form img").count(), 0);
      assert.equal(await page.evaluate(() => window.contentExecuted), false);
    });

    await t.test("cancel discards both late success and late failure", async () => {
      await reset(true); await select("旧.txt", "old");
      await page.locator("#resource-file-clear").click();
      await page.evaluate(() => {window.readers[0].succeed([79, 76, 68]); window.readers[0].fail();});
      const state = await draft(); assert.equal(state.content, ""); assert.equal(state.status, ""); assert.equal(state.hidden, true);
    });

    await t.test("new selection wins over late old success/failure and cancelled file selection clears", async () => {
      await reset(true); await select("旧.txt", "old"); await select("新.md", "new");
      await page.evaluate(() => {
        window.readers[1].succeed([78, 69, 87]);
        window.readers[0].succeed([79, 76, 68]); window.readers[0].fail();
      });
      let state = await draft(); assert.equal(state.name, "新.md"); assert.equal(state.content, "NEW");
      await page.locator("#resource-file").setInputFiles([]);
      state = await draft(); assert.equal(state.content, ""); assert.equal(state.hidden, true);
    });

    await t.test("editing name, format or text invalidates pending reads and detached snapshots", async () => {
      for (const field of ["resource-name", "format", "content"]) {
        await reset(true); await select("pending.txt", "old");
        await page.evaluate(field => {
          document.getElementById(field).value = field === "format" ? "md" : "user draft";
          document.getElementById(field).dispatchEvent(new Event("input", {bubbles: true}));
          window.readers[0].succeed([79, 76, 68]); window.readers[0].fail();
        }, field);
        assert.equal(await page.locator(`#${field}`).inputValue(), field === "format" ? "md" : "user draft");
        assert.equal((await draft()).hidden, true); assert.equal(await page.evaluate(() => resourceFileSnapshot), null);
      }
      await reset(); await select("已读.md", "original\r\n"); await finished();
      await page.locator("#content").fill("user final text\n");
      assert.equal((await draft()).body.content, "user final text\n"); assert.equal((await draft()).hidden, true);
    });

    await t.test("identity/project changes including switching away and back block late file results", async () => {
      for (const change of ["identity", "identity-back", "project", "project-back"]) {
        await reset(true); await select("旧.txt", "old");
        await page.evaluate(change => {
          if (change.startsWith("identity")) {
            token = "synthetic-identity-B"; identityConnectionGeneration++;
            if (change.endsWith("back")) {token = "synthetic-identity-A"; identityConnectionGeneration++;}
          } else {
            $("project-select").value = "project-B"; clearResourceMaterial();
            if (change.endsWith("back")) {$("project-select").value = "project-A"; clearResourceMaterial();}
          }
          $("content").value = "new context draft";
          $("resource-file-status").textContent = "new context feedback";
          window.readers[0].succeed([79, 76, 68]); window.readers[0].fail();
        }, change);
        const state = await draft(); assert.equal(state.content, "new context draft");
        assert.equal(state.status, "new context feedback"); assert.equal(state.hidden, true);
      }
    });

    await t.test("read errors, length mismatch, absent project and multiple files have local-only feedback", async () => {
      await reset(true); await select("failed.txt", "old"); await page.evaluate(() => window.readers[0].fail());
      assert.match((await draft()).status, /本地文件读取失败/);
      await reset(true); await select("mismatch.txt", "old"); await page.evaluate(() => window.readers[0].succeed([65]));
      assert.match((await draft()).status, /长度不一致/);
      await reset(true); await page.locator("#project-select").selectOption([]); await select("missing.txt", "old");
      assert.equal(await page.evaluate(() => window.readers.length), 0); assert.match((await draft()).status, /先选择项目/);
      await reset(true); await page.evaluate(() => {
        const files = new DataTransfer();
        files.items.add(new File(["A"], "a.txt")); files.items.add(new File(["B"], "b.md"));
        $("resource-file").files = files.files; selectResourceFile();
      });
      assert.equal(await page.evaluate(() => window.readers.length), 0); assert.match((await draft()).status, /一次只能选择一个/);
    });

    await t.test("actual preview screenshots and screen-reader status show local pending text", async () => {
      await reset(); await select("中文报告.md", "# 中文报告\r\n这是本地待保存的 Markdown 文本。\r\n\n- 没有上传\n- 没有授权\n"); await finished();
      assert.equal(await page.locator("#resource-file-status").getAttribute("aria-live"), "polite");
      assert.match(await page.getByRole("status").ariaSnapshot(), /尚未保存或授权/);
      await page.screenshot({path: path.join(evidence, "local-md-preview.png"), fullPage: true});
      await reset(); await select("中文数据.json", '{\r\n  "名称": "本地待保存",\r\n  "数值": 42\r\n}\n'); await finished();
      await page.screenshot({path: path.join(evidence, "local-json-preview.png"), fullPage: true});
    });

    await t.test("all reading stays offline, triggers zero submits and leaves content inert", async () => {
      assert.deepEqual(requests, []); assert.deepEqual(errors, []);
      assert.equal(await page.evaluate(() => window.networkAttempts), 0);
      assert.equal(await page.evaluate(() => window.submitAttempts), 0);
      assert.equal(await page.evaluate(() => window.contentExecuted), false);
    });
  } finally {
    await browser.close();
  }
});
