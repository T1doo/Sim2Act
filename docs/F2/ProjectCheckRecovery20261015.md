# PROJECT CHECK 已知取消的过期所有权回收

发现的真实条件：原 PROJECT 自然 CHECK 的模型在途时先暂停、再取消，原 30 秒 lease 已经过期后返回。真实响应留存为 REJECTED_KNOWN，usage 已知、无 unresolved operation；旧 worker 正确丧失所有权，原 fail_owned 不写终态，而普通 claim 不接管 RECONCILING。旧历史失败保留在 project-check-history-evidence-20261015。

新增 project_check_recovery，仅在普通 Worker.once 的 claim 前执行原键回收，不发送模型请求、不执行应用节点、不增加预算、不延长旧 lease。必须是 RECONCILING、cancel_intent=true、旧 lease 真过期、result 未写入，且无 unknown。control_scope 与独立 PROJECT control_binding 校验原 Run、AppRun、accepted Event、RUN_META 双份、PLAN/START/JOB/SOURCE 索引和确定性 CHECK iid；停止权限不要求重新获取私有材料/Goal 的访问授权。

原模型 reservation/counters、received、rejected/settled 独立事件和持久 attempt fingerprint 必须完整且 usage known；所有 operation 必须已 VERIFIED 或 REJECTED_KNOWN。回收并不重新判断模型语义，也不把 UNKNOWN 认作失败后安全成功。已有 usage、reservations、响应档案、effect、SOURCE/Release、人工锁、CHECK 证据全部保留。单一事务把原 Run/AppRun 改为 CANCELLED，原 version/fence 各加一，使旧 worker 不再能 SAVE；追加含原绑定、attempt fingerprint、实际 known effects 的 PROJECT_CHECK_CANCEL_RECOVERED 回执与 STATE 事件。回执失败事务完整回滚，双 Store 竞争最多一份提交。

同时修复已实测的 PROJECT QUEUED pause→resume：command_job 的首个 load_binding 使用原 frozen_contract.limits，后续重用同一原契约；旧 stop metadata 路径不读取私有材料/Goal，不增加/重建预算。非 PROJECT 与无 metadata 的停止逻辑保留既有行为。

实际验收等待候选源码独审、精确软件资格重新冻结后执行。测试将实际等待原 30 秒 lease，包含真实 mock Worker 接收、原公开 commands、已知回收、未知保留、撤权停止、坏索引/响应/预算证据 fail closed、双 Store 竞争、原 worker fence 拒绝、回执故障回滚和原 QUEUED resume。真实模型、费用、Windows、PG、原生浏览器与人工语义均 NOT RUN。
