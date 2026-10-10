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

2026-10-10闭合两/三步CSV内部流程限定推进：已成功版本可显式绑定同project另一份已有注册、当前授权/图/schema的不同真实CSV及数值列，经原worker实际执行、逐次确认保存独立目标Release/Instance，冷页新列生成新typed结果，旧历史不覆盖。源冻结预算不扩大，材料转移仅一跳；原注册入口仍create-and-authorize。来源仍实时依赖旧CSV bytes/当前授权，新增注册还可能使旧source图授权基线过期，需显式重derive/执行保存新source；没有完成AT10“不依赖固定旧文件”或完整AT11。最终源码709e0978c15236ed86bafc095d4cdf1301ad756c，SQLite最终页面12PASS/PG专项3PASS，后端22仅精确字节桥接此前通过，独立最终5场景/9页面/213检查LIMITED_PASS。范围、真实旧50b升级409/不迁移、所有失败/中止、原生固定11诊断及未执行inventory见[说明](CsvDagNewMaterialReuse20261010.md)和[证据](../evidence/csv-dag-new-material-reuse-20261010/README.md)。PG resources-history Future10、Report GET idle6及新材料读回整体性能观察继续OPEN；Windows900/Edge240/Node150整体NOT_ACCEPTED。PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、正式发布关闭、LIVE/实际模型0保持。

2026-10-10追加事先显式确认的无原材料内容逻辑授权限定切片：来源仍完整可核时先签24h可撤销独立逻辑授权，再登记新CSV、derive当前目标图，旧CSV用户/runtime撤权及删除后无需重跑原任务即可在当前授权目标实读新结果；原来源GET拒绝、未预授权失效源补发拒绝，不放宽旧权限。仅规范化已有注册read→sum[→report]及固定schema/cap，不复制旧列/CSV/input/output，private audit仍依赖封存来源JSON及opaque身份/版本记录。产品4a4b6949fd159bd35c1ed1ed9d111426a27b706f，作者SQLite/PG各59专项+各3旧material页共124PASS/0FAIL/0SKIP；独立58 API/worker场景250运行检查+4真实HTTP页面110检查LIMITED_PASS，原4e6请求键BLOCK已修且全原件保留。推进AT10固定家族“不依赖固定旧文件”部分，不签完整AT10/AT11、全部旧记录可删、语义/整体验收。详见[说明](CsvDataFreeLogicReuse20261010.md)及[证据](../evidence/csv-data-free-logic-reuse-20261010/README.md)；四早期PG DOMidle10、Report idle6、resources-history Future10、HTTP200恢复/性能OPEN、Windows900/Edge240/Node150 NOT_ACCEPTED，PROJECT PENDING/BLOCKED_PARTIAL、LIVE0保持。

同源原生run38045426944/job114193869021固定11通过，inventory2337/未执行2326；Edge整项FAIL于natural-goal.js ERR_NO_BUFFER_SPACE控制台门，根因未定、新OPEN，原日志与8个恢复对象保全，不以67主检查及内部流程局部PASS代替整体。无调gate/预算或重跑，原生清理成功，整体NOT_ACCEPTED保持。
