# G0 原30秒归因与原字典边派发实验

## 状态与真实范围

验收源码 `4e7b44437cfeea4d802aeaba9d344afecf3f5e33`，匹配业务基线 `97f4c0af7932c21cb21b6498b642b1639ab050ca`。普通30秒仍失败；Graph.commit是图校验方法，不是SQL提交。小型CSV保存／同键复用／正常停止／首次重开沿已验35e Linux限制候选保留；不把大型路径失败泛化成所有基础功能不能运行，也不把小目标推广为大型可用性。正式PG、大型live、新Windows和任意目标语义未验。本轮所有大型业务为合成固定Mock、test_only文件SQLite/WAL、真实墙钟；0真实模型。

## 先归因，不猜缓冲池

HEAD2a（应用字节97）的原30秒CPU／墙钟观察器d71ad614…：G0执行前缀CPU29.956832／墙钟29.961369秒，errors／未闭合frame／SQL均0。带观察开销，非无观察SLA，未执行剩余G0和G1。

| 最大互斥目标 | 次数 | CPU秒 | 墙钟秒 |
| --- | ---: | ---: | ---: |
| native.full_match | 6467 | 4.754059 | 4.761692 |
| native.pin_resolve | 41804 | 2.608670 | 2.633089 |
| typed.storage | 7574 | 2.411171 | 2.416883 |

Graph.check6481次：原read_checkpoint4325、typed trial_pin1273、Source own_fact318、trial._base309、Graph.add235、其余21；storage7574=Graph.input_bytes7526+OriginFacts.input_key48。parent inclusive不可再与子成本相加，不能按调用比例分摊时间。零化某函数只能给已执行前缀的归因天花板，已证安全可消除下限仍0，不能据4.76秒推完整30达标。

affb内部C分桶原30（另一诊断，不能与d71的调用量相加）：6904次match，约929.6万原dict命中。线程CPU分配0.042713、完整walk4.760901、cleanup及final-tags0.272050秒；reducer0.929022已包含在walk。walk减reducer3.831878也包含内部计时开销，不是无开销纯C成本。三段CPU和外层墙钟5.139447不可相加；若重入，父子聚合可重叠。Linux线程CPU正常实现，本工具的跨平台fallback不能签成同一时钟域。

因此拒绝缓冲池／touched清理方案；分配最多0.043秒，不是主瓶颈。临时四个CPU桶及time.h已从最终候选移除，诊断提交和原输出保留。

## 实际默认路径改动与审查

C compare_edge对已完整捕获的原exact dict、非零原版本、尚未memo的边保留原work／depth／entry signal边界及正反alias赋值，调用共享完整字典证明，避免通用类型派发递归。entry handler改变tag则转完整compare_node_data，不重计work或重放signal。共享证明的额外signal、原保守逻辑work边界、每次callback后tag复核、flat_ids和所有callback-capable清理后的最终tag复核均保留。exact原dict不能改变builtin类型，Tree保有强引用；未缓存Graph PASS或动态授权，不跨调用复用当前对象或alias数组。未知表示仍回原完整路径，W5五写和独立G1未缩减。

既有只读reviewer审查signal、异常identity、重入和alias无新增mustfix；313项相关／最早截止／commit尾窗及真实POSIX信号回归0失败0错误0跳过。原92项是重叠阶段，不累计签产品完整。最终计时已移除后的313项绑定4e7字节，源码冻结前后均clean。

无计时组件三对AB／BA／AB：重编97 C源码（非当时旧二进制）对冻结4e7，每臂1200完整比较、2000个合成dict，CPU中位57.164161→42.111113毫秒。两臂命中和逻辑work相同；只签该组件，不签Cold、净收益或SLA。初次含计时pair属于旧WIP字节／可能与回归并发的探索，保留原件但不用于正式速度结论。

## 原30秒负例

4e7原30使用与97相同轻观察器63460fa7…，Epoch29.959511秒，在首笔图commit→PB archive链→journal models→trial pin→Graph.check→动态checkpoint耗尽。首次DML未尝试、未完成、未进入G1；6Mock，接收响应／已知用量保留，预算负例断言通过不是业务目标成功。741次完整编码／612399762字节；7434次projection return不等于编码次数。97同观察器741次编码、7431次projection return，截断工作量近似，不能称明确改善或按窗口长度推提速。

## 中间失败与边界

CPU v1误引用runtime._graph_run_context而非typed，setup前即失败，0模型请求；v2先独立probe再真实运行。probe显式过期token只校验观察器，非业务性能。组件baseline构建首次从/workspace误用相对.venv路径，退出127、未构建；绝对解释器改正后的构建与数据单列。未删除失败原件、未放宽业务断言或预算。

保持版本内容完整性、owner／epoch／nonce／动态权限与撤权、stop／最早双时钟截止、过期续租拒绝、原子写和完整W5→G1。仅开发分支正常推送，无main／Release／新WindowsCI／电脑操作／付费／新凭据权限。现有token仅核注入布尔；无值落入证据。

## 相同大型输入：本次观测净收益，未恢复原30

均为同4e8e38…详细观察器、相同原fixture、无并发测量、固定Mock7次／0real／文件SQLite；表取snapshot-writer-timings字段，单位秒。

| 源码／笔 | G0 read | writer区段 | 总计 | 终态 |
| --- | ---: | ---: | ---: | --- |
| 97／1 | 35.738815 | 52.845530 | 88.585218 | COMMITTED |
| 97／2 | 38.375503 | 54.954441 | 93.330577 | COMMITTED |
| 4e7／1 | 34.115723 | 51.034718 | 85.151420 | COMMITTED |
| 4e7／2 | 35.219780 | 54.017114 | 89.237499 | COMMITTED |

本次总差−3.433798／−4.093078秒（约−3.88%／−4.39%）；不是重复随机配对或无观察SLA，环境波动及归因不确定性保留。不能把全部净差归为C边派发，更不能乘组件26.33%推业务。writer区段也不是SQLite精确锁获得瞬间。

独审逐key核所有timed调用次数完全相同，四phase编码833／820／869／853、每phase字节／projection及checkpoint20327／20614均与97相同。native.full_match四phase97为5.081510／7.065838／6.010151／7.462209秒，4e7为4.669680／6.382481／4.839978／7.043015秒。未减少完整输入、校验、动态授权或五写后的独立G1。两笔G0仍超过30秒；此显式120合同不等于原30通过。

保存后首次新解释器只读事务回读PASS：SUCCEEDED／typed v1、两Cold VERIFIED、7总attempt、HTTP／app／typed结果一致；主DB内容不变。WAL absent→empty是空辅助文件生命周期，physical identity明确False，非空WAL仍要求字节完全一致。

## 剩余结构缺口，未启用替代

测得7526次Graph.input_bytes都需完整PBTrialContract投影。真正尚未公开的生产所有权边界位于ProductionTrialBinding.__post_init__：原完整校验和parse_contract得到checked后，当前仍公开可变model根。dataclass frozen仅保护binding赋值，不能冻结caps／bindings／goal／recipe等深层值。

后续必须是完整PB合同族所有权迁移，连同binding/preflight/evidence、Graph／role／context、settlement caps/deadline、G1／archive／proof和DB恢复／cancel出口全迁移并退休原可变根；现有AppManifest所有权不覆盖它。未闭合前仍执行全部fresh扫描。精确否定证据在[input-bytes-copy-feasibility](../input-bytes-copy-feasibility-20261021/README.md)及test_cold_typed_storage_alias_contract：共享caps／键身份／顺序／复制窗口，不能重复浅拷贝／键池／借用snapshot方案；[旧GC限定typed backend](../typed-cohort-limited-20261031/README.md)普通GC覆盖0亦不能直接启用。完整新所有权方案尚未实现，不能写作已优化。

旧已安装Linux候选仍为35e源码：[Sim2Act-local-candidate-35eaa941f544.zip](../../../deliverables/limited-graph-current-20261101/Sim2Act-local-candidate-35eaa941f544.zip)，3,270,375字节，SHA256 `927501b0a87aee143ed152f998073be31631b4104cec642cfe697e8fdd49155b`。仅Linux x86_64／CPython3.12及已有锁定依赖；已有安装后CSV sum30/v1、同键复用、两次正常SIGINT停止和首次重开证据，不扩签新4e7或Windows。卸载仅移除所选Python环境内sim2act，保留工程／导出／日志与共用依赖；35e未另做卸载实测。

## 实际持锁取消与收敛

相同完整大型fixture，显式120合同，6FixedMock／0real。真实G1持锁探针SQLITE_BUSY5且未改数据；GET0.024659秒、cancel POST0.476484秒。G0 read33.460180、writer3.729029、总37.190025秒，ROLLED_BACK；此前历史、已接收Attempt正文／已知用量、资源、归档和typed均保持。比97取消样本G0／总时长更慢，不能概称所有场景提速。

原测试刚回滚后是RECONCILING／RECEIVED／DISPATCHED，不篡改为CANCELLED。随后原DB私有副本默认Worker.once实际收敛CANCELLED；重复cancel HTTP200/CANCELLED，第二个全新Store.once=False，0新model attempts，只有目标Attempt／Operation状态变为REJECTED_KNOWN、其余列及所有非目标行不变，原DB内容未改。未更改租约；默认Worker在复制数据上按原领取／恢复门自行判定资格，未替换时钟或Provider。原报告lease_expired_at_start字段实际上在结束时比较旧row值，且0释放值也满足，不能证明自然到期等待或真实起点租约值。

[精确执行身份](identity.json)、[完整大小与SHA清单](artifact-manifest.json)、[配置秘密值扫描范围](privacy-check.json)。本证据不包含DB或模型响应正文。源码与后续证据提交分开，4e7默认实现保留，但不生成新版安装候选；原30秒、大型live／正式PG／新Windows边界未闭合。
