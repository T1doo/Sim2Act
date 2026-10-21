# 同事务 Cold 完整 owned 消费闭包：未成立的精确见证

本片结论：**未完成完整 owned 迁移，不具备删除 typed cohort 或启用替代路径的资格。**
本次交付是两项真实 SQLite 反例及逐消费者闭包审查；没有运行完整 `_prepare`、任一
`trial.commit`、G0、Worker、Mock 或真实模型，也没有获得新的成功尾段或性能结果。
这不证明所有权优化不可实现，而是证明现有两族发行不能作为完整结算的所有权证明。

基线完整 SHA：`229ab325b3f249bd920c9b1d793ca3bb8e17d278`。
本片 `src/`、`scripts/` 无差异；原 BEGIN IMMEDIATE、连接、scope、renew、heartbeat、
授权/撤权、SQL 读集、Run/version/fence/stop 和各期限检查均保留。T0/T1 拆事务提案
暂停，不能以旧设计 ACK 启用；不新增“所有 Run 列变化都拒绝”的门。

## 可复现的反例

`tests/test_cold_owned_settlement_closure.py` 使用既有 `sql_facts` 隔离 SQLite 和
`native_segment`：原 Source/Generate producer、原事务和真实 `_ColdGraphRead`，
已经发行 OWNED 两族；随后从原 `_approved` SQL 路径取得真实 Approval，调用原
`_graph_trial_produced`。没有用 DTO 或替身实现 producer/guard。

两种情况分别普通赋值 `model.approved_at -= 1`、修改 producer 返回 raw 的同一字段。
每种情况均证明：

1. cohort 保留的就是原 model 和返回 raw，初始业务指纹相等，原完整 typed pin 通过。
2. 修改后完整 CGR `check` 仍通过，原 model/raw 业务指纹已经不同。
3. 原 `_graph_trial_models_pin` 拒绝，精确消息为
   `Typed trial storage changed after its complete raw proof`，graph/mode/scope 全部失效；
   原 scope 退出拒绝该失效状态。测试不重置 scope 以获得通过。

因此删除 typed pass、缓存其 PASS、或仅以已有两族 handle 身份替代它，会漏掉本来
被拒绝的意外内容变更。这里没有替换 runtime 函数，也不把任意进程内代码攻击作为
额外产品安全契约。真实边界是仍被消费者读取的原可变引用。

最终冻结测试 SHA-256：
`a4b3af0d09f5e0573c70fa307976bf2722575189fc0b15312178301aa3a8f310`。
前后 manifest 完全一致；最终 **2 passed / 3.06s**，Ruff 通过。两种参数是两个反例，
不是两次完整结算。一次既有 Starlette/httpx 弃用警告保留于日志。

开发记录亦完整保留：首跑 2 failed / 3.12s，错误是测试末尾误读不存在的 `mode.closed`；
改为真实 `active` 和 `scope._active` 后 2 passed / 3.05s。再把 `object.__setattr__`
改为普通模型赋值后得到上述最终 2 passed / 3.06s。三个运行不合并为六项独立覆盖；
初次失败不是产品失败。所有运行均无 Mock/Worker/transport。

## 必须一起迁移的内容消费者

以下是基于当前源码的具体边界清单，**不是已完成的穷尽证明**。完整只读独审见
`raw/` 内两份 SOURCE 审查。行号均对应基线源码。

| 内容族 | 当前 producer / 保留的可变源 | 尚未迁移的实际消费者 |
| --- | --- | --- |
| Trial / requirements | `_prepare:2719` 的 PBTrialContract、EvidenceRequirements；binding.contract；admission-prefix raw | `_typed_parameters`、stage/recipe helpers、policy `_run_check_from_facts:327` 的原业务 fingerprint、第二门 `_requirements` |
| generation / extraction / use | `_ColdBindingGraph:1912` 保存 FrozenRunContract、ExtractInput、GoalCardRunSource、CommitInput、AppManifest；release origin 和 binding/draft | `_cold_trial_binding:2271`、两个 stage tuple、`_graph_stage_current`、resolver、`_fields:2673`；exact-type/字段和原 model_dump 仍读取原值 |
| Ledger / cursor / proof | `_graph_journal_state` 的 Ledger、AccountQuotaCursor 与 raw | prefix source、完整 Slot/Identity/Outcome、archive 关系、budget scope、`_typed_parameters` |
| fresh Approval / phase | 每次原 `_approved` / `_saved` 返回值及 lexical triples | Run 谓词、authority/run/stage/approval-key 比较、semantic-authorities 与其业务 fingerprint；本片反例直接覆盖此别名问题 |
| SourceVerificationResult | `_source_value` 保留 live_source 和 source_record | `_model_source_key`、expires_at、`_dump`、commit output、`_typed_parameters`，不可用旧授权结果替代 fresh producer |
| RunCheck / FrozenRunContract / Limits | `_context` 原 model/raw；第二门及 commit 新 frozen/declared limits | deadline、三项业务 fingerprint、原输出和最终 finite；局部改 `_recheck` 不会移除外层 `check` 的重复遍历 |
| binding / call / receipt | 原 dict/list/RowMapping、call/meta/step/operation、counter reader 和新回执根 | `_cold_receipts`、完整 SQL/receipt 验证、Attempt readback、parse/schema/usage、第二 prefix、第二 commit、正常 scope 和最终时钟 |

`_trial_typed_hold:1371` 实际存储 `(expected, model, raw)`；没有所有权转移。
`_graph_trial_produced:1399` 返回普通 dict，并非不可变 capability。
`_fields` 汇集多族 raw 引用；冻结外层 dataclass 或单个 Pydantic model 不能消除这些别名。
已有 native accounted 纯值只覆盖声明的 Source/Generate 部分，不覆盖整张表。

## 发行前容量的具体断点

当前 `accounted_candidate.choose` 在 `_prepare:2810`，早于完整 `_fields`、第一门
context/manifest/source authority、新 source、第二门 fresh 输出及最终 context/output。
现有 qualification 虽已计入两 packet、原 Ledger、mutable frontier、固定 continuation
和精确 future raw roots，**没有**为所有后来 typed packet/schema view/规范输出及
临时比较空间提供完整 field-lineage/call-count/同时驻留证明。

future root 的名字获准不等于其 typed 发行或分配获准。现有 arena 发行后已封闭；
不能临时扩大、失败后回退、重放 producer，也不能将夹具 allowance 变为产品上限。
把完整 frame 的复制简单插在 `_prepare` 尾部，会在已经发行之后才发现容量不足，
同样不满足“一次选路”。

下一次实际候选必须同时闭合两项，而不是再交一个 `_recheck` 或两个标量原型：

1. 在统一发行前完成上述完整内容的字段/消费者映射。已有输入与后续 SQL 输出分开：
   对后续固定派生值逐项给出来源、字段及次数上界；不能证明容量的输入在任何新
   发行前选 LEGACY，复用原 producer 同批结果，不能提前执行后面的 SQL/业务动作。
   后续仍在原位置执行完整 producer/授权检查，并证明 fresh 值如何绑定同一已资格化
   内容；不得通过缓存旧批准使“容量有界”。
2. 私有 exact schema 的 owned record 必须成为全部纯内容消费者的唯一来源，包括
   stage 嵌套引用、context/source record、原业务 fingerprint/export 和 receipt 关联。
   不解冻出第二份可变业务来源；原协议输出所需临时序列化与长期消费者明确分离。
   固定类型、全部字段、两个既有 None omission、list/tuple、bool/int、共享 DAG/cycle
   规则、原 bytes 与回执不变。没有证明无逃逸的根仍由原完整检查保护。

这里尚未给出全区间 lineage/次数/预算和全部消费者实现，故没有提交 runtime 候选，
也没有用独审结论替代实施资格或性能验收。上述是同一结算任务的未闭合条件。

## 原位动态门与实测范围

即使内容未来全部 owned，`_base` 两次完整检查间的动态 state、每个 SQL/授权返回检查、
连接/事务/scope/thread/epoch、worker/settings/transport/current binding 内容、新鲜
model/max_output_tokens、Run/version/fence/cancel/stop、原时钟采样和最终 deadline 都
必须保留。私有 manifest 不进入旧 pickle/raw/pre/post/origin/software 签名命名空间。

| 本轮要求项 | 实际状态 |
| --- | --- |
| Approval 原 model 与返回 raw 意外 mutation | 两个真实 SQLite 反例通过；原拒绝及 scope 失效得到验证 |
| 完整 owned consumer 无逃逸与发行前预算 | **NOT PROVEN**，本片定位上述精确缺口 |
| 完整成功 prepare → 第一 commit → receipt → 第二 commit → 正常 scope | **NOT RUN / NOT PROVEN** |
| 完整候选撤权/期限/跨 scope/每写点回滚反例 | **NOT RUN**；无候选，不能拿既有局部测试冒充 |
| G0 / Mock / 真实模型 / 性能收益 | **NOT RUN / NO CLAIM** |

上次真实尾段观测仍以 `../tail-cost-window-20261021/` 原件为准。原 at 比 lease 晚
1.171571493 秒支持该比较过期，但不是原短路轨迹；本次没有改写此结果。
本片没有新 grant、后台进程、外部实例或待清理窗口。隔离测试连接由原 fixture 关闭。

`raw/manifest.json` 逐件保存压缩前后 SHA-256；原始测试失败、最终成功和两份只读
源码独审均保全。最终 Git/远端回执由提交后核实给出，不能从本文件自指推导提交 SHA。
