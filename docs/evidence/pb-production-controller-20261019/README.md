# P-B 原合同生产控制器：有限工程接线，整链未验收

结论为 **NOT_ACCEPTED**。本轮接通原 P-B 合同的生产控制器、Source 归档和提取/逐次使用/Cold 工程路径，修复提取账户校验嵌套事务及必要的只读证明接线；当前不能作为完整可用、已验收的 P-B 产品能力交付。没有新增 executor、Grant、账户来源、LIVE 许可、凭据或部署，也没有改变原七槽、1RPM、30 秒租约和 300 秒 Run 时限。

冻结源码及测试提交为 `c54571391bd695ea116afc0020738c3585ba4972`，产品源码与 `476733e8b9b5fa5b03320968d7ce77e3a9f763f1` 完全相同；c545 只补齐测试种子的必填 status。原阶段映射在 [事前方案](../../F2/PBProductionController20261019.md) 中保留。

## 当前提交的实际验证

| 原始阶段目录 | 结果 | 实际范围 |
| --- | --- | --- |
| v7-mypy | PASS，113 源文件；外层 41.782 秒 | 完整 src，非增量 |
| v7-lint | PASS，10 个改动文件 | 未声称全仓 Ruff 通过 |
| v7-projection | 1 PASS；外层 14.748 秒 | 标量投影的事件/Attempt 基数、缺失、混合 marker、owner、activation；种子不是完整生产证明 |
| v7-ordinary-guard | 1 PASS；外层 64.535 秒 | 3 次实际普通 Mock 生成；完整首证/复用/深拷贝、缺键与显式 null、写后失效、合成 Grant 无数据库写入到期 |
| v7-final-nodes | **2 PASS / 1 FAIL**；外层 199.879 秒 | 默认禁用/固定来源缺失/实际软件资格拒绝、同连接账户回归通过；P-B 长链失败 |

长链的 Generate Run 为 `run_0d175c9a46fe46ca8f1156d2b9e33077`，只记录 **1 次 Generate Mock**。后续预留前 Store.guard 拒绝 `Stale worker lease`，API 最终 Run 为 FAILED；Source、提取、Cold、四个归档损坏拒绝、Cold 同 key 防重复、同 Run 结果/人工验收，以及四次自然预留 token 观察均未执行。不能把测试代码中的这些断言当作已通过。

日志记录最后一次实际续租返回 lease `1792409987.294133`，随后有 `SQLITE_BUSY(5)`；最终 guard 的原行值为 RUNNING、fence=1（与期望相同）。原比较时刻和外层调用栈没有留存，故没有判定具体锁占用原因或持续事务时长。没有无变化重跑、延长租约/Run、改批准时钟，或扩展为通用 heartbeat/恢复矩阵。

## 原始失败及修复归属

| 提交 | P-B 批次实际结果 | 未到达的路径 |
| --- | --- | --- |
| ba0fa2a400e6289a3723256bd5f3ac913cba3cac | v1：2 Generate Mock；预留前 stale lease，141.703 秒；最初原因未明 | Source/提取/Cold |
| 0339844933db09980dedaa62871ced4926ba811b | v2：3 Generate + 2 Source Mock；Source SUCCEEDED；首次 extract_pb 的账户检查打开第二个 SQLite writer，544.832 秒 | 成功提取/Cold/归档四故障 |
| 91ffc55c15b6d3efb573913470db51dffbd9720e | 同一原连接账户检查两次，嵌套事务 tripwire 回归通过；无发送/业务写入 | 实际提取整链资格仍未证明 |
| 3b91e21cd2b07863d02561a0957bb7fb83feb4b4 | v4：3 Generate Mock；Source 首次预留的复合 guard 拒绝，392.960 秒 | Source 模型/提取/Cold |
| 97d6f4acc9e714ded0699853c21ca536e101a9c7 | v5：3 Generate Mock；Source 本地 read_pick 最终 guard 拒绝，303.983 秒 | Source 模型/提取/Cold |
| c54571391bd695ea116afc0020738c3585ba4972 | v7：1 Generate Mock；后续预留前 stale lease，199.879 秒 | Source/提取/Cold |

失败 P-B 批次合计 14 次实际 Mock，普通缓存权限回归另有 3 次；真实模型/账户探测为 0。不同源码、不同合同和不同 Run 的槽位没有拼成一次成功。实际代码修复不等于剩余路径运行验收。

只读剖析使用原失败合成数据库的副本，没有修改原数据库、合同、软件资格或时钟，也没有创建 Run/发送模型。v5 第一次剖析因 Limits 参数缺失提前失败；修正后的 profile 有自身开销，不能归因真实租约耗时。新旧标量 anchor 在实际副本上逐项相等，20 次调用的 SELECT 从 120 次降为 60 次。投影保留 owner→expected→own_project、双 anchor、当前 Grant、token/事务/线程/写 epoch 边界。LIMIT 4 只限定返回行数，未证明限定数据库扫描/排序量。4767 的首个投影测试因种子缺 status 失败，c545 修正后实际通过；原件均保留。

## 真实边界与证据

固定生产账户 resolver 仍因缺少经审查来源而拒绝；实际精确软件资格也不匹配。没有通过更换锚点或测试替身自授 LIVE。主 P-B 测试以有限 MockTransport 和普通 HTTP tripwire 验证工程分支，替换环境/来源/资格仅在测试进程内；LIVE 形状的合成行与 provenance 标签不证明真实账户、免费资格、费用封顶或真实服务来源。

每个阶段保留实际命令、退出码、stdout/stderr、JUnit、输入前后摘要、有限 Mock 原字节和合成数据库。当前 2110 项输入为 711 个逐 Git blob 核对的已跟踪文件与 1399 个 node_modules 依赖哈希；不是完整环境冻结，Python/egg-info 在清单外。打包保留各执行 SHA 的已跟踪输入、独审及脚本；明确省略生成的 mypy 缓存，描述但不跟随/删除临时符号链接。

早期 ba0 的全仓 Ruff 失败 110 项诊断仍保留；没有在最终源码声称全仓全绿。Windows、PG、native/UI、远端 CI、真实语义/场景、人工接受均未执行或未验收；最终人工验收不能由脚本批准。此前满盘丢失的旧独审报告没有补回。


可下载的 [完整原始证据包](pb-production-controller-raw.tar.gz)（27,402,348 字节、507 个成员，逐成员哈希校验通过）；[打包回执](package-receipt.json)、[原件清单](RAW-MANIFEST.json)、[seal](RAW-SEAL.json)、[全部阶段结果](phase-results.json)、[输入身份及边界](input-identity.json)。证据包与 seal 均明确 NOT_ACCEPTED，不是通过证书。

- 原始包 SHA256：`541714584ddf454fdc1f8b71ddf014787c3980b2506bcfc8638d794d7813a4ef`。
- 原件 manifest SHA256：`41d6ab1ff80176f07291b5ea290431505666a3b7104ab835d123793d762c3c95`。
- [最终独审](final-review.md) 的 [60 文件清单](review-manifest.json) SHA256：`6ed6ffcb1ed43f75d5428149ace57ddf7563fdc203489b0c56df62e4803b838f`；该清单的全部文件均在包内 `independent-reviews/v7-final/`。独审没有执行 DB 查询、模型、测试或网络，不能代替作者的运行证据。

本目录只归档源码 c545 的证据和结果文档。后续归档提交的 src/tests/配置与该执行提交逐字比较；最终远端状态在交付回执另核，本文不提前宣称推送或 CI 成功。
