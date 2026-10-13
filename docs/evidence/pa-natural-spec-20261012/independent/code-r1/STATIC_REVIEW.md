# 自然短规范实现：独立静态 code-r1 审查

**STATIC FINDINGS；IMPLEMENTATION NOT VERIFIED。** 本轮probe/测试0，不把静态推演当实际FAIL。root唯一仓库writer；reviewer只写指定workspace/code-r1，未改repo、读凭据、联网、escalate、启动PG/native/CI或旧取消探针。

本初始快照在HEAD259f583eba6dd6c5580834878da6bd3cb1f648a7、dev/pa-natural-spec-20261012取得16个实际变更/新增文件，原Git diff也保留。来源SHA逐文件在source-before.json，map SHA `3fde928b04c5a3b6476c5a4efade1b4ae1ed0fc48fb31fbb9b1043f25428a065`。以下行号均指不可变source-snapshot，不是持续变化的live树。源/测试在审查过程中由root正常修改；后观察4文件变化另存，绝不称live0diff或最终候选资格。

## 六个具体发现

### S1 — 模型结算末尾没有live门（高，初始快照）

natural_spec_runtime.py750附近先commit_guard，再Attempt VERIFIED/NS_SETTLED、op VERIFIED、SPEC_STEP_VERIFIED，最后仅spec.receipts。这些证明按此前captured current/binding验证原文/节点/锚，没有最后重新读取lease/stop/GoalHead/current身份scope/CAS。末事件callback若改变Goal、lease或cancel，可让本节点VERIFIED，虽下一步保存会拒绝。合同要求迟到/取消不能VERIFIED，后来save门不能替代这个门。

root已采纳且后观察代码825+实际补commit_guard/enabled/fresh bound/原auditFP相等/fresh完整receipts；RAW先存事务未改。**只静态看到修复，未实际跑。** 留初始源码；冻结后建议在SPEC_STEP_VERIFIED callback改Goal/lease/cancel/原audit/current参数，证明VERIFIED事务回滚而RECEIVED raw随后以REJECTED_KNOWN保留。

### S2 — 本次审计遗漏NS_REJECTED（高，初始快照）

ledger_digest382–414只取NS_RESERVED/NS_RECEIVED/NS_SETTLED/MODEL_RESERVED，漏NS_REJECTED；counters126+对它仅检查唯一aid属于rows；prove_node326+的VERIFIED分支不要求没有reject锚。故末save callbackappend同aid的NS_REJECTED可能不改变digest/完整节点证明，产生“已拒绝”证据仍成功。是受控损坏一致性推演，不是已证实外部攻击。

后观察实写digest纳入NS_REJECTED，counters精确锚集合按STARTED/RECEIVED/VERIFIED/REJECTED_KNOWN对应，VERIFIED不允许NS_REJECTED。初始与修后diff保留。未跑动态；建议一次末save追加reject的全local事务rollback和正常REJECTED历史正例。

### S3 — 新样例预览没有完整绑定已checked样例（高，初始快照）

goal-application.js53–57只核sample.candidate_fingerprint指针、0requests/0writes/外层UNKNOWN和source_retention，没有sample_fp==candidate.model_sample_check.sample_fp或可重算sample_nodes，也未核展示facts/source/内层semantic状态。受控200改显示facts但保留这些指针可能让用户确认不同于真实checked样例的预览。sample_preview794+最初只返回flattened report，不能从它唯一还原两节点sample分配。

后观察端点已返回实际sample_nodes，UI verifyNaturalSample规范hash绑定candidate/sample seal，Unicode codepoint exact引用/原文SHA/来源/原Goal16/固定UNKNOWN/完整report重建；caller哈希后current gate仍在。此修法可静态关闭所述自引用缺口，但未跑malicious200或正常页面；需冻结后实证，不将UI增加hash当PASS。

### S4 — fail_owned对原AppRun错链接仍写错误（中，初始快照）

fail_owned536–563仅按AppRun.id/principal/status更新，未核instance_id/release_id/request fp；header/internal:appRunID门能防替换另一个AppRunID，却不防该原行被损坏指向另一实例/版本。错误处理可能修改已错scope历史。仅使用ID投影核对应完整元组即可，不需读private input/output/old契约。

后观察代码实加binding iid/release/request_fp、独立ACCEPTED tuple和AppRun UPDATE exact对应谓词；无效pointer只写原Run error。未跑故障；冻结后在返回期间损坏这三个scalar，确认foreign/错链接AppRun未改、protected full cell0。

### S5 — S1修后仍需精确version/created_at CAS（高，后续静态建议）

fresh commit_guard核当前lease/身份/Goal/绑定，却不比较Run.version与settlement入口current.version；它用fresh created_at重算budget。callback仅改version或把created_at向后移、保持RUNNING/lease/fence时，fresh门可能接受新scalar。正常reservation/模型step不增加Run.version，故可比较入口version/created_at及既有scope/fp/key；末次按入口absolute deadline。将原created_at/deadline封到natural_spec reservation meta还能为跨节点提供独立锚。不要改旧family/提高budget。此项已经通知root，尚未在本后观察快照认定已修，未动态复现。

### S6 — rejection operation UPDATE没有run_id（中/高，初始快照）

797–805拒绝handler的operations UPDATE只WHERE id/status；sender_guard和VERIFIED更新也只有id/status。返回期间operation.run_id错链后，bound/counters会拒绝，但catch可能仍把已移到另一Run的DISPATCHED op改REJECTED_KNOWN。补原job.id的run_id谓词即可使owned写保持scope；Attempt raw/reject已经有run_id谓词。此为DB受控损坏一致性，非真实授权攻击；建议错链接故障时保留owned raw，foreign op不变。本后观察尚未认定修复，未运行。

## 其他已读关键接口

- 专用Worker.reserve(natural_spec_request)与planner/generation互斥，不落protocol_pool；effective/reservation_check在扣额前取Settings∩candidate∩frozen∩action，exact context与canonical messages；显式MockTransport/store.test_only/mock/noLIVE/defaultDisabled。sender exact request bytes/endpoint/POST/synthetic header再gate，absolute deadline，未借MockModel/offline replay。
- raw response归档独立tx只写已知owned Attempt ID/run_id/status STARTED/response NULL并保存NS_RECEIVED；immutable参数不改。随后当前授权/fence/live检查才quote/usage/model/schema解析及VERIFIED。原响应证据保留不等于可执行；unknown/已received-invalid不能重发。receiver/fail_owned读取metadata projection，不应访问旧protected全文；此轮只是读源码，未做UDF calibration。
- 已知参数含node/ordinal/op/intent/plan FP/limits，NS_RESERVED full params/reservation FP、NS_RECEIVED full reception FP、NS_SETTLED fullAttemptFP；prover回放exact wire/full response/model alias/usage/quote，primitive工具重算。原labelled bound分支仍0requests/repairs/tokens和Attempt空；自然节点计数单独，tools不含model operations。
- save复用原pa_spec事务；原generation audit fp与本Run ledger_digest入口/最终比较，resource/read grants/effect/op+intent/typed/i.dataCAS/terminal同tx。末save还核exactscope/fence/key/version以及原lease/deadline。模型此前不可退款reservation/raw合法留存，不要求整个模型Run全DB0writes。
- natural_specs没有语义关键词分类器；模型决定原facts/kinds/relations，source≤2048B/40lines、unicode_scalar_index.v1 exact quote。序列postcheck是真实citation_feedback，merge是完整first+second加法（重复ID/8item越界拒绝，无去重/删除），uncovered为实际spans机械补集，report保留fulltext/所有human16、UNASSIGNED/OPEN、semantic NOT_RUN/owner PENDING。8000字符越界失败不截断；MD只派生。
- recipe4/6节点，1/2模型、read/merge/verify/save local≤4，原ID/ops/ports/edges保留；既有连续topological prefix实现串行调度逻辑并行图，不证明同时发送。初始prototype的本文未验证所有可能DAG/tuple异常。
- compile reconstruct exact candidate、sample onlyfp在public app、新目标MODEL_EXECUTION_REQUIRED preview不调用模型；actual source/Goal来自bound target，新runtime messages不携旧sample答案。UI确认有独立SAVE consent，原key POST未知GET恢复及current/edit/identity/selection guard沿旧框架；自然sample integrity新增门仍需实跑。

## 冻结后有限优先验证

优先完成S1/S5的最后event scope/version/time变更、S2完整reject/digest、S6 moved operation、S4 wrong AppRun scalar与protected read barrier、S3受控200；同时跑single/dual-independent/dual-sequential真实offline sender/SQLite worker、cold新材料、Goal16、8facts/8000cap、defaultOFF/unknown原key、quota/account shared、old0 labelled与两个旧literal资格代表。预算0真实模型/费用，synthetic输出不能算语义PASS；此阶段没有自行展开完整大矩阵。

## 状态与证据

初始source-snapshot16项和tracked-diff.patch不改。source-after-observed与source-after-observation4文件/author-observed-update.patch仅记录root后续正常变化；S1–S4修法实写与所有6静态发现分开列，未宣称动态通过。root确认S1后再在mutable树补其它门，最终仍需新冻结任务。

本轮实际测试0/PASS0/FAIL0；所有新动态、真实模型/收费、凭据检查、PG/Windows/native/browser/CI、old取消精确窗口、wheel/真实升级/全P-A/P-B语义NOT_RUN。待S5/S6具体修复及最终冻结后才能签任何实际验收。
