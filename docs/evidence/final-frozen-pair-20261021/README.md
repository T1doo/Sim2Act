# 最终冻结版：两条完整 Cold 合成语义链

本轮只补最终产品源码 `6ae62ae20ecff3550001c746ebb88af5d340713b` 的完整正常链
证据。没有修改产品实现、重跑先前 67 项负例或运行真实时钟 G0 launcher。
此前 [资格收窄证据](../base-single-content-20261021/README.md) 的中间版完整 A/B
不作为本轮测量；下列数值均来自本次唯一执行。新增测试为
`tests/test_cold_final_frozen_pair.py`。

## 冻结和执行

启动前核实 HEAD、远端开发分支及 main；没有旧 pytest/timeout 运行者。环境断开通知
后实际命令、文件及只读 collection 仍可用；完整测试尚未启动，不创建替代写入者。
冻结全部 152 个 tracked 产品文件和 4 个相关测试，运行前后 156 个摘要全部一致，
`git diff -- src` 为空。新测试 SHA256 为
`fc443e7e40ecc50b6fd5dc1ae7dd68c9e9252fe89e198ba05be80fbcedf3fd90`。

一次命令，退出 0，**1 passed / 117.65s**；唯一 warning 是既有 Starlette/httpx
TestClient 弃用提示。执行使用真实监督 `timeout --signal=TERM --kill-after=10s 300s`，
没有重试。7 Mock 交换 / 9 方法入口保护在新前缀创建前设置：Generate3 + Source2，
Source 的两个同步 delegate 另计入口；两个独立 Cold1 各一次交换/入口。实际正好
7/9，逐条 Mock 原件为 5+1+1。HTTPTransport / AsyncHTTPTransport 被测试夹具拒绝，
仅 HTTP Mock，无真实模型、真实账户来源、Cold2 或 W5。

沿原 `configured` 的三个显式合成资格替换（environment / resolve_account / software），
新建完整前缀、审批及账链，原 pre `audit_seed=None` 不变。关闭前缀后复制到两个
隔离新 SQLite；旧对照仅令 `_base_segments.eligible` 为 False，候选使用原最终源码。
每条链重新构造可变模型和 Worker；共享前缀 DB 的 SHA256 在两条链后保持不变。

使用明确仅测试的 `SemanticClock`，原 lease30 / Run300 / TTL1800 及原动态门保留。
原 heartbeat 仍提交 SQLite 续租；产品运行时钟没有修改。业务时钟结果不构成真实
耗时、CPU 提速或 30 秒真实租约通过证据。逻辑配置预算也不是 RSS 或磁盘硬配额。

## 本次完整观察结果

从原 first binding 到原 context 正常返回及故意关闭 scope 后拒绝的观察范围：

| 实际计数 / 状态 | 旧双完整 pin | 最终候选 |
| --- | ---: | ---: |
| codec 次数 | 8337 | 8062 |
| 累计 codec 返回 bytes | 4,894,540,040 | 4,682,215,371 |
| `_base` 入口 | 569 | 569 |
| 正常返回 / 故意跨关闭 scope 拒绝 | 568 / 1 | 568 / 1 |
| 合格单内容 `_base` | 0 | 275 |
| 原动态检查 | 1137 | 1137 |
| 完整观察 SQL 语句 | 7735 | 7735 |
| 原 Run 行谓词入口 | 2 | 2 |
| prepare、两次 commit、Cold receipt、原 scope 正常返回 | 完成 | 完成 |

编码减少 275 次（3.2985486386%），累计输出减少 212,324,669 bytes
（4.3379902353%）。这些是最终冻结版新测量，虽与中间版计数相同，不能据此推算
CPU/墙钟收益或真实 G0 剩余裕量。两个 policy wrapper 在两边相同。

`exact_output` 严格比较完整 authority outputs 和完整 SQL 序列及参数，保留 exact
type、bool/int/float、list/tuple、bytes 和 quoted_name/quote。原 context / Source
业务指纹及两次 commit 的诊断摘要也一致；不以诊断摘要替代原业务指纹。

在原 `_cold_receipts` 的 exact Cold run、reader、pending operation 分支，记录动态
`len(_receipt_proofs)` 对应的原 receipt-binding 和 receipts 根，断言原 binding 身份、
返回 outputs/proved 与已存值身份及 pending_id / allow_pending。两边完整原回执结果、
存储 payload/flags 和原 binding audit fingerprint 严格一致。没有重新查询、重放
`_receipts` 或使用伪 DTO；**未将含 RowMapping 的整个 binding 序列化**。回执严格
编码指纹两边均为 `9ee9a02803e0fa46cce915f5313d88636d5206a5b35ec9c9a3c54367c6196b30`。

最终时钟观察只代理原函数的一次原采样，返回原值，不重新采时钟。只有 exact 原
`_cold_model_before` generator frame 记录样本；到达原 `and` 右侧证明左侧 stop
检查通过。两边原 `at=1800000300.0`，原 deadline tuple 最小值 `1800000330.0`，
scope 已关闭，原最终门和原 context 返回均完成。完整 tuple 保存原件，且严格等于
第二 commit 的 deadline tuple；不是根据总耗时推断通过。

成功在这里仅指原 Cold context 合成语义链。原观察器在正常退出后以 BaseException
停止于 W5 前，数据库 Cold Attempt 保持 **RECEIVED**；不是业务 SUCCEEDED，也不是
W5 五写组验证。本轮没有注入写故障或重新运行先前反例。

## 清理、审查和原件

两副本 clients / Store 均经原 `close_case` 关闭；测试断言新线程全部结束。
退出后精确检查可执行文件/argv，未发现 pytest 或本次 timeout 进程，无 SQLite
`-wal/-shm/-journal`，三个 DB 哈希及未改变的前缀哈希保存在 `postrun.json`。
没有删除锁、终止未知进程或更改权限。

Ruff 通过，collection 仅收集 1 项、0 Mock；唯一完整运行如上。先前最终版本负例
覆盖仍见原证据，本轮按任务只闭合最终版本正常两链差分，没有机械重复。
独审只读代码/原件，没有另行运行测试、导入产品或消耗 Mock。代码 ACK 与最终
结果 ACK 在 `reviews/`，限制仍为合成语义证据，不授予真实 G0/生产来源/W5 通过。

`artifact-manifest.json` 逐项保存原始/压缩 SHA256 和大小；`originals/` 为原 JSON、
完整 SQL/参数、输出、回执、最终样本、冻结清单、监督日志和 Mock wire 的 gzip
副本，可按 manifest 解压核验。SQLite 文件不提交，保留在本轮隔离 `/tmp` 目录。
本次提交仅测试与证据，产品源码与上述冻结 SHA 相同。
