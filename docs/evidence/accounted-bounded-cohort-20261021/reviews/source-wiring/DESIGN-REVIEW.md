# SQLite accounted cohort：来源与最小接线设计独审

结论：**CONDITIONALLY_FEASIBLE_DESIGN_ONLY**。可继续实现显式、未安装的私有 cohort；本报告不是代码完成证明、产品全域 bounds、性能改善或任何执行窗口批准。独审仅阅读源码，产品导入、测试、DB 打开、Worker、Mock、PB/G0 均为 0；未修改仓库。

审阅基线：`e617498a5d28b9bbfa4605c61546d57f02446144`。审阅对象为父侧设计消息和下列源码，不存在已冻结的新实现可签字。

## 必须闭合的接线

1. 单独的 SQLite/test-only 显式 cohort，内部各调用原 `_graph_stage_accounted(..., _owned=None)` 一次，保留完整 Source 与 Generate 原始结果，原 SQL/typed/full guards 不改。`pa_trial_dispatch.py:1569–1633` 在返回前已 pin 完整值及执行 full guard。不得先通过旧 `_AccountedScope.issue`（cold_accounted.py:244）再暂存，也不得复用旧 `_OwnedPrewriteMode._completed`（566）作未发行准备：前者调用 producer，后者立刻发行。
2. 两 role 完成、资格/预算投影及与原完整 pin 的比较均完成后，再执行原 full guard，整族只选择一次 OWNED 或 LEGACY。任何 handle/family 发行前必须没有外部可见的半族；Source 拟合而 Generate 超额时，释放未发行 prepared 及临时包，只返回已有原始结果，不重跑 producer。原始事实不能从调用者提供的 packet/digest/“已验证”布尔值导入。
3. 容量和确属表示兼容性的 unsupported 只能是新投影器专用私有异常；原 `_Rejected` 同时用于容量、cycle、nonfinite、未知类型，不能按其类型/message 统一 fallback。原 DomainError、原验证失败、cycle、nonfinite、mutation、scope/线程/stop/transaction 漂移均闭合；发行后任意失败闭合，绝无 LEGACY 重试。预算提前停止不证明未扫描尾部合法，LEGACY 必须仍走完整旧验证。
4. 当前 `_prewrite_mode`（676）要求旧 mode 精确类型；runtime `_prepare` 的 2718/2731 是逐 role producer 调用。最小实现应以独立显式 cohort/prepare 接口交付，保持默认 `_prepare`、旧 mode 及原授权边界不动。未来若接入默认 runtime，属于另一次精确审查。

## raw→prepared 的最小合同

- 所有新分配前收费：容器容量、边/键、工作栈、memo/active、RowMapping sidecar 与字符串安全索引、规范化键、typed 字段投影、节点及 wire 编码缓冲。不能先用 `_cold_graph_row_storage`（natural_spec_runtime.py:1679）重建 lookup，再对结果计费；需要直接按 exact native storage 逐项扫描，foreign index 项虽不复制也须收费，绝不调用其 key 的 hash/eq/str。原 keys、完整 data、所有安全字符串 index 含 hidden position 均保留，不只可见 18/13 列。
- 固定 Pydantic 类、nested 允许类、exact `__dict__`/字段表/fields_set、extra/private、缺项/多项及容器/数值类型，须达到 `_trial_typed_storage`（natural_live_admission.py:1274）已有合同；两个 omit 仅 BranchCondition.value=None、WorkflowStep.when=None。直接存储适配不得 `model_dump`，也不得隐藏恶意额外字段或将 list/tuple 漂移归一化。
- 共享 DAG 必须 memo 且逐边收费；cycle 明确失败。字符串长度计量不能先完整 `.encode()`；大 int/bytes/base64/JSON 的开销必须先算/保守 reserve，不依赖已有平台极限。转存必须保持 numeric/container exactness。
- 现 `_fixed`（692）返回 model_dump 的树，直接存储适配可能保留共享而改变节点排列/encoded/digest。`_equal` 合同是忽略共享与字典顺序的类型精确语义比较（_cold_accounted_values.py:222），不是 packet 字节相等。应显式采用新 prepared 命名空间/版本，或证明旧编码兼容；不可把语义相等推成旧 digest 相同。所有值仍需对原 producer 完整 pin 比较，身份/摘要不是可变全扫描替代。

## allocation ledger 的实际覆盖面

至少分开不可回退的累计 work/visit 与可释放的 live/reserved allocation。释放 temporary 不能重置工作计量；释放必须在最后引用真正消失后，不能 `_freeze` 返回就释放仍被 `_Node` 引用的 packet。

- `_capture`（703）先 row 字典、sidecar、typed 列表/元组，再 `_freeze`。现有 `_freeze`（_cold_accounted_values.py:42）有 keys tuple/set、done/active/heights、nodes、flat、完整 base64、JSON chunks、ASCII chunk、join 输出同时重叠；仅最终 encoded_bytes 不证明复制前预算。
- `_AccountedScope.issue:278`、旧 `_completed:574` 的 expected packet；`_same_native:929` 的每次 native snapshot；`_source_slot:362` 的 typed storage；`_archive_chain:1141` typed storage、1144 ledger packet、1146 receipt/request/response packet均须覆盖。后两 packet 与整族 packet 同时存活。
- `_equal`（222）会创建 pending、pair memo、items tuple/dict、sequence tuple 和 _Node；pair 数最坏须按两 packet 节点对保守约束，而不是只给每包各自额度。`_Family.actual/chains/ns_reads`（885/889/906）、`_usage:980` 的 wrapper/tuple/dict 也不能被“所有临时都已覆盖”的声明遗漏。
- `_source_exchange:1091` 会 strict_json、response_archive、normalize_usage，产生 JSON/canonical 和 decode 缓冲；要么纳入明确且事前 reserve 的原 body 局部有效界，要么明确排除于 ledger 声明。不能只包 `_freeze` 就声称整个 scope 分配有界。
- `_LegacyOracle`（373）仍创建 dict/list/tuple/typed snapshots。保留的原 full guards 调用 `_trial_pure_data:1245`（只有 active、无 memo）及 `_trial_typed_equal:1172`（无 pair memo），共享 DAG 可重复展开。这些原逻辑不得为 ledger 方便而删除/放宽。

因此新 ledger 能证明的是明确列举的新 accounted 组件额外工作/保留分配；**不能据此宣称整个 scope/RSS、原 fullguard/producer、数据库 materialize/JSON decode 前内存或 RowMapping parent/foreign key 的完整可达 heap 都被封闭**。DB 和平台局部限额不是部署无关的产品 bounds。

## 必要的后续验证（本独审未执行）

纯局部验证应覆盖：所有收费的恰好边界/不足一单位、copy 前拒绝；Source 拟合/Generate 超额且每 role producer=1；正常 joint issuance 与发行后失败不 fallback；原 DomainError/mutation/cycle/nonfinite 不 fallback；巨大 foreign-index 不触发 foreign callback；hidden data/index alias 不丢；共享 DAG/深度/容器数值漂移；Pydantic 缺额外字段/private/extra 与 model_dump tripwire；两 family 加两个 snapshots 的共同存活峰值与 finally 释放；编码/digest 版本兼容边界。此清单不授权 G0、Worker、Mock 或完整 PB。

没有从只读源码发现该显式未安装 cohort 在设计上必然不可实现；上面各项是精确补丁必须满足的条件，不能以设计 ACK 代替实现证明。
