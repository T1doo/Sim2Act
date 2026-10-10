# Report 历史读回的有限稳定性修复（2026-10-10）

产品与测试冻结 `47388f573746daa27f8d5790ca358eef91378ad5`，358 文件、69 产品文件。相对开发分支 `754f0c61dab111ada2db69bfeb8e8cccdfe2ad95`，产品只修改 `src/sim2act/report_presentations.py`。范围是同一次 Report presentation history GET 内，同一 definition 已完成的新鲜完整 scope，供其纯 readback 比较复用。每个 definition、每次请求仍完整重验；无跨请求缓存，无持久校验 token，无客户端上下文。

原 scope、propose、写 check 的 AST 完全相同。公有 load/readback 仍独立做新鲜校验；写 check 仍走两个完整 scope。保留当前授权、principal/project/app、source/version/grant/期限、PROJECT checks/locks、plan/seal、实际 Run/version/fence/result、完整 proof/check seal 与未知状态守卫。schema、worker、注册器、业务定义、前端、HTTP/测试时限与 resources-history 原 SQL observer 均未改变。[字节证明与证据](../evidence/readback-stability-20261010/README.md)。

## 原失败与本轮有限诊断

两项原失败分别读取原始证据，不能相互替代：

- [807 Report 原失败](../evidence/csv-dag-internal-reuse-20261010/pg-807/test_actual_late_receipt_curre0/failure.json)：原 `idle(6s)` 在 accepted 晚回执后等待最后 presentation history GET；前一 app/history 已 200，最后 GET 无状态。原日志没有该请求 SQL、CPU、锁等待或主机负载时间线，不能归因为当前观察到的开销。
- [42b resources-history 原失败](../evidence/linux-convergence-42b7a99-20261008/pg-first.xml)：原 Future 10 秒失败；原 observer 记录 395 项 project/grant graph 锁、跨度 17.59 秒、无 SQL 错误，HTTP 结果未记录。该 observer 对每条应用 SQL 额外执行 pg_backend_pid 与 SET LOCAL statement_timeout；本轮未改它。

在原开发基线 5427 上各一次有限剖析：SQLite 原 same-checks 页面通过，PG 原 same-checks 页面与 resources-history 节点通过。两原超时未稳定复现，继续 **OPEN**。实测 PG 非空 presentation history 每次 6,132 条 SQL、15 次 Report.load、2 次完整 scope；其墙钟 4.317/4.788 秒。原页面顺序等待 app/history、presentation history 后渲染，重复完整校验是明确的正常用户开销点。

473 的对应 GET 为 4,010 条 SQL、10 次 Report.load、1 次 scope；SQLite 为 6,133→4,011 条 SQL。PG 该请求 FOR UPDATE 总数 1,410→920。计数对应同一原页面的实际调用，不泛化为全部请求。最终墙钟与 CPU 记录仅诊断：基线/最终 profiler 版本不同，最终作者两库与独审并发、4 CPU cgroup；不是公平性能基线，也不证明原超时根因或稳定性验收。scope gate 本身的字段与逻辑没有削减。

下一次真实慢读若出现，应同时保全 request 开始/完成、原始 SQL 跨度、事务阶段、数据库 wait_event/阻塞关系、线程 CPU 与主机 cgroup/并发负载，避免记录参数或凭据；区分顺序前置 GET、纯校验 CPU、数据库查询/锁等待及测试观察器。没有真实慢读证据时，不靠反复重跑或加长 6/10 秒门槛关闭 OPEN。

## 精确 CI 样式修复

5427 的 Windows native run 38023764691/job 114130132129 在 2026-10-10 04:22:29 UTC 失败：72 项 Ruff 风格/导入问题，分布为 CSV DAG fixture 8、backend 58、UI 6；E701 21、E702 45、I001 5、E401 1。Setup 与 native API-worker-PowerShell smoke 成功；工程套件在 JUnit 前停止，Edge 跳过。这不是 72 个产品测试失败，也不是已定位 Windows runtime 故障。

`754f0c61dab111ada2db69bfeb8e8cccdfe2ad95` 只整理三份测试的样式和导入顺序，非导入 AST 与带作用域的全部导入/别名等价，69 产品字节与 5427 相同。完整 `ruff check src scripts tests` 与 `mypy src` 通过；未改检查严格度、CI、依赖或预算。新精确 [run 38024430136](https://github.com/T1doo/Sim2Act/actions/runs/38024430136)/job114132123197 的 Ruff、mypy、Setup 与 smoke 通过；2026-10-10 04:47 UTC 工程 pytest 在配置15分钟作业上限附近被取消，JUnit属性为863 tests、26 failures、38 skipped、0 errors（未完成，不能推算全部收集数量或整套通过）。Edge SKIP，Report及Cleanup成功。原始日志没有这26个失败节点与详情，未上传JUnit artifact；额外只读 job/check-run API受工具endpoint限制，细节 NOT_RECORDED。后续只读GitHub job公开annotation已确认超过15m0s上限；26个F标记全部先于取消，不能将这些失败归为取消导致，具体产品/夹具归因仍未知。artifact API为空，754无其他run。正常开发push自动产生6eb42aa的后续run38025760656（同473全部358冻结字节），核验时in_progress，不是通过；本代理没有取消、手动rerun、改CI或放宽时限。新的native工程失败/未完成保持OPEN。原日志私下保全，公开精确摘要和原文摘录。

## 边界

作者必要 59 节点双库集成范围、失败/跳过、真实页面与四种实际旧源码升级，以及独立冻结复核见[本轮证据](../evidence/readback-stability-20261010/README.md)。通过仅适用于记录的精确版本和限定范围。

Report GET idle 与 PG resources-history Future 超时仍 **OPEN**。HTTP200 其余损坏响应形式/入口提示与逐 item history map 限制保留；Windows900/Edge240/Node150 未验收。`LIVE=0`、真实模型调用0、正式发布关闭；PROJECT `PENDING/BLOCKED_PARTIAL`，semantic `UNKNOWN`，owner `PENDING`，overall `NOT_ACCEPTED`。不修改 main、强推、部署、凭据或安全网络设置。
