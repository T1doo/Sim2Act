# 独立文本应用自己的GoalCard与精确版本owner签收

基线233ba9618ba462aad19e1ca16f085cd0d7242632；分支dev/text-logic-owner-20261012，root唯一产品作者。接原V5 F2-T01/T08，复用已有GoalCard版本、owner PREPARE/DECIDE/CANCEL/REVOKE账本、普通Worker证据与读取代次门；不另建执行器、不继承旧源/目标GoalCard或签收。

1. 仅已正常验证的独立文本家族。本人在当前目标user+fresh app只读授权下，显式填写完整GoalCard(title/goal/known/assumptions/unresolved/constraints/acceptance_checks/resource_refs)及非空适用范围。constraints/acceptance至少1，refs只能该新材料；新创建自有card，不能传入旧card身份。
2. 新app→自有GoalCard精确版本绑定由独立双seal保存，包含当前app/candidate/runtime/resource/hash/logic/owner/project、原key/body/连续绑定序列。native card与immutable version、绑定双seal同项目锁事务提交，失败0部分写。每次明确修订新版本；期待head版本/指纹及旧绑定指纹CAS，ABA不复活旧签收。原key只GET恢复，不自动POST重发；64绑定版本/app。
3. 执行候选和不可变Release不改写goal或原回执。owner contract另外冻结本app自有GoalCard版本与适用范围、固定字面能力边界、准确Release/实例revision/data历史、当前Grant/logic和实际新输入Worker/typed/Operation/检查。原来源撤权/删除仍不阻断新应用目标签收，不读原私有内容。
4. 完整原始条目、标题、材料范围、各适用范围及固定技术范围均逐项人工ACCEPT/REJECT+非空依据，最多100项，不能缩减/重排/自动生成接受。源签收不继承；模拟选择仅SIMULATED，技术语义UNKNOWN，正式发布false、LIVE0。
5. 使用既有900秒PREPARE、256连续不可变owner ledger与seal/历史/停止余量。保存与读回时重新验证目标材料、独立逻辑、GoalCard/head/绑定、app/Release/实例及所选真实新输入证据；变更使旧签收STALE或拒绝提交。停止在撤权后仍允许本人metadata-only CANCEL/REVOKE，历史原key仅历史回执、不重新激活。
6. 页面提供空白新GoalCard与范围编辑、明确授权保存、自己的当前版本原文/范围与精确指纹；实例沿用owner完整证据/逐项选择与依据页面，正常可见操作和新版本失效/原keyGET恢复。保留已有身份/项目/导航/编辑/读取代次门。本轮不执行已取消精确竞态或替代probe、socket/native路径、CI Forbidden查询。
7. 先冻结Git跟踪及本轮新src/tests，ignored egg-info元数据单列不计远端。实际SQLite/TestClient/普通NoModel Worker/可见JSDOM，独审只/tmp，测试全部结束后才改源码，保留所有红轮。真实owner/语义、真实模型/付费、PG/Windows/native/设备崩溃/旧源码升级、完整P-A/P-B/正式发布/部署NOT_RUN。正常分支push核实时remote SHA、保护refs及未提交/未推差异，不称CI绿。

执行合同补充：自有Goal已存在时，RunInput必须明确提交当前binding fingerprint；Run快照封存自有card/version/goal fingerprint/绑定序列。正常Worker派发前与结果事务提交前、提交后最终检查都核当前Goal；新建或修订Goal后旧Run不能用于当前owner PREPARE，必须另行提交新输入并完成实际Worker。旧成功Run只读取其历史双seal，保留技术历史，不要求其Goal仍是head。owner contract冻结当前全部平台limits；任何当前预算变化使旧人工声明STALE。

软件版本边界：现有独立logic authority绑定所有产品Python实现的指纹（config除外）。本轮新代码使233ba9软件版本签发的authority拒绝继续使用；不自动重签、不迁移、也不把旧来源证明改成新版本。测试均用当前实现正常签发的新authority；旧持久库升级路径NOT_RUN，需另行定义显式迁移合同。

页面更新：旧owner记录失效后只保留历史metadata；另提供通过当前全部授权、GoalCard及全ledger完整性核查的prepare_current目标预览，允许新的明确PREPARE。此预览不能直接DECIDE，不恢复旧正文/判断，也不继承旧签收。读回未知save/decision只GET原key。
