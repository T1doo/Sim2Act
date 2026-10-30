# 大型 Cold G0：同一快照内延迟取得写锁

验收源码 `f58d1d4d96e5bd68d751fc4a47318013e617946b`，后端实现 `77559dac1aec274248a309729eb69145137b5592`；两者 src 字节相同，后一个提交仅修测试初始化。基线 `bee40b5fbe0a91519a8a5e9a3bc93bdbf5619db3` 的完整通过证据保留。此处是云 Linux、明确 test_only 文件 SQLite/WAL、固定 Mock 工程验收，真实模型调用为零。

## 实际实现

显式本地能力开启后，原 Store/连接执行 BEGIN DEFERRED。完整 G0 在同一 SQLite 只读快照中运行，不提前取得 RESERVED 写锁或 FIFO。G0 的原 Graph、原内容/权限/版本/时间校验全部保留；没有将 Graph/PASS 跨事务携带。只读阶段通过该连接发起非 SELECT SQL 会失败，不能借回调提前写入。G0 完成后才取得原有界 FIFO，第一条原 attempt UPDATE 实际升级；无假写、无删输入或扩大租约。原五写、完整 G1、最终 guard、提交仍全部原子。

任意其他连接提交后，旧 WAL 快照不能升级为 writer。真实 BUSY/BUSY_SNAPSHOT/LOCKED 在回滚后转独立 SnapshotChanged，绕过模型拒绝分支；不自动重试模型、不重放旧交易、不切回旧路径。原 RECEIVED/DISPATCHED 保留，通过原 fenced error lifecycle 收口。若本 epoch 已登记取消，则同取消中断一样，释放全部锁后先等待原命令完成；未完成不抢改 Run/version。这里没有按“相关行没变”复用陈旧资格，连无关项目写入和 ABA 提交也会使升级失败。

这利用的是 SQLite 的数据库级快照升级规则，参见[官方隔离说明](https://www.sqlite.org/isolation.html)和[BUSY_SNAPSHOT 定义](https://www.sqlite.org/rescode.html#busy_snapshot)。它以更多竞争失败换取 G0 不持写锁，并不减少 G0 的 CPU 工作。**G0 内部仍读取原快照授权，不会即时看见另一连接刚提交的 revoked；安全依据是此旧快照随后无法提交。** 成功升级后没有穿插其他 writer，原 G1 再完整核对当前输入、权限、撤权、版本、租约及有限时间。原 stop/clock、内存配置变化检查未删。

能力仅选择明确本地文件 SQLite；PG、普通 Store、内存库保持原路径。synthetic_workspace 先核既有目录结构/身份再显式开启 WAL，新目录按原授权初始化后开启；构造失败释放 Engine，未知目录不迁移。未降低 synchronous，不删 WAL/SHM。WAL 必须使用支持其语义的本地文件系统，不能将此候选宣传为网络共享数据库支持。专用私有候选 writer 仍独立走其原路径，未借新快照共享 proof。

## 同一原大型输入：正常完整保存

`complete-run.json`：04:03:47–04:13:02 UTC，退出 0，总 555.757 秒。原 P-B 控制器完整断言全部通过；生成3、Source2、Cold2，共7次固定 Mock，0真实调用。没有人为业务延时或替换校验函数。原同 key 去重、完整来源、fresh Cold Store/Worker、归档、结果和 owner PENDING 断言保留。

| Cold 结算 | 整个原子区段 | 完整 G0 | 首次原 DML 起算写锁时间上界 | 原120秒预留区间剩余 |
| --- | --- | --- | --- | --- |
| 第一次 | 104.881712 秒 | 42.114371 秒 | 62.766485 秒 | 15.116443 秒 |
| 第二次 | 105.731777 秒 | 45.891823 秒 | 59.839411 秒 | 14.266845 秒 |

原120秒合同从 G0 前开始，仍覆盖 G0＋五写＋G1；没有在升级处重新计时。写锁时间从首次原 DML 发起到交易关闭后的清理结束，是紧的上界，包含该 DML 和尾部清理，不是 SQLite VFS 精确锁探针。G0 时另一连接能实际提交的事实另由下述大型冲突验证给出。不中断的整个 SQL transaction 仍长约105秒，不能叫“整笔短事务”。

**原30秒目标未满足，CPU降幅未证明。** 写后区段包含原五写、完整 G1及提交，不能将该上界冒称纯 G1 profile。相比旧区段，本轮安全地把42–46秒 G0移出持写锁阶段；不能把不同运行的总耗时差异归因为硬件或 CPU 优化。

`reopen.json`：独立新 Python 进程 mode=ro 打开同一持久库，核实 Cold SUCCEEDED、唯一成果 v1、app output/typed data 与已保存 HTTP 结果一致；Cold2条 VERIFIED，整库7条 attempt为生成3 RECEIVED＋Source/Cold4 VERIFIED。主 DB、WAL 摘要前后不变，另记录全部表的逻辑快照摘要。**运行中的 WAL 状态不能仅由主 DB 文件复制或哈希代表**，SHM 为瞬态协调文件；未发布或删除数据库原件。`check-reopen.py`保留核对脚本。

## 大型输入的取消、修改和撤权

各案例都从原完整生成/Source/Cold链建立独立合成库，固定6次 Mock，0真实调用；在实际 Cold G0 已超过1000次原 checkpoint 且运行超过3秒后触发。没有用小样例或人为等待代替大图性能。

| 实际动作 | 响应/提交时间 | 结算结果 |
| --- | --- | --- |
| loopback HTTP GET control-progress | 82.010ms，HTTP200 RUNNING | 元数据不提供内容或成果资格 |
| loopback HTTP 原 cancel | 76.384ms，HTTP200 RECONCILING | G0总4.158秒后关闭，首次DML前回滚，无写锁区段 |
| 另一连接修改实际输入content | 15.176ms，在G0仍开放时提交 | 原G0约37.975秒后升级失败，WAITING_RESOURCE |
| 另一连接撤销当前principal的resource.read grant | 7.057ms，在G0仍开放时提交 | 原G0约36.764秒后升级失败，WAITING_RESOURCE |

两个冲突案例的 `writer_seconds≈0.000262` 仅是失败 DML 的尝试至清理时间，**不是成功取得写锁**。输入案例刻意只改 content，不借更新 hash/version 伪装检测；SQLite 整体快照冲突仍拒绝旧结果。撤权是直接 SQL 的实际并发边界，非用户界面撤权验收；旧 G0 继续做推测性内部计算，不能说即时观察到新权限。

三条异常路径均逐行核 RECEIVED 尝试和原 typed 历史、归档不变，operation仍 DISPATCHED，无 NS_SETTLED/NS_REJECTED、无新成果。取消还比较全部资源及既有五条 attempt。只有原 happy-path 精确“最终必须 SUCCEEDED”断言允许作为预期分歧，其他失败不能被接受。取消回执正确为 RECONCILING，不假称外部模型效果已被确定取消。

`cancel/input/revoke-run.json`分别保留04:13:02–04:18:27、04:18:27–04:24:25、04:24:25–04:30:21 UTC起止、原命令和退出0。四条成功案例共25次固定Mock。整个协调器已退出，没有遗留测量或并发重复运行。

## 回归、失败保全与独审

`local-boundaries.log/xml`：25项通过，核真实 WAL并发提交/旧快照拒绝、ABA、整写组回滚、只读回调写拒绝、FIFO超时与清理失败释放、未知工作区不改模式/字节，以及原本地交易/关闭回读边界。该批后只增加了 runtime 的 SnapshotChanged取消握手；该分支另在下述实际冲突单元与四条完整大图上验证。

`continuation-known-fixture-failures.log/xml.gz`：真实结果为 **17通过、15失败**，不能称全绿。其中新增 pending-control 用实际另一连接提交制造 BUSY_SNAPSHOT，同时挂起命令完成事件，核 worker返回False、不抢改Run/version、不拒绝RECEIVED/DISPATCHED。其余15个旧 continuation fixture使用SimpleNamespace worker及占位祖先，却进入现有完整Cold G1，因此在原 exact Worker 门失败；不是通过放宽类型或伪造Graph来修绿。独立 AST比较确认 `_ColdGraphRead.__init__`、`_model_settlement_read`、`_cold_model_before`与bee40完全相同，旧case能力默认关闭，见 `old-fixture-comparison.json`。完整真实Worker大图是独立验收门，不覆盖或抹去这些失败。

初次大图在3次生成Mock后、进入Cold前因测试将Store类换成函数而失败；原观察器需要Store.guard。该运行退出1、日志和空timings保留于 initial-large-fixture-failure*。f58保留Store类，只包装初始化选择同env URL；构造/原guard观察器快速检查通过后才顺序重跑。初次pending-control检查还有断言分支摆放错误，实际已保留RECEIVED却被旧拒绝断言误判；其XML原件保留，修正测试分支，没有修改生产门或删除旧断言。

独立只读审查 `/root/desktop_final_review` 核过实现、资格和四条实际终态，见 `readonly-review.json`。144项资格逐核、新增 `_sqlite_model_snapshot.py`，原143项无删除，固定pin `d084a9463455adc0135d3b71d615acbdc3d397ccbc0986bed77b54f1cf1d2f8d`，原 `_qualified()` 实际通过。C源码及两枚Linux原生二进制未更换。公开材料仅含选定合成摘要/日志/XML/脚本，解压后扫描已配置凭据值及常见秘密格式，未发现匹配，不含DB或原始模型交换包。

## 尚未闭合的核心部分

写后60–63秒区段仍是剩余瓶颈。`_model_settlement_read`实际要求 attempt/operation已VERIFIED、原事件已写入，再重建完整图和动态来源、权限、版本及期限。直接搬到五写之前会读到不同事实，搬到提交之后会破坏失败时五写全回滚。当前 ContentPlan仍只拥有数据，不能证明其等价。

进一步移出G1需要单独实现完整依赖集及不可变预期写后视图，再证明真实五写与该视图完全一致，并在writer内新鲜核对全部动态条件；未具备这份证明前不把既有Graph/PASS当计划使用。本轮可交付的是已实现并验证的G0写锁生命周期缩短和有界安全取消，而非G1分拆或原30秒目标完成。

未访问用户电脑，未启动第四次Windows CI，剩506秒保留；未改main、发Release、部署或新增费用/凭据/安全权限。真实模型、正式PG、新模式Windows/EXE/WebView2、像素及整体生产验收均未完成，旧版本通过不能替代这些边界。
