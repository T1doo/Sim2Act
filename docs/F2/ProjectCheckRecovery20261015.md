# PROJECT CHECK 已知取消的过期所有权回收

发现的真实条件：原 PROJECT 自然 CHECK 的模型在途时先暂停、再取消，原 30 秒 lease 已经过期后返回。真实响应留存为 REJECTED_KNOWN，usage 已知、无 unresolved operation；旧 worker 正确丧失所有权，原 fail_owned 不写终态，而普通 claim 不接管 RECONCILING。旧历史失败保留在 project-check-history-evidence-20261015。

新增 project_check_recovery，仅在普通 Worker.once 的 claim 前执行原键回收，不发送模型请求、不执行应用节点、不增加预算、不延长旧 lease。必须是 RECONCILING、cancel_intent=true、旧 lease 真过期、result 未写入，且无 unknown。control_scope 与独立 PROJECT control_binding 校验原 Run、AppRun、accepted Event、RUN_META 双份、PLAN/START/JOB/SOURCE 索引和确定性 CHECK iid；停止权限不要求重新获取私有材料/Goal 的访问授权。

原模型 reservation/counters、received、rejected/settled 独立事件和持久 attempt fingerprint 必须完整且 usage known；所有 operation 必须已 VERIFIED 或 REJECTED_KNOWN。回收并不重新判断模型语义，也不把 UNKNOWN 认作失败后安全成功。已有 usage、reservations、响应档案、effect、SOURCE/Release、人工锁、CHECK 证据全部保留。单一事务把原 Run/AppRun 改为 CANCELLED，原 version/fence 各加一，使旧 worker 不再能 SAVE；追加含原绑定、attempt fingerprint、实际 known effects 的 PROJECT_CHECK_CANCEL_RECOVERED 回执与 STATE 事件。回执失败事务完整回滚，双 Store 竞争最多一份提交。

同时修复已实测的 PROJECT QUEUED pause→resume：command_job 的首个 load_binding 使用原 frozen_contract.limits，后续重用同一原契约；旧 stop metadata 路径不读取私有材料/Goal，不增加/重建预算。非 PROJECT 与无 metadata 的停止逻辑保留既有行为。

普通 Worker 每次最多扫描 16 个候选，进程内仅保留按 Run id 轮转的游标；游标不是权限或执行证据，冷启动从头检查，不修改 Run。坏项目权限、缺失/损坏证据只跳过该候选，普通 queued 工作仍交给原 claim；后续轮次继续，坏候选不能永久占住首批。项目锁在 Run 锁之前取得，事务内复核原 owner pair；实际 PG 锁行为仍 NOT RUN。

停止的授权核验只使用原绑定与公共索引，不重读私有材料/Goal；但完整回收的原账审计需要读取已持久化的 Run context/messages、attempt parameters/response 字节，重算独立事件 fingerprint。它不重放、不披露这些内容，不以撤权材料授权执行或修改应用。不能把完整 helper 描述为仅标量元数据读取。用户读取完整 usage/effects 的现有页面 API 仍要求当前内容权限，撤权后只能公开控制回读。

独审后的候选 4921125b237ceedd91d5373847fa9cf708ced0e2，由根精确重冻结为 79 个模块（原 78 加 project_check_recovery.py），资格 pin 278e254e19505cb1891d94118380a03dab24b15eb751cf64811cf56b0e82029c；原 ANCHOR/CHANGED/config 排除与源 anchor 保留。实际执行冻结 SHA 59a5157691b44d5acb5f0b2f401940e039b24180，479 个 src/tests/pyproject 文件前后哈希零差异。

recovery-first 实际 26 PASS、0 FAIL、0 ERROR、0 SKIP，256.722875 秒：4 个真实核心测试加 22 个原资格负测。两个全新 fixture 实际等待原 30 秒 lease，真实 mock Worker/public commands、已知恢复、未知保留、撤权后双 Store 单胜、9 个坏证据反例及缺失 Release、回执故障事务回滚、旧 worker fence 拒绝、原 QUEUED pause→resume，以及 32 个显式未接受坏候选不阻塞普通真实 queue claim 和后续真实取消恢复均通过。原历史失败仍保留，未以新 fixture 的 PASS 改写原失败。XML SHA256：0b1e3151edd6e3339a3935e6436d77321ba014c81496f0d900c09ba70c1f873f；完整源码快照、raw stdout/stderr、XML、公开回执位于 project-check-recovery-evidence-20261015/author。

受影响四文件 Ruff PASS；三个 product 文件 scoped mypy 仍报告既有 tools.py:210/264 两错误，未报新增 helper/worker/app_jobs 错误，不能称全库 mypy 通过。真实模型、费用、Windows、PG、原生浏览器、完整 P-A/P-B、人工语义、旧源码升级、部署与远端 CI 均 NOT RUN；整个产品仍 UNKNOWN/NOT_ACCEPTED。
