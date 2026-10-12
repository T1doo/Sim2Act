# F2-T03 有限文本无旧内容逻辑复用合同

基线e2b856bb453fc74452583fa10843148758e2d9b9，独立开发分支dev/pb-text-logic-reuse-20261012，root唯一产品作者。依据V5计划F2-T03及产品P-B/AT-10，继续最小纵向价值，不签完整P-A/P-B或语义/发布。此前被拒精确候选安装竞态对照由用户明确取消，永久NOT_VERIFIED；不重做、不换方法实现该目标，相关原日志与未提交说明保留。

1. 只从实际SUCCEEDED初始已生成text.literal_evidence@1 AppRun/Release、完整当前授权/来源/步骤/typed结果验证后签发独立逻辑授权；不接受UNKNOWN、失败、CSV、agent、任意代码或递归提取来源。沿用真实verified_source和独立字面检查，未取得授权不能跳过原来源校验。
2. 用户必须明确确认来源证明/Release精确指纹及“本项目无旧内容逻辑授权”同意文本。规范化逻辑只含固定单节点、term变量、固定Schema/输出检查、原冻结限额、版本、owner/project/逻辑ID及24h期限；不含原goal、资源ID/hash/bytes、输入、引用、结果、路径、密钥或自定义名称/步骤标签。
3. 独立授权复用现有internal_approvals及delivery_graph_requests双seal，私有mint审计只存opaque源app/instance/Run/Release身份与证明/指纹承诺；另存以新logic ID为盐的不可逆材料身份承诺，用于排除原resource别名，不保留原resource ID/hash。授权以后不再SELECT原资源内容/hash、原Run私有字段、原Release/approval快照、生成轨迹或原Operation/typed内容。授权完整性取独立对象/seals，不以旧材料当前权限替代该新权限。
4. 只作用同owner/project内有限TXT/MD：4096 UTF8 bytes、64行、term非空trimmed且最多80字、命中最多16行。新绑定只能选择另一份现有且当前user/app已授权的初始文本应用材料，冻结target app/candidate/resource/hash；显式确认建立新独立只读runtime。该runtime无token/旧身份/密钥，仅新目标resource.read Grant，期限不超过独立逻辑及当前目标授权；不会复制旧来源或目标应用的全部权限。
5. 新候选由已证明固定结构规范化构造，task来源仅指向独立逻辑ID及本次精确绑定请求；fresh action/app/runtime身份，标准无旧内容goal说明。user当前材料Grant与fresh runtime授权相交；原材料撤权/删除不阻断已授权逻辑，新目标或独立逻辑撤销/过期仍拒绝。
6. 逻辑授权不可逆撤销：consumed或任一独立revocation seal存在即拒绝，单边恢复不能复活。全量账本管理员重写不属于产品能力。保留CLOSED/历史与所有原对象，逻辑最多64/project、绑定最多64/logic，满额新写前拒绝。每次读、preflight、enqueue、正常worker计算与最终提交都重验当前逻辑、平台预算、目标bytes/hash/user+runtime权限。
7. 原source任务、旧Release/候选原来需要内容的GET仍在撤权后拒绝，不放宽旧门。新app的compile/verify_origin只识别新独立marker，丢失/更换task marker或seal不得降级成普通goal来源。保留旧registered_run_extraction及CSV执行家族。
8. 新app/task receipt、fresh principal及唯一目标Grant、绑定双seal在同项目锁事务中提交，失败无部分修改。同key/body只一个效果，同key换body冲突；未知回复只原key GET，不自动POST重放。独立撤销在同项目锁下；worker每步及typed最终写前后重核，取消、过期、预算收紧和版本变化不能伪通过。
9. 页面提供来源预览/明确授权、项目独立逻辑索引及撤销、当前新材料/新身份范围预览/明确绑定；冷页面不打开原app/Release/材料。正常读回核原key/candidate hash再用已有Release/Instance/Worker运行新term。当前工作区/身份/选择/编辑改变后遵守已有代次门；本轮只正常使用链测试，不执行已取消旧/新安装竞态probe。
10. 新task-owner PENDING、技术语义UNKNOWN、LIVE0、正式发布false，不继承旧owner声明。本轮至少实际SQLite/NoModel普通Worker：先授权→原source user+runtime撤权/内容删除→绑定已授权目标→fresh Store/API冷未见term及错误输入/typed历史；保护原私有单元的整段SQL读取屏障、目标/logic撤销或expiry、跨owner/project、body/seal污染、预算、同key原GET恢复、事务回滚/原对象保留、实际HTTP资产/JSDOM可见交互。
11. PostgreSQL/应用角色、Windows/native browser、真实设备崩溃、真实模型/付费、真实人工语义、全旧源码升级、完整P-A/P-B/AT-10与正式发布/部署未跑即NOT_RUN。已取消精确竞态对照单独永久NOT_VERIFIED，不能用本轮数据权限与冷Worker通过来关闭。
12. 产品source/test先冻结再执行，编辑前等待所有作者/独审测试结束；独审只写自己的/tmp，源码仅root写。保留所有失败和退出日志，不以部分或不同SHA累计成一次全绿。普通开发分支push并核protected refs与未提交/未推差异，远端CI不预宣称。

## 实现与最终有效验证

- [text_logic_reuse.py](../../src/sim2act/text_logic_reuse.py)：独立24h授权、双seal、规范固定recipe、原材料盐化身份承诺、64/project与64/logic、新身份单目标Grant、精确绑定及原key GET。新候选不复制源/目标goal、身份、token或内容；授权后仅核独立对象，旧来源不再作为读取前提。
- [apps.py](../../src/sim2act/apps.py)、[text_apps.py](../../src/sim2act/text_apps.py)：可信新家族派发及防降级；[app_jobs.py](../../src/sim2act/app_jobs.py) 在结果事务结束前重核当前逻辑、目标和预算，异常回滚typed/SUCCEEDED。
- [lifecycle.py](../../src/sim2act/lifecycle.py)、[internal_api.py](../../src/sim2act/internal_api.py)：新家族Release与app→Release metadata索引双seal同事务；读取严格核索引；新版本列表只读取本app已核元数据索引，不扫描旧Release快照。没有新表、DDL或旧历史回填。
- [api.py](../../src/sim2act/api.py)、[conditional_apps.py](../../src/sim2act/conditional_apps.py)：冷页面目录使用metadata_only路径，普通任务摘要固定占位/mode UNKNOWN；资源目录先授权再投影hash。原默认API继续兼容；打开对象仍完整核验。
- [text-logic.js](../../src/sim2act/web/text-logic.js)：明确来源预览/授权、项目冷索引、目标与新身份确认、不可逆撤销、原key只读恢复和正常新应用执行入口。

候选8作者32 PASS/0 FAIL/0 SKIP；同产品源码的候选7有限相关回归84 PASS/0 FAIL/1 PostgreSQL SKIP。独审候选8 41 PASS/0 FAIL/0 SKIP，另2纯目录回归PASS。它们是分别执行的范围，不能累计成一次全套测试。候选7→8只有两个新UI harness测试文件变化，产品src逐文件相同；378个源码/测试文件前后hash无差异。四个作者/独审普通可见页面场景均为 valid、authorization-lost、binding-lost、revoked-retained；每场两次冷boot，真实HTTP HTML/CSS/JS共40资产；保护旧私有单元的全段SQLite屏障包括实际Worker，求值0。旧source删除和保留撤权两条路径均通过。真实第64写允许、第65拒绝、原key读取，单边JSON类型污染、撤销、过期、预算收紧、最终append过期回滚及index故障完整回滚均实际验证。

changed文件ruff与Node语法检查通过；全局ruff10/mypy5既有错误原日志保留，未修外围。所有失败、被中断范围及独审原记录保留在[证据目录](../evidence/pb-text-logic-reuse-20261012/)。候选4作者误选10个socket旧UI及独审误选2个socket旧UI是实际OUT_OF_SCOPE_EXECUTED，不计本轮验收、没有重试；不能改称未运行。候选7独审两个BrokenPipe未捕获当时Node stderr，原因仍UNKNOWN；候选8修harness关闭前drain并完整记录stderr/exit/SQL后实际重新通过，不覆盖旧失败。

PostgreSQL/应用角色、Windows、原生浏览器、真实设备崩溃、真实模型/付费、人工语义、全旧源码升级、完整P-A/P-B/AT-10、正式发布与部署均NOT_RUN。此前已取消精确安装竞态对照永久NOT_VERIFIED，本轮不能关闭。LIVE0、owner PENDING、semantic UNKNOWN、formal publication false。远端CI待精确提交核查，测试通过不等于远端CI绿。
