# resources-history 原首轮 10 秒超时：受控阶段调查

**结论：未唯一解释；不提交产品修复，不把重跑通过当作资源干扰根因。**
页面候选保持 `8bcafb0ce2735089f261748a385f16d127935fab`，基础 dev 保持 42b7a992。
本调查仅增加文档/外部仪器；产品、原测试、断言、原 Future.result(timeout=10)、
7000ms SQL 观察器上限及 Windows900 / Edge240 / Node150 都未修改。
LIVE=0，无真实模型、新 CI、部署、凭据或安全权限调整。

## 已有首轮证据

原全量源码 42b7a992：SQLite 1954 PASS / 97 SKIP；PG 2021 PASS / 28 SKIP /
2 FAIL。页面竞态由独立候选处理，本调查不改变这两个首轮结果。
第二个失败是原 `test_pg_resources_graph_share_project_first_lock[resources-history]`
在 `future.result(timeout=10)` 超时。首轮记录项目锁先行确实观察到、无 SQL 错误
或 40P01 死锁；响应状态尚未收集，不能从空字段推断 HTTP 没有返回。

图请求有 395 个 grants/projects 锁 SQL 前置事件（另有资源请求 7 个，总 402）；
图事件跨度 17.590 秒，最大相邻间隔 3.686 秒。原五项复查中的同用例同样为
395 个图锁事件，跨度 1.910 秒；本轮无故障观察为 395 个、1.893 秒。
随机 fixture ID/应用顺序使规范化 SQL 序列并非完全相同，数量相同不能证明每个
执行阶段完全相同。见 `archive-comparison.json` 和原归档路径。

首轮只有部分 SQL 前置事件；没有具体 Future 身份、开始/完成边界、原线程栈、
连接池等待、提交完成、客户端退出或当时资源采样。因此 SQL 事件持续进行
说明有阶段进展，但不能排除有限锁等待、调度暂停、观察器往返延迟、Python
校验代价或某个客户端退出等待，不能认定哪个 Future 超时。

## 外部最小仪器与本轮结果

只执行原测试文件的两个节点，没有重跑 2051 项。自有 PostgreSQL 17.9，镜像
固定原 digest，network=none、无端口、私有 Unix socket；测试保留全部原门、
断言和结果，源文件逐字节对照 8bcafb0 前后不变。

外部 pytest plugin 记录：实际 HTTP、Client enter/exit、原 Future 10 秒等待、
原 reached/release 事件、pool acquire/checkout/checkin、实际 psycopg cursor、
commit/rollback、history/current/build/load/expansion/authorize 阶段，以及进程
CPU/RSS/线程/负载样本。若原 Future 超时，保存线程栈及仅本自有数据库的
pg_stat_activity/pg_blocking_pids。仪器调用后才原样返回/重抛，不改返回值或
授权；计时包含仪器开销，不作正式性能基准。

| 原节点 / 模式 | 实际结果 | 说明 |
|---|---|---|
| resources-history，首个无故障观察 | 1 PASS，JUnit 6.979 秒 | `observed-first.xml`，原页候选未变 |
| resources-plan，无故障对照 | 1 PASS，JUnit 4.839 秒 | `normal-plan-validated.xml` |
| resources-history，明确 Python 校验等待注入 | 1 FAIL，原 TimeoutError | 诊断校准，不是产品新增失败/原根因证明 |
| resources-history，明确客户端退出等待注入 | 1 FAIL，原 TimeoutError | 诊断校准，不是产品新增失败/原根因证明 |

无故障 history 实际 HTTP：resources 0.060 秒、graph 1.912 秒；客户端退出
约 0.001–0.002 秒；最大连接获取 0.0053 秒、最大 commit 0.0022 秒。
原 Future 实际等约 0.015 / 1.877 秒。图请求记录 5878 次 cursor 往返，其中
3918 是原测试观察器的 `SELECT pg_backend_pid` / `SET LOCAL`，剩余 1960
包括业务 SQL 及 pre-ping；总 cursor 时间约 0.909 秒。当前无连接池耗尽、
死锁或长 commit/exit 的证据，但这些当前观察不能排除首轮存在瞬时等待。

两个正向诊断校准都只对私有夹具明确注入 10.5 秒等待，**不调整原 10 秒
断言或其他超时**。Python 校验暂停时，原 Future 在约 10 秒超时，线程栈落在
校验 wrapper/事件等待；事务 idle in transaction / ClientRead，blockers=[]。
客户端退出暂停时，HTTP 已返回 200、图请求也已结束；Future 仍 RUNNING，
线程栈落在 Client.__exit__，数据库连接均 idle，blockers=[]。这验证仪器能
区分 SQL 锁等待与线程/退出等待；不能把注入的原因套到首轮。

校准 setup 首次有外部仪器 NameError（误插客户端代码到 gate），原代码未变；
`normal-plan.log/xml`、错误仪器快照和 `instrument-setup-error.md` 保留。
该次仅是仪器缺陷，停止后修正仪器并使用独立输出，不覆写、不计产品结果。

`phase-summary.json` 保留准确阶段数值和超时活动快照。`current-environment.json`
记录现在的 CPU quota / 累计 throttling / 负载；没有首轮前后差值，**不能用于
给原失败归因**。未做 CPU 压力、SQL 延迟或网络/安全配置改变。

## 已证实与仍缺范围

已证实：原首轮项目优先序列存在、未记录 SQL 错误/死锁；本轮原节点能按原门
完成，池/事务/退出阶段均有界；原 Future 不只是 SQL 结果等待，也包含请求
函数及 TestClient 上下文退出；相同 TimeoutError 的不同阶段已校准区分。

仍缺：首轮的具体待完成 Future、其线程栈、SQL 活动/阻塞与资源时间线。
不能断言“就是资源干扰”“就是连接池/事务释放”或“已修复超时”。无确认的产品
根因，故没有产品补丁。后续若异常再次自然出现，应保留本最小仪器，在原
10 秒失败时抓取栈/池/SQL/阶段；确认具体路径后再最小修复，不能靠抬阈值、
删断言、增加 SKIP 或制造压力后的绿结果放行。

## 原 F2 与外部验收保持

[已归档原 F2 矩阵](../linux-convergence-42b7a99-20261008/F2-status.md) 已重读：
CSV 列绑定实际修改和受限 1–4 节点组合可用；一般 P-A/P-B 与非 CSV 明确
要求变更的实际输出/检查闭环仍部分，PROJECT revalidation_jobs 实际消费/
派发/受权终态仍缺。内部不可变 Release/审批/实例分离/兼容切换回退已实现，
正式发布仍关闭。一般语义、未见真实任务、外部效果核对与人工签收未完成。
Win11 普通用户安装/启动/停止/重启与实际 Edge 仍 NOT_RUN，Linux/JSDOM
不替代；历史 LIVE 不提供新预算，本轮 0 调用。

## 复现、清理与分支

`run_cases.py` 顺序执行三项后续观察/校准，要求显式私有测试 URL、LIVE=0，
验证源文件前后哈希，拒绝覆盖 summary。`diagnostic_plugin_first.py` 是首个
无故障 history 的准确仪器版本；当前 plugin 包含明确校准开关，默认无注入。
原测试入口保持 pytest 原节点参数，不启动新 CI。只在全新自有隔离环境与新
证据目录复现，不能指向共享数据库或覆盖归档输出。

全部测试结束后，`cleanup.py` 验证无测试 schema、角色、公共表，再移除仅
本任务容器、镜像和临时目录；原页面候选及其原证据不写入。普通推送本
调查分支 `dev/pg-history-timeout-investigation-20261008`，不合入 dev/main。

完整阶段事件以 `.json.gz` 无损保存，解压前后内容 SHA 和压缩 SHA 在 `trace-archives.json`；用 Python `gzip.open(path, "rt")` 读取。原日志/XML/首轮证据未改。
