# 最小实质修复提案：一个Cold结算的完整内容快照与原期限内读集CAS

状态：**待独审的架构提案，未实施、未获运行资格**。只讨论现有test-only SQLite
accounted native的一个已RECEIVED模型节点，保持默认路径、生产账户门、PG、post/origin
旧协议不变。不是恢复原样再跑，也不是用新grant/更晚renew延长原G0时间。

## 这次证据改变了什么

本次原Run消息拒绝处的已有参数再评价为20true/2false，仅before_lease与对应min关系
不满足：at−lease=1.1715714931488037秒，Run及contract仍分别余214.96321511268616、
1459.2702629566193秒。它不是原短路trace；但已排除“只知道总wall接近30，继续赌一次”
作为下一步依据。second prefix只0.056237143秒，原第二commit已花3.585821897秒，
其中_recheck已花2.247529643秒/273checks；剩余1.338292254秒仅已执行部分和解栈。
_recheck内codec0.922421088、raw_copy0.609859157、typed_storage0.236230090、
typed_equal0.231599413线程CPU秒，嵌套时间不能直接相加作为总CPU归因。
这证明当前尾部还有可观的内容扫描/模型快照成本，不证明每一次调用均属必要，也未
测得成功分支_recheck后续/正常scope关闭成本。没有下一轮完整窗口提案。

Store.tx在SQLite以BEGIN IMMEDIATE持写事务，advance_model在renew后将完整prewrite
放在该事务，第二门后才原五写组。SQLite单写者及BEGIN IMMEDIATE阻止其他writer的
语义已核官方资料：[Isolation](https://www.sqlite.org/isolation.html)、
[Transactions](https://www.sqlite.org/lang_transaction.html)。同一连接自己的写仍可见，
不能把“别的writer阻塞”误认为“当前对象/同连接状态永远不变”。

**单纯挪走BEGIN或让heartbeat可写，不能解决当前约31.2秒超过原30秒lease cap。**
必须减少重复内容工作，并保持原cap；拆锁本身没有性能通过含义。此前领域设计
`../cold-domain-boundary-design-20261021/DESIGN.md` 的未闭合项仍有效，本提案只把其
后续CAS边界具体落在`advance_model`的本次模型结算，不泛化重构全平台。

## 单一集成边界

- 起点仍为原response/usage接收及archive事务已提交之后、原renew的位置。
  不将renew挪到长计算之后，不将重领lease当成本次成功。
- 终点仍为原第二语义门、scope最终新鲜期限门之后的五写组及原post/live/tail/settle。
  NS_SETTLED、Attempt/Operation VERIFIED、App Run与SPEC_STEP_VERIFIED保持同一写事务。
- 第一/第二门的内容关系不删。仅将**已拥有且所有消费者闭合的内容**规范化验证一次；
  当前授权、撤权、Run/worker/version/fence/cancel/stop及全部finite在动作/提交处仍重查。
- 现有Source/Generate owned仅覆盖两族，**不是整个Cold对象图已不可变的证明**；
  不能据此现在删剩余pin或把旧CGR/issuer/handle跨连接、事务、scope继续用。

## 最低正确算法与证明条件

1. **T0短一致性读。** L0必须绑定原位置那一次同步renew实际写入且提交的精确
   renewed_until（同次返回或受锁保护的精确sequence/worker/run/fence见证），不是之后
   回读最新runs.lease_until，也不是heartbeat state的max(lease_until)。Store.heartbeat、
   renew_sync已有精确提交后返回值；当前runtime.renew两分支丢弃它，未来须只向上转交
   该同次值/见证，不增调用或重采时钟。这是未实施的明确接点，非当前已有L0能力。
   再捕获原Run/node/source/approval等期限。敏感读取仍先原授权。收集本次结算实际需要的全部领域值和
   读取见证；事务结束前复制为服务端拥有的不可变值，保留原bytes、全部字段/隐藏数据
   与严格类型。DAG仅复用已完成不可变子值，cycle/未知对象按既定规则拒绝；不得保留
   外部RowMapping/Pydantic/原dict/list/view或回调引用。
2. **锁外纯计算。** 内容函数只消费这些不可变值，无SQL、新敏感读取、网络/工具/回调，
   不发授权。一次内容规范化/SHA可复用其值，不复用任何可变验证PASS。原签名、业务
   指纹、原始回执/usage/UNKNOWN保持；新私有manifest不得冒充旧pickle/raw/pre/post/
   origin/software digest。计算与关闭仍计入L0和其他原期限，过期不复活。
3. **T1短写事务。** 新BEGIN IMMEDIATE后重新取得当前owner、worker、version/fence、
   status/cancel/stop和原权限交集；**取得写锁后先按当前时钟检查L0及原最严期限，
   将busy等待计入，必须早于任何新受保护回读/结果发行**，随后原各后续/最终检查点
   仍保留；Store.guard只看当前lease，不能替代此L0门。新敏感回读前先授权。
   对下述完整读集逐谓词重新读取
   完整投影、与T0比较。读取版本变化/新增删除/空集/来源未知/集合变化均在写前拒绝，
   不中途fallback、不重发、不自动重试。最低版本不依赖epoch，因此不假定所有写入口
   已维护一个revision；未来若改用epoch，才须另证全部正常/后台/修复/直接SQL写路径。
   首个最低正确版本**全部见证Run列（含lease）变化均拒绝**，不默默把任何Run差异
   归为heartbeat放过。正常heartbeat增长也会造成冲突，可能频繁拒绝；不得关掉原
   heartbeat迎合候选。放行lease-only非减少更新是另一个待证契约，须逐消费者/持久
   指纹映射后独审，当前不采用。因此安全设计ACK也不等于功能/性能运行资格。
4. **原子提交。** CAS比较和五写组必须在同一T1；比较后不允许未见证的可变callback或
   脱离锁的外部动作。保留原conditional写与实际postwrite读回/授权/账链/尾门；任何
   故障整体rollback，但既已提交的原接收与archive事实不丢。
5. **期限上界。** 最终提交的lease上界取min(T1当前有效lease,L0)，再与所有原Run/
   node/source/approval/contract finite取更严格值。正常heartbeat即使发生也不能扩大L0；
   任何lease减少、owner接管/version/fence/cancel变化均拒绝。不得用更晚at替换已过期
   检查来“续命”；所有原规定的检查点及scope关闭后时钟必须明确映射，非默默删除。

**条件证明。** 若每个纯消费者只取不可变S，T1中每个被消费事实/谓词Q的投影与T0
相等，且当前动态权限与期限成立，则纯结果f(S)仍适用于T1；T1单写者排除比较与五写
之间的外部DB改变。完整谓词结果见证覆盖phantom，不能以已读ID集合冒充。预期写
delta后由原post验证，不拿T0的RECEIVED与本次有意VERIFIED直接做“相等”比较。
单写者只保护数据库，**不保护进程settings/stop/registry/内存**；后者仍须以所有权、
必要锁/原检查点映射和无回调证明独立闭合，不能从BEGIN IMMEDIATE推导出来。
上述前提任一个没有证明，**不能启用新路径**。这是安全设计的条件推导，不是声称
现有实现已经完成全读集/无逃逸/性能证明。

## 此结算的完整读集必须覆盖的族（缺一即不合格）

| 入口/消费者族 | 必须见证的值与集合/空集关系 |
| --- | --- |
| lock_live/_cold_commit_from_audit/_recheck | 冷Run完整相关列、worker/owner/version/fence、关联Run不存在谓词、预期资源/Runtime/请求、原lease cap |
| _requirements/_approved/_keys/_saved | 完整Trial/Approval/源及Cold phase/撤权记录、按kind/key过滤的全部集合与缺失值、原业务指纹及审批对应 |
| _cold_first_binding与各binding/release prefix | App/实例/Recipe/Goal/Material/Release/冻结schema/model/tool版本，以及每个lookup的当前修订/来源内容 |
| Source/Generate accounted与两个stage/context/archive | 全部aid、Slot/Identity/Outcome、request/wire/response/usage、来源归档与业务指纹、集合增删及无未知用量 |
| _cold_receipts/_receipts/_ColdRunFacts | 完整operations集合/顺序/缺失后继、intent、effect、node-input/proof、pending_id及两成对receipt根，不能只登记实际已见op IDs |
| 本次settlement | 精确aid/run关联、STARTED→RECEIVED原事实、response bytes/usage/parse/schema/receipt、reservation原占额与未决请求集合 |
| authorize/authorized_read及来源resolver | 用户/项目/App/资源权限交集、Grant/撤权集合及实际来源内容，不用旧授权结果作新敏感读取准入 |
| 进程动态前沿 | worker/settings/transport/current binding的实际内容、model/max_output_tokens、stop、可信注册表/软件版本；身份相同不代表内容相同 |

见证必须是**实际完整query/消费者字段映射**，包括过滤、关联、排序、聚合、存在/不存在
与空集；非确定first/无序选择须证明唯一性/等价关系，不擅加SQL LIMIT或全局JSONcap。
proof_authorities只收集authorize调用，**不是SQL全读集**；现两accounted族manifest也
不是此表其余族的见证。当前仓库尚无已证明覆盖该表的统一读集，因此不能现在仅加
Run CAS就拆事务。跨事务也必须重新发行新scope/内容证明，旧graph nonce全部失效。

## 可实施前的最小一体化证明包

不再造孤立准入常数或继续完整窗口试时长。下一片应交一个默认关闭的**本次结算**
集成候选，连同：逐producer/consumer字段与query映射、全部被消费值无可变逃逸、
每个谓词/空集的T0/T1重读对应，旧新持久指纹隔离，L0到最终门的时钟映射。
无统一有限输入上界仍保留既有LEGACY接受域；新路径资格必须在任何发行/业务动作前
一次选定，不能拿诊断专用64键/256索引/64bit等限额充产品bounds，也不能中途降级。
若无法在不重复producer/不跨旧scope的前提下完成资格选路，则该项本身是启用阻断。

必要反例：version-only/fence-only/cancel-only/lease-only/Run-only/contract-only与成功
对照；撤权/Grant增删/空集→非空/无关行与相关字段变化；新operation/intent/未知usage；
来源bytes/schema/model设置变化；旧buffer意外mutation及跨scope重绑；T1 CAS之后
每个写点故障原子回滚；接收原件不丢；L0已过而当前lease更晚仍拒绝；busy/snapshot
冲突不自动重放。先纯合成/隔离SQLite完整集成及独审，未闭合不改运行路径、不新窗口。

本提案不承诺缩短多少秒或一定过30秒。真正改善来自消除重复内容计算，而非改变
lease开始点、放宽期限或单独放开heartbeat。PG与真实生产账户资格均不由此推导。
