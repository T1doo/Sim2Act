# F2 下一阶段路线与界面验收

2026-10-05，起点6b008b2。F1未签收、Win11未测、真实模型预算0，允许安全隔离F2工程；V5阶段门不变。

| 次序 | 工作与退出条件 | 保持的边界 |
| --- | --- | --- |
| 1 本轮可用性收敛 | 同工作区独立只读复核已有权限/来源/参数化/过期与冲突；修具体缺陷；小范围CSS与状态反馈；本地专项及精确ServerCI | 不增加生成能力，不拿DOM充当真实视觉/手机验收 |
| 2 真实渲染与交互验收 | 平台支持且保留保护的浏览器可用后审阅桌面/手机宽度截图及正常、空、加载、失败、成功状态；必要时迭代 | 当前Chromium无可用sandbox，工具目录无可调用平台浏览器，runtime show退出1；不使用--no-sandbox，不修改系统安全策略。缺安全通道时BLOCKED |
| 3 完整两路径工程 | P-A需真实目标规划/生成证据与保持硬条件；P-B需完整已完成任务来源、通用稳定变量识别和原规格全部证据；E14仅固定合成完成任务的显式旧内容退休/新输入与错误输入/冷会话子项 | 当前P-A人工目标+固定MOCK模板；P-B已有PREVIEW来源与E14本地完成任务两种固定求和切片；后者仅显式退休旧内容且保留来源授权门，未通用/正式发布。不能把“新候选”称真实模型生成；零预算不进行LIVE或models查询 |
| 4 发布及正式验收 | 按V5完成不可变Release/实例隔离、权限交集/版本兼容与拒绝、完整AT09—22；F1/Win11和阶段门据实签收 | PREVIEW_ONLY不允许发布；F1历史PARTIAL/AT02不改，无外部业务写入 |

用户新增偏好“前端得好看点”作为正式后续验收条件：统一绿色主色/中性色、清晰字号层级与行距、整齐间距与容器宽度、操作/来源/结果层次、键盘焦点和禁用态；空/加载/错误/成功给明确反馈，不用颜色作为唯一信号；桌面双栏与手机单栏内容/动作顺序一致，表单与长ID/回执不溢出。需真实渲染截图与实际点击审阅后才能写视觉PASS。

本轮仅保留原静态前端架构，做CSS/语义状态的小范围可逆改善。不引入框架/组件库或产品依赖，不大改三个工作区/业务契约；重大视觉重构等待可渲染审阅环境。Node/jsdom只核查DOM和状态/HTTP链路，不核查像素、手机触摸、真实浏览器引擎。

本轮第1步已交付E12：独立只读复核找到4项具体缺陷、主开发修复；精确d3de155的ServerCI37343525441SUCCESS/PG219PASS/0SKIP、11新专项、20DOM通过。配色/字号/间距/焦点/禁用态/手机规则及状态反馈已作小范围实现，**第2步真实渲染/视觉签收仍BLOCKED**；修复尚未独立复验。第3/4步未实施，没有新增真实模型生成、完整P-B或Release。

E13仅修既有来源锚点与已接受POST后的回读恢复。完整P-B下一步必须区分**不可变来源证明**与**运行时旧资料依赖**：当前提取候选每次读取/运行仍重新打开源候选、旧CSV及授权以审计来源；换新CSV和冷页面通过不证明摆脱旧文件，不能记作AT10。后续先明确来源退休后的权限策略（证明可留存、何时必须拒绝/失效、如何防止撤权旁路），再设计可核查完成终态的本地合成task fixture及最小必要接口，验证新输入/错误输入/冷会话及来源退休。未实施此策略或fixture，不扩写抽象，不宣称完整P-B完成。

E13邻接修复交付：源码4d01fb7/CI37346429353SUCCESS/PG224PASS/0SKIP，本地5新专项及33DOM通过，来源请求锚点/direct与preview GET恢复闭合；未增加完整P-B能力，未独立复验，真实视觉仍BLOCKED。

E14事前有界策略：最小不可变来源证明是完成任务/owner/project/source定位及hash、输入输出指纹、固定可信工具和独立oracle版本/完成状态/参数化范围，不能携带旧单元格、原答案或原会话。显式退休仅owner选择保留最小证明且匹配当前源hash/证明版本后，清除旧内容及任务输入输出；不恢复/新增旧源授权。来源grant保持为当前证明复用的保守门：撤权/过期即拒绝，即使已经退休；target新CSV仍逐次检查当前用户/项目runtime/应用runtime交集。策略不明或证明不一致默认拒绝。此安全工程切片不提出来源撤权后仍可用的放宽策略；若未来需要，必须另作明确产品决定。仅合成完成任务固定精确求和fixture与旧文件独立运行；既有PREVIEW、F1历史/V5不改，完整AT10签收待原规格全部证据。

E14本地实现及35专项/1PG待CI、完整254PASS/6SKIP、原33+新14 DOM/HTTP通过，实际合成LOCAL_DECLARATIVE_TASK成功后可显式清旧内容、冷客户端运行新输入。source当前授权仍必要，撤权/过期拒绝；不是权限独立。三表显式迁移，既有PREVIEW不适用退休豁免，共享F1/目标卡/应用来源拒绝退休。详见[接口与策略](TaskRetirement.md)。精确Server待核实；真实视觉、原规格完整AT10、通用生成/Release及F1/Win11仍未验收。

E14精确终态：c776fa2/CI37349609291SUCCESS/PG260PASS/0SKIP，36新专项含三表最小业务CRUD角色路径已通过；合成固定任务证明/显式退休/旧内容独立新输入子项交付。source撤权后继续复用未实现、默认拒绝，通用P-B与原规格全部AT10证据/Release/真实视觉及F1/Win11仍后续独立门。

2026-10-06 E15范围：恢复后真实PG两种顺序核查，共享project→card/app→grant锁和候选持久化前重验。基线grant锁已挡住观察到的direct交错，未复现成功插入失效app；project锁缺失按真实结果补强。9真PG专项已通过，完整聚合/精确CI待核实。仅映射[冻结AT10合成子项](AT10Subitems.md)，不改V5/不扩展CSV/不签收完整P-B，真实浏览器/Win11/F1/Release和预算0边界保持。

E15终态：53dc124/CI37411714116SUCCESS/PG269PASS/0SKIP，9真PG专项及完整角色CRUD通过。完成本轮退休/消费者串行补强及冻结AT10合成子项映射，到此切片结束；未独立执行/视觉，通用P-B/原规格全部证据/Win11/F1/Release仍后续独立门，模型0。

E16事前范围为V5 F2-T08的内部合成Release/Instance/AppRun生命周期，源码service及测试，不启用正式发布入口或实际部署。不变Release与精确批准、复用既有应用身份/Grant、独立实例类型化result数据/版本、真实网关新AppRun、兼容升级/回退及历史保留；不新增CSV功能或任意业务写入。同工作区独立审查及精确aggregate/CI后回报，原F1/Win11/真实P-A/更广P-B/protected browser阶段门、0模型不变。E15旧grant锁已串行化基线，准确记锁序加固。

E16本地内部service：[范围与接口](InternalLifecycle.md)。不可变Release审批/实例独立result数据/真实新AppRun与版本/兼容升级回退历史已实现；复用现runtime及grant。独立复验两schema问题关闭，原AT05恢复；32新内部SQLite检查PASS/1PG专用SKIP，完整SQLite286PASS/16SKIP。真PG/精确ServerCI待完成，不启用正式发布入口/部署或签收整个F2。后续仍须明确通用业务数据/动作与迁移政策、正式发布批准UI/部署链，原F1/Win11/真实P-A/P-B/AT10/protected-browser门保持，不追加CSV便利项。

E16终态：e029922/[CI37413258268](https://github.com/T1doo/Sim2Act/actions/runs/37413258268)SUCCESS/PG302PASS/0SKIP，新内部33项及原AT05完整覆盖；LinuxPG301PASS/1SKIP、SQLite286PASS/16SKIP，独立32PASS/1PGSKIP并关闭schema问题。[证据](../evidence/F2-internal-lifecycle-20261006/README.md)。本轮内部路径已交付，正式发布入口/真实部署未启用，原阶段门保留。后续按V5通用生命周期/数据与正式批准链逐阶段计划，不能将本切片扩大称整个P-B或发布完成。

E17路线：在已验E16固定内部Release/Instance上接入既有持久worker；先冻结queue/reopen、lease/fencing、pause/cancel前置、进程重启恢复、当前grant、结果版本恰好追加一次和FAILED保留。短事务输入授权与原子结果提交，中间计算不占DB长锁；任何不明效果保守等待并保留取消意图。正式发布入口关闭，不追加CSV/Grant。AT17仍OPEN：只读sum不能证明预览写隔离，需要后续受控写fixture，不能借内部result账本签收该条。

E17源码8b14cee7ca8b55bef5f5e2f3dfd3a89482f837e2已普通push；[持久内部AppRun接口与边界](PersistentAppRuns.md)、[证据](../evidence/F2-persistent-apprun-20261006/README.md)。首轮完整PG338PASS/1WindowsSKIP及4真实子进程、追加最低角色enqueue1PASS；最终38项aggregate/精确CI37415214667进行中。独立最终33PASS/5PGSKIP，未知门/来源metadata/失败绑定问题关闭。篡改到失去可信关联的原AppRun保留不可读QUEUED，不猜修；正式发布/部署/通用业务数据、AT17受控写隔离、完整P-A/P-B/AT10/F1/Win11/protected-browser仍后续原门，0模型。

E17终态：8b14cee/[CI37415214667](https://github.com/T1doo/Sim2Act/actions/runs/37415214667)SUCCESS/PG340PASS/0SKIP，38新项含4真实worker子进程及最低角色enqueue/控制/worker CRUD；LinuxPG339PASS/1WindowsSKIP、SQLite319PASS/21PG平台SKIP，独立33PASS/5PGSKIP，source/test hash匹配。现固定内部Release/Instance可持久enqueue、重开、恢复、控制并原子产生新结果版本；该切片交付结束。[证据](../evidence/F2-persistent-apprun-20261006/README.md)。正式发布/部署、通用业务写/迁移、AT17受控preview写隔离、完整P-A/P-B/AT10/F1/Win11/protected-browser仍原规格后续，0LIVE；不堆CSV便利项、不把未知外部副作用合成注入称实际连接器恢复。
