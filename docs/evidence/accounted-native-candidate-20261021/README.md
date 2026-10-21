# 默认关闭的 native accounted 集成候选

基线：`6570b7072e3cd415fbbcb3a130e8a80d9ad8be79`，开发分支
`dev/production-trial-stages-20261018`。本片实现原有 Source + Generate prewrite
协议的一个可审候选，默认关闭，只能显式内部接入 test-only SQLite、pre-origin
图。没有新增环境变量、公开配置或默认 Worker 接线。

本片没有运行完整 native `_prepare`、两次实际 trial commit、G0、Worker、业务
Mock、真实模型或性能窗口。归档的通过结果是离线合成事实、隔离 SQLite 和
helper／coordinator 级回归；不能据此宣布 G0 修复、生产资格或提速。

## 关键路径

- `_ColdTrialGraph._prepare` 原位保留 Source producer → recipe 校验 →
  Generate backend-version 查询／校验 → Generate producer。各 producer 一次；
  `stage` 只暂存完成结果，所有中间原校验通过后才统一选路。源码顺序经独审；
  测试用真实 producer 与版本 SQL 的有限 harness 验证顺序及中途拒绝，未执行完整 prepare。
- 发行前同时覆盖两族 raw／typed 完整副本比较、完整 upstream Run、Ledger、
  其余 graph／contract sizing、不可变访问器／结构等价类、Source canonical
  产品、后续两段协议的比较／快照／镜像暂存。容量或优化表示不适配才整族 LEGACY，
  复用同批原 producer 结果；变更、cycle、nonfinite、原校验错误不伪装为容量。
  OWNED 发行后失败即关闭，不中途回退／重读／重发。
- 原 raw／typed guard 一直保留到最后复制完成；最后一次原全检查后才安装
  native frontier 并释放 oracle。不是在旧两次扫描和 oracle 外继续叠加新扫描。
  未选择 native 的旧路径保持原模式。
- 两族使用同一 scope／账本、私有发行的不可变 packet、预构建并封闭的 Node／Value／
  Record／Family 表。完整 native 结构键作等价类（hash 碰撞仍比较完整键），
  保留容器／标量类型、字典顺序无关、quoted-key 文本语义、quoted-value 类型、
  浮点正负零和 DAG 值语义；不以对象身份或摘要代替领域相等。
- frontier 去掉两族 accounted 顶根以及 `complete.source`、`complete.generated`、
  `complete.generation.run` 的重复序列化。只替换已证明 owned 的精确路径；
  其他独立别名、可变根、context、外部 Ledger、授权／撤权、完整 DB 读集、
  transaction／fence／stop／最终期限仍走原新鲜检查。RowMapping 隐藏 data／索引
  仍被完整 capture；被忽略 foreign index 的遍历不调用其 hash／equality。
- Source resolver／archive 继续执行真实原查询、授权与动态检查，纯叶子读同一
  owned family；Slot／Identity／Outcome 逐字段关联、完整真实 receipt/proof 字段、
  原 wire／payload／业务指纹均比对，不解冻回第二份消费者来源。
- 私有 `SIM2ACT_NATIVE_ACCOUNTED_FRONTIER_V1` 与旧 pickle raw/pre/post/origin/software
  合同隔离。native active 时旧 origin bytes 导出拒绝；没有向持久签名混装 manifest。
- 正常退出资源寿命归原 graph scope；原 scope 最后检查仍执行，再 invalidate 关闭
  arena。commit／rollback／scope 关闭、写入、foreign graph／record／frontier 拒绝；
  foreign frontier 不能关闭另一 owner。

## 容量口径与协议边界

这是固定候选协议的保守逻辑分配／工作账本，不是精确 RSS、Python live heap、CPU
指令／时限、native hard quota 或整个 G0 的上界。没有给 SQL／JSON 加全局 cap，
没有截字段或缩小原业务接受域。合成测试的大 allowance 不构成生产规模资格。

完整当前输入只作发行前有界 sizing，不作新消费者来源；所有复制及 key／name／
mirror／arena／canonical 分配先预费，受控临时引用和 memo 在 ticket 释放前丢弃。
共享 DAG 只复用已完成不可变子值并核最长深度，cycle 不接受。

后续根是固定 12 项 continuation 根，另从同一次完整 bounded copy 的原
binding／source_binding 中导出最多两项精确 `release-pointer:<user>:<rid>`；
snapshot.release_id 必须匹配完整 release.id，先预费再构造键。没有前缀白名单、
提前 SQL 或新增 Release 权限。未知根／重绑在该内部协议中失败关闭，不冒充产品通用模式。

continuation 预费两个独立的 first-boundary 最大值：SourceBodies 两次 Slot 比较，
Archive 两次 Slot 比较，完整 resolver receipt 与两组字节 tuple。真实第二段
`_recheck` 不重放 Archive；离线 helper 测试重放两轮，比真实该段更强，但不是两次 commit。
当前 `_FIELDS` 公式实际计算 `slot_nodes=53`（完全展开为至多 51，仍保守），
`receipt_nodes=74`。源码旁注的 identity 15 项／55 是非阻断注释笔误；实际 identity
有 14 项，预算使用 `len(_FIELDS[...])` 的 53，不得把 55 报为实测／预留值。

结构等价类采用线性驻留表及字典排序（含 `sum(d log d)` 工作），无全节点平方
等价表；碰撞／遍历工作在发行前作保守逻辑预费。Stream 比较使用每次调用的
强引用 completed memo，不复用可变数据的验证 PASS。native resolver 18 字段、
两项 7 字段 proof 的 exact 长度先于遍历，覆盖当前原 producer 全部输出；
不加无界字符串长度 cap、不丢字段。其他 producer 输出形状不被默认为产品资格。

## 验证与失败保留

最终结果和命令见 [validation.json](validation.json)；六文件冻结 SHA 见
[source-hashes.json](source-hashes.json)，原始 pytest／JUnit 见 `tests/`。
Ruff、mypy、默认路径／旧 codec AST 比较及 diff 检查记录在 `checks/`。

最终冻结代码的定向回归为 66 passed；相关扩大回归为 337 passed／0 failed／
0 errors／0 skipped，184.00 秒。只有一项既有 Starlette deprecation warning。
覆盖整族选路／容量不足无半发行、producer／中途错误顺序、完整 nested frontier
排除及独立别名变更拒绝、当前 settings/model/max_output_tokens/binding/stop，
事务写入／关闭、独立当前 version/fence/lease 损伤、完整 Slot/Identity/Outcome，
外来对象回调／cycle/nonfinite、跨图／跨阶段与只读 arena、DAG／depth／预算释放。

真实 `_graph_pb_accounting` 仍因缺少已审生产 account evidence 而
`LIVE_BLOCKED: No reviewed production account evidence source is supported`。
测试在 LEGACY／OWNED 都证明拒绝，未 stub／绕过此入口；Source helper 阳性
来自合成已归档事实，不是生产 admission 阳性。

早期原始失败与中间通过日志全部保存在 [development-runs.tar.gz](development-runs.tar.gz)，
各原件长度／SHA 与 JUnit 结果见 [development-runs.json](development-runs.json)。
其中 first 为夹具错误／原 entitlement 拒绝，second 为 lexical scope 提前释放，
frozen 扩大回归为 333 passed／3 failed（两个 lazy Release 根缺失、一项私有模块
caller allowlist 遗漏）；均不重命名为最终通过。修正只补已有绑定的精确懒读键、
原 scope 生命周期及测试私有导入例外，不削弱旧拒绝。

## 独立审查与剩余条件

[来源／生命周期静态 ACK](reviews/frontier/CLOSURE-NATIVE-STATIC-ACK.md) 和
[协议／逻辑预算静态 ACK](reviews/monitor/REVIEW.md) 均核对同一组最终六 SHA。
旧设计、中间发现和旧 ACK 也保留，各报告明确自身范围。reviewer 没有运行测试、
数据库、业务、Mock、prepare／commit 或性能测量；最终测试由唯一写入者运行。

仍缺完整 native binding／prepare／两次真实 continuation 集成、生产规模资格、
真实生产 account evidence 及 G0 性能验收；本候选保持默认关闭。旧原始窗口与失败
证据不修改，没有新增 Mock 窗口或放宽 lease／TTL／Run／RPM／权限／预算。
后续启用或性能结论不得从这些 helper 测试和静态 ACK 推导。
