# 历史 Report 的受限 text 展示草案复现

源码候选：`ffda5b00a9a1469b454728adb5a0005016cd0a55`。
基线：`cc368dbbda1e4452df64efcac76e184dafe65e6d`；独立分支
`dev/report-text-binding-20261008`。这是未验收工程候选，未合并 dev、未发布。

## 原页面复现

1. 使用已有权限打开原目录中的 canonical Report Manifest 应用。必须已经有
   一个来源、完成证据及输出都可核查的 `WAITING_APPROVAL` 历史 Run。
   本云环境未找到产品数据库或真实 Report 材料；默认没有 provider 时仍会
   `WAITING_RESOURCE`。不要为此启用 provider 或触发真实模型调用。
2. 历史区显示原 `text / decision`。点击“保存 text: decision → explanation
   展示草案”。页面通过原 derive/plan 接口取得确切图锚及保守 PROJECT
   计划，再把独立展示草案保存到原请求账本；它不改 canonical manifest/图。
3. 查看保存回执中的完整 patch fingerprint，再点击对应展示版本确认按钮。
   服务端对确切 Run/version/fence/result fingerprint、来源、权限、人工锁、
   项目成员、各图锚及计划 seal 重新验证。只读取得已有结果的 explanation。
4. 页面并列保留原 decision 与新 explanation。新值用 `textContent` 显示，
   即使输出字面量含 `<script>` 也不会解释为 HTML。丢失回执时用“原键恢复”
   按钮；冷浏览器重新打开只读恢复，不能自动提交新草案或新 Run。

`展示回读 PASS` 只证明历史结果字符串的有类型投影。原 PROJECT 队列仍为
`PENDING/BLOCKED_PARTIAL`；实际材料验证 `PENDING`，语义 `UNKNOWN`，人工
确认 `PENDING`，整体 `NOT_ACCEPTED`。完整 AT13/F2-T07 和发布均未完成。
原执行定义、schema、输入、计算结果、结果历史及权限保持。

## 合成工程测试

使用自有隔离 SQLite 测试资源；不连接产品数据库：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false .venv/bin/pytest -q \
  tests/test_report_presentations.py tests/test_report_text_binding_boundary.py
```

DOM 夹具另外需要私有目录中的 `jsdom@30.1.2`；不要修改全局 npm 配置：

```bash
npm install --prefix /tmp/sim2act-report-view-repro-node \
  --cache /tmp/sim2act-report-view-repro-node/cache \
  --ignore-scripts --no-audit --no-fund jsdom@30.1.2
LIVE=0 SIM2ACT_LIVE_ENABLED=false \
  NODE_PATH=/tmp/sim2act-report-view-repro-node/node_modules \
  .venv/bin/pytest -q tests/test_report_presentation_ui.py
```

该夹具先通过原离线 MockTransport 工具链保存手写合成 Report，然后运行实际
loopback HTTP、原产品 JS 和 jsdom。它验证原键恢复、两次持有真实响应后的
项目/身份上下文失效、冷读、脚本字面量安全与七份实际脚本 SHA-256。
它不是实际 Report 生产结果、真实任务 gold、通用 P-B、人工签收或原生浏览器。
新导航夹具关闭 interval 并在关闭前排空自身 HTTP/actions；不证明后台轮询。
原 Report 49 断言驱动与 Windows 900 / Edge 240 / Node 150 标准保持原样。

PostgreSQL 运行同一测试时仅将 `SIM2ACT_TEST_DATABASE_URL` 指向自己的临时
测试库，允许创建/删除随机 `test_*` schema。不能把它指向业务库。
本轮使用固定 PG 17.9 镜像、network none、无映射端口、自有私有 Unix socket。
真实已有库不需要新增表或 API DDL：本功能复用 `delivery_graph_requests`。

## API 最小顺序

- 原 `POST .../apps/{aid}/delivery-graph/derive`：candidate fingerprint + key。
- 原 `POST .../delivery-graph/plans`：图指纹、原 VIEW ID/revision/content
  fingerprint 的单项 changes，保留完整 PROJECT 范围和遗漏集合。
- `POST .../delivery-graph/report-presentations`：确切 candidate/graph/原
  plan key/native_outer_fingerprint，Run ID/version/fence/result fingerprint，
  独立 request_key，View 恰为 `{"component_ref":"text","output_field":"explanation"}`。
- `POST .../report-presentations/{definition_key}/checks`：确切
  `expected_patch_fingerprint` 与检查 request_key。
- `GET .../report-presentations`：当前授权与来源核验后的不可变草案/检查历史。

来源变更、撤权、图/成员/锁变化和 seal 损坏会阻止旧回执继续作为有效展示证据。
相同键不能改参数，错误精确版本确认不产生检查账本。其他组件、未知输出、
HTML/表达式字段与 bool 版本均拒绝。
