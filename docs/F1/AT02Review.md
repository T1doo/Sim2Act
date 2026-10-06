# AT-02冻结操作与现有LIVE证据核对

2026-10-05；只读既有导出，真实API请求0。依据V5阶段计划§11.2和未改动tests/cases/AT-02.json。此核对不签收，不将PARTIAL改SUCCEEDED。

| 冻结要求 | 可核查证据 | 最小未决项 |
| --- | --- | --- |
| 真实书生理解目标并选工具 | dd195681-short-run.json冻结Read; echo.目标、第一attempt真实Intern-S2响应选resource.read；short-wire.json首轮HTTP200 | 验收方确认此合成只读目标属于AT-02操作覆盖；不扩大为F3广泛语义评价 |
| 收到工具反馈并修订 | persisted_context依序system/user/assistant/tool/assistant；唯一resource.read Operation VERIFIED、tool反馈与receipt匹配；第二真实attempt最终答案trim=42 | “修订”在冻结用例指消费反馈后的后续模型响应，未要求先故意答错；若验收方有不同解释需指出冻结条款，不新增门槛 |
| 请求/返回模型、工具及修订链可核查 | 两attempt RECEIVED、intern-s2/Intern-S2策略、usage、reservations、PG回读、source-hashes和evidence-hashes；short-run-validation.json独立导出检查PASS | 本轮链/哈希离线核验已通过，交给验收方签收；不声称当前源码又实际LIVE复跑 |
| 未用开发模型替代/禁止效果 | 正常InternModel/独立API-worker/PG17.9，两个官方端点请求，注册只读工具，无任意代码/外部业务写入；第一FAILED保留 | 真实调用已发生于dd195681；后续MOCK工程测试只回归实现，不能替代该来源 |
| 冻结资产起始/清理元信息 | LIVE明确授权、独立新临时数据库、运行/迁移角色分离、资源hash及实际停服务/导出清理记录 | 原验证任务已查创建脚本：仅一owner/一项目；DB已清理且无完整导出，历史完整两主体/两项目初态不能补证。不能凭E6合成fixture或别的FAILED DB填补 |

## 最小验证计划

1. 预算0时只离线验证归档哈希、两响应及tool_call_id/回执/材料hash、最终回答和持久回读一致，逐条映射冻结要求，保留原失败与PARTIAL。无需Win11、真实429、F2发布或真实用户材料作为AT-02新增条件。
2. 验收方针对操作覆盖和起始元信息作ACCEPTED或列明真实缺口。本轮独立审核为安全/源码及Actions只读审核，不等于AT-02签收；核心模型操作无需增加要求，但完整初态已确证缺口；父线程申请最多2真实请求的完整独立新验证预算，尚未批准。
3. 只有验收方明确无法以现有归档签收且需要重新完整记录时，另行批准最小预算方案：同一官方身份/项目路径、两个隔离合成主体/项目及无DDL应用角色，单个新只读Read; echo.任务、最多2真实请求、0自动重试/修复、既定字符/间隔/token上限、保留失败、导出哈希与清理、独立核验。预算仍0，当前不执行、不查询models、不预写通过。若2请求不足或出现错误按预算停止，不追请求。

Win11属于AT-01主平台缺口；广泛自然语言/真实材料评价属后续F2/F3，故不能把这些未完成项目写成AT-02冻结操作的必需新增请求。

本轮离线核验结果：evidence-hashes.json列出的12个文件字节数/SHA256全匹配；两个RECEIVED真实响应的请求intern-s2/返回Intern-S2、system/user/assistant/tool/assistant顺序、唯一VERIFIED只读Operation、PARTIAL/trim答案42及剩余预算0一致。未补造两主体/两项目初态，未增加真实调用；独立签收仍待验收方决定。

后续独立历史查询终结（父线程转交原LIVE验证任务结果）：找到当时创建脚本，仅创建一个owner、一个项目；自动项目runtime及同项目Grant不等于第二用户/第二项目。临时DB已清理，未保留完整principals/projects/grants导出，无法补证完整初态。既有bounded LIVE核心操作/oracle证据有效，完整AT-02仍未签收。父线程已请求额外最多2真实请求的预算，尚未批准；本开发预算仍0，不自行LIVE。本段为交接结论，非本开发重新读取原脚本或原sessions。

## 2026-10-06 新鲜双身份证据按原冻结 AT02 核对

当前预算状态：用户另批最多4次、每次512、仅合成TXT42/84、0自动retry；实际4次均RECEIVED、余额0。上文“最多2次待批/单主体无法补证”是旧历史状态，不再代表本批初态。历史E3不改；本批来自一个完整新DB，不能拼接旧失败记录。

原V5阶段计划§11.2/AT-02要求“真实书生理解目标、选工具、收到工具反馈并修订”，预期及oracle是“请求/返回模型、工具结果和修订链可核查；未调用开发模型代替”。未改动[冻结用例](../../tests/cases/AT-02.json)另要求每例独立DB、两个隔离主体/项目、调用用户和runtime独立、明确LIVE授权、输入hash、禁止越权/重复副作用/任意代码/降低oracle/删失败证据及owned清理。其result字段NOT_RUN是冻结规格初始占位，不覆盖独立execution report。

| 原冻结条款 | 本批真实证据 | 核对结果 / 尚需验收 |
| --- | --- | --- |
| 明确LIVE授权、独立DB/两主体两项目、用户/runtime独立 | `preflight.json`完整principals/projects/grants/resources初态：两owner/两project/两runtime，非SUPERUSER/CREATEDB/CREATEROLE/DDL的CRUD角色、四活跃read交集；源42/84 hash | **已满足本批证据要求**；旧E3缺口仍属旧历史，新鲜初态缺口已补齐 |
| 真实书生理解目标并选工具 | 两组固定Read; echo.各有第一LIVE RECEIVED Intern-S2响应，选择本组resource.read与精确ref；正常InternModel发官方固定端点 | **已满足冻结操作覆盖**；不扩称广泛目标理解/自然语言价值评价 |
| 工具反馈后修订 | 各有VERIFIED只读回执、assistant/tool/assistant及匹配call_id；VERIFIED先于第二reservation/send；第二LIVE响应各产生42/84 | **已满足反馈后后续响应/修订链证据**；原条款未要求先故意答错、必须改非空旧答案或产生多工具成果 |
| 模型、结果、修订链可核查且未被开发模型替代 | four-wire、four-attempts严格身份策略enforced/ACCEPTED、完整请求重建hash、usage、回执内容/hash、Run receipts、冷Store/API回读；独立58归档断言PASS | **已满足可核查性及模型来源**；独立审核仅重建归档，未复发LIVE/重查已清理PG，边界如实记录 |
| 禁止越权/重复副作用/任意代码/降低oracle/删失败 | 8初态HTTP403、跨runtime及owner/runtime撤权拒绝；后续跨owner Run/history403，资源/Grant逐行不变；两个注册只读Operation、4请求上限/0repair、原历史不改 | **已满足本批受限只读范围的禁止效果证据**；不替代AT04/AT06全部故障或非CSV写入验收 |
| 预算/元信息/清理 | 4实际发送，max512、2000全体字符、三间隔≥6秒；报告input2506/output299/total2805；独立角色/进程、owned PID/端口/容器/temp实际移除 | **已满足本批记录和owned reset**；余额0，未知权重不被补造 |
| Run PARTIAL、semantic goal acceptance NOT_RUN | 两Run原状态保留，trim42/84为冻结harness oracle；通用语义验收未运行 | **不是原AT02工具反馈标准的自动失败条件**。它限制通用业务任务成功/语义评价及P-B来源准入的声明；不能新增“必须SUCCEEDED/通用semantic PASS”才满足AT02的门槛 |

开发方结论：本批证据符合原冻结AT02工具反馈操作及完整初态要求，未发现需要额外模型请求才能补齐的具体AT02证据缺口。正式AT02 ACCEPTED仍由验收方确认目标覆盖、证据对应及独立审核边界后记录；不自行改冻结case或签收整个F1。若验收方提出缺口应指向原条款及缺失证据，不凭PARTIAL/NOT_RUN自动判败。

F1整阶段的Win11原生/AT01、§3同输入重复运行及其余AT01—08完整阶段签收，后续非CSV/P-A/P-B/AT24和广泛语义评价另有门；未因本批补齐而自动完成，也不是AT02所需追加LIVE请求的依据。本轮不发新请求、不改AT02历史/原oracle。[完整归档](../evidence/AT02-dual-live-20261006/README.md)及[独立报告](../evidence/AT02-dual-live-20261006/independent-review.json)。
