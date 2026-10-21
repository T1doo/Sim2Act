# 一次原限额尾段诊断：取得lease关系，G0仍UNKNOWN

执行候选 **`0a6b8f886c485b138a2ef87abbe4bc42f666e35f`**；source/dependency摘要
`bca95a150c371a4e8f921fa713dbf7cabce506a80e0772d90a3bc01aa27ec0b6`，profile
`f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`。
clean HEAD、远端一致、祖先、唯一launcher及绝对解释器/脚本身份先实核，冻结版本
前后及parent清理后的源码摘要完全相同。执行中未改源码/测试，没有新实现或回归批。
已审构建的66P与最终9P/44P4skip证据在`../tail-run-diagnostics-20261021/`，不重计。

新目录SQLite/新grant原子消费一次，**6Mock交换/8入口、2Source delegates**；
prefix480/G0120/总600+TERM5/KILL5清理10，lease30/Run300/TTL1800/RPM1/
reservation60全部原样。64MiB采样监测非硬配额，逻辑额度非CPU/RSS界。0真实模型/
费用/外网业务/新增凭据权限；禁Cold2/W5，不自动重跑，不恢复旧库或实例。

## 实际终态及拒绝

- 真正进入首G0，route **OWNED/native:issuance**。
- parent/child **UNKNOWN，exit2**；work wall **342.617473903003秒**，G0 wall
  **31.21108553600061秒**。前缀节流不与G0 CPU成本混淆。
- 第一次原Cold commit returned=true（无返回时间戳）；第二次进入但returned=false。
- `original_scope_returned=false`（未正常完成），final_deadline_check **NOT_PROVEN**，完整G0/PB仍未通过。
- VERSION_CONFLICT：**Run identity, cancellation, version or finite lease changed**。

完整原栈在diagnostic原件：`g0_guard.wrap:457 → advance_model:3752 → tail.wrap:281
→ CandidateObservation.observed:46 → commit:3001 → tail.wrap:295 → _recheck:2896
→ tail.wrap:317 → _require_run_context_row:869 → require:47`。没有cause/context，
原异常保持，包装器帧是新增仪器帧；不是前窗Store.guard或末尾最终期限门。

## 拒绝点已有参数事后再评价

`POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE`；diagnostic complete，
原固定Run谓词消息匹配。22项中 **20true，仅before_lease及before_min_deadline false**。
身份/项目/Runtime/请求/资源、status/cancel、version/fence、created/finite等均true，
不记录完整身份/资源载荷。原guard可能先抛/字段可能在回调中变化，因此此记录不是
原and短路每项当时执行的轨迹，不将任一事后false自动升格为唯一因果证明。

| 原参数标量 | 值 |
| --- | --- |
| at | 1792586396.782219 |
| lease_until | 1792586395.6106474 |
| created_at + caps.run_seconds | 1792586611.745434 |
| contract.expires_at | 1792587856.052482 |
| min_deadline | 1792586395.6106474 |
| **原at−lease** | **1.1715714931488037秒** |
| Run / contract剩余 | 214.96321511268616 / 1459.2702629566193秒 |

差值直接来自原同次at和已有参数，**不是G0 wall−30**，未重新采业务时钟或查询SQL。
本次证据支持lease关系已不满足；仍严格保留事后评价的上述限制。

## 四个尾段：只报已经观测的工作

| 段 | 达到与原方法结果 | wall秒 | foreground CPU秒 | check / input_key |
| --- | --- | --- | --- | --- |
| second_prefix | 1次，返回 | 0.056237143 | 0.056233534 | 8 / 0 |
| second_commit（inclusive） | 1次，抛原异常 | 3.585821897 | 3.585700599 | 436 / 0 |
| recheck（在second_commit内） | 1次，抛原异常 | 2.247529643 | 2.247471100 | 273 / 0 |
| scope_exit方法 | 1次，方法返回，0次raise | 0.000026090 | 0.000026079 | 0 / 0 |

second_commit−observed_recheck = **1.338292254 wall / 1.338229499 CPU秒、163checks**。
它包含实际已执行的recheck前段、异常解栈及诊断开销；不是_recheck成功后的余程成本。
第二commit后半/最终deadline/正常scope关闭分支未到达，**不补零、不外推**。

scope_exit的returns=1只表示原context对象`__exit__`方法返回，**没有记录其原返回值**。
falsey返回让原body异常继续传播是冻结contextmanager源码及异常链的控制流推论，
不是独立bool采样；尤其不等于CandidateObservation.original_scope_returned=true。
本次0check/26微秒仅异常退出，不是正常关闭最后hash/时钟检查的成本或通过证明。

原_cold_receipts→record_receipts、attempt回读/parse/usage/schema、receipt_for、
settlement-parsed已返回，也只是到第二commit处的源码控制流推论，无独立m/root计数。
Cold RUNNING/RECEIVED为StopBoundary保现场机制说明；本次未单独开库观测这些行状态。

| 最内层metric桶 | codec次数 / 成功返回字节 | codec inclusive线程CPU秒 |
| --- | --- | --- |
| second_prefix | 10 / 7746993 | 0.030621855 |
| second_commit（不含recheck桶） | 163 / 126776347 | 0.548723665 |
| recheck | 274 / 213117105 | 0.922421088 |
| scope_exit | 0 / 0 | 0（仅异常退出实测） |

recheck还记录raw_copy3570次/0.609859157 CPU秒、typed_storage2828次/0.236230090、
typed_equal5616次/0.231599413。它们定位内容扫描/复制成本，不等于判定全部调用
必要或可删除。metric最内层归属避免将recheck再算进second_commit桶；call counts
不是check counts。成功返回字节非SHA调用观测，线程CPU/wall仪器有非零开销。
首次五阶段仍5348 codec/3720455764返回字节/14.740890900 inclusive CPU秒，
尾桶447/347640445/1.501766608；九区间不含全部G0，不能宣称无仪器性能通过。

## 清理与证据保全

child THREADS_CLIENTS_CONNECTIONS_CLOSED；parent OWNED_GROUP_EMPTY；
finalization_errors=[]。独立ps核父64011、子64035均不存在、64035 PGID为空，
未向外部进程发信号。native逻辑budget resident/live458430612、peak478097556、
work188404034025305936651508；scope后active=false/live=resident=0，非RSS。

磁盘6798次采样：peak logical2295786、allocated2314240字节；间隔均值
0.05040685120523759秒、最大0.12782756800152129秒。配置0.1不是固定计划采样
周期；未称原生hard quota。authorizer拒绝0；W5为原STATIC_STOP口径非观测计数。

receipt evidence逐项hash/bytes实核。原件gzip解压逐字节恢复，DB仅本地保存及hash，
旧前两窗19/17项原件不变；所有收据、控制/异常栈、实际比较与metric细节见window/
original-manifest与outcome-analysis。没有自动重跑，没有在验收运行中改源码。

## 由证据推进的实质下一步

见 **NEXT-STEP-DESIGN.md**：只针对一个Cold结算，拥有且不可变的完整内容快照+
完整predicate读集CAS，短T0/锁外纯计算/短T1原子五写，保留原L0 cap及全部动态门。
**单纯移开BEGIN、让heartbeat可写或更晚续租不能让31.2秒在原30秒cap下通过。**
目前全族无逃逸、完整query/集合读集、旧新指纹及资格选路尚未闭合，设计只能条件
证明安全，不能直接拆事务。未实施新架构或开下一窗口，不再原样试时长。

两位只读reviewer已封本次窗口结果及设计文档回执，见reviews。设计仅CURRENTLY_BLOCKED条件方向ACK，不是实施/运行资格；runtime、保护、预算与验收代码均未修改，reviewer未运行产品、测试、DB或新窗口。
