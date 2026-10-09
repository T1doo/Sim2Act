# Report 展示晚回执候选修复

2026-10-09 集成状态：依据重新发布环境的明确授权，从远端开发基线
`cc368dbbda1e4452df64efcac76e184dafe65e6d` 快进集成候选
`bf939ac72298c4d0d5e6c94ed1e1aa0853eb2d7b` 至 `dev/f1-foundation`。
产品字节保持冻结点 `51487fd4787eae66f09f8ff2b01492d8f9c13503`。
本轮实际执行范围、日志和保留限制见[集成证据](../evidence/report-late-integration-20261009/README.md)。
以下候选发现及原复现说明保留为历史，不改变整体未验收状态。

原候选 `64576576bdbd0b811ecb875cd46ccbf302b5f686` 保留。平台复审在其
源码 `ffda5b00a9a1469b454728adb5a0005016cd0a55` 发现 P2：已被服务器接受的
`/checks` 响应延迟到同一应用关闭、重开及新历史返回之后，旧闭包只更新
共享 intent 和按钮，当前页面停留在 ALLOW，未显示 explanation。

此候选只修改现有 `report-manifest.js`。展示 definition/check 的请求结束后，
若原 DOM 已替换且当前仍是同身份、项目、应用及 fingerprint，当前页面重新
调用原 history 和 report-presentations GET。新内容通过现有严格 Run/version/
fence/result/patch/check 验证后绘制。旧闭包不绘制结果、不继续下一次 POST；
换应用或换身份不读取旧应用的受保护历史。失败清空原有受保护内容，反馈只
能归属于当前选择或本次回读自身清空的选择；显式重开可恢复已保存回执。

`tests/test_report_presentation_late_ui.py` 使用自有隔离夹具和实际 loopback
HTTP，先让服务器接受 POST，再扣住响应；通过现有产品页面及实际七个 JS
脚本操作。definition/check 各覆盖同应用 ABA、另一应用、实际 connect 身份
切换、撤权、当前 GET 失败及显式重试、已接受响应丢失、同上下文刷新替换
DOM。每例核对加载脚本 SHA256、无自动续写、无旧内容混入及非 delivery_graph
表不变（专门撤权例仅排除自身 grants 修改）。旧源码负对照使用测试实例的
既有静态路由替换，仅对自有夹具启用，不是产品输入或新产品接口。

在冻结源码 `51487fd4787eae66f09f8ff2b01492d8f9c13503` 的干净工作副本中，
沿用 README 的 Python 环境。创建自己的临时依赖与结果目录，复现新矩阵
及原两个 UI 回归：

```bash
repro_root=$(mktemp -d /tmp/your-owned-report-late-XXXXXX)
npm install --prefix "$repro_root/node" --cache "$repro_root/npm-cache" jsdom@30.1.2
LIVE=0 SIM2ACT_LIVE_ENABLED=false NODE_PATH="$repro_root/node/node_modules" \
  .venv/bin/pytest -q tests/test_report_presentation_late_ui.py \
  tests/test_report_presentation_ui.py tests/test_report_manifest_apps_ui.py \
  --basetemp="$repro_root/sqlite"
```

私有 Node 依赖为 jsdom 30.1.2。PostgreSQL 使用你自己的隔离测试数据库，
设置 `SIM2ACT_TEST_DATABASE_URL`；夹具创建并删除自己的 test schema。
旧负对照：用 `git show ffda5b00a9a1469b454728adb5a0005016cd0a55:src/sim2act/web/report-manifest.js`
保存至自有临时文件，然后设置 `SIM2ACT_PRESENTATION_JS_BASELINE` 指向该文件，
仅运行 `[same-checks]`；预期断言当前页面重新读取展示历史失败：

```bash
git show ffda5b00a9a1469b454728adb5a0005016cd0a55:src/sim2act/web/report-manifest.js > "$repro_root/old.js"
LIVE=0 SIM2ACT_LIVE_ENABLED=false NODE_PATH="$repro_root/node/node_modules" \
  SIM2ACT_PRESENTATION_JS_BASELINE="$repro_root/old.js" .venv/bin/pytest -q \
  'tests/test_report_presentation_late_ui.py::test_actual_late_receipt_current_page_readback[same-checks]' \
  --basetemp="$repro_root/old-negative"
```

核对输出并保存需要的证据后，删除自己创建的 `repro_root`；不要删除其他测试目录。

原契约、canonical 图、历史、权限和业务/模型边界不变。本轮是合成工程病例，
不是原生 Windows/Edge、后台轮询、真实任务 gold 或人工签收；PROJECT
仍 PENDING/BLOCKED_PARTIAL，实际材料 PENDING、整体 NOT_ACCEPTED、发布关闭。
原 PG resources-history Future10 秒及旧 DOM lost-check 6 秒问题继续 OPEN。
原测试断言及 Windows 900 / Edge 240 / Node 150 上限均保留；不重跑全量或
用以前 1591/2051 结果证明此修改。候选需平台复审后再决定是否进入 dev。
