# 原候选 serve 完整启停证据

本轮接续交付 `8875c225561e23d432934599531bbd3e740daa3a`，最终诊断源码冻结 `797894987a62c4ca603256d7049a5529e2a79b3c`；候选载荷仍为 `fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675`。见 [验收报告](../../F2/CandidateServeLifecycle20261016.md)。`SHA256SUMS` 按相对路径覆盖本目录除自身之外的全部文件。

没有 DB、venv、配置或凭据。本目录原件来自本次自己新建的 `/workspace/serve-complete-acceptance-20261016`，所读库为原 `/workspace/pa-use-running-clean-install/Sim2Act-local-candidate/synthetic-pa-demo`。没有新自然 Run、Worker 或模型请求。

## 输入与执行

- `input-provenance.json`：实际基线/单写入者/容量，旧两失败探针、候选包/脚本、原 P-A 失败 DB 和本次只读 DB 的 SHA256。旧失败未重放、未改历史。
- `execution-command.json`：首诊断源 `9346ff7d5b847312a53bc46988f554c852456aa8` 的精确父启动命令及源文件 hash；`execution-command-2.json`：最终 `797894987a62c4ca603256d7049a5529e2a79b3c`、严格端口 errno 修正后的执行命令。两个阶段都是直接原 CLI `Popen`，没有 runpy/TTY 包装。
- `probe.log`、`probe-2.log`：根实际执行探针的 stdout。两条原 stdout 均 PASS；第一条未记录端口 errno，不作为最终严格端口验收，不能省略此阶段限制。
- `post-run-preservation.json`：最终原始输入八项 hash 不变、11 夹具文件/48 表行不变、Run 4→4、真实 wait0、errno111 及完整范围。

## 两阶段原始进程证据

每个 `attempt-1/`、`attempt-2/` 内均有：

- `stdout.log`、`stderr.log`：持续 drain 的原始子进程输出，其中 stderr 含 CPython `-X importtime` 原始模块微秒耗时。
- `line-receipts.jsonl`：父进程逐行接收时的 wall/monotonic 与内容；**不是精确子进程导入起止时刻**。跨 stdout/stderr 的收到顺序只代表父观察顺序。
- `receipt.json`：原 Popen argv/PID、spawn、URL、认证 projects ready、随后 HTTP、SIGINT 和 wait 时刻、真实返回码、端口与数据前后快照摘要、日志错误列表。

首阶段 PID32124、wait0、10GET200/POST405和数据不变保留；其 `port_closed=true` 来自旧版非零判断，未记 errno，不改写其原 stdout，也不签为最终关闭证据。独审指出拒绝/超时可能假通过后，仅诊断脚本改为只接受 ECONNREFUSED，并作一次有界重验。

**最终 attempt-2 PASS**：原 CLI PID32310，实际 `Popen.wait(15)=0`、无清理 fallback；`connect_ex=111 / ECONNREFUSED`，确认端口关闭。认证 ready 在 spawn 后约3.834秒；随后10GET均200、POST405；同实例 P-A v1/v2 artifact 内容 hash/版本与原回执相同，owner PENDING。11文件及48表持久行摘要相同，DB仍 `32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780`。

60秒启动、60秒HTTP成功观察、15秒wait是外部诊断窗口，不改业务预算。同步HTTP分阶段 timeout不提供硬取消保证；返回后再核截止防止迟到结果算通过。日志读取/最终检查异常和任何fallback都禁止PASS；拒绝不重试或升级。

## 独审及历史边界

- `independent-design-review.md`：只读设计审查，建议原CLI、实际ready、持有Popen取真实码；落盘时未运行探针，保持该时点结论。
- `independent-final-review.md`、`independent-final-proof.json`：冻结源码和两个阶段原件的独立只读审查，不重新启动服务、HTTP、业务或进程操作。

此前两个15秒探针仍FAIL，旧TTY子服务退出码仍UNKNOWN，原件在[上一轮证据](../pa-first-use-candidate-20261016/README.md)，输入hash确认未变。源码print当前已flush=True；不能由缓冲风险定旧import失败根因。本次新Popen exit0不补签历史记录。原P-A最初异常仍UNKNOWN，旧F9/恢复矩阵不重跑，旧满盘末次独审缺口仍在。

产品src/原候选脚本和ZIP、预算/lease/guard/权限无变化；普通启动仍PG，本次仅显式SQLite mock只读验收。Windows、PG、原生浏览器、真实模型/场景/人工语义、远端CI及部署均NOT_RUN。
