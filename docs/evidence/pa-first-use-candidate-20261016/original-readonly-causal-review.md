# 首包P-A per-use停RUNNING：独立只读因果核查

分析基线e7dcdb4ff25e5765be5dc34a4edc72ecba1929bc；原实际执行源0f0819a6a481841a0221cc69f75959326f264529。本报告仅分析首包失败Run run_be5e46f6c8794042bc18f2f9ca7ea6a7，不重放、不恢复、不写原DB、不开新自然fixture或锁矩阵；根为唯一仓库写入者。

结论：不是异步业务尚未跑完的早轮询。原Worker.once同步调用已经返回True，但True只代表领取了Run。自然处理捕获DomainError后，在原租约已失效时fail_owned会按fence边界不写任何状态，正常返回；该路径解释RUNNING/error=null/无终态事件。**哪一个原始错误、哪个具体事务先耗尽lease尚无原时序证据**，不能定为旧F9同因或声称已复现具体锁根因。

## 从保留原件可确认的时序

只读sqlite3 mode=ro/query_only=ON核原synthetic-demo.db，读取前后文件SHA256相同：bf2293cb3d5f96d9a054596d7e1cccd9905e1088f69620e9fc4e2989375b1d4c。

- accepted created_at1792181079.3809516；CLAIMED1792181085.4630244，fence1，唯一worker_c3ba643d9ebc44878cf3249abd87da51。
- read_pick/resource.read VERIFIED事件1792181089.2296927。只有这一条operation，context tools1/requests0/repairs0/reserved_tokens0。
- 持久lease_until1792181122.4911053；原lease配置30秒，因此最近一次成功renew在1792181092.4911053。heartbeats行at1792181092.4119012；DB最后mtime1792181092.4927752与这次commit相符。
- 没有任何runtime Attempt、MODEL_RESERVED或模型响应回执。原mock-receipts只有生成3条，PA运行handler没有被调用。失败位置处于首个local read之后、首个model reservation提交之前；不应归因真实模型请求超时。
- Run及AppRun均RUNNING、无error/output/typed result；Run version1、cancel_intent false，未见竞争claim或状态命令。
- worker-receipts最后落盘mtime1792181163.3938835，约比持久lease晚40.903秒；HTTP receipt mtime1163.3912723，prepare.log最后mtime1163.5859299。

文件mtime仅是落盘观测边界，**不是Worker.once确切返回/GET开始时间**。GET /api/runs在读取job后仍做完整binding/proof；也可能花时间，不能把整个70秒空档全部归给Worker业务处理。现原件无monotonic边界，精确分配仍待新诊断。

已逐字比较原包实际installed worker.py/text_workflows.py/pa_spec_apps.py/natural_spec_runtime.py/app_jobs.py/db.py六文件与0f Git blob相同，排除本次分析误用后改产品字节。原根runtime-origin.json未生成，因为首次完整链失败；不把缺失文件当通过证据。

## 精确控制流与解释范围

scripts/local_candidate_demo.py(0f) Demo.once先同步worker.once，require(True)后才GET该Run并写worker-receipts。末尾Natural mock Run did not succeed是读取状态仍RUNNING触发的RuntimeError，不是worker抛出的未处理异常。

worker.py:670 once先claim，随后同步self.process(run)，最终return run is not None。它从不承诺True即终态。process路由app_jobs.process_job→pa_spec_apps.process_job→text_workflows.process_job的while advance；普通local/model业务均在调用线程执行，只有lease心跳是后台线程。没有“业务自动在后台继续、轮询太早”这一运行模式。

text_workflows.py:1019捕获DomainError后调用app_jobs.fail_job；app_jobs.py:1143自然家族转natural_spec_runtime.fail_owned。fail_owned:551先只读Run元数据，发现worker/fence/owner等变化、lease_until<=now、或状态不允许时直接return，不写STATE/error。Run原owner/fence仍相同且RUNNING，无cancel证据，所以“原lease已经失效，错误收尾安全拒写”是强控制流推断。具体异常code可能来自guard/renew/其他验证，原件没有保存，不能将其断言为已经抓到的异常栈。

Store.guard(db.py:994)先source_scope_gate，再读Run并核lease；Store.heartbeat同样在BEGIN IMMEDIATE内调用guard，且原CAS拒过期续租。过期后fail_owned不越权落FAILED是安全边界，不能通过移除lease/fence检查、吞异常、人工改状态或延长预算来“修复”。

text_workflows finally stopped.set/join(timeout=2)只处理心跳线程。存在心跳调用若尚在driver/full guard中，join2后仍可能存活的结构性可能；没有thread.is_alive观测，不能断言该次确有泄漏或以它替代最初因果。但该线程只续租，不执行模型或业务步骤，故即使迟退也不构成后续业务进展。

## 优先观察的具体候选

1. **前台重复完整PA per-use来源证明，持BEGIN IMMEDIATE跨过30秒lease。** pa_spec_apps._bound:748先app_jobs.load_binding(return_release=True)，app_jobs.load_binding:527已调用pb_natural_uses.bound；返回后pa_spec_apps._bound的pa_use分支:791再调用相同bound。两次之间只有identity/accepted等读取。PA bound→review:284分支还spec.verify_origin:323，可能重复完整生成来源和引用证明。这个结构是源码事实，但原件没有profile，不把它写成已实测瓶颈。
2. **BG心跳自身完整scope检查的持锁时间或前台writer占用，导致真实续租不成。** Store.heartbeat执行Store.guard/source_scope_gate，不能简单等同于短UPDATE。原失败没有BEGIN/acquire/commit/exception和heartbeat halt日志，不能确定是BG取不到锁还是拿锁后scope证明耗尽lease。
3. **其他DomainError在lease结束后才被发现/收尾。** 初始model advance在lock_live/bound/receipts/commit_guard/effective、wire构造、renew与reserve之间都有失败点；零Attempt只能把最终失败界限缩到reservation提交之前，不能辨认原始code。原预算300秒deadline尚长于持久lease，不能把“lease失效”叫300秒Run预算耗尽。
4. **同步调用后的GET证明成本扩大观测时差。** 检查job先读状态再完成证明；mtime不能分辨Worker处理与GET各耗多久。它不会启动Worker，不能使已退出业务正常推进。

## 最小有界观测建议（不在原Run执行）

一次新独立合成Run保持原300秒/30秒、只Worker.once一次，不drive/retry，包围以下阶段并把trace写独立文件/内存，失败也保全：

- demo/Worker边界：claim开始结束、process开始结束、once返回、GET开始/取得body/receipt落盘；epoch与monotonic均记。
- Store.tx attempt/acquire/commit/rollback/exception：thread、SQLAlchemy+driver connection、调用栈/阶段、driver code、进入/离开lease字段，不记录敏感请求正文。
- 具体阶段：Store.guard source_scope_gate前后及leasecheck；app_jobs.load_binding；pb_natural_uses.bound/review与spec.verify_origin；pa_spec_apps.bound/receipts/commit_guard；natural.advance_model初始事务/effective、sync renew、reserve。
- 心跳：attempt开始/结果/原driver code、failed latch/recovery/defer、thread结束，finally join前后is_alive；保留原3次/5秒/0.1秒/cadence。
- fail_owned：开始、结束或跳过的明确reason、当前now/lease/fence/worker/status；只添加诊断，不能改变其授权判定。

若证实同调用同connection、事务、owner、版本与无写read segment内重复证明，可优先通过私有out参数传回刚完成的精确proof结果，后续仍保留fresh commit guards；不能加跨事务memo、信任caller布尔、跳过live权限/版本。先有真实phase/tx证据再决定实现，不直接扩Store timeout、WAL、lease或重试预算。

## 可复核原件

/tmp/f2-pa-stuck-0f-readonly-timeline.json：原Run/heartbeats/events/operations与mtime、六文件hash、DB前后hash，所有数据只读。
保留原件：/workspace/local-candidate-clean-install/failed-pa-run-readonly.json；原synthetic-demo目录及demo-prepare.log。既有f9-pa-extra-history-failure-state是独立旧案，未建立相同事务时序，仍不合并。
