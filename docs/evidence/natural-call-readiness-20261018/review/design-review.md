# 未注册自然生产调用：有界独立设计审查

2026-10-18；实际HEAD `5a348ce97325ebbe450c2beb09dff767a4376252`、clean。只读源码、原V5及Git；未执行产品/pytest/collect、HTTP、Worker/模型、DB/SQL或网络，未写仓库、未新增agent或变更模型。新目录，旧sealed目录未改。此为设计结论，不是新测试或语义验收。

## 决定：NO_SAFE_INDEPENDENT_PRODUCTION_SLICE

在本轮禁止注册来源/sender、生成有效LIVE许可、读取凭据或真实请求、放宽现门的范围内，**未定位到尚未实现、可独立交付且有真实执行价值的最小生产调用代码**。这不是“常规开发未获授权”，也不否定未来可离线实现成组生产策略；当前实际依赖尚不形成一个安全的独立新增调用切片。不要重命名/提取已有编排或加另一个恒拒绝壳来冒充补齐接线。保持源/资格pin/门不变，推进独立holdout材料与验收合同准备；未评分就是未评分，不用Mock或参考答案替代真实语义。

## 已有实际调用行为，不能重复造

- `model.py:198–255,258–309` 已有exact serialized bytes、单次Intern适配器调用、bounded decoded-body capture、完整总deadline与取消清理，非缺少底层adapter。
- `pa_trial_dispatch.py:431–449,452–535,538–568,751–829` 已有原预算预留/请求归档→发送前原guard→fresh admission+原sent marker→exact InternModel capture→响应归档→原settle/reject，未知保持且不重发；不是缺一个send/capture wrapper。
- 实际调用点已在 `goal_applications.py:742–747` 与 `natural_spec_runtime.py:807–811`。分别服务generation和自然模型节点；原local tools/事务/成果保存继续独立。

## 真正未闭合的相互依赖项

| 边界 | 当前实证源码 | 最小未来接口与责任（仅描述，当前不新增实现） |
| --- | --- | --- |
| 可信生产账户权益来源 | `production_evidence.py:188–196` 仅requirements投影后NoReturn缺源；CandidateDiagnostic不是来源或权威 | 输入必须是原_approved后生成的EvidenceRequirements，精确user/project/runtime/trial/approval/contractFP、provider/model/endpoint/quota/expiry/paidcap0。受审服务端source负责真实账户归属、合法免费权益、强制不可收费机制、当前issuer/有效期/撤销及完整证据来源。输出须是真实已验证来源记录，不能用caller bool/hash、候选诊断、Mock record或函数参数callback替代。缺源/未知/陈旧保持LIVE_BLOCKED；权限拒绝仍先发生，不外发探测来发现免费。 |
| 生产准入决定及预算policy | `natural_live_admission.py:253–264,899–923` 只SYNTHETIC Permit及exact SyntheticOnlyFeeAuthority；`natural_trial_budget.py:163–195` 只SYNTHETIC_ONLY/test_only SQLite | 受信authority消费上项真实证据和原合同/当前stage Run/version/fence/cancel/权限/原expiry，产生短时、精确作用域的内部生产准入决定；不是HTTP可自填permit。预算须有分离的生产policy消费该决定，继续原3/2/2、总7、共享quota、非退还/未知STOP及发送前fresh guard。不能扩大现SYNTHETIC入口或用scope字符串/allow_live/fixture bool升级。当前没有可合法发行的生产决定。 |
| 生产身份、provider和证据归属 | `worker.py:36–45` 注入transport仅test-only/mock；`natural_spec_runtime.py:45–56,746–805` 强制mock及合成Authorization；`pa_trial_dispatch.py:48–62,290–325,538–543` 强制MockTransport/Attempt MOCK；`natural_source_archives.py:41–49` 归档provenance仅OFFLINE_MOCKTRANSPORT | 需将可信账户/配额及合法后端凭据选择与新实际Run/Attempt/原wire完整绑定，复用现InternModel及发送/捕获/保存guard，仍保护取消/fence/lease和不可重复IO。只能建立新真实身份与新真实证据，不能把旧MOCK/归档改标签成LIVE。凭据由受审后端机制供适配器，不能在HTTP/报告返回；当前不得读取或配置。 |
| 精确软件资格 | `production_trial_admission.py:86–94,114–146` 旧offline账户解析仍调用literal_qualified；生产preflight:103–111缺来源先拒，资格NOT_REACHED | 未来实际生产目标需有可复核的软件闭包和独立资格来源，且原批准绑定真实softwareFP。当前软件不符合旧literal目标的拒绝不能通过修改pin/monkeypatch/新自述对象冒充通过。缺源时后置资格不执行，不能报告qualified。 |

这些是接口输入/输出与数据来源责任，不是建议现在索取token或开启LIVE。源码开发授权不提供真实来源事实；我们也不编造它们。原V5产品§5.5（185–191）要求当前权限交集与撤回，§7.3（323–327）按实际上游账户共享配额，§7.4–7.5（331–343）要求请求/预算、未知用量及价格边界。不能用离线通过抬高真实免费、费用或生产来源资格。

## 可选OfflineSoftwareQualification：本轮不做

当前`OfflineRegistry/_resolve`被旧literal资格拒绝，确实可能阻止在当前源上直接运行专用七槽正链；这属于已知的软件资格前置，不是缺失adapter。新增exact immutable digest+test_only SQLite/mock/MockTransport对象可以成为未来**明确非生产开发设施**，但本阶段不必要：

1. hash只证明所用字节身份，不证明其独立审查与行为资格。让caller根据当前文件自造对象、从而把原_qualified拒绝改为成功，会增加新的资格策略/信任来源；即使LIVEfalse，也不能称未改变原资格保证。
2. 它仍不提供上述真实来源、生产Permit或生产预算policy，也不补新的生产调用行为。为它新增类型/可选flag并跑旧正链，属于相邻设施，不能包装为父任务要求的生产接线完成。
3. 父任务允许非生产Mock资格验证，不意味着必须制造该代码。当前保持_qualified/pin及全部test_only门，未执行猴补资格或重跑已有长链。将来如有独立的设施需求，应明确资格输入由谁审阅、固定闭包与结果、只进入哪条test-only路径、默认旧行为，以及如何证明不能流入HTTP/生产；不能自动把当前hash变成“已审软件”。

准确地说，`_metadata`自身主要核双seal/标量/事件，没有单独的mode条件；它属于经_binding/_identity约束的现归档链，不能误称它本身已有生产mode策略。

## 接续建议与范围

此阶段保持5a生产字节，不为代码数量创建空接口、软件自批准或重复测试。独立准备两份新中性TXT及Goal、事前rubric、私有reference和未评分表，作者不读reference用于实现；只可签收材料/合同/hash和隔离准备，不能填通过评分或冒称真实模型验收。若后续审材料pack，本目录暂不seal；它不影响上述无独立production slice结论。Windows/PG/CI、真实provider/模型/费用/语义、旧永久取消窗口均未执行或提升。
