# Sim2Act 独立桌面宿主

直接使用 WinForms + WebView2 SDK，不调用浏览器、不使用 MSHTML/IE 回退、不安装系统运行时。用户启动 `Sim2Act.exe`；只在原后端真实 READY 后显示工作台，关闭窗口通过该子进程的私有 stdin 请求原停止路径，核对同 worker 的 STOPPED、真实进程退出和输出 EOF 后结束。退出未知保留锁与数据，不 kill 或重启。

预先存在的依赖：Windows x64、.NET Framework 4.6.2 或更新版本、Microsoft WebView2 Runtime。缺项明确失败。SDK 为应用自身的固定文件，不是系统运行时安装包。

在新组装、没有旧 EXE 的候选目录中，用**已有** .NET Framework csc 构建：

```powershell
powershell -NoProfile -File .\desktop-build\Build-Desktop.ps1 -CandidateRoot 'E:\Software\NEW-CANDIDATE\Sim2Act-preview' -SdkPackage 'E:\Software\assets\microsoft.web.webview2.1.0.4314.35.nupkg' -SourceCommit '<完整40位应用提交SHA>'
```

以上命令在装配 ZIP 解压后的 `Sim2Act-preview` 根目录执行。仓库内直接调用时才使用 `scripts/windows/Build-Desktop.ps1`。

构建不下载或安装任何东西。官方 SDK 包 URL、固定字节数/SHA256 写在脚本与输出 manifest 中。窗口/生命周期尚须在 Windows 对当前精确应用包验收，`BUILT_NOT_WINDOWS_EXECUTED` 不能当 READY。

后台继续使用包内 `runtime/python.exe`，数据沿用 `workspace data`，WebView2 profile、缓存、temp、exports 与日志均在应用目录下。旧 Chrome profile 不修改。当前入口明确是合成 SQLite 工作台，不等于正式 PG/真实模型资格；原后端权限与安全门不变。

本次源码额外接受显式 `Sim2Act.exe --exact-read-live`，沿同一宿主、READY／STOPPED 和持久目录启动有限文本真实模型入口；默认双击仍不启用模型。只读取当前进程环境已有的令牌别名，不安装运行时、创建凭据或改变系统环境。使用范围见[有限文本目标](../docs/F2/BlankSyntheticWorkspaceQuickstart.md#显式开启有限文本目标)。当前7bf宿主已通过Linux交叉编译，但没有Windows执行或窗口验收，旧安装包不能当作包含本次功能。

桌面私有控制入口现在在 `workspace data/desktop-origin.json` 保存已实际绑定的回环端口。完整关闭重开后只重绑此端口，保留同一 WebView2 profile 时，规范运行的原请求键可继续按原协议只读核对，不会因随机端口丢失同源存储。记录绑定已认证工作区身份，只是启动元数据，不授予材料、模型或审批权限。

若端口已占用，后台报告 `PORT_UNAVAILABLE`，不会扫描、换端口或访问占用者。先核是否有此软件原窗口/后台仍未安全退出；保留数据、原键与日志，不删除 origin 记录或强杀不明进程。记录损坏、路径链接或身份变化也停止启动，不自动覆盖。Windows 使用独占监听及无覆盖原子移动，真实 WebView2 存储与窗口生命周期仍须目标机验收。

升级旧工作区时若尚无此记录，只会在首次成功启动建立新的稳定 origin，保障之后建立的键；不能找回旧随机端口中的历史意图，不能扫描旧 profile 或凭空迁移旧键。遇旧未知回执应先核对已有任务历史，不能将本次稳定 origin 当作旧请求已核验。移动/复制工作区时还须保留配套 profile；启动元数据不是身份凭据。

## 退出、恢复和移除

关闭窗口后等待后台正常退出。只有同worker的STOPPED、clean/data_preserved、实际exit0及双EOF都核对成功，宿主才释放本次运行锁；直接关页面或出现“退出未确认”不代表已停止。启动重开时先提供可交互工作台，再处理已经排队的任务，因此可以从正常任务入口读取或取消原Run，不需要另建请求。

这是一份应用目录内的便携构建，没有全机安装／卸载步骤。移除应用前必须确认原窗口与后台已正常退出；未知退出、残留锁或日志失败先保留现场，不自动删锁重启。需要保留工程时，先备份整个 `workspace data`（包含主库、配套控制库及启动身份）、`webview-profile` 和 `exports`，不要只复制单个SQLite文件或改动marker。核对备份后，可由使用者移除这个专用解压目录中的应用、私有runtime、SDK及缓存；不得删除共享Python、系统WebView2 Runtime或其他项目文件。本脚本不会自动永久删除工程，跨软件版本恢复仍服从原指纹／审批校验。

## Linux构建宿主组件

维护者可在包含指定Git提交的源码仓库中使用 `Build-CrossDesktop.py`，在已有的隔离官方构建工具上编译同一WinForms/WebView2宿主；便携目录内继续使用前面的`Build-Desktop.ps1`。`cross-build-tools.json`固定Microsoft .NET 8.0.33运行时、Roslyn4.11.0与net462参考程序集1.0.3的官方URL、SHA512及实际工具文件SHA256；.NET8只运行编译器，目标仍是.NET Framework4.6.2。脚本不下载、不安装全机工具、不运行Windows程序。工具不匹配、旧输出或编译失败明确停止。

```sh
python scripts/windows/Build-CrossDesktop.py \
  --source-commit 7bf6fd84fd694efe8348e1b565b01ad2e0765c40 \
  --tools /已有的隔离Microsoft工具目录 \
  --sdk-package /已有的/microsoft.web.webview2.1.0.4314.35.nupkg \
  --output /新的构建输出目录
```

工具目录包含`dotnet/`、`compiler/`、`net462/`三份已核内容，逐文件与锁定清单匹配。构建从指定Git提交读取真实宿主与manifest，实际调用编译器，检查x64／GUI／托管入口并保留命令、日志和结果。组件ZIP含真实EXE、对应SDK及许可，不含Python运行时、Windows应用wheel／四枚pyd，不是可直接使用的安装包。它只可与同一应用提交的完整后端组合；Windows实际启动、任务栏、保存、导出、关闭重开及错误流程仍需另外验收。不能拿交叉编译或Linux后端成功替代这些结果。
