# P-A generate3/source2/cold2 业务桥设计独审

结论：设计v1可继续实施，现有controller/adapter/归档可支撑该真实软件切片；无需真实账户才可离线编码。当前没有必须放弃该切片的架构依赖，但下列几处接线条件不可省略。尚未有实现或资格PASS；实际HEAD首次核为 `4bb3c26f5f67511795771c9187537aee4e852590`，clean。

## 实际复用路径

Worker.reserve（worker.py56–280）已保存Core STARTED Attempt、reservation、完整wire指纹、generation/NS参数及原请求归档。pa_trial_dispatch.request_captured（538–568）接现GA/NS原guard与同实际InternModel；GA process三次调用分别保存resource.read、实际checker反馈、最终candidate；NS advance_model维护PREPARED→DISPATCHED→VERIFIED Operation和实际结果。原_generation_accounted（natural_live_admission.py576–611）仍消费旧synthetic ledger，确需固定新Attempt版本→journal/capture/body链桥。不能往旧ledger复制新shape，也不能把新receipt当source阶段权限。

现journal重复key只读，因此Core reservation保持原样、journal reserve延至同一次request_captured共享发送核心，是正确时序。Core提交后尚无journal时失败也须保STARTED/占额，不自动resume；缺archive并不证明未发送。P-A新绑定暂拒PBTrialContract，避免误签P-B业务source/extract链。

## 必要最小收敛

1. **阶段精确provider及limits。** 当前GA configured_provider使用 `synthetic-offline-planner`（goal_planner.py206–219）；NS原provider使用 `synthetic-offline-natural-spec` 并应用effective node_limits（natural_spec_runtime.py746–805）。新sender原guard只认planner token且自行造provider（production_trial_sender.py435以后）。共享私有桥必须复用真实原controller选定的exact InternModel/同MockTransport，按确定阶段核原token与有效limits；不能将NS换成planner、放宽为任意token，或把较紧node caps抬回worker默认。wire max_tokens要与该原provider/节点预留一致且不高于trial上限。Core envelope按实际max_tokens，journal按既定保守cap，不能为追求两值相等重写旧预算。

2. **固定Store须覆盖原业务异常路径。** sender自身已捕获Store，但GA正常接收和catch仍多次读取worker.store（goal_applications.py753以后及900附近）；NS局部store虽固定，pa_trial_dispatch原_archive/reject/check_commit仍从worker取Store。若handler造成绑定漂移，仅在sender保facts后抛错，GA catch仍可能对foreign Store开写事务。应在原controller接收/失败路径继续固定captured Store，或在任何private read/write前确保原Store/engine与binding不变且拒绝foreign写；不能只证明新sender的6镜像安全。新binding合同应沿已有safe contract projection重建与重新比FP，不调用任意实例shadowed serializer。

3. **接收事实与业务拒绝分开。** 来源失效/取消/语义失败后，capture、journal和原BodyArchive先同c保存；原Core已知usage也不可丢。若返回错误但有parseable原bytes，需保 `_received_body`、complete及可用 `_received_response` 或在原Store内等价先落Core facts；GA reject_unsettled依raw记录usage，NS raw=None异常分支会canonical=None重归档（NS819–826），可能与桥先存canonicalSHA冲突。桥须遵守原complete/partial BodyArchive canonical规则，不能盲抄capture.canonical_sha256。原后续重复归档只允许同字节同metadata幂等，禁止回填已完结历史。原NS guard会在独立事务标DISPATCHED；后继journal拒绝不应把它冒充未发送/自动复位。

4. **新旧版本及历史proof严格选择。** 新binding不装API/Settings/CLI，不能被HTTP选会计后端。natural_trial_runs.associated_sql含context或任一持久锚（313–326），check_worker/check_claim仍强制旧PATrialBinding+字面资格（329–407），须保留，关联Run不能借新绑定逃门。新_generation_accounted只在原model_source/owner/候选lineage后，以三个实际Attempt上的全新固定版本选proof；mixed/unknown/缺证据/旧账本残留都拒绝，不fallback。历史generation已PARTIAL候选而不是RUNNING，不能复用policy._fresh/check_run去强求其旧lease仍活；当前source/cold执行才走原_stage_current/StageAuthority/Run当前门。proof须逐aid关联wire、envelope、worker/fence/runtime、raw SHA与canonical SHA各自bytes、Attempt RECEIVED+known usage、capture和实际候选，不只数accepted槽。

5. **业务成功仍由原controller证明。** Journal accepted只通用协议/费用会计；GA first read/checker/candidate、NS parse/prove_node/receipt/Operation/typed-result及当前commit_guard不能被新accounting代替。业务错误200即使usage已知、journal接受，也须原Attempt/Run/Operation拒绝并阻断后续source/cold；不改immutable Outcome来假装会计回滚。最终settle_verified不能用journal duplicate代替当前source/Run/阶段批准。公开结果仍live/dispatch/real_source/business_accepted=false，owner PENDING。

## 有界资格与原方案

原V5 F2-T02/T04/T05/T08及AT09/11要求同一真实控制器生成、发布实例、新输入使用；本片3+2+2实际Mock链可证明软件接线，不能当真实模型/语义/整体F2或AT10。建议保持拟3节点：实际时钟7次正链、基于本轮新鲜证据的必要只读篡改、实际known-usage但业务schema错误；不重跑旧19/12/8/9矩阵。

7次1RPM至少需六个60秒间隔；三个业务Run各受原300秒及manifest/action更紧deadline，GA与NS既有独立heartbeat须继续运行，等待放在未预留槽且不占长事务。原控制器fullproof可能耗时，900秒外层应只作有界测试预算，不可因失败延长产品Run/lease/原合同。日志记录实际reserve时差；不改时钟或用sleep伪造墙钟合规。

只读源码/Git/设计，无产品、pytest/collect、DB/SQL、网络、Worker或模型执行，未读取私有留出材料，未写repo或旧sealed。本目录为新未seal审查目录，后续实现/冻结与实际原件另审。
