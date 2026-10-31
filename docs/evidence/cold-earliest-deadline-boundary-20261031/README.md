# 更早截止修复；大型30秒仍未稳定可用

实际应用源码 **2ad3227621b48793a4d03747463b33207139147e**，已正常推送`dev/cloud-g0-live-20261028`并官方ref核回。上一应用2d41ad38b84630cb817d87374122bce31e357d0d、证据b5c3f898a352d100b890f7b243b17bcc39c9ae34及ZIP均保留。**本轮没有启用性能优化或纯数据计划，原普通30秒目标没有解决。** 没有提高30／120秒预算、跳过图校验或修改main／Release。

## 实际源码修复与失败原件

复核发现签署的SQLiteSettlementCaps 120秒路径只读取heartbeat state的fatal_heartbeat，未将原更早state.deadline纳入cutoff；原ordinary30路径已经取该最小值，不能据此假定120也已覆盖。当前state实际由worker发布binding.clock／Run最早截止，不是可以忽略的可选费用证明。

在改应用源码之前，同一原SQLite writer入口真实时钟复现3失败：state.deadline=0仍进入scope、记录一次RESERVED且改变lease；更早未来截止的commit callback跨界后，两种snapshot开关都仍将sentinel持久到DB，token却近120秒。原[失败XML/日志](raw/preparation-lifetime-before-b5c3-20261031.xml)及preparation-lifetime-before-b5c3的三JSON保留。应用当时src与2d41一致，HEAD为只加证据的b5c3；新增反例是当时未提交测试，不冒称该文件已存在旧commit。

修复仅5行行为变化：在原state.lock内同时捕获deadline，fatal仍原对象优先；缺失／bool／NaN／Inf／字符串拒绝，None和更晚截止保持原120逻辑；finite早截止只min收紧原cutoff。它自然贯穿原booking／RESERVED.deadline／wall+monotonic token／实际commit和cleanup的min，未重新起算node／Run或改变权限。四份软件资格记录按完整当前源重建，没有免检或源码文件豁免变更。

修复后首个JSON要求scope不进入、RESERVED=0、原lease不变；另两种snapshot JSON均拒绝越早截止的commit并回滚sentinel，token wall精确等于原更早state截止。原件和metadata非法/fatal优先/None／later、30／120、wall回退、stop、所有权和提交callback原回归见[75项冻结定向XML](raw/preparation-lifetime-final-20261031.xml)。完整16套件最终**307通过，零失败／错误／跳过**，约221.70秒，见[原XML](raw/lifetime-final-2ad32276-regression-20261031.xml)。不是全仓通过声明，不与安装子集相加。

## 生命周期架构结论和真实反例

[最小完整架构与尚未实现部分](cold-lease-minimal-architecture-20261031.md)。完整G0依赖已收到的模型响应／aid／wire／当前owner-fence，不能整体搬到claim之前。真实另一连接store.heartbeat提交后，原G0快照升级回滚；同G0连接续租UPDATE则被原只读门拒绝。两条新反例已在75与307中执行，未替换时间或伪造SQLite。现有通用snapshot测试另有SQLITE_BUSY_SNAPSHOT及ABA的精确因果断言，不能靠后移一行heartbeat复用旧Graph。

有意义方案需将完整Terminal Source／Generate纯事实族生产口至全部消费者迁移成严格自有不可变值，关闭准备事务后实际续租并开新Graph，重新授权、逐完整依赖比对，不携旧PASS；W5仍原子，G1 expected-post／全写集／回调／SQL环境证明也必须闭合。当前只移纯parse／compile或加一个仍执行完整spec.bound的wrapper不能解决大头，**所以未上线无收益原型，也未启用私有_owned_g0_candidate**。单移G0仍留本轮45–50秒writer区段，不能叫普通30秒完整保存可用。

## 本轮同条件大型两版本对照

固定顺序baseline2d41→candidate2ad，原同规模fixture／recipe、hashseed0、同CPython／SQLite、同四个已核源C扩展、同被动observer及诊断.so，先前307已结束后才开始，未并行测试／编译／测量。实际UUID／时钟／软件指纹不同，不声称逐字同输入或随机重复试验。旧bbe的29.4065／31.3387等数值属于历史；下表才是本轮各冻结版本实测。

| 版本／Cold笔 | G0读／准入秒 | G1阶段秒 | writer区段秒 | 原事务总秒 | 终态 |
| --- | ---: | ---: | ---: | ---: | --- |
| baseline／1 | 29.213887 | 43.305478 | 43.304439 | 72.519262 | COMMITTED |
| baseline／2 | 30.423459 | 45.781586 | 45.781027 | 76.204945 | COMMITTED |
| candidate／1 | 31.088062 | 45.451115 | 45.450233 | 76.539073 | COMMITTED |
| candidate／2 | 30.962690 | 49.600044 | 49.599339 | 80.562580 | COMMITTED |

G1阶段来自observer.phase_intervals，writer区段来自snapshot记录，边界不同，不互相冒充。G0记录含promotion／FIFO准入；writer从首DML执行前至cleanup，包含获取与清理，是占写区段的上界，**不是精确内核锁持有时间**。观察器开销全部保留。

候选两笔总耗时都比基线慢，本轮没有性能收益；只一组固定顺序对照，不把它归因未测环境或证明唯一因果。四个Cold phase的所有已测操作计数及累计编码量完全相等：例如第一笔G0完整图编码833次、累计743,310,245 B；G1编码821次、累计1,046,248,299 B。它们是重复序列化累计量，不是独立输入大小、驻留内存、网络流量或provider请求数。`source.current`是代码／所有权witness次数，不是实际账户服务调用。

[matched-summary](matched-summary.json)给每阶段互不重叠coarse exclusive耗时及未分类余项，原profile原件分别保存。候选G1大头prepare约12.33／14.69秒（含DB／完整lineage／权限，**不是纯计算**）、receipts6.02／6.45、trial.commit6.36／6.97、prove_node3.31／4.06。其余约17秒不擅自叫IO／fsync；包对照没有降低这些工作。不要重复相同样本试到偶然30以内。

每版本完整Generate3＋Source2＋Cold2＝**7次FixedMock、0真实provider调用**，Source epochs1／2和Cold epochs3／4分开；两笔均COMMITTED、原控制器最终Run SUCCEEDED。SQL mode字段LIVE只表示测试生产分支，transport实际httpx.MockTransport，不能称真实模型。各原controller仍核原账户槽间至少60秒，未改时钟或RPM；所以基线整次492.84秒、候选501.81秒含三个Run／原等待／前置流程，不是单一Cold事务或单一300秒Run。

两次原测试均exit0后，立刻各用新解释器只读重开，确认完整HTTP结果＝app output＝typed result；原Run状态、两条Cold Attempt VERIFIED、总7条Attempt、原数据库内容不变，见各matched目录first-reopen JSON。WAL absent／空文件的正常生命周期按内容对比，非空WAL绝不忽略，没有重试到过。原首次进程／完整命令／source-export清单／四扩展来源均保全。原数据库与独立Mock交换JSONL未复制到本目录；已发布合成HTTP结果及审计控制元数据，原Mock交换文件仍在云scratch并记录SHA。

## 当前原普通30合同的额外单次负例

两版本匹配对照都是显式签120，不能给当前原30路径冒签通过或失败。因此额外只做一次原TrialCaps30合成合同变体：保持原Source/Generate/Cold控制器、同fixture/recipe/四扩展/真实时钟/1RPM，只在准备输入中选择新TrialCaps，由**原库gate.approve**实际验证和存储同意。一次性prepare helper在任何应用调用前恢复原引用，生产文件／类／授权函数未改。原既有synthetic fixture仍模拟environment／account resolver并替换准入软件资格函数，和前面Mock对照一样；**这是原业务校验的工程模拟，不是正式生产来源、真实授权或live验收**，本变体没有新增免检替换。

这次349.49秒原控制器运行在首次Cold的原SUCCEEDED断言处未完成；诊断已经执行并通过“caps精确TrialCaps、lease30、没有120字段、同snapshot一笔ROLLED_BACK且27–120秒”前置断言。之后新写的scratch诊断错误地只允许Attempt仍RECEIVED，实际按原协议成为REJECTED_KNOWN，于是该**诊断pytest退出1，失败原件完整保留，不改签绿、不再次运行应用**。

[独立只读审计](ordinary-thirty-negative/ordinary-thirty-closed-state-audit-20261031.json)从已结束的原DB单一只读快照验证：持久P-B合同确无extended settlement；6次FixedMock、0real，首次Cold收到完整响应／known Mock usage1000后记录NS_REJECTED/BUDGET_EXHAUSTED；原response指纹与NS_RECEIVED一致，model op无成功receipt、无NS_SETTLED／该model step成功事件、无typed结果，app.output为真实SQL JSON null、result_version为空。既有read operation可以保持VERIFIED，不能把它误当此次model验收或要求整Run所有事件为零。审计没有修DB或重做业务，主DB字节不变；原数据库／raw Mock交换仍留云scratch，仅身份和合成控制证据归档。

原advance_model的DomainError处理本来就允许将同response／usage的RECEIVED→REJECTED_KNOWN并记录已知预算拒绝。其整函数、普通writer scope和original_interval在2d41／2ad字节相同，见[函数hash对照](ordinary-thirty-negative/unchanged-runtime-function-hashes.json)；不是这次signed120最早截止修复的新回归或响应丢失。NS_REJECTED发生在最后实际wall lease截止前0.029389858秒，随后真正过期的heartbeat被原Stale worker lease拒绝；这与保守monotonic／stop判定在wall之前相容，**没有原mono token日志，不能进一步断定唯一触发时钟**。原错误实为Finite model settlement interval ended，case结束时node／Run300及Trial截止尚未来到。

单次原Worker.once结束后，Run仍RUNNING/v1/fence1但lease已过期、无成果。没有在此负例重启持续worker／自动恢复或取消，不能称永远卡住或已验最终收敛；更不能在界面显示SUCCEEDED。当前这个原普通30规模的目标确未完成，仍在产品不可用边界内。307／安装44的通过范围与这个新scratch诊断失败分别报告，**只读negative审计通过不等于业务目标通过**。

## 新安装包与可用范围

[新ZIP／wheel准确身份](../../../deliverables/limited-text-candidate-deadline-20261031/README.md)。Linux x86_64／CPython3.12，本机glibc2.41，已有锁定运行依赖；不是Windows下载即用包或干净机依赖安装证明。原2d／1a ZIP未覆盖。

离线build／安装到新的专用venv，显式.pth仅复用已有依赖；python -I在源码目录外实际导入10个关键模块并逐Git blob核字节，原src不在sys.path。223条库存／嵌套wheel／四个.so完整C/header/Python输入hash匹配。安装后的新期限14＋图29＋正常UI/ASGI1＝**44通过、零失败／错误／跳过**，与307重叠，不累加。

新安装包默认CLI实际创建CSV／草案／内部版本／实例并执行sum=30、result_version=1；同键无重复Run，首次新进程重开同完整结果。自由目标仍FAILED/UNSUPPORTED_CAPABILITY，不偷换为单文本合同。两次真实SIGINT均STOPPED clean、exit0、双EOF；普通CLI随机origin53677→58703，不冒称桌面稳定origin。另在私有原工作区副本回读1a原真实成功结果、原键和五表不变，Attempt/Reservation9→9，原源DBhash不变，0新调用；**不是2ad新执行live**。真实1a两次调用1739tokens仍只属于原证据。

完成所有安装回归和服务关闭后，实际只卸载本次专用venv内应用，包／metadata／命令移除，6个工作区文件hash及30个共享METADATA不变；未删除用户数据、共用环境或venv。安装／启动／停止／重开／卸载范围沿包内docs/LimitedTextCandidate.md，默认数据保留。实际runner、日志及JSON均在本目录。

## 尚未完成

**原普通30秒合同下的大型Cold路径尚未稳定可用。** 此轮只实修最早截止，签120保存成功不能替代原30目标；完整纯数据计划及W5→G1等价桥仍待工程实现。现UI配置不足停止提交、MODEL_EXECUTION_REQUIRED待执行、失败／未决不显示成果完成；原SUCCEEDED仍须持久结果全核查，不改usable_product或人工／通用语义／正式发布门。

正式PG仍缺现有连接及principal/project/trial/approval/account来源选择，新Windows／大型live未验。所有新增模型真实请求0；未新增Windows CI、电脑执行、费用、凭据／权限、训练、main修改或Release。不能把小CSV／历史live兼容及本轮两笔Mock保存推广为完整产品交付。
