# 第三次授权纯 Mock 诊断：G0 原期限拒绝，分段热点已定位

本次执行冻结代码 `cdda2b2ed6bce1393b90a500c0377294e4d82e34`，沿用已独审的五阶段内存观测器。用户于 2026-10-21 明确批准这一次窗口；历史 READY 中“尚未批准”的记录保留，不能作为当前授权状态。启动前 HEAD/开发分支/远端祖先、干净工作区、唯一写入者及原预算已核验，见 [PRECHECKS.json](PRECHECKS.json)。本次仅消费新 grant `authorized-monitored-g0-third-20261021`，使用全新目录/DB，没有恢复前两次运行。

唯一实际执行命令：

```text
/workspace/Sim2Act/.venv/bin/python -B /workspace/Sim2Act/scripts/diagnostics/g0_bounded.py --execute-grant /tmp/sim2act-g0-monitored-third-20261021/grant.json --output-parent /tmp/sim2act-g0-monitored-third-20261021
```

该 grant 已消费，以上是历史命令，不授权重跑。执行入口退出码 0 表示诊断捕获并归档原拒绝；业务为 **INTERRUPTED，完整 PB 仍未通过**。本轮无第四次窗口、自动重试、真实模型、收费调用或发布。

## 实际结果与保护边界

- 分类 **G0_ORIGINAL_REJECTION_NO_W5**，真实 `g0_enter` 已记录；G0 **30.985113144 秒**，整轮父回执 **342.467021839 秒**。Generate 3 + Source 2 + Cold 1，共 **6 次 Mock 交换、8 次入口**，其中 2 次为 Source 同步委托；六份交换原件保留。
- 原 `DomainError / VERSION_CONFLICT`：`Production admission expired during verification`。原 stop=false，最小 finite 为 `run_check.deadline=1792548717.850685`，与实际捕获的 lease 相同；end=`1792548718.8062055`，超过 **0.955520630 秒**。其他 finite 未到期，原诊断 incomplete=false，authorizer 拒绝 0。
- 保留原租约 30 秒、Run 300 秒、TTL 1800 秒及 journal/RPM 节流；外层工作上限 600 秒＋清理 10 秒（TERM/KILL 各 5 秒），prefix 480 秒、G0 120 秒未放宽。整轮包含前缀与 journal 等待，不能把 342 秒当作 G0 计算成本。
- W5 位于静态停止边界后的下一句，未执行；不是独立 W5 观测计数。G1/finalguard 未到达。仪器运行不构成无仪器性能验收，也不能与历史异仪器结果直接比较收益。
- 父回执 **OWNED_GROUP_EMPTY**，PID/PGID/SID=708；结束后主审与独审分别只读 `/proc` 确认同组为空。子记录 **THREADS_CLIENTS_CONNECTIONS_CLOSED**，finalization_errors=[]；未操作外部进程。
- 磁盘监测 6796 次，峰值逻辑 2,257,262 字节、分配 2,273,280 字节（2.16796875 MiB）。**64 MiB 为监测预算，非原生硬配额**。配置值 0.1 秒不用于定时；每次父循环及收尾采样，selector 最多等待 0.05 秒。实际完成间隔均值 0.050399277 秒、最大 0.143231934 秒，观测频率约 19.842 Hz。

## 五阶段观测

原五阶段 wall 合计 24.919289479 秒，仅覆盖局部区间。下面 CPU 来自 `thread_time_ns`，不以 wall 推导 CPU；本轮没有整 G0 CPU 指标。

| 阶段 | 原 wall 秒 | check / input_key | codec CPU 秒 | typed storage CPU 秒 | raw copy CPU 秒 | typed equal CPU 秒 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| _prepare | 14.326910111 | 3486 / 3550 | 9.393750934 | 0.908708676 | 0.631620034 | 0.355564045 |
| _graph_run_context | 3.879206015 | 808 / 808 | 2.524724662 | 0.208615838 | 0.522693046 | 0.135577474 |
| _graph_pb_accounting | 0.410192454 | 93 / 93 | 0.301343449 | 0.022841025 | 0.011503229 | 0.007935280 |
| _graph_resolve_trial_source | 6.273141311 | 1226 / 1227 | 4.077238455 | 0.343275681 | 0.836774321 | 0.232613252 |
| _graph_pb_archive_chain | 0.029839588 | 7 / 7 | 0.022067564 | 0.001797113 | 0.001512176 | 0.000744170 |

| 五阶段指标合计 | 次数 | 包含 CPU 秒 | 减去被观测子调用后的 CPU 秒 | 成功编码返回字节 |
| --- | ---: | ---: | ---: | ---: |
| codec | 5697 | 16.319125064 | 16.319125064 | 4,408,544,578 |
| typed storage | 20783 | 1.485238333 | 1.485238333 | 不适用 |
| raw copy | 18996 | 2.004102806 | 2.004102806 | 不适用 |
| typed equal | 32672 | 0.732434221 | 0.732434221 | 不适用 |

五阶段均到达，20 个桶完整，所有调用均正常返回，最大观测栈深度为 1，因此本次两种 CPU 口径相等。“减去被观测子调用”不等于函数内部所有子操作的排他 CPU。codec 占四类已观测指标 CPU 合计约 79.447%，**不代表整 G0 CPU 占比，也不代表可删除的成本**。codec 次数和 input_key 次数统计范围不同；输出字节为累计成功编码量，不是 SHA 调用量、唯一输入量、磁盘量或峰内存。

[STAGE-COSTS.json](STAGE-COSTS.json)保留每阶段原始指标及整数汇总，包括根元素数/根字节数/未知根计数。typed storage 的 20783 个模型根均未测输入字节；其余根统计也不是完整递归输入量。观测器不读取未知模型属性来估算大小，未为统计新增遍历。完整原件见 [RUN/diagnostic.json](RUN/diagnostic.json)。

## 生产优化决定和最小剩余条件

主审与[独审](REVIEW/REVIEW.md)均不批准当前生产补丁，本轮 `src`、测试、诊断运行代码及预算保持不变。实际热点已收敛到完整 codec，但其 16.319 秒仍合并 C Pickler 遍历、缓冲分配及 RowMapping/Limits reducer 和新鲜元数据读取。缺少当前完整阶段输入下这些内部工作的成本与可安全消除重复计算的证据；先前 61,657 字节小样不能填补该缺口。

可审候选的最小前置是：针对已定位内部操作提出明确的重复工作和等价替代，证明完整字段、隐藏 RowMapping 数据、别名/环、未知类型拒绝和混合错误顺序仍一致，且每次 pin 的可变输入仍重新读取；再用相同实现和有代表性的完整离线输入验证成本及差分。当前没有这种候选，因此不重做已否决的标量提前校验、删 SHA、类型分派/前缀微调，不复用跨次 memo/字节/行元数据，不改流式 SHA 回调边界，不拆原事务或扩租约。这里记录的是缺口，未擅自新增诊断窗口或实施任务；**G0 期限问题未解决**。

## 原件、库状态和实际核验

[ARTIFACTS.json](ARTIFACTS.json)绑定 13 份运行/grant/description 原件及归档大小、SHA256；DB、source-manifest、description 用确定性 gzip 无损保存并验证解压等价，其余逐字节复制。PRECHECKS 和独审原件另行保留；[MANIFEST.json](MANIFEST.json)覆盖本交付文件（自身除外）。前两次失败及 observer-ready 历史材料未覆盖。

新库仅在结束后用标准库 SQLite `mode=ro&immutable=1` 做 SELECT/只读 schema 检查；前后完整 SHA256 均为 `f98bb0cb345b3c4377ff96dcd1ffee4957ac8353e8d24b259316da4678a27a0e`。共 3 个 Run、6 个 Attempt、10 个 Operation、72 个 delivery request。Generate PARTIAL、Source SUCCEEDED、Cold RUNNING；Cold Attempt RECEIVED，已保存合成响应及 known usage（100+900=1000 tokens）。这些是 StopBoundary 以 BaseException 保留的现场，不是生产漏收尾或业务成功。LIVE 标签来自合成生产形态路径，不表示真实请求或费用；未续跑、恢复或补写终态。见 [READONLY-DB-SUMMARY.json](READONLY-DB-SUMMARY.json)。

4137 项源码/测试/依赖输入均在归档前重新逐项核 hash；清单摘要 `9069483f35b43e61dcfb3be4ed92cd4c8eb5fc00c51a2e47ef957b5efd6118a4`，与 grant、子运行前后和父收尾一致。本轮实际运行证据只有这一次受限诊断及只读/归档一致性检查，未新增 pytest、profile、完整 PB、PG/Windows/CI 或真实模型测试。冻结观测器先前的单测不重标为本轮运行。正常开发分支交付 SHA、远端和工作区最终状态见最终回复。
