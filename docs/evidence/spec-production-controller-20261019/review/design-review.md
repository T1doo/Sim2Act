# SPEC 默认关闭生产controller：最小接点建议

**可以实施。** 现有字段语义足够，不需要真实账户值先到位，也不需要新审批层、安全框架或executor。最小实质工作是把一个独立的生产binding接回现有Goal/claim/Attempt/原wire/接收/提交闭环；不是重写InternModel或复制JournalTrialBinding。下述为实施前建议，不是运行PASS或生产准入。

## 一份新binding，复用一套控制器

建议不可变 `ProductionTrialBinding` 只绑定现有精确TrialContract/TrialContractV2及approval_key、原contractFP，并将account/canonical quota身份从固定服务端resolver结果核验/钉住；不接HTTP source对象、callback、registry、可执行Permit或任意provider selector。首次可明确只支持P-A七槽generate3/source2/cold2，P-B仍明确拒绝，避免把旧Journal拒PB边界悄然扩掉。

`pa_trial_dispatch` 的exact类型分流增加生产binding；旧PATrial/Journal的SQLite/mock/exactMock/空token约束原样保持。新binding校验原Store/engine/Worker/Settings身份不漂移、真实配置model/provider/endpoint/quota与原合同相同、显式mode=live/live_enabled/token、普通goal_planner_transport=None。这些是配置与身份检查，不建立收费授权。缺原批准或来源即拒绝；默认worker无binding继续不领取这类Run。不要给用户新增approve按钮、第二consent或自动选scope。

可复用：`production_trial_policy.check_run:157`核原approval/phase/Run/version/fence/worker/lease，`check_source:174`核既有requirementsFP/account/canonicalquota/provider/model/endpoint/期限/撤销及两项事实；`journal._apply_in_transaction:183`核原revision、完整identity、四CAS与account cursor；`pa_trial_dispatch.preflight:321`、`request_captured:659`、`_journal_exchange:1083`和原archive/history编排；`InternModel.request_serialized_captured:204`原bytes单次发送。不要把kernel Transition（始终live/dispatch false）升级或当成可复用发送许可，发送只能由固定controller在fresh检查后当场发生。

## 必须一并连接的断点

| 接点 | 最小要求 |
|---|---|
| 显式提交与claim | `natural_trial_runs:170–223`当前生成硬mock，`db.claim:1262–1333`仅认旧两binding。新增生产分流须在原同TX认精确合同/owner/project/生成key或已批准phase，核source后才claim；普通Worker、其他trial、旧key或关联Run不能被宽泛兜底选中。复用原范围/原阶段批准，不另加审批。 |
| GA生成与候选 | `goal_applications:275–277,731–755`对旧SPEC仍拒旧activation；新生产binding应独立核原TrialContract而非借pa-intern-generation-approval.v1。provider复用现配置InternModel；原实际read/check_candidate/最终候选三次协议和所有业务校验不改。 |
| NS节点与commit | `natural_spec_runtime:45–57,747–805`和`pa_spec_apps.commit_guard:1140`目前固定offline/合成头。生产分流只对已绑定原Run启用，核实际请求Authorization来自当前配置，原header/bytes/model/cap/lease及取消/权限门逐次保留；未绑定仍按旧offline或明确拒绝。 |
| 证据mode/lineage | 不可只改enabled：`natural_spec_runtime:159–189`MODEL_RESERVED与Attempt固定MOCK；`pa_trial_dispatch:1037–1053,1159,1208`固定JOURNAL_VERSION/MOCK；`natural_live_admission:609–639`分辨生成及Source实际计账。新binding必须有独立marker/version+LIVE mode和完整原历史证明分支，不能把旧MOCK历史重标LIVE，也不能降级旧pin/来源完整性。 |
| 发送/接收 | 固定原Store/settings/engine/Worker/Attempt/wire，原key先完整owner/history，无论当前source怎样都不重新send。source/reserve/marker/wire guard/commit各自同原事务fresh；guard后已在途无法追溯撤销，原received body/usage仍落原归档与账本，拒业务接受。 |

## 来源默认拒绝和迟到事实

`production_evidence.resolve_account:188–196`仍可保持缺来源就抛LIVE_BLOCKED。只由固定服务端接点调用，不能让CandidateDiagnostic、用户bool/hash或旧synthetic结果成为ALLOW。已有SourceVerificationResult字段已经覆盖所有绑定/状态；真实值未知不是字段语义不明，不用增加30秒provider续签假设。

特别注意：接收阶段不能先调用NoReturn resolver后直接抛掉已收body/usage。先从captured Store核owned Run/Attempt/slot和原wire；预期的来源缺失/拒绝/撤销转为内部UNKNOWN/DENY输入，复用`policy.settle:300–321`保留usage/占槽、accepted=false、halt=true；真正owner/DB异常不吞。沿原capture2+journal4与BodyArchive同一次commit，原semantic/parser/typed/CAS决定业务成功。`check_terminal_commit`沿原RUNNING快照/终态检查，不因已写终态而放松通用check_run；旧heartbeat、lease30、Run300、fence/预算不延长。

Journal的PG/SQLite原子insert分流**已经存在**（`:62–69,97–105`），无需新存储框架/namespace或重复算法。锁顺序和新quota双哨兵沿原；本次没有PG并发资格，不能由源码分流推断已实测通过。此前只读import检索误推及更正见observer-correction.json。

## 最小离线证明建议（非本次执行）

- 原批准/配置/来源缺失默认拒绝，不能产生claim/Attempt/slot/HTTP；旧synthetic绑定绝不借到生产分支，旧gaapproval不适用于SPEC。
- 在测试进程仅patch固定服务端source函数返回严格绑定的合成结果；在实际InternModel底层以MockTransport截获并阻断全部真实HTTP/socket/env凭据发现。fake ALLOW只能用于该受控软件测试，产品API与Worker不接它作为用户参数。不创建有效LIVE批准或触真实IO。
- 至少串起同一个原Goal/Run/Attempt的生成、节点、capture/settle及原业务提交；不重新实现业务oracle。错contract/account/quota/wire/worker、撤销/过期/lease、UNKNOWN/no-resend、已收响应后source失效必须走原门拒绝并保事实。原key重复只读、不能借新Worker继承send。

没有需要用户猜测的新业务语义字段：provider/model/endpoint、七槽阶段/上限、完整Goal/材料、Run/AppRun/Release/instance、account/quota和source状态均有原模型。实际账户与合法免费/强制不可收费来源仍缺，仅阻实际准入；这不妨碍本片failclosed工程。旧合同不容纳的新provider/channel则应保持拒绝，不能借当前接口改指向。

本次仅源码只读、写此新review目录，未运行产品、测试、DB、模型、网络或Git，未读私有留出集，也未修改旧sealed。待实际实现再核严格分流和完整mode/history链，当前无运行资格结论。
