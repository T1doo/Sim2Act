# Windows同版本完整装配候选

应用源码 `042ab21c4fa9c7e5ba70c4e2877fb7060d962422`。此目录保存实际 Windows Server 2025 原生构建的完整包，不是交叉编译宿主组件。

- 文件：`Sim2Act-win64-042ab21c4fa9.zip`，19,745,959字节。
- SHA256：`cc177eeb8815194a4f1e973e146ce7dd95c2949350745a296c4d6a9bfcd38027`。
- 内含独立WinForms/WebView2 EXE、私有Python3.12.10、四枚Windows扩展和21个运行依赖。EXE为27,136字节，SHA256 `d9bb4c6609d2832173a03b03fcb02b3af8b052bb91d132686f7774bf19238df6`。
- 原始CI：[41325692393](https://github.com/T1doo/Sim2Act/actions/runs/41325692393)，151秒；61个协议测试零失败零跳过，最终包后台两次CSV30/v1与15/v2、同键去重、正常EOF停止和首次新进程同源重开通过。0次模型调用。诊断见 `docs/evidence/windows-full-package-20261101/attempt-2/`。

解压至普通可写目录（非链接/junction），使用系统已有Microsoft WebView2 Runtime，双击 `Sim2Act/Sim2Act.exe`；程序不安装Runtime或回退浏览器。窗口关闭走原后台STOP/EOF及退出回执。工作数据位于该目录的 `workspace data`，缓存位于 `webview-profile`、`temp`，导出位于 `exports`；日志/锁保留至正常退出确认。卸载前正常关闭并确认进程结束，先备份工作数据与导出，再移除解压目录；不清理其他目录或系统设置。

本包的窗口、页面像素和目标机Win11尚未验收，不能称正式成品；后台合成SQLite通过不代表正式PG、真实模型或任意自然目标通过。旧Linux候选保持不变。后续普通原EXE窗口验收单列测试提交与证据，不能倒改此原始构建记录。

## 后续同包独立窗口验证（不改ZIP）

本包后续已在[run41328886324](https://github.com/T1doo/Sim2Act/actions/runs/41328886324)实际启动原EXE两次，UIA登录、真实前台窗口截图、同origin/principal数据目录、两次完整退出回执和无锁重开通过；使用系统已有WebView2，无浏览器回退。窗口1024×690，宿主Windows Server2025，合成空白SQLite，模型调用0。上文“尚未验收”描述的是原始装配终态，后续新增的窗口登录/关闭重开证据见`docs/evidence/windows-full-package-20261101/window-attempt-2/`，ZIP及原始manifest保持原字节。

解压后双击原EXE；合成工程页面显示公开测试令牌 `public-synthetic-blank-workspace`，在“本机访问令牌”输入后点“连接”。这是已明确标记的合成工作区，不是真实用户账户口令。窗口内业务保存/导出点击、Windows11、PG和真实模型仍不可扩签；普通后台CSV30/v1、15/v2是独立后台入口验收。
