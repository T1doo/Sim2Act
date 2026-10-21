# Codec 源码层分析：一个操作级候选被严格回调语义否决

基线 `ec9cf8f936427e64f0a07e2fc30f498076f05376`，生产执行代码仍与第三窗口 `cdda2b2ed6bce1393b90a500c0377294e4d82e34` 相同。本轮继续原性能问题的离线分析，仅增加本证据目录，没有新窗口、Mock/真实模型、producer、库恢复、profile、微基准或 pytest，也没有新观察器及生产优化。

## 具体提案及否决

[DESIGN.md](DESIGN.md)包含唯一考察的新操作级差异：把 `_cold_graph_limit_values` 返回处的生成器构造展开为六个固定有序字段对，原前置校验和六次新鲜字典读取保持。它试图减少生成器分配/恢复，不是缓存、删验证或类型分派；示意 diff **没有应用**。

独审发现严格语义反例：原实现会动态解析并调用 `tuple`，字面量展开会移除该调用。同一次编码中，RowMapping 首行 payload 完成后，marker 的原全局导入回调可以修改模块的 `tuple` binding；随后原 Limits 返回处可抛指定异常，展开版本则绕过该调用。原源码已有测试覆盖这条导入回调边界。本次新 tuple 反例来自静态源码推导，**没有运行或冒称实际复现**。正常 globals 下字段读取相同，不足以证明所有原回调/异常语义相同。

决定：**NO_GO_IMPLEMENTATION / NO_NEW_BENCHMARK**。不通过冻结 builtin/global binding、删原调用或缩小回调保证来让候选过审。没有必要为已存在语义反例的候选堆差分/性能测试。

## 为什么真实成本仍不足以选择另一个安全优化

第三窗口真实五阶段 codec 为 5697 次、16.319125064 线程 CPU 秒、4,408,544,578 累计返回字节；prepare+resolve 的 codec 为 13.470989389 秒，占该 codec 指标 **82.5472526%**。这些数据能定位区域，不能区分其中哪些成本可安全替换，也不是整个 G0 CPU 或可回收成本。

- 生产 C Pickler 已在一次 dump 内使用 native memo，并在 dump 入口缓存 reducer_override 方法。再加同次对象 memo 或缓存方法查找没有对应的已证重复工作；跨次 memo/bytes/行元数据复用则减少必须保留的新鲜读取。[CPython v3.12.14 实现](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c)
- C Pickler 分帧提交、原生遍历/memo、RowMapping/Limits reducer、sink 写入和 resize 仍合在 codec 时间中。`BytesIO.getvalue` 可返回现有内部 bytes，不能假设每次都有一份可删除的全量复制；不重做已无实质信号的前缀分配方向。[同版本 BytesIO 实现](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_io/bytesio.c)
- 旧 61,657 字节输入的 pstats 中，100 次 codec 仅有 100 次 Limits helper，其整个函数累计计时 0.000679291 秒；返回生成器只是更小子集。旧 pstats 的 100 次显式 BytesIO.write 对应 header 写入，不能用来计量 C 内部 sink 成本。这些受 profile 影响的小样数据不能外推本次 G0，且不是第三窗口 `thread_time_ns`。[Python 对 profile 与基准的区别说明](https://docs.python.org/3.12/library/profile.html)
- 旧输入小于 64KiB frame 目标；第三各阶段平均返回约 0.67–0.96MB。平均值不是每次大小/递归结构分布，不能反推原生分帧次数或 reducer 工作量。相近字节量可以来自大原生 payload，也可以来自许多小容器/行和不同共享拓扑，不能按字节量换算安全可删的 Python 工作。

当前缺失的性能/代表性输入是**当时完整编码输入的内存对象图**：各阶段不断增长的 inputs、真实 typed contract/role Limits、RowMapping 全部隐藏数据/安全索引/共享元数据，以及跨字段别名。第三观测器只保留聚合和根长度；库/交换 JSON 不能还原这些运行时身份和结构。旧 fingerprint-only 二进制不得加载，61KB 小样不具代表性。对此不默认开第四窗口、不恢复旧实例、不造替身或通用观察器。

尚缺的因果观察具体是：在可用的代表性完整输入上，各类 reducer 的实际次数/隐藏规模/别名分布，以及 codec 内原生遍历/分帧写入与 reducer 的成本区别。首先仍须找到不移除原调用或新鲜读取的明确操作替代；完整输入和收益不能弥补本候选已有的语义反例。约 0.956 秒越界并不证明一个总耗时较大的区域中已有同等可安全回收成本，也不提供无仪器性能验收。

## 本轮实际检查

[CODE-FACTS.json](CODE-FACTS.json)记录标准库 AST/内置 Pickler 身份检查及四份源码 hash：原 Limits 前置表达式没有 tuple 引用，原 tail 确为动态 tuple(genexpr) 调用；未导入或执行产品。该静态检查不是新增产品测试。

[OBSERVATIONS.json](OBSERVATIONS.json)仅重新计算已封存第三阶段指标、读取既有 pstats 条目，未新跑剖析；[SOURCES.json](SOURCES.json)记录实际读取的官方 v3.12.14 源码 URL、大小和 SHA，原文件留在 `/tmp/sim2act-codec-causal-source-20261021/`。独审原件按字节保留在 REVIEW；哈希、范围与本轮检查见 CHECKS/MANIFEST。历史失败、第三窗口原件、运行代码和所有预算未改。完整 PB/G0 期限问题仍未解决。
