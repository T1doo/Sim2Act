# Natural trial 精确批准与零付费准入（工程实现；真实执行未开放）

输入版本 ce6a0595c47dde0c5561265c3dbfa2ccc9b8721d；隔离分支 dev/natural-live-admission-20261015。本包只新增 natural_live_admission.py、独立 tests 和本文，不改既有 API、schema、sender、Worker、配置或软件资格。现 natural_spec_runtime 的 test_only/mock/MockTransport 检查完整保留。

原提案七槽只覆盖 P-A：3 Generate、2 Source、2 Cold。不是实际 P-B 或对照试验批准；不扩大额度、租约、时限、权限或预算。TrialContract 冻结同项目/主体/project runtime、两个完整不同 TXT 与 GoalCard 版本及全部快照/hash、全部现有 READ/SAVE 授权指纹、实际软件指纹、三个原意图 key、唯一 intern-s2/固定 HTTPS endpoint/stream=false、独立绝对 expires_at 和原 caps。材料 ≤1024 UTF8 bytes/20行，所有 Goal 内容及最多16人工未决项原样保留。这里不自动推断材料语义合规。

approve 在原 Store.tx 和 project lock 内复核两个 READ 与 SAVE，再读取完整 Goal/material 和批准正文。独立 namespace 的 scope/approve 双 seal 完整一致；同 trial/key/fp 幂等，改变帐号、内容、目标、模型、软件、预算、expiry 或 key 不覆盖既有批准。过期不延长，撤销只新增原 trial 的独立配对历史，不能再次批准。同 key cold recover 不新建 Run、发送、扣槽或改状态，仍需当前完整权限。

Generate 的 runtime 与未来生成应用的 runtime 不能混同。来源/冷阶段必须等已有实际 accepted AppRun 存在后，完整复核现 pa_spec_apps.bound/model_source、原实际候选确认、不可变 Release、instance revision、完整当前 Goal/material 和授权，再用独立明确 StageApproveInput 配对封存。阶段批准不能借用另一个已有生成 Run、仅靠公开 hash 或伪造 runtime；全部仍从原同一 trial 三阶段总账使用余槽，不创建新试验。每次 admit 核精确 stage Run、原意图 key、runtime、accepted fingerprint、版本/fence、取消意图、30秒原 lease、原 Run deadline 和 trial expiry。

强制零收费目前 NOT_VERIFIED。用户勾选 free、旧额度、常见免费或小请求均不能证明合法免费权益及强制不收费机制。FeeAuthority 是服务端受信依赖边界，未注册任何生产实现；任意用户/fake authority 不调用 verify，直接 LIVE_BLOCKED。唯一实现 SyntheticOnlyFeeAuthority 严格匹配合同 fp 与 quota_subject，且仅 test_only SQLite 可产生 scope=SYNTHETIC_ONLY、live_allowed=false 的 Permit；该 Permit 永不是实际 HTTP send 能力。

每个批准回执明确 EXACT_APPROVAL_RECORDED_LIVE_BLOCKED、fee_status=NOT_VERIFIED、live_allowed=false；阶段回执同样保持 LIVE_BLOCKED。模块不查凭据、账户、额度、models，不发 HTTP，不保留 secret，不部署、不改变付费/安全权限，也不授予正式发布或人工语义通过。

集成调用顺序必须为当前 admission → 跨 Run durable budget reserve → 发送前新的 admission/既有 sender guard；accounting reserve 不授予 send 权限。原 Generate 还须由原同 trial 的真实三 Attempt/slot wire、原始 bounded archive、usage 和接受回执完整闭环证明。缺少该审计模块或证明时阶段仍拒绝。实际 API/sender/controller 接线由集成负责人独审，本文不能代替已接线证据。

合法生产开放仍需：账户所有人的当前免费权益与强制零收费机制证据、受信 server-side fee authority 实现及独审、完整精确 trial 封存对象和独立批准、合法后端 secret 机制。当前无需提供 token，不自动开启 LIVE。真实工程验收与独立人工语义验收分开；引用/结构即便 PASS，语义 UNKNOWN/owner PENDING/formal publication false 保持。

实际首轮及修正轮命令、源码 before/after、原 stdout/stderr/XML 将保存在 /workspace/natural-live-admission-evidence-20261015/author；终态统计和独审结论待实际完成后记录。PG、Windows、原生浏览器、真实模型、账户免费权益、费用、人工语义、完整 P-A/P-B、部署/CI NOT RUN。
