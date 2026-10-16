# 候选 serve 完整启停验收：2026-10-16

接续已独审交付 `8875c225561e23d432934599531bbd3e740daa3a`，本轮只补原候选 `serve` 完整启停证据。普通开发分支为 `dev/candidate-serve-lifecycle-20261016`；最终探针冻结 `797894987a62c4ca603256d7049a5529e2a79b3c`。产品 src、原演示脚本、fixture、预算/lease/guard 均未修改，没有生成或重放自然 Run。

## 实际完整验收

使用原新安装候选及原 `synthetic-pa-demo` 只读库。探针直接 `Popen` 候选 venv 的 `python -u -X importtime scripts/local_candidate_demo.py serve --data-dir <原目录> --port 0`，全程持有同一个子进程并持续读取 stdout/stderr；没有 TTY 包装、runpy、手动调用 main、额外服务或 /proc 访问。

最终 `attempt-2` 实际退出 0，支持完整验收：

| 观察 | 实际结果 |
| --- | --- |
| 认证就绪 | GET `/api/projects` 200 且含原项目；spawn 后约 3.834 秒 |
| 已有结果读取 | 随后 10 GET 均 200：首页、两 JS、项目、NATURAL_PA 目录、CSV 结果、同实例 P-A v1/v2 各自人工入口及 artifact |
| 结果一致 | CSV sum=30，P-A v1/v2 artifact 内容 hash 和版本与原回执一致，owner 仍 PENDING |
| 只读写门 | POST `/api/projects` 返回 405 |
| 同一子进程退出 | PID 32310，直接发送 SIGINT 后 `Popen.wait(15)` 返回真实退出码 **0**，约 0.618 秒；无 fallback |
| 端口关闭 | `connect_ex` 原始 errno=111 / **ECONNREFUSED**；没有把权限拒绝、超时或其他非零值算关闭 |
| 数据保留 | 原 11 个夹具文件逐项 hash 相同；48 张表全部持久行摘要相同，Run 行数 4→4 |
| 日志完整性 | 两 reader 正常收尾，无 reader/eventlog/snapshot/端口错误 |

DB 前后 SHA256 均为 `32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780`。0 Worker、0 新自然 Run、0 模型请求；没有再次执行 P-A/P-B 生成、材料运行或锁恢复矩阵。

有限独审已只读核对原始日志、真实 wait 返回码和 errno，并重新计算 48 表及 11 文件摘要，无本范围剩余阻断；审查者没有重新启动服务、HTTP、Worker 或模型。

## 诊断边界及分期原件

探针记录 spawn 前后、每行 stdout/stderr 接收、URL 提示、认证 HTTP ready、SIGINT 及 wait 返回的 wall/monotonic 时间。`sim2act.api` import 行由父进程在 spawn 后约 2.019 秒收到。**这些绝对时刻是父进程接收上界；`-X importtime` 原日志仅提供模块 self/cumulative 微秒耗时，不能冒充子进程精确导入起止时刻。** URL 提示仅用于确定自有 loopback origin，实际认证 HTTP 成功才算 ready。

外部诊断窗口为启动 60 秒、HTTP 成功响应观察 60 秒、SIGINT wait 15 秒。同步 HTTP 的分阶段超时不是硬取消总时钟；每次 GET/POST 返回后仍核截止，迟到响应不能算 PASS。任何日志线程异常或最终检查失败均保留错误、禁止 PASS；只有自有 Popen 超时才可有界清理，fallback 也不能改签优雅退出通过。

先前探针冻结 `9346ff7d5b847312a53bc46988f554c852456aa8` 的 `attempt-1` 原 stdout 为 PASS，真实 wait0、HTTP 和数据不变已取得，但未记录端口 errno。独审指出 `connect_ex()!=0` 会误纳拒绝/超时，故该阶段不作为最终严格端口验收；只改诊断后在 `7978949` 有界重验一次，两个阶段原件均保留。独审还在执行前补上 HTTP 迟到返回和 reader 异常的假通过边界。Ruff 在最终探针字节上通过；没有重复自然重测或以轻测替代本次实际服务执行。

旧两个 15 秒启动探针仍为 **FAIL**，旧 TTY 包装器 exit1 / 子服务真实退出码未知的记录也保留。当前源码的 serve 提示已经 `flush=True`；本次显式 `-u` 增强诊断可观测性，**不能由 stdout 缓冲风险断言旧导入阶段失败根因**。本次新 Popen 的 exit0 是另一场实际验收，没有补称旧记录通过。首包 P-A 最初异常仍未知，原失败 Run 未重放或改历史。

## 交付及未执行范围

- [诊断脚本](../../scripts/diagnostics/local_candidate_serve_probe.py)：从 checkout 使用已有候选路径及已有合成数据，输出必须是新的夹具外目录。
- [原始证据和独审](../evidence/candidate-serve-lifecycle-20261016/README.md)：两阶段原始 stdout/stderr、逐行接收日志、receipt、执行命令、输入保全及独立审查。
- [原候选 ZIP](../../deliverables/pa-first-use-candidate-20261016/Sim2Act-local-candidate-fc69c863f57f.zip) 保持 1,515,823 字节，SHA256 `0ff78bc7330bcbbd5cc2a9fff76bb3cd2d2cd4e9ec37a3a0e1873acd50c74507`；候选 manifest 仍指向 `fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675`，没有重打包或替换载荷。

普通启动继续要求 PostgreSQL，本次是显式 SQLite mock 只读验收。Windows、PG、原生浏览器、真实模型/场景/人工语义、远端 CI、部署均 NOT_RUN，真实自然批准门/总账缺口与额度 0 保持。旧满盘最后独审未落盘的缺口没有补回。

最终交付仅在冻结探针后增加本说明和证据。普通分支推送的精确最终 SHA、远端相等、工作区/未推送差异、原远端 refs 和输入 hash，在 checkout 外的 `candidate-serve-final-delivery-verification.json` 单独记录；不以探针冻结 SHA 代替交付 SHA。
