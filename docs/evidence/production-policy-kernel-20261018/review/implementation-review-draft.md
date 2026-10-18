# WIP 实现静审

基线 `842a5b46d52131581edcbfa235ef067cc44b809b`，读取父级唯一写入者当前两个 WIP 文件；尚无冻结/产品执行资格。本审只读代码/Git，不执行产品、pytest、HTTP、DB/SQL、网络或模型，不修改仓库。`implementation-review-draft.json` 记录此次读取字节，不能代表后续修改。

## P2：恢复状态容许不可能由 reserve 产生的并行未决槽与过密历史

位置：`src/sim2act/production_trial_policy.py:204–230`（`_ledger`），后续 `:279–287`（`record_attempt`）。

`reserve` 自身要求所有旧槽 accepted 才增下一槽（`:271`），但 `_ledger` 只要求 reserved_at 非递减，并对“settlement 非空但未 accepted”要求 halted。其接受两个 `settlement=None, accepted=False` 的槽且 halted=false。该输入可由严格类型或 JSON 恢复构造；它并非合法 reserve 历史，但 `record_attempt` 随后只查当前槽存在、未 attempted、未结算和全局非 halted，即可在第二个未决槽返回 attempted=True。这样恢复入口没有保存“上一槽明确接受后才可推进”的同一状态机不变量。

同样，两个 accepted 槽的 reserved_at 相同也可通过 `_ledger`；合法 reserve 必经 cursor ≥60 秒检查，不会产生这种历史。当前时间检查只有 `previous <= reserved_at`。

最小修正：在 `_ledger` 严格要求所有非末槽均 settlement 非空且 accepted；最多末槽可未接受，并保留现有 failed settlement→halt 规则。相邻本 ledger reservation 至少间隔 60 秒。配套定向负测只需构造上述两种 impossible typed/JSON state，分别调用实际恢复/操作入口验证拒绝。该发现是静态控制流推导，未动态复现，不称产品已经实际失败。

## 其余已核范围

- 旧 `admit` 的抽取保留原调用次序：current approval/phase/Run → exact SyntheticOnly + test_only SQLite → verify → 再 approved → generation frozen → 原 synthetic Permit。没有改变旧 `_active` 或安装新 policy；新增 worker_id 为实际 Run 的标量读取。
- 新 check_run 在同 caller TX 使用既有真实上下文，校实际 worker；fresh source 与原 requirements/provider/model/endpoint、canonical account quota、expiry/revocation 匹配。没有把旧 30 秒工程诊断当供应商续签约束。
- `_data` 只接精确受信模型/tuple/原始值，`_typed` 重新验证字段，并复用已审 `_model_data` 拒绝额外/私有/伪 serializer 数据；没有调用 caller 实例 serializer/callback。
- `_bound` 先 scope/owner/project/runtime/原 wire 长度+SHA 约束再返回重复历史；fresh 操作比较实际 approval/stage/Run/runtime/version/fence/worker 与 item。reserve 重复只读，不增槽；record_attempt 第二次拒绝。settle 先原身份，再 fresh 失败降 accepted/halt，保留收到的 usage。UNKNOWN 不归零、不退款，当前实现不提供 UNKNOWN→KNOWN 路径；这不构成自动重试。
- AccountQuotaCursor 与 Ledger 联合返回；类和注释明确只 supplied-state 策略，未来原子 lock/CAS 持久化另接。没有声称当前全局 RPM 或 durable once-only。结构校验不能认证任意外部 ledger 的历史真实性；未来 controller 必须从受信封存/CAS 存储加载，不能允许 HTTP caller 选择旧/空 state。
- receipt 恒 UNINSTALLED_POLICY_ONLY/live=false/dispatch=false/real_source_verified=false；源 producer、有效生产许可、sender 均未安装。生产 resolver 仍 NoReturn；未发现 API/Worker 导入新 module 的接线。

该范围内除上述 P2 外，暂未发现确定 P1/P2；没有据静审称新内核通过。需要修正恢复不变量后再冻结、核必要定向结果；无需旧 UI/长链/取消安装窗口矩阵。

只读定位时曾查尚不存在的 `tests/test_production_trial_policy.py`，得到文件不存在；未运行或收集测试。设计阶段 `/tmp` 拒绝记录见 design-review.md，未再次访问。
