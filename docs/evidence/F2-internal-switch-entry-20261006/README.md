# E22：内部兼容版本切换入口（最小工程切片已交付）

原V5 F2-T08/AT16/产品§10.1最小工程切片。既有认证owner/project/app/runtime/instance，手动目标Release→准备→精确批准回读→未默认勾选确认→一次性事务切换。正式发布false/0LIVE，不新增Grant/身份/表/生产DDL/CSV能力。回退仅指针切换，不能删除结果/Run历史或撤销外部动作；已有Worker版本改变时保守拒绝旧接受任务策略不变。

prepare/GET/commit共用目标范围、兼容schema转移、保留数据验证；目标fingerprint/revision/data/hash/grant/expiry全部绑定。API实例URL与批准必须一致；服务commit在锁实例前核项目。损坏字段/类型及一致重hash跨app/project拒绝，批准不消费。重复提交一次成功其余409，无重放机制。UI代际保护迟到回执，取消/返回不撤销已接受切换，未知确认结果只提示读回历史，不自动重发。

[独立报告](independent-review.md)：11 SQLite PASS 6.36s、实际损坏批准及合成NodeVM双击/取消迟到复验；独立未跑PG/Windows/真实浏览器。独立首次复现旧服务跨项目损坏批准直接commit被接受（HTTP本已拒绝），当前修复后直接commit DomainError闭合。初开发helper变量错误6FAIL/44PASS/2SKIP保留[记录](implementation-first-failure.json)，修复后focused58PASS/2SKIP，后续新增类型与项目负例11PASS；不删失败。初SQLite360PASS22SKIP102.97s对应中间源码/10新测试；最终aggregate另存。

现WindowsBrowserCI仍同windows-2025既有job15min、browser step4min，官方固定SDK/签名预装Edge、chromiumSandbox:true、实际renderer只读token检查、CSP不改/bypassCSP:false。新增真实继续命令、兼容升级/回退/结果Run lineage、手动确认、重复点击、取消/返回迟到、过期及不兼容拒绝。仅owned test_only fixture调用已有service生成incompatible target；一次合成switch批准在首次回执前把TTL收紧3秒并重算精确fp，等待实际到期后UI禁用/实际API409，不改生产300秒期限或系统时钟。该短TTL不冒称生产五分钟计时验收。截图/JSON经既有job日志白名单回读/块序长度SHA核验，仅repo证据。

以下保留事前及执行中记录；最终精确源码/CI/PNG核验以收尾段为准。Win11普通用户、物理手机、其他浏览器、完整焦点/无障碍/复杂业务schema迁移、完整AT02/F1/F2/P-A/P-B/正式发布均未签收；E20最初AT05根因UNKNOWN继续保留，Linux SUID保护路径阻塞未改。

本地最终产品源码：SQLite361PASS22PG/platformSKIP118.65s；LinuxPG382PASS1WindowsSKIP300.43s；最后HTTP focused29PASS1PGSKIP14.14s，实际CRUD-only角色switch额外1PASS3.28s。PG collection之后在原role测试追加switch断言，已单独实际通过，最终精确ServerCI完整重验待；没有把此前aggregate当作新增断言已收集。ruff/mypy21/3JS syntax通过，[source hashes](source-hashes.json)；生产/API/UI与独立接受hash相同。最终follow-up只静态核新增worker-v2浏览器/role断言。

首轮精确3e1688e/CI37427612714 completedFAIL：原工程383PASS0FAIL0SKIP1warning175.11s，Report/Cleanup成功；正常Edge/browser8checksPASS，实际resume后已通过真实状态QUEUED等待，但紧接测试用innerText读折叠pre得空而断言失败。无console/pageerror；[失败JSON](first-browser-results.json)/[实际截图](first-failure.png)/run/长度hash receipt均保存。只把此检查改为实际可见状态栏QUEUED，未改产品/原AT05/CSP/OS或sandbox，需新源码精确CI复验。

第二轮64f9783/CI37428175050 completedFAIL：原工程383PASS0SKIP1warning175.82s/cleanup成功；已签名Edge/固定SDK准备成功，延迟实际响应用例在route.fulfill报`Route is already handled`，Node异步异常导致没有browser JSON/PNG回执。不能声称第二轮实际浏览器检查数量。原空receipt、run与有界错误excerpt保存second-*。已检查本地integrity锁SDK源码：unroute会更新拦截模式，待处理请求需先完成再移除handler。修测试等实际响应交付后才unroute，并捕获handler异常交回主catch保存真实失败报告；不伪造响应/放宽断言或更改产品/OS/CSP/sandbox。继续新精确源码CI。

## 最终精确源码 / 真实终态

`c16cbae1723eeaf089e4cb36eef9874846705d9b`普通push，[CI37428871976](https://github.com/T1doo/Sim2Act/actions/runs/37428871976)/job112154763261 **completedSUCCESS4m51s**。[原工程383PASS0FAIL0SKIP2旧warning178.95s / JUnit178.910](windows-results.json)，Setup/native最小角色smoke/原Test.ps1/ruff/mypy21/Report/Cleanup全部成功，新增CRUD-only role切换断言在该完整CI实际执行。本地SQLite361PASS22PG/platformSKIP118.65s、LinuxPG382PASS1WindowsSKIP300.43s、HTTP focused29PASS1PGSKIP14.14s及额外真实PGrole1PASS3.28s另存；独立11SQLitePASS6.36s+service篡改和NodeVM迟到/重复、final路由静态接受，未独立PG/browser/CI。生产/API/UI最后hash不变；最终[source-hashes](source-hashes.json)已逐文件重算核验。

[38实际浏览器检查](browser-results.json)全部PASS：已有认证Release/实例/Run、真实pause→resume→QUEUED→pause/cancel、新任务返回重开/实际Worker结果v1；手动目标无默认、冻结保留范围/未勾选禁止确认、实际接受后的迟到prepare取消/返回丢弃、双击单POST、兼容升级一次+原数据/Run保持；**升级后的新Run由独立Worker真实完成并固定targetRelease，追加结果v2**；已消费批准409；回退revision3保留两版数据/Run及三条版本历史；真实不兼容目标409及可读原因；首次回执前单次合成TTL3秒到期后UI禁用+精确API409、读回指针与数据不变；cold mobile读取同一history；第二实例独立及跨owner/instance/result/control403保持。7预期409/403原console条目完整保留，pageerror0/意外console0。仅合成CSV/固定可信动作，0模型/无真实业务外发/正式发布false；没有任意代码或通用writer。

正常预装Edge153.0.4234.48签名Valid/Microsoft、Node22.23.3，同windows-2025 job15min/browser4min，无新runner/订阅/浏览器下载。`chromiumSandbox:true`、原CSP/bypassCSP:false、去除锁SDK弱化保护默认参数；实际broker无这些SDK弱化参数/无sandbox禁用，两实际renderer AppContainer/restricted true/integrity0。broker为High RID12288且Server admin=true/EnableLUA1，如实记录[native context](native-context.json)，不是Win11普通用户。未修改系统权限/代理/SUID/安全策略。

[desktop](desktop.png)1366px和[mobile](mobile.png)390px两实际完整PNG，经既有job日志白名单解码、块序/长度/SHA256[receipt](evidence-receipts.json)核验，并逐张view_image original查看，[视觉检查](visual-review.json)记录两列/单列、目标与历史/两版结果保留、无横向溢出/遮挡或错误overlay，全部显示按钮>=42px且在viewport内。页面技术JSON和长历史仍密集，手机仅viewport，不是物理设备或全无障碍验收。真实浏览器取消/返回迟到覆盖prepare，迟到commit取消仅独立NodeVM，未冒称全部网络故障签收。合成3秒TTL不代表生产300秒计时验收；没有改时钟。

初开发变量失败、首CI隐藏pre读取失败/实际PNG及第二CI路由异步异常/无回执事实都保留；最终正常测试断言不放宽、不用跳过或安全降级替代。源码3e1688e→64f9783→c16cbae仅两次测试修复，产品/API/UI hash保持。当前E22最小内部工程子项关闭；**完整F1/F2/P-A/P-B/AT16、Win11/物理手机/其它browser/完整焦点无障碍、原完整AT02 fixture、通用业务数据/迁移/正式发布仍OPEN/NOT_RUN**。E20首次AT05根因UNKNOWN和Linux SUID路径BLOCKED保持。原work/V5/历史AT02/原AT05不修改，无恢复包/Library/额外artifact上传目的地。
