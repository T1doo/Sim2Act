# P-A 首次新材料 per-use：缺口、观测与直接回归

只读基线 `e7dcdb4ff25e5765be5dc34a4edc72ecba1929bc`，开始时clean。核对了旧0f JSON与HTTP/worker/mock回执、当前 `test_pa_natural_uses.py`、`test_natural_sqlite_heartbeat.py`、当前候选脚本和关键guard路径。没有连接旧DB，没有重放旧Run，没有启动新fixture，没有修改仓库。

## 旧0f精确事实

旧原件 `/workspace/local-candidate-clean-install/failed-pa-run-readonly.json` 中：

- Run `run_be5e46f6c8794042bc18f2f9ca7ea6a7`，状态RUNNING、error=null、version=1、fence=1。
- 只有一条CLAIMED，worker `worker_c3ba643d9ebc44878cf3249abd87da51`。只有read_pick的resource.read operation VERIFIED；tools=1、requests=0、attempts=[]。runtime MockTransport尚未被调用。
- binding明确 `pa_base_data_version=0`：这是新实例保存后的**第一次**执行，直接采用新材料/新Goal per-use；没有先跑原材料任务。
- accepted created_at=1792181079.3809516；CLAIMED=1792181085.4630244；read_pick event=1792181089.2296927；保存lease_until=1792181122.4911053。原natural_spec_clock deadline=1792181379.3809516，即原300秒。
- 同目录worker回执：CSV SUCCEEDED、生成PARTIAL、这条PA RUNNING；每个fence1/1claim。mock回执只有generation三条，无PA runtime条目。HTTP回执确有review200、相同pa-use-runs两次202、最后Run GET200。
- 旧回执没有Worker.once退出墙钟、异常栈、scope耗时或tx持锁区间。RUNNING/error=null不能区分错误是在何段发生；不能据此证明是SQLite BUSY，也不能认定与旧F9 WAITING_RESOURCE同因。

源码允许一种需要新trace验证的解释：runtime第二步尚未reserve就发生guard异常，随后 `fail_owned` 因同owner lease已失效而拒绝写终态，所以原Run保持RUNNING。这符合安全边界，但仅是推断；不能据有限旧原件断定具体触发函数或异常。

## 实际覆盖差异

| 入口 | 首次执行形式 | per-use开始时结果版本 | claim保证 | 本次缺口 |
|---|---|---:|---|---|
| `tests/test_pa_natural_uses.py:37–43` base_pa | 先默认SOURCE `/runs` | 1 | drive_to_success最多3claim | 未覆盖首次per-use 0→1 |
| prepared_pa(history=True) | 再COLD，然后THIRD | 1→2→3 | 同上 | 已有历史，不是旧0f首用 |
| `tests/test_natural_sqlite_heartbeat.py:139` | SOURCE默认Run，再COLD per-use | 1→2 | 每Run仅1次Worker.once | 严格单claim，但仍缺0→1 |
| 旧0f包实际loopback安装wheel | 生成保存后直接COLD per-use | **0→1未完成** | 1claim | 本次要补的直接节点 |
| 当前c9/e7限定候选 | 原材料默认PA，再PB per-use | PA v1 | 1claim | 明确PA新材料NOT_RUN，不能算此故障修复 |

旧0f包含同项目已完成CSV应用、生成Run及候选；现heartbeat测试env有初始CSV资源，但没有先运行CSV应用。实际HTTP transport也分别为loopback与TestClient。首用版本0是已确认合同差异；项目形态或HTTP transport影响时序只是待验证因素。

## 最小自然时序观测

只在全新自有目录构造一次新PA app/Release/instance。使用原预算：lease30s/run300s/maxrequests4/max_tools4，无wallclock替换、无sleep放大、无超时放宽。用当前候选固定single recipe与显式MockTransport。Worker.once仅调用一次，返回后立即记录并断言；RUNNING也作为FAIL原样保存，不自动重试/重新claim。

复用 `test_natural_sqlite_heartbeat.SqliteTrace` 的tx/heartbeat记录，补**少量函数层耗时/异常**即可定位read_pick到reserve之间：

1. `Store.guard`，`goal_applications.source_scope_gate`，`pa_spec_apps.job_scope_gate`。
2. `pa_spec_apps.bound`、`receipts`、`commit_guard`，以及per-use调用到的 `pb_natural_uses.bound/audit` 的实际函数（按当前源码实际命名选择）。
3. `natural_spec_runtime.advance_model` / `renew`、`Worker.reserve`。
4. `natural_spec_runtime.fail_owned` 进入/返回/异常，以及 `text_workflows.process_job` 捕获到的DomainError code/message。

记录调用name、depth、thread、monotonic开始/结束/异常及已有run_id、fence、已知lease/deadline数值；in-memory累积，finally落盘。每函数仅entry/exit，不开逐SQL日志或逐调用文件写。不得为观测在guard内部插入额外SQL、写缓存或提前返回，不改变guard行为。tx至少含attempt/acquired/body-complete/committed/failed/exit，区分等待时间与持锁校验时间。记录sync renewal已提交标记和background错误码，以免把CPU验证/递归scope耗时误叫数据库锁。

Worker退出后用普通read connection导出Run完整行、CLAIMED/步骤事件、binding、AppRun、operations、attempts和未知结果计数；保存HTTP完整request/status/body和mock线报。最先落内存trace，避免诊断读取失败掩掉原异常。不使用store.tx做持续观察（它会BEGIN IMMEDIATE并影响竞争）。

如果一次自然时序不复现，先分析耗时与调用计数，不盲重跑整fixture。只有定位到具体边界后，再用一个有界调度的小测试重现该边界；不启用旧Run恢复或扩展故障矩阵。

## 最小直接成功回归：一份PA软件，两个per-use

复用原 `setup + ready('single')` 保存PA候选、Release和空实例；**不调用base_pa/prepared_pa，不先默认SOURCE runtime**。

1. 断言实例data_version=0、data=[]、runs=[]。保存COLD材料/Goal，复用 `target_use` body（实际精确app/recipe/release/Goal fp）。review200，`instance_data_version=0`，预览前后全库快照相同。
2. 明确consent POST pa-use-runs202；原key相同body重复202返回同Run，并且不增加Run/AppRun/授权。一次normal Worker.once +单条COLD MockTransport响应；要求SUCCEEDED、fence1、恰一CLAIMED、原created_at/clock/principal/project/runtime不变。
3. 读取同Run spec-artifact和同Run人工GET，得到真实v1/COLD、PENDING/NOT_RUN。保存原执行Run完整行、AppRun完整行、typed v1行、artifact resource完整行与bytes SHA。
4. 同一app/Release/instance再保存THIRD材料+新Goal；review须 `instance_data_version=1`；新key明确POST，第二次Worker.once仅1claim、单条THIRD mock响应，真实v2。
5. 新artifact同app/release/instance；原v1行、原Run/AppRun/resource行及artifact bytes完全保留。instance只data_version1→2，revision/runtime/release/history保持。typed.run_id关联AppRun id，通过binding与执行Run id精确核对，不能直接把typed.run_id当执行Run id。
6. 关闭Store/API/进程；新进程新Store/API仅GET目录、精确app/实例、两个Run/artifact及同Run人工合同。冷读前后全库行相同；0Worker、0POST、0模型。只有读取已有PENDING合同，不合成owner ACCEPT。

自然最小直接回归为3生成mock+2个PA runtime mock，共5条，真实模型0；每Run仍原预算。CSV/PB不需要加入这个故障定位fixture。

最终候选若同时保留当前PB演示，再加上述第二次PA per-use，完整演示会成为6条mock（3生成+2PA+1PB）。须明确更新新候选回执和调用数，不能沿用旧5条通过证据或把已有PB结果预填成新执行；具体候选产品范围由root决定。

## 必要安全回归按触点选择

- 先上述一个精确首用0→1+再次1→2新节点；原完整 `test_natural_sqlite_heartbeat` 的SOURCE→per-use若无需改变，不必先重复慢fixture。
- 如果修复重复scope验证/相同tx证明，应保留每次写后重新查权限/版本的边界；可优先现有 `test_heartbeat_ownership` 的elapsed/wrong-worker和 `test_authority_refresh_detects_expiry_without_a_write`，都是轻量确定性节点。
- 若触及本地原子写组，选 `test_local_pure_precedes_atomic_preparation_and_commits_once` 以及一个相关写后撤权/lease边界；不要整套所有fault重建自然base。
- 如果触及heartbeat共享代码，选择已有真实SQLite短暂busy known/late、最终deadline回滚、late terminal不覆盖的小节点；不重复已通过完整heartbeat故障矩阵。
- 不允许通过延长lease/runbudget、跳过完整首验/最终guard、跨tx缓存授权证明或把一次Worker.once换成drive_to_success循环来完成此验收。

这是只读设计交付，尚未实际执行新复现或回归。旧0f FAIL保持原状态，Windows/PG/真模型/真实语义/远端CI均未执行。
