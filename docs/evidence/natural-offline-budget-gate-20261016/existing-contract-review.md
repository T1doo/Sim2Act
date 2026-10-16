# 自然 P-A/P-B 批准与跨 Run 预算：现有合同/最小缺口只读审查

基线 `463167fd308889bf81ae7730310a86da24909897`，开工 worktree clean、约 26GiB 可用。root 唯一仓库写入者。本审仅读源码/现有测试，不写仓库、不运行测试/Worker/模型/自然链。报告不把静读现有用例描述为本轮通过。未发现适用 AGENTS.md。

**结论：核心批准、跨 Run 非退还账本与离线 P-A/P-B 接线已经存在，不能再造相同系统。真正差距是既有固定七槽 trial 与当前普通应用逐次入口的 scope 不同，以及生产费用 authority/计费余额仍未建立。先明确复用哪一个 scope，再做薄接线或新版本合同，保留旧合同不可迁移边界。**

## 已有能力与精确位置

1. `natural_live_admission.py:50` TrialCaps：generate/source/cold=3/2/2，总7调用；每 Run envelope<=64000、总<=192000；总输出<=7168；wire/ASCII response<=32768；单输出<=1024；lease30、RPM1、run<=300、paid_cap=0。
2. `:79 MaterialGoal` 与 `:113 TrialContract`：两份不同 TXT，各 UTF-8<=1024 bytes、<=20行，完整 Goal 版本/fingerprint/resource snapshot、用户/项目/runtime/quota/software/authorization/key/endpoint/model 全部冻结。`:141 TrialContractV2` 额外冻结5分钟review、60分钟execution、900秒stage handoff；不会把v1自动延展/升级。`:161 PBTrialContract` 已有 P-B path、精确 extraction_recipe 和独立 extraction_request_key。
3. `:697 _authorize / :714 _current / :759 _approved`：先当前项目/READ/SAVE，再私有材料/Goal/批准 body；校当前Goal head、资源hash/content、权限及软件，批准同key不换scope。`:786 approve / :823 recover / :841 revoke_exact` 已有幂等原键批准、历史只读恢复、即使源READ撤销仍可metadata-only撤销。
4. `:614 stage_review / :625 approve_stage / :862 admit`：source/cold 需对实际已受理Run的app/Release/instance revision/recipe/Goal/源成果作精确阶段确认。admit重查实际Run身份/version/fence/lease/cancel/deadline。只有 exact SyntheticOnlyFeeAuthority + test_only SQLite 可以得到 SYNTHETIC_ONLY、live_allowed=false 的fixture permit；任意回调不执行，默认LIVE_BLOCKED。
5. `natural_trial_budget.py:62 scope_for / :229 _reserve / :280 _settle / :324 read`：同一caller-owned transaction，原始 `delivery_graph_requests` paired rows；跨3个Run非退还预算，project lock + 全局quota subject行串行化；等待quota后重新admit且不刷新原deadline。保留unknown、失败、late usage历史，不退款、不解halt。duplicate精确key只返回历史 `duplicate=true / dispatch_authorized=false`，不得重发。
6. `pa_trial_dispatch.py:33 PATrialBinding / :431 reserved / :452 _sent / :538 request_captured / :788 settle_verified / :806 reject`：复用原Worker/InternModel actual MockTransport、先reserve并存wire，再真实sender guard前fresh admit及不可重发marker；P-B cold还核原source/extraction/archive链。不是新executor。
7. `production_trial_admission.py:96 production_preflight` 没有resolver/sender override，默认拒绝；`:243 dispatch_offline` 是可直接复用的固定字节sender离线门，0 HTTP。AccountEvidence/OfflineRegistry严格fixture类型、account→quota映射、freshness<=30秒、revoked/expiry/paid_cap0均已有。
8. `natural_trial_api.py:80 mount` 已挂 authenticated `/api/projects/{pid}/natural-trials/{key}` 的preparation/consent/status/approval/recovery/revocation/stage-review/stage-approval/budget/admission；`api.py:894`实际mount。`natural-goal.js:470/504`已有用户显式准备/同意/撤回和unknown原键恢复UI，非空白。

## 必须区分的范围与缺口

- **固定 trial ≠ 任意普通逐次应用。** 现有source/cold proof要求该trial原始generation之后的指定app/recipe/两份TXT及阶段key。不能拿同一个旧批准为任意已有app/新Goal/新材料/新Run滚动充值。普通自然入口当前不因存在trial批准就自动加入该总账。
- **P-B 完整合同已存在，但 server preparation/atomic acceptance 尚偏P-A。** `natural_trial_preparation.py:214`只造P-A V2、quota subject为`unconfigured:<user>`；`natural_trial_runs.py:51 _scope`只接受 exact P-A V2。该module的submit_generate/submit_stage是server controller，不在natural_trial_api暴露为Run创建HTTP route。旧PB v1 controller不能冒称已有普通PB准备向导或v2自动支持。
- **单生成旧批准不能复用为自然权限。** `generation_approvals.py`是literal TXT/MD<=4096B/64行、单generation Run、最多3请求；audit明确只容1Run。`api.py:519`对natural_spec显式拒body.activation，`goal_applications.py:589`对spec generations activation也拒；不得删这两个门把旧literal批准扩权。`natural_activations.py`又是固定CSV规划scope，也不能转成自然授权。
- **费用不是已完成的计价余额。** generation prepare明确`monetary_spending_cap=NOT_ESTABLISHED`；trial只有限定 paid_cap0 和合成fee proof，没有生产免费法律资格/账号不可收费机制，也没有价格货币/可扣金额字段。未知usage/失败不可被“mock本次0费用”显示层抹成生产0成本。离线可以报告 mock wire requests、tokens已知/未知、保留envelope；LIVE持续0/NOT_VERIFIED。跨项目quota row目前只共享RPM，不是全账号跨全部新trial的终身调用/费用总上限。
- **软件资格严格门不能绕。** `production._qualified()`校全部*.py与pin manifest；`natural_trial_runs.py:51`及claim调用。现有`tests/test_natural_trial_runs.py:63`专测真实资格拒绝，synthetic fixture在`:43`显式patch _qualified。任何新Python源都会变implementation。不能为新离线功能悄悄扩兼容名单/忽略pin；patch证明需明确仅synthetic controller，不是已资格普通Worker或LIVE。

## 最小接线建议

1. 若目标仍是固定七槽自然试验：直接使用原TrialContract/PBTrialContract、approve/stage APIs、production.dispatch_offline或现pa_trial_dispatch，补总预算只读投影/清楚的入口说明与缺门用例；不增ledger、executor、Grant或新价格策略。
2. 若目标是当前普通PA/PB的精确多Run用量包：以**新合同版本或独立不可混用namespace**表达被批准的有限Run集合、每个app/Release/instance/Goal/material/ref/key和shared cap；旧v1/v2 body/fingerprint/expiry不改变。复用现pair/remember、Store.lock_project/guard、现reservations/Attempt、防重marker；不要把每次新Run形成新预算来绕开shared cap。HTTP只允许server-authored scope和显式ack，admission依旧server-owned，live_allowed=false。
3. 只有metadata read不应触发reserve或model。reserve、actual send、结果落盘均需原current authority/worker/fence/deadline证明；失败路径只补成本/usage证据不解锁下一请求。未知原key只能读历史，不能换key再申请。
4. 本轮若只需离线最小门，避免重跑7槽真实RPM等待或自然Worker重链：固定OfflineSender和真实SQLite事务即可证明拒绝/并发/非退还；受资格pin阻断应如实作为拒绝证明，不能“修”成允许。

## 合成验收复用与实际剩余证据

现有测试静读已包含：test_natural_live_admission（缺fee/漂移/撤销/过期/权限/原caps）；test_natural_trial_api（PA/PB HTTP和私有读取前拒绝）；test_natural_trial_budget（双Store同key唯一slot、不同keyunknown阻断、近上限拒绝、unknown/late usage不退款）；test_production_trial_admission（固定sender、账号失效、生产默认拒、unknown duplicate不重发）；test_natural_trial_reserve_fence（quota/write等待跨deadline原子rollback）。这些是现有源码覆盖面，不是本审执行结果。

用户要求“并发超额”的最小新增证明应明确最后一个剩余额度下两个独立连接竞争，至多一个获批且另一不得新增slot/Attempt/send。现有“并发同key”+“unknown阻第二key”+“串行近cap”是三个不同命题，不能简单合称已测并发最后额度。重复key在accounting API可返回历史，应在dispatch边界断言0新增发送而非破坏原幂等读。已知失败tokens保留、unknown继续占envelope、late补齐只会计不恢复许可，也要用原ledger直接核验。

本轮尚未实施或运行任何新门；等待root冻结后再独审diff/实际合成证据。Windows、PG、真实模型/收费资格/真实语义、远端CI未执行，旧自然锁/F9/首包异常未知不因本审改变。

16份基线源码hash及工作区逐字比对记录：`/tmp/f2-natural-approval-existing-contract-463167fd-proof.json`，SHA256 `ad47917a009cc069c37763322239cdcf4896af502afb1bfe35fb17930b48e42d`。
