# Cold实测热点与原结算期限准入修复

生产源码冻结并已推开发分支 `9523d3e2bd5e6429c0a3744d0c2ec22e0a8abafc`，基线 `8c1f2deac19387f0aca78d286427010ae30c9bcb`。本轮没有改main、放宽原120秒SQLite合同、删完整校验或改变最终五写原子性。原30秒目标仍未达到；较前单次样本更低的耗时不能归因为本次期限修复，也不构成稳定性保证。

## 实际修复

此前G0结束后，`_Read.promote()`固定向FIFO申请30秒等待；它没有扣除已经耗去的原结算期限。接近到期时仍可继续排队，且无FIFO Store首次DML没有这项期限检查。本轮将原Worker已签发的 `(absolute_monotonic_deadline, wall_lease_until)` 不可变二元组传入同一snapshot事务，不重新签发或重新起算。

准入取原两类时钟的剩余量及30秒排队上限的最小值，FIFO内部再钳住同一个绝对monotonic界；取得准入后和首次DML前复核，无FIFO也必须检查。SQLite busy_timeout只缩短至同一剩余预算，退出恢复。损坏、非有限或已过期原界走SnapshotChanged，释放准入并保留原RECEIVED及取消握手，不转成模型拒绝或重试。普通非snapshot路径，以及None+无FIFO旧路径保持原行为（实测45000ms不被新30秒上限覆盖）。

完整G0仍在原一致WAL读快照中，其他已提交变更（包括ABA）仍由SQLite拒绝升级；原五写、完整G1、权限/撤权、版本/fence及stop/time检查和最终commit保持原子性。此修复不把53–55秒G1挪到别处，也不承诺中断任意同步SQL/fsync/清理。原完整图/装配/advance的五个AST未删改；144项精确资格已更新并实际通过，pin见source-identity.json。

真实FIFO+时钟探针：原monotonic/wall期限分别只剩120ms时，约120.48/120.46ms即回滚退出；队列无残留，未开始DML。原接收/拒绝区分和pending取消握手等65项最终回归通过。原15项fixture对照、逐项失败和34条原断言保全见 [此前逐项证据](../continuation-fixtures-20261030/README.md)，本轮没有撤去生产exact Worker类型门。

## 同一原大型输入完整保存

06:25:59–06:34:49 UTC，原真实时钟控制器全部断言通过，exit0；7次固定Mock、0真实模型，文件SQLite WAL，含局部sys.monitoring计时及filtered strace。所有业务callee、SQL、输入和时钟未替换。源码G0两次graph.commit均为完整图校验方法；每个模型结算的SQL事务仅有一次最终commit，G1图校验及原预约/收短租约事务按原链执行。

| 实际区段 | 第一次 | 第二次 |
| --- | --- | --- |
| 完整结算 | 88.136829秒 | 97.242533秒 |
| G0读快照 | 35.314942秒 | 42.283132秒 |
| 首次DML发出到事务清理上界 | 52.821116秒 | 54.958875秒 |
| 原120秒合同余量 | 31.860826秒 | 22.755540秒 |
| 结局 | COMMITTED | COMMITTED |

首次DML前事件到清理不是精确VFS锁回调，保留这个测量边界。pending Python/C帧与SQL计时项均为0。未在此基础上额外扩大时限或循环盲跑。

| G1阶段 | 第一次秒/次数 | 第二次秒/次数 |
| --- | --- | --- |
| 完整结构比较（含reducer） | 17.726344 / 7681次 | 19.053402 / 7766次 |
| typed storage完整扫描 | 2.819613 / 9084次 | 3.120235 / 9232次 |
| typed values完整校验 | 6.424247 / 3325次 | 6.345711 / 3325次 |
| typed parameters材料化 | 4.231024 / 734次 | 4.232634 / 734次 |
| 完整序列化（含pickle） | 5.567401 / 1206次 | 6.332838 / 1260次 |
| SQL SELECT执行 | 0.252107 / 8174次 | 0.254078 / 8181次 |
| SQL事务commit | 0.001047 / 1次 | 0.000931 / 1次 |
| 原五写SQL执行合计 | 0.000194 / 5次 | 0.000182 / 5次 |
| trace精确WAL fsync | 0.000817 / 1次 | 0.000671 / 1次 |

原始计时含监测开销；含子项的父行不能相加。SQL execute不含fetch/材料化，事件计时没有从Python父帧扣除；native.compare包含Python reducer。fsync由真实成功syscall单独关联，不等同于commit。


完整结构比较每笔约7,700次，是主要实测成本之一。不是fsync或五条写语句造成几十秒延迟。现有pure fixed-callee/serializer段已有late pin合并；相邻graph pin跨SQL、输入发布/扩展、cohort或callback，不能仅以重复调用为理由复用PASS。当前G1依赖五写后的真实VERIFIED attempt/operation、journal和事件，直接搬到写前会改变事实，搬到commit后又不能回滚。本轮选择落地有界租约准入修复，未启用仅限Linux实验的typed候选器或缓存旧权限。更深重构需要拥有完整预计postimage和动态依赖的纯数据计划、提交时逐项重核；目前没有被本轮证明安全的现成替代。

## 真实并发及取消

| 同一原大型fixture的独立隔离SQLite验收 | 实际动作耗时 | 结局 |
| --- | --- | --- |
| G0实际owner HTTP取消 | progress 93.803ms；cancel 119.055ms | G0 4.070秒主动回滚，未开始DML；RECONCILING |
| G0内另一连接修改材料 | 提交 16.874ms | 完整G0 30.362秒后旧快照升级失败，WAITING_RESOURCE |
| G0内另一连接撤销resource.read | 提交 14.999ms | 完整G0 37.967秒后旧快照升级失败，WAITING_RESOURCE |
| 真正G1持写锁期间owner HTTP取消 | progress 221.058ms；cancel 504.266ms | 写入区段 4.672264秒后ROLLED_BACK；RECONCILING |

每项6次固定Mock、0真实模型。所有目标RECEIVED/DISPATCHED、既有typed history、归档及资源严格保留；没有NS_SETTLED/NS_REJECTED、新结果或部分VERIFIED残留。G1测试提交 `c5f539e128d409883062cee007434ee8dbda09c9` 只改两测试文件，所有产品字节与9523完全相同（见g1-test-only-byte-identity.json）；不是用旧源码冒充新功能验收。

G1先完整完成G0 33.898732秒，自然进入G1 3.220278秒；独立timeout=0连接BEGIN IMMEDIATE精确得到SQLITE_BUSY(5)，没有写入。探针后和progress后均核同一首个epoch仍在G1，最终唯一snapshot有真实writer_seconds>0并回滚。没有逐条记录本次取消前五条DML的执行数，因此只证明已执行未提交写集回滚、五写效果无残留；不凭3秒推断五条必已执行，也不声称任意C段即时可中断。


G0旧快照不会即时看见已提交撤权；安全依据是它不能再升级提交，不冒称即时授权刷新。材料/撤权是实际另一Store的SQL提交，取消是原owner授权HTTP接口；元数据回读明确仅为COMMITTED_METADATA_ONLY，不是完整受保护内容。

独立新解释器只读重开确认唯一v1、SUCCEEDED、页面保存响应=应用输出=typed result；7个attempt中3个generation RECEIVED、Source/Cold共4个VERIFIED。主DB与空WAL前后hash均完全一致，最终验收没有用None/空WAL豁免；见reopen.json。

## 失败、环境中断与边界

前一冻结 `11bd47c3d4994991353e9c7162adf3a8cdc120cf` 用普通strace跟踪所有线程时开销明显：G0 64.852秒，G1在原120秒处回滚，6次Mock，当前attempt/operation为REJECTED_KNOWN/BUDGET_EXHAUSTED；没有将失败改写为成功。其原日志/XML/trace及partial profile均保留，不能用partial表与新完整表直接比速度。后续filtered tracer在自有合成SQLite探针先验证可用，未改产品权限、业务时钟或合同。

重开先误用了旧strict-WAL helper，WAL相等断言失败且未存前值，具体原因未知；之后一次已审helper调用遗漏输出参数，报告写入IndexError。两次均不是通过。最终独立进程复用已审规则、绑定本次run metadata并传齐参数，主DB和WAL完全不变后才计为通过；原失败单列，不修改/修复数据库。

原串行session44652曾恢复失败；fresh执行及正式环境状态实际可用。进程/日志核清cancel、input已exit0且无遗留进程，revoke无启动记录，才单独接续未启动项，不重跑已完成项。见session-interruption.json。

Intern token本轮仅核注入布尔为true；没有选定正式应用PG连接及真实principal/project/trial/approval，本轮真实模型调用为0，免费授权仍有效。[既有正式入口与具体输入](../../ProductionConnection.md)保持原样，不新建凭据/权限。新C的现有Linux二进制源码hash一致并实际参与完整流程，带构建宏的现有GCC语法检查通过；它不等于Windows新原生库或目标机、PG、真实模型全链、自然语义、owner验收。独立桌面包和已认可UI未改，第四Windows CI未启动，506秒预算保留。公开仅选定合成摘要/日志/XML/trace/脚本，不上传DB或原始模型交换包。

独立只读审查在本轮各阶段核过实现、资格、完整原件和限制；结论见readonly-review.json。原受认可UI/桌面宿主未改。
