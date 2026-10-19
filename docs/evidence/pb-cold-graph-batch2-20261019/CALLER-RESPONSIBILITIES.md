# 第二批私有事实叶调用责任

这些叶不是授权入口或完整verifier。当前只由原公开路径在原位置调用；未启图、没有跨调用/跨写缓存。未来新调用者须先在同一Store/Connection/事务和读epoch内，按原permission-before-body及首错顺序取得全部原始多重集、完整历史、确切角色/ID和完整Limits，再调用对应叶。敏感回调后仍实际复核权限/owner/批准/source/Run/fence/期限；事实不能跨写传成许可。任何不足不能通过公开verifier fallback补证。

| 叶 | 调用者必须先做及保留的后续检查 |
| --- | --- |
| pb._source_proof_fields | 原source_gate→成功状态→owned Run→verify_job(完整角色Limits与全部receipt/history)→原candidate检查→typed SELECT；draft/snap/app_run保持typed读前别名。此叶仅纯前缀，之后原位置执行完整fresh source_audit，未完成audit不得发布Source proof。 |
| pb._review_source_from_facts | 输入完整Source proof及完整request；先比较Source指纹/recipe，再允许target IO。此叶不读取或验证Source历史/权限。 |
| pb._review_from_facts | 已完成Source比较，随后通过原target current Goal/材料/权限门；传完整Goal、不同材料/hash、完整Source proof/audit和caller Limits。源manifest继承Limits与caller编译Limits独立；不重入source/target。 |
| archive._body_payload_from_facts | exists→pair/seals→完整owner/run/aid/runtime/project→fresh evidence_mode/provenance/phase→完整anchors SELECT均已按原位置执行；叶只核完整anchor列表/extent/completeness/encoding/原始bytes/hash，不能代scope或Grant。 |
| archive._source_slots_from_facts | 先完整批准、Source Authority、完整accounting/ledger、全量Attempt SELECT及fresh evidence_mode；不能投影两条后假装完整历史。保留原slots顺序与基数；typed Ledger仍需原完整校验。 |
| archive._source_keys_from_facts | expected_ids来自完整已核Attempt多重集；keys必须是当下完整archive key集合。原REQUEST后RESPONSE顺序；缺少先OUTCOME_UNKNOWN，额外按原VERSION_CONFLICT。 |
| archive._source_exchange_from_facts | 全量rows/slots、mode/status/model/accepted已核；原REQUEST _read后RESPONSE _read，身份/seals/anchors/完整bytes均已核。传原角色contract/caps，原始hash与canonical hash分开，不是Source许可。 |
| trial._journal_attempt_from_facts | 原owner→metadata/body完整链→slot→capture/raw/canonical→实际Attempt SELECT；保留_journal_slot中的完整policy._bound/TX/ledger/typed以及current批准/角色/fence。此叶仅actual/wire/caps绑定尾部。 |
| trial._stage_slots_from_facts | 原stage-owner/phase/权限、app_run key、全量ordered Attempts、Generate3/其他2基数、全部backend/account marker、实际Run及完整_journal_state均已核；此叶不替ledger或scope校验。 |
| trial._stage_usage_from_facts | 每个实际aid已完成_journal_chain及原顺序，传全行checked==actual，不能只验hash；随后仍执行原Generation archive分支或NS双_read/Operation分支。 |
| trial._stage_source_archive_from_facts | 前置完整same-aid chain、usage和原REQUEST/RESPONSE _read均已完成；传完整原始NS/controller bytes，不仅摘要。叶之后仍在原位置实际SELECT并要求Operation VERIFIED。 |

第一批约束继续成立：policy._bound_from_checked_facts不替代事务检查、_requirements、完整_ledger及quota/identity typed验证，也不执行_fresh；generation._check_counters_from_facts不替代前置_check_counter_rows。此次未让第二批绕过这些入口。

公开路径仍共享唯一谓词实现；pb.verify中的name SELECT短路顺序、Source audit全字段集合、sender/reserve/reject/租约/五写与其他运行家族不改。第二批不是完整history或DAG平直完成；首证完整指纹及祖先独占成本仍UNKNOWN，完整P-B仍保留上一轮FAIL_NOT_ACCEPTED。
