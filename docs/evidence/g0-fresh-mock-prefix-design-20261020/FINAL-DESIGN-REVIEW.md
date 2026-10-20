# 最终设计 ACK 补充

结论仍为 **CONDITIONALLY_FEASIBLE_DESIGN_ONLY_NOT_START_ACK**。初审 DESIGN-REVIEW.md/.json 原样保留；唯一 P2 文档精度已闭，无未闭合 P1/P2。这不是 harness/启动 ACK，也不是新执行窗口授权。

最终只读复核 README SHA256 `cce525ab429eb01d0bcfef27268de08172464d4e24a5763c1afaea5a8ad5ef87`，design.json SHA256 `226adae42456bc614f784cd322d6eeacb5b29b50952557c847e418bde65a18db`。设计元数据已统一采用 line..end_line 包含两端的完整源码行字节，保留缩进及换行、lineno不含装饰器；18份文件完整SHA与24项源码行段SHA全部实核一致。此前21/3项采用不同换行口径的问题已在元数据闭合，无产品或设计语义变化。

文档现准确列明 Worker.process→app_jobs.process_job→pa_spec_apps.process_job→text_workflows.process_job，实际心跳 finally 位于最后者1093行。stopped.set()只请求停止，join(timeout=2)只进行有界等待；必须另核线程存活和对应自有PGID终止，残留/清理不确定均UNKNOWN。Python3.12官方 [Thread.join](https://docs.python.org/3.12/library/threading.html#threading.Thread.join) 明确指出应另用is_alive区分线程终止与等待超时，支持此限定。

Python3.12官方 [RLIMIT_FSIZE](https://docs.python.org/3.12/library/resource.html#resource.RLIMIT_FSIZE) 只定义进程可创建文件的最大大小；它自身不证明目录总字节或文件数上限。因此封闭文件清单、有界writer、SQLite临时路径及父进程输出/receipt仍是未来具体harness的执行前提，当前不宣称已保证64MiB硬界限。

其他非DomainError、资源/信号/observer/cleanup错误均保留UNKNOWN/INCOMPLETE，不替代原业务拒绝。新增诊断说明与源码一致：命名期限最多12项（3固定+最多5非None角色+4尾项），保持原顺序；run_seconds命名项已是created_at+时长的绝对截止，不能二次相加。五阶段wall/check/input_key是同stage前后快照差，最多5项、早拒绝可缺，不是与历史运行相减。没有补造缺失finite或成功时的拒绝快照。

剩余启动条件不变：具体harness/退出shim尚未实现，直接DBAPI写入路径闭合及实际目录硬限尚未证明，也没有新的一次执行窗口授权。此轮只封存文档，不实施harness。本人产品导入、Mock/PB/G0、测试、Worker、数据库打开及launcher执行均为零，没有分配执行目录；官方网页只读查询。
