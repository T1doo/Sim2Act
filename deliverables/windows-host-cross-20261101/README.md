# Windows宿主实际编译工件（非完整安装包）

宿主源码：`7bf6fd84fd694efe8348e1b565b01ad2e0765c40`。构建脚本／工具锁提交：`f471cad2897598b056ba0dc8ef613a5510440b25`。

| 工件 | 字节数 | SHA256 |
| --- | ---: | --- |
| `Sim2Act.exe` | 26,112 | `05e3624dcaa3045ce848a4c2e48d3bde563503d6e9baa922907c1aee38d786a5` |
| `Sim2Act-desktop-host-7bf6fd84fd69.zip` | 285,352 | `80d324804cc42fc32d082501d57a1049b819937bff0048a1024dba0e9b6a3061` |

这是对原WinForms/WebView2代码的真实编译，不是Chrome／Edge浏览器包装、设计图或预置失败页面。编译退出0、无错误或警告；PE为AMD64／PE32+／Windows GUI／CLR托管入口，目标引用.NET Framework4.6.2，嵌入原asInvoker/uiAccess=false manifest。不同目录复编的EXE与ZIP逐字节一致。

组件ZIP含真实EXE、固定WebView2 SDK DLL和许可、原C#／manifest、逐文件摘要与编译日志。它只供维护者与**同一应用提交**的完整Windows后端组合，不含私有Python运行时、当前Windows wheel／四枚pyd或系统WebView2 Runtime。没有创建假Python.exe来满足装配检查，也没有替换业务后端、安全门、READY／STOPPED或持久化。

状态是`CROSS_COMPILED_NOT_WINDOWS_EXECUTED`，不是下载即用安装包或已验成品。Linux.NET8只运行官方C#编译器，未运行本EXE；未新增Windows CI、用户电脑操作、系统安装、凭据、权限或费用。实际Windows窗口、任务栏、任务保存、导出、关闭重开及错误处理仍未对当前工件验收。

构建／复编命令、官方来源与校验、离线反例、原生执行缺项及长写锁边界见[完整证据](../../docs/evidence/windows-host-crosscompile-20261101/README.md)。现有Linux已验小型候选保留，没有再生成Linux包或发布Release。
