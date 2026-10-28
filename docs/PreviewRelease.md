# Sim2Act · 当前合成工程桌面候选

本候选保留已认可的紧凑工作台、资源、目标卡、应用、实例及持久结果流程。精确应用提交与文件摘要以 `candidate-manifest.json`、`portable-manifest.json` 为准；桌面 EXE 和 SDK 摘要另见 `desktop-manifest.json`。构建、实际运行、业务验收分别记录，不互相替代。

## 桌面入口

完成 Windows 构建后，双击 `Sim2Act.exe`，显示独立窗口及任务栏入口。原后端实际 READY 后才显示工作台；关闭窗口通过私有控制管道请求原停止路径，核对同 worker 的 STOPPED、子进程真实退出和输出 EOF。失败保留数据与日志，退出未知保留运行锁，不强制终止或删除锁来重试。

新装配 ZIP 当前是桌面构建输入，状态为 `NATIVE_HOST_BUILD_REQUIRED_NOT_WINDOWS_EXECUTED`，尚未含新 EXE；须由维护者按照 `desktop-build/README.md`，用已有编译器、固定应用 SDK 和已有 WebView2 Runtime 在新候选目录构建。未构建时入口明确报缺项，不打开浏览器。最终交付须补当前 EXE 的实际 Windows 窗口、操作、关闭和重开数据证据。

依赖 Windows x64、已有 .NET Framework 4.6.2+、已有 WebView2 Runtime、Windows UCRT；不自动安装系统组件，不绕过安全拒绝。`Developer-Browser-Preview.cmd` 仅供显式开发预览。旧 Chrome 包及其截图属于旧版本，不是当前桌面软件验收。

## 本地数据与功能

将完整包解压到新的普通目录，不覆盖旧目录。使用公开合成身份 `public-synthetic-blank-workspace` 登录，只输入无隐私的合成材料。项目、资源授权、目标卡、应用与实例的审批和版本确认继续走原流程。`workspace data`、`webview-profile`、`temp`、`exports` 和日志位于应用目录；不能承诺操作系统、Defender 的系统记录绝不出现在目录外。不要复用公开合成身份处理真实项目。

已有 Windows 8210 源码回归通过两个全新进程的 P-A prepare/verify，使用5次固定 Mock，保留两份新材料及冷读结果；这不是新 EXE 或真实模型整链验收。当前宿主后端的真实 READY→控制管道 EOF→原 STOPPED→数据保留在云端已验，原生 Windows 窗口仍待实测。

## 模型、保存链与剩余边界

固定免费 `intern-s2` 与原 Intern endpoint 已有可信账户来源和有限执行门，用户零费用授权有效。已有真实提取成功记录，和 Mock 完整结算证据分开记载。本包不含 token，不自动打开 LIVE，不以合成身份代替正式主体。

已封存 B2/9a 工程链使用7次有限 Mock、真实 SQLite 事务保存成功；两次 Cold 事务118.04/115.48秒接近其明确120秒界限，旧30秒条件未通过。新的拥有数据计划候选默认关闭，最近整链因120秒边界回滚，不能替代原通过版或声称稳定性已修完。详见 `docs/evidence/cloud-frontier-structure-20261028/README.md` 与新候选证据。

正式外部执行仍缺实际 PostgreSQL应用角色配置、选定 principal/project/trial 及对应精确软件、材料、预算审批；不凭空建立凭据或部署。完整真实模型链、正式 PG、自然语义和 owner 人工验收尚未完成，正式发布继续关闭。

包不含用户数据库、私人设置或模型凭据。保留 Python 与依赖许可证；运行库原件见 `THIRD-PARTY-SOURCES.json`，桌面 SDK 来源与许可证另随构建记录。已锁定 Python3.12.10 已被后续版本取代，此工程候选不能据此认定长期生产部署完成。
