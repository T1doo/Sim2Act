# F1 Plan

基线 V5；状态 IN_PROGRESS，阶段门未通过。当前工程增量为可复现 MOCK 底座；合成 LIVE 只读子链已验证，Windows及完整 LIVE 验收仍未通过。

本地收尾：[逐项验收矩阵](AcceptanceMatrix.md)、[下一阶段最小计划（未执行）](NextPhasePlan.md)、[文档推送只读诊断](GitPushDiagnosis.md)。6145bb8证据提交保留，本轮不重试网络同步、不启动F2；独立审计结论待交付。

| task_id | 目标/契约/依赖 | 状态与当前产物 | 测试/证据 |
| --- | --- | --- | --- |
| F1-T01 | GoalSpec/ActionSpec/AppManifest/Run/Operation/Grant/Approval；先冻结契约 | IN_PROGRESS：七类 Schema 草案；闭合嵌套结构、输入/条件/效果语义和有限 DAG 校验；Goal/Run手动任务冻结及最小清单引用/连通/权限/预算预检已做；完整编译执行属F2 | AT-03 工程子集；Architecture.md |
| F1-T02 | 原生启动链；依赖 Python/数据库 | BLOCKED（目标Win11）；Windows Server2025首次py-launcher Setup/六接口/独立API-worker/PG工程111项已测；普通用户与Win11组合待测 | AT-01 NOT_RUN；[Server云证据](WindowsCI.md)；AT-05 Linux及Server工程子集 |
| F1-T03 | 项目、应用、资源；依赖 API | READY_FOR_REVIEW（骨架）：项目/文本材料/实际任务/回执可用，应用空状态 PLANNED | 实际浏览器证据；不等于 P-A/P-B |
| F1-T04 | 用户/项目运行身份/资源授权/可信动作；依赖项目与 Grant | IN_PROGRESS：后端有效权限交集、三注册工具、两主体/项目拒绝、撤回/到期；AppRelease 权限在 F2 | AT-03/04/08 工程子集 |
| F1-T05 | 持久接受/队列/租约/fencing/心跳/Attempt/Operation/暂停取消 | IN_PROGRESS：本地效果与回执同事务、实际独立进程恢复；未知模型请求显式人工核对双路径、导入暂停/另行继续、成本保留；未知工具效果可信回读/已知不符/保守等待已做，取消保留效果摘要 | AT-05/06 工程子集、真实进程测试 |
| F1-T06 | 书生适配/配额主体/预算/工具反馈/用量 | IN_PROGRESS：官方固定HTTP适配器及合成LIVE只读反馈子链已在独立API/worker/PG验证；模型身份/用量/回执持久化，Run为PARTIAL；完整账号/故障/语义验收未通过 | AT-02合成LIVE子项已测；[实际证据](../evidence/LIVE-20261005/README.md)；AT-07工程子集；历史capability-report不代表本次LIVE |
| F1-T07 | 固定 AT-01—28 资产/夹具/oracle/重置 | IN_PROGRESS：28冻结规格、合成CSV/oracle、111个工程检查；后续阶段用例实现 NOT_RUN | ../evidence/F1-TestReport.md |
| F1-T08 | 环境锁/待确认/输入与预算上限 | IN_PROGRESS：Linux原锁保留、独立完整Windows版本锁和实际安装集合已验证；端口8000/显式数据目录；Win11组合/账号预算/授权真实材料待核实 | README、Architecture.md、Log.md、WindowsCI.md |

AT-01 Windows：NOT_RUN（前置 BLOCKED）。AT-02合成LIVE只读反馈子项已验证，完整场景尚未签收。AT-03—08 的本轮工程子集 PASS，完整阶段验收尚未签收；不能从 Linux、MOCK 推导 Windows/完整LIVE通过。AT-09—28 实现/执行 NOT_RUN，规格未降低。

本轮 F1-2 增量：上述契约语义、离线探针、心跳/并发专项及未知模型请求人工核对已验证；证据见 [F1-2 TestReport](../evidence/F1-2-TestReport.md)。F1-3已补运行级冻结、清单预检及通用核对入口；[证据](../evidence/F1-3-TestReport.md)与[范围划分](Scope.md)。文件落位及完整应用编译执行属F2，本轮停止扩大底座；取得安全注入和批准预算后另跑 LIVE；取得目标 Windows 环境后独立验收。F2 的 P-A、P-B、发布和增量验证范围保持。

C0 截止、体验链接、托管API模型文件要求从F1并行待核实，最终验收在R0后。参赛主体/成员待确认。

模型返回名称兼容已按独立接入证据修复，零网络专项及完整111项回归通过，实际账户复测由独立验证者完成；[身份规则](ModelIdentity.md)、[本次证据](../evidence/F1-model-identity-TestReport.md)。本任务不占用保留预算，未将真实复测预写为PASS。

2026-10-05独立实际复测归档：[LIVE-20261005](../evidence/LIVE-20261005/README.md)。保留04335528零请求模型名失败诊断、dd195681第一Run第二体2028字符未发送的FAILED记录、新短目标Run两轮成功PARTIAL/LIVE。累计10个HTTP请求，已知usage3143 tokens，预算0；停止进一步真实调用。Windows/语义/F1整体仍未通过，F2保持PLANNED。
