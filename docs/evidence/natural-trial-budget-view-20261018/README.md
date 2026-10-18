# 自然试验预算只读入口：执行原件与边界

基线 `fae2a3d7de3978671ca9c1c1c19cb8012e731eeb`；生产冻结 `85b65963ec91d723185164a4f6ee708fc8e19a27`；最终页面实测源码 `8e2cce44597a0a5adf057d47271b85ab6d763ed6`。普通分支 `dev/natural-trial-budget-view-20261018`，root为唯一仓库写入者，外部驱动作者和只读独审并行。

核实专属准入、跨Run七槽非退还账本、合成零费证据检查和默认拒绝早已存在。本轮新增现有P-A同意面板的“读取本试验跨 Run 预算”，复用原受鉴权GET。仅改index.html/natural-goal.js；后台.py、anchor/pin、Grant/Principal、发送器及默认LIVE均未改。当前同意记录与SYNTHETIC_ONLY permit不能授权真实模型请求。

3个唯一pytest节点最终各有PASS结果；共4次节点执行，3P/1F，未相加内部检查数：

| 实际批次 | 结果与归属 |
| --- | --- |
| 首轮85b，外13.695秒 | 两个既有默认拒绝用例PASS（1.913/1.725秒），新页面驱动FAIL（7.269秒）：遗漏现有先读取目标卡的可见步骤，恢复按钮尚未启用，budget GET为0。 |
| 第二轮8e2，仅页面 | 1PASS，JUnit9.092秒、外12.261秒。只给CJS加一条可见trial-refresh操作，所有断言/预算/时限不变；生产/Python/两个旧用例原样，两个已过拒绝用例未重跑。 |

最终48个检查标签=45个实际页面流程标签+3个合成validator负例；另4项helper记录含原响应副本ACCEPTED及3REJECTED，不另加用例数量。14可见操作、26 API GET+27实际静态资源，共53页面HTTP。预算GET实际409/200/200：缺账时清旧私有范围、保原key重核；原账本显示1槽、1124保守预留、原generate Run、partial prompt5/completion null/total null、RECONCILING/halted，以及费用UNKNOWN/币种null。双击一条读取；完整真实200只延迟交付，换另一原key并恢复后释放，DOM scope逐字段保持且无后续HTTP；普通换项目清空。

三个篡改拒绝仅为明确隔离的合成validator调用：错stage Run、原unknown slot被汇总字段伪称KNOWN/0、实际费用UNKNOWN被改0。原副本先通过；调用不改变DOM/HTTP/下载。它们不是实际HTTP响应被攻击或后端动态故障场景。

页面全程GET、0POST/下载，55表完整before==after。模型、Worker、有效LIVE令牌创建均0；账本夹具仅普通生成Run的store.claim及真实gate.admit配SyntheticOnlyFeeAuthority、原reserve/unknown settle，未dispatch模型。每次697输入/133生产零漂移。完整表等值是执行中的严格断言，持久化每表行数/指纹及全局指纹；未导出全行副本，独审未读DB或独立重算55表原行。费用仍未知，不能把未发送真实请求或合成账本等同已核实实际费用0。

主要原件：

- [首轮命令/冻结/时间](failed-1/execution.json)、[2P/1F JUnit](failed-1/junit.xml)、[完整失败输出](failed-1/pytest.stdout)、[首18原文件保全指纹](first-attempt-manifest.json)。
- [第二轮执行](passed-2/execution.json)、[PASS JUnit](passed-2/junit.xml)、[pytest原输出](passed-2/pytest.stdout)、[最终输入前](passed-2/inputs-before.json)与[后](passed-2/inputs-after.json)。
- [完整实际页面请求/原响应与检查](passed-2/actual-tmp/test_original_trial_budget_is_0/results.json)、[原进度](passed-2/actual-tmp/test_original_trial_budget_is_0/page-progress.jsonl)、[55表/生产hash证明](passed-2/actual-tmp/test_original_trial_budget_is_0/proof.json)。
- [合成账本、真实准入及非LIVE permit夹具](passed-2/actual-tmp/test_original_trial_budget_is_0/synthetic-ledger-fixture.json)、[正常fixture原始HTTP](passed-2/actual-tmp/test_original_trial_budget_is_0/fixture-http.json)、[provider调用空记录](passed-2/actual-tmp/test_original_trial_budget_is_0/provider-calls.json)。
- [先行独立设计](independent/design-review.md)、[修前P2](independent/prequalification-review.md)、[修后复核](independent/prequalification-followup.json)、[有限最终独审](independent/final-independent-review.md)、[纯文件审计程序](independent/audit-closed-evidence.py)与[结果](independent/closed-evidence-audit.json)。
- [作者原稿与root单步修正来源](provenance.json)、[精确一行补丁](author-to-frozen-driver.patch)、[49项原件逐字节映射](selected-artifacts.json)、[原远端](remote-heads-before.txt)及[基线](baseline.json)。

49项所选原件985,780字节；另加来源说明、映射和本README，共52交付文件，不复制DB/整树/bundle。独审新目录10文件/38,562字节，manifest另1807字节，SHA256 `4cc539c075e3864cf6d6d1b0b9a0c0a6f600328530fffaa8a35fde6e038ef003`；已停止写入。全部选取保留外部原件字节，最终另核Git blob。第一轮18文件中的3份合成DB只留原路径，独审仅stat并引用作者hash；15非DB逐字节复核。重复HTTP JSONL留在外部原路径，完整原响应文本已在results中；held投递字段的观察时点差异由独审明确规范化。

实际页面范围为P-A试验查账；两个既有用例验证无生产fee authority与任意callback/production store默认拒绝。READ撤权、跨账号、held项目切换或digest ABA、过期/撤回历史读取未在本新页面逐场景动态重跑，相关围栏仅源码核查。P-B页面、真实账户/费用/模型/语义、Windows/native、PG、远端CI未验收；不放行正式发布或完整F2/R0。旧取消窗口、旧未知故障及满盘未落盘报告缺口不补签。
