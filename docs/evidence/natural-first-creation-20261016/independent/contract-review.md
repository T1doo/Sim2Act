# 空目录首次自然 P-A 连续向导：只读合同核查

基线 `9d12e321d556c4b9c6ec2bf1ef4ccd7b958a645c`。只读核查，不改仓库、不跑模型、Worker 或旧矩阵。根是唯一仓库写入者。

## MOCK 与 LIVE 的真实边界

- `goal-application.js` 对 natural_spec/spec_checklist 禁选通用 provider choice、start 拒绝 choice，与现有后端一致，不是待补的 LIVE 入口。
- `api.py:generate_goal_application` 的 natural_spec 分支拒绝任何 activation，并使用封闭 app_limits。`goal_applications.source_scope_gate` 与 `check_provider` 都再次拒绝 SPEC_GENERATIONS 带 activation；自然生成没有现成 LIVE approval 路径。
- 现有自然生成可运行的唯一普通路径是无 activation、provider=intern-s2、Store.test_only、settings.mode=mock、live_enabled=false，并且 Worker 显式注入 `httpx.MockTransport`。`check_provider` 在实际 wire 前检查，任何缺项拒绝。policy.live_request_allowance 固定为0。
- `generation_approvals.approved_options` 返回的 OFFLINE_TEST/LIVE gaapproval 属通用已批准生成能力，不可因同一模型名就用于自然家族；准备新 gaapproval 也不能为自然家族开 LIVE 兜底。
- 现 `/api/projects/{pid}/natural-planning-status` 无论 provider 是否 intern-s2 都 available=false（reason=LIVE_ALLOWANCE_ZERO 或 PROVIDER_DISABLED），不能用其 available 或 provider choices 为空判定合法离线自然 mock 不可用。
- 现普通自然 POST 可以先接受一个 mock-mode generation Run，然后由 Worker provider guard 失败；它不能单独满足新向导“不可用时零 generation POST”的产品要求，前端需在提交前只读 gate。

## 同意的最小只读状态扩展

在现 `/api/capabilities` 附加 `natural_spec_generation` metadata：固定 version、provider、live_request_allowance=0、availability=`OFFLINE_TEST_ONLY|BLOCKED`。

OFFLINE_TEST_ONLY 严格由服务端 `db.test_only && s.mode==mock && !s.live_enabled && s.goal_planner_provider==intern-s2` 决定。它只证明当前服务端处于既有离线测试配置，**不是 LIVE 批准，不证明 Worker 已附加 adapter**；wire 仍由原 check_provider 验证 MockTransport。前端核固定 version、provider、allowance 和已知 availability，缺字段/未知/损坏一律 BLOCKED。

新向导在 generation entry/原 application-runs POST 之前 fresh GET；BLOCKED 时明确停止、零 generation POST、零模型发送。不能自动配置 provider、LIVE 开关、批准、凭据或注入 executor。有效离线 mock 允许无 gaapproval 走原 start，防止把“未选批准”误读为 mock 也不能运行。当前通用 renderResourceCatalog 不拒额外字段，可以兼容该 read-only 扩展。

## 最小连续入口

空目录有明确“从 TXT/MD 和 Goal 创建自然应用”入口。复用此前共享材料/Goal 保存和2048 UTF8字节/40 splitlines/Unicode C限制，Goal只绑定一份材料。保存材料、保存Goal不自动运行。

后续各阶段仍为已有独立显式动作：

1. 恢复精确已保存 Goal 当前 id/version/fingerprint/snapshot，选择 natural_spec；读取 readiness 并展示离线/阻塞边界。
2. 用户点击原 generation start。原 keyed receipt、PARTIAL候选读取、完整Goal/来源hash、candidate digest 与 sample-preview 独立引用核验保持。
3. 用户核对候选并分别确认 candidate ack 和 artifact write consent，走原 confirm-application-candidate；未知结果原 key GET，不再 POST。
4. 打开原 internal 控制器，明确 check、查看冻结快照、单独 version ack/commit；再由用户点击原 Release 的创建实例。
5. fresh GET/目录刷新后返回统一目录，展示真实保存应用和可打开实例；不冒称正式发布。之后第二材料/Goal沿用已验收应用内 preparation/per-use，新 Run/新结果且旧结果保留。

不可预先勾选确认、自动串 mutation，或自己拼候选/Release/实例请求绕开控制器。

## 上下文与共享表单手交重点

- showGoalCard 会 clearGoalCard→clearApp；showApp 也 clearApp；openGoalApplication 最后 selectWorkspace('apps')。这些会清此前 naturalUsePreparation并恢复表单。新向导不能未经明确阶段切换就把旧 per-use preparation state一直延用。
- 原 goalApplicationHandoff.current 绑定 workspace、appGeneration、Goal字段原始draft和编辑代际。保存后可先显式还原共享表单，用 fresh Goal恢复 activeGoalCard，再显示原生成控件；若另作handoff，仅限精确已保存Goal/预期app候选，不放松用户真实导航失效。
- 首次 await 前固定 identityConnectionGeneration、token/project、workspace、Goal id/version/fingerprint 和相关 app/creation edit代际；readiness/Goal GET/摘要hash/受理GET每步后复查。不能让迟到可用状态或候选进驻新身份/项目/Goal。
- 空目录 metadata 提示不证明授权、Release或运行结果。仍在显式打开当前候选/内部实例后核这些对象。
- 原生成 request key、确认 request key、内部批准指纹、instance create key、普通Run durable intent 与 per-use pending不应被向导清空来容许重复操作。

## 最小验证建议

一条从真空目录开始的 PA 可见 HTTP/JSDOM 合成链：用户保存第一TXT/MD+Goal→合法MOCK生成→精确候选确认→内部check/version/instance→首结果→目录→第二材料/Goal→原per-use→新结果且旧结果保留。MockTransport显式，真实模型0；生成和运行 wire分开记录，不能把 PARTIAL候选当成功运行结果。

轻量补 blocked readiness 零 generation POST、合法mock无gaapproval不被误挡、身份/项目/Goal/工作区迟到隔离、共享forms恢复和目录metadata零私有展开；不重旧恢复矩阵。Windows/PG/真实语义/真实模型/远端CI仍未执行，旧多历史心跳锁失败不能被称为解决。
