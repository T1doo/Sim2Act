# Sim2Act 独立桌面宿主

直接使用 WinForms + WebView2 SDK，不调用浏览器、不使用 MSHTML/IE 回退、不安装系统运行时。用户启动 `Sim2Act.exe`；只在原后端真实 READY 后显示工作台，关闭窗口通过该子进程的私有 stdin 请求原停止路径，核对同 worker 的 STOPPED、真实进程退出和输出 EOF 后结束。退出未知保留锁与数据，不 kill 或重启。

预先存在的依赖：Windows x64、.NET Framework 4.6.2 或更新版本、Microsoft WebView2 Runtime。缺项明确失败。SDK 为应用自身的固定文件，不是系统运行时安装包。

在新组装、没有旧 EXE 的候选目录中，用**已有** .NET Framework csc 构建：

```powershell
powershell -NoProfile -File scripts/windows/Build-Desktop.ps1 -CandidateRoot 'E:\Software\NEW-CANDIDATE' -SdkPackage 'E:\Software\assets\microsoft.web.webview2.1.0.4314.35.nupkg' -SourceCommit '<完整40位应用提交SHA>'
```

构建不下载或安装任何东西。官方 SDK 包 URL、固定字节数/SHA256 写在脚本与输出 manifest 中。窗口/生命周期尚须在 Windows 对当前精确应用包验收，`BUILT_NOT_WINDOWS_EXECUTED` 不能当 READY。

后台继续使用包内 `runtime/python.exe`，数据沿用 `workspace data`，WebView2 profile、缓存、temp、exports 与日志均在应用目录下。旧 Chrome profile 不修改。当前入口明确是合成 SQLite 工作台，不等于正式 PG/真实模型资格；原后端权限与安全门不变。

本次源码额外接受显式 `Sim2Act.exe --exact-read-live`，沿同一宿主、READY／STOPPED 和持久目录启动有限文本真实模型入口；默认双击仍不启用模型。只读取当前进程环境已有的令牌别名，不安装运行时、创建凭据或改变系统环境。使用范围见[有限文本目标](../../docs/F2/BlankSyntheticWorkspaceQuickstart.md#显式开启有限文本目标)。这个新增参数尚未对新版 EXE 进行 Windows 编译或窗口验收，旧安装包不能当作包含本次功能。

桌面私有控制入口现在在 `workspace data/desktop-origin.json` 保存已实际绑定的回环端口。完整关闭重开后只重绑此端口，保留同一 WebView2 profile 时，规范运行的原请求键可继续按原协议只读核对，不会因随机端口丢失同源存储。记录绑定已认证工作区身份，只是启动元数据，不授予材料、模型或审批权限。

若端口已占用，后台报告 `PORT_UNAVAILABLE`，不会扫描、换端口或访问占用者。先核是否有此软件原窗口/后台仍未安全退出；保留数据、原键与日志，不删除 origin 记录或强杀不明进程。记录损坏、路径链接或身份变化也停止启动，不自动覆盖。Windows 使用独占监听及无覆盖原子移动，真实 WebView2 存储与窗口生命周期仍须目标机验收。

升级旧工作区时若尚无此记录，只会在首次成功启动建立新的稳定 origin，保障之后建立的键；不能找回旧随机端口中的历史意图，不能扫描旧 profile 或凭空迁移旧键。遇旧未知回执应先核对已有任务历史，不能将本次稳定 origin 当作旧请求已核验。移动/复制工作区时还须保留配套 profile；启动元数据不是身份凭据。
