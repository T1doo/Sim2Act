# 预算查账入口 WIP 静态预审

2026-10-18，基线 fae2a3d7de3978671ca9c1c1c19cb8012e731eeb。只读当前未冻结 diff；当时生产仅 index.html/natural-goal.js 两文件，未见 Python/anchor/backend 变更。本审查未运行产品、测试、HTTP、Worker、DB/SQL或网络，未改仓库。

## P2：账本到展示投影缺少绑定（待修，不计通过）

当时 natural-goal.js:442–476 的 validateTrialBudget 校 Scope canonical 全字段和独立 contract SHA，校 money/LIVE/dispatch/status允许值及 stage 合计，但未将 stage Run/数量/envelope 和未知量与原 ledger.slots/stage_runs 相连。

两个静态可复现输入变体（未动态执行，也不声称保存了修前完整源码副本）：

- 一份原本合法预算回执只改 budget_projection.stages.generate.run_id 为另一个格式正确 run_xxx，原 ledger.stage_runs/slots 全不改。现判断仍可通过，renderTrialBudget 会展示错误“原 Run”。亦可在各 stage 间移动 held/envelope，保持总和。
- 保留真实 pending slot 的 settlement=null，只把顶层 usage_status 改 KNOWN、total_tokens/known_total_tokens 改0、p.unresolved_usage_requests 改0、status 改 ACCOUNTED。现判断仍可通过，展示完整总量0，违背原未知不填零合同。

最小修法：在既有最多7 slots的边界内，按原 backend _known 规则重算 stage count/envelope/唯一Run、stage_runs 精确键值及 unresolved/已知分量/已知未接受/总量null/状态。不要引入 Run查询或stage runtime要求；Scope.runtime_id仍只对应项目runtime。应将此单一一致性门补好后再冻结，非新账本或故障矩阵。

## 其余已核范围与失败策略

- 原嵌套批准 key、Scope完整 canonical 与独立 paHash、money UNKNOWN/null/NOT_LIVE_VERIFIED/livefalse、dispatchfalse、未知总量保留null、已返回分量可为0和明确不退款/余量非许可文案均已接；当前页面仅GET既有预算，不申请发送能力。
- readTrialBudget 的 current 绑定 token/connection/project/trialGeneration、workspace、entry/receipt对象、entry.operation和budget serial；API await及hash await后均复核。单flight防同current重复GET。clearTrialConsent、showTrialScope及各trial操作通过receipt/operation变化清旧账；现有app.js账号/项目/工作区路径调用clearTrialConsent。
- 读取错误清旧私有scope、receipt、账目并锁原key UNKNOWN，未删原key或产生POST。此策略保守但未发现同意/撤回的实际死路：recoverTrial仍可显式GET同key；READ/Goal失效时原consent-status只给本人metadata，恢复known后withdraw仍可用，预算按钮继续禁止。无账本409因此不得显示0；先恢复原key才能继续，符合原未知锁。
- 原withdraw在budget读取中仍能开始，它先加entry.operation，render使旧budget读取失效；旧finally只释放自身read，不会覆盖新操作。预算错误若晚于新操作也因current=false不清新状态。

结论：上述P2是本轮冻结前需要修的具体一致性问题；除此暂未发现确定P1/P2。尚无本轮实际资格，不预写PASS。后续修复、冻结及实际原件需另核。
