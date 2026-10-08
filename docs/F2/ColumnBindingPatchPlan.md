# CSV 列绑定局部修改：离线工程病例

2026-10-08 用户授权的实际开发，冻结远端 `dev/f1-foundation` 基线 `122b2e6f25402e5d693da05c945727b7cbf4ceeb`。独立开发分支 `dev/offline-column-patch-20261008`；main 是初始化内容，本次没有在 main 实现。工作树起始干净；仓库及 `/workspace` 未发现 AGENTS.md，`/workspace/.agents` 为空，仓库无 `.agents/skills`。

依据原 V5 §9.1–9.4、现有 DeliveryGraphIndependentContract/IntegrationContract：原合同的 planning-only 限制适用于原纯计划模块及原计划接口，不禁止本次用户明确授权的后续草案/检查执行。原接口和其 false 断言继续保留。新增固定能力不声称通用增量执行/发布。

冻结病例复用 `docs/FirstUse.md` 与 RegisteredRunQuickstart 的合成 CSV：`item,amount,quantity`、`A,10,7`、`B,20,8`。测试夹具 `tests/fixtures/column-binding.csv`；期望值由独立 csv.DictReader + Decimal 求和核对，不调用产品汇总函数：amount=30，quantity=15。原 `tests/fixtures/f1.csv` 只有 amount=4，不用它冒认本病例。

实现同一应用/求和节点的 **类型化参数绑定覆盖层**：原 canonical candidate/manifest/actions/input_schema/source/data_bindings/views 不变；新定义冻结 `column_binding(field=column, schema=string enum, value=quantity)` 和原 amount 输入。enum 来自既有可信 CSV 有界数值列解析，不接受客户端自授 schema/context/权限/代码。图中原 ACTION ID 保留，新绑定及其所有声明下游 ACTION/ARTIFACT/VIEW/CHECK/MANIFEST 增加不可变节点 revision，传播组成指纹；GOAL/SOURCE/REQUIREMENT 全内容/ID/revision/fingerprint 保持。新图是 preview 绑定草案图，不是新的 canonical AppManifest/Release。

已有交付图 API 下新增 column-patches，复用项目事务锁、当前授权、候选验证、原图锚、人工锁、来源与源码版本、delivery_graph_requests 及其独立 seal。没有新增表、DDL、Grant、身份或应用平行架构。定义提交与精确 patch_fingerprint 确认检查是两次显式动作；实际汇总复用 authorized_read/data.aggregate_csv 和原 action/output schemas。

默认未知语义依赖仍使 APP 全图重验，改变定义的集合只取声明下游，不能借保守重验改写无关节点。PROJECT/SEMANTIC/MODEL_CANDIDATE 不确定依赖超出此检查器能力时 fail closed，不过滤相关应用声称完整。手工锁由既有服务端内部 set_lock 维护，本增量不新增公共锁/权限编辑入口。

缓存、读历史、确认检查都先重验当前权限/来源/版本/锁。检查历史重新运行有界只读汇总并与保存证据逐字段比较；不会新增账本/业务记录。锁循环后旧草案只显示 INVALIDATED 元信息，旧原键执行仍拒绝，允许新基线的新草案显示。异常/被拒请求事务零追加；原应用、资源、旧预览、内部版本、实例和结果不覆盖。

页面复用原 deliveryContext/generation/epoch、候选 pin 和原键恢复，不自动重发写操作。补丁、图节点、指纹及保持证明在接受回执前复核，并回读持久历史。明确 DRAFT_PATCH/NOT_RUN → CHECKED_CANDIDATE/有限检查 PASS；semantic UNKNOWN、owner PENDING、publishable/formal_publication_enabled=false、0 模型、0 业务写入始终保留。

验证范围：新固定答案/API/冷 Store/全业务表保持、严格 schema 负例、撤权/来源/锁/旧版本/同键异参/协调重签结果、PROJECT 不确定依赖、并发；新实际 loopback HTTP/product JS 20 项及原 CSV/Report 29+29 项。原 JSDOM 驱动异步关闭失败另保存，最小复用已有 application_use.cjs 请求/事件 drain 助手，原 29 个断言/等待上限/90 秒 Python timeout 保留，定时刷新在此导航测试中关闭，不冒认后台轮询实测。

Windows 900 秒、Edge 240 秒、Node 150 秒的原 workflow/脚本/保护不改，不触发新 CI。LIVE=0；自有临时 SQLite/schema 与 `--network none` PostgreSQL 容器/本地 Unix socket 测试，结束核清理。正式发布、真实任务 gold、开放语义、完整 P-B、人工签收和原生 Win11/Edge 验收不属于本病例通过范围。独立答案与只读审计由本任务完成；没有第二人员/独立 agent 审查，不把同作者复核冒认独立审查人签收。

本工程病例每应用最多保存 50 个列绑定定义和 50 个检查回执；超出时新请求在接受前明确拒绝，历史不删除，原键恢复仍可用。这个容量约束防止已接受回执被历史窗口静默遗漏。
