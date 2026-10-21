# e617 候选代码：来源与接线第二独审

结论：**STATIC_SOURCE_WIRING_ACK_UNINSTALLED_ONLY**。在本次阅读到的候选字节中，未发现来源/发行/兼容接线方面未关闭的 P1/P2。预算常数的保守性、数值上界和所有分配覆盖充分性由另一独审负责，本 ACK 不覆盖该部分；也不是运行或安装批准。尚无父侧最终冻结测试证据，本报告不宣称新测试通过。

独审行为：只读源码、git diff、既有失败日志；产品导入、测试、DB 打开、Worker、Mock、PB/G0、compiler 均为 0。只写本 /tmp 报告，仓库修改为 0。父侧 baseline e617498a5d28b9bbfa4605c61546d57f02446144；阅读时补丁未提交。

## 已核实来源与发行顺序

- cold_accounted.py:692 `_select_cohort` 直接依次调用原 `_graph_stage_accounted`，Source、Generate 各一处，未传 `_owned`，没有通过旧 `issue()` 或 `_completed()` 重跑/提前发行。原 pa_trial_dispatch.py、natural_live_admission.py、natural_spec_runtime.py、_cold_accounted_values.py 没有本补丁差异，原 SQL、完整 producer/full guards、默认 runtime `_prepare` 均未接入新 cohort。
- 两 producer 返回后才将原 facts 加入 assertion-only `_LegacyOracle`，执行 `assert_current()` 的原全图/typed guard。预算捕获同时比较原完整 pinned value；两个 role 全部成功且末次 `assert_current()` 成功后，才在容量 catch 的 else 内登记 handle/family。没有半族 route。
- 唯一 LEGACY catch 为新私有 `_Capacity`（含 `_Unsupported`），只包未发行准备。catch 内再次原完整 guard 后释放候选包/关闭预算，返回同批原 facts；没有 producer 重读。原异常不被转换。登记、associations、发行后 current、context yield 均在 fallback catch 外。
- `_bounded_cohort:818` 在 finally 关闭 mode 与预算。发行后 `_snapshot:1085` / `_compare:1097` 捕获异常关闭 mode；registry 两族同时失效。原无 allocation 分支仍分别调用同一 `_freeze` / `_equal`。

## 完整值及命名空间

- `_capture_bounded:765` 强制原四元组、Source2/Generate3、NS reads2/0、chain6/NS read5、exact Slot/Capture/BodyArchive、完整 Run18/Attempt13 字段。schema 检查是完整 len+全部字段匹配，不是投影白名单后丢掉额外字段。
- `_Projection.row:339` 直接取 exact native RowMapping 的受信 parent、完整 data tuple、完整 index dict、keys list；扫描 index 不调用 foreign key 的 hash/eq/str，只收 exact str/quoted_name 安全索引但对所有 index 项计工作。全部 hidden data 复制进 sidecar，非仅可见业务列。keys/data 通过同一 memo 复制；安全 index 每次重建，与旧 helper 每次重建一致。
- `_Projection.copy:243` 只接 exact 原生类型及固定 nested Pydantic 类。原 storage 的 raw/fields/fields_set、extra/private 检查保留；仅两处已有 omit；不调用 model_dump；先 active cycle 检查、再 completed memo，保留共享值、list/tuple/numeric 类型与 quoted_name tag。预算限额不是授权。
- 新 envelope schema `accounted-family.pre.bounded.v2` 与旧 schema 分开；旧原图输入、pickle、pre/post/origin/software namespace 不改。原 pinned value 用类型精确语义比较，不宣称共享形状相同或旧 digest 字节兼容。
- `_source_slot` 新 snapshot 分支、`_archive_chain` 两个同时存活的 snapshot、`_same_native` 的可见 RowMapping 投影均只针对 allocation 不为 None 的新实验。实际 dispatch/archive 调用者仍包原 typed/full guards；原 oracle 仍保留原 facts、旧 pin 与完整 typed 比较。

## Inf 疑点的纠正

初读时曾依据当时新增测试 `test_legacy_baseline_with_unconsumed_infinite_result` 的预期，提出低预算 LEGACY 可能接受 Inf 的兼容疑点；该测试当时没有通过，不能把预期当实际行为。父侧提供的真实失败原件 `/tmp/sim2act-accounted-cohort-20261021/infinite-baseline.log` 显示：`_select_cohort` 首个 Source producer → pa_trial_dispatch.py:1628 `graph.add` → natural_spec_runtime.py:1852 `_cold_graph_validate_inputs` → :1661 fingerprint → db.py:697 JSON allow_nan=False，抛出原 `ValueError: Out of range float values are not JSON compliant: inf`。预算捕获未到达。

据此，该 P2 不成立。现测试改为正常/低 node budget 两参数，均期待原 ValueError，且 `_capture_bounded` tripwire 必须不到达。独审只阅读此测试和上述初次失败原件，没有执行修订测试。投影器自身 nonfinite/cycle 仍不是 `_Capacity`；不得在文档把旧 ValueError 写成投影器产生的 DomainError。

## 有限边界

这是 explicit test-only SQLite cohort，默认 runtime 不安装。ledger 模块也明确是逻辑 allocation costs，原 SQL decode、旧 full guards/oracle、RSS/GC/RowMapping parent/foreign transitive heap 不在证明范围。其他 reviewer 的数值/保守上界结论和根侧最终实际测试原件，仍须与最终冻结哈希共同封存。本报告不能转换为产品规模 bounds、G0 性能改善或任何 PB/Worker/模型执行许可。
