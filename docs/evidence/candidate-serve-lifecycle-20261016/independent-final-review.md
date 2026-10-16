# Candidate 原 CLI 完整启停：独立只读复核

- 诊断冻结：`797894987a62c4ca603256d7049a5529e2a79b3c`，分支 `dev/candidate-serve-lifecycle-20261016`。
- 候选执行源：`fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675`；既有交付基线 `8875c225561e23d432934599531bbd3e740daa3a`。
- 结论：在本次 Linux / SQLite mock 已有成果只读 serve 范围内，最终 attempt-2 的完整启停证据成立，未发现剩余阻断。该结论不修改旧失败、旧退出码未知或旧自然 Run 原因未知的结论。

## 复核范围及方法

本独审只读生产/诊断源码、Git 对象、原始日志/回执、包、候选数据文件，以 SQLite `mode=ro` 独立重算所有表的持久行摘要；未发送 HTTP、启动服务/Worker/模型、创建 Run、发信号或重放旧业务。只向 `/tmp` 写独审文件。相对 8875 的已提交变动仅新增 `scripts/diagnostics/local_candidate_serve_probe.py`，原产品、候选 CLI、打包脚本、测试、指南及包均不变。复核时 root 正准备新的未跟踪报告/证据，不将其称为干净工作区。

最终诊断脚本 SHA256：`4398b169884f65836a119e49008d54580436e482064019626f63578381fc5fd5`。相对首诊断冻结 9346，仅收紧端口检查：记录实际 errno，只有 `ECONNREFUSED` 可证明关闭；0、权限拒绝、超时及其他错误都阻止 PASS，无升级或重试。

原 CLI 由 Popen 直接执行候选 venv Python 的 `-u -X importtime ... local_candidate_demo.py serve`，没有 runpy 或替换执行入口。亲进程持有 child，双 reader 持续 drain 并记录异常。就绪须是认证 `/api/projects` 200 且匹配项目。成功 HTTP 响应的观察时间须在 60 秒窗口内；同步 HTTP 超时不是绝对硬取消，报告准确声明该限制。SIGINT 后真实 wait，任何 terminate/kill fallback 或日志/端口/快照异常均禁止 PASS。

## 最终 attempt-2 原件核验

原件目录：`/workspace/serve-complete-acceptance-20261016/attempt-2/`；执行声明 `execution-command-2.json` 和实际父命令输出 `probe-2.log` 位于其父目录。

- 子进程 `32310`：真实 `Popen.wait` 退出码 **0**；SIGINT 到 wait 返回 **0.617501299 秒**；无 fallback。
- 端口关闭：实际 errno **111 / ECONNREFUSED**，未将其他不可连接原因误计为关闭。
- 认证项目 GET 就绪：spawn 后 **3.833915269 秒**。`-X importtime` 的 721 行只提供导入耗时和父接收时间上界，不声称子进程绝对导入时刻或既往超时根因。
- 就绪之外 **10 GET 200**，含 NATURAL_PA 目录、同实例 v1/v2 结果及人工验收入口、两个成果的精确版本及 SHA256；**1 POST 405**。HTTP 成功观察阶段 **19.549311997 秒**，在声明窗口内。
- JSONL 全部事件有序，逐 stream 内容与原 stdout/stderr 完全重建一致；reader、finally、port、snapshot 错误均无记录。
- 独立重算全部 **48 张 SQL 表**的 schema/持久行摘要、全部 **11 个数据文件** hash，与 before/after 回执一致。Run 数 **4→4**，没有 Worker/模型/新自然 Run。
- 表摘要 `b74e2ae31bcd568177a4a2b1ff21d322e0ead572fed369e18883a815e032b4e9`；数据库文件 `32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780`。
- 已交付 fc69 ZIP 仍为 `0ff78bc7330bcbbd5cc2a9fff76bb3cd2d2cd4e9ec37a3a0e1873acd50c74507`；manifest 仍为 `6dda3942d9e6f20d6c89fa8b5444262362912159887301aa23563eab8fb35993`。

## 分期证据及限制

首诊断 attempt-1 / 9346 的运行回执为 PASS、child wait0，但未记录严格 errno；原件保留，不能替代本次最终完整验收。两次旧 15 秒外部探针仍为 FAIL，日志 hash 与前次审查相同。旧 TTY 直接启动曾完成 HTTP 验证，包装进程 exit1、后续 pidfd 停止自有 child 的真实退出码仍不可获得；此次新的可 wait child 退出0不追溯改变旧结论。旧 `/proc` EACCES 没有重试或升级。

首包 0f 的 PA Run 异常原因仍未知，原失败 DB hash 仍为 `bf2293cb3d5f96d9a054596d7e1cccd9905e1088f69620e9fc4e2989375b1d4c`。本次不产生新的自然业务证明，也不将既有 fc 单 claim 的 PA v1/v2 成功描述为自然恢复分支验证。旧 F9 未自然复现，旧磁盘满未落盘独审缺口不变。Windows、PG、真实模型/语义、人类最终验收、远端 CI、部署均未执行。

## 独立文件

- 核验器：`/tmp/f2-review-serve-complete-attempt2.py`，SHA256 `bfba39d61472723ff06fbde1a25516a2a951a6d470e0c0721a737fabc21a2ace`；实际只读执行 exit0。
- 机器可读证明：`/tmp/f2-serve-complete-attempt2-independent-proof.json`，SHA256 `fb8480a4b5d1dc4233747170c3df72a00beebcfbb9370a82dccebf1c5e611c73`。
- 机器证明包含最终四份原件 hash、执行命令/父日志 hash、已交付包和旧失败原件的逐项保留比对。
