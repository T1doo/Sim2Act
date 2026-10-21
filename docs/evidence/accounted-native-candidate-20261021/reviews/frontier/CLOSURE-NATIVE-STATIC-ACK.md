# Native 最后小修：六文件冻结静态 ACK

结论：**CLOSURE_STATIC_NATIVE_SOURCE_ACK_DEFAULT_OFF_ONLY**。六文件当前 SHA 全部与 `/tmp/sim2act-native-candidate-20261021/closure-hashes.json` 匹配；来源/默认路径/安全与生命周期范围没有未闭 P1/P2。旧 FINAL-NATIVE-STATIC-ACK 保留为 earlier review，不冒充已审新 SHA。本 ACK 不覆盖 monitor 数值上界，不签正在进行的回归，不批准生产资格/性能/启用或任何执行窗口。

已核最后增量：

- 发行前在同一次完整 `_SizingProjection` 的受控副本上取 `cold-trial:bound.binding/source_binding`。snapshot.release_id 与完整 copied release.id 先 exact str/值一致；user 来自原 graph.binding.contract.principal_id。最多两条去重 `release-pointer:<user>:<rid>` 精确 key，加入12固定root的 frozenset scope allowlist。resident/work 先预费字符串构造及中间重叠；无额外 RowMapping helper复制、无提前 SQL、无任意前缀白名单。
- `_Frontier.added` 只接受该同scope future_roots 中未出现的精确名；所有 lazy Release root 值仍走原 lifecycle.owned_release_pointer、项目授权/immutable_release_pointer 与 fresh codec。只补已证明绑定的原懒读根名，未增加可读 Release 权限。
- receipt/proof 先 exact dict 与 len18/7，再遍历 key/字段类型；保留固定 producer 输出域、不加字符串 cap。未知/额外字段仍拒绝，不被截断丢弃。
- sizing/copied/header/bound/release 临时引用在 ticket.close 前置 None；state/raw/expected snapshot 局部在 context 结束前 del。未添加业务读取/guard/SQL或改变 producer 原位置。原不可变 arena/seal、owned_ready 前最后原 typed+raw guard、scope 关闭顺序等前轮已审收口保持。
- 测试 fixture 仅把已有真实合成绑定原 raw 事实提前放入 bound 根，与实际 native prepare 的既有事实形状对应；不执行 binding/full prepare/commit。no-runtime-callers 只为私有 `_cold_accounted_native.py` 加 import 例外，其余禁止不删；新增独立 signature 检查 `_accounted_candidate` 默认 None。
- `_cold_accounted_values.py`、natural_spec_runtime.py SHA 与前轮终审相同，因此本小修不改原 codec/CGR/default-runtime路径；默认仍无配置/API激活，候选仍 test-only SQLite/pre。

前一轮333 pass/3 fail 的原件应保留；本报告没有把它写成通过，也未核本轮最终测试原件。所有 reviewer 产品导入/测试/DB/Worker/Mock/PB/G0/prepare/commit 执行为0，仓库写入0；仅/tmp报告。
