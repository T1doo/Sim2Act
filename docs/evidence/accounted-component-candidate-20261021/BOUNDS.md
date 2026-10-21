# 本片的限额合同与安装阻断

私有值组件要求显式 `_Bounds(nodes, edges, depth, leaf_bytes, encoded_bytes)`，均为 exact 正整数，没有生产默认值。候选只是按调用者提供的边界 fail closed；不是原生内存 hard quota，也不改变 Run/RPM/租约、TTL、归档或磁盘预算。旧 scope、producer、全图检查和全部更严格期限继续执行。

可从现存源码确认的局部边界：

| 内容 | 已有约束 | 尚不能由此推出的内容 |
| --- | --- | --- |
| accounted 根 | Generate 3 个实际 Attempts/chain，Source 2 个，每 chain 六项；NS reads Generate 0、Source 2，每项五项 | 不是整行 JSON 所有节点、边和字节的总上界 |
| typed 记录 | Slot/Identity/Outcome/Capture/BodyArchive 固定全字段及受控类型；模型字段清单由 test 与实际 schema 全量对比 | 部分字段仅有类型/下限，不能把字段数当作字符串或整数总字节上界 |
| 交换证据 | 原 ReservationIdentity.wire_bytes ≤ 32768、Capture.raw_bytes ≤ 131072、body_b64 ≤ 43692；原 body 完整读取必须满足 MAX_BODY_BYTES=32768 | 这些约束有不同语义，不能将 raw/decoded/canonical 长度混同；producer及完整字节证明仍保留 |
| parsed | 原 strict_json 限输入字节并拒深度 >20、重复键、非有限数；保留其完整额外字段 | Run/Attempt 的其他 JSON 不全来自同一次 strict_json |
| 完整 SQL 行 | 当前 Run 18 列、Attempt 13 列；复制全部嵌套值及 native row 的 keys/data/safe-index，包括隐藏位置 | DB `JSON`/`String` 列本身没有统一总大小约束；尚未穷尽每个字段可达写入路径及所有 native metadata extent |

最后一行是当前精确技术缺口：尚不能从已审源码证明整个接受域的一个统一有限 aggregate cap。**没有据此断言所有实际产品输入可无限增长**；需要将 producer 可达字段与实际写路径/上游 schema 一一映射，或审查一项必要的新接受合同。不能自行选一个较大的数字当兼容证明，也不能把本片 proof limits 升为产品额度。

因此本片允许显式测试限额下的组件资格检查，仍禁止安装到 pre 替代路径。后续若发生预算拒绝，旧运行路径继续保留所有原安全检查；不能自动降级跳过拥有化或原 pin。所有五条 chain、每 aid 完整行、固定模型、额外 parsed 字段和 hidden storage 都必须进入预算推导，不可为了配合数字删掉输入。新私有 digest 也不能替代规范化业务指纹/原签名。

编码采用平坦节点引用，单次 completed memo 复用已完成不可变节点、active 拒循环、共享路径仍检查最长深度；包括实际字符串/字节负载和最终编码的成本。它避免朴素 DAG 逐边展开，却不证明固定 CPU 期限、原生内存配额、G0 收益或能在原 30 秒内完成。当前仍在原事务，不声称解决 heartbeat 写锁问题。
