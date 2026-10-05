# F1 Plan

基线 V5；状态 IN_PROGRESS，阶段门未通过。当前工程增量为可复现 MOCK 底座；Windows/LIVE 保持 BLOCKED。

| task_id | 目标/契约/依赖 | 状态与当前产物 | 测试/证据 |
| --- | --- | --- | --- |
| F1-T01 | GoalSpec/ActionSpec/AppManifest/Run/Operation/Grant/Approval；先冻结契约 | IN_PROGRESS：七类 Schema 草案；严格 JSON/Action 注册引用；完整嵌套语义与编译待做 | AT-03 工程子集；Architecture.md |
| F1-T02 | 原生启动链；依赖 Python/数据库 | BLOCKED（Windows）；Linux Python 启停/进程/健康/端口/数据保留已测；PowerShell 六接口已写未运行 | AT-01 NOT_RUN；AT-05 Linux子集 |
| F1-T03 | 项目、应用、资源；依赖 API | READY_FOR_REVIEW（骨架）：项目/文本材料/实际任务/回执可用，应用空状态 PLANNED | 实际浏览器证据；不等于 P-A/P-B |
| F1-T04 | 用户/项目运行身份/资源授权/可信动作；依赖项目与 Grant | IN_PROGRESS：后端有效权限交集、三注册工具、两主体/项目拒绝、撤回/到期；AppRelease 权限在 F2 | AT-03/04/08 工程子集 |
| F1-T05 | 持久接受/队列/租约/fencing/心跳/Attempt/Operation/暂停取消 | IN_PROGRESS：本地效果与回执同事务、实际独立进程恢复；未知模型请求等待核对，人工核对入口待做 | AT-05/06 工程子集、真实进程测试 |
| F1-T06 | 书生适配/配额主体/预算/工具反馈/用量 | BLOCKED（LIVE）；官方固定 HTTP 适配器、MOCK/FAULT_INJECTION 与数据库配额已测，无真实调用 | AT-02 LIVE NOT_RUN；AT-07工程子集；capability-report.json |
| F1-T07 | 固定 AT-01—28 资产/夹具/oracle/重置 | IN_PROGRESS：28冻结规格、合成CSV/oracle、35个工程检查；后续阶段用例实现 NOT_RUN | ../evidence/F1-TestReport.md |
| F1-T08 | 环境锁/待确认/输入与预算上限 | IN_PROGRESS：Linux实测依赖锁、端口8000/显式数据目录；Windows版本组合/账号预算/授权真实材料待核实 | README、Architecture.md、Log.md |

AT-01 Windows、AT-02 LIVE：NOT_RUN（前置 BLOCKED）。AT-03—08 的本轮工程子集 PASS，完整阶段验收尚未签收；不能从 Linux、MOCK 推导 Windows/LIVE 通过。AT-09—28 实现/执行 NOT_RUN，规格未降低。

下一增量：完整契约与注册检查语义、配置/能力探针工程接口、独立心跳/并发领任务专项、未知请求人工核对与明确恢复规则；取得安全注入和批准预算后另跑 LIVE；取得目标 Windows 环境后独立验收。F2 的 P-A、P-B、发布和增量验证范围保持。

C0 截止、体验链接、托管API模型文件要求从F1并行待核实，最终验收在R0后。参赛主体/成员待确认。
