# 首次受限 CSV 使用核查

2026-10-07，独立 `dev/first-use-bounded-guide`，精确远端基线 `de907327dd5b3105c169008a9fe0c90dcc353a8b`。正常 fetch 的 FETCH_HEAD 与 ls-remote 一致；本地 origin/dev/f1-foundation 旧引用 e828 尚未移动，独立分支已按实际 FETCH_HEAD 快进对齐。没有改共享 dev/main 分支。

阅读 Installation/install_preflight、PBBoundedDeliveryStatus、F2 Plan/Log、ApplicationUsePlan、RegisteredRunQuickstart、V5 平台/阶段设计；仓库及 workspace .agents 未发现本任务适用 AGENTS.md/SKILL.md。主线 PG 报告超时工作不在本切片修改范围。

## 可体验缺口与改动

安装说明只给到 `demo.csv` 预览；普通用户尚需找到下方工程入口、核对精确版本、显式确认、创建实例、重新选择独立任务列，才产生持久 AppRun。资源输入是粘贴文本、顶部报告不是 CSV 入口、预览列不等于任务列、换列不等于换材料、冷页面使用入口与内部管理入口不同，这些实际操作此前散落在阶段文档。

新增 FirstUse.md 以当前真实按钮说明完整顺序；Installation 仅加入口链接。新增独立 scripts/first-use 两文件供开发者复核，不作为生产启动器。仅先创建自有临时 SQLite schema 和固定合成登录身份；项目/CSV/候选/版本/实例/Run/结果由真实页面事件和公开产品 HTTP 生成，无固定答案或候选种子。正常 Worker 注入 NeverProvider；任何模型入口调用都会断言失败。controller 不读 .env/环境 DSN/真实 token，不能激活 provider，不新建 PG 角色或部署；自动清理自己的线程/临时库。

## 实际通过与证据边界

[actual-ui-result.json](actual-ui-result.json)：空项目列表开始→项目→CSV文本→授权草案→真实预览30/2行→样本核查与人工确认内部 Release→独立实例→正常 Worker 两个不同 Run `amount=30/v1`、`quantity=15/v2`→新 JSDOM 会话读取两版。14 个断言实际 PASS；9 个明确用户意图 POST（含两次运行），冷请求全部 GET、0 POST，独立 cold Store 读到 1 draft、2 Run、2 result、3 Principal（合成用户、项目runtime、应用runtime）。PASS 只说明这个 SQLite/HTTP/JSDOM 路径，不代表生产安装/PG/Win11/真实浏览器像素。

两项既有离线真实 API 验证 PASS：`test_app_previews::test_new_input_new_result_and_persisted_history_without_model_or_business_write`；`test_registered_run_generation_http::test_http_server_generated_candidate_cold_new_input_no_permissions`。后者从真实成功来源保存草案后 cold Store/新输入得到15，不复制旧来源4.00、无新增授权。不是报告/完整P-B验收。

未改预检实现，原13项 unittest 全通过，见 install-preflight-tests.log。演示Python Ruff、Node语法、diff whitespace PASS；新演示缺JSDOM明确BLOCKED，见 missing-jsdom-result.json。没有扩大产品依赖或变更 lock；开发工具单独位于 `/workspace/Sim2Act-first-use-node`，Node24.19.0、jsdom26.1.0、playwright-core1.63.0，Python3.12.14/隔离31项Linux lock环境，实际 import 由 PYTHONPATH 指向当前src。

可复跑开发核查：

```bash
NODE_PATH=/自己的开发工具/node_modules PYTHONPATH=src python scripts/first-use/offline_verify.py --output /tmp/first-use-result.json
```

输出缺开发依赖为 BLOCKED，真实断言失败为 FAIL；从未将缺工具报告为 PASS。脚本不自动安装软件，普通用户页面体验不需要 Node/JSDOM。

## 保留的失败与未测

- 新驱动第一次 FAIL 在 amount 阶段：等待了错误文本标记/任务读取完成条件不足；第二次 FAIL 在 quantity 阶段：前一次刷新尚 busy 时提交被禁用，驱动须等真实操作完成。两个原始失败 JSON 保留。均修驱动等待，未改产品按钮或后端。第三次页面全路径成功但controller断言 Principal应为2导致FAIL；查明正常项目runtime+应用runtime+合成用户是3，修独立oracle。第三次只有运行记录，不保留原始JSON，不冒称原始artifact完备。
- 既有三项 focused 测试实跑 **2 PASS、1 FAIL**，见 existing-focused.xml。失败为 `test_application_use_actual_http`；JSDOM driver关闭旧window后，旧异步回调调用 `document.getElementById`，document已不存在，Node exit1。原始driver stderr保留 existing-application-use-failure.log。没有修改原测试/产品逻辑，没有重跑它掩盖失败。独立新演示关闭窗口前停止自有页面timer并排空fetch；这只改善演示清理，不证明原生导航缺陷已修复，也不替代既有测试恢复/撤权负例。
- 受保护 Chromium 探测（chromiumSandbox=true）SUID helper配置导致 **BLOCKED**，见 protected-browser-probe.json。未绕过 sandbox、chmod/ACL、安全策略，未执行页面截图；浏览器/视觉NOT_RUN。
- 干净 PostgreSQL 普通安装、六PowerShell真实执行、本机身份CLI、PG角色/迁移、Win11、真实UI布局均NOT_RUN。没有签收完整P-B/F1/语义/owner/发布，也没有修主线90秒Report门。

开发目录内新npm安装初次因默认缓存不可用而失败，随后仅选择自有 `/tmp` cache 完成，未改HOME/全局cache权限；既有弃用提示保留，不升级产品lock或工具。演示只启动自己loopback API/Worker；没运行新CI/LIVE/部署或操作其它服务。

## 最终独立审查

独立最新复跑 [independent-ui-result.json](independent-ui-result.json) PASS：真实预览30/2行；两不同Run30/v1与15/v2；17个冷页面API请求全GET、0POST；fresh Store确认2Run/2结果；临时库/自有线程清理完成。最终文档只读审查确认schema/固定合成身份边界、真实按钮及安装补链均正确，失败与未测范围保留，无剩余文档/工具阻塞。独审没有修改文件。Mypy新增演示1文件PASS，Ruff演示+原预检+原测试PASS，Node/diff PASS。

artifact-hashes.json 覆盖本目录原始证据、指南、安装说明与两演示文件；不含自身。源码/测试/工作流没有更改，独立分支普通push不匹配仅监听dev/f1-foundation的CI。
