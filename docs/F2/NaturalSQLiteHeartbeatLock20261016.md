# SQLite 自竞争后已续租仍消费旧心跳失败

基线 `87c1f0d0726f95270255a311983181ae1241bd09`，分支 `dev/sqlite-natural-heartbeat-lock-20261016`。root 唯一仓库写入者，两个代理只读审查和设计测试。已核同一指定环境、本地与远端、单 worktree、约 27 GiB 可用空间；未进入旧满盘实例或删除任何未知锁/进程。

原 F9 额外多历史准备的第二个 Run `run_f84938d5ad05425280d986f2284c2324` 单次 claim 后为 WAITING_RESOURCE，原错误为 `Heartbeat renewal could not acquire the database lock`。该批保持 1 FAIL / 5 PASS，原件未改。原证据没有事务/连接时序，不能追认旧失败的具体持锁者。

本轮未改产品的自然时序基线：实际 HTTP SOURCE 与 COLD 两个任务、同 app/Release/instance，每 Run 仅一次 Worker.once，1 PASS / 110.18 秒，得到 v1/v2。真实心跳 BEGIN IMMEDIATE 发生 7 次 SQLITE_BUSY；独立配对证明其等待窗与前台已获取写锁的事务区间重叠，第二次任务最长前台事务 13.17 秒。该基线没有重现最终 WAITING_RESOURCE，不把通过归功于后续修复。

随后一个有界控制器探针一次复现了可修竞态：基础 Run 原 lease=30、run=300、SQLite 默认 busy_timeout=5000ms 不变，仅把测试调度器的 Event.wait(10) 改为 .001。前台真实 BEGIN IMMEDIATE 已持锁，后台另连接 BEGIN 等待 5.024 秒得到 code5 并退出；前台随后真实提交，再调用原 Store.heartbeat，以相同 worker/Run/fence 完整 guard/CAS 后提交新 lease。旧控制器仍消费已锁存的旧错误，将 Run 改成 WAITING_RESOURCE。该探针是实际 SQLite/控制器/基础 Run，不冒充完全重现原自然业务身份和旧 F9 时序。

最小修复只改自然任务的同步续租发布与共用调度器的有界恢复判断：

- 原 Store.heartbeat 成功返回后，在同次调用私有 state 发布 worker/Run/fence/实际 lease 与单调回执序列。仅完整验证读取到的数值不产生该回执；原事务、guard、CAS 均不变。
- 心跳失败锁存时在 state 锁内记录当时序列。仅自然任务启用，且仅 SQLite 的明确 BUSY/LOCKED；只有锁存后发布的更晚同 scope 实际续租回执、未过原 deadline/lease、未 stop 才能结束这个过时的锁故障。
- 明确记录 heartbeat_contention_recovered 并恢复原心跳节奏。旧发送线程在 failed.set 后只有 return，没有后续 DB 工作；新发送线程从原 cadence 开始，不增加重试批次、driver 等待或模型调用。
- 无新回执、旧序列、错误 scope、截止时间过期、非 BUSY 错误及后续新错误仍走原拒绝/传播路径。原 guarded defer、未知效果和状态结算合同不变。

没有修改 Store.tx、SQLite timeout、lease/run/model 预算、fence、幂等、权限、executor 或 Grant；没有用等待更久、重领任务或忽略所有心跳失败求绿。真实模型、Windows、PG、原生浏览器、远端 CI 和部署均不在本轮已执行范围。最终冻结与原始证据另存本轮证据目录。
