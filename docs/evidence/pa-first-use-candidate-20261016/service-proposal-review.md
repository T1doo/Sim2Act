# 候选演示Worker生命周期调整：只读设计审查

基线e7dcdb4ff25e5765be5dc34a4edc72ecba1929bc；根新精确0f前缀trace只读复核，未运行新fixture、Worker、模型或原Run。

结论：可以独立修进候选脚本的普通Worker服务生命周期，不必先自然复现旧失租；但不足以认定0f首异常根因已经定位。旧Demo.once检查worker.once返回True后仍GET真实状态并明确FAIL，不能简化成“把True直接伪造成功”。旧演示原有限定一次claim条件。新版本从有限一次调用改为持续普通服务、可能出现原规则回收后的多claim，是必须披露的执行范围变化；不能称生产租约故障修复或藏成once。

## 已复核的新trace

/workspace/pa-use-running-investigation-20261016/baseline-first-pa-outcome.json实际PASS，首P-A新材料per-use结果v1；该次Worker.once22.479083秒。trace5188条，未见fail_owned_reason；heartbeat两次BEGIN IMMEDIATE真实BUSY(code5，5.018/5.056秒)，随后终态晚到VERSION_CONFLICT Stale worker lease。原产品/预算/调度未变。此成功证明同原链能够在一次claim完成，不重现原0f的RUNNING/errornull，不确定最初异常。

独立摘要/tmp/f2-pa-lifecycle-proposal-trace-independent.json，保存3原件hash。只读解析，未执行reproduce.py。

## 可接受的最小生命周期合同

- 仍用同一新自有SQLite mock目录、原Worker和原Store.claim/guard/心跳。普通worker.main本就循环once+原1秒cadence；脚本不要创建自己的恢复executor或目标特许claim。
- 单次HTTP受理、固定原key/Goal/Run，等待目标真实状态；不得重发受理、重建Run或改创建时间。成功只按实际SUCCEEDED（生成按其实际PARTIAL等指定终态），不能从once True/False推断目标状态。
- 截止只来自原accepted created_at+原run_seconds，不以循环/新claim/观察重置。每次once之前核未越界；在途业务仍靠原guard与deadline裁决，不许延lease/timeout/busy预算。
- FAILED/CANCELLED为失败；WAITING_RESOURCE/RECONCILING/PAUSED/WAITING_APPROVAL等需人或权限输入的阻塞状态必须停止并保留/报FAIL，不允许自动resume、清unknown或继续试到成功。不可吞Worker/SQL异常后无限重启服务。
- RUNNING lease有效时没有新的claim资格，按普通cadence服务即可；过期时Store.claim原恢复会WORKER_LOST→RECONCILED→QUEUED，再CLAIMED。此为真实恢复路径，fence可能从1跳3，不能标成“一次claim/fence1”。记录全部claim、状态转移、每次once耗时/TrueFalse、Worker身份与最终原deadline。
- 新fixture顺序产生的非预期Run必须显式记录/停止，不加私有目标选择器重排队列。普通claim选择原最老QUEUED。
- 禁止每秒GET完整/api/runs判进度：inspect_job本身BEGIN IMMEDIATE+完整来源证明会新增writer竞争。可对该自有合成Run做metadata-only标量状态/时间观测，最终终态才原API完整验收；metadata仅驱动服务生命周期，不代替任何产品权限或成果验证。
- 线程/进程停止要保留原Worker.stop、心跳收尾；不遗留后台业务，不删未知锁/进程。deadline导致停止只报未成功/保留，不人工写数据库终态。

## 最小验证与反证

受控轻测应实际复用脚本service helper，证明：第一次once True但目标RUNNING不会假成功/停服务；第二次普通once才目标终态；once False也不能推断成功；明确FAILED或WAITING_RESOURCE/RECONCILING停止；accepted deadline到期停止且不重置；异常不吞；不会再次POST提交。受控worker应清楚标为synthetic语义测试，不能说自然失租复现。

一次新实际安装fixture验证P-A新材料首v1、同实例另一新材料v2、原v1保留及冷读可用即可。它证明脚本/产品路径在本次实际时序可运行，若没有发生WORKER_LOST/reclaim，不宣称自然恢复分支已验证。若发生多claim则把ledger原样列出，不按一次claim门签收。没必要强制失租或扩恢复矩阵，也不应靠这种循环把阻塞/未知/拒绝变PASS。

旧0f FAIL、原最初异常未知、旧F9时序未复现仍保留。新版本不能沿用c9限定原材料候选包的SHA或PA新材料NOT_RUN说明，必须以新源码/包/实际证据重新标注执行范围；c9已验产物原封保留，不改写历史。
