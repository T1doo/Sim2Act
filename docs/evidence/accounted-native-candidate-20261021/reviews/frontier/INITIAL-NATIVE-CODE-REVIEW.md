# Native 初稿：真实来源/接线第一代码独审

结论：**BLOCKED_PENDING_SOURCE_BOUNDARY_FIXES**。尚不能给候选代码 ACK。此为初稿静态审，后续修复须另存终审，不能用最终哈希冒充本报告已审字节。独审只读源码/差异，不执行产品导入、测试、数据库、Worker、Mock、G0/PB、prepare 或 commit；未写仓库。

## 已确认的正向接线

- `_ColdTrialGraph` 新 `_accounted_candidate=None` 为显式私有入口，默认路径不创建候选。原 Source 完成、完整字段等值检查后才 stage；原 recipe 与 backend versions SQL/检查仍在中间；Generate 完成原 field/id 检查后才 stage/choose。候选 stage/choose 没有第二 producer。
- frontier 只按两个完整 accounted 顶层路径与 complete.source/generated/generation.run 三个嵌套路径替换；其余独立 Generation/Source/audit/job 根仍 fresh codec。新的 frontier 前缀与默认原 input_bytes 相隔；默认无候选时原 bytes 分支保留。
- arena 预建 owned packet 访问器，native canonical 来自 owned 纯值；旧 mode 默认仍 `_native=None`，其旧 oracle 分支保留。新增 native consumer 没有开启真实执行；根侧新测试为离线合成 consumer 与对象壳，不是完整 prepare/commit 证明。

## 阻断发现

**P1：跨 graph frontier 可替换。** `_ColdGraphRead.check` 在 `_accounted_frontier` 非 None 时直接调用该对象 `.check()`，没有验证 exact _Frontier、frontier.graph is self、mode.graph is self 以及 candidate/mode/frontier 双向锚定。把 g2._accounted_frontier 换成仍 active 的 g1.frontier 后，动态项检查 g2，但被扫描的输入属于 g1；g2 的剩余 mutable 根变化可以不被此次 check 检测。同样也会调用 foreign frontier 的任意 check 回调。修复必须同时绑定 exact 类型和同一原 scope/graph 来源，不能只检查类型。

**P2：native archive 失去完整受控值屏障。** `_archive_native` 仅检查 receipt/proof 为 dict 和 attempts 为 list，随即对 verification/source_run_id/aid 等可能为 foreign 的值做 eq/hash，并直接对 request_bodies/response_bodies 索引与 eq。原路径先 `_freeze` 完整 receipt/request/response 才业务比较；原调用者 typed guards 不保护 ResolvedSourceArchive 的这些原生字段。exact dataclass 可带 foreign __getitem__ 容器、foreign __eq__ 成员或 unused foreign/cycle/nonfinite 子树。native 当前会触发回调或遗漏原拒绝。须在任何实际 eq/hash/index 前完整覆盖原 controlled representation 与 extent，不仅补两条 tuple 类型。

**P2：canonical 缓存命中跳过 Source role/aid join。** `_source_exchange` arena 命中时只 `family._root()`，共享 arena 中 Source aid 会令 `_source_exchange(selected.generated, source_aid)` 返回 Source canonical。原 `_source_parts` 必要求 role=='source' 并完整检查该 aid 的 actual/read/chain 唯一归属。缓存纯值前仍须执行这些原 joins。

**P2：arena.node 绕过原 Node ref 边界。** `_node_ref` 见 arena 即调 `arena.node(packet, ref)`；后者在 exact Packet/int/range/arena 登记验证前 `nodes[ref]`，故负数、bool、foreign __index__ 的行为不同于原 _Node 构造器（先拒）。须先验证 exact packet、exact int、0<=ref<len(packet.nodes)、登记的是同一 packet，再访问。

**与 P1 同组的新 native 来源屏障。** mode 仅以 `_native is not None` 跳过旧 oracle，未先验证 exact _NativeCandidate 及 graph/mode 双向绑定；_NativeCandidate.__init__ 也在 exact _ColdGraphRead 验证前访问 graph.phase。未知对象不应成为跳过扫描的开关或回调入口。修复应与 frontier 来源锚定一起完成，而不改变旧 None 路径。

以上均为纯源码反例，本独审没有实际触发或重跑。预算数值/实际 peak 由 monitor 独审，本报告不扩张其结论；即便修复后，仍只可能给默认关闭组件的局部 ACK，不能批准 G0/Mock/完整 prepare/试运行。
