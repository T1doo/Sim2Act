# 本地诊断与共享清理预算：有限最终独审通过

精确 runner SHA256 `2ce638593d97dbf60800fa1f1cffc75c162e402871066d70d32dc9a783b44781`，测试 SHA256 `a2b604dcbf96d6681f5ef076619dc1677f89ae7300567d6b7f9dfbf6cd2b0a9a`。当前无剩余 P1/P2。

诊断只读取 postgres.log 和严格命名工具 stdout/stderr 普通单链接文件，拒绝 symlink/reparse/hardlink；最多 8 文件、每文件读取 4097 字节、扫描 64 目录项、最终 JSON 262144 字节。截断及未以换行结尾的半行不输出；已有四个 cfg 秘密、内存秘密、PG URI 和长 hex 被替换。private.json 与密码文件不是诊断输入；既有配置读取仍仅用于停库控制与取得已知脱敏值。首个 timeout/exit 已写输出保留，清理 finally 在删除前另存有界脱敏启动快照。

kill 等待、初始 status、可选 stop、最终 status 使用同一 45 秒 monotonic deadline；单次 status ≤5 秒、stop ≤35 秒并保留最终 status 5 秒，开输出文件后再次核剩余预算。原 workflow 清理 60 秒、job 15 分钟不变；约 15 秒文件归档/删除余量是预算设计，尚非 Windows 文件删除实测保证。

独审发现的 P2 已修复：缺失 PG_VERSION 标记现在拒绝工具调用、删除与 PASS，并仍保存诊断。对已初始化集群，最终 status3 必须成功才进入删除/PASS；预算耗尽或未证 status3 都保留失败边界。

已只读核作者最终原始 JUnit/stdout：6 PASS、0 FAIL/ERROR/SKIP、3.408 秒（stdout 3.41 秒）。实际为本地 POSIX Python shim 与临时文件，覆盖 timeout 输出脱敏、凭据/链接禁读、日志边界、共享 deadline、慢 stop、耗尽后不再启动进程及未初始化 guard。未由本审查重复执行。

产品、workflow、权限 fixture 未改。原失败 CI 日志 SHA256 仍为 `4324db64a8b67e2ff612c40b237ee4d823e5283cfaf99eb5afdafc8d1f05e67d`；原 PG 测试 0、重启 0 不变。当前修复不认证 Windows/PG；不得借普通 skip-CI 推送触发新 CI/数据库。未编辑仓库或运行任何数据库/CI。
