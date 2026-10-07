# Sim2Act 动态总入口

当前基线：V5；F1 IN_PROGRESS，两个 MOCK 工程增量已验证，尚未通过阶段门。仓库开发分支：dev/f1-foundation。

规范：[平台产品设计](平台产品设计.md)、[分阶段开发计划](分阶段开发计划.md)。
来源：[V5 原始文本与校验](sources/V5/manifest.json)。原始正文完整保留；修订见 [DocumentReview](DocumentReview.md)。

| 阶段 | 状态 | 当前证据 |
| --- | --- | --- |
| F1 | IN_PROGRESS | [任务](F1/Plan.md)、[日志](F1/Log.md) |
| F2 | PARALLEL_ENGINEERING / 正式准入 BLOCKED | 用户授权隔离并行 [CSV 草案预览切片](F2/Plan.md)；不是完整 F2 或发布签收 |
| F3 | PLANNED | 独立真实评价等待原阶段前置 |
| R0 | PLANNED | F1—F3 通过；禁止执行任意模型生成代码 |
| C0 | BLOCKED | 截止、体验链接、托管模型文件要求从 F1 并行核实；R0 后最终验收 |
| F4—F7 | PLANNED | 本轮不实施 |

目标平台为 Windows 11 x64 原生 + PostgreSQL，尚无用户环境实测。Windows Server2025云原生工程已通过：六PowerShell接口、独立API/worker、PG111项及清理；[实际证据](F1/WindowsCI.md)。Server和云端Linux工程测试不等于 AT-01/27 通过。
Server CI可复现性收敛已完成：独立完整Windows版本锁、pip check/精确包集合核验、真实首次py-launcher Setup通过；本轮一次CI成功（df31fe9），原Linux锁、V5来源哈希与历史失败保留。F1整体及Win11门仍未签收；后续用户授权 F2 隔离并行预览工程，正式准入仍 BLOCKED。
独立审计后：[owner环境继承缺陷的本地修复](evidence/F1-env-isolation-20261005/README.md)及PG114项回归已完成，修复后的Windows CI未运行；Git认证阻塞时不重复push。旧公开运行成功不替代这项隔离复验，111计数仍为开发方日志证据，F1安全准入待复核。
运行后端仅书生；2026-10-05在已授权安全注入与有限预算下完成合成LIVE只读反馈子链，完整LIVE验收仍未通过。10次HTTP预算已耗尽，停止真实请求；缺新预算时真实调用BLOCKED，不发现隐藏凭据。
保持项目、应用、资源三个工作区；应用发布与两条生成路径在 F2 实施。

## 最小待确认

- 参赛主体/成员、准确截止时间与时区、体验链接接受形式、托管 API 模型文件要求（F1 并行；未核实 BLOCKED）。
- 用户 Windows 环境及数据库安装条件（BLOCKED，仅影响原生验收）。
- 后续书生调用需新的明确预算；已完成的合成LIVE子链不授权追加请求（当前剩余0）。
- 授权真实材料与独立验证者（F1 收集条件，F3 评价）。

当前工程证据：[F1 TestReport](evidence/F1-TestReport.md)、[架构与限制](F1/Architecture.md)、[LIVE能力缺口](F1/capability-report.json)。Windows、LIVE、完整AppManifest编译和R0目标验收尚未通过。

工程源码提交：[f496f22](https://github.com/T1doo/Sim2Act/commit/f496f225ae109e4415cff3a1fa8117451a82fda3)（MOCK底座，F1未验收）。

第二工程增量：[契约语义](F1/Contracts.md)、[人工核对](F1/Reconciliation.md)、[实际检查与离线探针](evidence/F1-2-TestReport.md)。64 项 PostgreSQL 工程检查通过；LIVE/Windows 和完整发布门仍未通过。

第二增量工程源码提交：[637cca9](https://github.com/T1doo/Sim2Act/commit/637cca93aeb7022cb1062c73bb43ff40cab9c29d)。

第三工程增量：[F1/F2边界与验证前置](F1/Scope.md)、[90项回归及账本证据](evidence/F1-3-TestReport.md)。最小候选预检、手动Run冻结、可信本地未知效果核对完成；F1整体仍IN_PROGRESS，等待真实账号/原生环境及相关验收，F2能力未提前实施。

第三增量工程提交：[a38b98d](https://github.com/T1doo/Sim2Act/commit/a38b98d4d39712afcbf256fe7b697ce8ed16db8f)。

接入兼容修复：[模型身份规则](F1/ModelIdentity.md)、[111项回归证据](evidence/F1-model-identity-TestReport.md)。保留原返回Intern-S2并规范化为canonical；工程修复本身未消耗真实预算，随后独立复测结果见下方归档。

返回模型身份修复工程提交：[3707ef6](https://github.com/T1doo/Sim2Act/commit/3707ef63e249095d9ffabbb8a3671bd3099a0fc0)。

独立真实接入归档：[LIVE-20261005](evidence/LIVE-20261005/README.md)。测试源码精确提交dd195681；正常API/独立worker/PG两轮反馈子链最终PARTIAL/LIVE、答案42、resource.read VERIFIED。旧失败记录保留；累计10次请求，已知usage3143 tokens，预算耗尽。AT-02仅合成子项已验证，Windows、语义、F1整体门仍未通过；本轮不开发F2。

2026-10-05 后续用户决策：网络阻塞期间继续本地开发，开始 [F2 CSV 草案预览](F2/Plan.md)。固定可信模板、应用最小身份、声明式输入输出和持久预览历史；无 Release/业务写入、无模型请求。PG/Win11/完整 F2 验收保留，不以本地预览反向签收 F1。

2026-10-05 E11：[P-B可信PREVIEW来源受限提取](F2/PreviewExtraction.md)工程已交付；成功合成预览回执经独立oracle核查后绑定新CSV并冷客户端计算新结果。源码3d87f5e，ServerCI37340717581SUCCESS/PG208PASS/0SKIP，Linux203PASS/5SKIP。来源不是F1 Run签收；完整P-B/AT10/Release未完成。真实Chromium无可用沙箱而BLOCKED，Node/jsdom12项不替代浏览器验收；[精确证据](evidence/F2-preview-extraction-20261005/README.md)。原F1/Win11/AT02和真实预算0不变。

2026-10-05 E12：[现有两路径可用性收敛](evidence/F2-usability-20261005/README.md)已交付：独立只读旧基线复核4项缺陷，主开发修来源/模板接线/迟到选择/数值溢出失败，精确d3de155的ServerCI37343525441SUCCESS/PG219PASS/0SKIP。前端小范围样式和状态已改善，美观与手机一致性标准见[F2下一路线](F2/NextSteps.md)；真实视觉0/BLOCKED、20DOM不能替代截图。修复未独立复验，完整P-B/AT10/Release及F1/Win11未签收，模型0。

2026-10-05 E13：[来源请求锚定与回读恢复](evidence/F2-origin-recovery-20261005/README.md)已交付，精确4d01fb7/ServerCI37346429353SUCCESS/PG224PASS/0SKIP。5新专项、本地219PASS/5SKIP、DOM33明确非浏览器。完整P-B需先明示旧来源文件运行依赖、制定来源退休权限策略及完成合成task fixture，见[路线](F2/NextSteps.md)；当前未实施，不以冷页替代AT10。真实视觉BLOCKED、模型0、F1/Win11/Release未签收不变。

2026-10-05 E14：[合成完成任务来源与显式退休切片](evidence/F2-task-retirement-20261005/README.md)已交付，精确c776fa2/ServerCI37349609291SUCCESS/PG260PASS/0SKIP。36新专项及三表显式迁移/业务CRUD路径；本地254PASS/6平台SKIP，原33+新14DOM/HTTP不是视觉。owner显式清旧内容保留最小证明，当前source授权及target交集保持、撤权/过期拒绝，无grant恢复。仅LOCAL_DECLARATIVE_TASK固定合成来源/新内容冷会话子项，完整P-B/AT10/Release/F1/Win11未签收、模型0/真实视觉BLOCKED。

2026-10-06 E15：[来源退休与消费者PG串行](evidence/F2-retirement-race-20261006/README.md)已交付，精确53dc124/CI37411714116SUCCESS/PG269PASS/0SKIP，9真PG barrier/冷Store子项；LinuxPG268PASS/1WindowsSKIP、SQLite254PASS/15SKIP。基线grant锁阻止观察direct失效app，未虚写复现；消费者共享project锁和持久化前当前状态重验补强。冻结AT10合成子项映射不签收完整P-B/Win11/F1/Release，0LIVE/真实视觉BLOCKED。

2026-10-06 E16：[内部合成Release/Instance/AppRun生命周期](F2/InternalLifecycle.md)已交付，源码e029922/CI37413258268SUCCESS/PG302PASS/0SKIP；五表显式迁移及33新内部检查、原AT05进程回归保留。独立复验32PASS/1PGSKIP，两个schema缺口关闭；LinuxPG301PASS/1WindowsSKIP、SQLite286PASS/16SKIP。不可变快照/精确批准/独立instance结果账本/真实网关新AppRun/兼容升级回退历史，复用现runtime及Grant。正式发布入口/部署未启用，完整P-A/P-B/AT10/F1/Win11/protected browser未签收，0真实模型；[精确证据](evidence/F2-internal-lifecycle-20261006/README.md)。

2026-10-06 E17：[固定内部AppRun持久worker](F2/PersistentAppRuns.md)交付，精确源码8b14cee/CI37415214667SUCCESS/PG340PASS/0SKIP；38新项含4真实worker子进程及最低角色enqueue/控制/worker CRUD。复用现Run/Worker租约fencing/heartbeat，短事务取授权快照、事务外可信计算、当前Grant/Release/Instance重验后的原子结果版本+receipt+双终态，失联/暂停取消/unknown保守恢复。LinuxPG339PASS/1WindowsSKIP、SQLite319PASS/21PG平台SKIP；独立33PASS/5PGSKIP、source/test hash一致。[精确证据](evidence/F2-persistent-apprun-20261006/README.md)。无newGrant/preview复制/真实模型，正式发布/部署关闭，AT17受控写隔离OPEN，完整P-A/P-B/AT10/F1/Win11/protected-browser门仍未签收。

2026-10-06 当前来源生成切片：[成功 registered CSV AppRun → 可复用草案](F2/RegisteredRunGenerationSlice.md) 已按用户授权实施并独立审核，精确1413cbf/独立ServerCI37472996465 SUCCESS（559 PASS/1 SKIP）。服务端模板由可信成功回执生成，用户只选已有授权的新CSV应用与名称；冷worker新列新结果，不新增权限/表/模型请求。真实HTTP-DOM16与PG最小CRUD角色已测，生成入口原生UI/像素仍未验；不签收语义目标、完整P-B、F1/AT02/Win11/正式发布。[精确证据与失败历史](evidence/registered-run-generation-20261006/README.md)。先前独立UI修复9104b2a/CI37471361854已成功，新agent桌面/窄屏实际双像素审查通过有限当前捕获范围，旧空白根因仍UNKNOWN。


2026-10-06 本轮真实入口阶段闭合：普通push精确源码 `447b597fefd6c2a191ef4e9ff6d4bf2f0c06d3d5`，唯一原标准CI [37476996252](https://github.com/T1doo/Sim2Act/actions/runs/37476996252) 首次SUCCESS，无重试。Windows工程564PASS/2SKIP；原Edge38、旧agent33、新registeredGeneration29分别PASS。真实受保护浏览器完成源amount3→服务端草案→既有授权新CSV→人工确认版本→新实例冷worker quantity15/resultVersion1，并实测回执恢复、撤权、篡改、旧响应、跨主体/项目、空目标及窄屏。两次capture及最终实际保护审计PASS。两原PNG按stdout字节/SHA/尺寸与里程碑核验，主审及独立实际像素复审接受本次健康历史展示范围；runtime NOT_REVIEWED保留、人工审查另存。Report/Cleanup成功。最短说明补明预览列与新任务列分别设置，每次新任务需选quantity，历史刷新后amount默认不改变既有quantity15结果。见[证据](evidence/registered-run-browser-20261006/README.md)及[使用说明](F2/RegisteredRunQuickstart.md)。此有限原生入口缺口闭合，不提升Win11、完整AT02/F1、语义或完整P-B；旧空白根因UNKNOWN、失败历史保留、模型请求0。

2026-10-07 本地普通任务回执恢复切片：实际HTTP/DOM24项与相关47PASS，受保护Chromium启动BLOCKED且无截图；不push/CI、不带activation、不提升完整P-B/F1/Win11验收。[范围与限制](F2/TaskSubmissionRecoveryPlan.md)、[最终证据](evidence/task-submission-recovery-20261007/README.md)。
