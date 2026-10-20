# 唯一 paired dormant 首绑定对照：无提速信号

父侧接受窄分配优化后，明确授权本次且仅本次 paired dormant `_cold_first_binding` 对照。本轮不修改产品/测试，不运行完整 PB、G0 全链、Worker 执行、模型或新的审批。已执行一次配对，每臂独立子进程、一次 producer、45 秒上限，无 timeout、无 retry；没有为结果或记录补跑。

基线 `78ed5bef2da3a175d819eb9a2f58b3bbf097f75b`，候选 `25ee757bf07155bc30a809549af6a11a449bcd44`。两臂均用候选其余源码，旧臂仅覆盖 AST 提取的原 `_cold_graph_bytes` 单函数；候选 runtime 原文与固定 Git 提交一致。旧函数见 `baseline_function.py`，实际脚本见 `paired.py`，SHA256 `3af7202a7f5c458384c2ad87ec555f5f0b5ae7ebeabb1df16db25ac719b5a498`。原始 receipt 及逐文件索引见 `receipt.json`、`MANIFEST.json`。

## 实际结果与筛选结论

| 同一计时范围：仅 dormant producer body | 原函数臂 | 候选臂 |
| --- | ---: | ---: |
| wall 秒 | 5.686491346 | 5.947760033 |
| thread CPU 秒 | 5.685367237 | 5.938843657 |
| exit / producer 次数 | 0 / 1 | 0 / 1 |
| CGR check / add / input_key | 2028 / 130 / 2158 | 2028 / 130 / 2158 |
| producer SELECT | 2814 | 2814 |
| DML / 模型 / blocked | 0 / 0 / 0 | 0 / 0 / 0 |

候选在这一次观察中 wall 多 **4.59455%**、CPU 多 **4.45840%**。固定先旧后新、每臂一次，有对称观察器开销；不能推断统计退化或提速。**没有首绑定提速信号，明确排除该前缀优化作为 G0 根本解决；停止继续堆前缀/标量等同类小修，不重复本配对，不据此建议完整 PB。** 原较大合成向量的 allocation peak 结果仍只按其原窄范围解释，不升级为首绑定收益。

本次是封存普通合成前缀的一次 dormant 首绑定，不是实际 G0 全链或真实准入。约 6 秒结果不能证明原 30 秒 lease 通过，不能与旧重观察器的 23.08 秒或完整 G0 的 37.52 秒直接比较。原完整 PB 仍 **FAIL_NOT_ACCEPTED**，W5/G1/finalguard 仍 **NOT_REACHED**。

## 完整一致性与安全范围

- 每臂源库/副本前后均为 `9a9bdfcf0264a251670a2c59dcbd401e1e035656542413e032357a442802e4db`。helper 为 `1714d223e667948a1d84a54abfdb8e35f2670c6384fc162581105da775cf6d8a`，与 Git 归因 archive 的唯一闭库/helper 成员一致；未恢复旧实例或重建 G3/Source2。
- 最终完整 pin **579257 字节逐字节一致**，SHA256 `ef45c7661d66fbe5ab1abb2842df6d8af603c71d8a1b272460e3e146e2be5d8e`。原样字节无损保存在 `complete-input.bin.gz`，只能作为 fingerprint 证据，不反序列化。
- 两臂完整有序 SQL/参数 JSONL **956105 字节、2831 条逐字节一致**，SHA256 `dc54565dcf8dee3a55f0662abb64b07cf01c70daf98a3dece119db52485e1189`：setup 1 BEGIN + 15 SELECT，scope_setup 1 BEGIN，producer 2814 SELECT。保存共用的原样 `ordered-sql.jsonl.gz`；独审已从原始行重算计数与 hash。这是本次独立配对的记录，不倒填先前缺逐条日志的旧探针。
- 122 个源/配置文件（113 Python、7 schema、pyproject、原 requirements.lock）两臂前后与实际源码 hash 一致，详见 receipt 及各臂原始 result gzip。
- 未初始化 Worker 壳、未批准内存 read pin 仅作连续性检查，不算真实准入。为使两臂输入完全相同，只临时替换 helper 自己的 `time` 绑定；构造后恢复，产品真实 `time.time` identity 保持，没有更改数据库 TTL/lease 或实际时间门。
- 原 Worker/claim/审批/journal/模型/HTTP/Mock/public ancestor tripwires 及已知预绑定 alias 封闭保留。SQL 只允许 SELECT 与原 BEGIN IMMEDIATE；实际权限读取照常发生，0 新许可不表示权限检查为零。
- producer 内仅计数并将 SQL/原生参数序列化到内存；完整输出获取、磁盘 IO 与 hash 汇总在计时外。tracemalloc 只检查未开启，未调用 start；没有 trace/profile。check/key 计数不含初 pin/退出，不能混用旧 2030/2161。

实际命令 `.venv/bin/python /tmp/sim2act-envelope-paired-20261020/paired.py`。该目录仅准备从已提交 archive 核 hash 复制的闭库/helper 和基线单函数，未使用旧实例运行态。本目录脚本为实际执行原样副本；不在证据目录直接运行，不授权再次执行。本轮没有新增 pytest/mypy/Ruff 或将以前 119P 重标为本轮测试。

## 下一项具体判断

保留完整扫描以后，仍实际发生 2158 次新鲜完整 key 编码、2028 次 check 与 2814 次 SELECT；本轮未测函数内部排他成本，不能把旧 codec.bytes 10.308 秒、typed-storage 2.186 秒或 SHA 0.995 秒当作当前收益预算。此次排除的是末尾显式整段拷贝作为性能根治，并未定位全部当前 CPU。

下一证明切片选择 `_cold_graph_validate_inputs` 的**完整结构验证与丢弃的归一化/digest 分离**。当前源码中三个生产调用点（runtime 初 pin、add 入边、apps 初 pin）均为丢弃返回值的独立 Expr；这使“是否必须构造完整 nodes 再 fingerprint”值得进入设计。产品实施状态是 **NOT_READY**：不能直接删 nodes/末尾 JSON，因其仍承担非有限数、超长整数、UTF-8 surrogate 错误，以及“完整结构错误先于终端 JSON 错误”的顺序。nodes 的父节点先序与原 visit 时间顺序也不同，提前在标量访问时抛错会改变混合错误优先级。

具体下一步应先建立 validator 专项差分 oracle：成对组合结构错误、hidden RowMapping、forbid-root、非有限浮点、超长整数与 surrogate，保留当前原始存储范围、别名/环检测和终端错误顺序，再证明一种无需无用中间归一化的验证方案。历史 validator 133 次包括 130 add 与初 pin，不是每个 key 都调用；原仪器化 1.9 秒不承诺可回收。本轮没有实施该重写或运行新测试。

直接改为 Pickler 写 `SHA.update` 也 **NOT_READY**：虽然可形式上保持 prefix+payload 的 hash 域，分块 hash 会在尚未完成输入读取时引入 write 回调与 GIL 释放时点；原整段 SHA 在完整 bytes 生成后发生，当前没有可变别名独占证明。[Python 官方 hashlib 文档](https://docs.python.org/3.12/library/hashlib.html) 说明超过 2047 字节的单次 constructor/update 可释放 GIL。独审没有可直接接受的新大产品改动，因此不盲写 codec、不删 checkpoint、不扩租约或准入。
