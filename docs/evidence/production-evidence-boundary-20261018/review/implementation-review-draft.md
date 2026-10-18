# 生产证据模块 WIP：独立静态审查

2026-10-18，基线494cf2e1490967f8cf8621bb48b52fa00713436d；当时未提交生产差异仅新production_evidence.py及production_trial_admission.py五行。只读源码/Git，不执行产品、测试、HTTP、Worker、DB/SQL或网络，不改仓库。当前报告未封存。

## P2：requirements_for的exact类型检查未阻止model_copy遮蔽model_dump（待修）

当时 `production_evidence.py:108–112` 先检查exact TrialContract/V2/PBTrialContract，随后仍调用实例 `contract.model_dump()`。这三个合同继承原非frozen Strict，而Pydantic model_copy(update=...)不重新校验。对一个合法exact合同执行概念性输入构造 `contract.model_copy(update={"model_dump": trap_callable})`，仍保持exact类；新增实例同名属性可遮蔽类函数。helper随后会调用该值，早于SOURCE_MISSING拒绝，违反本模块不调用任意对象方法/回调的边界。

这是**静态发现，未动态执行或宣称复现**；也不是HTTP远程注入或LIVE授权绕过的证据——HTTP strict DTO不能传入Python callable，生产preflight先走旧_approved。问题直接涉及新helper承诺及计划中的forged.model_copy负例；旧上游序列化行为不由本切片补签。

最小必要修复：在访问任何实例方法/序列化前，读取受信exact模型的存储数据，拒绝实例方法遮蔽、额外残留及任意非primitive/不受信nested对象；仅在可信声明模型/容器内递归形成JSON-safe值，再原parse_contract完整校验。单把调用改成BaseModel.model_dump(contract)未证明任意model_copy嵌套值的序列化回调无副作用；无需新增业务接口或扩大矩阵。保存的是本次工具已见代码行及静态构造说明，不声称封存了完整修前源码副本。

## 已符合的有限边界

- 新EvidenceData strict/frozen/extra-forbid；_flat用exact类、object.__getattribute__读取__dict__，拒非primitive后重新schema校验。candidate及requirements的model_copy非法字段不直接当验证过的数据。
- legal/enforced/revoked均显式bool|None无安全默认；只有RECEIVED、revoked is False及两claim is True才结构上满足；null/False/unknown不提升。时间finite、issued<=checked<=reference<expires<=原expiry及30秒约束，now override只是纯诊断参考时点，不进入生产resolver。
- 全数据匹配仅返回CandidateDiagnostic，SOURCE_UNVERIFIED/NOT_VERIFIED/livefalse/dispatchfalse，没有FeeProof、Permit、AccountEvidence或凭据。opaque source/account有界，不承诺其字符串或hash是真实来源。
- canonical_quota_subject通过函数内局部import复用唯一旧算法，当前无模块初始化调用validate_candidate，故未见实际循环导入阻塞：production导入新模块完成定义后再定义canonical；独立导入新模块后首次validate则正常加载production。尚无运行时导入资格，此处仅静审。
- 新resolve_account为NoReturn，无source/record/registry/installer/transport覆盖参数，投影后始终缺源拒绝。preflight在原事务中原_approved后调用它，_qualified/admit仍保留，当前NOT_REACHED；不声明软件资格通过。旧offline _resolve、test_only/SYNTHETIC及全部sender/Grant/executor/预算算法未改。

结论：上述P2修复后可进入冻结及定向实际资格；当前不能把draft写成通过。未发现其它确定P1/P2；不要求真实来源、有效批准、provider调用或旧恢复矩阵。
