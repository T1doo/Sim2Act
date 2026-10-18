# 冷页P-B原key恢复：非作者合同审查

基线`1f725e8318a9f3993e782335203d5b2e76085c0f`，实际checkout clean，`/workspace`约25GB可用。父级唯一仓库写入者；本阶段仅只读源/文档/既有原件、纯hash，零产品测试/HTTP/Worker/模型，未改仓库。132生产文件基线及相关读回SHA见initial-source-manifest.json。父级后来告知1f725已有限通过并授权实施；本文件是实施前合同建议，不签尚未存在的实现或测试。

## 已有GET与安全顺序

`pb_natural_specs.py:505–520`已有`GET /api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}`，不新增模型/资源/运行/Grant。它先`:510 source_gate`，然后只按来源Run、主体及原key取app标识；缺失为OUTCOME_UNKNOWN，不是安全未受理证明。找到后load_draft→独立ExtractInput双seal→project/source Run精确相符→当前review→verify→原receipt。

`source_gate:76–123`先项目归属、Run主体/项目/runtime标量与唯一原natural P-A来源家族，拒绝P-B提取链或伪装P-A；job_scope_gate及SUCCEEDED；Run独立scope双seal及真实保存效果/event/AppRun/typed artifact指针一致；当前源成果READ授权先于后续完整Run/回执正文。`_source:301–327`进一步完整verify_job、typed、来源/结果/工具回执和当前审计证明。

`apps.load_draft:258–266`先draft_gate；`text_continuations.draft_gate:456–467`进入pa_spec.scope_gate；`pa_spec_apps.scope_gate:422–479`与`pb.scope_gate:188–210`以标量和独立标记识别家族、目标当前READ/SAVE和源当前权限后，才读取完整candidate/提取双seal。`text_logic_reuse.pair:143–150`要求左右seal完整等值、严格DTO及request fingerprint。`pb.verify:390–408`再核marker主体/来源/key/full body hash、META、当前目标/材料版本、原review/frozen/marker/candidate/name一致。不能绕过这些已有路径改为凭key直接返回旧payload。

`review:342–377`返回完整严格ReviewInput、其hash、source_proof/full hash、原/编辑recipe及hash、完整target Goal/current resource binding、candidate/full hash、确定app/runtime标识、review_fingerprint。`receipt:426–429`返回完整ExtractInput request（含精确review_fp和两literal consent）及重新验证的reviewed；顶层request_fingerprint来自完整ExtractInput。GET仍要求当前来源、目标、Grant、版本和证明一致；不是无条件历史下载接口。

已有`tests/test_pb_natural_specs.py:129–158`检查原POST/GET回执等同且读回不写；`:188–218`覆盖来源/成果/目标撤权及异主体前置私有读屏障。此处仅核源码，不重跑旧授权矩阵。

## 页面实际缺口与裸key结论

`internal.js:65`仅naturalTaskRequests Map；`:695`范围含页内token/project/run；`:675–679`只有Map存在才启用恢复；`:752–760`的GET后逐层验证依赖原pending.body和pending.review，成功后核fresh app再清Map。关闭面板保留Map，但整页重载丢失，既不知道原key，也丢失完整原意图和未知提交锁。

原方案F2-T03 `分阶段开发计划.md:95`与`平台产品设计.md:119–127`要求移除原会话依赖、分别冷会话验收；`PBNaturalSpecExtraction20261013.md:36`、`NaturalPBProductFlow20261016.md:7`及当前完整页说明`:27`均明确该限制。旧e039及491完整正常链已通过，不能假称未实现整个P-B。

裸key在正确当前授权来源下可用于读取服务器已有accepted记录，但不能证明它与已丢失的浏览器原冻结意图相等。把返回request/reviewed的自洽hash当作“原意图匹配”会取消原recover的一层独立比较；而只有输入框也不能在重载后阻止新key/POST。若做无原元数据的人工key查询，必须另称读取已保存回执，不得冒称原未知意图恢复或允许自动续写。本轮更小且满足未知锁要求的路径是元数据durable intent，而非裸key替换原recover。

## 最小17字段记录

单独namespace，例如`pb-natural-spec-extraction-recovery.v1`。严格闭字段列表：

`namespace, principal_id, project_id, source_app_id, source_instance_id, source_run_id, source_app_run_id, source_release_id, source_release_fingerprint, source_result_version, request_key, request_fingerprint, review_fingerprint, candidate_fingerprint, app_id, runtime_id, source_proof_fingerprint`。

这些共17项；向父级首次消息误数18已立即纠正，字段名列表才是合同。ID/key/hash/正安全整数均严格类型/语法校验，不接受多余字段。source锚逐项与当前已完整验证extraction-options.source_proof及当前expectedRun对齐。source_result_version>=1，不能将生成PARTIAL或另一Run当来源。

request_fingerprint是完整ExtractInput的SHA，不能错用review.request_fingerprint；review_fingerprint等于ExtractInput.expected_review_fingerprint，也等于reviewed移除自身fp后全对象SHA；candidate_fingerprint等于reviewed.candidate全对象SHA。app/runtime与review、candidate/manifest和fresh app一致。

存储key/锁范围只含稳定principal/project/sourceApp/sourceInstance/sourceRun，不能复用当前包含token的s.scope。不存令牌、令牌hash、完整request/review、名称、原文、Goal、资源或模型响应。元数据是恢复提示和匹配材料，不是授权凭据；无论记录存在与否，所有来源/目标读取仍走服务端当前授权。

## 生命周期与forget必要条件

复用`OrdinarySpecDurableRecovery20261016.md:5–11`及`internal.js:5–60,379–395`的合同，而非其固定input={}的请求重建。当前已获权来源核对后才读该scope记录。同scope exclusive Web Lock用ifAvailable，覆盖读取旧意图、严格校验、首次保存/读回、POST、GET验证和比较删除；不排队等待后隐式建立新意图。获得锁和每个API/WebCrypto await后核同一视图、原instance对象/instanceGeneration、source Run、workspace、connection、edit/operation代际及原record raw。

首次明确确认后，先冻结body/review和上述hash，在同锁成功写入并读回原raw，才允许唯一首次POST。缺锁、存储拒绝/配额/坏记录、已有记录都不得生成/覆盖新key或POST。冷页已有record只允许显式原keyGET；不能重发原POST。

冷GET必须先独立检查顶层namespace/kind/主体/项目/来源/key、ExtractInput SHA、完整reviewed SHA/candidate SHA以及冻结app/runtime/source proof，再在RAM重建pending。重建不覆盖别的pending，不把尚未验证服务器payload存为新可信原意图。随后保持现有recover逐层比较及fresh `/api/apps/{id}`的id/project/runtime/name/full candidate/canonical/spec_task.source Run检查；新controller可复用同次已收到的GET响应，不能跨请求缓存authority。

成功forget同时满足：仍持同scope锁；同operation/pending、naturalTaskCurrent及捕获各代际均current；fresh app和全部原契约校验已完成；localStorage再次读回的原raw逐字未变。删除必须比较同raw，不能清掉另一个文档写入的新record。先完成清记录和必要state的原子同步安排，不能在删除与设置已保存状态之间再await。导航/身份A→B→A或crypto await期间离开再返回，即使表面ID相同，也不能绘制、交接、聚焦或删另一记录。

OUTCOME_UNKNOWN、403、404、网络超时、版本/指纹冲突、迟到或被替换record都保留原未知锁，只可再次显式GET。PB没有spec-run那样的严格NOT_ACCEPTED/CLOSED证明或close墓碑；durable save之后但POST之前退出也可能永久只读未知，不能擅用普通spec close DTO或时间过期清理。要安全解锁需另一个明确服务端合同，本slice不扩。

合作文档的锁不约束旧版未刷新JS；本地记录被用户整个清除也没有服务端latest-intent fence。复用普通durable合同必须保留这些限制，不宣称跨设备/恶意同源脚本/清存储后的全局exactly-once。无token的完整record协同替换不是服务器授权；不能凭localStorage读私有内容。

## 最小实际验收建议（未执行）

1. 一个新SQLite、真实TestClient HTTP+生产脚本/JSDOM、正常Worker+MockTransport的实际成功来源；唯一提取POST真实201受理后合成丢回执。新DOM不得注入旧Map/closure/body/review，只共享显式Storage/Web Locks平台适配；cold重新授权相同来源，显示原未知key/锁，preview/commit不生成新key，明确恢复只有GET；核全request/review/candidate指纹和fresh app后找回原app/runtime并比较删除。后续另行打开内部版本，不自动创建Release/实例/Run。恢复阶段模型/业务写入/Grant增量均0；完整保存前后SQL快照及HTTP/rawhash。
2. 在该实际路径的有界场景核跨账号/项目/实例/Run和workspace导航ABA的迟到GET/WebCrypto不能绘制或删记录；返回原授权scope再GET可恢复。来源或目标当前撤权后GET403、不显示旧payload、保留未知锁；污染record/receipt完整body或review hash拒绝且POST增量0。仅测试新合同必要切片，不重复旧恢复故障矩阵。
3. 短纯协议用实际controller检查无锁、存储拒绝/配额、闭字段/错scope/错hash、raw替换、storage通知缺失及两合作文档成功竞争：ifAvailable拒BUSY，真实清记录后竞争者也不能因排队产生第二POST。协议模拟HTTP必须与实际HTTP资格分开计分。

原Node/HTTP/资产/Mock/Worker增量原件、精确source freeze和before/after映射、失败轮及observer修正保留。新DOM不等于native browser或浏览器/设备重启；实际人工决定仍不在本slice。真实模型、Windows/native、PG、CI和发布不冒签。

永久取消的精确旧/新安装digest并发窗口保持NOT_VERIFIED，禁止执行/换名/代理重试。本方案不新增require_latest/第二actor安装时序。既有额外只读探针exit139因果仍Unknown，本轮不重试。旧满盘未落盘报告缺口不补回。

本文件只给合同和验收建议。等待父级WIP后另做非作者实现审查与冻结字节/实际原件回读，不将计划记为通过。
