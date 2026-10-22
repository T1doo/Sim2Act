# 冻结版本的独立进程恢复

产品实现冻结在 `48028e8392500d2cdcabafb5edecee5716781f65`。本片没有改 src、tests、预算或资格门，没有重复37/20测试，没有 G0、Cold2、W5、真实模型或外部业务 HTTP。

**一次 PASS**：原进程 `8131` 包含实际 Store/Worker/Mock 接受路径和本地 API；原调用在完整 V2 accepted 已持久化、完成函数尚未提交时以既有测试 BaseException 边界中断。原 API 正常停服、线程 join、Store dispose，父进程 `wait()` 确认其 exit0 后，才创建新 API 进程 `8152`。新进程使用同一 SQLite 文件和 sidecar，未 initialize/migrate/reset、未重新构造 Run 或补证，无 runner。

原进程复用已独审夹具的 Source2＋正常 extract1＋中断 extract1，实际 **4次 Mock**。既有共享夹具防越界 guard 为8；本次固定前缀只执行这4次，未把它改成产品预算。新进程对 call/reserve/accept 和模型调用设立即失败见证，实际 **0调用**，未重占额。4个实际本地 HTTP 请求为原 API GET、新 API 完成 POST、GET、已知成功后的同键幂等 POST；不称 HTTP 请求为零。

恢复结果的完整 compiled/result 严格 JSON 表示与原中断点已计算值一致，包含原业务指纹和精确回执。原 sidecar 字节 SHA 相同；所有非 runs/protocol_jobs/events 表逐行指纹不变。仅原 Run 一行、其协议结果一行改变，原事件全部保留并新增4事件。完整 SQL 参数表明新 API 只有3 UPDATE（均同原 Run）和4 INSERT events，0 DDL/DELETE/新 Attempt/新槽。`api-sql.json.gz` 保存4087条 cursor SQL及参数，原进程14716条另存（包含独立合成库初始化55条 CREATE）。DBAPI commit 回调未另行记录，不声称旧正常完成与恢复的有序 SQL 字节完全相同。

Run `created_at=1800000021.0`、原 lease_until `1800000051.0`，新进程显式合成业务时钟 `1800000059.0`，原 Run/provider deadline 均 `1800000321.0`；原 lease30/run300未延长，原接受见证未更写。完成 fence 从1到2，随后旧 fence 的真实 `Store.guard` 在 UPDATE 之前返回 VERSION_CONFLICT，完整数据库快照不变。该拒绝同时涉及已完成状态/期限/fence等原谓词，不能据 `Stale worker lease` 推断仅一个比较失败。

两个自有进程均 exit0、线程正常 join、连接 dispose；`cleanup.json` 为 CONFIRMED、无错误/拒绝/未知进程操作，后核两个 PID 均不存在。不是杀进程模拟崩溃，也不是操作系统重启或 PostgreSQL 并发验证。产品仍要求 test_only+mock；合成时钟只作语义证据，不是30秒或 G0 性能验收。

实际命令（仅此一次，不自动重试）：

```text
timeout --signal=TERM --kill-after=10s 180s /workspace/Sim2Act/.venv/bin/python /workspace/Sim2Act/docs/evidence/protocol-extract-process-recovery-20261022/probe.py run /workspace/sim2act-extract-process-20261022
```

工作外限180秒＋共享清理10秒；实际在外限内 exit0，未单独计量 CPU/精确 wall，不从日志 mtime 推算。原件位于 `/workspace/sim2act-extract-process-20261022`，启动原文在同级 `.launch.log`；复制原件、前后闭库、SQL、完整 HTTP 回执及 MANIFEST 均在本目录。

启动前独审修正了 harness 清理累计等待、拒绝后再换 signal、probe未单独冻结的问题，均在执行前修正，无运行或自动重试。最终 `probe.py` SHA256 `58625657951246bf07d59268ad4fc71411617d71265695c352e89a27aca14b67` 获 `/root/independent_gap_review` 静态限定 ACK，单独 hash 及旧553文件清单在每次启动前/结束后核验；执行期间未改源码。共享清理错误或访问拒绝黏性 UNKNOWN，不写 PASS。归档阶段一次只读参数索引假设错误与纠正另见 `archive-note.txt`，未触发新业务运行。

这是现有窄恢复的进程级闭包，不扩多请求、UNKNOWN、V1、source/cold/bounded-check，不给真实账户、语义验收或完整 F2 签收。
