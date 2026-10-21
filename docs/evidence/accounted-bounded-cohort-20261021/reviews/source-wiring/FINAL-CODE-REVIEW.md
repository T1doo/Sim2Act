# 最终冻结增量：默认路径与接线独审

结论：**FINAL_STATIC_SOURCE_WIRING_ACK_UNINSTALLED_ONLY**。当前来源/默认路径接线范围无未闭 P1/P2。此报告追加前次 CODE-REVIEW，不覆盖 monitor 对预算数值及所有 allocation 覆盖充分性的独立审查；不构成默认 runtime 安装、产品全域 bounds、运行测试通过或 PB/G0/模型执行批准。

基线 e617498a5d28b9bbfa4605c61546d57f02446144。仅阅读源码、git 差异，以 stdlib AST/hash 对账，不导入产品，不执行测试/DB/Worker/Mock/PB/G0。仓库写入 0，仅本 /tmp 报告新增。

## 默认 allocation=None

1. `_cold_accounted_values._freeze` 和 `_equal` 的完整函数 AST 与基线逐项相同。新增 `_Node.allocation=None` 及 `_node_ref` 只在非 None 时验证 ledger 并收费；None 下 scalar 的原 float.fromhex/原标量返回、items 的键/值顺序及完整映射、sequence 的元组、get 的原缺字段错误均保留。packet 编码、marker、digest 和原 comparator 本体未变。
2. `_Value._check` 新增 ledger 必须是其 family scope 的同一对象。旧 scope 初始化 `_allocation=None`，旧发行 packet 创建的节点也为 None，故该条件没有放宽或改变默认合法 view。新 OWNED scope 禁止剥离 ledger 伪造 view；测试含 None/foreign ledger 伪造而不调用 foreign callback。
3. `_snapshot` / `_compare` 的 None 分支直接执行原 `_freeze` / `_equal`；`_source_slot`、`assert_upstream_run`、`_LegacyOracle.assert_run` 的旧 typed/完整 raw 分支保留。`_archive_chain` None 分支仍原 typed storage+typed_values+两个 freeze，提取公共 tail 后比较落入同一原 equal。旧 Source 业务函数提取为 `_source_exchange_value`，忽略函数名后完整 AST 与原 `_source_exchange` 相同；None wrapper 直接调用一次，不增加 Source JSON reservation 或新的业务调用。
4. natural_spec_runtime.py、natural_live_admission.py、pa_trial_dispatch.py、natural_source_archives.py 四个文件与基线全字节相同。因此默认 `_prepare`、原 SQL、原完整 guards 未启用本 cohort 或新分流。

## 新显式 OWNED 分支

新增 ledger-aware Node/get/items/sequence/scalar 和 consumer view 保守保留收费；scope close 清除预算，`on_failure=self.close` 将动态 view 的容量失败也关闭两族。SourceJSON 临时 reservation 只包新 allocation 非 None 分支且 finally 释放；archive 的 snapshot root 显式携带相同 ledger。native key hash 预费在新 budget projector 内，不修改旧 serializer 或原 SQL row storage helper。

前次已核两 producer 各一次、两族暂存后联合 route、发行后无 fallback、原 fullguard 不删除的结论继续成立。新 scope 仍只有显式 SQLite/test-only context 可创建，未接入默认生产路径。没有新增平台资格需求；原有产品规模 bounds/全闭包迁移等未关闭条件仍按原文保留。

## 最后三个 Slot 用例

只读核 `test_budgeted_slot_comparison_covers_all_nested_fields` 的三参数分别替换 reserved_at、嵌套 identity.fence、嵌套 settlement.response_sha256，沿实际 `_source_slot` snapshot+完整比较期待 DomainError；还断言 mode inactive、两族 registry 清空、live/resident 为 0。它们检查的不是仅 aid 相等。此处确认测试内容，未自行执行，也不把正在进行的根侧回归计作通过。

Inf 历史口径继续按前次报告：原首 Source producer 的 graph.add/fingerprint allow_nan=False 已 ValueError 拒绝，先前低 cap 可接受的静态猜测不成立。保留原失败证据，不冒称新投影器产生该异常。

完整冻结 SHA 与静态 AST/字节对账布尔结果见同名 JSON。最终实际回归原件由根侧另行封存；本独审执行产品/测试/DB 均为 0。
