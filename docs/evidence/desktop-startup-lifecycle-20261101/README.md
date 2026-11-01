# 桌面重开、异常退出与当前安装包

应用源码：`7bf6fd84fd694efe8348e1b565b01ad2e0765c40`，开发分支 `dev/cloud-g0-live-20261028`。本轮只使用原云环境，0 模型调用；没有 Windows 执行、用户电脑操作、新 CI、main 修改或发布。

## 实际产品修复

正常 `synthetic-workspace` 原先先执行 `Worker.once()` 再发送 READY。重开已有排队任务时，大型工作可能先占满桌面30秒启动窗口，界面尚未显示便被宿主请求停止。现在先注册实际worker并等原Uvicorn完成启动，发送真实READY后才第一次dispatch；原Worker、SQLite事务、取消、STOPPED和双EOF没有替换。

WinForms/WebView2宿主源码新增：READY关联实际数据目录、principal及保存的origin；stdout/stderr各自有界排队，stderr不能提供协议回执；实际Completed才提示导出完成，目录／COM异常明确报错；日志写入失败按原停止协议收口；没有READY且非用户主动关闭的退出不再误记成功。导出、提前退出异常分支经独立只读审查，未发现剩余mustfix，但当前C#没有编译或Windows运行证据。

装配脚本从同一候选manifest核对并带入两份实际使用指南，修正解压目录中的构建路径，补齐便携退出／保留工程／移除范围。没有新桌面框架、浏览器回退或系统运行时安装。

## 验证及版本边界

| 场景 | 实际结果 | 字节／平台边界 |
| --- | --- | --- |
| 新进程重开已有排队CSV | READY先于第一次原Worker.once；真实HTTP读取并等既有Run成功，EOF正常停止 | `queued-ready-process.log`，4项5.10秒；PEP669只观察一次入口，不替换业务函数或虚拟时钟 |
| 相关Python／装配回归 | 61项通过、0跳过，26.30秒 | `runtime-source-tests.*`；受测Python与7bf源码完全相同，之后仅有C#异常分支修改，不签C#执行 |
| 当前wheel安装身份 | 194项已安装源码／资源逐字节核对，4个Linux原生扩展实际导入并匹配wheel | `installed-identity.json`；Linux x86_64 CPython3.12，非Windows |
| 安装后原生协议回归 | 19项通过、0跳过，1.01秒 | `installed-native-tests.*`，在隔离安装环境、源码目录外启动 |
| 安装后正常CLI／HTTP | CSV=30/v1；原键同Run；SIGINT后STOPPED/clean、实际exit0及双EOF；首次新进程回读同结果；再次原键不重放 | `installed-cli/report.json`及原始输出；默认0模型、合成SQLite。普通CLI随机origin按每次READY进入，不能冒称WebView2稳定origin实测 |
| 不支持的自由目标 | FAILED/UNSUPPORTED_CAPABILITY，同键不另建Run，重开仍失败 | 同一实际CLI，不改状态假成功 |
| 隔离卸载 | 只移除此环境的应用，三份工程文件摘要不变；抽查共用FastAPI／SQLAlchemy字节不变 | `uninstall.*`；没有删除工程或卸载共享依赖 |

首次安装命令误用了不存在的`wheels/`子目录，pip退出1且未安装，原件保留于`failures/install-wrong-wheel-path.log`；随后按构建实际输出路径安装通过，见`install.log`。中间0c43包仍仅在scratch保留，不扩签为最终包。没有抹去失败或在未知进程上重启。

## 租约检查的小范围去重

`Runtime.lease`先拒绝陌生row／context，再取得精确已发行Session，由`Session.check`完成一次鲜活控制库读取；header、marker、owner/version/fence、intent、stop、schema、文件身份及双钟仍检查。其他`Runtime.session`调用不变。独审核过覆盖关系，foreign getter反例和原取消／过期／旧owner等测试保留。

真实文件SQLite配对按old/new/new/old各30次：连接60/30/30/60；墙钟0.028035／0.019433／0.017616／0.029511秒。每次仅节省约0.34毫秒，不是大图端到端计时，不能声称已解决分钟写锁。本轮没有重跑两笔大型Cold或真实Intern，既有大型保存／持锁取消／live结果仍分别绑定[前轮源码](../lease-control-final-fence-20261101/README.md)。新包小型验收不能改签旧大型成绩。

## 明确剩余项

当前云环境没有dotnet、csc、mono、mcs、pwsh或wine。现有固定WebView2 SDK归档可用且API成员已核，但缺能实际编译、运行当前四扩展及宿主的受支持Windows执行环境；旧Windows EXE不能作为当前软件。已有CI预算累计823/900秒，只余77秒，本轮未另触发Windows运行。最小后续动作是在有明确预算的Windows构建环境，用当前精确源码生成Windows wheel／4枚pyd，组装同版本便携目录，再用既有csc和固定SDK执行`desktop-build/Build-Desktop.ps1`，补真实窗口保存／导出／关闭重开及异常验收；无需新凭据或安全setter，仍不能跳过系统审批。

约一分钟写锁及300秒任务预算风险仍存在，没有提高30秒租约／绝对deadline或削弱提交屏障。正式PG仍缺既有数据库连接和实际业务principal/project/trial/approval选择；本轮不造凭据。原免费Intern token配置仅核ready布尔，0次新增真实请求；旧小文本live成功不代表当前Windows／大型live／任意自然语义通过。

当前包、摘要及安装／移除范围见[内部Linux限制候选](../../../deliverables/desktop-lifecycle-local-20261101/README.md)。它不是最终桌面成品或Release。证据中只有本轮生成的合成项目、公开测试身份和合成结果；未复制数据库或凭据。`files.json`固定原始文件摘要，包保持构建时状态，不改写为已整体验收。
