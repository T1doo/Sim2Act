# P-B 首次局部逻辑完整页面：有限非作者独审

结论：本轮限定范围通过；未发现阻止普通开发分支交付的 P1/P2。实际成功资格是一条 pytest、第四次 fresh attempt 的完整页面 PASS，并非四次全绿。本审查仅独立读取源码、Git blob 与已闭合原件并运行纯文件审计；没有亲跑产品、pytest/collect、HTTP、Worker、模型、SQL或打开数据库。

冻结源为 `459abcce146ed877ed8f893f3b06d10362cc7237`，前源为 `2fa76ff2458d3b732f1c18c000a51b4e9171d87b`，基线为 `e73004e3529ebfdc27e0105a33f888dbcf042543`。这是既有功能的当前完整页面资格补齐，133 份生产文件对三份 Git 源的 399 次逐字节核验全部一致，没有新增产品 executor、Grant 能力或权限。原方案 §9.3（`docs/sources/V5/平台产品设计.md:429`）、F2-T07/AT13（`docs/sources/V5/分阶段开发计划.md:99`、`:343`）对应的首次有限 dependency 修改得到本次页面证据；已有 PB 后端 R0/R1/R2 和修改版 per-use 资格不重新包装成本轮新增能力，也不提升为全部 AT13/14/15 通过。

## 实际闭合证据

作者原件根为 `/workspace/pb-first-logic-current-page-evidence-20261018`，成功 case 为 `actual-tmp/test_first_pb_local_logic_chan0/`。`execution.json` 为 exit 0、1133.845962254 秒；`actual-junit.xml` 仅一例 `test_first_pb_local_logic_change_checks_then_versions_and_uses_third_on_current_page` PASS、1129.738 秒。92 是该页检查数，不是 pytest 数。

独立可执行纯原件复算在本目录 `final-raw-audit.py`，原 stdout、stderr 与 `final-raw-audit.json` 均保留。审计没有导入或执行仓库产品模块。它核对了以下闭合材料，而非仅接受作者摘要：

- 第四轮 `inputs-fourth-before.json` 与 `inputs-after.json` 的 691 项完全一致，并逐项核当前执行文件；141 项直接 `source-before.json`/`source-after.json` 相同且属于该 691 项。2fa→459 仅两个测试 harness 路径改变，195 个业务 assert AST 保持一致。默认观察器仍 900 秒，只有本 case 使用 Node 1200 秒、外层 1500 秒；产品 Run 300 秒、lease 30 秒及模型/工具预算未改。
- 92 checks、36 actions、119 API、54 静态资源响应组成 173 页面 HTTP；两次 boot 各 27 资源逐字节 SHA 对当前冻结源吻合。204 份含 fixture 的原 HTTP response body 全部按保存长度与 SHA 回读；173 page-wire 的 request body 字节、响应字节、顺序/path/status 和 API/RPC 关系复算一致。
- 七个实际页面 POST 状态依次为 `201/202/201/200/201/200/202`：preview、CHECK、独立版本审批、commit、新实例、THIRD per-use review、显式 Run 提交。七份保存的全表 checkpoint 各含 55 张表，全部 fingerprint 重算一致；原 fixture 所有行在各 checkpoint 与逐 POST 快照中保持。
- preview 只新增两行 sealed metadata，没有运行或发布。六步并行原 logic 的一个 qualifiers dependency 从 false 改为 true；action/step 身份保持，另外五个 action 定义保持，候选 logic/action revision 为 2。CHECK 与新业务各 queue journal 6 行、完成 14 行，精确双 seal 与 fingerprint 通过；8 份实际 request/response durable body 的 base64、字节 SHA、Attempt 与 Mock wire/canonical response 关系通过。第二个模型输入实际消费第一个 requirements Operation receipt 的 items/feedback，非预造反馈。
- CHECK 使用独立实例与旧 Release；首次成功 CHECK GET 会写 CHECKED pair 两行，本报告不声称所有 GET 都零写。另一次显式审批/commit 产生新 Release，再从新 Release 明确建新业务实例，以 THIRD 和匹配 Goal 运行。旧 PB、CHECK、新业务三个不同实例/Run 各为 typed result **version 1**；logic revision 2 不等于结果 v2。原 PB/source/history 所有原行保留。
- 最终四个业务 phase 各单 claim、正常 SUCCEEDED，页面 Worker 命令 2 次，generation Worker 1 次。该成功 attempt 的 Mock 为 `3+2+2+2+2=11`，真实模型请求 0。实际新增 5 个既有 derived `resource.read` Grant，没有新 app/runtime、没有 SAVE Grant；独立原表比对与冻结生产桥相符。
- 冷页两次实际成果 GET 分别是 RPC170（旧 PB Run）与 RPC181（新逻辑业务 Run），响应原 SHA 为 `fbe01c2de8fa9b2888c47b74021ae09164afe7203ffa2abb76b4b1b472203505` 和 `425711bafd473c8739647f708c45e083cebf6b156177ce2e981ad19289b9e59c`。已逐项核 instance/Run/Release/result_version、resource 内容 SHA、来源材料与 canonical JSON，冷页前后全表完全相同。五次实际 owner GET 均为 PENDING、sequence 0；没有 PREPARE/DECIDE、下载或故障注入。

## 四次 attempt 的保留边界

| attempt | 源 | 实际结局 | 已保存 Mock | 有限边界 |
|---|---|---|---:|---|
| 1 | 2fa | 环境 transport 断连，UNKNOWN | 9 | 443 原件；无 exit/JUnit/finally；3 业务阶段、4 POST 到 commit200；后续旧实例 GET 未有回执，精确终止原因未知 |
| 2 | 2fa | 外层 900 秒到期，exit124，未通过 | 11 | 599 原件；900.207 秒；7 POST、4业务完成；最后完成新实例 GET891.855 秒，下一 Release GET 无回执，无完整冷页/pytest 终态 |
| 3 | 2fa | JUnit BrokenPipeError FAIL，exit1 | 11 | 870 原件；外1153.606秒/JUnit1148.997秒；Node900秒 watchdog 已杀本测试 Node，随后 GET200、stdin BrokenPipe；仅6/7 checkpoint、冷旧成果已读，冷新成果未完成；CHECK 合法2 claims，总5业务claims |
| 4 | 459 | JUnit 1 PASS，exit0 | 11 | 第四完整 fresh 页面闭合，7/7 checkpoint、两次冷成果回读完成 |

上述前三轮精确字节与因果边界分别见本目录 `first-interruption-review.json`、`second-timeout-review.json`、`third-watchdog-review.json`；本次不重复产品或旧矩阵。总计一条唯一 pytest、4 attempt、42 保存 Mock；两份已保存 JUnit 终态是 1 PASS + 1 BrokenPipe FAIL；3 次已知退出是 0/124/1，另一次未知。摘要的 `pytest_assertion_failures=0` 只限已保存 JUnit 未报告业务 assert 失败，不能推断第一轮未知尾部没有 assert 失败，不能称全程零错误。

## 审计错误与交付状态

独立纯文件审计自身有两次 schema 错误，已原样保留初版/第二版脚本和当时重定向 stdout/stderr：先误把 NOT_EXERCISED/NONE 枚举当 0/false，后误把 progress 中全为 null 的 rpc_id 当成 page-wire RPC ID。修正后按 node_started 后的 173 份有序响应逐一对齐 method/path/status/bytes/SHA，页面 API 与冷成果仍用原 wire/RPC 身份校验。`independent-observer-diagnostics.json` 明确区分它们与此前仅工具可见文本转录的诊断错误；没有修改作者原件/产品或重跑测试。此前一次将第三轮都单 claim 的口头误述已在 `third-watchdog-review.json` 纠正，最终只第四轮为四业务单 claim。

源码普通 push 的已保存 `watchdog-source-push.stderr/stdout` 显示自有分支从 2fa 更新至459，`watchdog-source-left-right.stdout` 为0/0；这是保存的作者回执，本独审没有访问网络独立 fetch。当前本地 HEAD 精确459；审查时仅交付文档和新 evidence 目录处于未提交状态，691 执行输入没有变化。后续文档/归档提交、最终远端 HEAD 不在本报告预先背书范围。

资格只包括一个合成账号/项目、Mock 数据、JSDOM + actual TestClient HTTP 的首次有限 PB dependency 调整页面。generation、SOURCE/source Worker、PB 提取、原 PB COLD v1 和 graph derive 是 fixture；没有将其称为页面创建。没有独立双账号权限矩阵、真实模型/真人语义验收、完整 AT13 多种修改类别/PROJECT 影响、原生浏览器、Windows、PG、远端 CI、部署或费用操作。旧永久取消安装窗口、exit139 原因未知、旧满盘原独审缺件均未重试或补签。性能上本次完整流程需要约19分钟且使用1500/1200测试看门狗，PASS 不证明交互响应性能指标。

本目录于生成 `sealed-manifest.json` 后停止所有写入；manifest 对自身之外的全部独审文件记录路径、完整字节数与 SHA256。没有新增仓库写入、产品执行或阻塞项；仅以上明确未验证范围继续保留。
