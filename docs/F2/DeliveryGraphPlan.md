# DeliveryGraph 核心切片 Plan

基线：`e700db211378e67ca99529f4a5270f0ea6162769`（含远端 `e828c066ec63689fe5de5d66f650eda33c0086e8`）。独立分支 `dev/delivery-graph-core`。本线仅新增 `src/sim2act/delivery_graph.py`、`tests/test_delivery_graph.py` 与本 Plan/Log；主线负责后续适配。对应原 V5 产品 §9，不签收完整增量修改、发布或 V5 验收。

| task_id | 目标 | 状态 | 验收 |
| --- | --- | --- | --- |
| DG-01 | 严格 AppManifest/ActionSpec → 闭合 DeliveryGraph | LOCAL_PASS | 真实 CSV/agent 声明、手绘多节点 oracle、六边/来源、版本与指纹、输入不变 |
| DG-02 | 当前授权/版本下保守变更规划及回执复用 | LOCAL_PASS | 确定/不确定传播、检查/包装失效、未知应用/项目扩验、锁、幂等/篡改/撤权 |
| DG-03 | 独立审查、专项及相关回归、普通独立分支 push | REVIEW_PASS / PUSH_PENDING | 精确 source/commit、限制及主线接法 |

## 冻结接口

`derive_manifest_graph(manifest, actions, source_versions, stable_ids, context, platform_limits)` 调现有 `contracts`/`preflight`，不调数据库、工具或模型。manifest/actions 为 JSON dict/list，platform_limits 为现有 Limits 或同格式 dict。source_versions/stable_ids/context **必须由服务端适配器从可信状态构造**，不能透传 HTTP 请求体中的同名对象。authorized=true 必须代表适配器已验证这个精确清单的全部权限请求、当前用户∩应用身份∩项目/资源授权及目标/外部快照归属；不能仅以已登录或拥有项目代替。授权代次必须覆盖实际相关 Grant 的变化。

逻辑键为：`goal:<goal_ref>`、`source:<resource_id>`、`rule:<tool|prompt|check>:<ref>`、`action:<step_id>`、`artifact:<output_field>`、`view:<component_ref>:<output_field>`、`check:<check_ref>`、`manifest:<app_id>`。每次 workflow 调用拥有独立 ACTION 节点；同一 ActionSpec 可复用但不同调用不混为一节点。完全相同的 view 键重复时拒绝，后续持久 ID 由主线稳定映射。

- `source_versions`：GOAL/SOURCE/REQUIREMENT/CHECK 的全部外部逻辑键 → `{revision: 严格正整数, content_fingerprint: 64位小写SHA256}`；不接受缺项或额外项。
- `stable_ids`：全部逻辑键 → 服务端稳定 ID（现有 `<小写前缀>_<32位小写hex>` 格式），ID 不重复。
- `context`：闭合对象 `{project_id, app_id, authorization_revision, authorized, resource_ids, node_revisions, locked_nodes, source_versions, dependency_edges, unknown_dependencies, graph_fingerprint}`。前八项必填；后三项默认 `[]`、`[]`、`null`。node_revisions 必须覆盖全部逻辑键，ACTION/MANIFEST/ARTIFACT/VIEW 修订与声明一致。locked_nodes 使用稳定 ID。
- `dependency_edges`：`{upstream, downstream, type, provenance}`，边方向上游→下游；type 为 DATA/RULE/PRESENTATION/SEMANTIC/VERIFIED_BY/PACKAGED_IN，provenance 为 DECLARED/ACTUAL_READ/HUMAN_CONFIRMED/MODEL_CANDIDATE。重复完整证据、悬空或循环拒绝。同一依赖的声明与实际读取可分别记录。
- `unknown_dependencies`：`{node_id, scope: APP|PROJECT, reason}`。未知读取可能包含任意变化材料，即使无声明路径也扩验；不能将缺边默认为无关。

返回图包含节点原始 definition、稳定 ID/逻辑键/kind、严格 revision、project/app、locked 和 content_fingerprint；节点指纹包含定义及上游修订/指纹/边证据，顶层 graph_fingerprint 包含全部图内容。按确定顺序返回，不创建 Release、结果或授权。规模上限 128 节点/512 边/256 KiB JSON。

`plan_change(graph, expected_graph_fingerprint, change_request, current_context, previous_receipt=None)` 的 current_context 沿用上述结构，但 graph_fingerprint 必须是服务端先前保存的派生图指纹，不能从当前请求图现场重算后当锚。锁、资源授权、外部版本及授权代次均重验；改变快照需要重新 derive。

change_request 为闭合 `{request_key, project_id, app_id, changes: [{node_id, expected_revision, expected_content_fingerprint}]}`。不接受客户端“仅展示”或影响集合，空变化、重复节点与旧节点版本拒绝。PRESENTATION 是图中的依赖关系，不代表用户声称的变化已证明只影响展示；照样传播到下游 CHECK/MANIFEST。

返回 `delivery-change-plan.v1`：请求/图/上下文/计划指纹，changed_nodes、definite_impact、uncertain_impact、revalidation_nodes、revalidation_scope（NODES/APP/PROJECT）、revalidation_checks、invalidated_packages、retained_objects 及 global_invariants。SEMANTIC/MODEL_CANDIDATE 路径不当确定性证据；未知扩验包括本图所有对象，PROJECT 要求主线另调度该项目其它应用的图/检查。对 MANIFEST/RELEASE 本身的整体变更也扩验 APP，因为此请求没有可信字段级差异证明。声明中的 check 依赖与所有锁定资源均显式入图，不静默遗漏。不确定不代表已改内容。

previous_receipt 是服务端按 request_key 保存的先前返回值。同键同参复用前完整重验当前授权/版本，并与新鲜计算结果逐字段一致；异参或篡改拒绝。本纯函数没有存储，无法在未提供先前回执时识别已使用请求键；主线须持久化幂等账本并序列化同键竞争。没有执行补丁、检查、业务写或发布。

## 错误及适配边界

旧图/节点/快照及协调图篡改 `VERSION_CONFLICT`；跨 project/app、缺当前资源权限或授权代次变化 `PERMISSION_DENIED`；影响集命中锁 `LOCK_CONFLICT`，原图/内容零修改；闭合结构、重复、悬空、循环、严格 bool/规模错误 `INVALID_MANIFEST`；既有 preflight 保留其预算错误。

现有 preflight 可能接受 validation_suite_ref 未列入 dependency_lock 的声明，本图接口因无法锁定该检查版本而显式返回 INVALID_MANIFEST；也拒绝没有实际 outputs producer 的可选 VIEW，不能绕过冻结或裸抛 KeyError。既有 contracts/preflight 不改。

现有 schema 没有独立 Requirement、Release、人工锁、实际读取或未知依赖字段：REQUIREMENT 从锁定工具/提示定义派生，checker 实现定义使用独立 REQUIREMENT 节点，实际待重验检查使用 CHECK 节点，避免检查实现依赖与对象→检查边形成循环；GOAL/外部内容的版本由可信快照提供；锁/额外证据/未知范围由 context 提供。本片不改 schema，不凭空生成 Release，不把声明提升为实际读取。ARTIFACT/VIEW 是清单的逻辑产物和展示定义，不冒称已有业务结果。ACTION 的 step_id/VIEW 的逻辑键重命名会成为新逻辑对象，主线若要保留身份须提供明确的稳定命名/迁移策略。

默认安全上下文只证明调用方提供的当前授权快照；本模块不查询实际权限，不提供客户端自授权功能。补丁/后续发布必须由主线再次核对动态权限和全部版本。本轮 0 模型网络/DB调用，Win11/browser/真实业务写/完整增量发布 NOT_RUN。

## 最终本地验证

见 [DeliveryGraphLog](DeliveryGraphLog.md)：83 项图专项纳入最终 144 项相关回归全部通过；Ruff 全 src 与专项测试通过，Mypy 38 source files 通过，独立复审三项发现已修复。此处只记录已取得的本地结果，提交/push 以最终 git 回执为准。
