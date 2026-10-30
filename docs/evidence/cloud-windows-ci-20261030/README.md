# Windows CI：实际失败与精确字节修复

第一次精确输入 `99e79653bbaf8d6324f833fb5f62158c89086b41`，实际run [40981407066](https://github.com/T1doo/Sim2Act/actions/runs/40981407066)，job123822091403，约1分08秒后失败。两个原生模块实际import已完成；随后的原严格_qualified在text_software_anchors原件SHA处报Software anchors changed。浏览器、像素、Windows回归未启动，不能计通过。原老分支jobs按条件skipped，不代替新job结果。

原.gitattributes只有*text=auto，源码和资格JSON没有精确字节规则。云端独立用git core.autocrlf=true过滤复现：text_software_anchors.json由Git SHA256 24f26f…4193a变98573e…bc60，共增加143份CRLF；资格JSON及py也被转换。实际失败日志未直接打印Windows文件hash，故这是一条可重复、与报错相符的checkout根因定位，不伪造远端字节实测。

最小修复仅让/src/sim2act/**保留Git原字节（-text），不删文件、不重算Windows变形字节的资格、不改pin或核心检查。142份资格源加锚点与前端共149文件在同core.autocrlf=true过滤条件下逐字节等于Git原件，原_qualified继续通过。新增CI只读诊断会先核checkout对Git原件，不写文件归一化蒙混过关。checkout-eol-before/after.json保留比较及全部摘要。

准备阶段使用公开仓库标准windows-2025、contents:read、现有锁定依赖和原生编译，0真实模型。原一次性标记和15分钟上限保留，无Actions artifact/cache上传。符合[GitHub对公有仓库标准runner免费、日志不计artifact存储的说明](https://docs.github.com/en/billing/concepts/product-billing/github-actions)。父层读回本次实际失败后明确允许修复版必要一次有界重跑；不会rerun旧job造成attempt2跳过，不自动重复未知失败。

first-run.json与压缩日志保留该次结果。后续修复版必须另记完整SHA、run/job和真实终态；Windows Server/Edge不等于用户Windows11/EXE/WebView2，Mock不等于live。未访问用户电脑、绕旧网络/Library拒绝、增加凭据或安全权限、改main或发布Release。

## 第二次真实失败与输入闭合

修复版完整输入 `37656e4b5a8ffadbc49c907b6cf465a3a503d135` 的实际 [run40982258111](https://github.com/T1doo/Sim2Act/actions/runs/40982258111)、job123824871578仍失败。它已通过149份checkout精确原字节、双Windows原生扩展导入、原完整_qualified、现有Node22.23.4、锁定npm依赖和既有签名Edge检查。这次失败是Python种子间接import测试模块时缺少独立合成GOLD，核心回归也在collection阶段同因失败；没有真正启动Edge，未产生任何像素证据。second-run.json和原解码日志压缩件保留真实结果。

两次不是同一失败。官方check-run起止：首次00:42:54–00:43:59 UTC，65秒；第二次00:51:10–00:52:31 UTC，81秒；实际job墙钟合计146秒。邮件中的整个workflow时长包含额外调度差异，不冒充精确计费分钟。原单job15分钟上限不变，两次均终止，不请求第三次CI。

本次只修复验证输入：稀疏检出明确加入现有independent-gold.json。只读独审进一步发现真实页面刷新会读4个protocol evaluation JSON，故一并精确加入这4个已pin的合成资产，避免页面静默RESOURCE_UNAVAILABLE。种子准备在任何Mock定义调用前实际GET所属项目协议目录，要求HTTP200及4份目录。没有复制整份docs、删除断言、替换pin、改变安全门或业务源码。这5个资产既有-text规则在core.autocrlf=true下仍与Git原字节一致。

独立解包目录只包含声明的CI输入，已确认加载的sim2act也来自该目录；在该目录真实执行原5个回归文件：22项通过、0跳过、83.522秒、exit0，包括真实后端退出重开、原键恢复、损坏回执、跨入口取消及精确结果导出。这是Linux/JSDOM/SQLite和显式固定Mock定义，不是Windows或live；测试时没有原生扩展。之后单独用现有gcc成功构建两枚Linux扩展，双导入与完整原_qualified通过；再用相同隔离输入实际GET核4份目录、无私有oracle字段、跨项目和无身份403，0模型调用。不重复整组测试来增加数量，不把后续原生构建追溯当成此前原生流程通过。

isolated-input-repair.json、isolated-flow.log/xml、isolated-native.log和isolated-catalog.json记录输入身份和边界。独立Windows/Edge实际重启、1366×768及1440×900像素和EXE/WebView2仍未验，当前不能宣称整体验收或发布就绪。

## 第三次有界 Windows 实跑与观察器修复

父层明确追加一次必要实跑：总预算900秒，前两次已用146秒，剩754秒。因此最小触发提交仅将本job上限从15减到12分钟（720秒，保留34秒余量）。实际输入 `9bf5d6218dc3064b8beb6a031630bbad95fa23db`；启动前重新核154份源码/资产在core.autocrlf=true下与Git原字节相同，五份目录输入均在白名单。未扩大租约、观察窗、权限或依赖。

实际 [run40983666437](https://github.com/T1doo/Sim2Act/actions/runs/40983666437)、job123829480876，01:04:59–01:09:07 UTC，248秒，最终 **FAILURE**。三次job墙钟累计394秒，原预算尚余506秒；没有请求第四次。邮件中的整个workflow时长含额外调度，不替代job计时。

这次准备已成功，且Windows Server2025真实后端原生回归22项全部通过、0跳过、126.084秒，包括稳定origin、三次后端进程/原键恢复、取消、跨入口及导出；third-native-flow.xml为实际runner的JUnit。不能把该组JSDOM驱动通过算成Edge全链通过。

实际Edge已启动，原进程参数和受限renderer token检查通过。首个真实spec POST返回202，按测试安排故意丢回执，页面正确保留原请求与待恢复状态。随后原请求键GET在观察器readJSON的固定15秒处被Undici AbortSignal中止，尚未进入浏览器/后端重启、CSV页面操作或两种viewport布局断言。唯一后端最终exit0、双EOF、STOPPED clean且data_preserved；这些退出证据不能证明该Run最终SUCCEEDED，也没有导出该Run最终状态。third-desktop-results.json保留这份失败原件。

third-failure.png是该次 **真实1440×900失败页面**（合成数据、Mock定义、本机预览），不是guide、设计图或成功截图；已实际查看像素。原request待恢复、Failed to fetch及LIVE关闭状态均保留。两份计划布局截图和EXE/WebView2验收仍NOT_RUN。第三次完整解码日志压缩件和文件长度/SHA校验单均保留。

只读审查核实：synthetic_workspace会把API读取排在整次worker.once之后；观察器外层原本允许30秒完成窗口，内部GET却硬截15秒。这是观察预算冲突，不能据此宣称产品保存失败。最小修复让until传递同一个绝对截止时刻给spec/CSV读取；HTTP和JSON正文受剩余窗口及原155秒全局上限共同约束，predicate返回后再次核时。原30/25秒窗口、事务期限、CI上限及200/SUCCEEDED/单POST/结果身份断言均不变。超时、非200、坏JSON不重试；新增日志只记类别、预算、耗时和状态，不含URL、请求键或token。

observer-http-check.cjs对原件和候选的原始helper执行真实回环HTTP，限定为观察器验证：同一16秒响应，旧版15005ms超时，新版16049ms在原30秒窗内成功；还验证观察/全局截止、迟到true、正文超时、403、坏JSON及未完成状态均不误通过。没有浏览器、模型或产品Run，该fixture的SUCCEEDED仅为HTTP测试响应，不冒充产品保存证据。observer-http-result.json/log、源码SHA和最终只读独审记录绑定此次结果。**该修复尚未再次执行Windows CI**。

产品本地SQLite长事务可能阻塞状态读取及取消的响应性风险仍在，本次仅修观察边界，不能把它当作产品响应性已修复或发布就绪。业务源码和资格pin未改变；新观察器通过不追溯覆盖第三次失败。
