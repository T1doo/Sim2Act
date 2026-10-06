# AT05 观察器与完整 PG 终态独立复审

新观察器静态未发现已确认的身份语义或常规 I/O 覆盖阻塞。原 manage 经 runpy 非 main 加载后调用原 main 一次；身份方法调用一次、值原样传回，process 返回真实 psutil 对象。命令、timeout、time、身份比较未放宽，日志仅安全元数据。先前 dispose 收尾也已 best-effort。

实际归档 JSON 断言：完整运行四个真实进程用例均 passed；before/after_commit 均 SUCCEEDED、结果各1，pause 为 PAUSED、cancel 为 CANCELLED、结果各0。四采样线程 thread_stopped=true，无采样 error_class。完整 PG 仍 **515 PASS / 1 FAIL / 1 SKIP**（739.18秒）；唯一旧 AT05 首次 start 返回1，API/worker exited，根因未明。

旧 before_commit 失败和新 AT05 startup 失败都保留。AB/BA 与本次恢复用例通过只能说明未复现，不能归因或签收完整恢复。psutil 原方法异常目前原样传播但缺单独字段级错误记录；legacy 无command的 expected_match 诊断不能代表原 fallback 比较结论。完整源码/日志哈希及限制见 JSON。

本审查未运行 fixture、PG、测试或网络，不操作进程，不修改产品或旧证据，不提升 Edge 接线/正式验收。
