# F2 下一阶段路线与界面验收

2026-10-05，起点6b008b2。F1未签收、Win11未测、真实模型预算0，允许安全隔离F2工程；V5阶段门不变。

| 次序 | 工作与退出条件 | 保持的边界 |
| --- | --- | --- |
| 1 本轮可用性收敛 | 同工作区独立只读复核已有权限/来源/参数化/过期与冲突；修具体缺陷；小范围CSS与状态反馈；本地专项及精确ServerCI | 不增加生成能力，不拿DOM充当真实视觉/手机验收 |
| 2 真实渲染与交互验收 | 平台支持且保留保护的浏览器可用后审阅桌面/手机宽度截图及正常、空、加载、失败、成功状态；必要时迭代 | 当前Linux执行器Chromium无可用sandbox；E21既有WindowsServer正常保护Edge已验内部最小流程，见最新E21证据。Win11/物理手机/完整界面仍未测；不关闭sandbox或改系统策略 |
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

E18只补AT17合成受控写隔离与阶段门审查：实际预览SQL事务内test-only受控写、成功独立读回/失败回滚/重复与namespace负例；原始数据/权限逐字节不变。测试适配器不注册到生产工具，不启用发布或真实业务写，0LIVE。完成后列原V5证据与最小未完成项及真正需要的决定/接入，停止相邻功能扩张；当前production preview仍读/计算，FAULT_INJECTION不能冒充生产写实现。

E18已实现受控preview record/receipt实际写入与rollback/retry/namespace负例，独立13PASS。见[阶段门审查与实际下一接入](StageGateReview.md)。当前仅合成隔离子项，正式AT17仍OPEN。下一步为Win11/保护浏览器接入、F1完整fixture/签收、真实任务族/预算或受限生产writer/发布政策及故障服务的明确选择；不在本轮继续堆相邻功能。全PG/精确CI待核实。

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

## E22已交付后的边界（2026-10-06）

此前E22“待接入”现在完成最小内部compatible switch认证API/UI：[精确c16cbae/CI37428871976 SUCCESS](https://github.com/T1doo/Sim2Act/actions/runs/37428871976)，PG383PASS0SKIP+38真实保护browserPASS，两viewport截图/升级后worker v2/rollback保留历史已验。取消迟到prepare/重复/过期/不兼容和实际resume覆盖；late commit cancel为独立NodeVM，短TTL仅显式合成oracle。初两个测试CI失败全保留，产品hash不变。无需继续堆CSV邻接能力或重复已有绿色工程。

后续仍按原V5未闭合项决定：Win11普通用户及完整AT02 fixture/F1签收输入；新任务族与独立成果oracle/P-A/P-B；F2局部修改/通用受限业务数据与schema迁移及正式发布政策；受控外部在途效果AT19/20。当前0LIVE、最多额外两次尚待明确批准，不models探测/自动真实重试；本轮不自动开通以上范围。Linux SUID安全路径仍BLOCKED，原AT05首因UNKNOWN。完整F2/AT16及正式发布未提升，手机viewport不代物理设备/完整无障碍。[E22证据](../evidence/F2-internal-switch-entry-20261006/README.md)。

2026-10-06本地bounded_agent主线已接原AppManifest/AppRun，源码3e27ad9，R0现app授权域/真实read反馈/可信literal checker/接受来源锚点/新MD冷Store结果闭合，详见BoundedAgentOfflinePlan与evidence/bounded-agent-offline-20261006。仍需回到原V5自主候选生成、自由规范语义验收与实际授权材料/接口；不能用literal fixture PASS扩为语义理解或完整P-B。当前0LIVE、不新增Grant；无现app MD授权则拒绝，不用项目runtime兜底。agent跨进程Replay自动恢复和新UI/浏览器尚未实现。本轮只本地commit，父检查前不push/CI，不再追加转换器家族。
