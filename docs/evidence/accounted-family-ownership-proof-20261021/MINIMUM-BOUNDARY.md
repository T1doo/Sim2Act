# 最小可实施边界与指纹兼容映射

状态：**OWNED_REPRESENTATION_COMPONENT_ONLY / NO_RUNTIME_ENABLEMENT**。本片不是设计 ACK 后直接替换 `_ColdGraphRead.check`。独立静态消费者审查全文保留于 `REVIEW/REVIEW.md`，以下将范围落实为下一片可审的具体合同。

## 字段闭包

| 输入 | 全部拥有化内容 | 原关系/动态证明仍保留 |
| --- | --- | --- |
| run | 当前 runs 全 18 列，含 context/result/error/lease/fence/version/cancel 等，不按本叶子用途裁列 | producer 完整 Run SELECT；当前 action/commit Run、owner/fence/停止/期限门 |
| actual | Generate 3、Source 2 个完整 attempts 行，每行全 13 列，保留顺序、重复边、嵌套 JSON/None/精确标量类型 | 原实际有序集合查询、marker/account/version/approval、数量及 aid/run 关联 |
| chains | 对应每 aid 的完整 Slot、Capture、parsed、独立 checked Attempt、wire、payload；不因 checked 与 actual 值相等而丢弃一个读见证 | 完整 journal owner/body pair/seal/event/policy/approval/settlement、canonical、usage 与 checked-row 关系 |
| ns_reads | Source 每 aid 的 aid、完整 request BodyArchive、wire、完整 response BodyArchive、payload；Generate 空 | NS 原有序 _read、pair/seal/anchor/provenance 与 VERIFIED Operation 查询；后续 REQUEST/RESPONSE 完整键集合当前查询 |
| native row sidecar | 原受控 keys、全部 data、safe-index；包括隐藏 data/alias，quoted_name 字符内容单独 tagged | 只用生产现有 `_cold_graph_row_storage` 的受控 metadata 检查；拒重复归一化键，不能携带 live metadata |

固定模型全部字段见 `SCHEMA-MAP.json`：Slot 5、ReservationIdentity 14、Outcome 6、Capture 11、BodyArchive 15。原型取实际 storage→固定完整 model_dump→类型精确对比，而不是用 coercing 构造器掩盖漂移。原序列和字典字段不扁平化成 aid/SHA 摘要。对大小写、类型、None/缺省、未知 usage 不做业务归一化。

## 消费者必须同时闭合

| 位置 | 最小迁移动作 | 现在的证明状态 |
| --- | --- | --- |
| dispatch `_graph_stage_accounted` 末尾 | 原全部 producer 证明成功且最终 guard 后发行 owned family；不得在首条 chain 后发行。原型 capture 仅示范复制，不具该发行能力 | 原 producer 未改，完整证明保留 |
| runtime `_prepare/_accounted_fields/_fields` 与 `_base/_typed_parameters` | `source_accounted/generate_accounted`、两个 accounted input、complete.source/generated 必须指向同一 scope 发行的不可变 family；不能还留一个 raw/typed 副本供后续读 | 已静态定位，尚未改写 |
| `cold_stage_facts/source_stage_facts` 及 gate `_graph_trial_stage_*` | tuple 中 Generate/Source 的所有出现点改为该 family 的引用；binding/frozen/extraction 等未迁移根继续旧检查 | 已静态定位，尚未改写 |
| gate `_graph_trial_accounted_models_from_raw/_models/_raw` | 发行/完整 schema 的 owned 合同代替本事实族的 mutable typed cohort；其他 cohort 原样 | 尚无 issuer 或 consumer branch，不能提前删 cohort |
| gate `_graph_stage_current` / `_graph_run_context` | owned run/actual/chains 验证全部 3/2 aid、checked membership、stage usage；当前 StageAuthority、授权指纹、phase、binding 和 Run 检查保留 | 只证明值可完整表示，尚未证明 View 等价 |
| archive `_graph_source_bodies/_graph_resolve_trial_source` | owned BodyArchive/完整行/字节关系与 Source/Generate stage tuple；当前 key-set、ledger、scope、source proof、extraction 及最终 expiry 原样 | 静态闭包；原 leaf 在离线 oracle 上部分验证，不是迁移路径验证 |
| dispatch `_graph_pb_archive_chain` | owned chain 与原完整 ledger/receipt 按 aid/run/顺序及 exact private bytes 联结；不能退化成公共 SHA 相等 | 尚未改写；journal、ledger/cursor、PB accounting 保持原路径 |

纯叶子的明确适配点是 `_stage_usage_from_facts`、`_source_row_from_facts`、`_source_exchange_from_facts` 和 archive-chain 中的 family 比较。原 helper 依赖 typed 属性和 native dict 相等；不可把 `View` 偷塞进去，也不可在运行中 `materialize_oracle`/重建可变 Pydantic 副本。需要固定 owned record accessors 或明确的纯比较函数，逐个与原性质回归。范围不含迁移全平台 rowcodec 或全局替换 pickle V2。

## 所有权和 DAG 的可证部分

在一次原型 freeze 中，先验证 exact type，再检查 active cycle，最后查 completed memo。memo 保留原 source 强引用直到该调用结束以避免 id 复用，只有节点完整写好后才发布；输出不含这些引用。复用已完成节点仍以保存的子图高度检查当前最长路径深度。所有边保留、重复边不重编码子树，平坦 node table 序列化以引用编号连接，不递归展开共享路径。字符串/bytes 负载及最终编码大小分别受显式 proof bounds 限制。

packet 的 nodes、tag、edge refs、标量、编码均递归 immutable，tests 直接遍历实际对象类型确认，不只是比较 digest。View 只持 packet 与 ref，不持 source/builder；dict/row 只接受 exact str key、sequence 只接受 exact int，未知 key 的 str/eq 不执行。原 source 的每 aid identity/outcome/Capture/parsed/checked/actual/BodyArchive 变化不会改已完成 packet，下次 capture 必重新读取并得不同内容。对 hidden row storage 的变化也如此。

这些性质**不证明同时修改内存的线程下具有原子瞬时快照**，不证明当前生产消费者已停止读原对象，也不赋予跨调用身份缓存语义。原 producer 完整 guard 与受控纯复制期间的所有权交接仍需一个原子的 scope 内注册步骤；未知可信回调边界按既有方案保守重查。当前原运行路径维持其全部检查。

proof bounds（20,000 nodes、50,000 edges、depth 128、4 MiB leaf、8 MiB encoding）仅是本离线测试的显式输入限制，**不是产品额度**。已知原边界有 Generate/Source 3/2、ledger 7 slots、wire/body 32,768 bytes、parsed depth 20 等，但完整 Run/Attempt JSON 与 sidecar 的累积界尚未推导完，不能拿这些 proof 数字直接启用运行或扩大接受域。共享 DAG 的 O(V+E+B) 表示规模不等于所有序列化器/所有整数编码的严格 CPU 复杂度，更不是 G0 提速证据。

## 指纹逐条映射

| 旧通道 | 新表示允许的变化 | 必须不变/本片实际证据 |
| --- | --- | --- |
| CGR local accounted/complete continuity | 将来可用私有新 domain/version，scope 发行完整 manifest，而非任意 caller digest；所有 occurrence 同源 | 当前未改 key；原型 digest 明确不兼容 pickle bytes。shared/duplicated equal subgraphs 可有不同私有 digest，不能据此产生业务修订 |
| Capture pair request identity | owned 完整 identity 值纯投影 | `sender._capture_request` 的 namespace/identity JSON 与 fingerprint 离线相等；原 persistent pair/seal 保留 |
| NS BodyArchive/anchor | owned 完整 BodyArchive 值纯投影 | 原 `db.fingerprint(body.model_dump())` 相等，原 `_body_payload_from_facts` 完整 SHA/base64/anchor 检查运行；pair/seal/event 仍由原路径证明 |
| wire/decoded/canonical | native bytes 直接拥有、原解析结果完整保留 | 原 wire/raw SHA/len、canonical response bytes/SHA 分别保留，不能由 node digest 代替；source receipt 七字段逐项对比 |
| StageAuthority/public receipt | 不将 node id/digest 写入持久输出 | 现有字段构造算法原样；本片不是完整 authority/receipt 集成等价证明 |
| post_graph/apps origin/software anchors | 暂不接受新 packet；prewrite 独立版本与模式必须显式 | 仍用原 pickle V2/raw/key。没有桥接代码，也没有宣称兼容已完成 |

## 下一片的最小实施条件

1. 先提交一个仅用于该 family 的 scope issuer 与固定 owned record/leaf 候选，仍不删现有 pin；其输入必须是原 producer 完整证明成功的结果。发行表绑定 graph 实例、connection/事务生命周期、role、phase、完整内容及 software/schema 标识；不能由 packet 构造器或 digest 自证权限。
2. 按上述矩阵同时迁移 family 出现点和纯消费者，查明所有原别名均只留在 producer 的局部生命周期，明确 pre/post 选择。对完整关联/集合、未知状态、混合错误类别与无副作用、可信回调 mutation 做真实纯叶子/小型离线存储回归，不靠原型成功推论。
3. 在消费者无逃逸、规模上界与 manifest/post 分隔经独审成立前，不从 `_base/check` 的可变 frontier 移除 family；其他根及原动态门一直保留。原 SQLite 事务仍持写锁，不能据此承诺 heartbeat 续租或 30 秒过门。

这三个条件均不要求开新 Mock 窗口或真实模型，也不是对拆事务、延租、减少授权门的批准。
