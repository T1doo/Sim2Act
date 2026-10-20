# 第二次明确授权的受限模拟：G0 原期限拒绝，W5 前停止

用户在适配器修复后明确批准这一次独立窗口。执行代码为 `0c97113480367265610e463310db9589748b1804`，启动前为干净开发分支，远端同 SHA，根为唯一写入者，无其他活动诊断进程。四份执行代码与前次独审哈希一致；原预算、产品 deadline/auth 和完整扫描均未修改。

本次只创建并消费独立 grant `authorized-monitored-g0-second-20261020`，全新目录 `/tmp/sim2act-g0-monitored-second-20261020/authorized-monitored-g0-second-20261020`。唯一执行入口返回码 0 表示保护诊断正常捕获原 G0 拒绝，**不表示业务或完整 PB 成功**。没有第三次窗口授权，也没有自动重试、旧 DB 恢复、真实模型/业务网络调用、费用、发布或第三次 PGCI。

## 实际结果

- 分类：`G0_ORIGINAL_REJECTION_NO_W5`；业务状态 `INTERRUPTED`。真实 `g0_enter` 控制事件已保存，G0 耗时 **31.125279530 秒**；整轮回执耗时 **342.200031355 秒**。
- Generate 3 → Source 2 → Cold 1，合计 **6 次 Mock 交换、8 次方法入口**（含 2 次 Source 同步委托）；6 份 request/response 交换记录均已保存。
- 原 `DomainError / VERSION_CONFLICT`：`Production admission expired during verification`。原 stop=false；最小 finite 为 `run_check.deadline=1792514198.2167094`，与捕获的实际 `lease_until` 相同；end=`1792514199.3257813`，超出约 **1.109071970 秒**。其余 finite 均未到期。没有延长原 30 秒租约。
- G0 authorizer 拒绝计数为 **0**，原诊断 incomplete=false。原异常及完整命名 finite/end/stop/五阶段计数原样保存，未用收尾时钟或 DB 重建。W5 在静态停止边界后的下一句，未执行；这不是独立 W5 观测计数。G1/finalguard 未到达。
- 父回执 `OWNED_GROUP_EMPTY`，自有 PID/PGID/SID=48773，结束后只读 `/proc` 核对同组为空；child 记录心跳线程/客户端/连接关闭，finalization_errors=[]。没有对未知进程/锁发信号或删除。
- 磁盘采样 6795 次，峰值逻辑 2,254,459 字节，分配 2,273,280 字节（**2.16796875MiB**），未超预算。**64MiB 是采样预算，不是原生硬配额**。

## 原五阶段实测

| 原阶段 | wall 秒 | check_calls | input_key_calls |
| --- | ---: | ---: | ---: |
| _prepare | 14.743300681 | 3486 | 3550 |
| _graph_run_context | 4.081457379 | 808 | 808 |
| _graph_pb_accounting | 0.414142918 | 93 | 93 |
| _graph_resolve_trial_source | 6.001871885 | 1226 | 1227 |
| _graph_pb_archive_chain | 0.030676602 | 7 | 7 |

各阶段为既有诊断的局部区间，不能相加冒充完整 G0。观察器开销非零，此次受保护运行不能直接当作历史无同一观察器运行的性能对照。这里只报告本次原期限确实拒绝，没有从数据臆推新的优化方案。

## 状态和证据完整性

[只读新库摘要](READONLY-DB-SUMMARY.json)记录：3 个 Run（Generate PARTIAL、Source SUCCEEDED、Cold RUNNING）、6 个 Attempt、10 个 Operation、72 条 delivery。Cold Attempt 为 RECEIVED，response 已保留，usage.status=known，合成 tokens=100+900=1000；Cold 的两个 Operation 分别为 DISPATCHED、VERIFIED；没有补写模型完成、settle 或拒绝终态。LIVE 标签来自隔离合成生产形态分支，不表示真实模型调用或费用。

新 `fixture.db` 为 1,527,808 字节，SHA256 `b9c152e7120893c13699f763b4400d4a7e67a52f58e82e197eae38896e6e4064`。只在运行结束后以标准库 SQLite `mode=ro` 做 SELECT/只读 schema PRAGMA；前后完整哈希均与父回执相同，没有续跑或修复。

[ARTIFACTS.json](ARTIFACTS.json)逐项绑定 13 份运行、grant 和 description 原件及归档的大小、SHA256。DB/源码清单/description 无损 gzip 保存并校验解压等价，其余按字节保留。[原始诊断](RUN/diagnostic.json)、[控制事件](RUN/control.jsonl)、[父回执](RUN/receipt.json)、[交换日志](RUN/mock-exchanges.jsonl)、[前缀证明](RUN/prefix-proof.json)可直接检查。

源码/测试输入/依赖清单共 4131 项，摘要 `25811132d9bbc0acf5ec79794033cb9e047efcf83045415c90d32f8b6327bd08`，子进程前后及父收尾均相同。[PRECHECKS.json](PRECHECKS.json)保留启动前核验及首窗口原件哈希。首窗口 13 份原始文件与启动前一致；仓库中原失败证据全部 26 份与基线提交逐字节一致，没有覆盖任何失败材料。

本轮未改执行代码或重跑单元/完整 PB；前次接口修复回归和独审仍绑定同一代码哈希。此次实际测试就是本份证据中的唯一受限模拟。当前授权已消费，后续仅保全及正常开发分支提交推送；最终完整交付 SHA 和远端/未提交/未推送差异见最终回复。
