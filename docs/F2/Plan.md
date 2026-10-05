# F2 并行工程 Plan：权威当前状态

2026-10-05。F1 IN_PROGRESS/未签收；用户已授权隔离并行工程，F2正式准入及发布BLOCKED，真实模型预算0。V5 F2-T01—09/AT-09—22全部保留，不改变source设计或冻结用例。

## 已完成切片：固定CSV草案预览

基线27232c6/实际测试0555593，固定可信data.aggregate_csv，单节点声明式输入输出、候选指纹/资源hash、preview应用Principal/Grant与用户-项目-应用交集、持久历史/请求键幂等和撤权回读拒绝已实现。PREVIEW_ONLY/不可发布；没有模型生成、P-B、Release/实例身份、外部写入、任意代码或异步AppRun可靠性。

[当前E6证据](../evidence/recovery-20261005/README.md)：WindowsServerCI37315778872成功，PG126PASS/0FAIL/0SKIP（CSV11专项含其中），Linux123PASS/3平台专项SKIP，正常push已成功。owner隔离/PATHEXT修复已Server复验；独立只读审核无新安全阻塞，非独立复跑。旧[首轮浏览器/SQLite证据](../evidence/F2-csv-preview-20261005/README.md)为历史：其中PG BLOCKED不代表当前CI，6浏览器检查点不代表最新多平台复测。

## CSV数值列选择与输入提示：已实现（以下边界于实施前冻结）

用户价值：打开草案即可选择可汇总数值列，看到记录数及无效列/材料说明，不必手输列名试错。范围为F2-T04/T06已授权固定模板的一小部分；不宣称自然语言P-A或完整目标卡。

只在现有inspect网关经过user-project-app及候选/资源版本验证后读取同一材料，返回列名、有限十进制可汇总性与记录数，不返回新增原始单元格。UI用安全DOM文本呈现下拉选项，保留输入类型校验/固定可信工具及历史；材料篡改、权限撤回拒绝，列提示不生成执行/写入或授权。实际预览仍重新验证，提示不作为许可缓存。

风险：CSV重复/空表头、行宽不齐、缺值、NaN/Infinity、超过1000行需要准确提示；元数据计算必须有界且与工具语义一致。畸形材料保持历史可见但禁止UI提交，API原有错误历史语义保留。输入框改下拉可能影响旧浏览器测试，需真实本地浏览器复测；新表/迁移/依赖均不需要。

验收：不同数值列产生不同新结果；文本/非有限数列不可选，空或畸形CSV有明确原因；跨主体/撤权/资源篡改不泄露列信息；元数据无模型请求/无preview写入；SQLite全回归、精确提交ServerPG CI及本地浏览器链路。Win11/多浏览器平台能力缺失如实报告，不能用Linux模拟认证通过。

正常阶段commit/push与标准windows-2025有界CI已授权；网络仅用正式执行器审批，不改代理/身份/策略。任何真实模型/外部发布/Release/任意代码执行仍不在本切片范围。F1 Win11及AT-02/独立签收缺口保留。

## CSV输入提示切片本地结果

已实现列元数据及安全下拉；10项新增工程检查、SQLite133PASS/3平台专项SKIP/1旧警告，ruff/mypy14模块/JS语法/diff通过。本地LinuxChromium实际6检查点及截图复核PASS，临时SQLite/合成身份已关闭；非Win11或其他浏览器引擎验收。普通push及精确源码07969cd的ServerPG CI37318927260已SUCCESS，PG136PASS/0FAIL/0SKIP（43.50秒），原生/锁/静态/清理通过；[证据](../evidence/F2-csv-guidance-20261005/README.md)。模型0/不可发布/F1未签收不变。

## 通用目标卡与版本化验收草案：已交付（以下边界于实施前冻结）

核对V5产品§2/§3.2/§5与F2-T01：P-A需要先将新目标拆成已知/假设/未决项、硬条件、验收检查及授权材料引用；P-B要求已完成任务来源与新资料冷运行，不能把当前PARTIAL任务或CSV固定模板冒充完成。因此本轮选择两路径共同输入前置的通用目标卡，服务任意TXT/MD/CSV/JSON目标，不继续加CSV小功能，不声称模型规划/生成或P-B完成。

明确交付：项目内创建/查看/人工修订结构化目标卡；分开保存目标、已知、假设、未决项、硬条件和验收检查；只绑定同项目已授权材料的ID/hash。每次保存生成不可变版本与指纹，旧窗口expected_version冲突拒绝且不覆盖新版本；历史可回读，标DRAFT/尚未验收/不可执行，不自动降低要求。用户人工编辑新版本允许明确修改条件，但保留旧版，模型不参与。F1原GoalSpec/冻结Run与V5/AT正文不修改，目标卡不能启动模型或成为Release授权。

范围/风险：新增goal_cards/goal_card_versions仅由现有显式migrate建立，API不隐式DDL；所有读取/修改先项目所有权、版本指纹及材料授权/实际hash复核，历史涉及已撤回材料时保守拒绝整卡回读，不以旧快照恢复权限。PG行锁+版本条件更新保护并发；SQLite仅工程。输入字段/列表/长度闭合；UI安全DOM展示，无任意代码、SQL、执行器、业务外部写入/发布或新依赖。

验收：一般目标而非固定CSV可创建；字段分离/材料hash/历史持久；修订保留旧硬条件与验收，旧窗口冲突且无多余版本；跨用户/同用户跨项目引用/撤权/材料或存储篡改拒绝，无新增Run/Operation/preview/权限；SQLite/PG工程回归、真实本地浏览器创建编辑冲突/历史链路；正常开发分支push/精确ServerCI到终态。预算0与Win11/F1签收/F2正式门保留。

## 通用目标卡本地交付结果

已实现通用字段分离、显式材料授权/hash绑定、不可变版本历史/指纹、PG行锁+版本条件更新与旧窗口冲突。新两表由显式migrate建立并需应用角色CRUD，不赋DDL；近50版历史逐一重新授权/hash验证，旧版本存储保留。14项专项，SQLite147PASS/3平台SKIP/1旧警告9.27秒，ruff/mypy15模块/JS语法/diff通过；LinuxChromium7真实检查点（一般文本目标、修订、旧条件、第二客户端、旧窗口保留文字/拒绝、最新与重载历史）通过，本地fixture已关闭。已普通push，精确源码6bf5e05的ServerPG CI37322479923终态SUCCESS：PG150PASS/0FAIL/0SKIP/1旧警告33.71秒，现有原生smoke/迁移/锁/静态/清理通过；[证据](../evidence/F2-goal-cards-20261005/README.md)。未声称模型理解/目标生成/正式验收或完整F2-T01完成。

## 目标卡 → MOCK声明式候选 → CSV应用预览：已交付（以下为实施前冻结计划）

演示路径：项目里保存带CSV授权材料的目标卡，明确选择可信目录的“数值列求和”能力；指定目标卡版本及材料，创建标MOCK_DETERMINISTIC的声明式候选；校验ActionSpec/AppManifest、依赖版本/权限/预算，建立仅所选CSV的preview应用身份；转到应用页选数值列运行新预览，查看成果/历史，返回目标卡或刷新后仍能回读候选与来源。

对应F2-T01/T02/T04/T05/T06的工程子集、AT-09/11/12/18/22相关子项回归；不是完整AT-09或P-A生成验收：操作/规划由用户显式选固定可信模板，模型请求0。P-B需要已完成任务来源与新资料冷运行，本轮不借用PARTIAL/LIVE任务伪造。允许目标文本作说明，但只支持选择一个已绑定CSV、输入数值列并求和；文档撰写、JSON加工、复杂DAG/分支、模型节点、任意工具/脚本、正式Release/外部写入不支持，明确拒绝其他能力。

目标卡全部已知/假设/未决/硬条件/验收检查及版本/hash原样冻结到候选来源，不自动降低或声称语义条件已满足；条件验收NOT_RUN，候选不可发布。候选绑定旧目标版本，不随新目标修订偷偷变化；指定expected_version过期的新提交拒绝。request_key绑定目标版本/资源/能力，重复返回同候选、不再创建身份/Grant，异参数409。候选回读/运行仍检查全部来源材料授权和hash，历史快照不得恢复已撤销权限；selected CSV每次按user-project-app交集执行。

新增一张goal_candidate_requests只存幂等绑定及candidate引用，显式migrate/应用角色CRUD；API不DDL或自授权。验收覆盖精确来源与冻结要求、编译版本/工具目录、恶意执行器/未知能力/跨资源/跨主体/撤权/篡改/旧版本/重复及并发提交、不同列新结果、零模型/无F1业务写入、浏览器正常/失败/返回/刷新状态；SQLite及精确ServerPG CI、授权普通push到终态。F1未签收/Win11/AT02追加预算待批不变。

## 2026-10-05 / 优先修复目标卡异步选择竞态（实施前范围）

独立审查0382b91发现showGoalCard迟到响应能跨项目或覆盖New草稿；合成双项目/实际延迟GET已复现，项目B显示A卡并PUT修改A，New文字被旧卡覆盖。仅合成记录，无真实数据事故证据。以选择generation使导航/New/重复选择失效，读取结果校验project_id，保存前核对活动卡项目，保存完成不恢复已离开的选择；保持后端CAS。先单独提交本修复，不夹带下一MOCK候选后端改动。浏览器覆盖延迟导航/New/重复打开/保存中导航与New/提交项目校验/正常保存及旧窗口冲突，再精确源码ServerCI到终态；预算0。

## 2026-10-05 / 目标卡竞态修复精确终态交付

已在0382b91真实Chromium/双合成项目复现跨项目PUT及New文字覆盖，无真实数据事故证据；22f352b4f2868c924834eecb546242c5246b8291单独修复并普通push。11交错浏览器PASS，SQLite147PASS/3平台SKIP/1旧警告9.19秒；精确ServerCI37325580965/job111815358944 completed/success（2m03s），PG150PASS/0FAIL/0SKIP/1旧警告40.98秒，ruff/mypy15模块、Setup/F1原生应用角色smoke/Report/Cleanup全PASS，server stopped。E9记录可复跑fixture/浏览器脚本及来源hash；Linux浏览器不冒充Win11/CI浏览器/独立复跑。下一MOCK候选后端及Plan在工作树保留未提交，未混入本修复；原work分支不变，真实模型0/F1未签收不变。

## 2026-10-05 / 候选纵向切片续作与取消边界（实施前）

基线1a2be0d，核对保留planning/API/goal_candidate_requests及apps来源复核改动属于既定切片。补授权目标卡版本的候选选项（已绑定CSV+仅csv.sum可信能力）、保存候选及回读入口、来源/全部条件NOT_RUN、预览成果/返回/刷新。选项只读不授权；显式创建才增仅一个材料24小时preview身份Grant。用户未保存编辑不进入候选，界面说明冻结已保存版本。取消提交前无写入；同步事务已接受后不能假称撤销，取消/导航只停止页面转入，候选仍在列表；网络不确定后同request_key可重试，重复提交保护。API闭合输入/权限/版本/旧来源/篡改/可信执行器/幂等并发/失败回滚测试及真实Chromium正常、无CSV、取消、版本失败保留编辑、重复、预览失败后返回/重载；精确ServerCI终态。MOCK固定模板不等于任意生成，P-A工程子集、P-B未实现；F1未签收/Win11未测/LIVE0不变。

## 2026-10-05 / MOCK候选纵向切片本地闭环

按事前Plan完成已保存目标版本/授权CSV/可信csv.sum目录→固定声明式候选编译→preview身份限定Grant→数值列新预览/历史/返回/刷新。完整人工条件及材料快照保留NOT_RUN，旧候选不会随目标修订改变，闭合输入/权限/来源篡改/幂等并发保护。取消提交前无写入；已接受事务返回编辑不冒充撤销，迟到响应不能跨项目打开。新增24工程检查含待PG应用角色专项；SQLite170PASS/4平台SKIP/1旧警告11.31秒，ruff/mypy16模块/JS/diff通过。Chromium实际正常UI链路、14候选交错/失败、3刷新回读、E9原11竞态回归PASS；旧fixture模块及截图CLI路径问题修正后最终复核，合成server/browser关闭。证据见../evidence/F2-goal-candidate-20261005。普通push后监督精确ServerCI，不预写PASS；P-A工程子集/P-B未实现/真实0/F1未签收不变。

## 2026-10-05 / MOCK候选纵向切片精确Server终态交付

源码e6b3e2c803f1a4dd2fe999e7645472ec0ff29343已普通push；run37329527816/job111828777592 completed/success（2m01s），PG174PASS/0FAIL/0SKIP/1旧警告43.18秒，24新增候选项含临时PG应用角色业务CRUD下目标/options/候选/幂等/预览/历史API路径通过，其余PG工程使用隔离test-owner schema。实际Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/PG17.11/admin=true/EnableLUA1；Setup/显式新表迁移/完整锁、已有F1原生角色API-worker smoke、ruff/mypy16模块、Report/Cleanup全通过，server stopped。Linux170PASS/4平台SKIP、实际正常ChromiumUI+14候选交错+3冷页回读+E9原11竞态保持PASS；不是ServerCI浏览器/Win11/独立复跑。E10精确run/results/source hashes及人工复核截图归档；文档收尾普通push不重复CI。明确P-A人工目标+固定模板工程子集、P-B未实现、目标条件NOT_RUN、PREVIEW_ONLY/无Release，真实模型0/F1未签收/正式发布门不变。
