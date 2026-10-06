# 精确 0389 Windows 标准 CI 终态证据

唯一普通 push 自动触发 run [37533601563](https://github.com/T1doo/Sim2Act/actions/runs/37533601563)，source `0389c871443e5fccb4920427fd4ba93bb3ff650e`，单 windows-2025，contents read。终态 SUCCESS：900 collected、895 PASS、5 SKIP、0 FAIL、0 ERROR；Ruff/mypy34、application-role smoke、原生 Edge、Report/Cleanup 成功。

`github-run.json` / `github-job.json` 保存远端终态；`remote-head.txt` 核对既有 dev 分支精确 SHA。冻结 workflow 实际 job 上限 **15 分钟**（父描述25），browser4分钟，未改 workflow/提高上限。没有新增 runner/权限/secret/Actions缓存/artifact上传；生产 activation68443及后续文档仍本地。

`focused-case-membership.json` 将同源900收集节点与原生900个 -q 字符逐位对应，总数另与真实JUnit aggregate核对。原13失败及新增5 socket oracle全PASS。该结果是 DERIVED_Q_ORDER，ordinal为zero-based，不声称下载了逐case JUnit。5 SKIP节点见 `native-skips.json`，原-q未输出每项原因。工程套件混合 env-backed PG 与显式 SQLite/Mock/JS，不称895全PG。

`browser-results.json` 40检查，`agent-results.json` 33 + registered generation29，`protocol-results.json` 26检查全PASS。真实source→独立登记核查→extract→fresh cold及metadata recovery、lost receipt、context race、跨项目/身份负例均通过；协议4个离线Mock Attempt，真实model/outside-origin/browser-review请求0。Grants/principals fingerprint不变。默认worker0发送，owner PENDING、semantic UNKNOWN，未发布。

9个原命名JSON/PNG从既有stdout限名chunk恢复，`emission-receipt.json`核验原bytes、length、SHA及2MB限额；不使用额外远端artifact。原JSON capture-time emitted:false/visual NOT_REVIEWED保持原样。`pixel-review.json`是实际查看6个未编辑PNG后的独立记录，协议390px截图另以原分辨率查看。桌面/窄屏内容与控制可见，协议document width等于viewport、overflow0；结果JSON容器只显示可滚动的一段，不宣称截图展示全部证据。

实际before/after Edge renderer审计 AppContainer/restricted token=true、integrity0、无sandbox disabling args；已装微软签名Edge，不安装fallback，不增加权限。browser fixture仍SQLite；390px仅viewport，Win11/物理移动验收 NOT_RUN。

`material-blob-fingerprints.json`记录19个material package/evaluation原blob SHA且对1aa完全一致。此前六实际素材checkout/core.autocrlf证明在0389已有修复证据；原生完整链的既有原始SHA断言现在通过，未改pins/gold/manifest。安全oracle仍拒绝普通direct connect及真实HTTPTransport，仅允许经过精确stdlib caller/socket/listener验证的内部socketpair。

`native-log-excerpts.json`为原日志去除base64 chunk行后的JSON原行记录（字符串保留尾随空白）；完整原日志留在 `/tmp/windows-native-37533601563.log`，其SHA见`final-validation.json`。清理step SUCCESS，原owned API/worker和临时PG停止；Windows残schema/role数量没有另测，不宣称0。先前37526795142真实13失败及归因证据保留。两个本地证据脚本的ordinal/path纠正单列在final-validation，不改变成功源码或重跑CI。

生产activation NOT_RUN、真实模型额度0；完整P-B、真实语义、F1正式签收、Win11、完整AT02未升级。本目录在原CI终态归档时仅本地保存；后续父授权将本目录与发布状态以纯文档提交移到0389之上同步。activation实现仍未推送；原JSON记录其捕获时状态，不重写历史。
