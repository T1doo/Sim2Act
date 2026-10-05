# F1-2 未知模型请求人工核对

原 worker 失联且存在 STARTED Attempt 时，不自动重新请求模型。请求预约中持久化消息、工具定义、请求模型的指纹；核对绑定该指纹和当前 Run 版本。账本会提升 fencing token，使原 worker 失效。

接口：GET /api/runs/{rid}/unresolved-attempts（所有者可读元数据，不返回请求内容）；POST /api/runs/{rid}/reconcile。需要 attempt_id、version、decision、expected_fingerprint、非空 evidence 和 acknowledge_unknown_cost=true。response 与 response_json 只能二选一；原始 JSON 在服务端解析，拒绝重复键。

| decision | 操作与后置状态 |
| --- | --- |
| record_response | 记录已经取得、可对应原请求的完整响应；检查模式/模型、响应结构、工具参数、当前输入/成果授权；只能有一个未解决模型请求且请求上下文一致；保持 PAUSED，不调用模型或工具，需另行 resume |
| close_unknown | 不导入响应，不抹除成本或已发生效果；当前 Attempt 为 CLOSED_UNKNOWN，其 error 为 OUTCOME_UNKNOWN；没有其他未知请求时 Run 为 CANCELLED |

先前取消意图不可被导入响应逆转，导入后仍 CANCELLED。数据授权已撤回时不能导入结果，但所有者仍可通过核对接口结束未知请求。旧版本、重复核对、其他主体、错误指纹、缺确认、截断结果均拒绝；旧 worker 不可再写入。任何 DISPATCHED/OUTCOME_UNKNOWN 工具效果仍阻止这类模型核对，不能用结束模型请求冒充工具效果已知。

原 Attempt 的 usage、reserved_tokens 和预约记录保留，不根据人工响应修改用量；缺失用量保持 unknown/null。审计事件标记 USER_SUPPLIED，保存主体、证据说明、请求/响应指纹。人工结果不是上游账单真实性证明。历史无请求指纹的 Attempt 只能 close_unknown，不能导入恢复。

界面位于现有项目成果画布，提供两种核对方式、依据和未知成本确认，保存不会自动继续；不是第四工作区。授权撤回后的结束可走所有者核对 API，界面读取成果仍受授权检查。通用外部效果人工核对、已知效果汇总面板和文件/数据库跨事务恢复尚未实现。

验证：test_reconciliation.py、test_runtime_coordination.py 和真实 localhost 浏览器操作。所有证据是明确合成的 MOCK/FAULT_INJECTION，未真实调用书生。
