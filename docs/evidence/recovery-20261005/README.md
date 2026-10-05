# 新任务恢复记录

2026-10-05；用户授权从上传包迁移四个未推提交，保留旧任务及 work 分支。附件说明作为技术参考，执行授权来自用户。

恢复包 Sim2Act-dev-f1-foundation-228b0f7-recovery.zip 为708334字节，SHA256 b1c579bd01a20e62dad554c4c56da0ac6120f0ebefb7ef678c65512f651023d3，与交接值匹配。四个补丁及157个head文件哈希均通过，恢复后157个包含文件字节和Git mode全匹配。备份排除文件未被覆盖，不声称这些文件经过包内比对。

独立工作副本 /workspace/Sim2Act-f1，分支dev/f1-foundation，基线df31fe9b4d4b27db601581cf9763a18d5f0f6366；原 /workspace/Sim2Act 的 work 保留在6f688e4dd80b5c81d41aecde90e360d3629f9c21。包不含原commit objects，恢复产生新SHA，不声称复现原HEAD。

| 原提交 | 恢复提交 |
| --- | --- |
| 6145bb8 | 0ffb957 |
| 8f7bbbe | c57fec5 |
| e171182 | 8d812c2 |
| 228b0f7 | 42b377897c1fe501772a5b0a12973c8845c6361c |

各补丁先git apply --check，再依序应用提交。30个Python文件语法编译、node --check src/sim2act/web/app.js、git diff --check通过。当前Python无pytest、原工作区无项目venv，SQLite/PG回归、真实子进程及浏览器功能复跑NOT_RUN。历史测试证据保留，不当作本环境结果。

此前本任务fetch已确认远端基线；恢复前再次fetch失败，退出128：Failed to connect to proxy port 8080 after 0 ms: Could not connect to server。无CONNECT/源站HTTP状态，不能确认当前远端仍未变化或推断认证拒绝。未修改代理/身份/凭据/网络权限、改通道或新增登录。

正常阶段push已授权；当前远端复核阻塞，push及精确commit Windows Server CI未执行。后续先正常fetch、比较远端及恢复分支；未知变化先核对，禁止force/reset用户内容；再正常push并监督同提交CI终态。新环境公开GitHub/API成功仅代表此前检查时状态，不证明当前写权限。

静态复核：CSV仍为固定可信模板的PREVIEW/不可发布，候选/材料/输入验证、用户/项目/应用授权交集与历史幂等逻辑保留；application_environment仍显式白名单，LIVE明确开启才传应用token。此核对不替代专项执行。真实模型请求0、预算0；Win11/完整AT-02/独立审计、F1签收及F2正式准入未通过。本轮仅恢复既有并行工程。

## 正式执行器审批后续验证

上述默认模式阻塞已通过正式require_escalated审批核对：同一origin的ls-remote与fetch均批准并成功，远端仍df31fe9，与恢复分支保持祖先关系。未改变保存环境、代理或身份；默认执行器网络restricted与保存环境连接能力需分别报告。依赖安装审批成功，按requirements.lock精确安装，pyproject固定setuptools82.0.1，no-index/no-deps/no-build-isolation editable安装及pip check通过。

默认沙箱TestClient执行停滞，已终止本任务该测试进程；经正式审批本机socket/IPC回归后，SQLite123PASS/2PG-only SKIP/1已有Starlette警告，7.47秒；JUnit见sqlite.xml。ruff通过，mypy14模块无问题，CSV11专项和两个真实配置子进程用例包含在该工程回归。无本机PG工具，不虚报PG权限/生命周期两项通过；Windows将按正式CI验证。真实模型请求仍0。下一动作：正常push恢复开发分支并监督精确commit Windows Server CI。

## Windows Server最终结果及修复

精确源码055559344430cfbfdc5eaa9aca09a22db6bdf8c8/[run37315778872](https://github.com/T1doo/Sim2Act/actions/runs/37315778872)，job111782032859，SUCCESS/1m43s。Server2025Datacenter/build26100、镜像20260925.250.1、PowerShell7.6.6、Python3.12.10、PG17.11、管理员上下文true/EnableLUA1；完整依赖锁与pip check、原生运行角色DDL拒绝/API-worker隔离/六脚本/重启回读、ruff/mypy14模块、PG126PASS/0FAIL/0SKIP（28.11秒，1旧Starlette警告）、Report/Cleanup全通过，PG server stopped。包括CSV11专项、owner环境隔离回归及新增真正Windows PowerShell输出/退出码专项。windows-run.json为实际读取的job/steps；windows-results.json及windows-source-hashes.json为脱敏上下文/结果和精确源码指纹。读取使用既有授权GitHub身份，未读取凭据或登录。

前三轮失败run37314684783/37315070121/37315380735保留，Setup/Report/Cleanup成功，smoke失败、工程回归跳过。隔离Python本体及同应用角色SELECT1已通过，PowerShell调用native LASTEXITCODE为空。定位并修复最小系统白名单遗漏PATHEXT；[微软环境变量说明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-7.6)指出未列入的扩展会另开控制台执行，与缺stdout/退出码现象一致。仅补PATHEXT，不继承测试owner/CI凭据；新增Windows原生测试确认同步输出及退出码。Linux重跑123PASS/3SKIP（2PG-only+1Windows-only）/1旧警告，7.33秒，sqlite-pathext.xml保留。此前sqlite.xml保留初轮123PASS/2SKIP。

网络及依赖初期阻塞已经通过正式执行器审批解除，普通push实际成功，故原身份写能力已验证。未更改保存环境/代理/网络策略、关闭保护、force/main merge、部署、使用收费runner或请求真实模型。最终证据仅文档提交，不需要重复CI；测试源码以0555593标识。Win11普通用户原生体验、多平台浏览器最新复测、完整AT-02及独立签收仍未完成，F1整体不标ACCEPTED，F2正式门仍未放行。
