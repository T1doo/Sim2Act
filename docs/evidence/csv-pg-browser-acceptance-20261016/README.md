# CSV PG / 真实浏览器前置检查原件

检查源 `f82869db2dbb53e1616f9c14b108696bb893662f`，普通开发分支 `dev/csv-pg-browser-acceptance-20261016`。本轮结果 **BLOCKED**；四步产品流程均 **NOT_RUN**，不累计历史或替代环境的通过数。详见 [报告](../../F2/CsvPGBrowserAcceptance20261016.md)。

- `environment-preflight.json`：实际 11 个只读命令的 argv、cwd、returncode、stdout/stderr，以及环境变量存在性（不含值）；各 `preflight-00.log` 至 `preflight-10.log` 是对应命令 stdout+stderr。
- `protected-browser-prerequisite.cjs`：本次一次性前置启动脚本原件，只打开 about:blank（本次未能到达），没有产品数据或替代 executor。
- `browser-prerequisite.json`、`browser-launch.log`：真实 Chromium 一次启动的原始结构化回执和 stdout/stderr，RC1、SUID 配置阻止、SIGABRT；未修改安全配置、未重试。
- `browser-execution-receipt.json`：实际 exec/write_stdin 工具返回值的明确转录，保留 session40326 最终 exit_code1；不是再次执行或独立操作系统 argv 捕获。
- `browser-process-postflight.log`：本次启动后只读进程状态；保留两条 STAT Z，不声称进程条目清零。
- `source-integrity-and-scope.json`：祖先与产品零差异检查、相关源文件 SHA256、四步 NOT_RUN 和本轮执行数量。
- `independent-review.md`、`independent-proof.json`：独立只读审查；独审未启动数据库/浏览器、未执行产品测试。
- `SHA256SUMS`：本目录上述证据文件逐字节校验，不包含自身或此索引。没有数据库、配置、令牌或凭据。

前置资源事实：无已配 PG DSN、无现有 PG 镜像/容器/本机服务可复用；真实浏览器保持沙箱启动被环境中止。未创建 PG 服务、下载镜像、安装依赖、新建凭据/角色、降低沙箱、调用模型或触发 CI。代码与原始候选包未改动。

`environment-preflight.json` 中 `earlier_read_denials` 是最初工具输出的情况记录，不是后来重新读取该拒绝路径的结果。没有访问绕过或待审批动作。
