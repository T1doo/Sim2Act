# F2 并行工程 Plan：权威当前状态

## 2026-10-05 / P-B 可信预览回执提取（实施前冻结）

基线9bd4bac，独立/workspace/Sim2Act-pb、dev/f1-foundation；原work树和旧任务不改。V5产品§4 P-B/F2-T03/AT-10要求从已完成任务的输入输出、工具与检查形成新输入应用；现F1 Run终态PARTIAL不可作成功来源。本轮只接受本地合成PREVIEW命名空间SUCCEEDED回执，不接受F1 Run，不改AT02。源声明式模板、输入指纹、输出、实际材料hash和独立Decimal oracle必须可重核；FAILED/UNKNOWN/PARTIAL、存储篡改、撤权、非可信模板拒绝。

范围：从单节点可信CSV求和预览提取稳定工具/版本与输出schema，明确column是运行参数、新CSV是创建时显式绑定参数，同项目新材料且hash不同；冻结源app/preview/候选/回执hash、原目标条件及NOT_RUN，绑定新材料版本和最小应用Grant。仅一层提取，不生成模型节点/代码/复杂DAG/Release，不承诺通用归纳。Manifest task_run来源明确指向PREVIEW回执ID，绝不冒充F1 Run。冷页面运行读取新CSV，不能返回旧输出；当前旧来源仍需可授权重核，撤权保守拒绝，是明确工程限制。

新增preview_extractions只由显式migrate建表、应用角色业务CRUD；API不DDL。源应用行锁串行幂等创建；expected_source_fingerprint防旧窗口、request_key绑定源回执与新材料，冲突不新增身份/Grant。每次回读/预览重核源回执与权限、新材料hash、提取声明及版本。UI从成功历史独立入口提取，明确来源类型、范围、授权与未发布，迟到响应不能跨项目或覆盖新选择。

验收：正常可信源→新资料候选→冷页新结果/失败历史；跨主体/同主体跨项目、源状态/回执/模板/资源篡改、撤权、旧版本、同键异参及并发、无额外Run/Operation/attempt；SQLite回归、PG应用角色CRUD/精确WindowsServerCI终态、真实Chromium正常/失败/导航/刷新检查。真实模型预算0，Win11/F1签收/完整AT10/P-B与发布仍未完成；失败和未测边界保留。

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

## 2026-10-05 / P-B受限提取本地结果，Server终态待核实

实现成功合成PREVIEW回执/完整可信模板/独立整数sum oracle→版本化来源证据→同项目新CSV最小权限候选→新结果/失败历史与冷客户端。32新增工程检查PASS、1应用角色专项待PG；全SQLite202PASS/5平台SKIP/2警告19.86秒，ruff/mypy17模块/JS/diff通过。Node/jsdom实际HTTP/产品JS12交互PASS，明确非浏览器。真实Chromium正式审批仍无可用沙箱，0检查/BLOCKED，不关闭沙箱；保留fixture/错误。证据E11，完整P-B/AT10/F1签收/Win11/发布未完成；模型请求0。普通push精确源码并监督WindowsServerCI，尚不预写PG通过。

源码8334bc1普通push已启动37340445433；提交后收尾核查补强源回执input被存储篡改为JSON null时的闭合拒绝（避免500），新增负例通过。最终源码全SQLite203PASS/5SKIP/1旧Starlette警告20.30秒，33新专项本地通过、1 PG角色专项待CI；DOM源码未改，12项原检查保持。补强单独普通commit/push，监督最终源码CI；早先200/202计数为阶段历史不覆盖。

## 2026-10-05 / P-B受限工程精确Server终态交付

最终源码3d87f5eb6c8738b8dad4027260fb526a045ca3d5普通push，run37340717581/job111866785041 completed/success（2m38s）。PG208PASS/0FAIL/0SKIP/1旧警告68.30秒，34新提取检查含临时PG最小业务CRUD角色源/提取/重试/回读/新输入整条API路径；其余工程隔离fixture-owner schema，包括两个并发提取writer。Setup/显式迁移/依赖锁/现F1原生API-worker应用角色smoke/ruff/mypy17模块/Report/Cleanup通过，server stopped。第一源码8334bc1/run37340445433也SUCCESS、PG207PASS/0SKIP/41.27秒，保留历史。E11源码hash/两run/最终平台结果归档；文档收尾仅普通push，不重复CI。真实Chromium0/BLOCKED、DOM12非浏览器、Linux203PASS/5SKIP不混写；模型0/F1未签收/Win11/完整P-B及AT10/发布未完成不变。

## 2026-10-05 / 已有两路径工程可用性与界面收敛（实施前）

基线6b008b2，同一/workspace/Sim2Act-pb。用户要求前端好看，下一阶段路线见NextSteps.md，冻结颜色/字号/间距/层级/五类状态/手机一致性验收；不换框架或大改架构。启动同工作区独立只读代理，限定权限/来源/参数范围/过期撤权/状态冲突，具体缺陷优先。核查平台可调用工具无浏览器入口，官方runtime show退出1/无连接元数据；现Chromium保护仍不可用，不关闭sandbox或探查私有认证/管道。只可小范围CSS/语义状态改善，不预写实际视觉PASS。

本轮验证：独立复核报告与可复现缺陷、针对修复的状态/导航/负例；源与目标Grant自然过期仍拒绝；SQLite/静态/DOM交互、普通push精确ServerCI。没有新增表/迁移或模型/代码生成/Release；PREVIEW来源子集不称完整P-B/AT10，预算0/F1和Win11未签收不变。浏览器/手机视觉未验证保留BLOCKED。

本轮独立代理基线6b008b2只读复核77PASS/2PG角色SKIP，并复现来源删除绕过额外撤权、P-A输出接线改写仍成功、direct创建迟到抢选择、Decimal溢出500/无失败历史4项；5组P-B自然过期仍403。主开发修复4项，CSV完整模板校验复用于P-A/P-B，goal_candidate_requests来源锚点；direct/preview选择世代与状态反馈，DecimalException失败历史/guidance一致性。11新增专项及全SQLite214PASS/5SKIP/2警告26.11秒、DOM20PASS；CSS可逆统一色彩/字号/间距/表单/焦点/禁用/状态/手机规则，不是实际视觉PASS。独立报告不覆盖修复，主开发实际回归；Server终态待精确核实，预算0。

## 2026-10-05 / E12精确Server终态与界面验收依赖

源码d3de155ba23cd5ba824f10f398f34b25c76e1817普通push；run37343525441/job111876274963 completed/success（2m36s），PG219PASS/0FAIL/0SKIP/1旧警告70.78秒。Setup/现显式迁移/最小应用角色CRUD/原生API-worker smoke/ruff/mypy17模块/Report/Cleanup成功，server stopped。11新增专项与既有完整工程通过；独立复核只覆盖基线6b008b2，修复由主开发回归，未独立复验。E12终态/results/89源码hash归档，文档收尾普通push不重复CI。真实视觉0/BLOCKED、20DOM不是截图；后续保留保护的浏览器通道/桌面手机状态审阅仍依赖，NextSteps前端美观标准保持。源码不再扩大抽象/框架/生成能力，真实0/F1/Win11/完整P-B/AT10/Release边界不变。

## 2026-10-05 / E13邻接锚点与已接受回读失败（实施前）

基线5d58951/d3de155，读NextSteps，范围仅静态复核指向的两个缺陷及preview同类回读。已合成复现同卡v2候选协调替换为有效v1的goal_version/snapshot/fingerprint/goal并重算candidate指纹，GET200/preview SUCCEEDED，撤回v2新增条件材料后仍然通过；属于既定DB篡改/重算指纹防御范围，非已暴露API攻击/真实泄露。新负例修前两FAIL；direct创建POST成功/GET503的DOM回读状态断言修前FAIL（测试脚本同名变量语法问题先纠正，不是产品缺陷）。

修复范围：从候选来源版本、所选resource和capability重建原始请求指纹，与持久goal_candidate_requests.request_fingerprint独立锚点比对；不靠重算被篡改对象自己的hash，也不将合法旧版本强制变成最新。direct/preview已接受POST后GET失败明确显示已创建/已执行及读取失败，提供只GET回读重试，不再POST；showApp开始选择的generation需被调用方跟踪，外部切换项目/草案/目标卡使迟到响应失效。新表/迁移/模型/新功能均无。

验证：协调降版/撤权负例、合法旧版本仍冻结、能力/材料绑定；DOM确认接受后失败/失败重试/仅GET恢复/不重复创建或执行/导航隔离；原20DOM与全回归、普通push精确ServerCI。真实浏览器0/BLOCKED，绝不称视觉PASS。NextSteps补明来源每次重开旧文件的运行依赖及后续来源退休权限策略/合成已完成任务fixture，不拿冷页面回读替代AT10旧文件独立。预算0/F1/Win11/P-B/发布门保持。

## 2026-10-05 / E13本地闭合，Server终态待核实

5专项PASS，全SQLite219PASS/5平台SKIP/1旧Starlette警告25.22秒；ruff/mypy17模块/JS syntax/diff通过。33 Node/jsdom实际HTTP检查PASS，含重复回读失败/仅GET恢复/创建执行各一次/三类导航隔离，非浏览器。实现独立已接受请求锚点及direct/preview恢复状态，NextSteps明示运行时旧来源文件依赖、来源退休策略及完成task fixture未实施。无新表/迁移/模型请求，普通push后监督精确ServerCI；未预写终态。

## 2026-10-05 / E13精确Server终态交付

源码4d01fb72990fb73687a46d902b574b53c583288d已普通push；run37346429353/job111886032367 completed/success（2m19s），PG224PASS/0FAIL/0SKIP/1旧Starlette警告63.13秒。5新锚点专项及完整工程，Setup/现显式迁移/业务CRUD最小应用角色/原生API-worker smoke/ruff/mypy17模块/Report/Cleanup全成功，server stopped。实际Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/admin=true/EnableLUA1/原生临时PG。Linux219PASS/5SKIP/1警告25.22秒，DOM33明确非浏览器；修复未独立复验。E13终态/结果/90源码hash归档，合成服务已停，文档收尾普通push不重复CI。来源仍每次重开旧文件，来源退休授权策略及已完成合成task fixture待后续，冷页不替代AT10。真实浏览器0/BLOCKED，模型0，F1/Win11/完整P-B/AT10/Release未签收。

## 2026-10-05 / E14实施前：合成完成任务与显式来源退休

基线c40b752/4d01fb7，独立静态复核关闭E13两项（未独立执行/视觉）。范围仅固定CSV精确求和的本地声明式合成任务、最小不可变来源证明、显式退休及新输入冷会话。不是F1 worker PARTIAL改成功，不复用PREVIEW充当完成任务，不扩展生成/Release/账户安全设置。

策略：任务实际可信工具读入/求和与独立整数oracle一致才SUCCEEDED，输入失败保留FAILED。来源证明只留owner/project/task/source定位与hash、输入输出指纹、可信工具/检查版本、完成状态和参数范围，不留CSV单元格/旧答案/原会话。提取必须在旧源可读且授权有效时复核完成回执，独立任务证明与候选锚点保持一致。显式owner退休命令只接受当前源hash/证明版本及retain_minimal_proof=true：原子清空旧文件内容及任务input/output，不保留可读备份；保存退休回执。退休不是撤权，不新增/恢复任何旧源grant，不设置真实账户安全策略。当前来源user/project-runtime读/求和grant仍需有效；撤权或过期继续拒绝候选。新输入依旧同项目固定新CSV，运行column参数，并遵守user/project/app三方当前授权交集。未知退休策略/证明缺失/篡改/源hash变动默认拒绝；未退休的来源仍实时回读。旧PREVIEW路线行为不改。

验收：真实LOCAL_DECLARATIVE_TASK合成完成/失败状态及可信回执，不是Run或PREVIEW；退休后的全新Store/API客户端新结果（不是缓存）及坏输入失败历史；旧file GET/工具读拒绝且存储内容/input/output清空；最小证明无内容/旧答案；源/目标撤权、过期及跨owner/project/runtime/App授权负例；证明/候选hash重算/版本、幂等与退休重试；显式迁移应用角色业务CRUD、聚合回归及精确ServerCI。真实浏览器沿E13 BLOCKED/0，不绕sandbox；AT10只记固定合成子项，完整原规格/F1/Win11/Release均未签收，模型预算0。

## 2026-10-05 / E14本地切片闭合，Server待核实

完成独立LOCAL_DECLARATIVE_TASK固定CSV可信执行/oracle及成功证明，不提升F1/PREVIEW终态；显式退休清旧content及任务input/output、不改grant，最小证明保留，源授权撤权/过期仍拒绝。新CSV user/project/app交集及坏输入FAILED历史，三显式迁移表/业务CRUD，既有F1/目标卡/应用共享源拒绝退休；UI只补来源说明与禁止递归，无生成/框架/Release扩展。36新专项，本地35PASS/1PG待CI，全SQLite254PASS/6平台SKIP/3警告30.16秒、ruff/mypy18/JS/diff，原33DOM及新14HTTP/DOM PASS，均非浏览器。最初测试状态映射和projects脚本响应结构错误已纠正；产品拒绝契约未更改。普通push精确源码/监督ServerCI，真实浏览器0/BLOCKED/模型0；只合成固定切片，完整AT10/P-B/F1/Win11/Release未签收。

## 2026-10-05 / E14精确Server终态交付

源码c776fa24dac957485a65337ed3d4b428848b584c普通push；run37349609291/job111896821583 completed/success（2m31s），PG260PASS/0FAIL/0SKIP/1旧Starlette警告69.05秒。36新检查含临时PG最小应用角色完成task/提取/退休/回读/新输入/错误历史/重试整条业务CRUD，三张新表由现显式Setup迁移创建，API/worker无DDL；原生API-worker smoke/ruff/mypy18模块/Report/Cleanup全通过、server stopped。实际Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/admin=true/EnableLUA1/原生临时PG。Linux254PASS/6平台SKIP/3警告30.16秒；原33+新14DOM/HTTP非浏览器。92源码hash/终态/results归档，修复未独立执行复验；合成服务停，文档收尾普通push不触发CI。完成LOCAL_DECLARATIVE_TASK固定数值任务，最小证明及owner显式清旧source内容/任务input/output，源当前grant不新增/恢复且撤权/过期拒绝，新输入交集保持。旧PREVIEW仍需旧资料审计，其他共享消费者拒绝退休。仅这个有界合成切片，完整P-B/AT10/真实生成/Release未签收，F1/Win11保持、视觉0/BLOCKED、模型0。

## 2026-10-06 / E15实施前：PG来源退休与消费者创建交错

恢复环境ready，/workspace/Sim2Act-pb干净dev/f1-foundation 54ac055，正常origin fetch同HEAD；旧初始work不改。范围仅E14来源退休与消费者创建竞态：用真实PG barrier控制事务两种顺序，核查grant现有锁是否足以闭合；对消费者统一project锁并在锁内重验当前内容/退休状态，锁顺序project→card/app→grant，避免退休扫描后出现新消费者及反向锁死。覆盖direct草案、F1提交、目标卡创建/修订、候选/提取共享持久化入口。保留旧来源授权/退休默认拒绝、无新表/权限/CSV能力/真实模型。实际复现结果据实记录，不将SQLite或假锁作为PG通过。聚合/普通push精确ServerCI；之后只映射冻结AT10的完成合成任务→提取→退休→fresh Store新/坏输入子项，完整P-B/Win11/F1/Release仍未签收，0LIVE/无导出/无sandbox绕过。

E15本地结果：真实临时PG17.11，9 barrier/冷Store专项PASS（3.26秒）；全LinuxPG268PASS/1Windows平台SKIP/2警告82.16秒，SQLite254PASS/15PG/平台SKIP/2警告33.30秒；ruff/mypy18模块/JS/diff通过。基线grant锁挡住观察direct退休交错，未复现成功失效app；共同project锁缺失的负断言1FAIL/1PASS，补强后统一锁及重验。冻结AT10合成子项映射已保存，不改V5/历史AT02或签收门。普通push精确ServerCI待核实；本地测试容器随后清理，0LIVE/无导出。

## 2026-10-06 / E15精确Server终态交付

源码53dc124ea8aeb554939ad79bbbb7d9526a66578f普通push；run37411714116/job112101374653 completed/success（2m51s），PG269PASS/0FAIL/0SKIP/1旧Starlette警告88.51秒。9新真PG barrier/冷Store子项及完整业务CRUD角色回归，原生API-worker smoke/ruff/mypy18模块/Report/Cleanup全部成功、server stopped；实际Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/admin=true/EnableLUA1/原生临时PG。LinuxPG268PASS/1Windows平台SKIP/2警告82.16秒，SQLite254PASS/15平台/PGSKIP/2警告33.30秒，PG专项9PASS。基线退休200/direct400（grant锁挡住交错），未复现成功失效app；共享project锁缺失真实补强，统一project→entity→grant与写前当前内容/退休重验。93源码hash/实际run/results及冻结AT10合成子项映射归档；未独立执行复验，真实浏览器0/BLOCKED，不新增CSS/视觉签收。保存环境恢复ready/正确工作树54ac055与origin一致，初始work未改，本地合成PG容器已停并删除；文档收尾普通push不重复CI。0LIVE/无导出，完整P-B/AT10/Win11/F1/Release签收未提升，V5/历史AT02不变。

## 2026-10-06 / E16实施前：F2-T08内部合成生命周期

基线764a20f/53dc124，origin正常fetch一致。读V5阶段§4.3 F2-T08及产品§10：不可变Release绑定清单/动作/依赖/检查、批准指纹与数据兼容；AppInstance独立持久数据，指针CAS，升级/回退不删数据，新输入新AppRun/结果版本；发布回退不等于数据回退。原F1/真实P-A/P-B/Win11/保护浏览器阶段门不放行，E15仅锁序加固（未复现成功失效app）保持。

本轮最小内部工程service，不接入HTTP发布入口/页面/实际部署。显式迁移internal_*表，内部批准payload一次写入绑定owner/project/source candidate及精确manifest/actions/dependencies、实际新可信验证/oracle证据、当前相关授权修订、到期时间和实例切换前置revision/data_version。提交时精确fingerprint/版本/当前授权重验，Release副本独立于可变草案、无编辑入口；instances复用该候选既有应用runtime/grant，不创建/恢复/扩大grant。实例数据限新AppRun计算出的类型化result记录及可选release_ref元数据，独立namespace/版本/历史；无任意业务写入/CSV新便利项。新AppRun实际走现权限网关/严格输入输出和独立数值检查，不复制PREVIEW历史，失败真实保留。只兼容字段保留/类型不变/不新增必填的声明升级，回退也按当前数据/schema校验；不自动迁移或删除记录。

测试范围：批准前指纹/草案/资源/授权/到期改变拒绝；Release写后篡改/不可变旧快照/跨owner；两instance数据和幂等独立，fresh Store回读、失败历史与新结果版本；用户/project/app当前撤权/过期拒绝，Grant前后完全一致；升级/回退CAS及不兼容拒绝/历史保留；明确正式发布入口不存在。用户要求同工作区独立只读审查，完成源码后委派，修具体问题并aggregate/普通push精确ServerCI。0真实调用，无导出/备份/安全策略绕过，完整P-B/AT10/Release正式发布、Win11/F1仍未签收。

## 2026-10-06 / E16实现与独立审查修复

内部生命周期service与五表显式迁移实现，精确批准绑定快照/来源/权限版本；独立实例类型化result账本与真实新AppRun，兼容指针切换保留历史/数据。不新增CSV功能或运行身份/grant，不启用HTTP/正式发布。独立合成复现schema缺properties异常和额外enum批准覆盖缺口，修为封闭受限schema；测试文件重名覆盖原AT05发现后逐字恢复，新增test_internal_lifecycle.py。补实际source bytes hash重验及严格schema版本转移。定向32PASS/2平台SKIP，SQLite/真PG聚合、独立修复复验、精确ServerCI进行中。详见InternalLifecycle.md，失败/未测门保留。

E16源码固定前aggregate：真LinuxPG301PASS/1WindowsSKIP/2警告111.58秒，新内部33项含PG应用角色业务CRUD；全SQLite286PASS/16平台或PGSKIP/1警告42.21秒。独立复验32PASS/1PGSKIP/1警告5.41秒且3个源码hash一致，未独立执行PG/Windows。静态ruff/mypy19/JS/diff通过，源码正常commit/push与精确ServerCI下一步。

## 2026-10-06 / E16精确Server终态交付

源码e029922794c9f9829ddb41bca0010aebc277e761已普通push，CI37413258268/job112106185925 completed/success（3m26s），PG302PASS/0FAIL/0SKIP/1旧警告118.16秒。33新内部检查及原AT05进程完整覆盖；Setup/五张internal表显式迁移/业务CRUD角色/原生API-worker smoke/ruff/mypy19模块/Report/Cleanup成功，server stopped。LinuxPG301PASS/1WindowsSKIP/2警告111.58秒；SQLite286PASS/16平台PGSKIP/1警告42.21秒。独立复验32PASS/1PGSKIP且两schema问题关闭，三个源码hash与交付一致；未独立PG/Windows/视觉。95源码/test/config及run/results已归档，专用本地PG stop/remove，原work树不改。只内部不可变Release/instance结果账本/真实新AppRun/兼容指针生命周期，正式发布入口及部署未启用，完整P-A/P-B/AT10/F1/Win11/protected-browser未签收，模型0。文档收尾普通push不重复CI。

## 2026-10-06 / E17事前：固定内部 AppRun 接入持久 worker

基线1149816/e029922，正确/workspace/Sim2Act-pb、正常origin fetch同分支。依据原V5 F2-T09与产品§8/§10，仅E16已有固定可信Release/Instance：原子enqueue新内部AppRun、固定Release/实例revision/输入和既有Run队列；复用现claim/lease/fencing/独立heartbeat/事件账本，不建grant，不扩展CSV。短事务授权读取输入及PREPARED意图，可信纯计算在事务外，短事务重验当前Release/Instance/Grant/fence并把结果版本+回执+AppRun终态原子提交；不在长服务事务中同步执行。正式发布/部署入口保持关闭。

验收冻结：enqueue后全新Store重开；实际独立worker进程接受/停止/重启与前后提交崩溃窗口；派发前pause/cancel阻止新动作；heartbeat/过期fencing拒绝旧提交；当前grant撤权/过期进入WAITING_RESOURCE并保留历史；同键幂等/跨instance隔离/并发只追加一次；错误输入FAILED无结果版本。失联只重排已知安全纯读/未提交本地事务，已有VERIFIED本地结果不重复追加；注入未知操作保持等待/RECONCILING及cancel intent，不清账本盲目重试。升级导致已接受revision前置变化采用保守拒绝，不静默换Release或迁移数据。独立只读关键边界审查，最终SQLite/真实PG/精确ServerCI；新增表经显式migrate/Setup，API/worker无DDL。

AT17只读sum不证明preview写隔离，保持OPEN直到受控写fixture真正验证。本轮不是通用动作/业务数据写入、未知外部接口已恢复或完整F2。0LIVE/无导出/无sandbox绕过，原AT05/V5/历史AT02保留，F1/Win11/完整P-A/P-B/AT10/protected-browser门不提升。

## 2026-10-06 / E17本地实现及独立复验

内部新AppRun+现Run队列+固定输入契约+一张internal_run_bindings原子enqueue，既有claim/lease/fencing/heartbeat及事件/Operation；固定授权快照取入、事务外可信计算、当前source/Grant/实例revision重验后结果+receipt+双终态原子追加。仅已有app runtime，旧F1 envelope最小接受appruntime格式，F1创建身份/历史不改。任意call_id未知门及cancel intent保持；源码失败写入也用独立accepted快照绑定，不改另一instance历史。

独立实际复现初版Literal/格式拒绝、未知call_id误SUCCEEDED、可改plan来源及output metadata、failure原始binding引用损坏foreign成功历史，均修复并持久负例；无法安全定位的原残留AppRun不猜修，读取拒绝边界保留。独立最终33PASS/4PGSKIP/1警告12.29秒，source/test hash核对，原AT05保留。主开发真PG定向35PASS/1警告31.11秒含4真实worker子进程：提交前/后os._exit与另进程恢复，hold时heartbeat/独立控制事务/暂停取消无追加；新补lease同fence过期及budget负例在完整aggregate。SQLite319PASS/20PG平台SKIP/3旧警告59.52秒，静态通过；完整PG/精确CI待核实。正式发布/部署关闭/模型0/AT17写隔离OPEN，其余阶段门保持。

E17源码稳定后首轮完整真PG338PASS/1WindowsSKIP/3旧Starlette/Pydantic警告150.41秒，全部37新增用例包含4真实子进程；全SQLite319PASS/20平台PGSKIP/3旧警告59.52秒。补一项必要的最小PG角色直接enqueue binding/控制/resume/worker/result业务CRUD（先前子进程仅worker消费角色、enqueue为test-owner），以覆盖新表INSERT实际路径；源service不变。该新PG检查与最终完整aggregate/ServerCI另外核实，绝不合并猜数。

## 2026-10-06 / E17精确Server终态交付

源码8b14cee7ca8b55bef5f5e2f3dfd3a89482f837e2普通push，CI37415214667/job112112211461 completed/success（3m24s），PG340PASS/0FAIL/0SKIP/1旧Starlette warning128.36秒。38新内部项含4真实最低角色worker子进程与最低角色enqueue/控制/worker CRUD；原AT05逐字保留及完整实跑。Setup/binding表显式迁移/原生API-worker smoke/ruff/mypy20/Report/Cleanup全成功，server stopped。最终LinuxPG339PASS/1WindowsSKIP/2旧警告145.72秒、SQLite319PASS/21PG平台SKIP/2旧警告55.34秒；独立最终33PASS/5PGSKIP/1警告12.54秒，source/test hash与交付一致，未独立PG/CI。98源码/test/config/run/results已归档，专用PG stop/remove、原work/V5/AT02未改；文档普通push不重复CI。仅内部固定queue/reopen/lease/fencing/currentgateway/原子结果版本与安全恢复；关联损坏残留AppRun不猜修、指针改变保守拒绝、未知外部效果未恢复证明。正式发布/部署关闭、AT17受控写OPEN、完整P-A/P-B/AT10/F1/Win11/protected-browser不签收，模型0。

## 2026-10-06 / E18事前：AT17受控预览写隔离证据与阶段门

基线727d023/8b14cee，正常origin fetch核对、正确/workspace/Sim2Act-pb，初始work树/V5/历史AT02保留。本轮不扩CSV或生命周期功能；仅原AT17预览中真实写入的合成故障fixture与阶段门审查。现生产preview是固定读/计算，不具写action；因此严格标FAULT_INJECTION，而非生产写接口、正式发布或完整F2签收。

fixture只在tests中、明确test_only Store与pytest SQLite临时目录/隔离test_ PG schema；独立MetaData表经fixture显式Setup，生产meta/CLI迁移/工具目录/HTTP接口无新增写能力和Grant。把受控SQL business-record写入注入实际apps.preview持久INSERT同一Store.tx，以真实数据库行为核查namespace/rollback/idempotency。明确PREVIEW/owner/project/app/preview_id，不接受instance/release目标；固定受控record来自实际preview输入，不隐藏新调用参数或自授权。

冻结验收：成功实际写并新连接独立读回；after-write故障先证明事务内已写再抛错、preview及fixture写全回滚；相同逻辑请求重复/并发只有一份record/receipt，不同输入键冲突；错误namespace/owner/project/app/instance/release绑定拒绝。真实E16Release/两instance和数据预先落库；每次前后对所有生产meta（仅允许app_previews历史变化）的原始column CAST text/UTF8快照逐字节比对，包含instance typed-data/版本/历史、grants、principals、resources、runs等。不能只核table count或hash宣称字节一致。

同工作区独立只读审查、SQLite/真实PG最终aggregate、精确源码ServerCI及正常devpush；无真实模型/外部写/恢复包/安全绕过。然后依V5明确F1/F2/P-A/P-B/AT10/AT17/AT20/WindowsServer/Win11/真实浏览器每项证据及最小缺口、下一阶段实际决定/接入，不用总测试数签收。AT17只闭合该受控写隔离现象证据；生产writer/正式preview action与完整阶段门仍需独立前置。

## 2026-10-06 / E18实现与独立复验

13项实际受控SQL写隔离检查已实现；独立发现receipt写入前故障不能证明receipt回滚，已移至record+receipt实际INSERT/同conn读回后。最终独立13PASS/1warning4.57秒，三文件hash一致；主开发真PG专项13PASS/1warning13.01秒，SQLite完整332PASS/21PG平台SKIP/1warning55.92秒。全PG/精确ServerCI待核实。生产唯一变化保存已有test_only标志，默认False；测试独立MetaData，不新增生产表/工具/Grant/入口。阶段门逐条见[StageGateReview](StageGateReview.md)，仅AT17_SYNTHETIC_FIXTURE，正式AT17/发布仍OPEN。

E18最终本地全PG352PASS/1WindowsSKIP/3旧警告155.54秒、SQLite332PASS/21PG平台SKIP/1旧警告55.92秒；13新项全两DB已过，独立13PASS、最终hash一致。源码925e560dc1a196c6c4747cb349d558156a721c0f普通push，精确ServerCI37416936441进行中；原AT05/V5/历史AT02差异为空，不提前记CI成功。

E18精确终态：925e560dc1a196c6c4747cb349d558156a721c0f已普通push，[CI37416936441](https://github.com/T1doo/Sim2Act/actions/runs/37416936441)/job112117505998 completed/success2m47s，PG353PASS/0FAIL/0SKIP/1旧警告105.29秒；Setup/应用角色原生smoke/ruff/mypy20/Report/Cleanup全成功，server stopped。LinuxPG352PASS/1WindowsSKIP/3旧警告155.54秒，SQLite332PASS/21PG平台SKIP/1旧警告55.92秒；独立13PASS1warning4.57秒且3文件hash一致，未独立PG/aggregate/CI/browser。13新合成写项及100source/test/config hash/实际结果归档到docs/evidence/F2-preview-isolation-20261006；专用PG stop/remove，原work/V5/历史AT02/AT05不改。仅AT17_SYNTHETIC_FIXTURE PASS；正式AT17/发布、完整P-A/P-B/AT10/AT20/F1/Win11/保护浏览器仍OPEN或NOT_RUN，0LIVE/无导出/无安全绕过。本轮停止相邻功能扩张，下一真实决定/接入见F2/StageGateReview.md。文档收尾普通push不重复CI。

## 2026-10-06 / E19事前：已认证内部工程入口

基线b7895ea/925e560，正常origin fetch核对一致，正确/workspace/Sim2Act-pb。依据原F2T05/T08/T09，仅把已有可信只读内部Release→Instance→持久AppRun接入认证API及应用页；明确INTERNAL_ENGINEERING_ONLY，正式发布部署False。精确snapshot审批须页面显示回读冻结清单/检查/期限及指纹后显式确认；只读action与当前user/project/app授权保持，不新增/恢复Grant，无任意代码、外发或LIVE。新增实例同意图request_key幂等复用现表，不新增DDL；新运行复用持久worker及Run控制，结果版本/历史独立。

冻结验收：无身份/跨owner/project/instance读取和变更拒绝、批准指纹/版本/到期/当前授权变化拒绝、重复创建/提交只有一个逻辑效果及异参数冲突、应用页切换时迟到响应不覆盖、重复点击busy、提交返回失败保留原键可恢复、取消返回不取消已接受后台、pause/cancel/resume及刷新重开当前历史。桌面/手机可读样式，受保护真实浏览器先核现工具正常途径，不可用保存实际错误；不--no-sandbox/改策略，DOM不是视觉验收。全SQLite/真实PG/精确源码ServerCI/普通devpush/证据与阶段门更新；原V5/AT02/AT05及初始work不改，0LIVE/无导出。该内部入口不是正式发布或完整F2/P-A/P-B签收。

E19本地入口实现：精确内部批准/Release/独立实例/持久queue/control/history接入Bearer API/UI；实例同键持久幂等、不增表或Grant；撤权owner仅最小stopmetadata，resume仍当前权限。独立实际复现late create抢实例选择并关闭，refresh两交错复验通过；新增本页旧意图结束按钮必须先GET当前历史，不取消后台/自动新提交。独立18PASS/1PGSKIP5.50秒、4文件hash一致；真PG专项19PASS11.17秒含最小CRUD角色；实际HTTP/jsdom27PASS且另一进程实际revision→UI409/新意图，NOT视觉。SQLite350PASS/22SKIP/2旧warnings75.53秒；完整PG出现1失败待定位，未记CI成功。protectedChromiumSUID helper BLOCKED，无--no-sandbox。

E19完整SQLite350PASS/22PG平台SKIP/2旧warnings75.53秒；首轮LinuxPG370PASS/1FAIL/1WindowsSKIP/3旧warnings202.56秒，原AT05 start检查API/worker exited、两空日志，无异常栈/oom证据，根因未定位。原AT05/manage不改，相同源码单独重跑1PASS10.72秒；保留抑制配置后的失败JUnit，完整PG再跑/精确CI待核实。27actualHTTP/jsdom和独立18PASS/1PGSKIP/4hash一致，版本冲突旧意图可显式读取历史后结束，不自动提交或取消后台。

E19收尾修正通用项目页showRun：内部AppRun不再误称书生记录，明确内部只读/0模型及版本；迟到task/project/token/generation回读和命令返回保护。最终actualHTTP/jsdom29PASS（不是视觉），原27项未删。JS源码变更须另普通push/精确CI，5462b24候选CI不替代最终源码验证。

E19最终Python/API/service完整LinuxPG重跑371PASS/1WindowsSKIP/2旧warnings229.50秒，原AT05通过；首轮启动failure保留、根因未确认，AT05/manage/V5/历史AT02不改。最终源码aaf07f49b3d32eeb360d8cd60a52a4fad22959fd普通push，项目页JS最终actualHTTP/jsdom29PASS（NOT视觉）、独立接口18PASS/1PGSKIP及UI交错，103source/test/config hash保存；旧候选CI37419044735被新提交concurrency取消，新精确CI37419363378进行中，不记成功。

E19精确终态：aaf07f49b3d32eeb360d8cd60a52a4fad22959fd普通push，[CI37419363378](https://github.com/T1doo/Sim2Act/actions/runs/37419363378)/job112125096801 completed/success2m39s，PG372PASS/0FAIL/0SKIP/1旧warning100.86秒，19新项含实际最小CRUD角色API链及原AT05；Setup/原生smoke/ruff/mypy21/Report/Cleanup全成功，server stopped。LinuxPG最终371PASS/1WindowsSKIP/2warnings229.50秒，SQLite350PASS/22PG平台SKIP/2warnings75.53秒；首轮AT05启动failure、空日志保留，根因未确认，单独1PASS及完整重跑通过，原AT05/manage不改。actualHTTP/jsdom29PASS不是视觉，独立18PASS/1PGSKIP5.50秒及UI交错/最终main JS静态，5hash一致，未独立PG/CI/29DOM/browser；protectedChromiumSUID helperBLOCKED，不绕过。103source/test/config/results/evidence归档，仅内部工程认证只读Release/Instance/持久AppRun批准/history/control/reopen，无新增生产Grant/表/业务writer，正式发布部署false。兼容switch未接页面、完整F1/F2/P-A/P-B/AT10/19/20/Win11/视觉原门保持。合成server/PG stop/remove、原work/V5/AT02/AT05不改，0LIVE/无导出；文档普通push收尾不重复CI。

## 2026-10-06 / E20事前：有界稳定性诊断

基线e94ddc9/aaf07f4，正常origin fetch同HEAD。仅收敛原AT05首次进程启动failure及E19身份/instance/history/control复验，不加feature。原失败JUnit与空日志现象保持，失败test time1.269s、manage报exited而不是startup健康timeout；现证据不能区分真实子进程退出与process身份判定拒绝，更不能从空日志或后续绿色推断根因。

冻结诊断上限：4次原AT05原样独立重复，再4次保留原全部断言的diagnostic launcher重复（只观察monotonic时间、process判定/当前cmd匹配/创建时间差/实际Popen退出码/日志长度，输出不含配置/凭据）；每次合成隔离PG schema/最小CRUD角色/新port/tmp，不引入生产诊断flag或额外工具。不改原测试、失败时也完整原finally停止。若发现具体可复现原因，另记录最小修复与负例及原AT05/aggregate/精确ServerCI；否则保持未知，不改产品凭猜测、不无限加次数。

用户显式要求独立只读E19认证API/跨owner-instance-history-control/currentgrant复验，默认继承6.1solmedium。读protectedChromium实际helper65534:65534(mode4755)，工具已因非root-owned拒绝；只列环境方正常安装/root-owned helper或可用内核namespace sandbox/受保护CDP runner的最小要求，本轮不chmod/chown/关闭sandbox/绕过拒绝，不追加DOM冒充视觉。0LIVE/无导出/正式发布关闭/原work/V5/AT02/AT05保持，正常devpush及精确CI按实际源码变化与授权执行。


## 2026-10-06 / E20有界稳定性诊断终态

见 [稳定性报告](../evidence/F2-startup-stability-20261006/README.md)：原AT05原样4PASS39.99s、观察修正后4PASS35.59s，原断言/manage/test未改；初版probe参数名冲突4FAIL14.55s独立保留，仅观察包装器修正。有效12start/24child、0启动process拒绝，boot epoch恒定；停止阶段拒绝不能解释首次启动failure。首次1.269s进程guard错误、空日志、无PID/rc/bootepoch，原因保持UNKNOWN，不从绿色推断修复、不无限重复、不改产品。独立E19 API18PASS/1PGSKIP4.53s及跨owner-instance-history-control/撤权合成负例拒绝；损坏binding聚合history遗漏但直接409边界保留，未独立PG/CI/browser。

受保护Chrome实际helper65534:65534 mode4755，owner错误/正常namespace历史No usable sandbox；环境方最小提供正常沙箱浏览器或已有protectedCDP/connector，不chown/chmod/--no-sandbox/绕拒，视觉0BLOCKED。24有效child已退出为ppid1 zombie，无执行中owned服务，环境init未reap如实保留；专用PGstop/remove，不杀系统进程。source/tests/config与aaf07f49b3d32eeb360d8cd60a52a4fad22959fd无差异；精确CI37419363378重新核验success/372PASS0FAIL0SKIP，文档push不触发paths，不借CI关闭UNKNOWN。0LIVE/无导出/正式发布关闭，原work/V5/AT02/AT05/阶段门不变。有效上限4+4结束，不加feature；最小后续仅再次真失败记录rc身份时间与环境受保护浏览器接入。


## 2026-10-06 / E21事前：既有WindowsServerCI受保护真实浏览器

基线5c3292d/aaf07f4正常fetch；不加业务feature、不重试LinuxSUID拒绝。既有windows-2025作业15分钟预算，前轮实际2m39s；新增最多4分钟同job浏览器步骤，不增runner/订阅/超时，官方镜像预装Edge先做实际路径/version/签名检查，缺失或不可信直接BLOCKED。不自动下载浏览器。唯一新增测试依赖官方npm registry固定playwright-core1.63.0及integrity lock，ignore-scripts，和应用Python lock隔离。官方Playwright Chromium默认sandbox false，必须显式chromiumSandbox:true；核实际args无禁用sandbox，并只读Windows renderer restricted/AppContainer及低integrity token证据，不改系统权限/UAC/沙箱策略、不--no-sandbox，失败不降级。

冻结最小流程：现有认证内部Release快照确认→实例→持久Run QUEUED/暂停/取消/返回后重开；另任务实际现Worker成功→独立结果history；desktop1366x900/mobile390x844同WindowsServer真实viewport截图/布局检查、页面runtime错误检查；另一owner/instance历史及control拒绝并不显示他人数据。只用test_only明确临时SQLite合成身份/CSV，显式test初始化不生产API建表，无真实模型调用或新Grant能力。结果与合成截图经既有GitHub job日志回读保存repo evidence，不用额外artifact/export目的地，普通既有devpush并监督精确ServerCI。Win11/手机设备/其它浏览器/正式发布/F1/完整F2/P-A/P-B门不提升，原AT05与首次UNKNOWN保留。方案若真实受保护启动不支持或需要安全/费用变更即停止并列最小需求。


E21执行中检查点：源码59f34817dd65201bd5ba204661d6787b19255fd3普通push，[CI37422476293](https://github.com/T1doo/Sim2Act/actions/runs/37422476293)实际运行，非整体排队；新shell查询成功。Cf0732e/CI37421853614 PG372PASS0FAIL0SKIP170.611s/cleanup成功，但浏览器诊断getBrowserCommandLine因缺enable-automation失败，匿名真实截图与失败JSON保持；未证实renderer-token/认证流程。修只读精确PID查询及新测试整数返回40期望，不加启动flag、不改OS或原AT05。首次8ee候选在浏览器前cancelled/skipped，去掉SDK弱化保护默认参数后才正常尝试。E21证据/checkpoint已保存；当前CI终态与desktop/mobile/auth流程仍待，0LIVE/正式发布关闭/Win11等门不变。


## 2026-10-06 / E21受保护Server真实浏览器终态

精确源码2ead9b615226a2be1bdc59ef745473b7589fd120普通push，[CI37423790107](https://github.com/T1doo/Sim2Act/actions/runs/37423790107)/job112138779536 completed/success3m55s：原PG372PASS0FAIL0SKIP1warning136.70s，新增25真实浏览器/布局/只读sandbox检查PASS，Setup/native最小角色smoke/ruff/mypy21/Report/Cleanup全部成功。既有同windows-2025 job/15min预算、browser步骤最多4min，预装签名Valid Edge153.0.4234.48，官方固定playwright-core1.63.0隔离依赖，无新runner/订阅/浏览器下载。正常chromiumSandbox:true，去掉SDK弱化保护默认参数，实际browser无这些参数；两实际renderer AppContainer/restricted true、integrity0。broker High/admin及EnableLUA1如实存档，不当Win11普通用户；CSP原样/bypassCSP false，不改系统安全/权限/SUID/代理或关闭sandbox。

实际UI/API快照确认→Release→独立实例→QUEUED/pause/cancel→接受新任务后返回并重开→独立one-shot Worker真实sum40/resultv1→cold mobile读回→第二实例独立/跨owner-instance-history-control403均通过。显式test_only临时SQLite合成两owner各一project，非业务库、非原AT02完整初态；PG角色/native另有原工程结果。desktop1366x900/mobile390x844两真实完整PNG已回读验块序/长度/SHA256并人工查看，两列/单列无横向溢出、标题/按钮/状态/结果可读；四预期403 console完整保留，无pageerror/意外console。

首候选browser前cancel/skipped；原诊断接口缺enable-automation失败、CSP字符串等待失败、真实mobile长标题溢出失败及对应PNG/JSON/run/receipt均保留。只修测试查询/函数等待与原整数契约40期待；产品仅一条标题overflow-wrap:anywhere，布局原断言不放宽。最终证据[README](../evidence/F2-protected-server-browser-20261006/README.md)，所有失败保留first/second/third-*；handoff状态另存旧checkpoint，新checkpoint记最小流完成。0LIVE/无Library或恢复包/额外artifact目的地，正式发布false，原work/V5/历史AT02/AT05不改。Win11/物理手机/其他browser/全界面焦点无障碍、撤权stop及更多迟到响应真实浏览器仍NOT_RUN；完整F1/F2/P-A/P-B/AT10/19/20门不提升，E20首次AT05根因UNKNOWN保持。


## 2026-10-06 / E22事前：兼容升级/回退的认证内部入口

基线e3a2843/2ead9b6，正常origin fetch HEAD一致，正确Sim2Act-pb/dev；原V5§10.1、F2-T08/AT16要求数据与版本分离、切换/回退均先兼容检查、运行固定Release、保留历史；不是数据回滚或外部效果撤销。本轮仅将既有prepare_switch/commit_switch接认证API/UI，不新增CSV能力/Grant/表/身份/迁移/正式发布。限既有封闭typed-result schema，同schema/version升级回退和可选metadata兼容服务；通用业务schema/复杂迁移仍未实现。

接口限制owner/project/app/runtime/精确instance及targetRelease fingerprint、revision；prepare只产生既有精确批准，GET再检查完整payload fingerprint/expiry/currentgrant/data/pointer/兼容性，commit只accept精确fingerprint，并事务内再验绑定。UI先手动选target（无默认）/prepare→回读快照及保留数据/当前目标/期限/指纹→未勾选禁用commit；取消/返回仅本页选择，不撤销已接受切换，迟到结果不抢选择。一次性批准consume保持，重复或旧批准409，不增加重放机制；未知网络结果不自动重发，提示读历史。升级/回退增加revision/history，旧data/Run记录保留，新运行用读回的新版本。既有worker在指针变化后保守拒绝旧接受任务边界明确，不在本轮改可靠性政策。

冻结验收：真实API兼容切换/回退及新worker result、数据/历史与Grant/principal不变；不兼容required添加及删除式回退拒绝、无token/跨owner/project/app/instance、fp/tamper/expired/consumed/stale revision/data/grant/target拒绝；并发重复只有一次切换。独立只读review、SQLite/真PG aggregate/最小CRUD role及精确源码现有标准CI/普通push。正常受保护Edge+CSP维持，扩已有真实浏览器流程覆盖升级/回退、精确显示/确认、取消/返回、重复点击、过期批准以及实际pause→resume→QUEUED→worker。仅test_only既有fixture加最小服务生成target/不兼容Release和一次短TTL oracle，无新fixture HTTP接口；短TTL在新switch批准生成同事务内绑定精确expiry/fingerprint，等待实际过期再拒绝，不在收到批准后篡改fp、不改生产300秒或时间/OS/CSP。所有截图/JSON仅合成repo证据，保留失败与未测。0LIVE/noLibrary或恢复包导出/正式deploy false，原work/V5/AT02/AT05及首因UNKNOWN、Win11/物理手机/完整PA/PB/F1F2门不提升。
