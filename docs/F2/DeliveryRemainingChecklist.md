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
