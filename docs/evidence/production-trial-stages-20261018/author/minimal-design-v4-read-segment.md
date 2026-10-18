# 实际Source阶段性能补充（不放宽原期限）

run4在9c0d7bda冻结实际走通gen3、原候选、Release/实例、Source原批准及claim/read；首NS Core请求归档后，发送前阶段完整proof重复，lease失效，Run仍RUNNING/Attempt STARTED，NS adapter0，没有自动恢复/重发。保留299.30秒首节点ERROR，不冒称链通过。原Core预留/未知状态保留，不据缺journal推断免费。

一次closedrun4 fixture只读cProfile：gate.stage_review 14.805秒，_stage_current14.629，13409SQL；verified_candidate5次11.147秒。无模型/网络、DB bytes SHA前后相同。优化对照仅调用私有_stage_current（因为旧批准的软件FP不能随新代码迁移），6.560秒、4782SQL、完整_verified_candidate1次；同DB bytes SHA仍相同。此为性能定位不是资格/重签/模型成功。

最小实现复用现pb_natural_specs._SourceReads及已存在write-epoch失效hook，不新建缓存模块、Grant、executor或跨TX许可。仅原P-A test_only SQLite且三条actual Attempt为精确新JOURNAL_VERSION时，_stage_current在同一个同步read call内保留现SourceReads上下文。goal_applications原verified_candidate完整函数原体移名_verified_candidate，首次仍完整所有source/history/read/checker/candidate/anchor验证；相同run完整指纹/limits/owner key在同c/Store/engine driver/Tx/thread/epoch方可复用完整结果copy。每次先source_scope_gate，再recheck_proof_authorities；run/limits在重核前后仍相符；异常清空、不允许inflight结果被复用。任何非SELECT/SQL写入、跨TX/线程/driver、退出、回调导致epoch变化，现hook立即pop token+epoch递增，fallback完整原证明。旧PB和旧PATrialBinding不扩大到新outer read scope。

保原每个发送guard、source原loader、原approval/阶段/currentRun version/fence/cancel/lease/Run300/每60秒以及Cold同trial Source2 proof。不同TX不复用任何证明，journal reserve/mark/receive仍实际fresh；不延长lease/Run帽，不把历史StageAuthority作为send权。

仍4唯一资格；B原fresh-prefix只读负例中增加一个必要窗口：同段完整候选proof重复得到独立相等结果，然后SQL写FAILED使原token失效，完整重验拒绝；拒绝窗口全55表不变，rollback后prefix回原状，无新模型调用。不扩旧恢复/取消矩阵。run5新软件FP/新原批准/freshDB重跑本次新4节点，以实测为准。
