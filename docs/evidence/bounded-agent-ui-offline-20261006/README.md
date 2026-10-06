# 既有 bounded agent 内部 UI：本地工程证据

基线 `4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5`，`dev/f1-foundation`。仅本地实现、验证与提交，等待父线程检查；本轮没有 push、CI、LIVE 或模型查询。原 V5、AT02、旧工作树及 workflow 未改。

## 对原目标的价值与实现

已验证来源的 bounded_agent 候选现在能在原应用工作区打开，查看适用字面检索词、来源链和资源 hash/revision、仅 resource.read 的限制，复用现有手工批准、Release、Instance、AppRun 和独立版本历史。明确显示 OFFLINE_REPLAY_ONLY、调用者提供响应、尚无真实模型自主生成、字面 PASS 与语义 UNKNOWN；CSV 界面保持原路径。

原审批/运行请求增加可选 offline_replay，严格两条、有限 wire JSON；HTTP agent 必须显式提供，CSV 拒绝。接受请求和既有 internal_run_bindings.snapshot 冻结响应与指纹，新冷进程默认 Worker 从冻结响应执行；不新增表、API 建表、工具、Grant 或 Principal。此前 Python 显式注入 Replay 路径保留。提交与成功冷读从已接受 Replay 和当前授权材料重建输出及协议并校验精确指纹，避免把不同的 Replay 冒充已接受执行。

独立合成内部篡改检查曾实际发现两次错误成功：替换 tool_call.id 的协议轨迹，以及将整数 1 换成 True 绕过 Python 相等比较。两项已修、独立重现拒绝 VERSION_CONFLICT，原脚本和失败输出保留。这是内部合成损坏验证，不是公开 HTTP 攻击。DOM 首次完整验证还发现刷新只核查冻结 Release、未核查当前选定 draft；现刷新先核查当前 draft 的授权/来源与精确指纹。

## 实际证据

- 新 HTTP/服务回归 20 PASS；覆盖批准、真实冷 Store/Worker、结果 v1、没有 provider fallback、无新增 Grant、严格响应输入、CSV 拒绝、幂等冲突、跨 owner/project、当前撤权、源和绑定篡改、成功收据冷读、实际服务器到期拒绝。
- HTTP 驱动 jsdom 功能检查 22 PASS：应用打开、离线标识、手工确认、冷运行 v1/v2、历史重开、引用 textContent、丢回执后冻结意图重试、过期批准、输入/文件/app/project 迟到响应、当前 draft 篡改及撤权清空。调用真实本地 API；文件完成和丢回执/迟到交付是明确的合成故障注入。无布局或视觉能力，**不算原生浏览器**。
- 完整 SQLite：493 PASS、24 SKIP、3 warnings，327.90 秒。PG 完整终态见 result.json 与 full-pg.log。
- Ruff PASS；mypy 23 源文件 PASS；JavaScript 语法检查及 git diff --check PASS。独立最终 HTTP 20 PASS、旧内部 API 18 PASS/1 SKIP，旧 agent 44 项在组合检查中通过；最终静态 UI 复审未发现新的已确认阻塞。
- source-sha256.json 固定实际产品/测试/脚本内容；独立报告分别保留执行与静态审查边界。

DOM 中途 v2 回读失败日志仍在：独立 HTTP/DB 实际有 v1/v2，但当时 Node fetch failed 后界面清空内容。夹具命令由同步 execFileSync 改为 await execFileAsync，增加底层 cause 诊断后最终 22 PASS，未加入 HTTP 自动重试。该历史传输故障的精确根因未证实，不能追认旧回合通过。早期 globalscope、错端口与独立到期测试 KeyError 等夹具失败亦保留。

日志里的 providerRequests/modelRequests=0 是检查脚本的范围声明，**不是独立网络计数器**；无 provider fallback 的执行证据来自 HTTP 测试中 NeverProvider 与实际默认冷 Worker、精确 Replay 类型校验及源码审查。本轮未执行 LIVE/models 查询。

## 原生浏览器阻塞与未完成边界

安装 Chromium 的正常 agent-browser 启动、正式 require_escalated 同命令，以及保持 chromiumSandbox=true 的原生 Playwright 启动均在 DevTools 之前退出：`/usr/lib/chromium/chrome-sandbox` 的 SUID helper 配置不正确。正式审批不是拒绝；实际主机配置阻塞。没有关闭 sandbox、改变系统安全设置或通过未授权 CI 绕过。原生检查 0、截图生成/查看 0、390px 窄屏视觉未验收；protected-browser-results.json 保存真实 BLOCKED。原 Edge38 或旧截图不作为本 UI 证据。

自主生成 AppManifest/候选、自由语义正确性、工具/模型步骤中断后的跨进程完整恢复、完整 P-A/P-B、Win11/F1 正式签收仍未完成。冷进程执行一个新接受 Run 不是完整断点恢复。失败 Run 不追加成功结果，没有将 FAILED/UNKNOWN/PARTIAL 来源当成功。

## 后续本地复现

scripts/agent-ui/fixture.py 在独立临时目录中创建明确的合成用户、材料与预先授权测试夹具。仅 seed 创建测试 Grant；运行 UI 与检查动作不创建 Grant。先 seed，再以同一 root/port 启动 serve，然后跑 dom-check.cjs 或 protected-browser.cjs；两种检查都应使用**独立新 seed**，因为末尾故意损坏候选与撤权。Python 要设置 PYTHONPATH=src，已有测试依赖可用；DOM 脚本使用本环境 `/workspace/browser-tools/node_modules/jsdom`。原生脚本使用 scripts/browser-ci/node_modules/playwright-core 及真实 Chromium/Edge，可传第三位置参数指定浏览器。父线程检查前禁止 push/CI；本脚本尚未获原生功能或视觉通过，不承诺其未来运行全通过。

## PG 完整终态与遗留失败

实际完整 PG17：**515 PASS、1 FAIL、1 SKIP、3 warnings，868.82 秒**。唯一失败为既有 `test_real_pg_process_crash_reopen_recovers_without_duplicate_results[before_commit]` 行504：故障子进程达到73，恢复进程返回0，但 Run 仍 RUNNING；根因未确认，不能宣称完整 PG 通过或恢复验收通过。两项崩溃用例单独复验实际 2 PASS/1 warning/18.79 秒，仅为额外证据，不能覆盖完整失败。新 HTTP 20 项在完整 PG 中均通过。本轮完整恢复边界仍开放。原生浏览器与此 PG 失败均须父线程检查后继续验收；没有因此增改 lease/权限或跳过失败。仅自有合成 API 与 PG 容器已清理，端口关闭，见 cleanup.json。

独立静态 PG 诊断确认 db/worker/旧 crash fixture/test 未改，失败路径为 fixed CSV，不走新 Replay 重建分支；未发现静态可确认的本轮恢复回归。恢复夹具不校验 Worker.once 返回值，exit0 不证明实际完成。1秒 lease 失效后 guard/fail_job 均拒绝陈旧写可兼容 RUNNING，但无该失败 Run 的 lease/fence/event 时间线，仍不能认定根因；下一步应先记录真实失败时间线，不放宽失效租约写权限。
