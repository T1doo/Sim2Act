# 默认 Graph 完整版本生命周期：源码接线与语义验收

验收源码：`4d0b16f2cce1d83363106aa00c05bc969e39ac23`，分支 `dev/cloud-g0-live-20261028`。首个完整协议提交为 `75b8639c5173cf625308c3478967ce9c80fee2d6`；其新增跨 Graph 清理回归由 `d7860dfe644fbe0524cb74bec8e7669ce598b279` 修复，最后提交只保留测试 fixture 导出及通用依赖。完整生产者→消费者列表见 [协议入口表](../../graph-version-lifecycle.md)。

## 实际接线

Graph 初始化与 add、Frontier 初始化与 added 是固定发布入口。C Journal 每版持该次原 codec 的完整 immutable V2 bytes/key/sequence；字段、精确类型、顺序、别名及 RowMapping 隐藏存储仍在原完整域。版本身份另绑定原 Graph、连接、事务、scope、epoch、phase、driver 和 thread。check、selector、fallback、export 和 G1 proof 均消费相同版本，未把当前可变图回算成旧期望。`input_bytes(_snapshot_values=True)` 仍是原 live alias 投影。

独立 C issuer 弱登记防删除、替换、降级和复活。固定生产者、predecessor 及分配后复核约束发布。异常先撤销原登记，无需沿损坏的 Python 引用找发行方。清理时不会因借用别人的 Frontier 撤销其 issuer。完整动态授权、撤权、owner/epoch、stop、deadline、原子事务和 W5→G1 原完整执行均保留，30／120预算不变。

## 冻结结果

实际数量、退出码、时间、源码树及四个原生二进制身份以 [identity.json](identity.json)、[最终回归](final/regression-run.json)、[最终垂直链](final/vertical-run.json) 为准。两个 runner 在前后核 HEAD 和 clean worktree，且有独立有界进程组等待；没有并发重复业务运行。

最终回归覆盖原 Graph/Frontier 结构、原 accounted native/receipts/component、持久配对错误边界、准备生命周期及新增版本反例。新反例保留旧期望、变异、别名、跨 Graph、重入、实例和类方法替换、GC、隐藏行、foreign dict/key/active 回调、原生缺失 fallback 及三种新进程导入顺序。参见 [JUnit](final/regression.xml) 与 [原始输出](final/regression.log)。这是相关套件范围，不是全仓库或全产品验收。

实际垂直链从现有 Generate/Source 合成前缀接续一次 Cold 模型步骤，默认前图与独立 post 图都实际发行版本，执行原五写、完整 G1、proof READY→CLOSED 及 SQL COMMIT，新事务读回 Attempt/Operation 均为 VERIFIED，导出 raw/key 正是 proof 持有的同一个 Version。参见 [结果](final/vertical-result.json)、[原始输出](final/vertical.log)、[JUnit](final/vertical.xml)、[完整运行脚本](final/run-vertical.py)。

**该垂直链使用虚拟业务时钟、6次固定 Mock、0次真实模型，数据库为独立 test_only 文件 SQLite。**现有三处合成来源替代仍在；不是正式账户/PG，也不是两个 Cold 的完整自然目标、首次新进程重开或原30秒性能验收。脚本墙钟时间包含合成前缀及观察开销，不能当 G0/G1 净耗时。本轮未执行原30秒转正验收，不能声称性能修复完成；W5→G1 依赖桥没有缩减或替换。

## 失败与逐项归因

原 [75源码相关回归](failures/source-75-related.log) 为4失败／108通过。

| 原失败 | 对照及处理 |
| --- | --- |
| `cross_graph_frontier_swap_cannot_skip_other_mutable_inputs` | 新协议真实回归。顶端 C 已只撤销自己的原 issuer，Python 随后仍撤销借用的 Frontier。删除重复 Python revoke，exact/plain 字段及原 graph 所有权门限定剩余缓存／原 mode 清理。原测试未改，最终重新通过。 |
| `issuer_order_registration_original_pin_and_no_runtime_callers` | 父版也失败：静态导入名单漏原有 receipts、base_segment、structure_guard。仅补确切已有模块；原 issuer 次序、捕获后变更拒绝、禁止 scope 私用断言保留。 |
| `owned_malformed_extract_pair_matches_old_controlled_error` | 父版也在 Graph 构造时 Source 固定代码门拒绝，尚未进入 parser。去无关 origin/scope/parser 替换，以原 controlled(pair) 对照真实 `_cold_extract_pair`，实际观察原 model_validate，保留同一受控错误及失效状态。现在是 persisted-pair focused 覆盖，不能称完整 verify 授权链验收。 |
| `guard_valueerror_is_original_and_stops_before_second_lookup_or_parse` | 父版相同构造拒绝。保留原生产代码，用监测点在首查询后的原 check 入口抛同一个异常；保留1次查询、0次解析、异常对象身份和失效断言。 |

父版 `d6c37f1203126781b043775b0f1f3f29ce4f3197` 独立只读源快照，939个 tracked 源／测试／构建文件逐 Git blob 一致，四原生扩展在该快照实编；相同原四测试最终3失败／1通过，见 [父版结果](parent/parent-four-final.log)、[XML](parent/parent-four-final.xml)、[输入闭包及构建身份](parent/source-control.json)。此前缺证据 fixture 输入的准备错误不作为此对照结果。

fixture 修订首次对照暴露了原 pair 本身抛 ValidationError、须使用原 controlled 映射，以及静态名单另两个遗漏，保留 [原失败](failures/fixture-adjustment.log)。d786扩大收集因删除了其他套件使用的 `local_origin` fixture 导出失败，保留 [原收集错误](failures/d786-collection.log)；4d0恢复原导出，并令 malformed fixture 直接依赖通用 env 而不新增跨模块 fixture 依赖。未删除或跳过测试，未放松生产门。

早期75源码垂直链曾通过，但与最终源码不同，单列 [earlier](earlier/source-75-vertical-run.json)，不混作最终版本证据。

## 独审、候选及未验边界

两位既有独立只读 reviewer 复核协议与最后修复，未发现新增 mustfix；实际最终命令不由 reviewer 冒签。详见 [独审范围](independent-review.md)。发布文件只有合成测试输出、脚本及代码／包身份；不发布 DB 原件、模型请求体或私人账户内容。提交前对本轮工件做当前注入秘密值精确匹配扫描，仅保存通过布尔及工件 SHA256，不打印秘密；这不是全仓库保密证明。

原 Linux 限制候选 `Sim2Act-local-candidate-2ad3227621b4.zip` 保持 3,188,692 bytes、SHA256 `6b6e42d909089ad001a6ff889976b7eff0e65ab7e4229fd95f15377b57efe81d`。本轮没有覆盖该包或把新源码称为包内已安装内容。新 C API 仅 Linux CPython3.12／gcc 实编；新 Windows、正式 PG、大型 live、普通30秒目标和完整产品交付仍未通过。无新 Windows CI、本机操作、main、Release、部署、费用、凭据或权限变更。
