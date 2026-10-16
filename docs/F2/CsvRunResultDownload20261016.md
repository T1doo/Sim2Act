# 所选 CSV Run 的 JSON 结果下载

普通“使用已保存的本地应用”入口现可显式下载所选成功 CSV Run 的 JSON。打开实例，在历史中选择一次运行，核对 Run 与结果版本后点击 **下载此运行结果 JSON**；未选 Run、失败或结果谱系无法核对时不提供下载。每次点击重新通过原有鉴权 GET 读取，不直接导出页面缓存。

开工确认唯一仓库写入者 root、干净 HEAD/远端 `da540dbf443b920ae25471c2487d938aca3e2a4e`，main `6f688e4dd80b5c81d41aecde90e360d3629f9c21`；约26 GiB/8.8 GiB可用。普通分支 `dev/csv-run-result-download-20261016`。产品源提交 `897558064a9bf759b609e22edd7cbe4f6d589d42`，最终执行源 `a0730fab025af68c10ae2706c7b9125d91ac2241`；两者产品 `use.js` 字节相同，后续只改测试夹具、观测和使用说明。

## 下载合同及边界

复用 `GET /api/internal/instances/{iid}/runs/{rid}`。原服务端保持 scope_run、当前身份/项目/材料权限、Release 及 typed 数据谱系检查；没有新增接口、executor、Grant、配置、迁移或持久账目。

文件仅含 `instance_id`、队列 `run_id`、该 Run 自身的 `release_id`、`result_version` 和 `result` 的 `resource_id/column/sum/count`。不导出 typed AppRun ID、原 CSV、合同、事件、鉴权或项目/账号信息。`sum` 原样作为字符串保存，不经 Number/parseFloat；历史 v1 的合成值 `9007199254740993.123456790` 保留全部位数。JSON 使用 UTF-8、两个空格缩进及末尾换行，MIME 为 `application/json;charset=utf-8`；文件名由实例、Run、结果版本构成，不使用材料内容或列名。

下载前检查 fresh response 的成功状态、实例/队列 Run/typed AppRun/Release/结果版本、四个结果字段及 known_effects 中相匹配的 typed 数据行，必须与所选已核对版本一致。非成功、403、错绑定、结果不一致或网络失败不生成文件；当前403清除保护结果与控件。历史版本按它自己的 Release 比对，不借当前实例 Release 代替。

回调绑定账号 token、连接代数、项目、工作区代数、实例对象、读取代数和所选 Run。切换或切走再返回后的旧响应失效；同 Run 刷新重绘也共享 in-flight 去重。临时 anchor 删除，Blob URL 在点击后下一个定时回调释放，anchor 点击抛错也释放。文件由页面明确操作生成，读取/下载没有后台运行、授权或持久写入。

## 实际工程验证

最终一次作者组合 **7个唯一 pytest 节点 PASS、0 FAIL/ERROR/SKIP，85.56秒**；独审另外独立复跑其中3个新增节点 **3 PASS、0 FAIL/ERROR/SKIP，45.54秒**，不累计为10个唯一节点。均有1条既有 Starlette/httpx 弃用 warning。Ruff（新增Python文件）、两个JS的 node --check、源码/测试/使用说明 diff --check通过；本轮未执行mypy或全库测试。完整证据归档的 diff --check 为RC2：两轮原始失败pytest日志/JUnit共4份文件自带尾随空格，按原字节保留；其余归档内容检查通过，不改写失败原件。

三个新增用例分别覆盖：

- 当前 v2 与所选历史 v1；无所选/失败 Run 无按钮；每次点击 fresh/no-store GET、防双击、完整 UTF-8 字节白名单、字符串精度、文件名/MIME；18种响应绑定/结果篡改和网络失败均拒绝；anchor异常回收及后续可再次点击。
- 工作区、Run、实例、项目、账号、同账号重连切走再返回，以及刷新重绘时重复点击；故意延迟真实200后均不创建Blob，旧锁释放后当前明确点击可用。
- 受控撤回真实合成 resource.read Grant，再释放尚未送出的下载GET；实际HTTP403、无Blob/anchor、清除缓存结果和控件。

这些用例使用实际合成 CSV、现有版本/实例 API、正常 Worker 和真实 loopback HTTP；页面产品JS在 JSDOM 执行。Blob 使用 Node Web Blob，URL/anchor由工程适配器捕获，`captured-blob-*.json` 是捕获 Blob 字节的证据，**不是实际浏览器下载落盘**。源码HTTP加载SHA与执行冻结匹配。

每个新增用例对SQLite **48张表全部持久行**作前后比对：版本/拒绝、导航两组完全不变；撤权组仅夹具显式通过原撤权 API 改Grant，撤权后的下载GET与该快照完全一致，其余表保持原样。没有新增Run、数据版本、身份、授权或读事件。其余4个节点是既有普通应用使用、鉴权HTTP链、错实例/版本/撤权边界及失败Run保留回归。精确JUnit身份和原件见证据索引。

## 保留的先前失败

1. `897558064a9bf759b609e22edd7cbe4f6d589d42` 首轮新增3节点：**2 PASS / 1 FAIL，53.56秒**。撤权测试夹具POST缺少JSON请求体，被未改动 strict_json 中间件HTTP400拒绝，尚未执行撤权。修正仅为夹具发送合法 `{}`，没有修改产品校验。
2. `eff5309989b468fc255c1a5ebeaed42c1d573630` 组合7节点：**6 PASS / 1 FAIL，85.46秒**。版本组初始化选择Run时，一个实例GET在8秒driver等待截止仍未返回；尚未开始下载，原回执未记录该请求最终耗时，**精确原因未知，未声称修复**。
3. 最终 a073 只为driver补请求单调时钟耗时、失败后排空和最终状态记录；**原8秒等待、75秒子进程上限及全部断言保持**。随后7节点通过，独审3节点通过，不把后续成功改写为前两轮通过。原 log/XML/失败JSON保留。

## 未执行和剩余缺口

PG 与受保护真实 Chromium 的环境阻塞仍按 [da540记录](CsvPGBrowserAcceptance20261016.md) 保留；本轮没有重试沙箱、降低保护、搜寻配置/凭据、下载镜像或启动PG。真实浏览器文件保存、PG、CSV导入→明确保存运行→下载→API/worker及浏览器重启找回四步验收、Windows、真实模型/语义/人工场景、远端CI、部署均 **NOT_RUN**。本功能的工程通过不提升自然语义或人工验收状态，也不证明这些目标通过。

最终归档提交只增加本报告及证据；普通分支正常推送后的精确SHA、远端和干净状态由交付核验另存。不改main、不强推、不部署、不新增费用/凭据/安全权限。完整原件、Blob字节、失败和独审见 [证据索引](../evidence/csv-run-result-download-20261016/README.md)。
