# 新鲜本地 Mock 前缀 → 首个 G0：仅设计与可行性

只读基线/远端 `dc9b6350c3f184f6184be35727c6d7fb2ade6883`，分支 `dev/production-trial-stages-20261018`；main `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。本轮没有导入产品、创建数据库/Worker/fixture、调用 Mock/模型、运行测试或 producer、实现 launcher、分配运行目录或新建执行窗口。仅读源码、解析 AST/hash、保存设计并独审；本轮实际运行预算为0。

## 可行性结论与授权范围

允许保留既有本地合成测试的有限 Mock 后，[此前零sender构造阻塞](../cold-first-admission-entry-design-20261020/README.md)在设计层可解除：既有正常路径可从全新 test_only SQLite 构造 Generate3→Source2→原提取/发布/实例→Cold首响应1，随后原 `advance_model` 自然进入首次 `_cold_model_before`。不能直接运行原完整 PB 测试，它会继续 Cold2、W5/G1/finalguard，且创建四个损坏副本，与本方案相反。

这里的“合法”限定**原有隔离合成测试合同**：沿用 `test_spec_production_controller.configured` 的三项既有测试替换——test_only/SQLite 环境断言、固定合成 account evidence producer、software qualification测试替换——及它将 AsyncClient 送入确切 MockTransport 的方式。不是现实生产账户/软件资格通过，也不是新增的生产许可。不再增补 ALLOW、不改原账链/鉴权/StageApproval/时间/预算函数。若“原鉴权”被要求连这三项原合成替换都不得沿用，则生产默认环境/真实来源依然 fail-closed，本方案不能构造；所需最小决定是是否允许原三项隔离夹具边界，而不是延租约或提供真实凭据。

本轮只给设计 ACK；未来须把具体有界 harness 实现并独审，再由用户另行明确一次新执行窗口。不能复用已消费的完整PB授权、永久取消的JS双actor窗口或任何旧DB/Run/过期批准。

## 新上下文的唯一有限路径

1. 在唯一新目录/新 SQLite 上沿用 `conftest.env`、`prepare_pb`、`configured`。先安装真实网络阻断、有限Mock计数、资源/清理保护；不通过导入旧闭库、手填事实/Run、改时钟/lease/fence/provenance或重签旧 seal 构造。配置 token 仅原 `isolated-noncredential-placeholder`，不读现实凭据。
2. 原 `apps.ready(style="ordered")` 完成三份 Generate 原收发和成功回执；只接受固定三个不同原步骤。原 enqueue、stage_review→StageApproveInput→approve_stage 绑定同一 Source Run，再原 Source两收发和成功结果。完整原 wire/body、Capture、journal、Attempt/Operation/usage、controller/archive来源照常落库；不注入批准DTO代替真实评审。
3. 原 extraction-options/review→明确ExtractInput consent→trial.extract_pb，两次原键调用只检幂等且均0新增收发；原resolve_trial_source核原两份请求/响应字节和 `SPEC_PRODUCTION_CONTROLLER_ARCHIVE`。不调用 `refused_archive_copies`，它是旁支损坏矩阵，不是合法前缀必要条件。原正常 release/instance保留。
4. 同一新库正常重新打开 Store/TestClient，沿用原冷环境 test_only断言；原 pb-use-review、明确use consent、enqueue及同键幂等、cold stage批准仍全部执行。Provider和Worker的transport字段仍保持原生产分支要求的None，不能改成另一个对象绕过原identity检查；仅原configured的AsyncClient构造替换把实际HTTP送入有限MockTransport。
5. Cold第一次原请求/响应、receive/archive事务、原renew、fresh lock_live自然完成，然后进入同一 `advance_model`/连接/transaction/读取epoch的真实G0。五函数 `_prepare`、`_graph_run_context`、`_graph_pb_accounting`、`_graph_resolve_trial_source`、`_graph_pb_archive_chain` 和所有下游完整扫描/鉴权/业务检查逐一保持原对象、代码、调用顺序，不能缓存、跳过或以stand-in替代。

## 计数、期限、输出与清理预算（未来提议，当前不消费）

| 资源/边界 | 明确上限与定义 |
| --- | --- |
| 实际出站Mock收发 | 最多6次：Generate恰3、Source恰2、Cold最多1；构造失败可以更少，绝不重试/补齐。按原 `configured.factory.receive` 的实际exchange计数，记录stage/attempt/wire关联 |
| MockTransport方法入口 | 最多8次：上述6次async实际收发，另有原Source响应构造器内部 `normal.handle_request(request)` 的2次本地同步委托；这两次不另造Attempt/slot。若实现去掉或改写委托，则不是本设计，不可悄悄改变计数口径 |
| G0内sender/transport | 0；入G0即永久关闭本次全部Mock收发额度，第7个实际exchange或第9个Mock方法入口在执行handler前拒绝，禁止Cold2 |
| 真实模型/网络服务 | 0；HTTPTransport/AsyncHTTPTransport同步/异步真实I/O与INET/INET6连接、DNS一律拒绝；ASGI TestClient无监听服务。保留MockTransport类/原方法及精确夹具handler，不把真实HTTP临时放开。原InternModel仅可经该Mock路径；MockModel/fallback及任何无关sender拒绝 |
| 业务限制 | 原TTL1800秒、各Run300秒、lease30秒、RPM间隔60秒、原7槽合同/输出7168/预留192000/wire32768/paid cap0全部保持。6次收发至少5个60秒间隔；“少跑第7槽”不是缩小/改写原合同 |
| 构造前缀wall | 从唯一子进程启动算起最多480秒，包含准备、真实RPM等待、所有原验证、接收和归档；任何原拒绝/未知响应即终止，不重建或换一个上下文 |
| G0wall/全轮wall | G0自原context manager进入前起最多120秒；全轮工作最多600秒，另TERM最多5秒、KILL最多5秒清理，总上限610秒。原期限先到即拒绝，外层剩余预算不续任何产品期限 |
| 磁盘总量 | 唯一运行目录全部文件（包括DB/WAL/SHM/journal、原字节、日志、artifact与manifest）最多64MiB；不借旧目录、不删原件腾空间、不新建副本/恢复矩阵 |
| 可执行硬限前提 | 未来必须验证封闭文件清单+预留/有界writer；SQLite DB/WAL/SHM/journal最多4个，各12MiB（子进程只降低RLIMIT_FSIZE，不改主机权限）；其余stdout+stderr合计2MiB、原wire/response归档2MiB、artifact合计2MiB、source/dependency manifest与元数据最多8MiB、诊断256KiB、控制消息64KiB、退出receipt1MiB，总预留<64MiB。所有额外临时文件计入闭合清单；不可把目录轮询当硬上限证明。未验证IO路径闭合时无启动资格 |
| 并发/退出 | 仅一个自有子进程和原Worker所需线程，无第二actor/服务/Worker消费循环；父进程只监控界限、持续排空有限输出并收尾。只对记录且核实归属的PGID信号；不按名字杀进程、不干预旧服务 |

上述数字是**尚未实现的保护合同**，不是已经保证的launcher能力。遇资源上限、网络tripwire、超额Mock、标识不符或清理不确定均结束为边界失败/UNKNOWN，不冒充G0业务拒绝。需要额外目录/预算时必须停，不自动扩大。

## 首拒绝与完整G0结束的停止控制

只在测试边界包一层原 `_cold_model_before` context manager；不替换五函数、commit、check、input_key、任何semantic producer、Store.guard或业务审批。外层wrapper以原worker/run/Cold首attempt/connection标识限定一次context，非Cold调用只原样委托。原context的 `__enter__` 也在G0计时/拒写范围内，不能把首binding排除。

- **拒绝**：让原G0完整抛出并完成原context的异常展开/失效。保留同一原异常对象、code/message/traceback及其 `_cold_admission_diagnostic`；再由测试wrapper抛专用 `BaseException` 终止信号（原异常为cause），避免落入 `advance_model except DomainError` 的reject写入、`fail_owned`或Worker失败终态写。不是替换原require结果、返回成功或恢复Run。若原context退出期间又发生异常，两个原异常/cause链都保留，不以observer错误掩盖。
- **成功**：原context至少完成首commit、enabled、原cold receipts、当前Attempt、parse/usage/schema/receipt、第二commit，以及context退出时最后完整图hash和原stop/有限期限检查，才记 `G0_COMPLETED_NO_W5`；wrapper在原context成功返回后立即抛同一专用BaseException。首commit或第二commit单独返回都不算G0结束。不得在yield处提早停。
- 原 `Store.tx` 明确捕获BaseException并rollback；此路径由 `Worker.process` 经 `app_jobs.process_job`、`pa_spec_apps.process_job` 委托给 `text_workflows.process_job`，实际心跳finally在后者1093行，仅调用 `stopped.set()` 和 `thread.join(timeout=2)`。这只能证明请求停止和最多等待两秒，不能证明线程已经退出；未来须核实对应线程存活状态及自有PGID已结束，仍存活/清理不确定即UNKNOWN。DomainError处理不会吞专用测试信号；此为静态可行性，具体shim/退出路径仍须另审。父/子只在最外层识别该类且限定对象/阶段；任何其他异常（包括非DomainError、资源/信号/observer/清理失败）均保持UNKNOWN/INCOMPLETE，不能转成原业务拒绝，不重试。
- 独立SQL拒写保护从原G0进入前到停止/rollback一直作用于确切G0连接，SQLAlchemy执行前拒绝INSERT/UPDATE/DELETE/REPLACE/DDL及写PRAGMA，正常rollback可用；W5第一句就是 `c.execute(update(attempts).values(status="VERIFIED"))`，在调用DBAPI前必须拒绝。只有SQL hook不足以证明所有可能DBAPI直写：未来shim审核还须封闭直接driver执行路径；未证前不启动。
- 原heartbeat/renew不停止、不跳过，原其它连接的元数据心跳保持，可能继续发生原SQLite竞争，不能据此称全库DML为0。保护的是G0读连接与W5；记录0 W5进入/0业务写入/0第七收发，而不是事后typed行0代替边界证明。异常停止后不“修正”Cold Attempt/Operation/Run终态、不执行NS_REJECTED/NS_SETTLED、不恢复或复用该新库继续；原已提交6次接收/用量/journal前缀原样保留，未完成的业务验收标INTERRUPTED。

## 已有诊断如何原样取得

首commit最后命名期限require拒绝时，直接保存原异常上已有 `_cold_admission_diagnostic`：原finite名字和值、原end与原那次stop读取、RunCheck.checked_at/deadline及`_graph_run_context_existing_row`的lease/version/fence、五阶段wall/check_calls/input_key_calls与incomplete。不重读DB/时钟填补，不把旧finalDB lease当失败瞬间变量。记录`end-min(finite)`和各原期限余量仅作派生字段，并分别列stop及原短路条件，不能把过期最小值自行认定为唯一因果。

命名期限保持原顺序：`run_check.deadline`、`source.expires_at`、`natural_spec_clock.deadline`，随后仅对原非None角色添加 `role.source.run_seconds`、`role.generate.run_seconds`、`role.platform.run_seconds`、`role.trial.run_seconds`、`role.per_use.run_seconds`，最后为 `frozen.run_seconds`、`draft.run_seconds`、`call.meta.deadline`、`call.node.run_seconds`。其中run_seconds项原值已经是 `job.created_at + run_seconds` 的绝对截止，报告不得再加一次created_at或把它当持续时长。五阶段每项原 `wall_seconds`、`check_calls`、`input_key_calls` 均为该stage前后快照之差，不是与历史运行相减；早拒绝只保存真实已进入阶段，可缺项，最多5项。

为了保留**早拒绝或成功**时未挂到异常的五阶段数据，未来允许一个极小的诊断observer：仅包 `_ColdCommitDiagnostics.__init__` 原样调用并保存该次真实实例引用（最多1个），不改其stage/_snapshot/rejected方法，不改五函数或计数顺序。停止并完成原context展开后，才复制其已有stages/run_context/incomplete标量到有界报告，不复制guard inputs/Row/正文，也不新增计时或全图扫描。它只保存诊断，不提供缓存/许可；其非零开销要标记，不能宣称与旧深observer运行零扰动可比。

若拒绝早于命名finite组装/require，私有拒绝diagnostic可能不存在，记录NOT_REACHED，已有partial stages照实保存。若G0完整成功，没有“拒绝finite/end/stop”；原成功第二commit authority_record中的deadlines若仅作已知边界提取，标签必须标明按冻结源码顺序派生，不能冒充原拒绝快照，且不可额外重读worker.stop/时钟冒充原值。本方案不通过反射栈跳转、重演producer或修改产品来补造成功的拒绝诊断。若原诊断缺失/observer失败，标UNKNOWN/INCOMPLETE，不为凑齐数据再跑。

因果报告只回答：原复合拒绝是否发生、原end/stop与哪些已记录期限的关系、五个真实阶段的实际时间/计数差值、完整G0还是前置未达。G0总wall包含首binding与退出守卫；五阶段不覆盖全部工作，未计入部分单列，不当成可追回CPU预算。即使G0成功，也不能关闭W5/G1/finalguard、七槽完整PB或真实模型资格。

## 未来收尾证据与最小后续事项

未来具体harness需先冻结并独审：源码/测试/依赖逐文件hash及五函数identity/code；唯一环境/进程/目录、实际三项原隔离替换；完整新合同/原批准与stage链、6次原wire/response/usage/slot计数、normal-source字节一致；G0进入/退出、SQL执行前拒写、实际诊断、退出分类；恢复所有观察器/fixture替换，结束自有heartbeat/client/Store/线程，核自有PGID为空，原件大小/hash与预算用量。stdout/错误输出截断须显式标记，诊断关键字段无法持久保存则结论UNKNOWN。

此轮只读设计不做上述准备或验证。**最小后续事项**不是重跑完整PB：先实现并只审具体“原新鲜6Mock前缀+单次G0+执行前停W5”harness的停止/网络/资源/自有进程保护；通过后，用户另行决定是否批准一次该有限新窗口（6实际Mock/8方法入口、600+10秒、64MiB），明确沿用原三项合成资格替换。若不同意这些前提，停止在本设计，不请求真实凭据、不改生产默认拒绝条件。

## 官方语义核对

只读核对Python3.12官方资料：[Thread.join](https://docs.python.org/3.12/library/threading.html#threading.Thread.join) 的超时等待须另以 `is_alive()` 判别是否仍存活；[RLIMIT_FSIZE](https://docs.python.org/3.12/library/resource.html#resource.RLIMIT_FSIZE) 限制单个进程可创建的文件大小，不是目录总量上限。上面的清理与文件闭合要求据此限定；查资料没有执行产品或创建运行窗口。
