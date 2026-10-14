# Natural trial 精确批准与零付费准入（工程实现；真实执行未开放）

输入版本 ce6a0595c47dde0c5561265c3dbfa2ccc9b8721d；隔离分支 dev/natural-live-admission-20261015。本包只新增 natural_live_admission.py、独立 tests 和本文，不改既有 API、schema、sender、Worker、配置或软件资格。现 natural_spec_runtime 的 test_only/mock/MockTransport 检查完整保留。

原提案七槽只覆盖 P-A：3 Generate、2 Source、2 Cold。不是实际 P-B 或对照试验批准；不扩大额度、租约、时限、权限或预算。TrialContract 冻结同项目/主体/project runtime、两个完整不同 TXT 与 GoalCard 版本及全部快照/hash、全部现有 READ/SAVE 授权指纹、实际软件指纹、三个原意图 key、唯一 intern-s2/固定 HTTPS endpoint/stream=false、独立绝对 expires_at 和原 caps。材料 ≤1024 UTF8 bytes/20行，所有 Goal 内容及最多16人工未决项原样保留。这里不自动推断材料语义合规。

approve 在原 Store.tx 和 project lock 内复核两个 READ 与 SAVE，再读取完整 Goal/material 和批准正文。独立 namespace 的 scope/approve 双 seal 完整一致；同 trial/key/fp 幂等，改变帐号、内容、目标、模型、软件、预算、expiry 或 key 不覆盖既有批准。过期不延长，撤销只新增原 trial 的独立配对历史，不能再次批准。同 key cold recover 不新建 Run、发送、扣槽或改状态，仍需当前完整权限。

Generate 的 runtime 与未来生成应用的 runtime 不能混同。来源/冷阶段必须等已有实际 accepted AppRun 存在后，完整复核现 pa_spec_apps.bound/model_source、原实际候选确认、不可变 Release、instance revision、完整当前 Goal/material 和授权，再用独立明确 StageApproveInput 配对封存。阶段批准不能借用另一个已有生成 Run、仅靠公开 hash 或伪造 runtime；全部仍从原同一 trial 三阶段总账使用余槽，不创建新试验。每次 admit 核精确 stage Run、原意图 key、runtime、accepted fingerprint、版本/fence、取消意图、30秒原 lease、原 Run deadline 和 trial expiry。

强制零收费目前 NOT_VERIFIED。用户勾选 free、旧额度、常见免费或小请求均不能证明合法免费权益及强制不收费机制。FeeAuthority 是服务端受信依赖边界，未注册任何生产实现；任意用户/fake authority 不调用 verify，直接 LIVE_BLOCKED。唯一实现 SyntheticOnlyFeeAuthority 严格匹配合同 fp 与 quota_subject，且仅 test_only SQLite 可产生 scope=SYNTHETIC_ONLY、live_allowed=false 的 Permit；该 Permit 永不是实际 HTTP send 能力。

每个批准回执明确 EXACT_APPROVAL_RECORDED_LIVE_BLOCKED、fee_status=NOT_VERIFIED、live_allowed=false；阶段回执同样保持 LIVE_BLOCKED。模块不查凭据、账户、额度、models，不发 HTTP，不保留 secret，不部署、不改变付费/安全权限，也不授予正式发布或人工语义通过。

集成调用顺序必须为当前 admission → 跨 Run durable budget reserve → 发送前新的 admission/既有 sender guard；accounting reserve 不授予 send 权限。原 Generate 还须由原同 trial 的真实三 Attempt/slot wire、原始 bounded archive、usage 和接受回执完整闭环证明。缺少该审计模块或证明时阶段仍拒绝。实际 API/sender/controller 接线由集成负责人独审，本文不能代替已接线证据。

合法生产开放仍需：账户所有人的当前免费权益与强制零收费机制证据、受信 server-side fee authority 实现及独审、完整精确 trial 封存对象和独立批准、合法后端 secret 机制。当前无需提供 token，不自动开启 LIVE。真实工程验收与独立人工语义验收分开；引用/结构即便 PASS，语义 UNKNOWN/owner PENDING/formal publication false 保持。

实际命令、源码 before/after、原 stdout/stderr/XML、逐条用例及全部历史在 /workspace/natural-live-admission-evidence-20261015；最终索引为 AUTHOR_FINAL_INDEX.json。PG、Windows、原生浏览器、真实模型、账户免费权益、费用、人工语义、完整 P-A/P-B、部署/CI NOT RUN。

## 精确工程终态与独审

产品与测试冻结 `033204609063c4b4bbcbd6434e1c804d8de9917f`。本隔离树当前源码 **34 唯一 PASS / 0 FAIL / 0 ERROR / 0 SKIP**：final-short 33 PASS（另1 deselected，不重复加分母）+ final-seven 1 PASS，两组均实际终态，同一423源文件 before/after/current 全相等。外部并行预算模块实际只读导入路径为 `/workspace/Sim2Act-trial-budget-20261015/src/sim2act/natural_trial_budget.py`，源码 SHA `b372708a3da4c0f8176189f8bf7f8de5cef0deee851b5c392b37cfd4df1e56ce`；两轮前后均相同，并封存实际执行字节。本模块 SHA `ca0227e0b34f83c4d84e8320e0cadf2ba95949dc5e9c81a3c6dccd9371ec2480`。

实际组合JSON（author/final-seven-tmp/test_actual_mock_generated_app0/actual-combined-admission-budget.json）SHA `b1121423b76ae0bcacab30246bb6ebe5fc1af236459f48a7d6b698630fba921a`：三个不同实际Run，Generate3+Source2+Cold2 七个不同真实 mock Attempt，全部已知并被原试验总账接受，ACCOUNTED/KNOWN，保守预留48354、真实合成usage total7000。相邻预留间隔最小60.080589秒。21个实际返回 Permit 均为 SYNTHETIC_ONLY/live_allowed=false，budget回执 dispatch_authorized=false；必须经过真正新鲜 sender guard 后才进入明确离线 MockTransport。这个 fixture 新批准的独立绝对 expiry 为1200秒以容纳实际七槽，不延任何已批准对象；原每Run300秒、lease30秒、每分钟1槽、原7/3/2/2及全部字节/token上限未改。源、冷阶段既有 Run 均真实完成保存；确认丢ACK历史读取覆盖 RUNNING、SUCCEEDED、instance revision 改变之后，以及错误原key/撤权拒绝，读取不写、不重新批准或扣槽。

原历史不并入本次分母：first 33 PASS 是尚未加入同trial实际账本审计的前身支持；final-combined 为33 PASS/1 FAIL（夹具拦同步而实际sender走异步，未入总账，阶段正确拒绝）；strict-combined 为33 PASS/1 FAIL（第七槽已预留但未结算，冷Run HTTP为RUNNING/error null，总账RECONCILING/UNKNOWN）。这两个原失败全部保存，未恢复、重发、退款或删除其锁，也不把它们改签为通过。修正严格按真实 usage.tokens 字段核对，使用取消可协作异步 transport，在真正 admission→reserve→fresh admission→dispatch→settle 之后复用已有 fresh Permit 作观察，去掉只为观察的第4次完整 proof 遍历；不改租约/时钟/权限，不称原未知原因已定位或原Run已恢复。

独审最终报告 `/workspace/natural-live-gates-review-20261015/ADMISSION_033_FINAL.md`（副本 independent/ADMISSION_033_FINAL.md），SHA `9f37da876be2ca217cde3dddcada000c9c5ce336749b08a21316f77cde413b17`，仅只读 code/XML/JSON/Git，未跑测试或读取DB：本有限工程原语与合成组合 **无P1阻塞**。确认版本Literal类型标注的代码桥、完整原阶段权威/同trial三实际Attempt证明、历史原key只读恢复和精确预算边界。

Ruff新增模块与测试实际 exit0。单模块 mypy 实际 exit1：tools.py 两项既有注解错误，另隔离树不存在并行预算文件的 `natural_trial_budget` 静态 import attr-defined 一项；保留正常固定 import，不通过动态加载或抑制来制造类型绿。原namespace Literal赋值类型错误已修。根合并后预算模块存在，须重新核完整类型/软件资格/实际组合；本文不能代替该验证。本子任务不改资格或push，由根统一独审集成、正常分支交付。根树将使用正常本地导入移除隔离依赖 fallback，并在实际同一完整源码闭包复验。
