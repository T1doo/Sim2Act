# 第二提交Run拒绝与尾段诊断：默认关闭、未开新窗口

基线 `d665c69074e3d97c3332e65a933bb0eaa4dd118d`。上一窗口真实拒绝点是
`second commit → _recheck → _require_run_context_row`，不是前窗Store.guard，
也尚未到最后有限期限检查。没有该次actual/at，不能从G0 30.890秒唯一归因lease。
本片仅补下一次判因所需诊断；**没有新grant、Mock、Worker、G0或真实模型运行**。
上一窗口UNKNOWN/NOT_PROVEN不变。本片不实施心跳/延租约/事务拆锁或其他优化。

## 接线与证据边界

仅显式synthetic candidate的launcher安装；产品src、预算、授权/DB读集/事务/
fence/stop/期限检查全无改动。原Run谓词精确调用一次，保持参数、原at、guard顺序、
原异常对象/cause/suppression及原短路。异常后，另从已有安全参数存储再算比较bool；
不调用_guard/_trial_result、SQL、time.time、model_dump、repr或序列化。

**POST_EXCEPTION_EXISTING_SAFE_ARGUMENTS_NOT_SHORT_CIRCUIT_TRACE** 明确表示
事后只读再评价，不是原and中每项当时实际执行的轨迹。原guard可能先抛，字段也可能
在原guard回调中变化，故即使出现false也不自动唯因化。仅记录错误类型及是否匹配
原Run谓词固定消息，不记录身份/资源/完整业务载荷；身份等仅bool。记录原at、
lease_until、created_at+caps.run_seconds、contract.expires_at及三者min。

诊断子域：exact已知模型安全__dict__（最多64键、键全exactstr）、dict row或
exact RowMapping（_data最多64、索引最多256，原生迭代，只投影exactstr/quoted_name，
忽略外来alias但不执行其hash/equality），字段text最多256字符，整数最多64bit、
有限float绝对值最多1e20。先门后算，非有限标量不导出NaN/Infinity，记null及incomplete。
这些只限制**新增辅助观测**；超出时不改变原业务接受域/异常，只使证据不完整。
未知模型/描述符/外来元类/字典键/不支持字段均不为取诊断额外调用回调。prefix先核
exact原_ColdCommitPrefix类型，安全字典后取key；boundary先exactstr再比较。

固定四尾段：second_prefix、second_commit、recheck、scope_exit。记录monotonic_ns
wall、foreground thread_time_ns CPU、原check/input_key计数；现有codec/typed_storage/
raw_copy/typed_equal四项仪器扩至这四段，内存聚合，原context退出后才归档。
只有second_commit→recheck这一种嵌套；metric桶按最内层归属，所以second_commit桶
排除recheck。时间/原计数是inclusive，second_commit−observed_recheck另给余段，
仅扣已观测子span，不称所有child独占；缺失/负差/诊断故障标不完整，不补零或推算。
未进入段calls=0就是NOT_REACHED，不能外推其完整成本。

scope proxy位于StopBoundary内，只包**原_cold_model_before context对象.__exit__**，
原__enter__/__exit__各一次，原exc triple与__exit__原返回值不变；不把外层必抛
G0Stop算成scope失败。exact target来自原StopBoundary.bind/entered之后的
CandidateObservation.trial，Source/Generate/独立入口不归入尾段。
StageObserver默认仍原5stage/20rows；仅显式candidate开启9stage/36rows。

诊断clock/counter/存储/report失败不替换原异常或影响原cleanup；report标INCOMPLETE，
record_tail在原工作返回/异常之后将最终**诊断分类**改UNKNOWN，不能冒充完整G0通过。
不更改业务返回或原门的通过/拒绝；原candidate完成条件（两commit/原scope最终期限）
仍保留。仪器非零开销，不是无仪器性能验收，不声称CPU/RSS或磁盘原生硬配额。

## 实际验证（无完整运行）

原Run谓词有限反例覆盖lease-only、Run期限-only、contract期限-only、version-only、
fence-only、cancel/status、身份/资源、created interval、非有限、类型错误及成功对照；
真实RowMapping+已知模型构造值（未验证成产品资格），原guard执行序列/异常对象保留，
禁止SQL和业务time读取。guard先抛的对照所有事后bool可真，防止误认Run门是唯一来源。

纯合成尾段验证四span、嵌套metric归属和inclusive余段；scope body/exit异常、原抑制/
原exit返回值，诊断clock开始/结束、聚合、线程/选择/report故障均不改原控制流。
外来类型元类、碰撞字典键、prefix/boundary/error描述符和RowMapping隐藏foreign索引
均有外部callbacks计数断言；即便observer吞掉回调里的pytest.fail，外部断言仍会失败。

初有限25P/0.19秒。旧stage9项出现7P1F1E，原因是新增桶改变默认shape；原失败日志
保留，改为explicit opt-in后未删旧断言。Ruff初E731仅测试lambda风格已修。
冻结相关批 **66P/10.56秒**（JUnit10.559），纯observer/guard **48总=44P4skip/
0.597秒**；四skip均需独立编译native unit依赖，非新增保护通过或硬配额证明。
随后依独审只增强外部callback断言及真实RowMapping foreignindex反例，诊断三个源
保持原SHA，最终选中 **9P/0.18秒**（JUnit0.176，25 deselected）。不把66批声称为
最终test版本整批实跑，不相加成75个不同测试。运行中未改源码/测试，冻结前后SHA
均实核；最终Ruff四文件通过。gzip原件/manifest可逐字节恢复，开发失败未覆盖。

最终诊断源SHA256：

- g0_tail_observer `b23c45591ca71b98d04a3c38fa5ccaf0141adf66476edae31ee33b37e8efc4a8`
- g0_stage_observer `adacdff642f9dc30693df817c49c28e87114a14e813d7143e323ed14eab00d03`
- g0_prefix `dfe1299c28746db393afa3c26340c87792e7b39d665548f093c1b472151647d4`
- 最终test `f60cc0865a42070cdfd2b7f10ce93f13f96b63d888498dfcb6e98cb146c780be`

## 当前结论

本片证明观察器局部语义与诊断价值，**还没有本次真实Run假项或完整尾段CPU/wall**。
因此不能判定尾段主要是必要校验，更不据此实施事务边界/CAS架构改动。若后续决定
一次完整观察，须新冻结摘要/新目录SQLite/单次grant，仍6Mock/8入口、prefix480/
G0120/总600+清理10、lease30/Run300/TTL1800/RPM1/reservation60、64MiB采样等
原门，禁Cold2/W5，不自动重试；本提交本身不执行或授权新窗口。

两位独立只读reviewer已封限定SOURCE/BUILD及有限证据ACK，见reviews；发现的P2与callback证据盲点均有修正回执，未隐藏中间意见。reviewer未执行产品、测试、数据库或窗口。
