# 最新收窄：只读成本/预算投影的最小短节点映射

适用root最新决定：复用已存在natural_trial*专用合同/七槽ledger/pa_trial_dispatch，仅新增既有账本的只读投影。此前 `minimal-tests-and-reuse.md` 是初始较宽的完整门设计；本文件取代其中需要新scope或完整5mock执行的本轮建议。

没有运行测试或创建Run。本轮不要重做普通任意per-use批准，不放宽literal software qualification、mock guards、原cap/lease/时钟，不跑七槽长例、PB prefix fixture或旧恢复矩阵。

## 投影本身最少新增断言（3个小例足够）

1. **已预留、无settlement**：保留原reserved_requests/envelope、未决slot与未知usage；actual_cost为None，cost_status为UNKNOWN，paid_cap=0不代表已核实际费用。新增字段不能使dispatch_authorized变true，不能创建账本或收费记录。
2. **known失败/超额和partial/unknown**：已知tokens按原数显示；unknown total保持None；失败、accepted=false、halted、initial/current settlement history不丢。None的分量不可为了算总量变0。actual_cost仍None/UNKNOWN，不由token虚构价格；reserve不可退款、不能只算accepted slots。
3. **cold只读、corrupt fail closed**：新Store重复read投影不改DB行/原expiry；primitive非owner或损坏pair仍拒绝，不能回退为空ledger/零成本。若还未有ledger，要明确未预留状态或原拒绝合同，不能自动初始化空账本。

优先把这些字段断言附到现有短fixture，不创建新的Run/executor/权限。对`_public`纯函数形状断言与对`read/audit`真实owner/paired-ledger边界应各有至少一处，避免只测返回字典。

## 推荐现有短节点：按证据等级分开记录

### A. 会计primitive（admission=admitted测试stub，不当自然准入）

来自 `tests/test_natural_trial_budget.py`，可以选下面7个函数（late参数只unknown/overflow）：

```text
test_duplicate_cold_restart_original_key_is_read_only_and_nonrefundable
test_two_stores_concurrent_same_key_one_slot
test_two_stores_different_keys_unknown_first_blocks_second
test_late_or_unknown_usage_retained_halted_no_refund[unknown]
test_late_or_unknown_usage_retained_halted_no_refund[overflow]
test_role_cannot_bind_same_run_and_reserved_cap_is_atomic
test_unknown_original_response_usage_recovery_preserves_history_halt
test_corrupt_pair_and_nonowner_fail_closed
```

共8节点，覆盖同Attempt不重扣、两个Store并发、unknown占用、已知失败/超额、跨role不转移及保守总cap、未知→已知仅恢复账且不退款、corrupt与owner。`role...`明确使用owned synthetic账本边界，不声称全七槽实际发送。不要选择 `test_seven_actual_reservations_stage_binding_nontransfer_no_refund`（真实60秒间隔>=6min）。

如果只读投影不改reserve/settle实现，新增3小例+duplicate/unknown/overflow/corrupt四类即可最先验证；并发2例与cap边界用于必要共享不变量，结果按实际执行列表报告。

### B. 真实自然合同/HTTP负测（不替换qualification）

最小5节点：

```text
tests/test_natural_trial_api.py::test_http_exact_approval_recovery_revoke_and_identity[False]
tests/test_natural_trial_api.py::test_http_exact_approval_recovery_revoke_and_identity[True]
tests/test_natural_trial_api.py::test_actual_claimed_generate_http_admission_denies_no_fee_override[False]
tests/test_natural_trial_api.py::test_actual_claimed_generate_http_admission_denies_no_fee_override[True]
tests/test_natural_trial_runs.py::test_actual_strict_qualification_refusal_is_atomic
```

第一对真实PA/PB canonical approval/recovery/revoke/身份，无模型/Run创建；第二对真实已claim生成Run经过HTTP admission，无客户端fee/free/live override，当前源可因literal qualification严格拒绝或默认LIVE_BLOCKED，账本无部分写；最后一个用`controller` fixture（**不是synthetic**）明确当前软件qualification refusal/全库不变。

这5节点不证明完整P-B source/archive/runtime执行，只证明专用PB合同/API同样受门控。当前源严格qualification拒绝是预期边界，不能为了让历史正例过而patch `_qualified` 或更新software anchor。

可选真实gate.admit短节点：

```text
tests/test_natural_live_admission.py::test_default_real_deny_and_test_permit_is_not_live
tests/test_natural_live_admission.py::test_synthetic_authority_never_works_as_production
tests/test_natural_live_admission.py::test_revocation_irreversible_and_readable_with_no_new_permission
```

它们使用真正canonical gate.admit及明确SyntheticOnlyFeeAuthority，不是primitive的返回SimpleNamespace stub；仍不等于production fee/qualification已通过。此次不必为了投影重复全部expiry/漂移参数矩阵。

### C. Worker.reserve组合：必须精确标注事务范围

现成：

```text
tests/test_natural_trial_budget.py::test_actual_admission_generate_worker_reservation_combination
```

这个短例是真实自然Goal-card生成Run、真正Worker.reserve、原GA_WIRE_RESERVED、真正gate.admit+SyntheticOnlyFeeAuthority；不发transport，取消后的已知晚usage仍保留。适合把新增投影断言放在这里。

**但现例不是同事务原子组合**：它先完成worker.reserve，再在另一个tx读取wire，再调用budget.reserve自己开新tx。因此可说“真实Worker reserve与真实自然admission/ledger顺序组合”，不能说“同tx全回滚已验”。

当前产品真正同tx的代码是：`src/sim2act/worker.py:275–277` 在原reserve事务中调用 `pa_trial_dispatch.reserved(worker,c,run,aid,serialized)`；`pa_trial_dispatch.py:431–449` 用同一c调用budget._reserve，再归档原request；没有嵌套连接。其完整positive历史属于原七槽实际链，不是本轮新执行证据。

若root增加一个真正同tx短负测，应沿这个**已存在hook**进入，验证当前严格natural/qualification拒绝时Attempt/reservation/ctx/charge/request archive全无部分提交，transport sentinel0；不要patch qualification或mock guard争取positive。若严格拒绝发生在Worker构造/claim前，也只计该拒绝阶段，不宣称已触达reserve hook。

如用测试注入把budget._reserve放在ordinary Worker事务中做原子组成实验，必须明确标为“受信测试组合”，不能当产品pa_trial完整准入已验。仅只读投影不值得为此重构Worker或新增scope。

## 明确不选的模块/节点

- `test_pa_trial_dispatch::test_actual_seven_slots_use_existing_worker_and_adapter`。
- `test_natural_trial_deadlines::test_actual_seven_slot_v2_worker_fixed_clock`。
- `test_natural_live_admission::test_actual_mock_generated_app_stage_binding_and_cold_per_use`。
- PB dispatch模块的module级prefix/clone、PB source callback/private-read/UDF/barrier故障模块。
- 整文件通配 `test_natural_trial_runs.py` 的synthetic positive会替换qualification，不作为真正当前源准入证据；只点名上面的strict负测。
- 任意已知受限callback/UDF/barrier模块、七槽或旧恢复矩阵不为本投影重跑。使用显式nodeid，不用宽泛-k误选。

## 最少结果表

报告分四栏：投影新增小例、primitive短节点、真实合同/当前源负测、真实Worker顺序或同tx组合。原始XML/log记录每个实际nodeid、精确SHA及是否stub；一项不能补另一项分母。真实费用始终None/UNKNOWN、paid_cap0、LIVE拒绝；不新增费用凭据/Grant/模型请求。

本建议不要求本轮重新批准或执行新自然软件，不把旧七槽或历史完整PA/PB成果当作当前源重复通过。尚未执行任何新节点。
