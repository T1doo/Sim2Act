# 修正回执直达新 Run（2026-10-18）

基线 `a7403b379b1278fd1be533ca21d790f0311244af`。此片交付实际页面入口：自然 P-A/P-B 原拒绝结果的受限修正被接受后，用户可点击「打开此修正Run，完成后独立复审」。不再必须手动刷新实例并在历史中寻找新 Run。

## 行为与边界

- 原 key GET 完整核对预览、声明和新 Run 回执后才显示入口；新增项目与 Run ID 检查。
- 不自动跳转。点击刷新同一实例，核对账号连接、项目/应用、工作区代次、实例/Run 选择代次，以及原 Release ID、指纹、revision 和新 Run 成员关系，再调用现有 `showInternalRun`。
- 已完成 Run 接入同一 Run 的现成人工状态读取；排队 Run 展示进度。没有自动冻结/接受、没有新 POST、executor、Grant 或权限。
- 迟到回执、迟到实例/Run 读取与中途导航不能继续旧选择；双击只发起一条本页导航。现有一次修正上限、durable intent 和后端权限/版本检查不变。

## 实际验证

本地 Linux / Node 24.19.0 / JSDOM，真实 HTML 与 app/internal/use/owner-review 控制器，合成 GET 响应；Switch/PBUse/logic 渲染器为 stub。不是完整 HTTP/Worker 或真实语义验证。

| 范围 | 结果 |
| --- | --- |
| 新 `correction_run_entry.cjs` | 24 检查 PASS：回执显式入口、精确 child、同 Run PENDING、QUEUED、不自动跳转、零 POST、防双击、账号/项目/工作区/实例/Run 导航和迟到隔离、错项目/Run 回执拒绝 |
| 新 pytest 包装 | 1 PASS，4.89s，JUnit 留存 |
| 既有 `natural_application_navigation.cjs` | 36 检查 PASS |
| JS 语法 / 新 Python Ruff / 源码与测试 diff --check | 全部 exit 0 |

首次新 Node 检查保留 19 检查后 FAIL 原文：测试曾在实例刷新已清空列表时直接调用不可达的 Run 选择；改为实例已呈现、Release GET 等待时实际可达的 Run 选择后通过。首次 pytest 包装继承旧 NODE_PATH，因缺 jsdom 在运行功能前失败；指定已安装 `/workspace/node-tools/node_modules` 后通过。无安装依赖或网络操作。原始失败 JUnit 中有3行尾空格，随原字节保留；加入原始证据后的全量 staged diff --check 因此报这3行，源码/测试/说明文档范围检查通过。

既有 `natural_spec_corrections_ui.cjs` 已换用新按钮和精确 Run 断言，**此次未重跑**其 HTTP/Worker 修正整链。没有重跑前序 7call 链或恢复矩阵。Windows、PG、远端 CI、原生浏览器、真实模型、真实场景/语义与真人验收均 NOT_RUN。

本次[原始证据与执行范围](../evidence/correction-run-entry-20261018/README.md)保存了完整记录；原始目录 `/workspace/correction-run-entry-20261018`，有限只读独审 `/workspace/correction-run-entry-review-20261018`。当前实例原始记录与封存清单见同目录，未从旧满盘实例恢复任何报告。

## 真实 source/controller 的独立核查

这里仍有项目实现缺口，不能归因为只缺 key、环境变量或持久权限：

1. `production_evidence.resolve_account` 固定在验证原合同要求后拒绝 `SOURCE_MISSING`，没有真实账户 producer/解析器。
2. `production_preflight` 先 `_approved` 再解析 source；source 缺失时未到软件资格检查、reservation 或发送。合成通过不能证明这些生产门通过。
3. `worker.main` 构造普通 `Worker(Store(...), settings)`，未安装 trial binding。已有 Journal binding 仅接受精确 test-only SQLite、mock、live=false、空 token、MockTransport，不能作为真实安装脚本使用。
4. 所检查 `scripts/` 没有 source/controller 的真实注册命令。已有离线 demo/pytest fixture 是测试安装，不是 LIVE 配置。

因此，本片没有把固定拒绝改成接受任意 JSON/ALLOW/callback，也没有增加新的模拟安装链。真实 producer 与既有 Worker/InternModel 的受审安装仍待实现。

最小外部依赖：提供现有账户的官方可读账户标识、当前分别可用的输入/输出额度，以及同账户当前有效、可强制执行零新增费用且无付费回退的机制和对应官方接口/记录结构。可由一个来源同时证明这些事实，不要求额外凭据、签名格式或 provider 每30秒续签。已有 token 不回显、不复制、不哈希，不需要重复提供。取得这些接入依据后仍须实现并审查服务器固定 producer/注册；不是提供余额截图就已完成安装。当前没有执行任何该外部操作，真实模型 POST 为0。

## Git 交付限制

此前 `a7403b37` 推送有 exit 0 回执，但其后的独立远端读验得到明确认证拒绝。本片遵从停止要求，零次远端读/推送重试。只作本地普通开发分支提交；最终本地 SHA 与未推送差异以交付记录为准。未改 main、未强推、未部署、未换凭据或持久安全配置。
