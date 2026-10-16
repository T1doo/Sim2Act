# 自然任务 SQLite 心跳锁：因果、修复与分期验证

基线 `87c1f0d0726f95270255a311983181ae1241bd09`；生产与新增测试冻结 `99f878a83387a7ef1b2e8734aef3e015dff3020e`；旧测试断言修正提交 `8b0f74d101a9fb8843304f346e5390694eaafeae`。root 是唯一仓库写入者。分支 `dev/sqlite-natural-heartbeat-lock-20261016`，后续仅归档本证据和说明。未访问旧满盘实例、旧 bundle 或共享文件，没有删除锁或进程。

旧 F9 失败原件保留于相邻 [原交付证据](../natural-application-entry-20261016/README.md)；四个原件的本轮前后校验见 heartbeat-lock-original-evidence-hashes.json。旧批仍为 1 FAIL / 5 PASS，第二次任务 WAITING_RESOURCE 的事实未覆盖。原件缺少事务持锁时序，不能追认其具体持锁连接。

**未改产品的自然基线 1 PASS / 110.18 秒**：同 app/Release/instance 的 SOURCE 与 COLD 两次实际 TestClient HTTP + Worker，每 Run 仅一次 claim，得到 v1/v2。真实出现 7 次 BEGIN IMMEDIATE 的 SQLITE_BUSY；[独立配对](f2-hb-baseline-overlap-independent-87c1.json)证明等待区间与前台已持写锁的验证/结算事务重叠。该轮没有复现最终 WAITING_RESOURCE，因此不能将其通过归功于后续修复。

**旧代码受控机制复现**：[完整因果报告](f2-sqlite-natural-heartbeat-causal-87c1-review.md)、[原始受控回执](baseline-controlled-sticky.json)、[脚本](f2-sqlite-sticky-probe-87c1.py)、[日志](f2-sqlite-sticky-probe-87c1.log)。实际基础 Run、真实两个 SQLite 连接、默认 busy_timeout=5000ms、原 lease=30/run=300；仅测试心跳调度器 Event.wait(10) 加速为 .001。前台已获写锁 → 后台 BEGIN 等待 5.024 秒真实 code5 并锁存失败退出 → 前台提交 → 原 Store.heartbeat 以相同 worker/Run/fence 完整 guard/CAS 后实际提交新 lease → 旧控制器仍消费旧失败，WAITING_RESOURCE。这个有界探针复现了明确竞态，不冒充原自然业务身份或旧 F9 的完整时序。

修复只认同次自然调用内、失败锁存后发布的更晚实际同步续租回执，核相同 worker/Run/fence、原 deadline/lease 未过和未 stop，明确记录恢复并重启原 cadence 的发送线程。数值更大本身、旧回执、不同 scope 或未实际续租都不够。Store.tx、driver 等待、三次重试批次、lease/fence/CAS、预算、权限、幂等及未知效果处理均未改；不从新 key 补交或重领任务。详细行为见 [实现说明](../../F2/NaturalSQLiteHeartbeatLock20261016.md)。

| 实际阶段 | 原始结果 | 说明 |
| --- | --- | --- |
| 99f 自然两次使用完整正例 | 1 PASS，210.07 秒 | 两个 Run 各一次 Worker.once/CLAIMED、fence1、实际 SUCCEEDED，v1/v2 |
| 99f 相关安全完整批 | 45 PASS / 1 FAIL / 0 SKIP，96.53 秒 | 共46，唯一失败是旧测试把合法第三次 heartbeat 当失败 |
| 旧测试断言修正后定向 known/late | 2 PASS / 0 FAIL / 0 SKIP，10.92 秒 | 只改一个旧测试函数，不重跑整批；原失败保留 |
| 独立新增完整轻模块 | 9 PASS / 0 FAIL / 0 SKIP，29.71 秒 | 重复节点单列，不累计唯一分母 |

主线程最终覆盖 **47 个唯一节点都有对应 PASS**，但不是一次 47 项全绿批。上表和 XML 保留实际分期。修正的两个节点运行开始时是 99f + 单个测试 WIP，随后以相同字节提交 8b0f；[字节与共享夹具桥](test-only-source-bridge.json)明确这条边界，不伪称在 8b0f 已重跑整批。

唯一旧测试失败：`test_real_sqlite_busy_recovers_without_new_claim[late]` 的 codes 实际仍是 `[5]`，调用次数为3而非硬编码2；加速调度下 observed.set 后可再合法提交一次续租。测试修正记录每个实际成功返回值，仍要求恰好一次 BUSY、其余每次调用均有成功提交值、DB lease == state lease == max(真实返回值)，并保留同 owner/fence。没有加等待、重试或放松权限。原 45P/1F 日志/XML、修正前源码和定向2P均归档。

新增轻模块有9项：真实默认5秒 SQLite锁失败后同步提交恢复、后台实际重启再续租；仅数值进展、旧序列、错误 scope、过期 deadline 均不认领；非 BUSY、恢复后另一次非 BUSY 仍传播；第二次合成 BUSY 不能用旧 marker 恢复；实际续租失败不发布 marker。第二次合成 BUSY 仅将私有 cached scheduler bound 置0以触发原 halt，实际 Run lease/clock 不变，不能冒称真实 lease 到期。其他负向也标为合成故障，只有 real-lock 使用真实 driver BUSY。原相关完整模块覆盖既有短竞争、截止回滚、撤权/stop/新owner/未知效果、终态及 Worker 后续存活边界，没有另铺外围矩阵。

[自然最终原始证据](final-natural/test_sqlite_same_natural_insta0/proof.json)及同目录 retained-rows、run-observations、run-ledgers、http-receipts、runtime-wires、tx-heartbeat-trace、heartbeat-logs 均保留。两份结果绑定精确同 app/Release/instance；typed.run_id 通过各自 AppRun id 关联，不混同执行 Run id；原 Run、AppRun、v1 typed、artifact 资源行和原制品字节保持，instance 只 data_version 1→2。新结果内容为 COLD，owner PENDING、semantic NOT_RUN。两次使用各有独立 Worker 身份和一次 claim，未声称同一 Worker 对象；既有安全模块另验证 Worker 可处理后续任务。

自然最终日志没有 heartbeat_contention_recovered（已有受限 defer 和终态后的迟到 halt），所以新恢复分支的实测证明来自真实 SQLite/基础 Run 控制器轻测。自然业务旧 F9 的最终 WAITING_RESOURCE 本轮未自然重现；长验证事务锁竞争仍存在，不能宣称修好所有 SQLite 锁故障、长期多历史压力或完整旧 F9 归因。

早期轮次不累计：WIP 新轻测 7 PASS / 1 FAIL，repeat-failure 用例误以为既有 defer 应在3秒内halt；修正用例后 prefreeze45P，新增repeat-busy另1P。各源码/JSON/log/XML保留。真实模型请求0；生成3条和两个运行各1条均为 MockTransport。Windows、PG、原生浏览器、远端 CI、部署、真实场景/人工语义、全仓及外围恢复矩阵均 NOT_RUN。旧满盘环境未落盘独审报告没有补回。

最终有限独审和逐项校验在同目录归档；SHA256SUMS 包含除自身以外全部文件，推送后的精确远端/工作区核验另存交付回执。
