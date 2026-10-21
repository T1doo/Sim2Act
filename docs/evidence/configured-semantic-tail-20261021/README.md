# Configured Cold 完整合成尾段差分

基线及被测产品源码：`2a7dcfcca65960ad956d7caf03fe48494972eb24`。本提交只增加测试和证据，
没有修改产品源码。完整合成语义差分已通过；**真实时钟 G0 是否通过仍未证明**。

## 实际完成的路径

使用原 `test_spec_production_controller.configured`、`prepare_pb` 和既有前缀操作：
Generate 3 次、Source 2 次 Mock，原 extraction/replay/archive 验证、release、Cold enqueue
及 stage approval。每个尾段恢复到独立新 SQLite，执行真实 Store、Worker、审批、账链、
`_cold_model_before`、完整 binding、prepare、首 commit、Cold receipts、第二 commit，
再从原 context 正常返回。只有原 configured 的 environment / resolve_account / software
qualification 三项合成替换；没有新增账户证据替身或生产成功门。

观测器精确绑定 Cold run、counter_reader 和 pending operation；Source 内部 receipts 不
充当 Cold 回执。实际 pre 模式要求 `audit_seed is None`，没有伪造 post seed。成功路径从
原 context 返回后检查 guard/mode 已关闭，再证明跨 scope `trial.check()` 拒绝。最后用
`TailStop(BaseException)` 在 W5 前保留现场，所以持久 Attempt 为 RECEIVED，不能称业务
SUCCEEDED、生产来源通过、Cold2/W5 或完整 PB 验收。

旧对照仅将两个私有 policy wrapper 换回原 guarded 函数；其余源码与候选完全相同。
这验证上一提交的两段优化，不是两个完整历史 checkout 的性能对比。

## 测试时钟与边界

显式仅测试 `SemanticClock` 替换业务 `time.time`，只在原 `_journal_wait` 的已注册 worker
stop Event 等待处推进，每步最多 0.25 秒。原 heartbeat 线程按虚拟期限唤醒，执行原数据库
续租；推进前后等待这些原线程完成本轮并重新等待。等待状态不等于续租提交确认，原
Store/Run 检查决定接受；不伪造 heartbeat 返回、不跳过原谓词。G0 计算期间虚拟时间暂停。
自然适配器的业务 elapsed 也使用此测试时钟，以便比较完整输出；诊断及外部监督保留真实
时钟。测试时钟不会进入运行产品配置。

原 lease 30 秒、Run 300 秒、contract TTL 1800 秒、reservation、授权、SQL、fence、stop、
scope 和最终期限门全部保留。配置沿用已审合成 candidate Bounds/Limits；这些逻辑计量
不代表 CPU、RSS 或全进程内存界。此次不是带 64 MiB 磁盘监测的 600 秒 launcher 窗口，
没有将开发回归重命名为该窗口或真实 G0 资格。

整套由真实 `timeout --signal=TERM --kill-after=10s 300s` 监督；时钟调度另有真实 5 秒
线程握手和 300 秒协作检查。没有自动重试，HTTPTransport/AsyncHTTPTransport 均拒绝，
仅本地 HTTP Mock。每个恢复用例最多 1 个 Cold Mock / 1 个入口；连同共享前缀相当于
Generate3 + Source2 + Cold1，即每条逻辑路径 6 次交换 / 8 次入口。无真实模型或费用。

## 实际结果

冻结七个源码/测试文件后执行，退出后 SHA256 全部一致。主测试为 **1 passed / 257.53s**，
其中六个隔离用例的最终断言全部执行；另有无 DB/Worker/Mock 的五个时钟/编码单测
**5 passed / 0.22s**，Ruff 五个新文件通过。现存 Starlette/httpx 弃用提示原样保留。

| 完整原 context 内指标 | 旧 guarded 对照 | 候选 |
| --- | ---: | ---: |
| codec 次数 | 8373 | 8337 |
| codec 累计返回 bytes | 4,920,607,268 | 4,894,540,040 |
| 前台 SQL 语句 | 7735 | 7735 |
| 原 Run 行谓词入口 | 2 | 2 |
| prepare / 两次 commit / Cold receipt / 原 scope 返回 | 全部完成 | 全部完成 |

次数减少 **36（0.430%）**、累计编码输出减少 **26,067,228 bytes（0.530%）**。
这是从完整 first binding 到正常 context 退出的实际计数，包含原 scope 收尾；不是先前
四个局部调用点的 52→16，也不外推到其他输入、CPU、省时或真实租约通过。

内存中直接比较两条成功路径的完整 authority records、完整 SQL 序列及参数，均相同；
两次 commit 的完整输出另用保留 bytes、tuple/list、quoted_name 类型及 quote 值的诊断
编码逐字节归档。诊断编码不是业务协议或业务指纹替代。原 context/source 业务指纹及
原 Source 回执也保留在总报告中。

| 候选反例 | 实际达到 / 原拒绝 |
| --- | --- |
| 最终期限过期 | 两次 commit 和 Cold receipt 完成；原 scope 最终门抛 VERSION_CONFLICT，`Production admission expired after closing the Cold read scope` |
| 首 commit 后 frontier fingerprint 突变 | 首 commit 后原完整门抛 VERSION_CONFLICT，`Native mutable frontier changed`；scope 失效 |
| 首 commit 后撤权 | 原 configured 撤权开关由原 `check_source` 拒绝，LIVE_BLOCKED；scope 失效 |
| 同事务写故障 | 首 commit 后真实 SQLite INSERT(1) 返回，INSERT(2) 违反 CHECK、sqlite_errorcode=275；异常回滚后查询 probe 表为 0 行 |
| 跨 scope | 两条正常路径关闭原 scope 后 `trial.check()` 均拒绝 |

写故障只证明测试 probe INSERT 在同事务回滚，**不是 W5 五写组故障覆盖**。

负例不把 harness AssertionError/KeyError 算作安全拒绝；原 DomainError / IntegrityError
保留为 cause，按类别、错误信息及到达位置断言。写故障表只存在于测试数据库。

## 实际消耗与失败保全

本任务累计实际 **13 次 Mock 交换 / 15 次方法入口**（含 Source 两个同步 delegate），
而不是只报告最后成功命令的六次。13 条原始 Mock 交换日志可逐条核对。

1. 初次 harness 在 Event.wait descriptor 绑定处失败，0 Mock；修复后以无 Mock 单测验证。
2. 首个完整集成命令 41.04 秒失败，实际 6/8：共享前缀 5/7 加旧 Cold1 1/1。观测器误将
   内部 Source receipts 当作 Cold，在首 commit 前断言失败。未把该失败认定为产品拒绝。
3. 修正精确绑定后续接，旧路径已走完原两 commit、receipt、scope，但归档器不认识
   SQLAlchemy quoted_name 键，44.01 秒失败，再消耗 1/1；没有完整报告，不冒认测试通过。
4. 用无 Mock 编码单测修正后，明确开发回归累计上限为 13/15，执行六个尾段的最终命令，
   新增 6/6，并按累计 13/15 断言。原先自设 12/14 计划及审查保留为历史，未冒充当前版。
   这不是扩大任何生产 grant、租约或真实时钟窗口的额度。

续接只复用**本任务自己构建且从未执行 Cold 的 QUEUED 前缀**，不恢复任一失败 Cold DB。
原前缀 Cold Attempt=0；每个尾段复制为新库，独立 contract model/settings/fixture/clients/
workers。原前缀 DB SHA256 始终为
`7edd97daf5096bab4f329d860bbb155c8456837a848266eeeb5585f2a2bb9650`。
首次 harness 未归档模板 metadata，之后从原存储 contract、fixture 默认配置及只读原接口
恢复；虚拟时刻 1800000240 从 Cold 入队时间及原 journal-only 推进规则重建，不冒称首次
原样记录。恢复期间无 Mock，源库哈希未变。两个 metadata 版本和已花费计数均归档。
正常 fresh pytest 会自行构建前缀；checkpoint 环境变量只用于本次明确的本地测试续接。

## 清理、独审与复现

原 worker stop、client close、heartbeat 线程退出后才处置 Store；清理覆盖已启动但尚未
注册等待的线程。最终断言本测试新增线程无存活，后续只读检查未见 pytest/timeout 进程，
所有本任务 SQLite 均无 WAL/journal sidecar。没有停止外部进程。夹具 DB 留在本机证据
目录并只记录摘要，不提交数据库。

`artifact-manifest.json` 给出原件、gzip 及解压后 SHA256；`originals/` 包含完整成功输出、
总报告、13 条 Mock 记录、失败日志、冻结清单、checkpoint metadata 和实际验证记录。
`reviews/` 中保留阶段及最终只读独审，阶段回执只绑定各自当时的源码/预算，不追认后续版。
审查者未重跑测试、未访问夹具 DB、未调用 Mock。

fresh 本地复现（会产生新的合成 Mock 消耗，本文不会自动再运行）：

```sh
timeout --signal=TERM --kill-after=10s 300s .venv/bin/pytest -xq tests/test_cold_configured_semantic_tail.py
.venv/bin/pytest -q tests/test_cold_semantic_clock.py tests/test_cold_tail_output_encoding.py
```

真实时钟 G0 及生产账户来源资格仍待后续独立验证；本证据只闭合完整合成语义差分。
