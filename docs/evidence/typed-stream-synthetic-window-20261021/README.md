# 流式 typed cohort 的一次 SYNTHETIC 完整尾段验证：UNKNOWN

执行源码完整 SHA：**`21ec0f9d7b2efb51cd698e6b211af0bc4793cafe`**。
冻结 source/dependency 摘要：`276156f611f1407f969898f571155115d3cb34293960ef6a822b90dc714e54f4`；
原 candidate profile：`f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`。
新目录、新 SQLite、新一次技术 grant：`typed-stream-g0-08d398893c0749f2b24f20c81151f7d5`。

本轮明确授权执行既有 `g0_prefix.py:251 configured(...)` 合成工程路径，区别于上一片
无替身真实生产资格的夹具搜索。仅沿用 test_only SQLite 的 environment、账户 resolver、
软件资格三项既有业务资格替换；原 Store/Worker、审批、账链与检查实际执行，HTTP
仅 Mock。其余原 Mock 工厂、网络拒绝及诊断包装保持。**不证明真实账户来源、免费
资格或生产软件资格通过**，没有新来源、凭据、付费、权限或外网业务。

## 实际执行和终态

- 实际启动 **1 次**；技术 grant 已原子消费；无重试、无旧实例/数据库恢复。
- 真正进入首 G0，route **OWNED/native:issuance**；6 次 Mock／8 次入口、2 次 Source
  delegate（Generate3、Source2、Cold1），没有把 delegate 另计成额外交换。
- parent/child **UNKNOWN，exit2**；work wall **343.38433615500253 秒**；
  G0 wall **32.19487701400067 秒**。
- 首次原 commit returned=true，保留其 11 个原 deadline，没有返回时刻遥测。
  第二次 commit 已进入，在 `_recheck → _require_run_context_row` 抛原 VERSION_CONFLICT。
- `original_scope_returned=false`，`both_commits_returned=false`，
  final_deadline_check **NOT_PROVEN**。完整 G0/PB、正常 scope、最终期限均未通过。

保持原 6/8、prefix480/G0120/总600+TERM5/KILL5清理10；lease30、Run300、TTL1800、
RPM/reservation 不改。64 MiB 为采样监测，非原生硬配额；native 逻辑额度非 CPU/RSS
上界。Cold2/W5 禁止；W5 为原 `STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER`
口径，G0 authorizer denials=0。失败不据此开新窗口。

## 原异常及已有参数

原消息：`Run identity, cancellation, version or finite lease changed`。
完整原栈保全于 diagnostic 的两条原记录：guard.wrap:457 → advance_model:3752 →
tail.wrap:281 → CandidateObservation.observed:46 → commit:3001 → tail.wrap:295 →
_recheck:2896 → tail.wrap:317 → `_require_run_context_row:869 → require:47`。
无 cause/context；新增包装帧不替代原异常。不是 Store.guard 或最终 deadline 处拒绝。

22 项**异常后对已有安全参数再评价**为 20true，仅 before_lease、before_min_deadline
false；不是原 and 短路执行轨迹，不将其冒充唯一已证明因果分支。

| 原参数 | 值 |
| --- | --- |
| at | 1792591728.1871762 |
| lease_until / min_deadline | 1792591726.0243828 |
| Run deadline | 1792591942.3875508 |
| contract.expires_at | 1792593186.704455 |
| **原 at−lease** | **2.1627933979034424 秒** |
| Run / contract 余量 | 214.20037460327148 / 1458.5172786712646 秒 |

该原参数差支持 lease 比较过期，**不是 G0 wall−30 的推算**，未重新采业务时钟或查询
SQL。身份/资源/status/cancel/version/fence 等事后 bool 为 true，不记录完整业务载荷。

## 完整尾段的实际达到范围

| 段 | 实际方法结果 | wall秒 | foreground CPU秒 | check次数 |
| --- | --- | --- | --- | --- |
| _prepare | 返回 | 15.288695678995282 | 无该原span总CPU字段 | 3504 |
| second_prefix | 返回 | 0.077078970 | 0.077075000 | 8 |
| second_commit（inclusive） | 抛原异常 | 3.900742309 | 3.900647427 | 436 |
| recheck（在second_commit内） | 抛原异常 | 2.407523844 | 2.407467776 | 273 |
| scope_exit方法 | 返回，0次raise | 0.000027742 | 0.000027761 | 0 |

second_commit−observed_recheck 为 1.493218465 wall／1.493179651 CPU 秒、163 checks；
只含实际执行的 recheck 前部及解栈/观测开销，不是未达到后部的成本。

原 `_cold_receipts`、Attempt 回读、parse/usage/schema/receipt_for 及第二 prefix 已经过，
仅由第二 commit 的达到点和冻结源码顺序推断，**没有独立 receipt 返回/根计数遥测**。
scope_exit 的 returns=1 只表示 `__exit__` 方法返回，未采样其原返回值；原 body 异常
传播和 candidate.scope_returned=false 明确不是正常 scope 完成。0checks／约28微秒为
异常解栈，不能冒称正常关闭最后 hash/时钟的成本。未达到的后段不补零或外推。

## 成本观测的边界

上次同一尾段诊断 G0 wall 为 31.21108553600061 秒，本次为32.19487701400067 秒；
**本次没有取得 G0 提速或期限通过证据**。两次不是受控因果 A/B，不能仅由差值归因。

九区间 codec 次数及成功返回字节与上次逐项相同（详见 metric-comparison）：首五段
5348 次／3,720,455,764 B；尾部最内层桶447次／347,640,445 B，不代表全部 G0/SHA调用。
recheck 的旧 helper 计数由 typed_storage2828→274、raw_copy3570→1016、
typed_equal5616→508，符合替换副本构造与比较的源码方向；但 **新 `_cold_typed_stream`
方法没有单独进入旧四类 metric**，其工作仍包含在整体 span CPU 中。不能把旧 helper
下降当成总工作下降、声称新方法CPU为零，或把上一片11模型小样收益外推此完整输入。
保留全部原仪器，观测有非零开销，不冒充无仪器性能验收。

## 冻结、清理和原件

执行前两次只读 describe 完全相同，干净 HEAD、远端及祖先实核；绝对解释器/脚本
argv 精确匹配自身身份保护，未删除/绕过父身份门。无旧活动 launcher。上一窗口
19 项原件逐项 hash 不变。运行中没有改源码、测试、脚本、保护或配置；子进程前后
及父清理后 source digest 均为上述276156f6…。

child `THREADS_CLIENTS_CONNECTIONS_CLOSED`；parent `OWNED_GROUP_EMPTY`；
finalization_errors=[]。独立核父71490、子71514均不存在，PGID71514为空，独立核查
发送信号0。native scope 后 active=false／live=resident=0；逻辑 peak478097556，非RSS。

磁盘6815次采样，logical peak2,271,672／allocated peak2,285,568 B；完成间隔均值
0.05039362094291143、最大0.129539390996797秒。配置0.1不是固定调度周期，不声称hard quota。

本地原件位于 `/tmp/sim2act-authorized-typed-stream-g0-08d398893c0749f2b24f20c81151f7d5`。
fixture.db 只保留本地并做文件 SHA，未打开/查询/恢复执行；其余原始 stdout、control、
Mock 原字节、grant/consumed、prefix proof、两条 diagnostic、receipt、冻结清单及清理
记录均 gzip 归档并可逐字节还原。原件 manifest 含后处理比较共20项，追加分析不改
运行原文。源码/运行保护无新差异；本片提交只保全结果，不新增代码或再次运行。
