# Fresh Mock prefix → first G0：只读设计独审

结论：**在原三项隔离合成夹具边界内有条件可行；不是 harness/启动 ACK，也不是新的执行授权。** 当前无源码层“必须先调用 Cold2/W5 才能进入 G0”的不可达障碍。实际执行预算仍为零。

## 已核实的路径

`configured` (tests/test_spec_production_controller.py:71) 原样替换环境断言、合成 account evidence resolver 与 software qualification，并让生产形态 Provider/Worker 的 transport 仍为 None，由 AsyncClient 构造替换指向精确 MockTransport。这是原合成测试合同，不能称真实生产资格。原 factory.receive 记录真正 exchange；它直接调用目标 handler。原 PB Source handler (tests/test_pb_spec_production_controller.py:285) 又同步调用两次 normal.handle_request，因此最多六次出站 Mock exchange 对应最多八次 Mock 方法入口，两个计数不能合并。必须在 setup 之前安装两个独立的执行前上限。

`apps.ready(style="ordered")` 的三次 Generate、同 Source Run 的 stage_review/StageApproveInput/approve_stage、两次 Source 和原 extraction review/consent/extract/resolve/release/instance 均有正常源码路径。refused_archive_copies 是独立损坏矩阵；去掉该旁支不需要伪造 Source provenance 或跳过正常 extraction 证明。原冷 Store/client 重新打开和 cold stage approval 保留。正常六次收发至少五个 60 秒间隔；480 秒前缀预算在静态上没有必然矛盾，但不能保证当轮一定达到 G0。

`advance_model` (natural_spec_runtime.py:3333) 在 Cold 首响应的接收事务、record_response、renew、lock_live 后，在同一真实事务进入 `_cold_model_before`。五个指定函数确有该正常路径；本次只解析/读取其源码，没有导入或运行。`_cold_model_before` (2959) 包含首 binding、第一 commit、所有原 body 检查、第二 commit、scope 完整 hash 退出及最后 stop/finite 检查；首 commit 成功不等于完整 G0。

原 context 成功返回后下一句就是 attempts→VERIFIED 的 W5 首写 (3619)。测试 wrapper 若完整委托原 context，并在其成功退出后立即抛出专用 BaseException，能够在该首写前退出。若原 G0 DomainError 拒绝，应先让原 scope 完整展开/失效，再以同一原异常为 cause 抛该专用信号；advance_model 的 DomainError 拒绝块因而不执行。Store.tx (db.py:726) 捕获 BaseException 并 rollback；Worker.once、text_workflows 的失败写入捕获 DomainError，不会吞该专用信号。其他非 DomainError 异常或独立护栏失败必须保持 UNKNOWN/INCOMPLETE，不能改名为原业务拒绝。

## 一项文档精度与后续必需门

P2 文档精度：实际 natural-job 心跳 finally 在 `text_workflows.process_job:1093`，由 `pa_spec_apps.process_job:2290` 委托；`Worker.process` 自身在此路径只路由。finally 是 stopped.set()+join(timeout=2)，只能证明请求停止及最多等待两秒，不能单独证明线程已停。未来须核 thread/connection/client 生命周期和自有进程组结束；仍存活或清理不确定应 UNKNOWN。已向根报告，不是新的产品改动要求。

其余均为设计中已承认、仍未实现的执行门：确切首次 Cold 对象/事务限定；原 context __enter__ 也计入 G0；G0 内 transport 永久零额度；原 SQL 执行前拒写且直接 DBAPI 路径闭合；专用 BaseException 唯一识别；异常/cause 链及早拒绝 partial diagnostic 原样保留；观察器恢复；所有自身线程/客户端/连接与 PGID 收尾。

64MiB 账面预留为四个 DB 文件各12MiB+其余15.3125MiB=63.3125MiB，算术小于64MiB。但 RLIMIT_FSIZE 只约束每个文件，不自动限制文件数量或目录总量；SQLite 临时文件、其他目录/临时路径、父进程有界日志/receipt 以及超限错误输出都须封闭。不能用轮询或事后目录大小代替硬边界证明，也不能删原件腾空间。该保护尚无实现，当前没有启动资格。

480秒前缀/120秒G0/600秒工作+5TERM+5KILL=610秒、64MiB均只为提议合同。具体 launcher 必须从首子进程启动计时，G0进入另设绝对截止，所有阶段共享总截止；一次唯一 parent 调用、无补齐/重试、无重入重开收尾预算。产品原时钟/1800TTL/300Run/30lease/60RPM/7槽等保持原样，任何原期限先到即原拒绝；外层预算不延长期限。

最多保存该次真实 `_ColdCommitDiagnostics` 实例引用的设计不需要重演五函数；引用必须限定确切本次首次 G0，仍须在具体 shim 审核其计数/保存故障不替换原异常。首次绑定前或早期拒绝可能没有实例/finite，必须 NOT_REACHED/UNKNOWN；成功不能制造拒绝 finite/end/stop。该 observer 有非零开销，不可与历史深层 observer 结果作零扰动性能比较。

本轮没有 Mock/PB/G0/测试/产品导入/DB/launcher 执行，没有分配运行目录。仅创建本独审文档目录。若允许沿用原三项合成替换，下一步是先完成并静态独审具体硬限/退出 harness，再由用户决定是否明确批准一次新窗口。若不允许三项替换，现实生产默认仍 fail-closed；不要求真实凭据、权限或延长租约。

设计和读取源码完整 SHA256、五函数行号及源码段 SHA256 见 DESIGN-REVIEW.json。
