# 冻结 AT-10 的合成子项映射（E15）

V5冻结条目不改：AT-10“P-B 从已完成任务提取应用，在冷会话中运行”，要求“不依赖原聊天或固定旧文件；存在独立应用清单与新结果”。本页只映射固定合成CSV子项，不签收完整AT10/P-B。

| 子项 | 实际路径与判据 | 证据及限制 |
| --- | --- | --- |
| 完成任务来源 | 新隔离CSV→LOCAL_DECLARATIVE_TASK可信工具实际求和→精确整数oracle→SUCCEEDED；失败不提取 | E14固定目标fixed_csv_exact_sum.v1；不是F1 Run/PREVIEW升级，不含通用任务归纳 |
| 提取候选 | 完成证明/版本/hash/owner/project→不同hash新CSV→独立固定清单与task_proof锚点 | PREVIEW_ONLY；不允许递归、任意代码/外发、模型生成或Release |
| 显式退休 | owner匹配证明/source hash并显式retain_minimal_proof及policy；清旧content和任务input/output | 源当前grant仍必要，不恢复/延长；旧GET/工具读取拒绝；已有消费者拒绝退休 |
| PG交错 | 消费者先持project锁则创建成功/退休409；退休先持锁则清内容成功/后创建400，拒绝前无principal/app/grant副作用 | E15真实PG backend/blocking-pids barrier，direct/目标卡创建/修订/F1提交双顺序8项；无SQLite假锁替代 |
| 冷会话新结果 | 全新Store/连接/TestClient重开候选，旧数据已擦除，新amount10+30=40（旧4不可重放） | E15第9项直接复用E14冷Store oracle。保留源证明/授权元数据，不依赖旧CSV字节/聊天 |
| 坏输入 | 同新CSV缺失列→FAILED持久历史，与成功记录并存 | 不改失败为成功；源/目标撤权和过期/跨owner/project/证明篡改仍拒绝 |

对应测试：`tests/test_retirement_race.py::test_pg_retirement_consumers_serialize_and_recheck`（8种参数），`test_pg_fixed_at10_subitems_after_serialization`；后者实际调用`tests/test_local_task_retirement.py::test_completed_task_retired_source_cold_client_new_input_and_failure`，创建新Store/API客户端，不从原Session取缓存。

实际源/当前完整聚合/精确WindowsServerCI见[E15证据](../evidence/F2-retirement-race-20261006/README.md)。E14的量化与冷DOM历史仅作为历史旁证；本轮不宣称重新完成真实渲染/浏览器或手机视觉。通用稳定变量识别、非固定任务族、真实P-A生成/完整P-B、正式运行/发布/实例与原V5其余验收未完成，Win11/F1/Release仍未签收，真实预算0。

2026-10-06追加本地R0 agent证据：精确3e27ad9源AppManifest/AppRun的显式字面任务→真实resource.read反馈/精确VERIFIED receipt→独立接受来源提取marker→已授权新MD/新term→冷Store同Worker新结果，零新增产品Grant/Principal/表/API，provider0。PG45专项、完整473PASS1WinSKIP/SQLite450PASS24SKIP及独立44PASS1PGSKIP通过。仅literal引用完整性，semantic UNKNOWN，候选/Replay由离线调用者提供；不代表自由规范语义正确、真实模型自主生成、一般F1任务提取、跨进程Replay自动恢复或完整AT10/P-B。无push/CI，本轮父检查后再决定。
