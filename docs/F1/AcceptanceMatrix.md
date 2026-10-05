# F1 权威当前验收状态

2026-10-05；当前工程源码c776fa24dac957485a65337ed3d4b428848b584c（合成完成任务最小证明与显式旧来源退休切片）。本页取代逐轮记录中的当前时态结论；历史见[收敛前快照](history/AcceptanceMatrix-before-convergence-20261005.md)。V5源设计和冻结用例未修改。

F1仍IN_PROGRESS，未签收；用户已授权F1未签收时并行F2隔离工程，CSV固定模板PREVIEW_ONLY已实现，F2正式准入与发布仍BLOCKED。原身份正常push已验证，正式执行器审批允许项目网络操作，不改变保存环境策略。旧E10只读审核曾核对源码/精确run且无新阻塞；E12对6b008b2的独立只读复核发现4项具体缺陷，主开发已修并回归，但未独立复验修复，不自动完成阶段签收。

历史E10：人工目标卡/授权CSV/可信csv.sum→声明式校验/冻结条件候选→新预览/历史/返回/刷新已实现，PG174PASS/0SKIP（含临时应用角色候选整条API路径），Linux170PASS/4平台SKIP、Chromium14候选+3刷新检查PASS。P-A仅固定模板工程子集，P-B/Release未实现，真实请求0。E9目标卡迟到响应与保存完成不再跨项目恢复或覆盖New草稿，真实LinuxChromium11交错回归PASS、精确ServerCI37325580965成功。E8通用目标卡/人工验收草案已实现，14专项及两个并发writer版本冲突，LinuxChromium7检查点、SQLite147PASS/3平台专项SKIP、ServerPG150PASS/0FAIL/0SKIP；E7的CSV输入提示保留。仅F2共同前置工程，不声称模型P-A/P-B生成、完整F2-T01或Win11/多引擎通过。

历史E11：可信本地合成PREVIEW成功回执经完整模板/实际hash/工具回读/独立整数sum oracle核查，提取一层稳定逻辑并显式绑定新CSV；原目标NOT_RUN，来源PREVIEW不是F1 Run。33新工程负例及1PG业务角色全链专项，精确ServerCI37340717581成功，PG208PASS/0FAIL/0SKIP/1旧警告68.30秒；Linux203PASS/5平台SKIP，Node/jsdom12交互PASS。真实Chromium无可用沙箱，0检查/BLOCKED，不以DOM或旧E10截图替代；E11未经独立审核/复跑。完整P-B/AT10/源资料解耦/通用归纳/Release仍未完成，真实请求0。

历史E12：修目标来源声明可移除/额外撤权绕过、固定输出接线篡改仍成功、direct创建迟到抢选择、CSV Decimal溢出500不存失败；preview同app重选保护与加载/错误/成功反馈、CSS小范围配色/字体/间距/表单/焦点/禁用/手机规则收敛。11新专项、精确ServerCI37343525441SUCCESS/PG219PASS/0FAIL/0SKIP/1旧警告70.78秒，Linux214PASS/5平台SKIP/2警告、20DOM交互PASS。独立只读报告覆盖旧基线与4缺陷，主开发修复回归不是独立复验。真实浏览器/截图/手机视觉仍0/BLOCKED，不关闭sandbox；完整P-B/AT10/Release/F1/Win11未签收、模型0不变。

历史E13：协调有效旧版本降版/重算候选hash不能替换已接受请求锚点，绑定card/version/resource/capability，合法旧版本保持冻结。direct/preview已接受后读取失败显示已创建/已执行，GET-only恢复及项目/草案/目标卡迟到隔离。5新专项，精确ServerCI37346429353SUCCESS/PG224PASS/0SKIP/1警告63.13秒，Linux219PASS/5SKIP/1警告、33DOM非浏览器，未独立复验。来源每次重开旧文件仍是运行依赖；来源退休权限策略与完成task fixture待实施，冷页面不替代AT10。真实浏览器0/BLOCKED、完整P-B/Release/F1/Win11及模型0边界不变。

最新E14：独立LOCAL_DECLARATIVE_TASK实际可信工具+精确oracle才SUCCEEDED、失败真实FAILED；最小证明不含旧单元格/答案/会话，显式owner匹配证明/hash及保留最小证明consent后清旧content和任务input/output。旧source GET/工具拒绝，新Store冷会话新CSV40/换quantity5及坏输入FAILED；source现授权仍必要，撤权/过期拒绝，不恢复grant；target用户/项目/app交集保持。既有F1/目标卡/应用共享源拒绝退休，PREVIEW原路径保持。36新专项，精确ServerCI37349609291SUCCESS/PG260PASS/0FAIL/0SKIP/1警告69.05秒；Linux254PASS/6SKIP/3警告，原33+新14DOM非浏览器、未独立复跑。只完成固定合成任务/退休旧内容子项，不签收完整AT10/P-B/F1/Win11/Release，真实视觉0/BLOCKED/模型0。

## 当前证据索引

- E1/E2：[旧Server111项](../evidence/WindowsCI-lock-20261005/results.json)和[旧Linux/身份回归](../evidence/F1-model-identity-TestReport.md)，均为历史源码。
- E3：[真实LIVE归档](../evidence/LIVE-20261005/README.md)，dd195681，两次真实反馈链、PARTIAL/LIVE、唯一resource.read VERIFIED，预算0。最小未决项见[AT-02核对](AT02Review.md)。
- E4：[历史浏览器](../evidence/F2-csv-preview-20261005/README.md)，6检查点；不是最新Win11或多浏览器复测。
- E5：[契约](Contracts.md)、七Schema及冻结AT资产。固定CSV候选可编译执行单节点可信预览；完整P-A/P-B、通用DAG及Release仍未实现。
- E6：[ServerCI37315778872](https://github.com/T1doo/Sim2Act/actions/runs/37315778872)，0555593，PG126PASS/0FAIL/0SKIP；原生六脚本/运行角色DDL拒绝/真实子进程白名单/PATHEXT专项/重启/完整依赖锁/清理通过。[精确结果及源码指纹](../evidence/recovery-20261005/README.md)。Linux123PASS/3平台专项SKIP。开发方读取真实日志，审核者核对run/job成功，均不称独立复跑。

- E7：[CSV输入提示证据](../evidence/F2-csv-guidance-20261005/README.md)，07969cd/[CI37318927260](https://github.com/T1doo/Sim2Act/actions/runs/37318927260)SUCCESS，PG136PASS/0FAIL/0SKIP、原生/静态/锁/清理通过；开发方实际读取日志，非独立复跑。

- E8：[通用目标卡证据](../evidence/F2-goal-cards-20261005/README.md)，6bf5e05/[CI37322479923](https://github.com/T1doo/Sim2Act/actions/runs/37322479923)SUCCESS、PG150PASS/0FAIL/0SKIP，原生/迁移/锁/静态/清理通过。目标卡工程用隔离test-owner schema；非独立复跑或Win11 UI实测。

- E9：[目标卡竞态修复证据](../evidence/F2-goal-card-race-20261005/README.md)，22f352b/[CI37325580965](https://github.com/T1doo/Sim2Act/actions/runs/37325580965)SUCCESS，PG150PASS/0FAIL/0SKIP，LinuxChromium11交错检查PASS，SQLite147PASS/3平台SKIP。合成数据复现并修复0382b91审查问题；该源码修复仅含竞态闭合，后续固定MOCK候选切片见E10。

- E10：[目标卡到MOCK候选及预览闭环](../evidence/F2-goal-candidate-20261005/README.md)，e6b3e2c/[CI37329527816](https://github.com/T1doo/Sim2Act/actions/runs/37329527816)SUCCESS，PG174PASS/0FAIL/0SKIP（24新项含应用角色API路径），原生/静态/显式迁移/锁/清理通过；真实LinuxChromium14候选交错+3刷新/正常UI路径、E9原11竞态保持PASS。不是Server浏览器/Win11/独立复跑或完整P-A/P-B验收。

- E11：[可信PREVIEW来源提取证据](../evidence/F2-preview-extraction-20261005/README.md)，3d87f5e/[CI37340717581](https://github.com/T1doo/Sim2Act/actions/runs/37340717581)SUCCESS，PG208PASS/0FAIL/0SKIP；显式迁移/应用角色CRUD/原生/静态/锁/清理通过。真实浏览器BLOCKED，12 DOM交互非浏览器。仅受限P-B工程子集，不签收完整P-B或F1。

- E12：[独立缺陷与可用性收敛](../evidence/F2-usability-20261005/README.md)，d3de155/[CI37343525441](https://github.com/T1doo/Sim2Act/actions/runs/37343525441)SUCCESS，PG219PASS/0SKIP；原生/静态/业务CRUD/清理通过，DOM20非浏览器。下一阶段视觉及完整两路径门见[F2路线](../F2/NextSteps.md)。

- E13：[来源请求锚定与回读恢复](../evidence/F2-origin-recovery-20261005/README.md)，4d01fb7/[CI37346429353](https://github.com/T1doo/Sim2Act/actions/runs/37346429353)SUCCESS，PG224PASS/0SKIP；33DOM非浏览器，源文件依赖未解除，完整P-B/AT10未完成。

- E14：[合成完成任务与来源退休](../evidence/F2-task-retirement-20261005/README.md)，c776fa2/[CI37349609291](https://github.com/T1doo/Sim2Act/actions/runs/37349609291)SUCCESS，PG260PASS/0SKIP；36新检查及应用角色CRUD路径，原33+新14DOM非浏览器。固定合成子项可冷会话运行独立新内容，来源授权仍必要；完整P-B/AT10未完成。

| F1任务 | 已实现/证据 | 当前缺口与边界 |
| --- | --- | --- |
| T01 契约 | E5/E6：严格结构、输入输出/可信引用/冻结/预算预检；CSV固定模板单节点预览 | 完整目标生成/通用编译属F2，消费版本及阶段签收待验收，不新增F1要求 |
| T02 原生进程与依赖 | E6：Server2025/PS7.6.6/Python3.12.10/PG17.11，首次Setup/六脚本/依赖锁/重启 | 目标Win11普通用户/真实安装组合未测；Server不替代Win11 |
| T03 工作区 | 项目/资源/任务/回执及CSV草案输入/运行/历史已有 | 最新Win11与多浏览器复测待执行；不称完整P-A/P-B已验收 |
| T04 身份与权限 | E6 owner环境隔离及应用角色无DDL；CSV preview应用Principal/Grant与user-project-app权限交集已实现、撤权回读拒绝 | Release/实例身份及授权交集尚未实现，归F2；只读审核无新阻塞不替代签收 |
| T05 持久任务可靠性 | 队列/租约/fencing/心跳/核对/暂停取消、真实API-worker与重启回读 | 保留函数/事务故障注入粒度；preview同步事务不等于AppRun异步/崩溃链 |
| T06 真实书生与账本 | E3：两轮真实选工具/反馈后回答、身份/usage/持久回读 | 核心操作/oracle独立只读核验通过；历史脚本仅一owner/一项目，完整初态缺口无法补证；额外最多2真实请求预算待批，当前0；权重unknown |
| T07 冻结资产与回归 | 28用例资产不变；E6工程126通过 | 126工程测试不代表28完整AT通过；早期AT仍需逐项签收 |
| T08 环境与待确认 | 双锁、Server实际组合、loopback、真实预算已耗尽 | Win11主平台验收；授权真实材料/独立评价归F3，赛方条件归C0，允许提前核实 |

## 冻结AT状态

AT-01 Win11仍NOT_RUN；AT-02真实操作链已有E3且独立核验一致，历史完整两主体/两项目初态未满足、不能补证，额外预算待批准，PARTIAL不改SUCCEEDED。AT-03/04/05/06/07/08有工程子项及E6回归，独立阶段验收仍未签收；AT-07保留允许故障注入，不强加真实429压测。AT-09—22的正式P-A/P-B/发布/可靠性完整验收未完成，已完成固定CSV预览工程子集；23—27归F3、28归C0。原§4.2正式阶段前置保持；用户授权的并行工程不等于放行F2发布链。
