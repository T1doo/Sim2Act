# E21：既有 WindowsServerCI 的正常沙箱浏览器验证

当前测试源码 `59f34817dd65201bd5ba204661d6787b19255fd3` 已普通 push，精确 [CI37422476293](https://github.com/T1doo/Sim2Act/actions/runs/37422476293) 进行中，未提前签收。原工程回归后同一个 windows-2025 job 增加最多4分钟浏览器步骤，job仍15分钟；无额外runner/浏览器下载/发布/真实模型。唯一官方npm registry依赖 playwright-core1.63.0 integrity-lock/ignore-scripts，与Python依赖锁隔离。

先验证预装Edge签名与版本，正常 `channel:msedge, chromiumSandbox:true` 启动；在匿名合成首页先检查实际argv及CDP精确browser/renderer PID，用Windows只读TOKEN_QUERY核低integrity/restricted/AppContainer。任何缺失或失败直接FAIL/BLOCKED，不改UAC/权限/系统策略/安全沙箱参数、不unsafe fallback；不重试LinuxSUID路径。

再真实浏览器点击已存在认证UI与API：冻结只读Release精确确认、实例、QUEUED/pause/cancel、返回/reopen持久历史、独立Worker真实可信result40与v1、cold context移动viewport结果、另一实例/owner读取与control403且不呈现foreign内容；真实1366x900与390x844viewport截图/无横向溢出/按钮布局及脚本错误。fixture显式初始化test_only临时SQLite，两合成owner/CSV；现生产API不建表，无业务库/模型。ServerUI路径SQLite证据不冒充新增PG最小角色验收。

只将显式白名单合成result JSON/截图经既有GitHub日志分块回读，逐文件sha256/长度/块序验证后存repo；不上传额外artifact/Library/恢复包/其他目的地。实际protected renderer结果/截图未回读前，真实浏览器/视觉仍未签收；WindowsServer viewport不等于Win11或物理手机。E20原AT05首次原因UNKNOWN、历史失败及各原阶段门保持。

官方依据：[runner镜像浏览器清单](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)、[Playwright channel和chromiumSandbox](https://playwright.dev/docs/api/class-browsertype)、[Windows sandbox架构](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/design/sandbox.md)。实际runner版本须以本次inventory为准。

候选CI37421567905在浏览器步骤开始前主动取消：固定SDK源码审查发现默认unsafe SwiftShader/禁用浏览器保护参数，不能借常规SDK默认当作正常保护证据。仅用官方ignoreDefaultArgs去掉这些参数（包含整个禁用features switch以保持默认AutoDeElevate/HttpsUpgrades等）；没有加unsafe参数或改OS设置，不能重新添加保护弱化参数来解决启动失败。修正源码/精确新CI另核实。

首轮正常保护尝试Cf0732e/CI37421853614已completed/failure：安装Edge153.0.4234.48签名Valid、Node22.23.3，正常启动与匿名首页真实渲染成功；Browser.getBrowserCommandLine因未设置enable-automation拒绝，发生在首个参数检查前，不能宣布renderer token或认证流程成功。原工程PG372PASS0FAIL0SKIP170.611s，Cleanup成功。首轮JSON/截图/receipt全部保留在first-*，首次失败图已人工查看，仅证明匿名首页渲染。改为SystemInfo精确PID→只读psutil真实args与WinTOKEN_QUERY，不新增启动flag；新测试整数10+30的返回字符串期望修为原契约40，负例核无result/sum字段，不改原AT05或生产行为。

当前59f3481/CI37422476293进度及实际shell执行证据见checkpoint.json/current-run.json。此处是父线程请求的可接续状态，不是浏览器任务终态；仍须监督CI并检查真实desktop/mobile截图和身份/控制流程。只在原授权范围有具体故障才有界修复；安全路径不支持则BLOCKED并报告最小环境需求，不加fixture/feature。
