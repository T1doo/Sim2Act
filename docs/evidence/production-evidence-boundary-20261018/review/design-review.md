# 生产账户证据来源边界：独立设计审查

2026-10-18；只读基线 `494cf2e1490967f8cf8621bb48b52fa00713436d`（实核HEAD/clean）。未执行产品、pytest、HTTP、Worker、模型、DB/SQL或网络，未改仓库；本目录新建，所有旧 sealed 目录未改。

## 结论

**设计可进入最小实现，无已知设计阻塞。** 有限产物应精确定义为：生产账户证据要求、无权威候选数据诊断，以及“可信生产来源尚未注册”的failclosed接点。它在现有工程基础上补明确的生产证据来源边界，具独立交付价值；不声称已实现生产账户解析、真实免费权益、强制不可收费、生产FeeAuthority或sender，不产生任何有效LIVE能力。

## 实际已有及尚缺

- `production_trial_admission.py:26–48` 的 AccountEvidence明确SYNTHETIC_ONLY；`:110–143` 的旧解析器只接受test-only SQLite、exact OfflineRegistry/OfflineSender/AccountEvidence，核账户canonical quota、30秒新鲜度和完整软件资格。该路径不能改造成生产来源。
- `pb_live_source_contract.py:1–6,117–143` 已有PB运行归档来源合同、protocol、固定合成resolver与livefalse receipt；这是实际执行来源，不是账户免费权益来源，不能重复包装为生产账户resolver。
- `natural_live_admission.py:218–264,862–923` 已有FeeProof/Permit和默认拒绝，只exact SyntheticOnlyFeeAuthority及test-only SQLite可返回不可LIVE的Permit。`natural_trial_api.py:30–44,157–165` 现有strict DTO没有来源/免费/发送器字段，两admission route共用production_preflight。
- `production_trial_admission.py:96–107` 当前先原 `_approved`，再literal `_qualified`，最后无生产authority的admit；未有生产账户证据来源入口或注册实现。新增显式缺源resolver可补此边界，不能忽略原有门/总账而重造。
- 原V5产品 `docs/sources/V5/平台产品设计.md:185–191` 身份权限与每次当前授权，`:323–335` 共用上游账户配额主体与原请求记录，`:341–343` 有限预算/未知用量与价格不推断免费。本切片符合这些边界，但不提升完整真实链、R0或正式发布。

## 收敛后的接口与约束

1. **EvidenceRequirements**：strict、frozen、flat、extra-forbid。仅从已经通过原 `_approved` 的exact TrialContract/V2/PBTrialContract投影本人/项目/trial/完整contractFP、固定provider/model/endpoint、quota_subject、原expiry和paidcap0；不信HTTP额外字段。完整contractFP已包括材料Goal、runtime、软件授权及预算；若诊断不包含原approval key，需明确其不证明具体批准。严禁把caller给的requirements当已批准或当前授权。
2. **AccountEvidenceSnapshot候选**：同样strict frozen flat；opaque account/source_id、exact作用域、issued/checked/expires、revocation与legal_free_entitlement/enforced_non_chargeable的严格bool或None、两种证据hash。未知撤销不得默认False；必须显式False才数据上满足。两种权益未知/False不能当True；值全True也不证明来源。source_id限定有界opaque标识，不是URL/文件路径/secret；不容纳凭据、可执行callback、任意metadata或原始证据正文。
3. **validate_candidate**：纯数据一致性诊断，不读文件/凭据、网络或DB，不调用source/callback。先exact类型/严格parse再访问数据，防任意对象属性/model_dump回调。quota规则复用原 `production.canonical_quota_subject(account_id)`，不新造可拆账户桶；无需更改旧offline算法。时间须有限，issued<=checked<=当前参考时点<expires<=原expiry，checked距参考时点<=30秒；不刷新或续期。该30秒只是既有保守工程约束，不声称provider已确认规则。
4. 诊断报告无论数据齐全与否都恒 **SOURCE_UNVERIFIED、live_allowed=false、dispatch_authorized=false、fee_verification=NOT_VERIFIED**。可报告data_consistent及固定原因码，但不能返回AccountEvidence/FeeProof/Permit、VERIFIED免费/已准入状态，不能把bool/hash/source_id等同真实权威。当前无任何安装、注册、自动发现或HTTP诊断/批准入口。
5. **resolve_account**：生产代码无records/source/registry/FeeAuthority/installer/transport覆盖参数，无可执行plugin路径；只投影原已批准合同要求，因无支持生产source明确抛LIVE_BLOCKED（建议NoReturn），不取凭据、不构建许可、不写账本、不reserve。数据诊断不能经此resolver升级为生产证据。
6. **preflight顺序**：原transaction内 `_approved` → 新缺源resolver → 保留原 `_qualified` → 原admit。先当前主体、两READ+SAVE及Goal/material/auth/software等原检查，再报告缺源；不把缺源错误暴露为跨租户数据oracle。无source时提前LIVE_BLOCKED改变先前literal软件资格可能先VERSION_CONFLICT的错误优先级，属于安全收紧，不给不合格软件权限。原literal资格未执行时标NOT_REACHED，不能称已通过；不得改anchors/pin或绕过已有软件拒绝。后续任何生产source实现仍须另行审阅，不能删后置门。

## 最小合成资格建议

在同一冻结源下核纯候选作用域/账户quota/未知或False/撤销/过期与新鲜度/paidcap/额外字段，以及全部数据吻合仍只有非权威诊断。使用现有owner真实API及原精确同意合同验证无source明确LIVE_BLOCKED、strict额外source/fee字段422、原READ/身份拒绝优先、全55表不变；不新增sender、Worker、真实费用探测或模型请求。foreign callback/registry不能通过函数接口进入，也不能被调用；既有SYNTHETIC Permit仍livefalse/test_only隔离不变。预算/未知用量/重发沿旧控制器，不重做七槽/恢复/旧撤销窗口。

以上仅设计静审，不是新代码或实际资格PASS。不得设置token、启用LIVE、注册provider/sender或生成有效批准；真实来源、账户合法权益和强制不可收费证据当前仍缺，Windows/PG/CI/真实语义不因该切片关闭。当前目录尚未封存，待实现/冻结/闭合原件另核。
