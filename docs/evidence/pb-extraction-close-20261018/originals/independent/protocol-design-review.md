# P-B 未受理原提取意图：只读协议审查

基线3d1a3160fda6e9bfead96fae8a40935617270da4。结论：存在真实产品缺口。冷记录已保存但POST未到/未受理时，现by-key只回OUTCOME_UNKNOWN，用户永久锁住。可用既有project事务锁+双sealed journal增加显式metadata-only CLOSE及永久latePOST fence，不需要executor/Grant/新业务表。本文是设计建议，不是已实施/已通过。

## 现有可复用点及不能直接照搬处

- pb_natural_specs.py:444 project锁；446先重算review，448–454按sourceRun/user/key恢复已接受结果；466–472原marker、META与EXTRACT双seal；505–520 GET在source_gate后读scalar marker、核target/current draft和完整原request/review。
- spec_run_terminals.py:38–40 任一terminal存在即fence；43–75 scope/accepted残留不等于absence；105–133 close同事务幂等。app_jobs.py:129–134原普通Run在oldkey/副作用前拒永久关闭key。**此CloseInput要求完整空input ordinary spec请求，不适合冷PB metadata，不能把原DTO放宽成通用。**
- db.py:702–727 SQLite BEGIN IMMEDIATE/PG transaction；815–828 project row lock。text_logic_reuse.py:143–155两份snapshot/request DTO指纹一致；delivery_graph_requests主键(app_id,principal_id,kind,key)可借sourceRun作lid，专有kind，不污染旧app family。
- **pa_trial_dispatch.py:203直接调用pb._extract**：fence必须在共享_extract内，不能仅HTTProute；严格源家族/权限不能省。

## 最小合法合同

关闭scope固定为(user,pid,sourceRun,originalKey)，source app/iid/appRun/Release/version应与原独立source绑定元数据一致。闭合Strict DTO可用既有17字段metadata白名单，至少包含fullExtractInput request_fingerprint及scope锚；不得收token/正文，不可用server回显正文重构所谓原意图。其他fingerprints为客户端冻结声明；服务端未见原POST时只能声明“此scope/key已永久保留为未受理”，不能声称已验证原Goal/材料/recipe正文。

journal request_fingerprint应仍是**Close DTO自身hash**（remember/pair约定），返回的original_request_fingerprint另字段才是fullExtractInput hash；不要混成review.request hash或只比较expected_review_fingerprint。terminal回执应严格包含namespace、CLOSED_NOT_ACCEPTED、完整scope+原fullhash/metadata、terminal自身fingerprint以及new_model_requests=project_writes=0，不能包含可打开的app receipt/request/reviewed正文。

所有POST/CLOSE均先按同project顺序获得事务锁；任何已关闭残留使原key POST永久拒绝，匹配正文也不允许重新执行、不同正文更不允许借旧key创建。source当前owner/project/family/READ授权必须在任何terminal/accepted私有读取前执行。未受理关闭不需要重新通过targetGoal/fullreview（否则stale目标导致拒绝后仍无法退出），不以旧source proof当当前权限capability；原来源稳定ID可独立核验，完整动态source_audit不应被误当永久身份。

### CLOSE-first

授权→锁→独立accepted残留检查→严格核已有terminal（重复同DTO幂等、换hash/scope冲突）或插入双terminal→最终当前scope核验→事务提交。返回明确closed；之后exact与changed-body latePOST都在shared_extract、review/oldkey/任何业务写前拒绝。单seal/损坏terminal也必须fence，不可因pair读取失败当absence。

### POST-first

原_extract现有事务成功：1app/runtime+原2Grants+marker+4原双seal。随后CLOSE不能删除/撤销结果或写CLOSED。可拒绝并让用户显式走原GET；若返回ALREADY_ACCEPTED，只是控制状态，不能替完整receipt/freshapp核验，不能据此forget。返回任何私有accepted receipt前仍需现有source+target授权及verify/load_draft，不得key命中即泄漏。

### 完整性要求

不能仅task_extractions缺行就断言未受理。应联合独立原EXTRACT(.seal) metadata、提供的派生app/runtime及其它明确接受锚；任一接受残留/marker缺失/单seal/冲突均OUTCOME_UNKNOWN或VERSION_CONFLICT，**无CLOSED**。客户端提供的app_id可能错误，不能只用它检索原接受证据；原sourceRun+user+key必须有独立SQL scalar锚。若accepted和closed同时出现，GET/CLOSE fail closed，不挑一边掩盖损坏。新GET先当前source gate，再读closed；严格双seal与scope/hash、无接受残留才可返回可忘记terminal。

coldmetadata只有独立fullhash不是问题：CLOSE绑定该hash进行永不执行的reservation，不需要恢复正文。GET收到closed只能与本地原17字段独立比较，然后在既有同scope WebLock+原raw+pending身份+所有generation/current fence下忘记。不得自动提交CLOSE；显式按钮说明原key永久停用，业务结果不会被撤销。close响应丢失仍保留锁，显式GET读terminal；不能“收到4xx即解锁”。同页面/另一页面已移除raw仅允许原pending RAM清理，不remove新raw。成功closed后清review/ack/editor原准备态，不能设置saved/安装应用。

## 最小实际验收建议（未执行）

复用正常synthetic成功来源fixture即可；提取/CLOSE本身模型0，不需要重复新Worker或旧恢复矩阵。后端实际两个Store/连接+两个线程，让事务真实竞争同project，分别证明CLOSE先获锁和POST先获锁；赢家提交前记录另一事务实际入场等待、原HTTP完整回执与最终DB，而非仅顺序调用。close先：恰两terminal、无新app/runtime/Grant/marker，两个latePOST（exact/changed body）拒；post先：恰一原接受、无terminal、关闭不能删结果。另查sameclose幂等/changedhash拒、单seal/接受锚缺失不能伪absence、crossuser/project/current source撤权在正文前拒。

页面actualHTTP最小两路径：保存票据后模拟POST未投递→新DOM→显式原GET UNKNOWN→显式CLOSE→闭合回执独立匹配→仅此raw解锁，旧POST由服务端永久拒；以及POST已接受但丢201→CLOSE不能关闭、仍须原GET+独立原hash+freshapp完整匹配才忘记。附同锁两页/迟到CLOSE回执导航保持原raw，避免复用当前5case整批长矩阵。

## 保留范围

旧v1→v2/下载只读报告保留在 /workspace/pb-result-version-readonly-20261018，未变成当前资格。永久取消旧安装candidate双actor digest窗口不执行不换名；当前CLOSE/POST事务竞争是用户明确新要求，目标不同。旧满盘独审缺证、exit139Unknown不关闭。真实模型、Windows/native、PG、远端CI、真实语义均未执行。
