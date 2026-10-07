# 下一只读切片：普通任务步骤与等待原因

由原V5 §7.4进度处理和§8等待/失联语义导出；基于本轮冻结UI源，新建独立worktree/本地分支，不能混入正在CI验证的commit。

只使用现有已授权Run inspect返回的events/known_effects/error/contract以及既有unresolved-attempts GET；不新增数据库表、API或授权，不自动续跑/核对/模型请求。事件仅映射已知类型为简明步骤标签和原持久时间，不渲染任意data/private context；最多最近20条。MODEL_RESERVED是尝试登记不是发送成功，TOOL_VERIFIED不代表目标验收。已知效果需核查与VERIFIED分开。

成果画布明确显示技术终态与目标验收NOT_RUN；WAITING_RESOURCE的GRANT_REVOKED/RESOURCE_UNAVAILABLE/RATE_LIMITED/OUTCOME_UNKNOWN以及RECONCILING/WORKER_LOST为具体等待原因，不虚构网络/服务失败；无error时使用待核对未知原因。未知Attempt告知不要重复发送，已有核对入口保留；页面读取不发写请求。

验收真实MockHTTP/Worker生成的ACCEPTED→CLAIMED→MODEL_RESERVED→TOOL_VERIFIED→STATE(PARTIAL)，原待授权/未知/失联合成负例，收敛UNKNOWN/SUCCEEDED或malformed receipt不冒认成功；XSS/text/time/20条限制/同源/切换项目身份/迟到响应。保留完整原events/raw receipt细节，页面新摘要不更改账本。当前切片不提升语义、完整P-B/F1/Win11/Release验收。
