# Trial/stage/Run 同事务关联的有限后端切片

基线 `a8dc3e0eccb6c40fa22e1459482cd7dd202e979a`，独立分支 `dev/pa-trial-stage-association-20261016`。开发期扩大回归冻结 `dcfbcb985c14d98f1cd7b3a375f9d4f9373f3afc`；最终受影响切片冻结 `e6b29ee19fb6a8fcd9b51d3081f2ad082e2c7aaa`。根代理为唯一产品写入者，独审只读。原 main/core、原 owner WIP、旧锚与此前封存证据未改；本轮未删除缓存或任何旧目录。

这是可独立开发的 server-controller 后端协议，没有新增 HTTP 入口或页面操作；没有把普通 Worker 冒充已获软件资格的绑定 Worker。

`natural_trial_runs.py` 用 prepared P-A V2 的原 Generate/Source/Cold key、完整合同和批准建立关联。Generate 使用机械拆出的 `Store.submit_tx`；Source/Cold 使用现有 `app_jobs.enqueue(logic_tx=c)`。Run、两组配对关联、context marker、事件同事务提交，提交后重核批准/资格/来源；任何失败整笔回滚。普通旧 Run 不得被原键收养；重复受理只返回同一个 Run，变更输入冲突。仅元数据的 original-key recovery 不再执行、延长或返回私有材料/Goal；fresh Goal 漂移、过期和撤销后的历史读取不恢复执行权，撤销资源读取权限仍拒绝。

`Store.claim` 以 scalar marker 或任一持久关联侧识别任务，普通 Worker 跳过关联任务，V2 绑定 Worker 仅领取同一合同/批准且具备原明确阶段批准的任务。未批准阶段保持 QUEUED、fence=0、零 attempt。V1 只保留原精确 Generate key/已批准阶段身份的兼容选择，不领取其它普通任务。关联绑定原 created_at 和冻结合同摘要；claim 在完整证明后、实际写前、CLAIMED 写后严格使用同一原 Run/合同最小截止，迟到写回滚，不能用续租或篡改 created_at 延长。handoff900 只约束明确批准，已批准阶段仍受各自原 Run≤300/原 execution/lease，不能把 review 窗口当 dispatch TTL。

`Worker.process/reserve` 防直接调用绕过关联检查；reserve 与 Generate 最终写组在原事务内重验；`pa_spec_apps` 原完整 guard、最终实际写和 readback 仍在原事务内重验关联。所有原账户、fee、ledger、权限、软件资格、实例/来源、取消、租约和预算门保留，未复制执行器。

初审 CHANGES_REQUIRED 的四项问题及截止 TOCTOU 均保留独审原文，修复后冻结静审未发现新增提交阻断。开发批次 20P、27P、31P 分别保留，不累计为独立节点，也不冒称最终冻结验收。Ruff 最初35项格式/fixture问题、后1项 fixture lint，最终变更文件检查 PASS；原日志不覆盖。

最终33项协议测试中的正向场景只替换 literal qualification；Source/Cold 正向还明确替换 enqueue/lineage 为有限合成依赖，最终写故障测试明确替换账户/旧 commit 边界。它们证明事务/原键/排队/回滚约束，不能证明实际绑定 Worker 或真实应用完整闭环。真实 `_qualified()` 拒绝路径不替换，实测 VERSION_CONFLICT: Current software differs from the exact reviewed literal target，且全库不变。其它原有真实 Mock Worker 回归是其各自普通/合成路径证明，不会给新 coordinator 自动授予资格。

## 实际结果与完整失败历史

最终 `e6b29ee19fb6a8fcd9b51d3081f2ad082e2c7aaa`：144个唯一节点 PASS，0 FAIL/ERROR/SKIP。新增协议33项、原 trial111项。主批143P、1项deselected（368.09秒）；该原RPM=1七槽节点在隔离进程1P（361.62秒），不是SKIP，不放宽速率。两个进程实际exit0、未超时、受限模块导入尝试/加载均为空。512份src/tests/pyproject前后摘要一致，HEAD相同、测试期间tree clean。最终Ruff仅变更五个文件检查PASS；mypy未运行。

开发期 `dcfbcb985c14d98f1cd7b3a375f9d4f9373f3afc` 扩大套有279唯一原节点记录：275P、4F、0E/S。原111P、新31P、扩大137项133P4F。它不是最终e6的279项完整重跑，不能迁移SHA或宣称全绿。四个实际失败完整保留：

- `test_goal_card_runs::test_source_damage_before_worker_zero_model_requests[grant]`：Worker.once返回False，原测试要求True；精确a8基线同测试也1F，原行为在claim前拒绝撤权任务。未改测试预期。
- `test_natural_spec_apps::test_rejected_scope_damage_never_mutates_other_history[missing_slot]`：STARTED不等于原测试要求的REJECTED_KNOWN；精确a8基线同节点也1F，未修复或改标SKIP。第一次基线比较因漏573字节原gold fixture而collection ERROR，原log/XML保留；仅补同一Git基线原件后第二次实跑1F。抽取120文件逐一与a8 Git原件核同。
- `test_queued_revocation_updates_pair_without_private_body_reads` 与 `test_revoked_receiver_only_preserves_owned_raw_no_protected_full_read`：扩大前漏筛了函数内部 `sql_private_barrier` 导入；既有 `pb_allowed_imports.StopRestrictedImport.find_spec` 在导入前分别抛 `RuntimeError: Known restricted diagnostic import is not allowed`。实际计2F；模块加载为空、诊断本体NOT RUN。没有去掉保护插件、换工具/路径或重试这两个节点。原历史工具拒绝完整范围未在本轮补造；这里只处理已知精确目标。

扩大主批因本地监控窗口不足而主动SIGINT分批，原批named150P4F、另一个无名time-only reporter为UNKNOWN，绝不算PASS。原汇总脚本解析无名reporter TypeError、exit1，原文件/错误不覆盖。按原collection，保守保留已有后续完成证据的前152项；同一dc冻结续跑剩126原ID，全部PASS；加隔离RPM节点，279唯一覆盖完整。尾2项重验去重；受限节点没有重跑。四份512文件manifest完全一致。中断fixture/数据库、原XML、所有原case包和命令均保留。

扩大套之后另加冻结源码外的两条精确红测：最后资格检查返回时才到execution expiry，Generate/Source都DID NOT RAISE，实际错误提交。这2F不混入279，也不隐藏。阶段正向使用明确合成lineage依赖，不冒称真实provider事故。最终e6仅在原 `_qualified()` 后再完整 `_approved()`（3行实现），另增对应2项测试（25行），使晚到资格/原授权再核失败整笔回滚。db.py、worker.py、pa_spec_apps.py在dc之后未改。最终33+111在e6重新实际通过；原红测原件和首次静审遗漏一起保留。

只支持有限后端协议切片的开发结论。完整页面、实际新controller绑定Worker、当前软件资格和生产验收仍未通过。最终144P不表示开发期四项失败已修复，也不表示未跑的其余扩展路径在e6全绿。

## 当前软件资格的具体缺口和最小步骤

现有资格只列86个实现文件；当前完整88文件集合相对其规范化 files 新增 `natural_trial_preparation.py`、`natural_trial_runs.py`，另改变 db、natural_live_admission、natural_trial_api、natural_trial_budget、pa_spec_apps、pa_trial_dispatch、worker。`text_continuations.py` 原 pin 的唯一64字符置零后没有额外差异。原 anchor SHA `24f26f3621b8fc49a24fa3566484b568148d9317f2d279d79f264416b994193a`、qualification SHA `f8ec19c731ab5ac1f675d909bb6186febb381c9deebd9a705ba05cf440c7f5a5`、CHANGED 和全部资格执行代码原字节未改。旧 proof 的 review_baseline/review_candidate 是其历史合同字段，不能当作当前冻结 SHA 的独审证据。

1. 固定待审实现全集、完整 SHA 和逐文件原字节摘要，并把当前两新增/七改变文件与86文件资格、原两检索锚逐项对照，审查真实权限/执行/历史边界；config 排除及唯一 pin 64字符规范化保持原规则，不能加文件名豁免或放宽 UNKNOWN/语义依赖。
2. 在已有允许的隔离测试条件下，完成当前冻结目标的资格/篡改矩阵、两个既有锚的原实例/历史/权限/深层校验及受影响通路复验，保留所有失败和独审结论。本任务的新协议合成测试不能替代这些证明。已知拒绝的私有 SQL 诊断和浏览器路径在这里仍不执行；若所需校验只能依赖这些受限动作，则明确该证据缺口，由原授权流程处理，不能改工具/路径绕过。
3. 只有上述具体范围得到独审证明后，才可按既有完整 files manifest + 单 literal pin 的流程提出独立资格更新，附当前冻结 SHA/原证据/精确范围；保留严格 schema 和历史字段的真实含义。若需改变资格合同元数据或协议本身，单独审查，而不是自行写入“已合格”。本轮没有执行任何 repin、锚重建、豁免或资格授权。
4. 资格更新会改变实际 implementation fingerprint；需新 prepare/精确批准以及适用的逐实例软件许可，旧 trial/Release/人工决定不自动继承。先重新执行真实 `_qualified`、批准/撤销/版本漂移及服务器绑定 Worker 的离线有限链路，最后接页面。软件资格通过仍不等于存在生产零收费账户 resolver/sender，也不授予真实模型或付费调用权。

Windows、PG、原生浏览器、真实模型/费用、实际绑定 Worker 的新 controller 完整执行、页面 Generate→candidate→Source→Cold、完整 P-A/P-B业务验收、旧用户升级、部署、远端 CI：NOT RUN/NOT ACCEPTED。无凭据配置、权限扩大、真实模型请求、付费 API 或强推。

## 交付证据

[最终独审](../evidence/pa-trial-stage-association-20261016/FINAL_REVIEW.md)、[最终结果](../evidence/pa-trial-stage-association-20261016/FINAL_RESULT.json)、[完整原始证据归档](../evidence/pa-trial-stage-association-20261016/complete-originals.tar.xz)、[归档核验回执](../evidence/pa-trial-stage-association-20261016/BUNDLE_RECEIPT.json)。归档逐一核验 1195 个原始文件，SHA256 `0edf56108b44d0d09c67d706f75d353e5e0427a2d2cbe8558d6025f1934ed71d`。包含所有失败、中断、基线对照、红测及独审检查历史。
