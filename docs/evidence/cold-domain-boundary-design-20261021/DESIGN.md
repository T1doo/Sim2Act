# G0 新鲜性边界最小设计：领域快照与当前授权分离

状态：**设计供独审，未实施，不是减少现有防线或拆事务的授权**。基线 `c20b8b6baf2c023b5dc7c89f7e8282bad112f350`。本轮无 Mock/真实模型/G0/W5、旧实例恢复、运行代码/租约/权限变更。本设计取代“任何优化都必须保持任意进程内猴补丁的逐调用行为”这一过宽前提；此前提案、失败和审查原件保持历史原样。

## 1. 规范来源与应保留的契约

已按 `docs/sources/V5/manifest.json` 重核原产品及阶段计划完整 hash，见 SOURCE-HASHES.json。规范来源是 V5 产品约束和阶段验收，当前 helper 的实现不是额外产品规范。

| 必须保留的性质 | V5 来源 | 本设计的处理 |
| --- | --- | --- |
| 用户、发布能力、App 身份、资源授权交集；每次敏感读/工具/副作用前重查撤权 | 产品 §5.5、§8.4 | 快照/摘要不提供授权；原动作/读取/提交网关继续读取当前权限 |
| owner、fence、Run 状态/取消、有效租约；旧 worker 不得提交 | §8.1—8.3 | 动态事实在实际动作/提交处重新读锁；过期/竞争拒绝，不以快照 owner 作准入 |
| 本地业务变更与回执同事务，未知结果不盲发 | §8.3 | 原 W5、postwrite live/tail/settle 与原子回滚保留 |
| 审批绑定精确请求、Release、资源、数据前置版本、身份、有效期和授权修订 | §8.4 | 持久业务指纹和签名算法不因局部快照变更而替换；变更必须重新预检 |
| 规范化定义、相关上游 revision、工具/Schema/提示/验收版本；实际读集含集合增删与未知依赖 | §9.1—9.3 | 领域指纹及完整读取/集合见证，不用仅 Run CAS 或已读 ID 清单代替 |
| 固定 Release，继续检查动态权限；模型不能注册或执行任意代码 | §10.1—10.2 | 运行期间使用已审可信代码/注册工具；不把任意进程代码替换当作本机制可防御的攻击者能力 |

V5 未规定每个 helper 全图 pickle、Python 对象身份/别名作为业务版本，或任意模块 monkeypatch 的相同异常对象/精确错误顺序。有权替换 `tuple` 的任意进程代码同样能替换 `require/check`；逐 pin 哈希不能建立这个安全边界。因此前一 tuple 方案的严格实现等价否决不应升格为产品架构的普遍否决。它本身没有充分价值证据，本设计不重新实施或跑微基准。

**可信代码造成的意外 mutation 仍在范围内**。不能因它通过 monkeypatch 注入，就删除其保护目标。仍须保证最终使用的值就是经过验证/授权的快照，且当前 DB/Grant/版本/期限变化不能被旧值覆盖。保留公开拒绝类别、安全终态、原接收/未知用量和无未授权副作用；不承诺跨实现保持所有私有 helper 的抛错先后。

## 2. 当前代码事实及最小范围

`advance_model` 在 renew 后进入 `Store.tx()`，SQLite 为 `BEGIN IMMEDIATE`；`_cold_model_before` 内有两次原 commit 语义门，关闭图后再读 stop/时钟，随后才 W5。现 `_ColdGraphRead.check` 每次重做 typed contract、全图 codec 和 SHA；五阶段 codec 累计 5697 次、16.319125064 线程 CPU 秒，返回累计 4,408,544,578 字节。这里定位了重复全图工作，未分解全部内部成本，不承诺新设计的秒数或 30 秒通过。

特殊图选择 `_cold_model_eligible` 明确要求 `store.test_only && store.sqlite`。本设计首先仅覆盖这条隔离工程路径的 **G0 prewrite 读区间**；PG/普通 Cold fallback、postwrite 验证、apps origin 都不能自动认作已迁移。它不是已验真实生产方案。

`_cold_graph_inputs` 还被 `apps._ColdGraphOrigin` 使用；`_ModelSettlementRead` 又消费 post graph 的 `(raw,key)`。禁止全局替换 codec。新局部协议必须有明确 domain/version，并列清旧新 consumer 桥；未迁移的 origin/post 路径保持旧类型和验证。未查清传播到持久 audit/software anchors 的字段前，不声称局部 key 变化完全兼容。

## 3. 首选最小设计：同事务的拥有事实，不先拆锁

先证明一个封闭 prewrite 区间，仍在原连接/事务中运行。不是将 `input_key()` 改为返回旧摘要，也不是在旧可变 graph 上设一个“已验证”布尔值。

1. **实际读取入口仍走原 gate。** 例如 `lock_live/Store.guard`、`_approved/_current`、`authorized_read`、来源/归档解析及账链 producer，仍完成原身份、当前权限、版本、内容哈希和完整业务关系校验。输出尚未进入可信事实包以前，保留原可变参数的检查；来源不明 DTO、调用者自报 digest 或旧包不能充当 producer 结果。
2. **所有权移交。** 在受控入口把已核的业务数据深复制成私有、递归不可变的领域值，再交给纯消费者。只允许受约束的原生标量/immutable bytes、定长 record/tuple；拒绝未知对象、非有限数、循环、重复键、超深/超限输入，不运行 foreign reducer、动态属性或用户 serializer。frozen Pydantic、frozen dataclass 的嵌套 dict、MappingProxyType 活视图均不足以证明不可变。
3. **彻底断开可变别名。** 事实包不保存 RowMapping、Pydantic、原 dict/list、元数据 view 或生产者闭包引用。纯 helper 必须只消费包内领域值，不能再回读旧 typed model/row/cohort。若有一个消费者仍依赖原对象，这一根仍属于可变 frontier，继续执行原完整检查，不能计作已迁移或跳过它。
4. **完整初始投影。** 第一片对现有受控 row-storage payload 保留全部 `_data` 位置、安全索引/keys 信息及所有业务字段；不以“不是可见列”直接丢弃隐藏数据。这是本片保守迁移选择，不是 V5 对 driver 布局的普遍硬要求。它只允许完整的受控递归值投影，不允许 foreign metadata 对象进入包，不保留 live RowMapping 或可变别名。后续只有在读路径审查证明消费者不可达且不参与任何定义/证明/版本后，才可单独审减。领域规范不把 Python alias 身份当作权限；若某消费者仍依赖 `is`/可变别名联动，先保留其旧检查或重写该消费者并提供行为证明。
5. **一次内容验证与指纹。** 新事实在入口校验完整值、已存指纹及 source 关系，再产生规范化定义/版本描述和 SHA；已拥有不可变内容的摘要可复用，但不是权限、动态状态或可变验证结果缓存。业务定义指纹沿用既有 `db.fingerprint`/已签范围；局部包完整性采用新私有 domain/version，包含 schema/字段类型、来源 ID/revision/内容、相关上游和工具/提示/检查版本。bytes 保留原件与原 SHA/长度，不能把缺失用量规范化为零。
6. **纯区间内轻检查。** 纯 helper 只读已拥有值；小型 scope 检查仍绑定活跃段、连接/事务、owner/worker、必要 Settings/binding 当前小型前沿、source token/write epoch/driver changes。它不重新遍历大包，也不供跨事务授权。事实包 manifest 的摘要在明确边界和最终关闭处完成；按稳定 fact ID/声明的有序依赖编码，不按内存地址生成业务指纹。
7. **一切非纯边界结束该段。** SQL 写、事务切换、任何可能持有/改变参数的可信 callback 或实际工具/IO 都不属于纯区间。返回后先重查受影响的动态前沿/当前授权，重新取得必要事实，再进入新段；影响范围未证明时沿原网关保守重查完整范围，不能乐观只选一个小子集。已密封值不会被回调改变，但不能把旧授权延用到新敏感读取或动作。未证明纯的 helper 默认按非纯处理，不能仅因无显式网络而认作纯。
8. **原提交门不删。** 保留 first/second 完整业务准入语义、原 finite 向量和最终 scope 关闭后的新鲜 stop/时钟检查；W5 不前移、不拆组。W5 后真实 owner/授权/账链/live/tail/期限复核继续原路径；任何失败回滚。原 response/usage 单独接收事务和拒绝保留也不改。

为何可比重复 pickle 更省：目前约为 `Σ每次pin的全部图大小`，新设计目标是入口各事实的完整复制/校验/规范化一次，加上边界的动态前沿及必要 manifest 检查；重复访问真正不可变事实无需重新序列化所有旧 payload。**前提是所有权与消费者闭合证明成立**，并非预测已测得收益。同事务设计仍持 SQLite 写锁，不能声称已经解决 heartbeat 写入阻塞。

## 4. 精确的新鲜性边界

| 边界 | 内容事实 | 必须当场重新检查的动态事实 |
| --- | --- | --- |
| 敏感数据实际读取前 | 读取当前数据并核内容/版本，取得该次快照 | 用户/项目/App/资源权限交集、撤回修订、相应 Release/身份 |
| 进入已审纯 helper | 只可使用已授权取得的密封值，不能重新取得外部可变引用；内部字段访问不是一次新的外部敏感资源读取 | 同 scope/事务/写 epoch/当前必要进程设置；不是新权限凭证 |
| 可信 callback 返回/新增事实 | 返回的可变结果未自动可信；重新核来源关系并拥有化 | callback 可能触及的 DB/Grant/状态/设置/owner；受影响下一消费者前完成 |
| 两次准入与 W5 前 | 本次定义/输入和完整来源/账链/原始回执关系仍成立 | 当前 Run/version/fence/worker/status/cancel/stop、审批/撤权、全部原 finite/lease 和当前授权 |
| W5 后至 commit | 新写的真实 Attempt/Operation/回执与预期 delta 一致 | 原 postwrite full live/tail、当前 owner/授权/未知结果/停止/期限；失败整体回滚 |
| 对用户展示/再次读取历史结果 | 历史内容/来源保持原版本 | 当前访问权；历史成功或旧包不授当前访问 |

意外 mutation 的预期明确变化：原可变生产者 buffer 在移交后被修改，而消费者确实只读已拥有值时，该修改不改变已取快照；不能仅因 alias 断开就认作授权失败。若消费者实际使用了被改的值，或 DB/Grant/版本/来源发生变化，必须在其消费/提交前拒绝或重新获取；这是新的值所有权契约，须由回归证明，不是放弃 mutation 防御。

## 5. 后续短读—锁外纯算—短写方案：当前不实施

在同事务所有权/值语义闭合后，才讨论释放长写锁。此时旧 CGR/token/connection epoch 不得跨事务继续使用。

- T0：短一致性读事务，当前授权后读取完整领域快照；登记每个单行字段、关联、存在/不存在、排序、聚合及列表谓词（含过滤、权限范围、上限/截断标志）。只保存已读 ID 会漏新增/删除与空集变化，未知依赖扩到实际资源集合/项目范围。
- 锁外：仅对拥有的不可变输入执行可信纯计算，无外部动作/新数据读取，不产生授权；不扩大原 Run/node/source/lease 期限。
- T1：新短写事务先锁同 owner/version/fence，再按原权限网关授权，重取完整读集/集合投影，与 T0 的规范化定义、上游版本及结果精确比较后才允许原提交组。最低正确版本可逐谓词重查完整投影；目前没有覆盖全部写路径的 revision witness，不能直接用本地 epoch、单 Run CAS 或保存的 digest 替代。若将来用版本/集合 epoch，所有更新/插入/删除/修复/后台及直接 SQL 路径都须有原子不可绕过的维护机制；未证明就不采用。
- 检查与业务写必须同一写事务；提交前读集比较后不能穿过可变 callback。postwrite 审计使用预期写 delta 和当前真实行，不能拿 T0 的 Attempt 状态与有意 VERIFIED 的行直接作“相等”判断。
- 保留本次操作在原续租后捕获的非延长 lease cap，加上所有原 Run/node/source finite；提交取当前有效 owner lease 与原 cap 的更严格界限。正常 heartbeat 不能让本设计通过放大 G0 时间来过门；过期不可复活。跨事务 cap 的确切捕获点需同现有 RunCheck 比对后独审，不能静默沿用旧 token 或改用更晚 lease。

SQLite T1 的 BEGIN IMMEDIATE 提供单写者排除；PG 的隔离/行锁、谓词/phantom 以及写入竞争须独立设计并实际回归，本方案没有 PG 实测结论。这是后续架构扩展，**同事务第一片不依赖此 CAS 方案获得批准**。

## 6. 迁移接口与实质测试

第一片必须列出 `_ColdGraphRead`/`_ColdBindingGraph`/`_ColdTrialGraph`、`_graph_trial_*` producer/consumer 的 owned 与 mutable frontier 清单及每个原 pin 的替代保护理由；不能只修改 check()，留原 helper 继续使用可变参数。以明确的局部版本选路，旧模式保留，拒绝跨版本 proof/包混用，不允许调用者以标志自选更弱路径。post_graph `(raw,key)` 与 apps origin 在未完成 consumer 映射之前继续现有协议/旧模式（当前 header 为 `SIM2ACT_COLD_GRAPH_PICKLE_V2\0`、受控 row payload 为 row-storage-v2），禁止把新摘要塞入旧 raw/hash 合同。需追踪 software/audit anchor，确认内部版本不导致旧批准被误认，若影响持久签名则另列明确兼容/重新批准迁移，不改历史。

| 现有测试保护目标/例子 | 新架构仍须证明 | 可变更的实现断言 |
| --- | --- | --- |
| `test_trial_approval_sql_drift_stops_before_any_paired_payload`、release drift 测试 | 当前撤权/Release 变化在正文读取前拒绝、零越权读/写 | 不要求相同私有 pin 次数 |
| `test_actual_capture_callback_checks_every_accounted_aid_before_digest_consumption` | 每个 aid 的 wire/usage/slot/capture 关系完整，改变实际被消费事实不能漏验 | 已移交的旧 mutable buffer 修改可以被隔离，不能让仍读 raw 的消费者通过 |
| typed cohort 的 bool/int/float、未知字段/对象测试 | 严格 schema/类型及所有字段、未知对象无用户代码回调；不接受伪造 DTO | 不要求保留 Pydantic 实例或 Python alias 身份作为领域定义 |
| 原 row-storage hidden data/unknown reducer 用例 | 初片全部隐藏数据保留校验；forged foreign key/对象不能执行 | 只有证明不可达后才可另审去除 driver 布局字段，不自动删用例 |
| `test_cold_model_before_rechecks_clock_after_owned_graph_close_before_w5` | 关闭/最终规范化耗时也计入原期限，过期时 W5 零进入 | 不绑定同一检查函数对象/逐行调用序列 |
| policy owner/version/fence/cancel/lease、revocation/unknown 用例 | 当前状态、撤权、既有占额/未知 usage、无额外请求 | 不要求任意 module monkeypatch 抛同一异常对象 |
| 本地写组故障/原 postwrite 实测用例 | 中途异常全事务回滚，收到的原 response/usage 不丢，提交后真实回读对应 | 不用旧快照充当写后证据 |
| 集合依赖/新文件/新增删除/空集变更 | 实际读集和范围变化使审批/计算结果失效 | 不用仅已有行 ID 列表判定“没变” |

这些是设计验收要求，不是本轮已运行结果。旧模式测试继续保留；新模式测试按安全性质提供反例与正例，不按是否 monkeypatch 粗暴分类。局部协议 bytes 可不同，但业务规范化定义、真实源/回执 SHA、授权决策、拒绝类别、安全状态及无副作用须比较；任意 helper 导入错误顺序/对象 identity 不是默认的产品等价判据。先做必要的拥有化/消费者纯性/边界离线回归，未经新的明确批准不运行 Mock/G0/W5。

## 7. 独审前未闭合事项及风险

此处请求的是架构方向审查，不是代码实施 ACK。尚须补完：逐 producer/consumer 字段与回调边界清单；不可变表示和无可变逃逸证明；同事务动态状态/最终授权的覆盖；局部指纹与已有 software/audit/post_graph 合同的兼容分类。跨事务还另缺完整 read-set/writer/predicate 覆盖，第一片不得以此代替当下的事务原子性。

主要迁移风险是遗漏隐藏字段/未见集合、某 helper 偷读旧模型、将内容摘要误当权限、回调后未重查、未知用量被规范化、旧签名/跨版本 proof 错配，以及关闭阶段超期却进入 W5。每项均要绑定相应故障断言后再改运行路径。旧完整对象图没有保留并不禁止设计领域快照；可以从正式 schema 与获准离线事实构造针对性安全用例，但不能据此宣称当前完整 G0 性能通过。

## 8. 原方案独立产品断点的当前核验

旧 FirstMaterialRevision20261018 文档所说的 App 追加 CSV 材料授权页，在当前基线已有实现：`csv_material_access.py`、`api.py:27/1037` 挂载和 `web/csv-goal-revision.js:315—423` 明确 READ/SUM、App/材料、全部实例范围、最长 24 小时及独立确认；来源提交 `a1649ed443280ad16da45a0a55a0f8086889d8fd`，当前说明 `docs/csv-app-material-access.md`。因此不能再制造同一开发任务或替用户授予权限。本轮只是只读源码核验，未重跑该片验收或提升其原 PG/Windows/native/真实场景状态。
