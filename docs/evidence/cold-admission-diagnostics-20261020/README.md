# 首次 Cold admission：最小拒绝诊断

产品与测试提交：`6301e19964bd4c309d98ec9f004a6e79d3b03958`。它只补齐诊断，不是性能修复。[上一完整 Mock 失败](../pb-full-current-once-20261020/README.md)的 G0 32.041 秒、首 binding 4.368 秒及 W5/G1/finalguard 未到达结论保持；其失败帧的 finite/end/stop 没有记录，不能事后补造或用终库 lease 代替。

## 保留什么

仅在 `_ColdTrialGraph.commit` 第一次 admission 的原 `Production admission expired during verification` 拒绝处，给同一个 DomainError 添加私有 `_cold_admission_diagnostic`：

- 按原顺序、使用原已求出值命名 finite：RunCheck、source、natural_spec_clock、各有效 role、frozen、draft、call meta 和 call node。
- 原 `end` 和原那一次 stop 读取值。仍然是 `end=time.time()` → 原 pin → 单次 stop → 原短路表达式；没有拒绝后重读或推断 stop。
- RunCheck 的 checked_at/deadline，以及 `_graph_run_context` 当次已有 Run 的 lease_until/version/fence 标量快照。标签明确说明它是此前读取并用于 RunCheck 的那一行，不是拒绝瞬间的新查询。
- 五个固定外层调用：`_prepare`、`_graph_run_context`、`_graph_pb_accounting`、`_graph_resolve_trial_source`、`_graph_pb_archive_chain`，各记录单调时间差及已有 check/input_key 入口次数差（包括失败入口）。不做深层逐字段观测。

原异常对象、code/message/public、SQL、业务回调、鉴权及所有完整全图检查顺序保留。诊断和两个浅计数不进入 graph inputs、指纹、typed cohort、权限或成功 output；不缓存、不删除边界、不增全图调用、序列化、哈希或产品 I/O。原完整测试的既有 failure JSONL helper 只额外保留这一私有字段；产品 API 不公开它。

私有字段只含固定标签、期限数字、version/fence、bool 与最多五个计数/时间记录，不含 ID、正文、token、URL、账户或指纹。诊断仅尽力处理普通 Exception，采样不完整会标记 incomplete；不承诺在终止、资源耗尽等情况下产出记录。

## 开销与独审

每个现有 check/input_key 入口新增一次受窄 Exception 保护的浅计数。首次 admission 五阶段各两次单调时钟读取和有限标量记录；成功路径不构造完整拒绝报告。开销非零、未基准测试，不能从这些局部测试宣称性能不变、性能修好或租约通过。[Python 官方 time.monotonic 文档](https://docs.python.org/3.12/library/time.html#time.monotonic)用于确认只取两次读数差，业务期限仍使用原 time.time。

[最终独审](independent-review/FINAL-REVIEW.md) ACK：原 P2 已闭合，无未解决 P1/P2。P2 是计数损坏可能抢先抛错；两处自增已隔离故障，两个真实本地 CGR 参数用例证明坏计数不会阻止原完整字节计算，原输入漂移仍 DomainError 并保持失效。首版审核先读旧 diff、后采 SHA 时 writer 已落修复，因此其 hash 不是缺陷版冻结证明；原件保留，最终审核明确解释并以最终三文件精确 SHA 为准。

`raw/behavior-ast.json` 与配套脚本只解析源码，不导入产品：移除明确新增的诊断语句/包装、将单次物化 stop 内联回原位置后，`_ColdGraphRead.__init__/check/input_key` 和 `_ColdTrialGraph.commit` 的语句树与 `a952866022a3976eedf045408778ea901760646b` 一致。这是静态顺序检查，不是零时序影响或完整运行等价证明。

## 实际验证

最终三个文件的字节与上述提交完全一致（执行时 HEAD 为证据提交 `4f60bbcb948d1e1c31d1dfa8796154d62a6e3f3c` 加这三份修改）。[validation.json](validation.json)保留命令、精确 SHA 与各次 JUnit。

最终 **34 passed / 0 failure / 0 error / 0 skipped，5.568 秒**：9 个新增诊断局部用例、22 个既有 guard delta 用例、3 个 fixed-key 用例。包含原 end→pin→stop 顺序、stop 短路、pin 错误优先、诊断故障不掩盖原异常、公共输出隔离、已有 Run 快照不被后改覆盖、原完整图重新序列化及漂移失效。合成首拒绝已通过实际 JSON helper 保存至 `raw/synthetic-admission-rejection.json`；其中五个 1 秒时长来自测试替换时钟，绝不是性能样本。

首次局部运行因合成夹具漏 binding 而 6 failed / 1 passed，补齐夹具后 7 passed；随后相邻用例 32 passed；独审 P2 修复及两个坏计数用例加入后为最终 34 passed。早期 JUnit 原件保留，不把早期候选当最终冻结验证。一次 Starlette/httpx 弃用 warning 保持原状。

这些仅是局部合成协调器（语义/SQL producer 使用明确 stand-ins）和真实本地 SQLite/CGR 原语；没有 Worker 构造/claim、完整 PB、producer 探针、模型请求、PG、部署、CI、凭据或权限变更，也没有延长期限。最终独审只读、未执行产品或测试。

## 剩余因果条件

诊断现已能保留将来的首次 admission 拒绝证据；本轮没有新的完整链阶段数据，所以尚不能判定五阶段中的独占热点或唯一最小期限。本次不选择推测性性能修改，不重做首 binding/validator/SHA 方向，也不把诊断交付当作 G0 修复。后续安全核心修改须基于实际固定阶段差值与完整有限期限，而不是历史聚合量猜测。本提交没有新增完整 PB 执行或重跑授权。

原件及派生报告的大小/SHA 见 [MANIFEST.json](MANIFEST.json)。
