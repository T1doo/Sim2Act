# 自然试验只读预算入口：有限独立设计审查

基线：`fae2a3d7de3978671ca9c1c1c19cb8012e731eeb`。2026-10-18，只读源码、Git及原规格；本审查未执行产品、pytest、HTTP、Worker、模型、SQL/DB或网络，未改仓库。当前目录为新目录，所有既有 sealed 目录未改。

## 结论

建议实施一个最小可见功能：在既有 **P-A 精确试验同意面板**添加显式“读取本试验跨 Run 预算”，只接既有受鉴权 GET。这是用户目前缺少的查账入口，不是准入/账本重写，也不开放真实模型。静态设计无已知阻塞，可进入实现及一次定向实际资格；当前未执行新功能验收。

纠正上一阶段概括：自然家族专属准入、跨 Run 总账、默认拒绝和受限 Mock Worker 接线已经存在。普通自然生成的 OFFLINE_TEST_ONLY 守卫不能证明这些模块不存在；尚无生产零收费 authority/resolver/sender，不等于工程原语尚未实现。

## 原规格及实际源码依据

- 原产品设计 `docs/sources/V5/平台产品设计.md:337–343` §7.5：限制和用量报告，unknown/partial 不填零，价格未知不折算费用、不承诺免费。`:185–193` 权限交集；`:111–127` P-A/P-B 分别验收及限制可见。分阶段计划 `docs/sources/V5/分阶段开发计划.md:409–411` 保留失败/响应丢失的未知成本；本切片不签收完整 F2/R0/P-A/P-B。
- 确实缺的入口：`web/natural-goal.js:354–550` 只准备、同意、恢复、撤回、结束；`:418–425` 只显示合同固定 caps。整个 web 当前没有调用 natural-trials 的 budget GET。既有 P-A 面板不是 P-B 同意入口，本轮不要扩大该声称。
- 可直接复用 `natural_trial_api.py:144–148`：original_contract → gate.recover → budget.read。`:54–76` 先核 owner/project、两份材料 READ 和项目 SAVE，再读完整原 scope，核当前 Goal/material/auth。不得用 metadata-only 状态绕过它。
- `natural_live_admission.py:759–829` 已有 exact approved/recover，`:862–923` 已有 stage、Run/version/fence/lease/deadline 和默认拒绝；只有 exact SyntheticOnlyFeeAuthority 且 test-only SQLite 才可能返回 SYNTHETIC_ONLY/live_allowed=false，不能变实际 HTTP 权限。`production_trial_admission.py:96–107` 默认 preflight 无 authority 参数，不注册 resolver/sender；`:110–143` 仅明确离线 registry，不能当生产账户证明。
- `natural_trial_budget.py:229–268` 已有原子不可退还预留、3/2/2与7槽、原 Run 绑定、账户节流及二次 guard；`:280–320` 保留未知、失败、迟到结算；`:324–393` 原键只读及现成 budget_projection。`worker.py:277–279`、`pa_trial_dispatch.py:431–449` 已在原预留事务调用预算/请求归档；`pa_trial_dispatch.py:48–62` 保留 test-only/mock/MockTransport 门。`natural_source_archives.py:1–4` 明确归档不证明真实 provider/免费权益。
- `docs/F2/NaturalOfflineBudgetGate20261016.md:7–30` 已精确说明上述原门、投影与未知费用；其历史实测不作为本轮重跑。

## 最小只读合同

1. 仅完整、当前读回的 `PREPARED_LIVE_BLOCKED` preparation receipt，且 approved=true 且含严格嵌套 approval 时可查。原 key 从 `receipt.approval.approval.request.request_key` 取（`natural_trial_preparation.py:117–119`、`natural_live_admission.py:815–819`），不猜 key、不要求用户填写指纹、不新增同意/Permit/Run。完整 receipt revoked/expired 可保留只读历史；当前材料/Goal权限校验仍由原 GET 拒绝，不降级。
2. 对原 contract 做独立 digest；校核 nested approval 的 contract/project/principal/expiry/key 绑定，预算 Scope 所有字段必须精确等于原 trial_key、approval_key、contract_fingerprint、project_id、principal_id、项目 runtime_id、quota_subject、expires_at。Scope.runtime_id 是项目 runtime，不能要求 Source/Cold 的应用 Run 都用项目 runtime。
3. 对 bounded ledger/投影进行类型和一致性校验，再 paint：阶段键只能 generate/source/cold，3/2/2及总7固定；Run/原请求键不串阶段；held 与原 slots、wire_bytes+1024、数学余量、unresolved、stage_runs 一致。顶层 dispatch_authorized=false、live_admission=NOT_VERIFIED；money 精确为 paid_cap=0、actual_paid=null、currency=null、UNKNOWN、NOT_LIVE_VERIFIED、live_allowed=false。不接受异常数字、非有限数或不一致回执。
4. 显示 held/原 Run、known/unknown/partial、HALTED/RECONCILING；所有槽均不可退还。`known_total_tokens`（budget.py:390–391）仅已返回的已知分量，不能冒充完整或已接受总用量；total_tokens=null 必须显示未知。unreserved_* 仅数学未预留容量，不是可执行余额。token envelope 不等于 tokenizer 或货币。
5. 原 budget.audit:335 在无账本时 VERSION_CONFLICT；必须显示“暂无可验证账本/读取失败”，不能编造0已用/7可用。失败/拒绝不保留旧账画布，不把 metadata-only 状态当读预算的来源。既有 API 没有初始化空账本的新副作用，本轮不加。
6. 显式单次 GET；无自动 poll、POST或后台执行。开始读先清旧账；同 entry/receipt/operation single-flight；每个 await（含 digest）之后重核 identity、connection、project、trialGeneration、entry对象、原 receipt和本次读取代数。任何同意/撤回/恢复/新建/地址历史或账号项目连接变化均清 RAM/画布并使迟到读取失效；最后释放只释放自身 pending，不干扰新操作。绝不持久化身份 token/合同正文/账本正文，不增加权限、Grant、executor或软件资格旁路。

## 最小实际资格建议及界限

复用既有合成 test-only Store、真实已保存材料/Goal、真实精确同意记录与既有 budget reserve/settle。明确测试用 primitive admission stub/SYNTHETIC_ONLY 只是合成账本数据，不是有效 LIVE 批准。页面通过实际现有 API GET 验证已知与未知占额、费用未知、非退还数学容量、无账本拒绝；再以真实 READ 撤销验证拒绝和画布清理，以一个 held callback 验证账号/项目/原 trial 变化不能迟到覆盖。合成与实际 HTTP 层分别标注；不需要 Worker、模型、长七槽或旧恢复矩阵。读前后业务表及预算/批准行不变；模型及真实请求0。默认自然/LIVE入口、.py/pins/权限/发送门不改。

本审查是实现前静态设计意见；没有亲跑新页面。Windows、PG、真实模型、真实费用/免费权益、语义、远端CI、正式发布均未执行或提升。真实生产开放仍需另外精确授权和可信生产零收费证据/实现，不能靠勾选免费、填 token、Mock permit 或展示数学余量开启。
