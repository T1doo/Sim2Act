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
