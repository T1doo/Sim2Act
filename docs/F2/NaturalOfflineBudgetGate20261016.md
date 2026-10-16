# 自然 P-A/P-B 有限离线批准门与总预算投影

本轮接续 `463167fd308889bf81ae7730310a86da24909897`，执行冻结 `4aaea50d4ea40b7d2425f3c1561bc99b5e3def53`，普通开发分支 `dev/natural-offline-budget-gate-20261016`。已核现有能力，直接复用专用批准和跨 Run 账本；产品只增加 `natural_trial_budget.py` 的 **28 行只读投影**，另增直接测试。没有新合同、第二账本、执行平台、权限、迁移或真实发送路径。

原 [V5 分阶段计划](../sources/V5/分阶段开发计划.md) F2-T01–T03/T06、F3-T05/AT-23 要求冻结材料和 Goal、两路径分别验收、失败及未知用量不丢。原 [产品设计](../sources/V5/平台产品设计.md) 的身份、资源版本、软件和授权修订边界保持。本轮是有限工程切片，不签完整 F2/F3/R0 或真实语义通过。

## 复用的离线最小门

| 要求 | 已有实现及本轮边界 |
| --- | --- |
| 专用批准合同 | `natural_live_admission.TrialContract/v2`、`PBTrialContract`，原 prepare/consent/approval/revoke/stage API；绑定 principal/project、P-A/P-B 类型、阶段键、intern-s2、完整两份 TXT 与 Goal 版本/指纹、软件/授权指纹、有效期 |
| 有限总上限 | 原 generate/source/cold 最多 3/2/2 槽、合计 7；每阶段 envelope 64000、跨三 Run 合计 192000、output 7168、paid cap 0；原 300 秒 Run、30 秒 lease 和账户节流不变 |
| 原子预留 | 原 `Worker.reserve` 事务内调用 `pa_trial_dispatch.reserved` → `budget._reserve(c)` 和原请求归档；继续使用原 Attempt/reservations、项目/账户锁及 paired seals，没有另造 sender |
| 不重复扣或重发 | 同 key 仅返回历史 `duplicate=true/dispatch_authorized=false`，不重新 admit；原 `reserved` 拒绝拿 duplicate 取得新发送，原 durable send marker 禁止重复 IO |
| 未知与失败 | 未结算/unknown 槽继续占额并阻止新发送；已知失败、取消后晚 usage、超额和未知核账保留原记录与 settlement history，不退款或清零 |
| 默认拒绝 | `goal_applications.check_provider` 仍拒自然族套用旧 literal generation activation；`natural_spec_runtime.enabled` 仍要求 test_only + mock + 明确 MockTransport。生产 fee/account/sender 未注册，LIVE 持续拒绝、真实额度 0 |

这是**已有固定三阶段七槽 trial**。普通任意材料、任意多次 per-use 的滚动批准没有新增；旧单生成 Run 的 `generation_approvals` 不能冒充跨 Run 自然总账。literal 软件资格和 anchors/pins 未改、未 patch；当前不合格软件的严格拒绝仍有实际负测。合成 Permit 仍 `SYNTHETIC_ONLY/live_allowed=false`。

## 新增可查账内容

现有认证 GET `/api/projects/{pid}/natural-trials/{key}/approvals/{approval_key}/budget` 继续走原 owner、材料/Goal 与 paired-ledger 检查，新增 `budget_projection`：

- 总计及各阶段的 limit、held requests/token envelope、数学上的未预留容量、原 Run ID。
- 未决 usage 请求数和已知未接受 tokens。所有已预留槽都参与 held，成功、失败、unknown 不释放额度；未知 `total_tokens` 仍为 null，部分已知 usage 仍在原 ledger。
- `money={paid_cap:0, actual_paid:null, currency:null, status:"UNKNOWN", fee_verification:"NOT_LIVE_VERIFIED", live_allowed:false}`。

未预留容量不是发送许可；原 HALTED/RECONCILING 和全部发送门仍有效。token envelope 是原字节保守预留，不是实际 tokenizer 或货币。**真实费用没有被核实，不能把 mock、known tokens 或零真实请求换算成真实费用 0。** 可计价余额/单价/真实免费权益与强制不可收费机制仍未实现。

源 AST 比对确认所有旧 class/function 不变，只有 `_public` 多一个返回字段和新增纯读 `_projection`；原 approve/admit/reserve/settle/guard 算法及配置均未改。旧批准因软件漂移需要原重预检，投影不恢复或升级任何授权。

## 实际验证及独审

精确 `4aaea50d` 上，作者两批各 17 PASS，共 **34 个独特用例**；独审重复新增同 17 PASS，不相加为 51。原始命令、JUnit、日志和逐例合成 JSON 已归档。

| 批次 | 实际范围与结论 |
| --- | --- |
| 新增 17，26.65 秒 | pending/unknown/rejected/overflow 的非退还投影与冷 Store；两 Store 争最后 requests/token 额度；同 trial 三个不同 Run 累计；P-A/P-B 真合同、真实 gate.admit 配 SyntheticOnlyFeeAuthority 和 ASGI 预算 GET；缺批准、真实已保存 Goal v1→v2 漂移、过期、撤销全部拒绝且 accounting rows 不变 |
| 既有短 17，27.65 秒 | 8 个账本 primitive；5 个 P-A/P-B API/严格资格负例；3 个真实自然准入；1 个真实 Worker 预留与自然账本的顺序组合 |
| 独立新增同 17，24.19 秒 | 独立私有临时库重跑；核 17 份唯一 JSON、源码前后字节及旧算法 AST，有限通过 |

并发最后请求额度：仅一个 contender 成功，held 从 2→3，另一个 BUDGET_EXHAUSTED。最后 token 额度：仅一个成功，held envelope 54816，另一个 BUDGET_EXHAUSTED，未越阶段 64000。三 Run 同 scope/trial_key 累计 3 槽、3372 envelope、24 合成 known tokens，不因换 Run 重置。**这三项使用明确的 primitive admission stub、合成 fixture 时钟和真实 SQLite Store，不能称完整自然模型运行或 PG 并发验证。** 没有真实等待七槽的长链，也未放宽生产时钟或租约。

旧 Worker 组合实际先 `worker.reserve`、再另一个事务 `budget.reserve`，仅证明真实 Attempt/GA_WIRE_RESERVED 与真实自然准入的顺序组合及取消后晚合成 usage 保留；**不能签成本轮同事务 Worker 完整链实测**。真正同事务产品挂钩本轮静读/AST 核验，不为证明它修改资格 pin 或注入资格旁路。

Ruff 在最终源上通过。初次 fixture 导入造成 3 个 F811，已在实际 pytest 前修正。`mypy src` **未全绿**：当前 90 源文件报 4 文件 7 错；以 Git `463167fd` 的 `src/pyproject.toml` 自有静态快照复核，原诊断逐字相同，修改文件没有新增诊断。基线与当前原日志均保留，不能称历史 5 错或类型检查通过。

## 交付及保留限制

[原始证据和独审索引](../evidence/natural-offline-budget-gate-20261016/README.md) 包含两批作者结果、独立重跑、34 用例去重、前后源 hash、AST、基线类型检查及拒绝原件。后续交付提交只追加说明/证据，执行代码保持上述冻结；最终 SHA、远端实际相等及未提交/未推送差异另在 checkout 外记录。

没有真实模型/账户探测、凭据生成/配置、新费用或持久权限；没有新自然七槽业务执行、锁/恢复矩阵、受限 callback/UDF/barrier 诊断、Windows、PG、原生浏览器、真实语义/人工验收、远端 CI 或部署。上述均 NOT_RUN。普通启动仍要求 PG，SQLite 是显式合成测试。main、旧分支、候选 ZIP、旧两探针 FAIL、旧 P-A 最初异常未知及旧满盘末次独审缺口均保持，不以本轮覆盖。
