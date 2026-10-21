# Codec 操作级候选审查：Limits 返回 tuple 展开被否决

基线 `ec9cf8f936427e64f0a07e2fc30f498076f05376`。本轮仅离线源码/既有证据分析；不运行第四窗口、Mock、Worker、生产 producer 或旧库恢复，不改运行路径。

## 明确的候选差异

只考虑 `_cold_graph_limit_values` 最后的生成器 tuple 构造；其余完整前置 require、读取和 C Pickler/协议/memo/SHA/pin/签名/事务/期限全部保持原样。下面仅为供审差异，未应用到生产或测试，也不是已批准优化：

```diff
-    return tuple((name, raw[name]) for name in names)
+    return (
+        ("max_requests", raw["max_requests"]),
+        ("max_tools", raw["max_tools"]),
+        ("max_repairs", raw["max_repairs"]),
+        ("max_total_tokens", raw["max_total_tokens"]),
+        ("max_output_tokens", raw["max_output_tokens"]),
+        ("run_seconds", raw["run_seconds"]),
+    )
```

它试图移除每个 Limits reducer 的一次生成器对象创建、恢复和固定 names 迭代开销，不复用字段值或验证结果，不涉及类型分派或前缀分配。完整 raw/keys/extra/private 校验及六次类型检查仍在原位置；返回处六次 exact dict 下标读取仍按原字段顺序发生。每次仍新建外层 tuple 和六个字段对，字段值仍是当时读到的原对象。只把受代码控制的固定六项展开，不从新缓存取数据。

以上只是在正常未替换 globals 下的操作级论证，不是完整编码/回调等价证明。固定字段名重复也增加维护漂移风险，不能把这份示意差异直接应用。

独审指出一个更强的静态反例：原 tail 会动态解析并调用 `tuple`，字面量展开会移除该原调用。在同一次编码的 RowMapping→Limits 顺序中，首行 storage 检查完成后，保存 marker 的原 import 回调可以把 `runtime.tuple` 绑定为抛出某一异常对象的 callable；随后 Limits 的完整前置 require 没有 tuple 引用，原 tail 会调用该 binding 并抛同一异常，而展开字面量不会。现有 `test_shared_row_metadata_is_reread_after_pickle_global_import_callback` 已证明这条 import 回调边界存在；此新 tuple 反例为源码推导，未执行，不冒称新增复现测试。

因此仅保持六次字段读取顺序不足以保持所有原可观察调用、异常和回调语义，**该候选按严格要求否决**。没有通过删新鲜读取来改良它，也不通过冻结 builtin/global 绑定、扩权限或缩小原回调保证来让它过审。

## 为什么现在不实施

真实第三窗口测得 codec 合计 16.319125064 CPU 秒；prepare+resolve 占其中 82.5472526%。它没有记录每个 codec 的 Limits/RowMapping 次数、递归原生节点和别名分布，也没有 reducer 内部 CPU。因而无法把 0.955520630 秒的实际租约越界归因到本候选，更不能把 codec 总量当作生成器成本。

旧 61,657 字节离线输入在 100 次调用中只有 100 次 `_cold_graph_limit_values`，其整个函数的 cProfile 累计计时为 0.000679291 秒，返回生成器仅占其中一部分；该小样本自身不支持把此变更列为显著收益方案，也不能外推当前完整 G0 中的次数。此轮没有重跑该小样或制造新的弱替身。

**当前缺失的性能/代表性输入是：没有保存的、可离线重新构造且具代表性的完整编码输入图。** 这不是该候选唯一阻断，上面的严格回调语义反例已独立否决它。第三观测器只存各阶段聚合、根长度和返回字节计数，未保存任何阶段的完整 inputs、typed contract/role_limits 及其对象身份图。库和交换 JSON 保留业务数据，却不能恢复当时不断增长的 `g.inputs`、SQLAlchemy 隐藏 `_data`/索引/共享元数据、模型对象及跨字段别名。旧 complete-input.bin.gz 明确 fingerprint-only，绝不反序列化；旧 61KB 两模型向量也不能代替它。

缺少该输入时，即使做一组新微基准，仍不能确定 Limits return 构造在真实热点中的权重；即使找到了代表输入，收益也不能弥补已识别的回调差异。因此决定 **NO_GO_IMPLEMENTATION / NO_NEW_BENCHMARK**；保留具体否决过程，不提交产品微修，不新增通用观察器。

后续若出现另一个没有此语义反例的具体候选，并且已有获准的完整离线输入，才适用最小差分：相同生产 C Pickler/协议和 fresh memo，基线/候选有界比较完整 bytes、真实类型/隐藏行数据/别名/环/未知类型/混合错误次序/前后 mutation，并保留原调用边界。此条件不让被否决的展开候选复活，也不要求或授权再开业务窗口。

## 官方实现核查缩小的范围

与运行版本一致的 CPython v3.12.14 两份源码 URL/大小/SHA 见 SOURCES.json。`save` 先在 native memo 检查已见对象，再进入 reducer_override；`dump` 已在入口缓存 bound reducer。因而“同一次编码再加 memo”或再缓存方法查找没有对应的重复工作。原 row reducer 的每次新鲜读取仍须保留，包括第一次 marker 全局导入回调之后下一行 metadata 的重新读取。

`_Pickler_OpcodeBoundary/_Pickler_FlushToFile` 包括原生 frame 提交、内部 buffer 获取和 sink write；`BytesIO.getvalue` 在无导出/无需复制分支可返回现有 bytes，而不是无条件再次整段复制。不能根据累计编码字节直接推出一份可删除的拷贝。现有 pstats 的 100 次显式 BytesIO.write 也不单列 C 内部 sink 调用成本。

旧向量小于 64KiB frame 目标；第三各阶段平均返回约 0.67–0.96MB，平均值不是每次大小分布，也不直接给出 frame 次数。native 遍历/memo、fresh reducers 与分帧写入/resize 在本次 16.319 秒中仍未区分。保留同一 C Pickler、完整输出 bytes 和回调边界时，当前没有一个可直接替换掉原生缓冲路径的已证公共 API。

参考：

- https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c
- https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_io/bytesio.c
- https://docs.python.org/3.12/library/pickle.html#pickle.Pickler.reducer_override
