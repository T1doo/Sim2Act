# 当前Windows独立宿主：实际编译与静态验收

宿主输入源码：`7bf6fd84fd694efe8348e1b565b01ad2e0765c40`；构建脚本与工具锁：`f471cad2897598b056ba0dc8ef613a5510440b25`，仍在`dev/cloud-g0-live-20261028`。本轮只做原云环境常规构建，未修改应用Python／C#业务代码、main或Release。

## 实际结果

原WinForms/WebView2宿主已实际编译，三次compiler均退出0且stdout／stderr无编译错误或警告。不是仅语法分析或事先写入成功状态。独立首编与可复现脚本编译的EXE相同；脚本在不同输出目录中的EXE及组件ZIP也逐字节相同。

| 工件 | 字节数 | SHA256 |
| --- | ---: | --- |
| Sim2Act.exe | 26112 | `05e3624dcaa3045ce848a4c2e48d3bde563503d6e9baa922907c1aee38d786a5` |
| Sim2Act-desktop-host-7bf6fd84fd69.zip | 285352 | `80d324804cc42fc32d082501d57a1049b819937bff0048a1024dba0e9b6a3061` |

实际文件见[宿主工件](../../../deliverables/windows-host-cross-20261101/README.md)。ZIP全部11成员与manifest精确库存、大小、摘要核对；实际C#和嵌入manifest逐字匹配7bf Git blobs。原生`file`／`objdump`及只读独审核到AMD64、PE32+、Windows GUI、CLR ILONLY与非空托管入口；CLR metadata v4.0.30319，BCL AssemblyRefs为4.0.0.0与固定WebView2 1.0.4314.35，不引用System.Private.CoreLib或.NET8目标程序集。嵌入manifest与原文件完整相同，含asInvoker/uiAccess=false。

## 工具和可信来源

原环境无dotnet／csc／mono／pwsh；在工作区临时目录准备了Microsoft官方Linux.NET8.0.33运行时（仅运行编译器）、Microsoft.Net.Compilers.Toolset4.11.0与Microsoft.NETFramework.ReferenceAssemblies.net462/1.0.3。运行时按官方发布元数据SHA512核验，两份NuGet按官方catalog的大小与SHA512核验后解包，保留来源、哈希、选择记录、实际下载日志和准备脚本。没有全机安装、改系统设置或新凭据。

目标引用全部来自net462参考程序集及固定SDK的`lib/net462`，`/noconfig /nostdlib+ /target:winexe /platform:x64 /langversion:5 /deterministic+`；不是把Linux.NET8程序重命名成EXE。既有WebView2 SDK1.0.4314.35原包9818548字节、SHA256 `90778deb1b77e36292828b4b5833c9255c27533f40e0ddd55891ae718944edc4`，解出SDK两程序集、x64 loader及许可。205项实际工具文件的精确库存、大小和SHA256固定于[`cross-build-tools.json`](../../../scripts/windows/cross-build-tools.json)。

官方来源：[.NET8下载](https://dotnet.microsoft.com/en-us/download/dotnet/8.0)、[Roslyn工具包](https://www.nuget.org/packages/Microsoft.Net.Compilers.Toolset/4.11.0)、[net462参考程序集](https://www.nuget.org/packages/Microsoft.NETFramework.ReferenceAssemblies.net462/1.0.3)。这套编译工具仅用于本次受控构建，不作长期生产运行时方案。

## 实际命令与普通离线验证

源码仓库中执行：

```sh
.venv/bin/python scripts/windows/Build-CrossDesktop.py \
  --source-commit 7bf6fd84fd694efe8348e1b565b01ad2e0765c40 \
  --tools /workspace/scratch/sim2act-desktop-cross-tools-20261101 \
  --sdk-package /workspace/scratch/microsoft.web.webview2.1.0.4314.35.nupkg \
  --output /workspace/scratch/sim2act-desktop-cross-build-v2-20261101
```

脚本从指定提交读取真实Git blobs、核对全部工具和SDK、创建新目录、实际调用csc，并保留命令／compiler原始日志／真实退出码；不下载、不运行Windows程序、不派发CI。无原应用后端／数据或安全状态改动。

- v1为首次真实编译，v2为实际脚本，v3为不同输出目录复编；各自命令及真实退出原件分目录保留。`desktop-cross-reproducibility-20261101.json`核对跨目录EXE／ZIP相同以及ZIP成员全量摘要。
- 对已有v2输出重新运行，明确拒绝且全部旧工件摘要不变；向工具目录临时加入一个非可执行库存反例，脚本在创建输出／调用编译器之前拒绝，随后仅移除这个本轮自建反例。没有绕过校验、改pin或覆盖旧产物。
- 原组装／版本绑定36项离线回归通过、0跳过，2.13秒。它不等于Windows进程／UI测试。
- 独立只读审查核实际PE、net462引用、Git输入、SDK、工具清单、ZIP、禁止覆盖和平台边界，未发现mustfix；不替代运行验收。

云盘原仅29MB。为准备工具，本轮将已完成313项通过的临时pytest数据目录`/workspace/scratch/graph-original-edge-final-regression-20261101`完整归档，233普通文件哈希与全部符号链接逐项核对后移除展开副本；原日志／XML保留。可从同路径`.tar.gz`恢复，归档8580302字节及逐文件清单在`.archive-manifest.json`；没有删未知进程／锁、源码、失败原件或用户工程。下载原压缩工具包在核验／解包后仅清理本轮新建副本，实际工具字节与可信来源清单保留。

## 未验边界与最小下一步

本次只编译真实宿主组件，没有拿旧Python或pyd组合，没有创建假的后端来通过构建资格。工件明确是`HOST_COMPONENT_ONLY_NOT_INSTALLER`、`CROSS_COMPILED_NOT_WINDOWS_EXECUTED`。Windows后端仍缺当前同源码的wheel／四枚pyd和完整私有运行时装配；尚未执行本EXE、实际WebView2窗口、页面、关闭或重开。原正常READY、租约续期、提交屏障、同源绑定与退出协议保留于源码，编译结果不能代它们实跑。

原Windows CI累计823／900秒，只余77秒；当前完整原生构建／装配／运行不能可靠限定在此余额内，本轮没有启动第五次CI或更改安全策略。最小后续是另有明确有界预算的标准Windows构建执行：在当前开发SHA编译四枚扩展和wheel，复用固定SDK与已有csc／Runtime组成同源包，再普通执行此EXE并核窗口、保存／导出／停止／重开。只需普通构建／执行范围与预算；不需新token、OAuth、系统安装或安全setter，不自动关闭sandbox，不以Server2025结果替代用户Windows11。若环境或系统要求具体审批，仍须停在该动作并报告，不代点。

## 写锁证据保持分版本

本轮没有应用热路径修改或新大型Cold计时，不声称改善长写锁。既有[实际闭环](../lease-control-final-fence-20261101/README.md)中的两笔源码66f1：G0在写锁前42.572954／45.837719秒，写锁59.493538／64.917686秒，总102.067327／110.756078秒；实际持锁取消的源码5db仍是完整回滚、默认恢复CANCELLED。7bf的单次权威读去重仅约0.34毫秒，不能解决分钟锁。原30秒滚动租约、提交屏障、取消和300秒绝对任务deadline没有扩大或删除；仍存在大任务预算耗尽风险。这些旧结果不改签为本轮Windows／新大型验收。

全部网络仅官方构建依赖，0新增模型调用、0付费fallback、0用户电脑操作，无新凭据／安全权限。当前工具链在工作区即可完成交叉编译，没有向用户泛问安装许可；当前Windows完整实测仍单独受执行环境、预算和具体系统审批约束。
