# 自然有限离线批准门、非退还总预算与费用未知投影

执行冻结 `4aaea50d4ea40b7d2425f3c1561bc99b5e3def53`，基线 `463167fd308889bf81ae7730310a86da24909897`。见 [交付报告](../../F2/NaturalOfflineBudgetGate20261016.md)。本目录 `SHA256SUMS` 按相对路径覆盖除自身外的全部文件；没有 DB、venv、私人配置、凭据或模型传输记录。

现成的 P-A/P-B trial 合同、API、paired ledger、Worker/reservation 和默认零 LIVE 门直接复用。产品新增纯 `_projection` 和一个 `_public` 返回项（28 行），原所有 class/function AST 相同；不把这次投影说成新建批准或通用逐次 per-use 余额。

## 当前源码及执行命令

- `source-before.json`：HEAD/clean、11 核心源 hash、真实 SQLite 测试范围；含初次 fixture 导入的三个 F811 声明，修正后才跑 pytest。
- `COMMANDS.json`：根实际工具调用的参数/环境及退出码元数据。stdout/JUnit 是下列原件；命令元数据不是进程 argv 的独立捕获。
- `author-test-and-source-proof.json`：两批完整实际 case、34 唯一用例、11 源 before/after 一致和旧算法 AST。此文件是处理后汇总元数据，其 mypy 字段在基线比较完成后更新；原始 XML/log/逐例 JSON 未改。
- `existing-contract-review.md`、`existing-contract-proof.json`：独立先读 463 现有专用合同和实际缺口；明确固定三阶段七槽、非任意滚动 per-use、真实计价/资格未实现。
- `independent-static-review.md`、`independent-static-proof.json`：冻结 4aa 静审，实际 Goal 漂移已修；没有以早期 WIP 采样代替冻结证据。
- `independent-test-mapping.md`：短节点及 primitive、真实准入和 Worker 顺序组合的等级边界；不选七槽长例和受限诊断。

## 作者两批：34 个唯一用例

`author-new.xml/.log`：17 PASS、0 FAIL/ERROR/SKIP，RC0，26.65 秒；`author-new-data/` 内恰 17 份唯一合成 JSON，排除 pytest current symlink：

- 4 份 `PROJECTION.json`：pending、unknown、known rejected、overflow 的预留都保留；新 Store 冷读和原 key 重复不写 accounting rows，不重新 admit。unknown total_tokens 为 null，已知未接受 8/2025 tokens 保留；money actual_paid/currency 均 null，UNKNOWN/NOT_LIVE_VERIFIED/paid_cap0。
- 2 份 `CAPACITY_RACE.json`：真实两个 SQLite Store、同一个 ledger 争最后 requests/token 容量，各一成功、一 BUDGET_EXHAUSTED。使用明确 primitive admission stub、合成时钟和原 heartbeat，不是自然模型或 PG 并发验证。
- 1 份 `CROSS_RUN.json`：同一 scope/trial_key 下三个不同合成 Run 累计 3 槽/3372 envelope/24 known synthetic tokens，不换 trial 重置；同样是 primitive 证明。
- 2 份 `REAL_CONTRACT_HTTP.json`：真实 P-A/P-B canonical contract、原 approve/gate.admit 配 SyntheticOnlyFeeAuthority、ASGI GET 预算投影和原 key 历史幂等；不调用或绕过 production qualification。
- 8 份 `REAL_CONTRACT_REFUSAL.json`：P-A/P-B × 缺批准、已保存 Goal 真实 v1→v2 漂移、过期、撤销，原合同预留全部拒绝、accounting rows 不变。`actual_goal_drift` 保存实际 PUT 返回。

`author-regression.xml/.log`：另 17 PASS、0 FAIL/ERROR/SKIP，RC0，27.65 秒，与 new 17 无交集：8 个 primitive、5 个真实合同/当前资格负测、3 个真实自然准入、1 个真实 Worker 预留与账本**两事务顺序组合**。仅新增 `author-regression-data/.../STRICT_REFUSAL.json` 是该批原测试落盘 JSON；其他断言由原 JUnit/log及源码支撑，不虚构逐例额外回执。

原 Worker 同事务产品挂钩是 `Worker.reserve → pa_trial_dispatch.reserved → budget._reserve(c)`，此次静读/AST 核验。顺序组合测试先 Worker.reserve 再 budget.reserve，不称实际同事务完整 Worker 链通过。0 模型 transport 调用；没有新完整自然生成/执行、七槽长等候或恢复矩阵。

## 独立重复及类型检查

- `independent-new.xml/.log/.rc`：独立同新增 17 PASS/RC0，24.19 秒；`independent-data/` 17 份唯一 JSON。与作者 new 同集，不再加 17 个独特用例。
- `independent-execution-review.md`、`independent-execution-proof.json`：独审实际重跑、源码前后闭包和全部 JSON 核对，有限通过。
- `independent-regression-mypy-supplement.md/.json`：独立只读核作者旧 17 及 34 去重、mypy 基线/当前原件。关于处理后作者汇总的较早时点表述另见 `independent-timing-note-correction.md`；较早报告原字节保留。
- `mypy.log`、`mypy-baseline.log`：当前与 Git463自有静态源码快照均 RC1，4 文件 7 错、90 modules，诊断逐字相同；**类型检查不是 PASS，也不是历史 5 错**。未执行快照产品/Worker。
- `mypy-baseline-source.json`、`mypy-comparison.json`：快照来源及实际比较；baseline/current 的四个报错源未改，修改文件无新增诊断。

所有预留仍非退还，数学未预留容量不是发送许可；真实货币费用保持 UNKNOWN/null，paid_cap0 不等于已核真实免费。LIVE 拒绝、真实额度0、原 pins/guards/300秒/30秒不变。普通任意材料 per-use 批准与可计价费用余额未新增。

未执行真实模型/账户/费用资格、Windows、PG、原生浏览器、人工语义、远端 CI、部署、受限 callback/UDF/barrier 诊断或旧锁/恢复矩阵。旧首包 P-A 原因未知、旧两启动 FAIL 与旧满盘独审缺口保持。
