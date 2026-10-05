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

## F1-3 未知工具效果核对

GET /api/runs/{rid}/unresolved-operations 返回所有者的未知 Operation 元数据；POST /api/runs/{rid}/reconcile-operation 接收 operation_id、version、expected_fingerprint 和 evidence。没有“我认为失败所以重发”或手动设 VERIFIED 的入口。

Operation 的受信任请求与本地写入关联分别保存在 operation_intents、local_effects，与业务效果/原回执同一事务。核对只允许原注册工具、原指纹、原上下文，重新检查当前授权和冻结输入。纯读取/CSV计算可以在相同冻结输入上确定性回读；文本写入必须有原 Operation 对应的效果关联、对象和内容哈希，缺指针不能证明没写入。不执行原写入、不再次调用模型。

可信回读通过后恢复原工具反馈、标 VERIFIED，正常任务 PAUSED，另行 resume；取消意图且所有未知请求/效果已解决时 CANCELLED。内容已知不符标 EFFECT_KNOWN_INVALID，不重写、不补偿；未知适配器或缺请求/效果证据仍 OUTCOME_UNKNOWN，保留等待/核对状态。未知 Operation 或 RECEIPT_KNOWN 阻止 resume 和直接取消完成。Run 返回 known_effects（操作状态、工具及已知文本资源 ID/哈希），取消不是“没有影响”。OUTCOME_UNKNOWN 的公开 error.effect_known=false。

人工依据是审计说明；效果真实性来自 TRUSTED_LOCAL_READBACK，无法确认的事件标 UNCONFIRMED。费用和 Attempt 预约不修改。F1-3 新增接口只在 HTTP API 与账本层提供；通用核对未新增页面控件。外部业务工具仍禁用，不能凭合成断言宣称真实外部核对能力通过。
