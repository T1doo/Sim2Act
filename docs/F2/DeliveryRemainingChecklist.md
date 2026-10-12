# 当前最小交付剩余清单 — 2026-10-08

依据：[V5产品设计](../平台产品设计.md)与[分阶段计划](../分阶段开发计划.md)。F1→F2→F3→R0和P-A/P-B分别验收的依赖不变。

最短Win11首次体验按[安装说明](../Installation.md)：Git/Python3.12x64/PowerShell7/本机PostgreSQL → 拉取dev/f1-foundation → 私有.env保持MOCK/LIVE=false、应用角色URL与绝对数据目录 → Setup/启动前预检 → 独立迁移操作者建表、管理员仅授业务CRUD → Doctor → init-user一次并私存令牌 → Start/Status确认API和worker → [第一次使用](../FirstUse.md)创建项目、粘贴CSV、显式授权、固定草案预览30 → 人工内部版本/实例 → 新AppRun amount30和quantity15、冷会话历史 → Stop。无需模型账号、Node、Docker、WSL或自然语言激活；不将管理员URL用于日常运行。刷新后重连已有令牌，不重复init-user。这是当前说明路径，不是Win11成功回执。

|剩余项|可继续离线工程|必须取得的真实条件|
|---|---|---|
|Windows900容量|有测量依据的fixture优化、完整阶段与次数测量；本轮减少新PG schema的重复探测|同容量当前源码完整工程+保护Edge+清理时序；900/240/150不变，当前NO_GO，不盲跑CI|
|Win11首次安装/使用|预检、Doctor、生命周期和CSV路径的合成负例；修复可复现缺陷|用户干净Win11普通权限、实际软件/DB角色/浏览器与首次结果、人工记录干预；Linux/Server不能替代|
|P-B完成任务→复用|已有固定CSV/可信注册来源/有限整体验收/候选/新输入/冷历史；只推进原声明式路径的具体缺口|更宽任务可信整体验收、稳定逻辑与适用范围、用户新/错误输入评价；有限合成PASS不等于完整P-B|
|P-A与真实模型|严格清单、预算、工具、确认、恢复与fault注入|真实provider、明确获批预算、工具反馈修订与语义质量；当前预算0/LIVE0，不查询models|
|应用验收/发布|既有候选检查和内部版本；核对正式发布最小权限与入口缺口|用户对精确候选/适用范围/版本的owner验收与正式发布授权；不自动批准或外部部署|
|F1/F3/R0签收|补既定AT02双主体双项目fixture、撤权/故障/恢复缺失证据|完整固定测试、真实provider、干净Windows、独立对照与人工签收；AT02历史不改，F1未正式签收|

本轮优先Windows瓶颈：900秒阻塞现有全部产品入口的原生资格，且已有可测量的重复初始化工作。更宽语义与发布缺口不能靠新增固定目标替代真实provider和人工契约。下一步先扩大原完整工程的阶段/fixture次数测量，取得可比较的完整成本包后才判断是否能安排一次原预算内native验收；当前局部Linux收益不是资格证据。

2026-10-08新实例取得[完整Engineering PG首轮诊断](EngineeringPGPhaseLog.md)：基线5c06520，1586个原集合节点，1552PASS/7FAIL/27SKIP；已观察call/运行查询成本大于初始化，但不能推导Windows根因或节省量。7项已确认问题有最小候选修复，相关SQLite105PASS；修复后完整PG在首次连接处失败且测试未开始，按断连指令未再次启动PG。完整候选PG、当前源码完整原生成本与Edge尾段仍待验证，900/240/150和NO_GO不变。

随后获明确授权，仅一次捕获完整启动日志的隔离PG诊断健康；同一冻结运行源码的四关联模块58PASS（45项数据库关联测试使用实际PG，13项预检不依赖数据库），原7个失败节点及真实PG取消竞态均包括，前后schema/role/public表均0、自有容器与卷清理核验通过。旧首连关闭原因仍不能追认。现在值得安排一次同源码完整PG工程复验，本轮未跑全量；Windows900/240/150与NO_GO保持。

再获一次完整复验授权，冻结1932200的原1586集合与JUnit完全一致：1559PASS/27个原SKIP，ruff/mypy PASS，pytest报告1065.03秒、进程墙钟1067.583秒；原7个失败节点现均通过。283个源码文件前后一致、11项应用角色测试通过、前后schema/role/public表均0、自有容器/卷/夹具清理通过。完整Linux PG Engineering正确性验证已完成，call占77.685%、setup占20.393%，实际排名与优化证据边界见日志。本轮没有已证实性能节省；当前原生完整成本与Edge尾段仍缺，Windows900/240/150与NO_GO不变。

后续[热点诊断](../evidence/engineering-pg-hotspots-20261008/README.md)自然复现材料列表与REPORT图的反向授权取锁，确认40P01/HTTP500为实际竞态。最小修复统一项目先锁，旧四组受控调度失败、新四组成功；关联91PASS及独审通过。两个原始DOM对照均PASS，REPORT call32.686→29.401秒，报告清单36.595→37.427秒，仅为单对带观察器样本；不能声称稳定提速。原1586与所有原断言/驱动保留，另加5项回归，未再跑全量。各热点节点仅一次初始化，主要成本在历史/来源重验和运行查询；下一优化需要证明可安全复用当前来源验证。Windows900/240/150、LIVE0与NO_GO保持，原始未提交计划/日志未复制。

最终修复d85f6f5随后获一次[完整PG回归](../evidence/engineering-pg-final-20261008/README.md)授权：实际1591集合含原1586+新5，1564PASS/27原SKIP，Ruff/mypy通过，报告1086.70秒、进程1089.253秒。284源码散列一致、24应用角色夹具节点通过，PG40P01/观测HTTP500均0；唯一503为原明确故障注入。自有schema/role/public均0、容器/卷移除核验通过。当前完整Linux正确性在原跳过范围内复验闭环，成本已超过900秒，不能据此关闭Windows900/Edge240/Node150与NO_GO；原生完整阶段和Edge尾段仍缺。核心整合提交2315fea+d85f6f5与证据祖先关系已列明，开发分支只能在远端未变条件下普通快进，不main/force/新CI。

2026-10-08继续48accbb进行[请求内相邻指纹去重](../evidence/engineering-request-hash-20261008/README.md)：仅protocol_jobs两行复用同一snapshot的紧邻纯hash，保留所有SQL、授权、新鲜性和异常顺序；7个精确同输入9对阶段样本减少47.292%–50.858%，旧DOM第二hash累计143.371毫秒。固定27次历史读取hash1512→756；两个DOM原49检查/7MOCKwire均PASS，但进程39.490→40.551秒，不认领端到端提速。必要PG回归191PASS/0FAIL/0SKIP、ruff/mypy通过，未再全量或死锁验收。原284源码仅一文件两行变化，原断言/驱动/预算保留；独审及原生最小实测条件随证据保存。此小收益不能关闭Windows900/Edge240/Node150容量，NO_GO/LIVE0保持；不main/force/新CI，原实例未提交计划/日志未复制。

2026-10-11 接续原P-B声明式路径与内部版本需求：[CSV流程实例版本切换](CsvDagVersionSwitch20261011.md)补同应用、相同两/三步执行合同的显式升级/回退、保留旧结果与冷历史、当前版本的新输入worker运行；有未终止Run时拒切换，不混合执行家族或改签旧来源。精确作者/独审范围与原失败见[本轮证据](../evidence/csv-dag-version-switch-20261011/README.md)。不将这项内部工程交付提升为完整P-A/P-B、正式发布、Windows或真实模型验收。

2026-10-11 接续明确指定的双求和缺口：[双求和DAG内部实例](CsvTwoSumInstances20261011.md)实现已有一次读取→两个无条件求和的手动版本、按稳定节点双列新输入、独立worker完整双结果与冷历史；原单求和/报告格式兼容，未扩张到双求和新材料/无原内容逻辑。工程结果与未测边界见[证据](../evidence/csv-two-sum-instances-20261011/README.md)。不替代更宽P-B/AT10、Windows/native或人工语义验收。


2026-10-11 F2-T07核心接续：[有限项目共享CSV列修改](ProjectColumnPatches20261011.md)将既有局部列overlay扩到同材料固定单求和应用的有限集合，经旧/新列实际worker和独立读算后保存整组检查候选；无关节点与人工锁保留，未知依赖不作为安全改写依据。仅内部候选，原始计划/失败/历史保留；不关闭完整P-A/P-B、人工语义、正式发布或Windows等剩余门。

2026-10-11 [有限列候选→可执行内部版本](ProjectColumnVersions20261011.md)补上保存后的实际复用：整组另行精确确认、同事务版本/实例/回执，冷页面以新输入派发既有三步worker并保留旧数据。当前来源授权与完整实际Run指纹不能用预览自引用代替；原键恢复、取消及合法A→B→A历史保持。范围仍为固定共享CSV单求和应用与冻结数值列，未知/语义依赖不获得执行资格。失败与最终结果见[证据](../evidence/project-column-versions-20261011/README.md)；更宽P-B、人工语义、正式发布以及未跑平台仍在清单中。

2026-10-11 [修改后固定版本的新材料/无内容逻辑](ProjectColumnMaterialReuse20261011.md)补有限F2-T03/AT10：直接授权新CSV保留项目批准默认，另行无内容逻辑授权允许旧源删除后显式绑定目标新列；实际Worker、新版本默认与冷未见输入、旧数据/锁保持、原键只读恢复已实核。最终262PASS/7SKIP（5PG角色、2缺旧源码归档）、另2升级deselected，独审13后端实测字节桥/最终fresh16页面LIMITED PASS；原两页面产品FAIL修复且留档。此有限工程缺口已完成，完整P-A/P-B/AT10、通用语义、owner/正式发布、PG/Windows/native/旧源码升级/真实模型/远端CI仍未验收，不能用这些合成结果代替。完整边界与失败见 [证据](../evidence/project-column-material-reuse-20261011/README.md)。

2026-10-11 后续证据纠正：上段与原材料独审的整个 Worker「未读取旧 Run 私有内容」结论撤回。原2b SQL trace 两次无 WHERE全表返回context/result，相邻全表合同读取；旧探针只匹配参数中的旧Run ID，漏检。原141文件/脚本/trace/报告原字节保留，不能以262窄窗或原LIMITED PASS签收该边界；尚未证明用户泄露或旧结果复用。新增功能暂停，按 [共享调度修复合同](RunPrivateReadScope20261011.md) 限定claim/恢复/池实际候选后读取，保留五标记31非空组合的防降级和当前lease/fence/CAS。实际原代码红轮、按行/列屏障校准、修复、独审及扩大回归见 [新证据](../evidence/run-private-read-scope-20261011/README.md)；原P-A/P-B、未知/语义依赖、人工锁与正式发布各门未提升。

该修复最终作者1730唯一节点1664PASS/66SKIP/0FAIL/0ERROR，原650=641PASS/9SKIP，30页面原预算串行全PASS；独审59检查LIMITED PASS另计。401项作者代码冻结由396个Git跟踪文件及5个ignored文件组成，不能称401项均可由Git复验；141原证据同字节，2升级deselected、63PG/2旧归档/1Windows的SKIP原因完整列明。历史两页面超时和隔离FAIL保留，具体既有冷读递归热点已测，新namespace样本调用0，完整超时因果仍未确定；不能认领性能/原生容量资格。全树Ruff10/mypy5与原2b同基线，改动Ruff通过。PG/角色、Windows/native/视觉、真实升级/模型、完整P-A/P-B/AT10、语义/owner、远端CI/部署仍NOT_RUN。

2026-10-11 上述共享私有读取修复 `1dadba831a4d15fc164398e2f1070f22d7a5d77d` 获接纳后，按明确授权恢复原 F2-T02/P-A 核心工程，而非继续CSV外围扩张。[有限非CSV目标到应用](PATextGoalPlan.md)已贯通完整GoalCard→实际resource.read反馈→一次候选修订→ActionSpec/AppManifest→精确指纹确认→既有内部版本→冷实例新词和错误输入。独立app身份仅获该材料读取权限；成功/失败/类型化历史与来源完整复核，未知发送只原key GET恢复。实际SQLite/普通Worker/进程内HTTP/JSDOM结果、失败保留和静态基线见[证据](../evidence/pa-text-goal-20261011/README.md)。生产生成仍默认disabled/LIVE0；合成provider与确定性字面检索不替代真实provider或语义接受，完整P-A/P-B、owner/正式发布、PG/Windows/native等门仍未关闭。

2026-10-11 P-A 缺陷纠正：旧轮 4 场景/102 检查直接调用隐藏处理器，撤回其对用户可见确认→预览/实例链的证明；旧轮仅 STARTED 路径保存拒绝原 JSON，撤回「所有已收到拒绝原响应均留存」的宽泛表述，原 109 份证据字节保留。新 [合同补充](PATextGoalPlan.md) 和 [红轮/修复证据](../evidence/pa-text-handoff-20261011/README.md)覆盖可见导航/焦点与迟到保留、原 key 先核后保存 Run ID、RECEIVED 后完整 bounded JSON 留存与独立锚。超 32768 canonical ASCII 字节明确拒绝并仅留大小/hash/省略标记，旧无 raw 不补造；JSDOM 仍非原生浏览器，原未验收门不提升。

同日 P2 接续：父复审指出 `7e86ec7` 的草稿最终值比较漏过同卡 A→B→A；上一轮 A→B 结果不证明编辑撤销后仍拒绝迟到交接。新增单调编辑代次保护确认及原 key 恢复，覆盖七字段与材料选择器，原值检查和未保存编辑保留；[新红轮/独审证据](../evidence/pa-text-edit-generation-20261011/README.md)另存，之前两个 P-A 目录共270份证据原字节不改。下一 owner 精确版本/新输入验收切片待本修复签收后续做，未以本测试提升 owner 或语义门。

该轮相邻回归同时暴露 `/goal-application.js` 固定静态路由缺失；旧页面测试本地嵌入脚本未证明HTTP资源交付。只补这一路由，驱动现在对每次开页的HTML/CSS/16脚本实际GET并保留精确HTTP/hash回执。原68PASS/5FAIL和单脚本404红轮留存，不能把旧本地源码加载说成HTTP脚本加载。

2026-10-11 `d3b375d13e1b235015ec5344152eb9b4c9668120` 获接纳后，接续原 F2-T01/T08 [owner 精确版本逐项签收](OwnerVersionAcceptance.md)：有限生成文本应用显示完整冻结 GoalCard、未解决项与正常 Worker 新输入证据，人工逐项 ACCEPT/REJECT 及依据，追加精确版本声明；当前来源/目标/实例/授权/运行变化、ABA、并发和迟到提交重验，取消/撤销/新预览/原 key 仅读恢复保留历史。独审实测发现较早 payload 损坏仍可直接追加，已补当前内容授权后的全历史提交核验，原始失败及 withdrawn 候选验证保留于[本轮证据](../evidence/owner-version-acceptance-20261011/README.md)。此条只交付人工签收的有限工程流程；测试中的人工选择为 SIMULATED，真实用户语义、完整 P-A/P-B、正式发布、PG/Windows/native/旧源码升级/真实模型和远端 CI 均须单独验收。


同日父复审 P2 的 [owner 页读取顺序纠正](OwnerReadOrder20261011.md)已完成有限代码与实测：真实 HTTP 旧 ACCEPTED 初读在新 REVOKED/PENDING 刷新后不得回滚；初始/刷新/原 key/提交后读取统一最新请求资格及范围、序列、历史回执绑定。独审还发现两层 catch 间新读取或编辑再撤销的旧错误污染，五项调度回归及初始完整 fence 已修，所有旧 FAIL/撤回候选按[新证据](../evidence/owner-read-order-20261011/README.md)保留。最终页面/调度作者及独审各34 PASS；同字节后端48实际子集另列复用，非一次完整82重跑。独立附加API2及受控37通过；人工选择仍SIMULATED、语义UNKNOWN、正式发布false，真实owner/PG/Windows/native/升级/真实模型/完整P-A/P-B/CI等原验收条件不提升。


2026-10-11 接续 F2-T03 / AT-10 的[有限非CSV成功运行提取](PBTextExtraction20261011.md)：原实际 SUCCEEDED 文本 AppRun 经独立来源、步骤和完整字面结果重验，提取为绑定不同已授权 TXT/MD、接收新 term 的独立应用，再通过冷正常 Worker 复用。新 task 来源自身封印完整请求/key，原 key 仅读回执与实际候选指纹/来源绑定匹配后才安装；错误第三应用、指纹替换和协调替换另 key 应用的独审红证据保留并修复。新 owner PENDING，不继承旧声明；沿用登记字面算子，LIVE0、语义 UNKNOWN、发布 false。精确工程范围及最终实际轮次见[本轮证据](../evidence/pb-text-extraction-20261011/README.md)。原来源授权/证据仍参与审计，完整 P-B/AT-10、真实模型/真实owner语义、PG/Windows/native/旧源码升级/CI等门未据此关闭。


2026-10-11启动、实际延续至2026-10-12的F2-T09 / AT-05/18 [有限原请求身份冷恢复](PBColdRecovery20261011.md)完成：受保护服务端journal先保存精确key/主体/项目/来源/目标/请求指纹及单调历史；未知仅原key GET复核当前授权/真实候选后安装，不自动重发。候选/回执/COMMITTED同事务，metadata-only CLOSE不把已有提交伪签为关闭；CLOSED与latest CAS拒绝迟到/重复意图，浏览器不新增正文或秘密持久存储。独审真实发现错误source绑定、最后GET后异步hash竞争，以及第65来源写入后项目冷索引失效，均修复，三撤回候选和输出路径夹具事故全留原证。最终同项目事务冻结64来源/每来源64历史预算，第65首prepare拒绝全DB0变，原64冷索引与既有来源明确新请求可用。作者一轮503 collected/502 selected/1 deselected，492PASS/10PG前提SKIP/0FAIL/ERROR；独审39、43、6、1分别PASS，有限LIMITED_PASS，不加总为语义或一次完整AT覆盖。369源码前后一致，精确HTTP/JSDOM/SQLite/普通Worker及失败档见[本轮证据](../evidence/pb-cold-recovery-20261011/README.md)。原GoalCard/source授权仍参与审计，新owner PENDING、语义UNKNOWN、LIVE0、发布false；PG/Windows/native/设备崩溃/旧源码升级/真实模型/真实owner语义/完整P-A/P-B/AT05/18/source退休/长期容量性能/远端CI/部署等原验收条件不提升。


2026-10-12 父级精确复审纠正：e2b856冷恢复中原late-latest-digest最终trace仅一次latest409、latest_reads=0，未覆盖安装窗口；撤回该具体动态推论，保持原492及独审历史执行数字和原证据字节，不把缺口称为当前产品漏洞。当前代码顺序可见，仍待同一精准probe的旧源失败/当前通过及完整200→候选GET/hash→并发201→最后409时序。该精确独审委派被当前平台风险筛查拒绝，已停止受拒动作，未换名/工具/代理/环境重试；本跟进仅准备[声明纠正与完整阻塞证据](../evidence/pb-exact-install-window-20261012/README.md)，动态测试和独审尚未运行、未提交推送。其他原始分母/授权路径仍由父级独审，原NOT_RUN门不提升。

2026-10-12 用户后续明确取消被拒的精确旧/新候选安装竞态对照：该具体资格永久NOT_VERIFIED，不再等待解除或改换代理/工具/框架重做。原拒绝、trace与未提交纠正保留，取消回执见[记录](../evidence/pb-exact-install-window-20261012/cancellation-20261012.json)。主线转入独立F2-T03文本无旧内容逻辑复用，不以新功能测试替代此项。


2026-10-12 F2-T03 有限文本无旧内容逻辑复用：独立授权→原材料撤权/删除→新只读身份/单Grant绑定→冷普通Worker与严格新Release索引纵向子项已实际验证。作者32PASS，独审41PASS+2目录PASS，同产品有限相关84PASS1PGSKIP，分开记录；见[合同与证据](PBTextLogicReuse20261012.md)。语义/任务owner PENDING、LIVE0、发布false；完整P-A/P-B/AT-10与各NotRun条件仍未闭合。旧取消精确竞态对照永久NOT_VERIFIED不受此子项影响。


2026-10-12 原F2-T01/T08的[独立文本应用自有GoalCard与精确版本签收](TextLogicOwner20261012.md)完成有限纵向工程验证：显式完整新卡/适用范围及双seal原子版本绑定，实际新Goal版本下正常Worker输入证据、全部最多100条原项ACCEPT/REJECT，旧签收失效后仅独立当前目标新PREPARE、旧原key仅读历史。作者新34PASS；独审同选34+独立9共43PASS；原家族152 selected为147PASS/5PG前提SKIP，分别记不加总为完整工程。377 Git src/tests前后同指纹，5 ignored egg-info不计远端；全部红轮、SQL屏障、HTTP资产与独立报告保留在[本轮证据](../evidence/text-logic-owner-20261012/README.md)。人工选择SIMULATED、语义UNKNOWN、LIVE0、发布false；旧233 authority因软件all-py指纹变化失败关闭，未重签/迁移、旧实库升级NOT_RUN。真实owner/语义/完整P-A/P-B/PG/Windows/native/正式发布/真实模型/部署各门不提升；CI Forbidden未再查，取消精确竞态永久NOT_VERIFIED。

同日先完成自有Goal读取迟到错误的P2修复并推送`df5f422174c4eeea96e5dd16c141dc0a4b36b3e6`，随后接续F2-T08的[有限显式软件续用](TextCompatibleContinuation20261012.md)：在两个已接纳精确旧Git实际生成的四份SQLite库上核原完整Worker成功/失败合同，原数据/Release/Goal/人工历史保持，新精确软件许可、Release及所选实例revision同事务；未获许可其它实例不能借归档读取执行。最终作者249=243PASS/6PG_SKIP/0FAIL/ERROR，401冻结零差异；独审80唯一节点及受控UI12另计。旧235PASS/2FAIL/6SKIP、R8损坏FAILED历史红轮、夹具错误及断线日志全部保留于[证据](../evidence/text-compatible-continuation-20261012/README.md)。这是合成旧SQLite有限cold续用，不是实际用户旧库升级，也不支持软件接续链/未知schema或语义迁移；PG/Windows/native/真实owner/模型/完整P-A/P-B/正式发布/CI等剩余条件保持，原取消精确竞态永久NOT_VERIFIED、Forbidden CI保持停止。

父级随后只读复审b244发现Run错链先投影正文后scope检查，以及缺typed成功历史/失败结果残留遗漏。已按[历史边界合同](TextContinuationBoundaryReview20261012.md)同轮最小修复：完整Run查询先约束精确主体/项目/runtime；按冷inspect_job规则对任何潜在结果完整verify，再核typed↔AppRun双向集合。原两锚缺typed201→201→冷读409、12错scope真实cell求值和VERIFIED-operation迟到commit201已实际复现，未称响应泄露/真实攻击。新410冻结作者291=285PASS/6PG_SKIP/0FAIL/ERROR，独审112PASS另计；真实旧FAILED-only/CANCELLED-only无结果实例继续通过。原38/4红轮及夹具错误、全部前轮证据保持于[新证据](../evidence/text-continuation-boundaries-20261012/README.md)，原NOT_RUN/永久取消/CI停止条件不提升。


2026-10-12 [有限四步非CSV任务与提取](TextFourStepExtraction20261012.md)：实际读取TXT/MD → 两次独立检索 → 条件引用报告，经普通Worker四份真实Operation/Intent/Receipt、独立source/report oracle及完整当前Goal冻结复验，再一次显式提取到新材料及自己的当前Goal；false保留3VERIFIED+report SKIPPED/PARTIAL，无成功typed行、不可提取。原key回执与独立origin锚、缺scope/ACCEPTED损坏指针的授权前置、实际Attempt空、严格JSON/完整accepted-input header已补齐。最终r11作者55PASS（47新切片+8旧续用资格，另50deselected），独审56PASS另计（47与作者重叠，9额外），0FAIL/ERROR/SKIP；r10完整535=523PASS/12SKIP（10PG前提、2缺旧源码archive：67c6ccc8与f13升级），不改写为r11实跑，412文件/web与私有2函数改动的准确桥证、最终fresh均见[证据](../evidence/pb-text-multistep-20261012/README.md)。原r8三真实核心红例及错key页面红例、夹具错误/中断历史均保留。仅有限F2-T03/T04/P-B工程片；owner仍PENDING且此家族人工提交UNSUPPORTED，语义UNKNOWN、发布false、模型0。完整P-A/P-B、真实owner/客户材料/模型/PG/Windows/native/实际旧库升级未跑；Forbidden CI停止与旧精确取消窗口永久NOT_VERIFIED保持。

同日父复审补正：r10的12SKIP实际为10PG前提缺失＋2旧源码archive缺失，原错误表述及XML保留；两处页面P2分别冻结Open workspace/edit代次、仅清同一pending对象原key，原红例及定向验证见[纠正证据](../evidence/pb-text-multistep-20261012/parent-review-corrections/README.md)。仅有限页面修复，不改后端、不升格全仓或owner资格。


2026-10-12 主线按明确指示转到 [P-A受控书生适配与模型图新材料复用](PAInternProvider20261012.md)：默认关闭/真实请求0；独立精确Goal/材料/身份/软件/原key批准与不可退还请求槽，实际sender前重验，实际读取反馈→原模型候选→明确确认→模型图指定槽绑定自己的新材料/Goal→冷NoModel Worker。这里只计合成协议与确定性引用工程，不称真实书生或业务/语义/完整P-A完成。原owner草案保全未扩展。实际专项/独审/原失败及唯一源map见 [本轮证据](../evidence/pa-intern-provider-20261012/README.md)。相邻675回归原587P84F4PGskip保留；82旧软件兼容门FAIL继续保守关闭（白名单不放宽），另外2个接口/授权前ledger问题已修。真实provider/费用硬预算、旧软件接续资格、PG/Windows/native、完整验收/正式发布/CI仍未关闭。

同日后续 [两个旧锚到精确新软件的有限兼容合同](PATextSoftwareCompatibility20261012.md)：上段6088阶段的82阻断已按70预检拒绝/12深层未进入分类，并在原锚/CHANGED集合不变、完整70文件精确新资格及原逐实例明确批准边界下修复。原a4fd源码两文件100PASS；当前相同两文件100PASS且82逐名通过，主线56PASS、资格篡改22PASS、共享129=122PASS/7隔离PG前提SKIP，作者307唯一=300PASS/0FAIL/ERROR/7SKIP。独审190唯一PASS/0FAIL/ERROR/SKIP，其中178与作者重叠；其自身82映射/36deep-UDF原JSON已封存，补证重复36不加分母。425冻结条目前后零差异。原失败/旧seal/6088证据/owner草案不改签；其它软件及6088时期模型对象不自动迁移授权。原生浏览器/Windows/PG/真实模型费用/完整P-A/P-B业务语义/部署/CI仍NOT_RUN；wheel构建因缺setuptools失败并保留原错误，未安装依赖。详细原始证据见[本轮证据](../evidence/pa-text-compatibility-20261012/README.md)。
