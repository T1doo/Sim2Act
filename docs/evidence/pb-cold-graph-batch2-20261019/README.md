# P-B Cold 结算共享谓词：第二批

基线 `e84f98bbc13262bcd6f54a3b94c6d8b750af788d`。仅改 pb_natural_specs.py、natural_source_archives.py、pa_trial_dispatch.py，新增8项定向测试；11个私有事实叶共用原唯一谓词实现。Source audit仍在纯字段指纹之后，verify/name短路不动；完整归档字节、原始/canonical区别、全量历史/多重集、NS/controller和usage配对、完整Limits角色及原SQL/首错位置保留。未改sender/reserve/reject/租约/五写/其他家族，未接图或shadow双证明，完整history尚未平直。

[逐叶caller责任表](CALLER-RESPONSIBILITIES.md)是边界的一部分：完整历史、同事务/epoch事实、当前权限及原顺序由调用者承担；私有叶不是授权入口。第一批 _bound_from_checked_facts 不替TX/完整ledger/typed，counter叶不替前置typed-row门。

正式短门13 PASS/0 FAIL/ERROR/SKIP（新增8＋原adapter3/第一批纯顺序2）；Ruff四文件通过，mypy113源文件通过。Linux/Python3.12.14/隔离SQLite；存在5次显式MockTransport adapter请求，真实模型调用0，无Worker/成功Source/P-B长链。QUEUED Run/VERIFIED Attempt的测试种子仅为synthetic字节事实，不是完整批准/ledger/成功Source证明。每组pytest有1条既有Starlette弃用warning。

首轮新增测试7P1F：错误预期把继承Limits等同候选Limits。原natural.expand固有max_repairs0未改；v2仅改测试，分别核继承完整向量、派生完整向量及真实candidate=approved2/compile=platform4参数。原失败与两版本快照、全部日志/JUnit均保留。mypy在v1执行；三生产文件v1/v2字节相同，测试文件不属mypy src输入，没有宣称v2测试被mypy检查或全113源码输入封印。

独审 **BATCH2_FACT_LEAVES_ACK**，49项独立基线AST对照，0开放P1/P2。报告SHA256 `f801d47c5430228078874b13954f059c6ee6f2c6dbe68422d70b4624f738cf21`；manifest SHA256 `5cfbf2ade43a644e10b35f6e4d1382504e4cbacb2cd1a25975cb54bb3f35f687`（54成员，不含自身）。[原始证据包](raw-evidence.tar.gz)及[完整性回执](RAW-SEAL.json)包含完整最终独审和所有本批门；不含测试SQLite DB/符号别名，不代签未来commit/push。

[第一批超时证据](../pb-cold-graph-batch1-20261019/README.md)保持原样。上一轮完整P-B仍 **FAIL_NOT_ACCEPTED**，完整指纹/祖先独占成本仍 **UNKNOWN**。本批没有完整图/性能/P-B集成接受；Windows、PG、真实模型/语义/场景、人工验收未执行，远端CI未验证。旧满盘最终独审缺口仍缺失，下一批未开始。
