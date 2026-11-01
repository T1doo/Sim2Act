# 同版本Windows完整装配：构建、失败与修复

最初装配阶段是用户再次明确授权的普通免费Windows构建，不是重跑旧900秒批次。总运行预算不超过480秒。使用公共仓库标准Windows Server2025 runner，最初只做普通编译、原生模块加载、合成SQLite协议／后台检查，未运行桌面EXE；后续原生窗口验收见文末。始终不启独立浏览器或PG／真实模型，不改系统安全配置、不用用户电脑、不改main／Release。

## 第一次真实Windows运行

源码 `57ecb98fafbe1d3b7369d2a8c56a3dbb59cb04da`；[run41322277031](https://github.com/T1doo/Sim2Act/actions/runs/41322277031)，job124894829879，15:38:52–15:40:47 UTC，共115秒。

四枚CPython3.12.10 x64扩展和wheel真实编译成功，非editable安装成功；逐模块PE32+／AMD64、PyInit导出、python312.dll导入、SOURCE_SHA与完整源码组合匹配；`_qualified()`、Source `available/current`和精确依赖版本检查通过。原生记录及二进制摘要在`attempt-1/report.json`，不是Linux交叉编译结论。

随后协议测试54通过、6失败、0跳过，所以停止，没有带失败继续装配；C#新Windows编译、最终私有runtime、全包与桌面均未在此运行完成。制品原件51425字节、SHA256 `80d7f92f580600d71d01f19cb76d364179ce4a1e3cb3b1bd5fa7dc536b39c868`，artifact13089955289。11份原始诊断已完整取回和核摘要，见`attempt-1/`。

## 六项失败的具体判定

1. `test_business_commit_success_ack_failure_is_not_a_rollback`：旧故障注入在业务`main.commit()`之后，重命名还被控制writer打开的SQLite文件。Windows正确返回WinError32，delegate未正常返回，生产代码正确分类`CommitOutcomeUnknown`；旧测试却期待`CommittedAckPending`。这不是产品丢失提交或应该绕开Windows锁。修正为在实际主库提交返回后，只对实际控制连接的后续ACK UPDATE施加SQLite authorizer拒绝；仍必须`CommittedAckPending`，再核持久收据、ACK恢复及delegate仅调用一次。另保留提交后delegate抛错的独立参数，必须`CommitOutcomeUnknown`，同样核不重放。
2. 五个`test_runtime_rejects_store_method_shadow_before_foreign_dispatch[tx/guard/owns_connection/frozen_contract/event]`：Windows锁定pytest9.0.2的`setattr` undo留下原bound method的实例属性。原C协议`lease_store_fields_current`明确禁止任何固定actor方法的实例影子，因此恢复后被拒是正确行为。官方pytest9.0.2 wheel SHA已核并实际复现`namespace_after_setattr_undo=['guard']`，见`pytest-902-undo-reproduction.json`；本地pytest9.2.0的undo则清理该key。修正为对实例字典setitem并精确撤销，外来方法必须拒，原bound method的实例影子也继续明确拒绝，foreign调用数仍为0；未改生产门。

修复后当前本地两文件43项通过；在实际锁定pytest9.0.2下，相关7个参数化反例全部通过，均0跳过，XML及原日志保留。这仍不是新版Windows通过，必须再核新源码。

## 下一验证与包身份

第一次已用115秒，剩365秒。完成必要独审后只对修复源码验证一次：job硬上限5分钟，编译步骤4分钟，内部子进程剩余门210秒；即使该job用满300秒，累计415秒仍低于480秒。不是原失败源码自动重试，不增加付费／安全权限。最终状态须按该次实际结果记录，不能预置成功。

控制器在成功wheel生成后立即保全wheel、候选manifest与原build.log，避免后续测试失败丢失已编译字节。最终装配只复用旧固定镜像中的1554个已核运行库／依赖文件，完整剔除旧Sim2Act和旧dist-info，再加入本次同SHA wheel和四pyd、同SHA C# EXE。旧依赖ZIP、内部manifest、全部文件和21个依赖的版本／provenance都必须匹配，不将重新压缩文件冒充原wheel。

最终私有Python必须在`-I -B`下再次实际核四pyd路径／二进制摘要／SOURCE_SHA／资格／ABI、全部22份发行元数据（21依赖+本应用），然后执行两次CSV=30/v1、15/v2、原键去重、EOF clean退出和首次同origin重开。普通PE导入表和未打包的系统DLL需求单列，不把它当delay-load/API-set或干净机器完整验收。正常桌面入口仍是原WinForms/WebView2 EXE，浏览器只是显式开发预览；不新增失败壳或换后端。

本地真实后台driver已完成上述CSV／同键／同origin／双EOF操作，相关本地70项回归通过；它只是触发前检查，绝不替代Windows最终全包装配。当前应用src、C和C#业务代码相较7bf基线未变，保持已修READY、权威续租、提交屏障与取消；本轮没有重新打Linux包。

## 传输与剩余边界

通用GitHub fetch拒绝job日志URL（400，未支持的参数端点）后不重试该调用；云端直接HTTP制品下载在代理CONNECT处403，未取得字节，该传输保持停止。随后发现并使用现有GitHub连接器的专用日志／artifact工具，正常已有应用授权成功；通过其返回的授权文件引用取回原件并核SHA，没有改代理、认证或权限。未发布临时签名URL到仓库。未来读回应优先这些专用工具，不再尝试已拒HTTP路线。

Windows本机正式传输helper是否恢复由唯一协调任务另行核实；文件未跨机共享，也未把本机连接当输入可用。截至首次装配时只能准备完整源码／包／manifest／摘要；后续云端窗口验收见文末。不能绕旧传输拒绝或私自使用用户电脑。

长写锁仍是已知未解风险：`advance_model`的W5后仍在写事务内调用`_model_settlement_read`重建post图并执行完整权限／回执／绑定复核。本轮只核源码位置，没有新的大型Cold性能计时，也没有删检查、扩大30秒租约／300秒截止或缓存授权PASS。正式PG、任意自然目标、Windows真实模型仍未由本轮证明；截至该段记录时的桌面未验状态，后续以文末原生窗口限定证据补充。

## 第二次真实Windows终态与下一窗口检查

源码 `042ab21c4fa9c7e5ba70c4e2877fb7060d962422`，[run41325692393](https://github.com/T1doo/Sim2Act/actions/runs/41325692393)，job124905034942，16:19:01–16:21:32 UTC，151秒，SUCCESS。上述61项协议测试0失败0跳过；四扩展、私有runtime、完整同源包、两次CSV30/v1和15/v2、同键不重放、EOF clean退出及首次新进程同origin/principal重开均实际完成。原始日志、XML、完整清单及本地逐文件复核在`attempt-2/`。应用src/C/C#业务字节与7bf6fd基线一致。

完整包 `deliverables/windows-full-20261101/Sim2Act-win64-042ab21c4fa9.zip` 19,745,959字节，SHA256 `cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027`。1779个清单成员及whole-zip、wheel/source/native一致性已独立复核，未含DB、私有env/私钥或托管token模式。此时原EXE尚未执行，状态严格为ASSEMBLY_AND_BACKEND_ONLY，不是整体交付。

本批累计115+151=266秒，余214秒。按用户新增独立窗口与截图要求，下一次仅对这份精确原包做普通窗口/登录/关闭重开与自身像素检查，job硬上限180秒；即使用满累计446秒也小于480秒。仅用已有交互桌面/稳定WebView2；缺失或拒绝则停止，不安装Runtime、修改sandbox/ACL/会话/显示设置、不启Edge浏览器/CDP，也不使用用户电脑。新的测试提交不改变已冻结包身份。结果须追加真实终态，不预置通过。

### 原生窗口第一次准备失败与修正

测试提交 `f45e6d99ca67a67e0a6d36b04f3063498296e32a`，[run41328741556](https://github.com/T1doo/Sim2Act/actions/runs/41328741556)，job124914138434，16:54:59–16:55:18 UTC，19秒。实际session2、UserInteractive=true，屏幕1024×768；脚本1060最小宽门过严，于启动EXE之前拒绝，starts=[]。这不是窗口或业务失败，Runtime尚未核查；原报告/完整job日志/638字节artifact已保存在`window-attempt-1/`。

产品原最小窗口为1024×680，仅将测试屏宽门1060改1024，不改显示设置或产品。整窗GetWindowRect仍必须完全在VirtualScreen内，UIA登录、真实像素、同源重开和完整退出要求均保留，实际溢出仍拒。独审无mustfix。累计266+19=285秒，余195；修正源仅必要单次验证，job180秒硬上限，累计最多465<480。不得将本轮准备失败改写为窗口通过，不安装Runtime/修改sandbox/ACL或使用用户电脑。

### 同一原包原生窗口实际通过

测试提交 `b5bfb4635aab24f2d894c487f96d8023d97c30c6`，[run41328886324](https://github.com/T1doo/Sim2Act/actions/runs/41328886324)，job124914577921，16:56:42–16:57:22 UTC，40秒，SUCCESS；累计115+151+19+40=325秒，480秒批次余155秒，没有继续触发运行。应用始终为原042ab21c完整包，未改业务或窗口源码。现有Windows Server2025 session2、1024×768桌面与WebView2 155.0.4283.62；没有安装Runtime、改显示/sandbox/ACL或使用用户电脑。

原EXE实际两次启动PID9540/8792，窗口标题Sim2Act工作台，UIA通过本机访问令牌/连接/切换身份及研究工作台。真实前台整窗像素两张1024×690；地址、principal、data_dir两次相同，worker不同；两次后台STOPPED clean/data_preserved/worker_stopped以及DESKTOP_EXIT receipt_verified/ready_seen/child_returncode=0/exitcode=0、无残锁均确认。只验窗口登录与正常关闭重开，未在该窗口操作任务保存/导出。独立后台的CSV30/v1、15/v2证据来自同一原包上一151秒运行，不能混为窗口点击业务通过。

两张图已实际看过：固定左导航、右侧工作区和局部滚动、暖橙按钮可见，合成空白工程没有任务/结果。截图发生在首次2.5秒健康轮询前，左侧仍为初始“正在检查后台”；成果区为空态图标，不代表模型/任务执行中或READY造假。原生READY/退出与页面health状态是不同证据。按用户最新要求，不借此开展新视觉改版，保留像素原件，普通字号与宽屏体验仍待后续审查。

截图和原始artifact只保存在本地及既有CI授权artifact中，不新增公开图片分享或重试旧Library401。artifact13092342632，154359字节，SHA256 `82e63dbf3a29226fd2691ea8a98984a45aef05aed7eab2c80c88a28386063317`，正式工具file引用 `file_00000000fe14820ca529c7f5917c2193`；包含两张PNG、report.json、desktop.log。仓库仅保全文本协议证据及每个图片摘要，取图可由原授权artifact获取，不假设跨机器文件共享。

当前范围是完整Windows装配、Windows Server2025普通后台CSV保存/重开及原生窗口登录/关闭/重开均通过；目标Windows11、窗口内完整用户点击保存导出、真实模型/正式PG、大型Cold长锁体验没有由本轮证明。0次真实模型。旧长写锁风险不因此消失。现已具备可追溯的限制候选输入，尚未创建正式Release或改main。

### 下一有界窗口基础写入验证

上一成功运行后累计325秒、余155秒。继续用户要求的功能收尾，新增仅一次120秒硬上限的`native-material-once`检查（最多累计445/480），不重复相同窗口登录测试冒充功能。包仍为原042、cc177eeb摘要不变；只在原EXE通过UIA创建合成项目、选择CSV类型、填写固定文本并点击原保存授权按钮，GET仅核回执和持久内容，不能用POST直接造数据替代UI。正常关闭重开后核同一项目/材料ID和完整内容。材料均新建在本次独立临时合成工作区，不访问用户电脑或私人数据。仍不执行模型、求和任务或导出，不新增安全/显示/浏览器配置。内部阶段门75秒加正常退出清理，job硬限120秒；若UIA卡住到硬限，不能宣称清理或完整功能通过。实际终态须另行追加。

### 窗口材料第一次失败：UIA读取模式兼容性

`8a75f4630f61d3a863c36d9994e5e6d9036b45d6`，[run41329802210](https://github.com/T1doo/Sim2Act/actions/runs/41329802210)，job124917311950，17:07:12–17:07:49 UTC，37秒。原EXE真实READY、登录、项目创建动作及项目列表GET执行到达，但在核项目选择时，WebView2的HTML select不支持SelectionPattern，脚本调用GetCurrentPattern抛Unsupported Pattern。未进入材料保存，未重开，不能报UI材料通过。失败截图与日志保全在本地/原授权artifact13092468927，仓库仅文本和hash，正常关闭自有窗口确认，未强杀。

修正同一控件的只读取值适配：TryGetCurrentPattern明确检测Selection/Value/LegacyIAccessible可用模式，仍必须精确等于期望项目名／csv；都不支持则拒绝，不能凭HTTP结果假造UI选择或绕页面提交。新增成功项目ID阶段证据。应用/原包不变。已用325+37=362秒，余118秒，仅修复源再做一次job60秒硬上限，累计最多422<480；内部阶段门40秒、异常正常退出最多5秒，超过job硬限则不得宣称清理完成。本次后不再自动追加原生CI。

### 窗口材料第二次终态与收口

`8717578c48f660f4cda15680d7bf70edeb9b9a9f`，[run41330123010](https://github.com/T1doo/Sim2Act/actions/runs/41330123010)，job124918253400，17:10:42–17:11:27 UTC，45秒。原EXE READY、登录、UI创建项目及精确project selector读取已通过，项目ID写入真实阶段报告；随后已切到“资源”，在Open-Summary枚举无名称按钮时对null Name调用StartsWith，脚本84行失败。尚未填写/保存材料，未执行材料重开验证；不能将“项目创建可用”扩成“窗口材料保存已通过”。当前Selected-Value兼容入口在项目选择段已通过（原报告没有记录具体返回的pattern），后续CSV选择尚未验。异常路径正常CloseMainWindow、进程退出确认；原desktop.log还保留完整STOPPED/DESKTOP_EXIT。

本次只修脚本枚举：匿名/空元素不可能匹配目标summary，先检查Name确为string再StartsWith；精确选中、唯一提交、完整退出和内容核查门不变。此修复未再原生运行，不能称Windows实测通过。按本轮停止计划不再追加CI。实际累计115+151+19+40+37+45=407秒，480秒批次余73秒；旧900秒批次余77秒继续单列，不混为新预算。所有失败、空状态和原始协议保留。

原包042ab21c及其完整装配/独立后台CSV两结果保存、首次同源重开/原生窗口登录关闭重开通过仍成立；新的窗口材料UI验收属于未完成的自动化能力，不是已证明产品保存失败。需要现有Windows普通UI条件或后续明确有界验证完成材料/运行/导出点击范围；不因此扩大安全权限或伪造签收。Windows11正式传输/目标机验收、PG、live、本轮大型Cold未验维持原边界。未创建Release，交接准确包与测试范围供最终发布评估。
