# 普通开发分支集成

起点dev `66709612d5acd2e4b0dc41f75ef5c9f769508b0c`，产品/测试冻结 `fdc91282b2107164ba33624246be6f50e007cd13`，独审 LIMITED_PASS。候选 `dev/local-csv-file-entry-20261010` 最终普通推送到 `41957e3b544f28f520139e3993ac60c0567674a3`；其中首证据提交c5929cd8后，使用普通后续提交保留14份独立CRLF CSV，未改原白名单hash或产品。候选远端逐SHA核对通过。

集成前正常fetch并核对远端dev仍66709612、main仍 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`；切回 `dev/f1-foundation`，以 `merge --ff-only` 从667快进到41957e3，未改main、不强推、不部署。该集成沿用精确冻结作者SQLite26PASS/1PG角色SKIP和PG27PASS、3实际旧源码升级、独审8新场景9实际HTTP页201检查及原667负对照，不重复跑字节相同的测试。

快进前后352运行/测试文件同时与工作区和Git blob逐SHA256匹配，68产品文件仅app.js/index.html相较基线变化；独审114白名单、作者81白名单均核对工作区及Git blob原件。只在快进后添加本集成说明与字节回执，不改产品。

最终普通开发推送、远端dev/候选/main精确SHA、全部祖先、无未推送差异和自有PG清理核查由私有 `/tmp/sim2act-resource-file-20261010/remote-verification.json` 记录，并由最终交付回复返回完整SHA。最终HEAD自身SHA不嵌入该提交的文本，避免自引用；当下GitHub分支历史可直接核验。

已知零字节codex-index-refresh.lock原样保留，未删除未知锁。作者所有测试/HTTP线程结束，独审自有线程与Node退出；自有PG最终schema/role/public0|0|0，正常stop/rm-v后容器与卷不存在。完整初始失败与独审harness三轮失败均保全，字节归一问题记录于FailureLedger。

LIVE=0，PROJECT PENDING/BLOCKED_PARTIAL，semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、正式发布关闭。PG resources-history历史超时OPEN；其余HTTP200坏响应/入口、逐item历史map、页重载后持久UNKNOWN/有效形状ID完整证明仍有范围限制；Windows900/Edge240/Node150未验收。下项离线业务切片可评估已有固定CSV DAG的内部版本/实例/冷运行复用合同；完整真实模型、用户材料、owner/semantic、原生环境和R0仍是剩余关键路径。
