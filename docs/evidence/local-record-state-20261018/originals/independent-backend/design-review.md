# 本地记录业务族：独立设计审查

审查基线为 `5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`；本人不写仓库，父级唯一产品写入者。尚未审阅未落盘实现，下面是设计判断与实现硬门，不是已确认源码缺陷或通过结论。没有执行测试。

## 判断

新增固定 typed 本地记录收集/状态版本，是原 F2-T06 的端到端缺口。它可以继续使用 **artifact.save_text@1** 的 project_write/transactional 效果及已有 user∩projectruntime 授权，不需要新增注册 executor.ref、写 Grant 或 Principal。必须如实称为新增的受限业务合同/typed适配器，不要描述为旧报告换名或“零业务逻辑变化”。低层保存只证明受控文本资源真实落位及回读；record_id、revision、合法状态、投影和CAS由公开、严格的新业务合同负责。

既有 write_text_artifact 会为新成果增加既定 resource.read 派生Grant；授权已明确保留该行为。它不能被写成0新增Grant行，也不能让新API在读取/重试时补回已撤销Grant。身份写 user_and_project_intersection，准确披露复用projectruntime，不能冒称独立App Principal。

原方案依据：docs/分阶段开发计划.md:98 F2-T06；docs/平台产品设计.md:99、103 记录读写/typed表单及状态；:158 权限声明不授Grant；:195–199 durable202/同键幂等/版本比较；:207 业务记录属于AppInstance；:383 业务效果与回执同事务；:452–456 Release与业务数据分离。

## 最小真实业务合同

- CREATE接受title(1–200)/details(≤2000)，服务器分配record_id和revision=1、初态OPEN；不能接受用户自由JSON/text绕过typed schema。
- SET_STATE仅接受record_id、expected_record_revision、target_state=DONE、reason及公共instance/release/data_version前置条件。第一个切片不允许偷改title/details、任意状态或跨实例引用。
- 固定、版本化“typed command→唯一canonicalJSON event”的映射与typed schema必须保存在新family的不可变定义/批准和接受Run中。ActionSpec输入text/输出resource_id+hash保持真实；Manifest若只描述text，仍须冻结上述产品级typed合同并在每次派发前独立核对，不能藏有未记账的实际字段/转换器。
- 每次显式业务提交产生新Run/AppRun/Operation及一个不可变JSON事件；事件含kind、server event/record标识、record revision、actor、iid、release、当前字段、状态及前一事件hash。当前事件不要含自己的artifact hash形成自引用；artifact资源引用/内容hash置于结果封装。
- internal_instance_data继续 `{result: <typed event与artifact引用>, release_ref}`；独立projection从完整、经证明的事件链折叠为按record_id索引的当前业务状态，另提供逐record历史。不能只取最后一个AppRun.result当“记录集合”。至少创建A/B再将A变DONE，证明A@2 DONE、B@1 OPEN、A旧版原字节保留。

## 实现前必须守住的硬门

1. **一个事务。** tools.dispatch自己开tx，不能先dispatch保存再另tx追加业务行。复用现有pa_spec_apps SAVE模式：同一project/iid锁定事务、同一fence下insert原Operation/intent，调用原write_text_artifact、回读原JSON，写local_effects/VERIFIED receipt及typed事件，CAS推进data_version/record revision并终结Run。最终当前write/read权限、租约、取消、版本、预算再检查；任何错误完整回滚artifact、派生Grant、Operation及事件。
2. **旧路由先拒绝再private read/write。** 不入app_drafts只挡app级入口，不能保护共享release/iid/run。当前lifecycle.owned_release_pointer/_read_release会读完整snapshot；internal_api.scope_run可经load_binding(authorize=False)读旧格式body；app_jobs.inspect_job与普通/api/runs/{rid}、Store.inspect/commands/reconcile也需核查。给新family一个独立、标识专用的metadata gate，旧共享入口在读取typed/private payload前strict-reject；只有专用新API及normal Worker的精确family分支进入新verifier。不依靠最后namespace报错，也不依靠contextflag单独决定家族。
3. **缺失标记不能降级。** 独立journal双seal、Release/approval、iid.source_app_id、Run/AppRun binding和accepted Run metadata交叉核对。移除一个marker/伪造一个namespace/context flag时，任何剩余新family提示仍应fail closed；不能掉回旧CSV/自然规范/ordinary模型循环。
4. **先授权，后内容。** 首先只读取owned project/iid/release/Run及artifact标识，核对独立指针，再授权project保存交集及将要读取的全部历史JSON，最后才读typed event/record title/details/projection。不可用project write替代历史resource.read；撤销某历史JSON读取后，不从instance_data、缓存或旧receipt泄露内容。metadata停止/恢复范围另外明确，不把业务state/title当无条件公开metadata。
5. **两个CAS。** 记录revision、实例data_version、Release/fingerprint在接受时与真正保存时都核对；拒绝未知record、跨iid引用、重复CREATE ID、bool冒整数、跳revision、断previous hash、非法跃迁及在途冲突。服务器从历史推导下一revision/current snapshot，不能信客户端回传旧业务字段。全局data_version可以先保守串行化，避免扩大并发实现。
6. **真正的事件证明。** 每条事件必须对应本iid的精确接受Run、同Release、一个成功AppRun、唯一VERIFIED save Operation/intent/local_effect/receipt、实际JSON内容hash和typed fingerprint；链上ID/revision/previous hash及当前projection独立重算。成果指针污染不能授权或读取另项目/private对象。
7. **预览与幂等。** preview不保存JSON、不新增derivedGrant/typed业务行。202之前冻结typed input与原key；同key异body冲突，同key同body只返回该原运行且内容重新授权，UNKNOWN只原GET恢复，不因刷新或导航重发。Worker旧fence/晚回调不能产生第二业务事件。保留原失败/取消历史。
8. **页面与家族诚实。** 显式表单→预览→确认→保存中的新Run→实际回读/当前列表/历史；记录DONE不是语义人工ACCEPTED，不借自然owner ledger自动签收。固定配置表单不冒称真实模型自主生成或完整P-A/P-B通过。新增族的Release更新不删除旧业务事件；首片可拒绝切换而保留授权历史。

## 最小验收建议

一个实际HTTP/JSDOM正例：选目录/实例，创建A、创建B、显式将A OPEN→DONE，三次正常NoModel Worker；独立重算当前集合/逐record版本，冷独立Store回读，核对artifact bytes、Operation+typed事件和旧数据/权限变化只限预期。再各一项有界真实CAS冲突/撤权无写，以及账号/项目/实例导航迟到和双击/UNKNOWN原GET。无需重做相邻恢复矩阵。测试必须分别统计新成果派生readGrant与禁止的新writeGrant/Principal，并验证preview不保存JSON。

当前没有因该设计本身需要扩大执行器/写权限授权的阻塞；上述前置门需等实现落盘后作为非作者源码审查与最小真实验收的重点。未运行真实模型、Windows/native、PG、远端CI或部署。
