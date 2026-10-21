# Native 第二代码复审（仍待最终收口）

结论：**P1_CLOSED_TWO_LOCAL_P2_PENDING**。本轮只读，产品导入/测试/DB/Worker/Mock/G0/PB/prepare/commit 执行均 0，仓库写入 0。预算平方票和所有 allocation 数字不属本审批准范围；本报告不构成运行资格。

已静态确认前轮关闭项：

- CGR 在调用 frontier 前校验 exact _Frontier 且 frontier.graph is self；Frontier.check 再校 mode/candidate/graph/frontier 双向锚。mode._dynamic 校 exact _NativeCandidate、candidate.mode is self、graph 同一；constructor 先 exact CGR 才访问属性。跨 graph P1 和未知 native 开关屏障关闭。
- cached Source canonical 先经过 `_source_parts` 的 exact Source role、aid、唯一 actual/read/chain 归属。上一轮绕过 Source 归属的 P2 关闭。
- `_archive_native` 先 `_native_domain` 遍历整个 receipt/request/response 含 unused 值，拒 foreign 键/值、cycle、nonfinite；再 exact 容器/字节成员和固定字段屏障，后才 eq/index/hash。原 P2 的具体 foreign callback 反例已关闭。新测试源码覆盖这些反例；本审未执行它们。
- `_native_equal` strong done 持原对象防 id 复用，active 用原模型/row/container identity，RowMapping 只受控流式索引扫描，不建立 broad lookup/visible dict。
- upstream 全 Run 比较已在发行前 qualify 中；_prepare 原 Source→recipe→backend version→Generate 位置及原 field/id 检查未移，无第二 producer。默认 candidate=None 不选择新路径。
- owned_ready 初值 False，原 oracle 在复制与 arena 纯值初始化期间仍完整检查；安装 frontier 前 `_assert_raw_before_owned` 最后 typed/fullguard，再 discard+owned_ready=True，防复制后原 typed 事实变化漏检。
- 正常 native helper 退出不提前关闭 arena，而保留到原 graph context 的末尾 check，随后 graph.invalidate 递归保护地关闭 mode/arena；异常立即 close。独立 graph/SQL/事务/期限动态项与 remaining frontier 仍 fresh。

待关闭 P2-A：`_Arena.node` 已验证 exact Packet/int/ref 正负，但先 `len(packet.nodes)`、后检查 packet 属于 arena，且没有 exact tuple 检查。exact `_Packet(nodes=ForeignLen())` 可先触发外部 __len__；原 _Node 构造器先检查 type(nodes) is tuple。父侧已确认待当前测试结束后加该最小门，尚未把承诺算已修。

待关闭 P2-B：‘immutable arena’ 的发行后 tables 仍是可变 dict/set。`_Node.scalar/items/sequence` 直接读取 scalars/items/sequences，relations/canonicals/usage 也直接决定纯比较/结果；frontier 只钉 immutable packet digest，未钉这些表。对 `arena.scalars[(id(packet),ref)]` 的修改可以改变 Record 观察值而 packet/frontier 不变。建议发行前封为只读 MappingProxy/tuple/frozenset 且 build backing 不再暴露，并将 ledger._native_arena 锚为该候选原 arena；或 scalar 直接从原 immutable packet 读。无需重扫 cache，更不要求新增平台机制。若不修则必须撤回‘纯不可变 arena’并提出等价安全边界，不能以 cache 命名代替冻结。

本次为第二轮静态中间报告；初稿保留，最终修复须另附精确哈希终审。没有把父侧正在运行的测试当已通过。
