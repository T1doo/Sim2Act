# 第三批 origin / Binding / per-use / Authority 事实边界

本批只在批准的 apps.py、app_jobs.py、pb_natural_uses.py、natural_live_admission.py、pa_spec_apps.py 内拆私有叶。原公开调用仍在原位置取得并核实全部事实；没有 Cold 图生产者或运行时接入，没有 shadow、通用 resolver/cache、executor 或 Grant。原两个 epoch、五写和 ModelSettlementRead 不变。完整 P-B 的历史状态仍为 FAIL_NOT_ACCEPTED，指纹独占成本仍 UNKNOWN。

## Dormant strict origin handoff

`apps._cold_graph_origin_facts` 只为未来局部完整图生产者传入已核 origin 事实，当前没有生产调用点。其 exact `_ColdGraphOriginFacts` 只能在工厂局部活动作用域内供 `validate_frozen_candidate` 消费；HTTP、普通 dict 或其字段不能启用严格分支。类型及作用域不是完整证明或权限。工厂不会 verify_origin、read_release、读库补证、授权或调用 source resolver；没有任意 check 回调、resolve 接口、c.info/global 图存储。

未来生产者在创建它之前必须按原权限/首错顺序完成该角色完整 origin，包括原 Source/Generate 的全量有序历史多重集、全部基数/唯一性和独立 NS/controller 完整字节核对。显式传入完整 inputs、角色和每项完整 Limits：source / generate / platform / trial / per_use（None 语义独立）；这些键不会互相替代。`limits` 还单独固定本次原函数实际使用的完整 Limits。source/cold/gen runtime、有效 per-use candidate 与提取基稿即使同 app ID 仍是不同角色。局部传入缺项、完整性不足或漂移必须拒绝，不得回公开 verifier 补证。

每次检查先重验 inputs/role/role_limits/origin 的 exact 形状；Limits 不能被同字段 dict 替换，tuple 不能被等值 list 替换。engine 固定原对象，不能只比较当前 Store/Connection 两边的新关系。固定检查覆盖 Worker/Settings（身份及全部值）/Store/engine/controller binding/stop/transport/worker id、完整原 binding、Connection/TX/SQLite driver、线程、write epoch/source read token、driver.total_changes、局部 nonce/active scope、角色/全 Limits、完整 inputs 和 origin 各字段。inputs 的完整集合由未来生产者负责，固定指纹本身不能证明“没有漏传事实”。bytes 指纹只是漂移检测，不代替逐字节原验证。实际 role 的 None/六维值必须由生产者按原调用确定，不能选择较宽值。

严格入口先检查；draft_gate、own_project、validate_source_family、compile_preview 返回后立即检查；family 判断后、origin 消费前及输出返回前检查。即使 candidate 改成其他家族也直接拒绝，无 fallback。任一异常/漂移或离开工厂作用域后永久失效，原异常对象原样抛出，不用 finally 的 current 检查覆盖原异常。重入同 facts 拒绝。默认及普通 dict 的原匹配/fallback 分支保留。

当前 pin **不重核 Grant、批准、source ALLOW 或当前截止**，不能作为 fresh Authority。未来完整图生产者仍须在每个敏感回调后、图完成及最后使用边界实际重核完整当前权限五元组 `(principal,runtime,project,resource,tool)`、原批准/source/Run/fence/stop/lease/所有期限。Source resolver 每个原边界仍 fresh 调用，不能从本对象缓存 ALLOW。G0/G1 必须独立创建及完整重读，不能跨五写传旧事实。

lifecycle.py 没有改动，原样透传 `_reuse_origin`。其 apps 前后仍有 family/schema/source bytes/logic 等调用和早返回；严格对象只封住 apps 的内部 fallback。未来调用者须先按原 owned scalar 分流排除 execution_source/archival/logic/correction/project 等非目标变体，并对完整 read_release 前后做 current pin。不得声称本批覆盖 lifecycle 每条内部边界，也不得把这些要求推迟到生产启图之后。

## 叶调用责任

| 叶 | 前置与仍必须保留的后续责任 |
| --- | --- |
| app_jobs._binding_queue_from_facts | 原 legacy reject、authorize/return_release 限制、correction scope/job_gate/必要失效后重新授权和 binding SELECT 已在原位置；此叶拒绝 owner/queue 身份后才允许读取 AppRun 私有正文。不能把叶当 job_scope gate。 |
| app_jobs._binding_app_run_from_facts | 原带 owner/instance/release 条件的 AppRun SELECT；本叶在所有 logic/project marker/body 检查前保留原缺失/指纹错误。 |
| app_jobs._binding_request_from_facts | 完整 request 逐原字段构造，logic marker 存在性、project.job_gate 等已经按原位置执行；不遗漏 PB/PA/correction/logic/project/offline/CSV/ownerGoal 字段。之后原 own_project→完整 frozen Limits→Release 仍执行。 |
| app_jobs._binding_release_from_facts | 完整 frozen Limits 已与 snapshot 六维相等；原 read_release/owner goal/csv/offline/对应 per-use bound 全通过；传该次实际 expected_resource，不能用 saved base source 替代逐次材料。叶不验证 Release 内容、frozen 或 per-use 合同。 |
| pb_use._review_identity_from_facts | base/saved 来自原已核 Release（logic 分支仍独立验证），身份/recipe gate 通过后才运行原 target current 材料+完整 Goal/权限。后面的 expand/PA origin/compile、Grant 全量收集、base_audit 和结果构造顺序未移。 |
| pb_use._bound_review_from_facts | 原 use pair/seals→frozen Run/AppRun→owned instance→历史 accepted revision/runtime（PA data_version）→完整 review 已通过。必须传完整 checked/frozen/request，包含 approved_grant_state；本叶仍以该角色实际完整 caller Limits 编译有效 candidate，不用 inherited manifest Limits 替代。后续 audit readout 只沿原 same-call 边。 |
| pb_use._audit_from_facts | 原 owned Run scalar→scope gate→base/meta/body/snapshot/owned release marker→logic proof（若有）→完整 base audit（或原受限 same-call/current-authority 路径）均已完成；传完整 meta/seal/request/frozen，没有字段投影或历史去重。 |
| gate._stage_target_from_facts | 原 stage scope/owned Run/full bound/current Instance+Release+app_run key；完整材料内容/hash/id 和完整 Goal 逐字段核对。不是 stage 许可。 |
| gate._stage_generate_from_facts | 原 stage target 后按 frozen future key 查询唯一 Generate、完整 model_source、trial runtime/ref、批准 pair、完整 Generate Run/frozen 读取已通过；本叶保持批准时点、完整 frozen Goal、generation 家族及 model 谓词。 |
| gate._stage_authority_fields_from_facts | 所有原 source/提取、recipe、Generation 全历史/accounting/ledger、Source 阶段全 Authority/accounting 和 stage deadlines 已通过。只产生部分字段 dict，缺 authorization_fingerprint，不能当 StageAuthority。原末位 authorization_fingerprint 实际读取后，原 StageAuthority/V2 构造才产生完整对象。 |
| spec._bound_clock_from_facts | 原 full binding、ACCEPTED 恰一、所有 family/per-use/logic/Goal/frozen contract 与原短路 generation_mode 检查已通过；此叶后仍原位置 counters 的完整历史/receipt、多重集/唯一性检查。两种 Limits 的 run_seconds 仍取原 min，不省其他维度角色校验。 |
| spec._bound_plan_from_facts | 原 counters/静态状态、validate_input（如启用）已通过；只重建完整 definition/input/source_hash/plan fingerprint，之后仍实际完整 audit（包括 per-use）；不能把 plan 当 bound 或 Authority。 |

本批无任何全量历史/receipt/ledger/NS/controller 检查删减或投影替代。没有把 P(pair/seal) DTO 升为 V(完整 Authority)。第一 guard 前后、permission-before-body、callback 返回后 current 检查及原 SQL/锁/错误顺序不得由未来新调用者重排；跨写事实一律失效。若下一批不能在已批准生产文件内满足这些责任，应先报告具体缺口，不静默扩范围。
