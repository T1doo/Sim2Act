# AT-02冻结操作与现有LIVE证据核对

2026-10-05；只读既有导出，真实API请求0。依据V5阶段计划§11.2和未改动tests/cases/AT-02.json。此核对不签收，不将PARTIAL改SUCCEEDED。

| 冻结要求 | 可核查证据 | 最小未决项 |
| --- | --- | --- |
| 真实书生理解目标并选工具 | dd195681-short-run.json冻结Read; echo.目标、第一attempt真实Intern-S2响应选resource.read；short-wire.json首轮HTTP200 | 验收方确认此合成只读目标属于AT-02操作覆盖；不扩大为F3广泛语义评价 |
| 收到工具反馈并修订 | persisted_context依序system/user/assistant/tool/assistant；唯一resource.read Operation VERIFIED、tool反馈与receipt匹配；第二真实attempt最终答案trim=42 | “修订”在冻结用例指消费反馈后的后续模型响应，未要求先故意答错；若验收方有不同解释需指出冻结条款，不新增门槛 |
| 请求/返回模型、工具及修订链可核查 | 两attempt RECEIVED、intern-s2/Intern-S2策略、usage、reservations、PG回读、source-hashes和evidence-hashes；short-run-validation.json独立导出检查PASS | 本轮链/哈希离线核验已通过，交给验收方签收；不声称当前源码又实际LIVE复跑 |
| 未用开发模型替代/禁止效果 | 正常InternModel/独立API-worker/PG17.9，两个官方端点请求，注册只读工具，无任意代码/外部业务写入；第一FAILED保留 | 真实调用已发生于dd195681；后续MOCK工程测试只回归实现，不能替代该来源 |
| 冻结资产起始/清理元信息 | LIVE明确授权、独立新临时数据库、运行/迁移角色分离、资源hash及实际停服务/导出清理记录 | 导出未显式枚举AT资产所写“两主体/两项目”的完整初态，需对既有证据标为未证明；不凭E6的合成两主体fixture填补历史LIVE记录 |

## 最小验证计划

1. 预算0时只离线验证归档哈希、两响应及tool_call_id/回执/材料hash、最终回答和持久回读一致，逐条映射冻结要求，保留原失败与PARTIAL。无需Win11、真实429、F2发布或真实用户材料作为AT-02新增条件。
2. 验收方针对操作覆盖和起始元信息作ACCEPTED或列明真实缺口。本轮独立审核为安全/源码及Actions只读审核，不等于AT-02签收；目前没有证明还缺新的模型操作。
3. 只有验收方明确无法以现有归档签收且需要重新完整记录时，另行批准最小预算方案：同一官方身份/项目路径、两个隔离合成主体/项目及无DDL应用角色，单个新只读Read; echo.任务、最多2真实请求、0自动重试/修复、既定字符/间隔/token上限、保留失败、导出哈希与清理、独立核验。预算仍0，当前不执行、不查询models、不预写通过。若2请求不足或出现错误按预算停止，不追请求。

Win11属于AT-01主平台缺口；广泛自然语言/真实材料评价属后续F2/F3，故不能把这些未完成项目写成AT-02冻结操作的必需新增请求。

本轮离线核验结果：evidence-hashes.json列出的12个文件字节数/SHA256全匹配；两个RECEIVED真实响应的请求intern-s2/返回Intern-S2、system/user/assistant/tool/assistant顺序、唯一VERIFIED只读Operation、PARTIAL/trim答案42及剩余预算0一致。未补造两主体/两项目初态，未增加真实调用；独立签收仍待验收方决定。

后续独立历史查询终结（父线程转交原LIVE验证任务结果）：找到当时创建脚本，仅创建一个owner、一个项目；自动项目runtime及同项目Grant不等于第二用户/第二项目。临时DB已清理，未保留完整principals/projects/grants导出，无法补证完整初态。既有bounded LIVE核心操作/oracle证据有效，完整AT-02仍未签收。父线程已请求额外最多2真实请求的预算，尚未批准；本开发预算仍0，不自行LIVE。本段为交接结论，非本开发重新读取原脚本或原sessions。
