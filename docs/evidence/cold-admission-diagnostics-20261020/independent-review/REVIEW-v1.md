# Cold admission 诊断补丁只读独审（首版）

结论：发现一个 P2，修复前不签最终 ACK。无 P1。

`_ColdGraphRead.input_key/check` 的 `_diagnostic_counts[i] += 1` 没有异常隔离，且 check 自增位于原 try/invalidate 外。仅诊断状态损坏（如 counts[0]=None）会提前抛 TypeError，掩盖原业务校验，直接调用时绕过原 sticky invalidation。此为静态源码分析，没有执行探针。最小修正是仅对两次自增做窄 Exception 保护；坏计数不得阻止原 input_key/check，阶段采样标 incomplete，不能新增全图调用或缓存。

建议仅加一个真实本地 CGR 合成测试：损坏诊断计数后，有效原输入仍完整序列化；再修改原输入必须继续 DomainError 并 sticky invalid。无需 PB 或 Worker 流程。

其余源码审查未见新增 P1/P2：原 end→pin→stop 顺序保留，stop 仅一次，min 短路保留；finite 表达式顺序不变；五阶段只单调时钟和计数快照；actual Run 快照捕获于 RunCheck 后且不重读；私有异常仅标量和固定标签，public/message 不变；成功 output 不新增诊断。

已只读核作者 JUnit 原件：7 passed / 0 failure / 0 error / 0 skipped，0.541 秒。此是作者局部合成测试结果，审者执行 0；不证明 PB、模型、PG、期限或性能资格。三文件精确 SHA256 见 REVIEW-v1.json。
