# 因果修复后单次重试：有限设计独审通过

精确三文件冻结 hash 已核，见 final-review.json。无 P1/P2 阻塞。原 fixture/conftest hash 不变，产品无 diff。

仅认可父侧已明确复核的一个新 marker 提交 `[record-pg-retry-20261020]`：当前 dev、公有 repo、标准 windows-2025、attempt1、contents:read。不复用旧 marker；新 marker 也不得再用，不允许第三次执行。此标记不是跨 push 持久去重机制。

新 job 上限 600 秒，前次实际 238 秒，两项配置口径合计 838 秒，小于原 900 秒预算；这不是对未来真实运行或队列/控制器开销的预先测量。首个原生步骤写 UTC+450 秒操作截止，各进程转换为 monotonic deadline。setup 在创建 root 前核预算，三个启动工具及连接等待均收紧至剩余时间；连接不足 2 秒拒绝，不向上延长。重启工具同样受操作截止约束。

测试 watchdog 为 min(100 秒, 剩余操作预算−18 秒)，留自身进程树回收与收管道余量，step 120 秒。清理继续独立 45 秒共享预算，绝不受已过期操作截止阻止；cleanup/report 各 step 60 秒，job 10 分钟保持。角色、十节点、同库重启、脱敏诊断、status3/删除门均未扩大。

已只读核作者原始 JUnit/stdout：8 PASS，0 FAIL/ERROR/SKIP，3.639 秒，包含新预算压缩/短连接拒绝及过期 setup 不触 root、cleanup 仍可执行的本地用例。本审查未重复执行。所有验证均为 POSIX Python shim/临时文件，不是 Windows/PG。

原失败 CI 日志 SHA256 仍为 4324db64a8b67e2ff612c40b237ee4d823e5283cfaf99eb5afdafc8d1f05e67d，首次失败与 PG 测试/重启为零的历史不变。当前重试尚未运行；不得预签 PG、受限角色、重启或清理成功。本审查未编辑仓库、未执行数据库/CI。
