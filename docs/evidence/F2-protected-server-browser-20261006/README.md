# E21：受保护 WindowsServer 真实浏览器最小验收

**内部只读入口的最小真实浏览器流程已完成**。精确源码 `2ead9b615226a2be1bdc59ef745473b7589fd120`，既有 [CI37423790107](https://github.com/T1doo/Sim2Act/actions/runs/37423790107)/job112138779536 **completed/success，3m55s**。原工程 PG **372 PASS、0 FAIL、0 SKIP、1 warning，136.70s**；新增 **25 项真实浏览器/布局/只读 sandbox 检查 PASS**，不把两者加成正式 AT 数量。Setup/native最小角色smoke/ruff/mypy21/Report/Cleanup均成功。[完整结果](browser-results.json)、[工程统计与范围](windows-results.json)、[原生runner实际context](native-context.json)、[精确run](final-protected-run.json)、[源码hash](source-hashes.json)。

本轮没有新增业务 feature；产品唯一变化为 `#internal-instance-title{overflow-wrap:anywhere}`，修真实390px页面长实例ID溢出。新增 test harness 与既有CI同job步骤，仍15分钟job/4分钟browser step，无新增runner/订阅或浏览器下载。官方npm registry固定 playwright-core1.63.0 integrity-lock、ignore-scripts，与原Python lock隔离。普通dev分支交付，0真实模型，正式发布部署false，无Library/恢复包/额外artifact目的地。

## 正常沙箱与真实执行

实际预装 **Edge153.0.4234.48**，微软签名Valid，Node22.23.3；实际镜像/context以归档为准，不用在线镜像清单替代实测。官方 `channel:msedge, chromiumSandbox:true` 正常启动，未改变OS/UAC/SUID/权限或使用no-sandbox。固定SDK默认弱化浏览器保护的参数被官方ignoreDefaultArgs过滤（含unsafe SwiftShader、self-XSS/phishing/IPC保护弱化、整个disable-features，以保持AutoDeElevate/HttpsUpgrades等默认）；实际browser参数检查确认无这些弱化，全部观测browser/renderer无禁用sandbox参数。没有为了通过而重新加入弱化参数。

通过CDP SystemInfo拿**本次精确PID**，只读psutil参数及WinOpenProcess QUERY_LIMITED_INFORMATION/Token QUERY：两个实际renderer均 **AppContainer=true、restricted=true、integrity RID=0**。browser broker本身High RID12288/unrestricted是本次admin runner事实，不宣称整个进程树都sandboxed，也不代替Win11普通用户验收。未调整token/privilege，不开启调试权限。CSP保持产品原策略，context `bypassCSP:false`；函数谓词缓存避免异步字符串eval触发CSP，未修改响应头或禁用CSP。

fixture仅显式test_only临时SQLite、两合成owner各一个project/CSV及已注册可信只读草案，实际生产API/UI，无额外fixture HTTP接口、任意代码或新生产Grant/表。任务由另一个真实Python进程调用现Worker.once消费持久queue并提交结果；这是one-shot worker，不宣称浏览器流程重新验证了整个长驻worker可靠性。原PG最小角色/native smoke与回归另外通过。浏览器SQLite证据不冒充新增PG角色验收或历史AT02完整双主体双项目初态。

## 实际流程与截图可读性

真实浏览器点击认证→冻结快照展示/未勾选不能确认→保存内部Release→独立实例→持久QUEUED→暂停/继续按钮呈现→取消及intent保留；新任务接受后返回页面不取消后台，重开读回历史；独立Worker计算整数10+30得到原契约字符串40/结果v1，原取消历史仍在。冷mobile context重新认证、读服务端结果/历史；新第二实例无继承结果，错误instance及foreign owner的instance/history/control403，foreign UI不呈现另一owner成果。

[桌面完整页面截图](desktop.png)：真实 **1366×900 viewport**，两列内部布局，状态/操作/历史/结果v1可读；scrollWidth1366，无横向溢出。
[移动宽度完整页面截图](mobile.png)：真实 **390×844 viewport**，单列卡片，长ID在卡片内换行，按钮/字段/Cancelled及Succeeded历史和sum40可读；scrollWidth390，所测按钮高42–43px且在viewport内。两张最终PNG均实际打开人工查看，没有空白页/错误覆盖层或裁切；仍是较密的工程JSON展示，本轮不改版。截图是完整页面，图片高度大于viewport高度，不声称物理手机或移动专用browser。

没有pageerror或意外console错误；四条**预期403** console条目完整保留在JSON，分别对应负例，不能写“console完全0”。25检查不是完整界面/焦点/无障碍签收。仅查看了本轮定义的状态与流程，不借早期jsdom或Linux旧图填本轮证据。

## 初次失败及修复证据（全部保留）

|源码/CI|实际结果|原因及范围|保留文件|
|---|---|---|---|
|8ee75ed / [37421567905](https://github.com/T1doo/Sim2Act/actions/runs/37421567905)|cancelled；browser skipped、Cleanup成功|SDK安全默认参数审查后在browser前取消；不当浏览器失败或通过|candidate-cancelled.json|
|cf0732e / [37421853614](https://github.com/T1doo/Sim2Act/actions/runs/37421853614)|FAIL，0已完成browser检查；PG372PASS、Cleanup成功|匿名页面真实渲染，但诊断Browser.getBrowserCommandLine要求enable-automation；改为只读精确PID查询，不新增启动flag|first-browser-results.json / first-failure.png / first-protected-run.json / first-evidence-receipts.json|
|59f3481 / [37422476293](https://github.com/T1doo/Sim2Act/actions/runs/37422476293)|FAIL，7项PASS；PG372PASS、Cleanup成功|异步字符串waitForFunction触发CSP unsafe-eval拒绝；只改测试函数谓词，CSP/sandbox不放宽|second-* JSON/PNG/run/receipts|
|783c33c / [37423117191](https://github.com/T1doo/Sim2Act/actions/runs/37423117191)|FAIL，16项PASS；PG372PASS、Cleanup成功|桌面/任务完整通过、cold mobile读回后，真实移动页面长标题横向溢出；最小CSS换行修复，原布局断言保留|third-browser-results.json / third-desktop.png / third-failure.png / third-protected-run.json / third-evidence-receipts.json|
|2ead9b6 / [37423790107](https://github.com/T1doo/Sim2Act/actions/runs/37423790107)|SUCCESS，25项PASS；PG372PASS、Cleanup成功|当前定义的最小流结束，无未处理本轮故障|最终JSON/两张PNG/receipts/run|

新测试数值期待曾误写40.00，依据原整数结果契约在59修正为40；负例核403且不含result/sum字段。没有修改原AT05、吞错、删旧测试或篡改AT02记录。第一次父线程请求的执行中状态保存在checkpoint-at-handoff.json/run-at-handoff.json，最终状态见checkpoint.json。不同实际缺陷分别修复，不无限重复fixture或扩相邻feature。

## 回读与保存边界

只把白名单合成JSON/PNG经**既有GitHub job日志**分块回读，[collect-log.py](collect-log.py)严格检查文件白名单、最大2MB、块序/长度/SHA256，并验证report的精确source SHA。[最终receipt](evidence-receipts.json)及各失败receipt保留；失败归档加first/second/third前缀，receipt仍记录原emitter文件名。没有上传额外artifact、业务DB/配置/profile/env/log全量、Library或其他目的地。Windows fixture API child由Python terminate/wait并必要时kill/wait owned child；browser正常close，job-owned fixture由finally移除，既有PG Cleanup成功。原work树保持，LinuxSUID仍BLOCKED，未作系统修复。

## 剩余门槛

本次仅提升 **WindowsServer上已认证内部只读入口的最小真实浏览器工程证据**。Win11普通用户、物理手机/其他browser、全界面状态/键盘焦点/无障碍仍NOT_RUN；撤权stop UI、更多迟到响应仅早前service/DOM证据，未借本轮签收。兼容switch页面、通用DAG/业务writer/迁移、正式批准发布部署、完整F1/F2/P-A/P-B/AT10/19/20门不变。E20原AT05首轮根因仍UNKNOWN；本轮原AT05/PG通过不说明根因已修。

官方依据：[runner镜像清单](https://github.com/actions/runner-images/blob/main/images/windows/Windows2025-Readme.md)、[官方Playwright参数](https://playwright.dev/docs/api/class-browsertype)、[Chromium Windows sandbox架构](https://chromium.googlesource.com/chromium/src/+/HEAD/docs/design/sandbox.md)。SDK实际default及过滤以固定包/source代码和runtime查询为准。WindowsServer正常平台能力不是绕过LinuxSUID拒绝，不关闭保护来补证。
