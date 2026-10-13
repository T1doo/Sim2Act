# P-A 未标注短规范：259 基线独立设计审查

结论：**有限方案可接入现有框架，但本报告不是实现或运行验收。** 新动态测试0，真实模型/费用0，语义和新执行路径全部NOT_RUN。root为唯一产品写入者；reviewer只读取本环境代码/合同并写本任务指定workspace证据目录，没有修改仓库、读取凭据、执行probe、联网、申请escalation或清理旧证据。

## 精确审查对象

基线HEAD `259f583eba6dd6c5580834878da6bd3cb1f648a7`，分支 `dev/pa-natural-spec-20261012`。首读Git-tracked429项源码/测试/pyproject的map SHA256为 `e69705c672d4f3229baddfcc0b164ff3adc844faa597787991a750d2a105728b`。17个已读生产文件由Git259逐字保存到 `source-reviewed/`，各blob SHA等于首读checkout map，详见 `reviewed-source.json`。

主合同快照 `contracts/docs/F2/PANaturalSpec20261012.md` SHA256 `14a0414dea4886ab47ca1378731dad69479d926513ac6e65f7f3e0b928437fd3`；NonCSVTaskProposal/ExecutionPlan也已完整读并存原bytes。后观察时429个原tracked项没有变化，但root已经增加未tracked `natural_specs.py`，所以**不宣称整个live实现树0diff**。`source-after-observed.json`是作者持续开发中的观察，不是新实现冻结/资格证明；本设计结论只对259基线和上述合同快照负责。

## 最小可执行接入

`natural_specs.py`只负责闭schema/recipe展开、精确引用、纯机械merge/uncovered、版本化prompt/schema和安全JSON/MD；`natural_spec_runtime.py`只负责已登记1/2模型节点的真实Attempt/reservation/序列化sender/回执核验。自然生成仍复用goal_applications实际read→check→final三响应；应用模型节点在cold目标Run重新发送当前材料/完整Goal，不借普通MockModel或offline_replay。

扩pa_spec_apps的**显式family分派**来复用已验source scope、原生成审计、Release/instance/typed/local-save事务和末CAS框架；不要另写通用执行器。新namespace、generation version、recipe codec、scope meta、binding与ACCEPTED标记必须彼此精确匹配；unknown family不可else回退为literal或labelled。旧家族的0Attempt/纯函数oracle保持原严格规则。new family没有LIVE activation路径；无显式test_only+mock+MockTransport时先拒绝模型reservation/dispatch。

## 必须落实的具体接口和边界

| 项 | 259实际证据 / 风险 | 最小方案 |
| --- | --- | --- |
| D1 reservation分派 | worker.py51–55将`request_tools is not None`且非planner/generation判成protocol；164调用protocol_pool.reserve_slot。runtime借`generation_request=True`也会检查application_generation三阶段history，应用contract没有它。 | 新runtime专用显式互斥分派，调用同一个Worker.reserve/quotas/不可退款ledger；不伪装protocol或generation。generation阶段本身可在新增typed version后沿既有generation_request复用。 |
| D2 旧0门/回执不是模型oracle | pa_spec_apps.py657–685强核requests/repairs/tokens0与Attempt空；763起只接受连续workflow前缀，nonSAVE依赖pure独立复算；result_ref硬编码model_requests0。 | 新family单独核1/2个模型slot、Attempt↔node↔op↔wire↔fence的唯一映射和safe-output/schema/quote/usage/model proof；纯工具仍重算。既有labelled门不放宽。模型receipt的VERIFIED只意味着来源/结构/传输证据，语义仍UNKNOWN。 |
| D3 预算需在扣额前求交 | worker.process先app_jobs early-return，后面才做contract limits的replace；reserve123主要使用worker.s，旧spec commit_guard仅需要tools/time。Limits.max_requests最小1，所以预算0并不能靠设置max_requests0表达。 | reservation之前验证platform∩Release∩FrozenRun∩node有效requests/tokens/output/time，明确默认provider allowance0。每次request完整wire byte-envelope，包括schema/Goal/read/此前输出，不缩字段绕上界；runtime单节点不得自动repair或重发。 |
| D4 顺序真实反馈的步数冲突 | read→model1→check1→model2→merge→check2→save是7步/5local tools，超过合同6/4。 | 首模型receipt内执行版本化citation postcheck，保存真实check对象/hash/依赖；node2消费该已验证receipt反馈；末merge→verify→save仍是6步/4local工具。inline check不增加工具slot，也不是假PASS。root已明确采用此方案。 |
| D5 并行计数与DAG顺序 | reserve使用caller context后写回；两发送线程各持requests0有丢更新风险。旧receipts把储存列表当连续前缀。 | 稳定ready-set按真实边解释可执行集合；保留模型原ID/ops/edges。最小实现可串行调度逻辑并行DAG，明确未验证同时发送。若actual并发，需同Run原子slot/counter/CAS或批量reservation，不能扩大scope或绕任一未结算Attempt。 |
| D6 精确wire / immutable模型历史 | model.py159/172提供request_serialized与完整绝对deadline；goal_applications673–715有发送前wire/url/POST/STARTED/current gate，parse_response/checked_usage能复用。 | 绑定step/ordinal/RID/Release/iid/sourceGoal/recipe/前驱receipt/checkfp、wire bytes/hash、reserved envelope与独立事件。发送前重新核身份/授权/source/GoalHead/fence/lease/stop/current软件；拒函数调用/额外工具、错误alias/usage/截断/refusal。新receiver的parameters保持immutable。 |
| D7 收到但迟到/撤权 | Store.has_unknown1236识别STARTED/unknown效果；claim/recovery999–1041保留这些为等待/对账。raw收到与获得执行批准不是同一事实。 | 按root设计先把完整raw包存受保护Attempt.response，再当前授权/fence/deadline检查后生成VERIFIED receipt。拒绝/迟到也保留真实received证据和reservation，不能把raw归档当成功。仅凭owned opaque ID/已知slot做只写metadata/CAS，当前授权之前不full-read旧Run/Goal/contract/Attempt包。STARTED/unknown或已收到未验证slot不能重发；GET原key仅恢复原状态。 |
| D8 原私有读取门 | Store.guard921、frozen_contract937均先source_scope_gate；goal_applications113–163用独立ACCEPTED+contract ID hints；pa_spec scope/metadata/历史读取已有多门。 | 在claim/inspect/approval/options/preview/Run/instance-history/classifier所有接线显式识别自然family，任何残存hint不得降级。完整body先current principal/project/runtime/source授权；history fullRun WHERE保持exact scope。新增Attempt raw只在授权后读，公共event只放有限hash/ID。 |
| D9 原与本次审计末门 | pa_spec save1014–1017比较最终verify_job的原审计fp与入口b，再原lease/deadline/stop；typed+grants+effect+CAS同tx。 | 保留原byte digest并增加本Run全部模型Attempt/response/parameters/usage/identity/reservation锚/操作/receipt的精确核验，不能只重建使用到的semantic字段。save末callback改任何审计unused field也要回滚全部本地写。保持30s lease、300s deadline，网络发送在本地save事务外，heartbeat不能延absolute deadline。 |
| D10 阶段预算与未来授权 | generation policy240是3 requests/1repair/live0；自然应用Run1或2请求；现4请求cap是per-Run，非整个多Run任务总数。 | 明确generation3+一个应用1/2＝4/5合成发送槽、再每次新材料各1/2；不把一次4-slot审批偷扩多个Run。最终真实提案必须给分阶段及总上限，当前0live。旧ga/nl activation不能授权新family。 |

这些是待实现的设计约束/基线差异，**不计为十个实际产品测试FAIL**。root follow-up已采纳显式分派、提前预算求交、inline check、分开tools/models及分阶段总账，尚无本reviewer动态证明。

## Codec与机器/语义边界

固定source只用逻辑资源TXT/MD、UTF8≤2048B/≤40lines；content/hash按actual read冻结，不接路径/URL，不通过关键词/regex或developer gold替模型分类。需写清坐标是Unicode code points、0-based half-open（或另一个唯一明定系统），保持原CRLF/newline/空格，严格int拒bool；quote必须逐字等source[start:end]。byte上限与char span不能混用，Unicode/emoji需测试。

事实原kind/说明/quote/spans/关系和模型节点safe output全部保留。全局ID使用明确node-qualified标识或严格唯一规则，避免两节点同ID覆盖。条件/例外目标必须是已存在requirement或显式UNASSIGNED；open_question不允许自动resolved字段。merge做可复算的保留性合并，不能按相似text、关键词、开发gold或“更好的第二答案”消除首节点事实。8合并事实或JSON8000字符越界直接失败，不截断。若去重，两个原输出仍存且映射不能丢项；跨节点冲突保留为未决或拒绝，而不自动裁决含义。

uncovered应是实际quote intervals的机械补集，完整原文始终在最终JSON中。覆盖全原文只证明span覆盖，不证明义务/例外/未决完整；一个错误摘要引用整文也不获得语义PASS。声明`citation/structure PASS, semantic UNKNOWN, semantic_goal_acceptance NOT_RUN, owner PENDING`；如没有模型事实，明确“没有可验证抽取/全部原文待检查”，不可用vacuous quote PASS表示Goal完成。Run.SUCCEEDED仅表示这份待验JSON已原子持久化。不得据此进入可信P-B/owner acceptance或正式发布。

完整native Goal（原约束与全部最多16 human unresolved）独立封到accepted binding/FrozenRun；model open_questions另列，不向GoalSpec.unresolved追加实现tag，也不自动resolved/省略/合并原人工项。样例完整答案只留protected generation history；public app只有recipe、schema/prompt dependency版本和samplefp。runtime prompt由actual新target read receipt/新Goal及本Run verified前驱结果构建，排除旧sample/旧source/旧Goal答案；绑定preview应MODEL_EXECUTION_REQUIRED，不给未经发送的新材料假结果。安全MD从核过JSON派生，无第二保存。

保存失败的“0partial”应指同一local-save事务resource/grants/effect/op/intent/typed/dataCAS/terminal全回滚。模型已发送的不可退款reservation、raw reception/rejection/history可以合法留存；不要把模型全过程错误地要求全DB零写或退款。对最终callback测试可比较save入口/退出全表；对late receiver测试应分别证明ledger保留且没有VERIFIED/制品/typed成功。

## 冻结后最小实际测试建议（此轮未运行）

1. 两份无标签中性短规范，条件/例外/待定决定变体；外部gold只在测试断言。至少single-all、dual-independent与dual-sequential三recipes，actual generation read/check/final；故意错误quote收到真实diagnostic后仅一次修订，PASS改graph/candidate拒绝。
2. 新材料新Store冷Worker：捕获actual wire，source/hash/完整Goal16来自新read和新Goal；旧答案不入prompt；1/2 actual Attempt与真实JSON/readback/effect/grants/typed/CAS；模型关闭时Attempt/reservation/send0，无MockModel/offline_replay兜底。
3. Budget1阻止第二节点、token/wire/input byte cap、8facts/8000边界，不截断。每reservation与完整wire一致，usage missing/wrong identity/工具调用/截断只留失败证据，无receipt成功。
4. 原key未知/STARTED、已收到未verify、重复same node、dup/missing/wrong Attempt/op/event、same IDs不同body；不重发/不再扣额。独立节点逆序完成不得改变原DAG或少记请求；若actual parallel，另做受控counter race。
5. Quote/schema/relations：Unicode+CRLF、错span/bool假int/dupJSON/extrafield、未知target、UNASSIGNED、重复ID、merge删首conditions/exception/question；遗漏原文或错误语义但quote合法时必须仍语义UNKNOWN，不以外部gold暗改模型结果。
6. 实际SQLite UDF屏障允许exact IDs投影，故意full protected读取先校准命中；撤权/foreign与联合marker剥除后private完整cell0。覆盖raw receiver的只写保留与之后current-auth-before-full-read。
7. 末save callback：身份/runtime/project/source/hash/GoalHead/instance revision/dataVersion/lease/deadline/stop/revoke、原audit unused field和本次Attempt/response锚byte篡改；local所有写及terminal同tx回滚，模型先前reservation留存不退款。
8. 原UI真实HTTP/IPC离线DOM：family明确选、机器/语义状态、MODEL_REQUIRED preview、write consent、lost POST仅GET原key、edit/identity/project late fence。新qual精确全实现map+旧两个literal源/旧labelled实际Worker代表回归；原ANCHOR_HASH/CHANGED不扩文件名免审，不自动重签旧approval。

这些是最小验证主题，不是已跑节点清单，不借旧永久取消安装窗口；所有新fixtures应直接位于本任务workspace证据root，完整保留红轮/原错误及freeze before/after。

## 仅proposal的真实验收边界

proposal需列精确Intern-S2和当前实现endpoint锚、材料仅自造中性类别、generation与runtime/新材料分别及总请求/token/full-wire上界、自动重试0、未知停、局部SAVE/readback权限、费用0的已核与未核前提、独立semantic gold及其不外发；当前不发请求、不读凭据、不设账单、不借AT02历史授权。代码中的endpoint常量/合法环境变量入口仅是实现事实，不能作为此轮已核官方政策、账户资格、免费余额或真实provider可用证明。官方/余额/凭据合法来源未核就注明未核，最终让用户批准具体有限提案。

真实模型、网络、费用、凭据检查、PG、Windows、native/browser、CI、真实oldDB upgrade、wheel/package installation、全产品/P-A/P-B语义，以及永久取消安装窗口均NOT_RUN/NOT_VERIFIED。本报告没有调用或恢复任何旧被拒probe。

## 交付

DESIGN_REVIEW_259.md、source-before.json、source-after-observed.json、reviewed-source.json及17个baseline source snapshots、完整三个contracts快照、contract-after-observed.json、parent-design-update.json和manifest。审查只读、动态0、保留新live作者变化而非造0diff。后续冻结候选另做源码审查/实际独审，不能从本设计报告继承测试PASS。
