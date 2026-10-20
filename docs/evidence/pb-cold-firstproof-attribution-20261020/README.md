# 首证逐调用归因：未证明性能改善，完整验收仍失败

本轮从已推送的 `f9dfcf319b1a5bd66246aaa07a4dd0a082d1bd98` 接续，仅运行一次有界 dormant 首证读取探针，并保全归因和独审证据。**未修改产品源码或测试，没有可接受的性能修复候选。** 原完整用例的 `FAIL_NOT_ACCEPTED`、W5/G1/finalguard `NOT_REACHED` 保持；本轮不授权也未执行第二次完整链。

探针复用本实例先前生成的合成 G3/Source2、queued Cold 前缀库，只复制一个已关闭 SQLite，构造局部 read pin，实际调用 `_cold_first_binding` 一次。没有运行 Worker、认领 Run、创建 Attempt、审批、Stage、journal ALLOW 或模型。旧环境没有访问或恢复；旧满盘环境最后独审报告未落盘的证据缺口仍在。

局部 pin 使用 `object.__new__(Worker)` 的未初始化壳对象，不调用 Worker 构造器或执行循环；内存中另建未批准的 synthetic read-pin contract，假软件/授权指纹及 `now + 3600` 只供读取连续性检查。它没有延长数据库中任何原合同或租约，也没有获得真实准入。实际 `own_project`/`authorize` 权限读取照常发生；表中“0 新审批或许可”不表示权限检查为零。

| 本轮实际观测 | 结果 |
| --- | --- |
| 首证 producer | 1 次，正常返回；同一 guard 有效 |
| 外层 | 23.080816 秒，exit 0，非 timeout，原上限 90 秒 |
| producer body | wall 19.784824 秒；thread CPU 19.423375 秒 |
| CGR.check / input_key / add | 2030 / 2161 / 130 |
| Generation reader.check / record | 272 / 16；raw_seed 分支 0 |
| 原 SQL | setup 15 SELECT；首证 2814 SELECT；各 1 BEGIN IMMEDIATE；DML 0 |
| 模型 / 新审批或许可 | 0 / 0；有限 tripwire 未触发 |
| 源码、源库、复制库 | before/after 一致；原始 hash 在 receipt |
| observer | secondary/error/dropped 均 0；原返回值/异常身份不替换 |

`input_bytes` 共 2161 次，累计返回 **553,170,433 字节**，单次长度范围 6,435–579,257。它与 codec 和 SHA 输入重叠，不是唯一数据量，也不能相加。每个 check 恰好调用一次 input_key；另有 130 次 add 的完整重 pin 和 1 次构造初 pin，即 2030 + 130 + 1 = 2161。没有发现 input_key 内同一次 check 重复算两遍 hash 的现成冗余。

| 原调用 CPU（包含探针开销） | inclusive 秒 | instrumented-child-exclusive 秒 |
| --- | ---: | ---: |
| codec.bytes | 10.308181 | 10.308181 |
| trial.typed_storage | 2.186465 | 2.186465 |
| input_bytes | 12.666613 | 0.276785 |
| validator | 1.908761 | 1.891971 |
| SHA constructor | 0.995218 | 0.995218 |

完整精度以 `ANALYSIS.json` 和原始 call records 为准。inclusive 指标有嵌套；排他值只减去已安装子探针的 body 时间，仍含观察器开销。这里显式安装了 typed-storage tap，原完整 observer 没有；原报告 input_bytes 排他 7.207 秒不能全归为其自身处理，也不能与本表直接比较。没有无探针对照。**先前完整 G0 的 37.52 秒与本轮 23.08 秒属于不同夹具、执行范围及观察器，且产品源码相同；不能声称优化或退化。**

静审及逐调用记录排除了几个不安全的表面合并：

- Generation reader 和 Run facts reader 的入口完整 pin 后仍可能执行 serializer/warning 回调。下一入口 pin 可能就是回调后的完整漂移检查，不能仅凭相邻 tuple 或 registry 查询删除。
- `record` 中的 `deepcopy` 可执行 hook；`add` 的入参验证、事实插入及完整重 pin 是真实事实扩展边，均保留。
- typed cohort 的 fixed serializer、真实 SQL、权限/source 回调、封口和末时钟边界均保留。raw_seed 的嵌套入口属于未到达的后续路径，不能充作本次 G0 的改善。
- 仅发现 apps 的两个 prefix 入口可在补充 exact 输入门后构造纯共享 core；本次最多省 2 次 pin，其原调用 CPU 合计仅 0.005330 秒。没有为这一微小收益修改产品。

因此尚未证明高频完整扫描可安全且实质减少，**不建议现在再跑完整链**。这不是新的代码、性能、Stage 或产品验收 ACK。本轮没有候选源码变更，因而未新增产品 pytest、mypy、Ruff、漂移/错误顺序/回滚门；原先通过和失败的短门均按原封存解释，未重标为本轮通过。只实际执行了探针的 3 项纯 stdlib fake 自测（调用归属、原返回值/异常身份、第二次 producer 前阻断），3 PASS / 0.018 秒。

`raw-evidence.tar.gz` 保留完整 parent/child receipt、原始 calls/site/summary、15 秒堆栈、复制库、局部 read-pin 参数、探针及 unchanged helper 源码、stdlib fake 原始结果、分析脚本及 v16/v17 独审报告。`ARCHIVE-MANIFEST.json` 给出逐文件 hash；打包后按实际读取内容复核，未将未来封存/推送冒充独审范围。

最新保存配置重新发布后，本实例没有被假定为自动更新。父侧应先核本 writer 终态，再在最新指定实例 clone 本开发分支，验证本证据提交与 `f9dfcf31…` 祖先和工作树；阅读本报告及原 `pb-cold-settlement-graph-20261020/README.md`，从只读 raw call stacks 选择下一最小切片。不要重跑本轮唯一首证探针或完整链，除非获得新的明确授权；不要复用本地绑定为真实审批或恢复旧实例文件。

没有 Windows、PostgreSQL、远端 CI、真实模型/语义/场景或真人验收。没有改 main、强推、部署、延长 TTL/Run/lease、增加费用、凭据、安全权限或绕过拒绝。
