# Bounded accounted cohort — 2026-10-21

基线 `e617498a5d28b9bbfa4605c61546d57f02446144`。本片完成显式、未安装的 SQLite 核心接线：**直接有界 raw→prepared 复制、同一新增工作 ledger、两族未发行时一次选路、发行后失败闭合**。既有运行路径仍关闭；无 settings/env/API 入口，`_ColdTrialGraph._prepare` 没有调用本入口。没有 G0、业务 Mock/Worker、真实模型、第四窗口、完整 native `_prepare` 或两次 trial commit 运行。

原事务、SQL/JSON 获取、查询完整性、授权、租约/fence/期限和全部 fullguard/pin 保留；没有 SQL LIMIT、全局 JSON cap、裁字段或新业务限额。没有修改 main、外部权限、凭据或费用设置。软件内容修订正常改变 implementation 指纹，未重签旧 Run/批准。

## 接线和选路

`cold_accounted._bounded_cohort` 只接受原 `_ColdGraphRead` 的有效 pre / test-only SQLite scope，显式 `_Bounds` 和 `_Limits` 没有产品默认值。

1. 原 Source、Generate `_graph_stage_accounted(..., _owned=None)` 依次各完成一次。保留原完整查询、Slot/Capture/body/usage/Operation 验证与末 fullguard；失败立即传播，不为优化补跑、重读另一批事实或发送。
2. 两组完整原 tuple 暂存未发行。原 assertion-only oracle 和 fullguard 核完整业务 raw 与 typed 来源，动态 settings/worker/model/max_output_tokens/transport/current binding、scope/事务/fence/授权等仍走原门。
3. 在任何 handle/owned 消费发布前，有界投影直接复制全族，构建私有 packet，并与同批原完整 raw 进行受管比较，最后再原 fullguard。两族构建前和构建中都执行预算；预检不替代强制构建限额或后置验证。
4. **仅专用 `_Capacity` / `_Unsupported`** 在这一未发行区间可选择 LEGACY。容量不足（含极小启动 resident/peak）仍要先完成原 producer/原错误检查；回退前再次原 guard。未发行副本丢弃，ledger 关闭，返回同一批完整 raw tuple。LEGACY 没有新 issuer，不经过旧 `scope.issue()` 重跑 producer。
5. 合格后一次选择 OWNED，在容量 catch 之外登记同 scope 两 family，再完整 associations/原 guard。初始化两族时结果尚未向消费者发布。开始登记后或消费者预算/动态检查失败均关闭两族、清空 handles/逻辑输入并释放 reservations；没有晚回退、解冻、重发或自动重试。

固定路由控制对象/ledger 管理元数据本身是常量控制开销；65536 的 resident reservation 用于 OWNED registry/固定小结果脚手架，发生在原校验之后、数据构建之前。它不是低预算时抢先拒绝原业务的全局门。

## Raw→prepared 覆盖

`_cold_accounted_budget._Projection` 不调用旧 `_capture.row/_fixed/_cold_graph_row_storage` 或先 `model_dump` 出全图再数。字典/序列复制在每节点/边分配前 reservation，按长度廉价拒绝巨大浅容器；字符串逐字符计 UTF8 surrogatepass/ASCII 膨胀，normalization 前预留，bytes 计原长度和 base64 上界。整数先 bit_length；深度含最长共享路径，另受递归编码器可安全执行的保守表示子域限制，超域选旧路，不改变全产品接受域。

| 来源 | 新路径保留/检查 |
| --- | --- |
| Run / Attempt | 完整 18 / 13 列及原实际数量，含 context/result/error、parameters/usage/response 等，不投影成少字段 |
| RowMapping | exact parent/keys/data/index；遍历全部 index 预付 work，foreign 项也计成本，但不对其 hash/equality/str/repr；保留全部 hidden `_data`、keys、有效原生字符串 safe-index；位置与可见字段集照原规则检查 |
| Slot / Identity / Outcome、Capture、BodyArchive | 只有明确的 typed 位置启用固定模型适配；exact class/raw/fields/fields_set/extra/private 屏障后逐字段复制，不预先 model_dump，不省非 aid 字段 |
| 原生 JSON / hidden data | 不默默把模型对象变成字典；表示不适配走发行前 LEGACY。native 与 typed memo 域分开 `(id, typed)`，不借另一域完成结果绕门 |
| 别名 / DAG / 环 | 每次局部强 memo、active、完成 height；同域复用完成的拥有值，保留 shared hidden/native 容器；每条复用边检查最长路径，环拒绝，不按每条路径指数展开 |

复制产物不含外部可变 dict/list/RowMapping/Pydantic 引用。只重用不可变原生叶子；quoted_name 的原生文本语义保持，由既有 encoder 变成纯文本/tag。未知类型不会触发 reducer、foreign iterator 或 metaclass equality。

新 packet envelope 是 **`accounted-family.pre.bounded.v2`**，固定领域字段合同继续使用已有 record schema；与旧私有 packet bytes/digest 不保证数值相同，尤其固定模型别名不再依赖 model_dump 的复制偶然性。原 raw/pre/post/origin/software/公共回执合同没有混入新 manifest/digest，也没有用它替代原字节业务 SHA。原始字节、完整 Slot/Identity/Outcome 及回执由实际等价/拒绝用例核实。

## Ledger 的明确范围

一个 `_Ledger` 同时覆盖两族的新增受管数据。单位是**保守逻辑分配/工作费用**，不是精确 heap bytes、RSS、实际仍存活对象数量、CPU 指令计数/计时硬限或原 64MiB 磁盘监测。没有声称 Python 原生硬配额。

| 类别 | 预留及寿命 |
| --- | --- |
| 复制 | 节点/memo/active/height、dict/序列构建与 list→tuple 重叠、字符串 normalization、全部 safe lookup / visible / sidecar，新建前增 ticket |
| 编码 | 私有 prepared 先被有界 meter 核实；在第一次旧 `_freeze` 前预留保守全部 encoder 峰值，包括 prepared、nodes/ref/memo、UTF8 临时、base64 bytes/str flat、JSON Unicode/ASCII chunks/list、最终 join 与输出同时驻留 |
| 两 packet | 各 resident reservation 持有至 scope.close；先有 Source 再构建 Generate 时共同占账；不是每 packet 单独清零的假总峰值 |
| 原 raw 比较 / snapshot | 同 ledger 的临时 projection+packet lease，with/finally 释放；Slot、完整 Run/upstream Run、usage/response、ledger/resolved archive 等均接入 |
| 比较 | 每 pair 预费、pending/done/table 先 reserve；宽度与长标量/长 key 内容（含保守 hash 碰撞比较）在 items/sequence/hash/equality 前付 work |
| 消费视图 | Node/get/items/sequence/scalar 有前置 work/分配收费，Node ledger 必须同 family scope；可能被调用者持有的 tuple/Node 费用**保守累计为 resident 到 scope.close**，不把仍被持有的结果提前当临时释放 |
| Source 纯叶 JSON | 由已验证 wire/body 字节数先付 work、reserve 其附加 strict_json 树、canonical/UTF8/ASCII、usage/SHA 临时；原算法仍执行，Canonical 小结果沿原合同返回 |
| 失败/释放 | reserve 先于被保护构建；close 幂等、防负余额，释放 ticket 不退累计 work；预算失败 hook 立即关闭 OWNED scope；异常 traceback/外部引用不等于已 GC，故不作 RSS 释放声明 |

编码沿用旧 `_freeze`，不为 chunk 重写 codec。整块 encode/base64 仅在完整重叠上界已预留后执行，且只读私有 native 副本；原外部输入随后增长不能让该编码器突然读无界源图。构建当时继续逐项 enforcing，并由原后置 guard 防漂移。原 `_freeze` / `_equal` 默认算法 AST 与基线完全相同。

**明确排除**：原 producer `.all()`、DBAPI/SQLAlchemy JSON 解码、旧 `_ColdGraphRead.check/input_bytes` 的全图 C Pickler/memo/bytes、原 typed/storage/model_dump/oracle、原 SQL/授权查询及其原解析工作；模块/控制框架/异常栈/allocator 管理、外部调用者对象和整个进程 heap 也不被此数据 ledger 封闭。保留这些原工作，不能由新增组件局部有界推断整个 G0 时间/驻留峰值有界。新增 owned 视图和 Source 纯叶解析已经另记，未借上述排除漏掉它们。

本测试的 resident/peak/fuel/整数 allowance 仅为合成夹具显式配置。随着覆盖补齐，原先较小 fuel 实际拒绝后，测试改用更保守的有限逻辑 allowance 以完成该数据的正向证明；没有把它迁成任何产品限制、原业务预算或生产资格。

## 错误分类与实际反例

- 容量或新表示能力不足，只能在未发行阶段、原校验仍成功时选 LEGACY。一般 DomainError、cycle、nonfinite、字段/模型变更、撤权、事务失效不被容量 catch 吞掉。
- Inf 接受域疑点用了授权的新 SQLite 最小差分。真实原链是 `producer -> graph.add -> _cold_graph_validate_inputs -> fingerprint(allow_nan=False)`，在新资格前即抛原 ValueError；低/正常新预算均保留它。`infinite-baseline.log` 保留了最初错误假设的失败，不能称 LEGACY 接受。Python [JSON 文档](https://docs.python.org/3.12/library/json.html#basic-usage)也明确这一编码行为；本环境实际原件为主。
- 预算失败曾实际发生，原件按阶段保留。另一次 `Trial software changed` 正是测试期间源码补屏障导致原内容指纹门拒绝；未绕过此门，修订完成后冻结所有 src/test SHA 再验证。
- 既有回归找到 wrapper 过早读 foreign Family/Scope、伪造 Node 缺 allocation 时错误类别漂移；已恢复 exact type/ref/range/sentinel 屏障，新增 nested scope/role/handle 和 none/foreign ledger 零回调反例。

## 实测与独审

最终结果以 `verified-pytest.log` / `verified-junit.xml` 和 `source-hashes.json` 的同一冻结版本为准。`cohort-cost.json` 是实际 SQLite 正向用例的逻辑账目、原 producer 次数、回执一致及最终释放，不是 G0 profiler。

最终 **181 passed, 1 warning in 128.10s**：42 个新 cohort/预算用例、39 个共享计量器用例及 100 个既有组件/SQLite/纯 cohort/诊断/Source 回归。唯一 warning 是既有 Starlette TestClient 弃用提示。Ruff 8 文件、mypy 4 模块及 diff check 通过；运行前后的 8 文件 SHA 完全一致。

正向样例 Source/Generate packet 分别 58550 / 144298 编码字节；消费者检查点 resident 为 44736833 逻辑单位、scope 总 peak 为 46124601，最终累计 work 1213827073。resident 字段是消费者结束检查点，不冒称实际存活字节或独立最大值；peak 包含同时驻留的 resident 与临时 reservation。结束时 `live=resident=issued=0`，两 producer 次数为 `[source, generate]`，`receipt_equal=true`。这些值只描述该合成事实/实际调用序列，不能外推全 G0。

```text
env -u SIM2ACT_TEST_DATABASE_URL -u SIM2ACT_RECORD_PG_CONFIG .venv/bin/pytest -q tests/test_cold_accounted_cohort.py scripts/diagnostics/test_cold_accounted_size.py tests/test_cold_accounted_component.py tests/test_cold_accounted_sqlite.py tests/test_cold_trial_pure_cohort.py tests/test_cold_admission_diagnostics.py tests/test_source_accounting_fact_leaves.py --basetemp=/tmp/sim2act-accounted-cohort-20261021/verified-data --junitxml=/tmp/sim2act-accounted-cohort-20261021/verified-junit.xml
```

覆盖：两族 2/3 aid；任一族超容量、hidden 超限、native hidden Limits 表示不适配仍旧路；小启动预算不抢先遮撤权；预检/构建后的真实 typed mutation；第二族失败无半发行/重试；完整 Slot.reserved_at / Identity.fence / Outcome.sha256 错配；rollback/commit/SQL revoke；发行后 snapshot/fuel 失败双族撤销；共享 DAG/最长路径/模型 extra-private-fields_set；编码前 reserve tripwire、宽 consumer/比较/长 key/scalar fuel tripwire、巨错误名称不复制；旧默认/纯 cohort/诊断/Source 回归。

两份源码独审只做读取、AST/哈希/日志复核，没有运行数据库、测试、Mock 或产品。限定 ACK 不代表 native `_prepare` 两次提交、真实生产 bounds、原 G0 收益或安装批准。本片没有等待或申请新运行窗口。

## 下一资格边界

显式核心组件的接线/预算/回退证明不能冒充完整原生运行资格。当前仍未把本模式接入 `_ColdTrialGraph._prepare`，未移除旧 mutable frontier 或任何 pin，未调整原写锁/租约。未来若安装，需审其具体选路接入位置、其余未迁移根/原读取成本及产品可接受 allowance，而不是用本夹具常数替代合同。没有全域统一上界的结论仍成立；超域兼容原完整路径的规则不变。
