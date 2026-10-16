# 只读预算投影及轻量证明静审

冻结 `4aaea50d4ea40b7d2425f3c1561bc99b5e3def53`。有限静审无剩余阻断；本独审未运行 pytest/模型/Worker/HTTP，未修改仓库。

产品只在原 `natural_trial_budget._public` 添加纯 `_projection`，不修改已有reserve/settle/admit/guard、写事务、额度或资格pin。每个已预留slot都持续计入held请求和wire+1024 envelope，成功、失败和unknown都不释放；stage及总量未预留容量只是账本数学差额，`dispatch_authorized=false`不将其当发送许可。真实费用保持`actual_paid=None/currency=None/status=UNKNOWN`，paid_cap0、fee NOT_LIVE_VERIFIED、live_allowed=false，不从token或mock推算真实费用。known_unaccepted_tokens精确表达有已知usage但未获accepted的证据，未把其直接称为所有业务失败。

新测试的两个SQLiteStore race已从静态控制流确认竞争同一trial、同generate stage最后请求或envelope容量：胜者在同controller transaction reserve+固定usage settle后提交，对手必须从预算边界拒绝；合成clock、primitive admitted stub和0IO明确标注。三Run案例沿用同trial，展示累计不重置；PA/PB真实admission与ASGI budget GET另分证明，没有资格绕过或实际模型执行。

首读WIP的Goal漂移测试原先只改传入scope，现冻结已修为批准后实际PUT saved Goal增version且保留原approved contract；不再是阻断。早期WIP笔记在root并行修复期间采样，不能用作当前冻结证明，已由本文件与新JSON明确替代。

精确证据边界：旧`test_actual_admission_generate_worker_reservation_combination`先调用Worker.reserve，再另行budget.reserve，是两个事务；执行它也不能称当前“Worker reserve同tx组合实测”。实际同tx链`Worker.reserve → pa_trial_dispatch.reserved → budget._reserve`是已有源码接线；本次primitive race证明caller-owned transaction，不替代qualified Worker完整链。该严格资格门保持拒绝，不应为绿色结果放松。

机器证明 `/tmp/f2-natural-budget-projection-4aaea50d-static-proof.json` SHA256 `3566aab1d50ef1ea750961f9b8e2aba7a32477963c89df58b7ee0dcb1151a2e3`，含两份源码/测试hash与freeze逐字比较。待实际轻量pytest回执后再签运行范围。Windows/PG/真实收费资格/自然语义/CI均未执行；既往未知事项不改变。
