# 实际 CI 失败与最小适配器修复：有限最终独审

唯一 run 39367188323 / attempt 1，精确源码 ba5c6d107acdcd42b89a219c49882b113fae5739，结论 failure；job 238 秒，setup 120 秒超时。原 trace 明确 pg_ctl start 的 35 秒 TimeoutExpired 后进入无 timeout communicate / stdout reader-thread join，最终 KeyboardInterrupt。日志支持输出管道保留等待，但没有具体持有句柄的 PID 或 PG readiness 证明。17/bin 仅为路径，没有完整实际 PostgreSQL 版本输出。

目标 DB、受限 app role、role 测量、schema CRUD 授权、DOM 工具、10 项 PG 测试和重启 oracle 均未到达；实际 PG 测试 0、通过 0、重启 0、JUnit 不存在。此前 SQLite 和设计独审不能代签本次 PG。

cleanup.json 303 字节已由本审查从原日志 base64/gzip 独立解包，并与 actual 文件及 manifest SHA256 逐字验证。证据仅证明最终 pg_ctl status3、整个 owned root/cluster/密码/配置删除。未记录清理前是否 running，也不能声称 stop 命令曾必要或成功执行。

原日志 72973 字节，SHA256 4324db64a8b67e2ff612c40b237ee4d823e5283cfaf99eb5afdafc8d1f05e67d。数据库凭据 URL、未遮蔽 Bearer/GitHub/JWT、password 赋值及 add-mask 原值的有界模式扫描均零命中；唯一 64hex 为 cleanup manifest hash，checkout 认证已遮蔽、模型 token 值为空。可按原字节封存；这不是所有秘密形式不存在的证明。

此前静态独审遗漏 pg_ctl/server 后代继承 stdout PIPE 句柄这一真实场景；此前有限设计通过意见不能继续作为启动方案已就绪的依据；它原本也没有证明运行通过。本审查明确承担这一遗漏，不把它改写为已预见或已测通过。

最小修复仅 scripts/record_pg_ci.py 的 tool()，SHA256 53a1444970e857448ec2c1170e3974617da8cff905c03bdfea98a3d1354812da：stdin DEVNULL；stdout/stderr 改为 owned root 内随机普通文件；保留默认 35 秒上限和原 str 返回接口；临时文件在停库后的整体 root 清理中删除。未发现本补丁 P1/P2 阻塞。它针对观察到的 PIPE EOF 等待机制，不是 Windows/PG 修复已通过的证据。

本地适配器脚本/stdout 仅有原工具记录的事后转录，明示该边界，未补跑。其实际 Linux Python wrapper 0.016 秒返回和 0.2 秒 watchdog 有界结果，只认证该本地进程适配器；不认证 Windows 句柄或 PG readiness。

唯一执行许可已消耗，不得重用 marker、重跑或触发第二次 CI。本审查未编辑仓库、未运行数据库/CI。后续若要实际验证完整版本、角色、十节点与重启，仍需新的明确授权；本次失败和原 G0/PB/Win11 门保持。
