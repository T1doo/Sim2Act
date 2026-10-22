# 窄完成 UI：关闭/返回回调边界与受限浏览器候选

基线 `4cb2dee1c207e75760012721e3d72a084c13f651`。此前入口对 Run/身份/项目 ABA 已有保护，但 `selectWorkspace()` 不失效协议完成控制器；离开项目后返回，先前的完成/详情回调可能继续读取或展示成果。本片在实际工作区代次及可见性上校验 POST、GET、错误与 finally；工作区切换失效 intent/selection、清理成果/冷输入，并保留 Run 元数据和当前页原命令 Map。明确返回读取才能继续；已确认回执只能 GET，UNKNOWN 仍用原 body/key。页面刷新/关闭不保证恢复内存键。

最终两项定向 pytest **2 PASS / 0.99s**，见 `pytest-final.log/xml`。实际控制器 VM 新增工作区 POST ABA、迟到 accepted GET 反例，另复用已封存事实的真实 loopback HTTP。VM 不是 DOM 或浏览器；0 新 Source/extract/Worker/Mock/Grant，未重跑37/20或进程恢复套件。独审者 `independent_gap_review` 对实际 UI 差异只读限定 ACK，未执行、开库或写入。源码绑定 `source-manifest.json`。

本地浏览器预检 `local-browser-preflight.json` 原件保留：sandbox helper 所有权不合正常受保护启动要求，因此 NOT_RUN；未 chown/chmod、关闭 sandbox、安装浏览器或转用户电脑。GitHub 只读权限读取成功，仓库公开；现有 `windows-2025` 标准 runner 可按[官方免费范围](https://docs.github.com/en/actions/reference/runners/github-hosted-runners)复用。新 job 仅现有普通开发分支、公开仓库、attempt1、精确一次 marker；原 foundation job 不会在此分支运行。标记不是服务器端永久去重；不得重复推送带该标记的提交或手动重跑。

候选只复用原 Python/Windows lock、现有完整性锁定 Playwright-core 1.63.0、有效 Microsoft 签名的已安装 Edge 和既有只读 token/命令行审计。不下载浏览器、不新增 SDK/许可/凭据/权限、Actions cache 或 artifact；不调用原全量 WindowsCI Setup/Test。只有封存 SQLite/sidecar 的副本，没有新 Worker/Source/extract/模型。应用业务时钟显式合成，不是 G0/真实源或 PostgreSQL 验收。

第一步在 checkout/setup 前设180秒 UTC 工作截止；两个 Actions setup 各1分钟上限，后续自有启动器只使用剩余时间。安装过程同句柄监督，浏览器/真实 API 退出和依赖清理共用额外10秒；4分钟 job 只是灾难兜底，不用其当工作预算。每次业务 GET（含 health/poll）最多30、完成 POST最多3、截图最多4；静态资源另计最多40，其他写操作和 off-origin 页面请求均拒绝。正常应用 polling 未修改。任何超额/失败不自动重试。

浏览器验证计划：真实 DOM 显式确认/双击→实际 POST 已接受但回包丢失→同页选择另一 Run 后返回→原命令重试并核精确 cached 回执→一次受控成果 GET 403→仅 GET 恢复并严格比较原计划/回执→持有真实详情 GET，在工作区离开返回后释放，确认无迟到展示。此403只是响应故障注入，不声称真实服务端撤权。所有业务事实由原 API 读取/完成，不替造账户或响应来源。

正常结束须确认 API/AnyIO/Node 与登记浏览器后代终态、原非完成表/sidecar/期限不变。Windows 已加载 pyd/DLL 只能在 Python 退出后由外层自有进程清理依赖目录；沿同一最早清理截止。`.NET Kill(true)` 后 WaitForExit 只证明直接进程退出，[不证明后代终止](https://learn.microsoft.com/en-us/dotnet/api/system.diagnostics.process.kill?view=net-9.0)，任何强制收尾/未知后代/拒绝均 UNKNOWN，不重置时间或换杀法，不签完整清理，不删除未确认资源。

当前本目录仅本地定向结果及启动前证据；原生窗口结果须另行归档，不能从 VM 或候选源码推断 PASS。
