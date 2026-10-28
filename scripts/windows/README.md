# Sim2Act 独立桌面宿主

直接使用 WinForms + WebView2 SDK，不调用浏览器、不使用 MSHTML/IE 回退、不安装系统运行时。用户启动 `Sim2Act.exe`；只在原后端真实 READY 后显示工作台，关闭窗口通过该子进程的私有 stdin 请求原停止路径，核对同 worker 的 STOPPED、真实进程退出和输出 EOF 后结束。退出未知保留锁与数据，不 kill 或重启。

预先存在的依赖：Windows x64、.NET Framework 4.6.2 或更新版本、Microsoft WebView2 Runtime。缺项明确失败。SDK 为应用自身的固定文件，不是系统运行时安装包。

在新组装、没有旧 EXE 的候选目录中，用**已有** .NET Framework csc 构建：

```powershell
powershell -NoProfile -File scripts/windows/Build-Desktop.ps1 -CandidateRoot 'E:\Software\NEW-CANDIDATE' -SdkPackage 'E:\Software\assets\microsoft.web.webview2.1.0.4314.35.nupkg' -SourceCommit '<完整40位应用提交SHA>'
```

构建不下载或安装任何东西。官方 SDK 包 URL、固定字节数/SHA256 写在脚本与输出 manifest 中。窗口/生命周期尚须在 Windows 对当前精确应用包验收，`BUILT_NOT_WINDOWS_EXECUTED` 不能当 READY。

后台继续使用包内 `runtime/python.exe`，数据沿用 `workspace data`，WebView2 profile、缓存、temp、exports 与日志均在应用目录下。旧 Chrome profile 不修改。当前入口明确是合成 SQLite 工作台，不等于正式 PG/真实模型资格；原后端权限与安全门不变。
