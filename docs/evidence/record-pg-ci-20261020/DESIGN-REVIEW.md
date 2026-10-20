# 一次临时 PG CI：有限设计独审通过

已核精确冻结四文件 SHA256（见 final-review.json），无未解决 P1/P2。未编辑代码、未执行测试或 CI。

此前发现的 cleanup 解释器、清理失败前公开未脱敏原件、SQLite 专属屏障误列 PG 节点、port 链式比较及父进程退出后 Node 管道孤儿五项均已修正。当前明确为原 11 中 10 个 PG 兼容节点，加指定原内容更正节点通过后的同库停止/重启 oracle；SQLite row-cell 屏障仍保留原范围，不降低断言冒称 PG 通过。

认可一次指定 marker push 的执行边界：仅本 repo public、当前 dev、run_attempt1、标准 windows-2025、15min；初始 owner 仅为独占临时集群和 schema 建表/授予 CRUD，实际 API/Worker/冷池均为非 super/createdb/createrole/replication/bypassrls app role；仅 loopback。测试 300s 看门狗，child finally 与 parent timeout 均限制自身后代并核回收。

清理 always 使用已安装 venv；仅对 owned cluster 执行 pg_ctl stop/status3，再删整个 root、密码及配置。证据先按已知秘密脱敏并封 hash，report 必须先核清理/脱敏成功和文件 hash，才输出上限 2MB 的压缩日志原件；无 artifact 上传。

run_attempt1 只阻止同一 run 重试，并非跨 push 的持久一次性消费锁。因此本结论仅认可用户已授权的一个指定标记提交；不得复用标记或另发第二次标记 push。真实 PG/Windows 结果与实际清理均仍 NOT_RUN，待唯一 CI 原件判定；不得预签成功。
